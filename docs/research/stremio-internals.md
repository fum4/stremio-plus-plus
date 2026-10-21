# Stremio internals we depend on

Two evidence sources:
- **server.js v4.22.4** — the pinned bundle (`var/stremio-server/server.js`, `mise run server:fetch`; sha256 in `infra/env/stremio-server.env`). Lines below are `server.js:<line>` in that exact file. Verified 2026-10-21.
- **Public repos** (enginefs, stremio-web, stremio-video, stremio-core) — from the 2026-10-20 planning research; `file:line` as cited there. **Re-check against the repo before relying on one.**

Bump server.js → re-verify every `server.js:` row below in the same PR.

## Server version
- stremio-service (latest release v0.1.22, 2026-08-25) pins **v4.21.1** (`Cargo.toml [package.metadata.server]`).
- `dl.strem.io/server/<v>/desktop/server.js` has no index; probing finds **v4.22.4** as the newest (v4.22.5 / v4.23.0 / v5.0.0 return XML = missing). Bundle self-reports `version: "4.22.4"`.
- We run server.js directly under node (`launchd/server.plist.template`) instead of stremio-service: same bundle, newer version, no tray app, and the same layout works under systemd on Linux.

## Paths and env (server.js)
| What | Evidence |
|---|---|
| `APP_PATH` overrides the data dir; macOS default `~/Library/Application Support/stremio-server` | `server.js:16500` |
| Settings file `server-settings.json` in `SETTINGS_PATH` or `APP_PATH` | `server.js:12991` |
| ffmpeg/ffprobe searched in `--ffmpeg`, `FFMPEG_BIN`/`FFPROBE_BIN`, next to node, then system paths | `server.js:47750` |

We set our own `APP_PATH` (`~/Library/Application Support/stremio-companion/stremio-server`) so a Stremio desktop install never shares or trims our cache.

## Cache and download limits
| Fact | Evidence |
|---|---|
| Default `cacheSize` = 2 GiB on desktop (0 on Android); `DISABLE_CACHING` forces 0 | `server.js:13022` |
| Default `btDownloadSpeedHardLimit` = 3 670 016 B/s (3.5 MiB/s) — the "≈3.5 MB/s cap" | `server.js:13027` |
| `cacheSize == 0` (or `--noCache`) → 15 MB buffer + **45 MB in-memory circular buffer** + `swarmCap.maxBuffer .75` — the mode that stops downloading while paused | `server.js:48184` |
| Every engine creation trims the cache dir to `cacheSize` (`cache.clearCache(..., settings.cacheSize, 0)`) → a finite cache can evict a file we are still processing | `server.js:48110` |

**"Infinite" = `cacheSize: null`** — the UI's options are `[0, 2 GiB, 5 GiB, 10 GiB, null]` (stremio-web `src/routes/Settings/Streaming/useStreamingOptions.ts:9`; the server's own `/settings` `options` say the same, `∞ → null`). JSON can't hold `Infinity`, so it is stored as `null`.

**What `null` actually does** (`clearCache`, `server.js:36236-36266`): the early return is `toSize == 1/0`, which `null` fails; then `Math.min(null, …)` coerces to `0`, so **every engine creation deletes every cached file of every *inactive* engine**. Files of engines still in `enginefs.list()` are skipped (`omit`). So "∞" really means "keep only what's active, clean the rest on the next engine creation" — no re-watch cache, but no disk fill either.

**A huge finite value** (we use 4 TiB) keeps everything: `toSize = min(cacheSize, used + free − required)`, and a file is deleted only while the running total exceeds `toSize`, which never happens for files already on disk. So the server never trims and the disk can fill.

→ For us (since 2026-10-21, plan phase 2): cache = **4 TiB** ("keep until we decide"), and the companion owns deletion: the daily `cleanup` agent drops torrents unplayed for 7 days and evicts least-recently-used torrents below a 3 GiB free-space reserve, never touching live engines (`src/stremio_companion/downloads/cleanup.py`). Phase 0 used `null`, which wiped a show's files as soon as another title started — wrong for "resume tomorrow" and rewatches.

## Torrent profiles
stremio-web `useStreamingOptions.ts:30-61`: default (hard 3.5 MiB/s, 55 conns), soft, fast (hard 37.5 MiB/s, 200 conns), **ultra fast** (hard 75 MiB/s, soft 8 MiB/s, 400 conns, 25 s handshake, 6 s request timeout). We apply ultra fast + the cache size from `infra/stremio-server/settings.json` via `POST /settings` (`mise run server:configure`; re-applied on every `services:install server`). `POST /settings` merges and persists to `$APP_PATH/server-settings.json`; verified surviving a restart.

## Engine lifecycle
| Fact | Evidence |
|---|---|
| enginefs defaults STREAM_TIMEOUT 30 s / ENGINE_TIMEOUT 60 s… | `server.js:18250` |
| …overridden by the server to **STREAM_TIMEOUT 20 s, ENGINE_TIMEOUT 120 s** | `server.js:48109` |
| `engine-inactive` (120 s after the last open HTTP stream closes) → **engine destroyed** | `server.js:48119` |
| `engine-idle` → swarm paused. It fires 20 s after `stream-cached`, i.e. **only once the file is fully downloaded** — harmless (it just stops seeding) | `server.js:48115`, emitters `server.js:18564` (`stream-created`), `server.js:18575` (`stream-cached`) |

→ the **engine pin**: keep one HTTP stream open per active engine (`Range: bytes=0-`, read 1 byte, then idle) so a paused TV that closes its connection doesn't start the 120 s countdown. Whether the TV actually closes its connection on pause is a phase-0 check — if it holds the socket open, the pin is belt-and-braces.

## Prefetch (whole-file download)
| Fact | Evidence |
|---|---|
| An open-ended Range request (`bytes=N-`) on a non-circular-buffer engine calls `prewarmStream` → `files[idx].select()` (whole file) | `server.js:18398`, `server.js:18333`; enginefs `enginefs.js:263-264,514-518` |
| `stream-open` selects every piece of the file | enginefs `enginefs.js:672-721` |

So with cache > 0 the server already downloads the whole file; the only things stopping it are the engine dying (pin) and the speed cap (profile).

## Remote HTTPS (`remoteHttps`)
Setting `remoteHttps` to a LAN IP makes the server fetch a cert via `GET /get-https?ipAddress=<ip>` (`server.js:48041`, `https.newCertificate`) and serve HTTPS on **:12470** for `<ip-with-dashes>.519b6502d940.stremio.rocks`, a public DNS name resolving to that private IP (Let's Encrypt wildcard). This is how a non-localhost client (the TV app) can use a LAN server. The server **logs the client's `authKey` in plain text** on `/get-https` requests (server.log).

## Endpoints
`/{ih}/create`, `/{ih}/{idx}`, `/{ih}/{idx}/stats.json`, `/stats.json`, `/opensubHash?videoUrl=`, `/subtitles.:ext?from=&offset=`, `/subtitlesTracks`, `/tracks/:url`, `/hlsv2/probe`, `POST /settings`.

## Subtitles path (client side)
- stremio-video rewrites every addon subtitle URL to `{server}/subtitles.vtt?from=<url>` → a plain-http SRT on the LAN works and CORS is moot (planning research; **phase 0 verifies on the TV**).
- stremio-core requests subtitles **once per load** → a track that finishes mid-film appears only after a reload.
- The subtitles request carries `filename`, `videoSize`, `videoHash` (OpenSubtitles hash) — **no infoHash**. We match against the server's `/stats.json` (active engines → files → name/size), then read `localhost:11470/{ih}/{idx}`.

## The TV side
- **Confirmed 2026-10-21:** the TV's server URL is `http://127.0.0.1:11470`, server **v4.20.8** — an **on-TV server** (the published `tizen/server.js` build). That's the likely cause of today's pause stalls. Pointing the TV at Batman replaces it; Batman asleep ⇒ no torrent playback until reverted.
- **The TV app is "Stremio Theater v1.12.1" (platform tizen 5.5), not stremio-web.** No public repo under the Stremio org matches "theater" (checked 2026-10-21) → closed source. Consequences: (1) the stremio-video `subtitles.vtt?from=` rewrite and the once-per-load subtitle request were researched in stremio-web/stremio-video/stremio-core and may not hold for Theater — phase 0 must test them on the TV; (2) a `stremio-web` fork would **replace** the official app with a different one, not patch it.
- A stock stremio-web build on Tizen falls back to HTMLVideo: platform `tizen` vs `'Tizen'` in `src/common/Platform/device.ts:31-33`, and `index.html` doesn't load `$WEBAPIS/webapis/webapis.js`. Only relevant if we fork (deferred).
- stremio-web: GPL-2.0, ~5 commits/day. enginefs: public, **no LICENSE file**.
