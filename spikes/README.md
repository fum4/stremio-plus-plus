# `spikes/` — throwaway experiment code

Code written during spikes to answer a question, kept for the record (owner's call, 2026-10-21). **Not production code**: no tests, not linted/type-checked (excluded in `pyproject.toml`), never imported by `src/`. Each feature that graduates gets a proper implementation under `src/` and the spike is deleted in the same PR.

## `phase-0/` (2026-10-21, results in `docs/research/phase-0-results.md`)
Graduated and deleted (in git history): `live_ro.py` → `src/stremio_companion/subtitles/`, `tvctl.py` → `src/stremio_companion/tv/`.

| File | Answered |
|---|---|
| `test_addon.py` | Does Theater call a plain-http / an HTTPS addon? Does it re-fetch on re-select? |
| `download_watch.py` | Per-file download progress, TV connections, disk, every 15 s |
| `bench/` | Tears of Steel: ffsubsync offset/drift, parakeet vs Whisper, WER/coverage scoring → `docs/research/benchmarks/tears-of-steel.md` |
| `stt/` | MobLand S01E03 real-content STT + sync scoring → `docs/research/benchmarks/mobland-s01e03.md` |
