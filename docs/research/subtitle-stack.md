# Subtitle stack — choices and why

Status: sync + STT **benchmarked 2026-10-21** (numbers in [phase-0-results.md](phase-0-results.md)); translation pending. Originally proposed to be benchmarked on Batman (M4 Pro, 48 GB) in phase 0 ([phase-0-results.md](phase-0-results.md)). Versions are re-checked at pin time, never from memory.

## Sync
| Choice | Why | Alternatives |
|---|---|---|
| **ffsubsync** (`--skip-sync-on-low-quality`, `--min-score`) | audio-VAD alignment, handles constant offset + framerate drift; quality score lets us refuse a bad sync instead of making it worse | — |
| **alass** fallback | handles splits (cuts / ad breaks) ffsubsync can't; fast (Rust) | sushi (unmaintained) |

Estimate ~30 s/movie once audio is local. Audio: ffprobe picks `language=eng` > default > first, skipping commentary; 5.1 → centre channel (`pan=mono|c0=FC`); honour a non-zero container `start_time`.

## Speech-to-text
| Choice | Why |
|---|---|
| **Whisper large-v3-turbo** via mlx-whisper, `condition_on_previous_text=False`, `hallucination_silence_threshold=2`, every decoding option explicit | **changed after the phase-0 bench**: 17.5 % WER, 96–97 % of cues covered, 29× realtime (~4 min per 2 h film); multilingual. Defaults hallucinate loops — never run it on defaults |
| parakeet-mlx (`parakeet-tdt-0.6b-v3`) — not primary | ~100× realtime and no hallucinations, but missed 20–25 % of cues (short shouts, action-scene lines). Speed isn't the bottleneck (the download is), coverage is → Whisper wins. Re-test if a newer parakeet improves recall |
| **Silero VAD** gate | skip silence/music, cut chunks at silences, cuts hallucinations on non-speech |

Chunks overlap 1–2 s, cut at VAD silences, stay 2–5 min ahead of the playhead.

## Translation EN → RO
| Choice | Why |
|---|---|
| **Claude Haiku 5.5** (`claude-haiku-5-5`), 40–80 numbered cues per batch, prior batch as context | cheap (est. $0.02–0.05/movie), fast; batch context keeps pronouns/register consistent |
| Model sees **cue ids + text only** | timings re-applied by code — the model can't shift or merge timings; re-wrap to ≤ 2 lines × ~42 chars |
| Sonnet 5.5 as the quality alternative | owner (native speaker) judges Haiku vs Sonnet on ~200 cues in phase 0 |

## Prior art reviewed (reuse before rebuild)
- **subgen** — Whisper-based, no MLX, translates only *to* English. Not reusable.
- **Bazarr** — needs a file library; we have live torrents. Not reusable.
- **xtremexq/StremioSubMaker** — Stremio addon with AI translation (no sync, no STT). Study for the addon wiring and id-preserving translation.

## Bottleneck
The torrent download rate, not compute: we can only process what's downloaded. Pitfalls: MKV index at the end forces tail pieces first; reads past the downloaded range stall (timeouts + ffmpeg `-reconnect`).
