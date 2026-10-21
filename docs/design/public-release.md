# Proposal: make stremio++ usable by anyone (self-hosted, configurable)

Status: **proposal** (2026-10-21), for the owner's decision. Configuration is decided and its phase 1 built: [config-ui.md](config-ui.md) (TOML file + Svelte UI, translator adapter).

## Goal
Anyone with a Stremio TV/client and a spare computer can run their own companion: their machine, their
subtitle languages, their AI provider (subscription, API key, or fully local), their TV. Install in
minutes, configure in one file or a wizard, no knowledge of this repo's internals.

**Non-goal: a hosted public service.** We would be streaming torrents and proxying AI for strangers:
legal exposure (torrents), unbounded cost (AI), and the LAN-only security model breaks. Every user
self-hosts; the project ships software, not a service.

## What's personal today (inventory)
| Area | Hard-wired to the owner | Make it |
|---|---|---|
| Subtitle language | `LABEL="Romanian (AI)"`, `LANG="ron"`, Romanian-specific prompt (diacritics) | `languages = ["ro", "de", …]`: one track per language, label from the language name, prompt template per language |
| Source language | Whisper forced to `en` | auto-detect, or `source_language` |
| Translator | `claude -p` on the owner's subscription | provider: `claude-cli` · `anthropic` (API key) · `openai-compatible` (OpenAI, OpenRouter, OpenCode, Groq, **Ollama local**) · `none` (source-language subs only) |
| Speech-to-text | mlx-whisper (Apple Silicon only) | provider: `mlx-whisper` (macOS arm64) · `faster-whisper` / `whisper.cpp` (Linux, Intel, NVIDIA) · optional cloud (OpenAI/Groq Whisper) |
| Host OS | launchd plists, Homebrew | service backend: `launchd` (macOS) · `systemd` (Linux) · **Docker Compose** (any box, N100) |
| HTTPS for the addon | `stremio.nomadware.io`, Cloudflare token, lego | modes: `own-domain` (any of lego's ~150 DNS providers) · `tailscale-funnel` / `cloudflare-tunnel` (no domain needed; public, token-protected) · `lan-http` (clients that allow plain http, e.g. desktop) |
| TV control | `TV_OS` adapters exist (`samsung` · `webos` · `androidtv` · `firetv`, [research](../research/tv-remote-protocols.md)); only Samsung verified on hardware; `TV_HOST`/`TV_OS` committed | per-user `TV_OS`/`TV_HOST` · add `none` · hardware-verify the other three |
| Secrets | devbox `repo-secrets` + age key | secrets backend: OS keychain (macOS Keychain / libsecret) by default, env file (mode 600) for Docker, `repo-secrets` kept for the owner's own deployment |
| Identity strings | `io.github.fum4.*` labels, Batman, `fum4/devbox` engine | neutral names; owner-specific bits move to the owner's deployment profile |
| Config location | `infra/env/companion.env` + `.env.local` in the repo | one user config file outside the repo: `~/.config/stremio-plus-plus/config.toml` (XDG; `%APPDATA%` later) |

Already generic: download manager (prefetch, cleanup), playhead-first generation, subtitle store, server.js
pinning (downloaded from Stremio at install time, never redistributed), tracker, doctor, HTTPS guard + token.

## Shape of the product
```
stremio++ (public repo, MIT/Apache-2.0)
  ├─ core           tracker, downloads, subtitle pipeline, addon, store   (unchanged, generic)
  ├─ providers/     translate/{claude_cli, anthropic, openai_compat, none}
  │                 stt/{mlx_whisper, faster_whisper, whisper_cpp, openai}
  │                 tls/{own_domain, tailscale_funnel, cloudflare_tunnel, lan_http}
  │                 tv/{samsung_tizen, …}   secrets/{keychain, envfile, repo_secrets}
  ├─ host/          launchd/, systemd/, docker/ (compose: server.js + companion)
  └─ cli            `stremio-plus-plus setup | doctor | status | addon-url | promote | demote`
config.toml  ←  written by `setup` (a wizard: asks only what it can't detect)
```
Each provider = one small class behind a `Protocol` (already the pattern: `Transcriber`, `Translator`);
config picks it by name. Capability checks in `doctor` (e.g. "mlx-whisper needs Apple Silicon").

## Install paths (in order of effort)
1. **Clone + `mise run setup`** (today's flow, generalised): works now for technical users.
2. **Homebrew tap** `brew install fum4/tap/stremio-plus-plus` → `stremio-plus-plus setup`: the wizard
   detects the LAN IP, finds TVs (SSDP), offers providers, writes config, installs launchd agents.
3. **Docker Compose** for always-on Linux boxes (N100, NAS): server.js + companion + whisper.cpp;
   `docker compose up` with a `.env`.
4. Later: a small **status page** served by the companion (LAN only): what's downloading, subtitle
   progress per title, provider usage, buttons for "regenerate", "pair TV". A menu-bar app only if wanted.

## Example config
```toml
[host]
lan_ip = "auto"                 # or "192.168.1.132"

[subtitles]
languages = ["ro"]              # one "<Language> (AI)" track each
source_language = "auto"
stt = "mlx-whisper"             # mlx-whisper | faster-whisper | whisper-cpp | openai
translator = "claude-cli"       # claude-cli | anthropic | openai-compatible | none

[subtitles.openai_compatible]   # e.g. Ollama: base_url = "http://localhost:11434/v1", model = "qwen3:14b"
base_url = ""
model = ""

[addon]
https = "own-domain"            # own-domain | tailscale-funnel | cloudflare-tunnel | lan-http
domain = "stremio.example.com"
dns_provider = "cloudflare"     # any lego provider; its token goes to the secrets backend

[tv]
kind = "samsung-tizen"          # samsung-tizen | none
host = "auto"                   # SSDP discovery
```
Secrets (API keys, DNS token, addon token, TV token) never go in this file: `setup` stores them in the
keychain (or the env file on Docker).

## Things to decide (owner)
| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | Public repo now, or after the refactor? | now / after | **After** phase A: today's repo has the owner's IP, domain and paths in committed config; secrets are encrypted but the history shows them as files. Fresh public repo or history-preserving after scrubbing config. |
| 2 | License | MIT · Apache-2.0 · GPL | **Apache-2.0** (patent grant; no GPL entanglement: we don't ship stremio-web or server.js) |
| 3 | Name | ~~keep · rename~~ | **Decided 2026-10-21: stremio++** (repo and package slug `stremio-plus-plus`, GitHub allows no `+`). Still check Stremio's trademark guidance before publishing |
| 4 | Owner's own setup | stays in this repo · separate private deployment repo | **Separate**: public `stremio-plus-plus` (generic) + private `stremio-plus-plus-deploy` (or a profile in `Nomadware.io`) with the owner's config.toml, encrypted secrets, DNS record |
| 5 | First providers | — | translator: `claude-cli`, `anthropic`, `openai-compatible` (covers OpenAI/OpenRouter/OpenCode/Ollama); STT: `mlx-whisper` + `faster-whisper`; HTTPS: `own-domain` + `tailscale-funnel`; TV: `samsung-tizen` |
| 6 | Default translator for new users | claude-cli · API key · local | **API key or local (Ollama)**: `claude-cli` on a consumer subscription is the user's own call (personal use only); documented, not the default |

## Phases
- **A. Config + providers (no behaviour change for the owner):** `config.toml` loader replacing env files,
  provider interfaces + current implementations behind them, `languages` list, secrets backend
  abstraction (keep repo-secrets for the owner). Owner profile moves out of the repo.
- **B. Second implementations:** `anthropic` + `openai-compatible` translators, `faster-whisper` STT,
  `tailscale-funnel` HTTPS, keychain secrets. Multi-language tracks.
- **C. Distribution:** `setup` wizard + TV discovery, Homebrew tap, Docker Compose + systemd, public
  README / docs site, issue templates, CI release workflow (needs owner approval: Actions minutes).
- **D. Polish:** LAN status page, more TV plugins, translation quality knobs (model per language, glossary).

## Risks
- **Legal/trademark:** torrent streaming is the user's responsibility; we never ship server.js (downloaded
  from Stremio at install) or stremio-web code; "Stremio" in the name needs checking.
- **Support load:** many TVs/routers behave differently (HTTPS-only clients, DNS-rebind protection,
  MagicDNS caches); the doctor must explain every failure in plain words.
- **Provider drift:** model names, CLIs and APIs change; pin and test each provider with a tiny fixture.
- **Subscription ToS:** `claude-cli` mode stays opt-in with a clear note.
