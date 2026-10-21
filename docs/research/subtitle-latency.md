# Subtitle latency: how big each generation window should be

Measured 2026-10-21 on the host (MacBook Pro M4, mlx-whisper large-v3-turbo with the repo's decoding options, Claude Haiku via the `claude` CLI), on Carrie S01E01 (stereo AC3, 7 lines in the first 10 s of dialogue), audio already in the torrent cache.

## Cost of one window

| Window | Lines | Whisper (2 runs) | Claude (2 runs) |
|---|---|---|---|
| 10 s | 7 | 4.8 / 4.8 s | 4.7 / 4.1 s |
| 30 s | 16 | 5.1 / 5.0 s | 13.9 / 8.1 s |
| 60 s | 28 | 15.5 / 11.0 s | 6.2 / 7.4 s |
| 120 s | 40 | 25.4 / 38.9 s | 11.4 / 10.8 s |
| 1 line | 1 | – | 3.7, 2.3, 4.0, 4.7 s |

Reading cached audio is negligible (160 s in 0.9 s). Uncached, the audio has to be downloaded first: L seconds of video at bitrate b over a torrent rate R add L·b/R seconds (4K ≈ 2 MB/s of video; on a 0.2 MB/s torrent that is 10 s per second of audio, and no window size helps — the stream itself stalls).

Model: **T(L) ≈ a + r·L** with a fixed cost **a ≈ 8 s** (Whisper start + one Claude round trip) and **r ≈ 0.3 s per second of audio** (Whisper ~0.2–0.3, Claude ~0.05). `STEP_FIXED_S` / `STEP_PER_S` in `subtitles/constants.py` use these, conservatively: Whisper and Claude are pipelined (the next window is transcribed while the previous one is translated), so the real per-step cost is closer to max(Whisper, Claude).

## Sizing

The player fetches the SRT once per track selection (see [plan.md](../plan.md) risks), so two things matter: what is ready when that fetch is answered, and staying ahead of the viewer afterwards.

- **Staying ahead.** A window has to finish before the viewer reaches it. With `lead` seconds covered ahead of the playhead, the next window can be at most **L ≤ (lead − a) / r**. The lead after it grows by (1 − r)·L − a, so lengths only grow if the first window is longer than **a / (1 − r) ≈ 11 s**. A 10 s first step looks attractive but never builds a lead: each next window would be shorter.
- **First window: 15 s.** Ready ~10 s after the request (measured end to end, cold: 10.0–11.0 s), under the 20 s the SRT request now waits (`FIRST_ANSWER_WAIT_S`), and long enough to grow.
- **Aim it ahead.** It starts where the viewer will be when it's done (playhead + a + r·15 ≈ 12.5 s), not at the playhead: lines for the seconds spent generating would arrive already in the past. Those seconds are back-filled once everything ahead is covered.
- **Growth.** With the viewer watching: 15 → 23 → 51 → 120 s, then 120 s windows (`MAX_WINDOW_S`, long enough for Whisper's context and few Claude calls: ~30/hour while watching, well under the hourly cap). Paused at a fresh selection: 15 → 65 → 120 s.

End to end on real audio and models (paused at 0 s): 12.5–27.5 s ready at 10.0 s, 27.5–92.5 s at 29.8 s, 92.5–212.5 s at 70.4 s.

## Not done
- Shorter Whisper windows lose context at the edges; the 2 s overlap (`OVERLAP_S`) and keeping only cues that start inside the window handle it, but the first 15 s window is the least accurate one. Not measured (WER per window size).
- Re-fetching the SRT after the first answer needs a re-selection on the TV; automating it is in [backlog](../work/backlog.md).
