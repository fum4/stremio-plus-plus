# `spikes/` — throwaway experiment code

Code written during spikes to answer a question, kept for the record (owner's call, 2026-10-21). **Not production code**: no tests, not linted/type-checked (excluded in `pyproject.toml`), never imported by `src/`. Each feature that graduates gets a proper implementation under `src/` and the spike is deleted in the same PR.

## `phase-0/` (2026-10-21, results in `docs/research/phase-0-results.md`)
| File | Answered |
|---|---|
| `live_ro.py` | End-to-end live Romanian subtitles: addon → engine match → continuous centre-channel audio → Whisper turbo (mlx) → Claude Haiku via the `claude` CLI (subscription, serial + hourly cap) → SRT served over LAN http. Run: `HF_HOME=… HF_HUB_OFFLINE=1 python live_ro.py <lan-ip> 11471` + an HTTPS front (temporary Cloudflare quick tunnel) |
| `test_addon.py` | Does Theater call a plain-http / an HTTPS addon? Does it re-fetch on re-select? |
| `download_watch.py` | Per-file download progress, TV connections, disk, every 15 s |
| `tvctl.py` | Samsung TV remote over `wss://<tv>:8002` (pair, keys, text); tolerates `ms.remote.touch*` events |
| `bench/` | Tears of Steel: ffsubsync offset/drift, parakeet vs Whisper, WER/coverage scoring → `docs/research/benchmarks/tears-of-steel.md` |
| `stt/` | MobLand S01E03 real-content STT + sync scoring → `docs/research/benchmarks/mobland-s01e03.md` |
