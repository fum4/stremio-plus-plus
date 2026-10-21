# Configuration: one file, one UI

Status: **phase 1 built** (2026-10-21). Builds on [public-release.md](public-release.md); this doc owns *how a user configures stremio++*.

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

## Next
1. **Profiles + languages (decision 2):** `languages = [...]` per install URL, `behaviorHints.configurable` + `/configure` page; STT once per file, translation per language (store keyed by language, append-only migration); one prompt template per language.
2. **`openai-compatible` backend** (covers local models), then benchmark candidates on Batman.
3. **Server tuning in the file:** cache size (never 0) and the torrent profile from `infra/stremio-server/settings.json` move into `config.toml`, applied through `POST /settings`.
4. **First-run wizard** in the UI: LAN IP, HTTPS mode, provider + key, Whisper model download with progress, TV pairing, then the TV-side step with its revert ([tv-setup.md](../runbooks/tv-setup.md)).
5. **Admin password** for the UI once hosts are shared beyond one household.
