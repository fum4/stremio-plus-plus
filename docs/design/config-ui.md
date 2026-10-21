# Configuration: one file, one UI

Status: **phases 1–2 built** (2026-10-21): settings file + UI, first-run setup, translation style. Builds on [public-release.md](public-release.md); this doc owns *how a user configures stremio++*.

## Decisions (owner, 2026-10-21)
| # | Decision | Choice |
|---|---|---|
| 1 | Where settings live | **TOML file, the source of truth**: `~/.config/stremio-plus-plus/config.toml`. Hand edits, agents and the UI all write the same file; the companion hot-reloads it. Secrets live next to it in `secrets.toml` (mode 600), never in `config.toml` |
| 2 | Per-person profiles in the addon URL | **Yes**: each install URL carries its own choices (languages, …) through Stremio's `/configure` flow. Phase 2 |
| 3 | Translator | Start with what the owner uses (**`claude` CLI subscription**, **Anthropic API key**) behind one adapter, so any other provider plugs in as one class |
| 4 | UI stack | **Svelte 5 + Vite** SPA in `web/`, built to `web/dist`, served by the companion. No SSR or Node at runtime |

## How it works
```
config.toml ──┐  (poll every 2 s; a broken edit keeps the last good settings + shows the error)
secrets.toml ─┤
              ▼
      config/settings_file.py  ──►  Settings (pydantic, extra="forbid": typos are errors)
              │
              ├─► subtitles/translators/registry.py  ConfiguredTranslator: rebuilds the backend on change
              ├─► subtitles/stt.py                   model + spoken language read per chunk
              ├─► downloads/manager.py               disk reserve read per decision
              ├─► downloads/cleanup_job.py           reserve + stale-after, read at start
              └─► app/admin.py  /api/*  ◄── web/ (Svelte UI)   [LAN port only; header + Host check]
```
- **Saving** goes through tomlkit: comments and key order survive, writes are atomic (tmp + rename).
- **Machine wiring** (ports, paths, LAN IP, domain, the CLI path) stays in `infra/env/` + `.env.local`; it isn't what a user tunes.
- **Security:** `/api/*` and the UI are 404 on the public HTTPS listener (https_guard.py). On the LAN every API call needs the `X-Stremio-Plus-Plus` header (forces a CORS preflight the companion refuses, so another site open in a LAN browser can't read or write) and a LAN `Host` (stops DNS rebinding). Secrets are write-only through the API.

## The translator adapter
`subtitles/translators/`: `base.py` holds everything provider-neutral (prompt, structured-reply validation, 3 tries, the hourly cap, keep-original on a bad reply, stats). A provider is a `Backend` with one method:
```python
async def complete(self, system: str, prompt: str, schema: dict) -> dict | None
```
Raise `TranslatorConfigError` for "can't work as configured" (no key, bad key, unknown model, CLI missing): the chunk fails and retries later instead of being stored untranslated. Then add a `ProviderInfo` row in `registry.py` (label, description, which secret, suggested models); the UI picks it up from `/api/providers`.

| Provider | Status | Notes |
|---|---|---|
| `claude-cli` | built | the owner's subscription; personal use only, so it stays opt-in for others |
| `anthropic` | built | official SDK, structured outputs (`output_config.format`) |
| `openai-compatible` | next | one backend covers OpenAI, OpenRouter, Groq, Mistral, DeepSeek, Gemini's compat endpoint, and **local Ollama / LM Studio** |
| `deepl` | to evaluate | not an LLM: strong EU languages, no batch-to-batch continuity |

Switching the default model or provider needs the same ~200-cue benchmark the owner judges ([subtitle-stack.md](../research/subtitle-stack.md)).

## What the UI covers today
Overview (server, translator calls vs cap, disk vs reserve, per-file chunk strips with the playhead, torrents with pins) · Subtitles (provider cards, API key, model chips or any id, a live "try it" on four sample lines with unsaved settings, limits; Whisper model + spoken language) · Downloads (disk reserve picture, cleanup age) · Install (addon URL, `stremio://` deep link, QR). Every control shows its `config.toml` key on hover.

Dev: `mise run ui:mock` (canned data, no host) · `mise run ui:dev` (proxies to a companion) · `mise run ui:build` (also run by `services:install`).

## First-run setup (phase 2, built)
Goal: a stranger with an Apple Silicon Mac goes from `git clone` to subtitles without editing a file or owning a domain.
- `mise run install` (setup + services + prints the UI link). Nothing is required in `.env.local`: the LAN IP is detected (`config/host.py`), the addon token is generated once into `secrets.toml`, and without `ADDON_DOMAIN` the addon is served under the streaming server's own stremio.rocks certificate (`tls/stremio_cert.py`: server.js keeps it, key included, in `<APP_PATH>/httpsCert.json`; the companion renews it through `GET /get-https` and hot-reloads it). The owner's own domain, TV control and encrypted token stay as optional env values.
- The UI opens on **Setup** until it's finished: This Mac (Apple Silicon, ffmpeg, server, disk) → Streaming server (one click: `POST /settings` with `infra/stremio-server/settings.json` + `remoteHttps`, refusing a zero cache) → Translator (pick, key, try it) → Speech model (download with progress) → Your TV (server URL + revert value; confirmed by a tick) → The addon (link, deep link, QR; ticked). It stays as a health page afterwards.
- `with-secrets.sh`, `install-repo-secrets.sh`, the `tls` agent and the doctor all work without the owner's age key; an owner host (ADDON_DOMAIN set) without the key fails loudly instead of minting a new token.

## Translation style
`subtitles.translator.style` (free text, ≤ 2000 chars, presets in the UI): it **replaces** the tone guidance of the system prompt (next to "as a professional subtitler would" the model plays it safe) while the id/format rules stay. Verified on Haiku 5.5: "cowboy" → *Unde dracu' ai fost, partenere? / Ne cărăm. Acum.* Applies to newly generated windows; **Regenerate** (Overview, `POST /api/subtitles/{hash}/{file}/regenerate`) forgets a film's subtitles so they're redone playhead-first, dropping any translation started before the click.

## Activity and logs (built)
The UI's **Activity** page has two tabs:
- **Activity:** a readable timeline (`app/activity.py`, rules in `app/activity_rules.py`, history in SQLite `activity`, migration 4).
  - Fed by the server-log tracker (TV connected, playing, seeks, torrents) and by every companion event.
  - Titles and posters come from the TV's addon requests, looked up on Cinemeta.
  - Repeats coalesce ("Romanian subtitles: 14 parts").
  - On first start it backfills from `companion.log`.
- **Raw logs:** server.js and companion lines, live (`log/hub.py`, an in-memory ring fed by the tail and a structlog processor, seeded from both files).
  - Filters: source, level, noise, search.
  - Untagged server requests are labelled **TV**.

What we can and can't see is in the PR. In short: no client IPs or timestamps in server.log, nothing from inside the TV app. Secrets are redacted on the way in (the authKey server.js prints, the addon token, API keys).

## Next
1. **Profiles + languages (decision 2):** `languages = [...]` per install URL, `behaviorHints.configurable` + `/configure` page; STT once per file, translation per language (store keyed by language, append-only migration); one prompt template per language.
2. **`openai-compatible` backend** (covers local models), then benchmark candidates on Batman.
3. **Server tuning in the file:** cache size (never 0) and the torrent profile from `infra/stremio-server/settings.json` move into `config.toml`, applied through `POST /settings`.
4. **TV from the wizard: built** (discovery, pairing in the UI, Type it for me, connection detected from the server log). Left: record `SET_SERVER_URL` on the Samsung (launch Stremio by app id, keys to the field) with the owner at the TV, then other TV OSes as people contribute them.
5. **Admin password** for the UI once hosts are shared beyond one household.
