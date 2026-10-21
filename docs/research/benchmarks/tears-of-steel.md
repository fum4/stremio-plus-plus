# stremio++ phase-0 benchmarks

Run date: 2026-10-21 (local, ~01:30-01:50). Machine: "Batman".
Scratch: `/tmp/stremio-plus-plus-bench/` (repo untouched).

## Environment

| item | value |
|---|---|
| Hardware | Apple M4 Pro, 48 GiB (hw.memsize 51539607552) |
| OS | macOS 15.3.1 (24D70) |
| ffmpeg / ffprobe | 9.0.2 (/opt/homebrew/bin) |
| uv / uvx | 0.13.4 (7456b60bc 2026-10-20), binary at `~/.local/share/mise/installs/uv/0.13.4/uv-aarch64-apple-darwin/` (the mise shim errored with "No version is set for shim: uv" outside the repo, so the binary was called directly) |
| Python for all tools | CPython 3.12.9 (Homebrew), picked by `uvx --python 3.12`. 3.12 worked for every tool, so 3.13 was never tried |
| ffsubsync | 0.5.1 (latest on PyPI). Deps: numpy 2.5.4, webrtcvad-wheels 2.0.14.post1, auditok 0.1.5, ffmpeg-python 0.2.0, srt 3.5.3, pysubs2 1.9.0 |
| alass | not run (see 2c) |
| parakeet-mlx | 0.5.3 (latest PyPI), mlx 0.32.4, mlx-metal 0.32.4, numpy 2.5.4, librosa 1.0.0, huggingface-hub 2.2.0 |
| parakeet model | mlx-community/parakeet-tdt-0.6b-v3 @ ed2b7e8c (model.safetensors 2,508,288,736 B), bf16 (default) |
| mlx-whisper | 0.4.3 (latest PyPI), mlx 0.32.4, torch 2.14.1, tiktoken 0.14.0, numba 0.68.0, huggingface-hub 2.2.0 |
| whisper model | mlx-community/whisper-large-v3-turbo @ a4aaeec0 (weights.safetensors 1,613,977,612 B), fp16 |
| jiwer | 4.0.0 (used to cross-check WER; a separate Levenshtein script gives the same numbers) |

Isolation: every uv and HF download went to the scratch dir (`UV_CACHE_DIR=/tmp/stremio-plus-plus-bench/uvcache`, `HF_HOME=/tmp/stremio-plus-plus-bench/hf`). This made cleanup exact: `~/.cache/uv` stayed at 79M, and `~/.cache/huggingface` was never created.

## Test material

- Source: https://download.blender.org/demo/movies/ToS/ (the primary mirror worked).
- Video: `tears_of_steel_720p.mov`, 372,178,639 B (smallest video file in the directory; last-modified 2012-09-26, etag `"50631085-162efecf"`). Duration 734.17 s.
  - Stream 0: h264 video. Stream 1: **mp3, 44.1 kHz stereo, 192 kb/s, language=eng** (the only audio track).
- Subtitles: `subtitles/TOS-en.srt`, 4,764 B, sha256 `ce9578f6...c6e6fe`. CRLF line endings, 76 cues (the cue number "76" appears twice), cues run from 00:00:23.000 to 00:09:27.000.
  - Check that it matches the film: reference cue 1 "You're a jerk, Thom." is at 23.000 s. Parakeet heard "You're a jerk, Tom." at 22.88 s and Whisper at 22.90 s. ffsubsync run on the *unmodified* reference SRT found an offset of only +0.060 s at scale 1.000. **It matches.**
  - Quirks: the SRT does not subtitle the pre-roll radio chatter at 4-10 s ("We have main engine start. Four, three, two, one."). Cue 9 also contains the on-screen caption `"Fourty years later"`, which was removed from the WER reference. Some cues are stylized ("Whoaaa!", "RAAAAAAAAH!", "Could'a").

## 1. Audio prep

```
ffprobe -v error -show_entries format=duration:stream=index,codec_type,codec_name,sample_rate,channels,channel_layout,bit_rate:stream_tags=language,handler_name -of compact tears_of_steel_720p.mov

# 10-minute clip used for STT (film is 12:14 > 12 min, so the first 600 s were used; all reference dialogue ends at 9:27)
ffmpeg -hide_banner -loglevel error -y -i tears_of_steel_720p.mov -map 0:a:0 -t 600 -vn -ac 1 -ar 16000 -c:a pcm_s16le tos_10min_16k.wav

# full-length WAV (used as an alternative ffsubsync reference)
ffmpeg -hide_banner -loglevel error -y -i tears_of_steel_720p.mov -map 0:a:0 -vn -ac 1 -ar 16000 -c:a pcm_s16le tos_full_16k.wav
```

| output | duration | size | wall | peak RSS |
|---|---|---|---|---|
| tos_10min_16k.wav | 600.0 s | 19,200,078 B | 0.42 s | 16 MiB |
| tos_full_16k.wav | 734.2 s | 23,491,056 B | 0.51 s | 16 MiB |

## 2. Subtitle sync

Broken inputs were generated from the reference by `scripts/break.py`:
- (a) `broken_a_offset3.7.srt`: every timestamp +3.7 s.
- (b) `broken_b_offset2_drift.srt`: `t' = t * 25/23.976 + 2.0`. Error before sync: +2.98 s at the first cue, +26.17 s at the last, median |err| 15.65 s, p90 23.53 s.

Residual = |synced cue start - reference cue start| over all 76 cues (`scripts/residual.py`).

### 2a/2b. ffsubsync 0.5.1

Commands (`uvx --python 3.12 ffsubsync ...`, every run timed with `/usr/bin/time -l`):
```
ffsubsync tears_of_steel_720p.mov -i broken_a_offset3.7.srt     -o ffsubsync_a_video.srt     --skip-sync-on-low-quality
ffsubsync tears_of_steel_720p.mov -i broken_b_offset2_drift.srt -o ffsubsync_b_video.srt     --skip-sync-on-low-quality
ffsubsync tears_of_steel_720p.mov -i broken_b_offset2_drift.srt -o ffsubsync_b_video_gss.srt --skip-sync-on-low-quality --gss
ffsubsync tos_full_16k.wav        -i broken_a_offset3.7.srt     -o ffsubsync_a_wav.srt       --skip-sync-on-low-quality
ffsubsync tos_full_16k.wav        -i broken_b_offset2_drift.srt -o ffsubsync_b_wav.srt       --skip-sync-on-low-quality
ffsubsync tears_of_steel_720p.mov -i TOS-en.srt (unmodified)    -o ffsubsync_control_ref.srt --skip-sync-on-low-quality
```
Relevant flags in this version (from `--help`): `--skip-sync-on-low-quality`, `--min-score` (default 0.0, rejects only negative scores), `--quality-max-offset-seconds` (default 30), `--max-framerate-deviation` (default 0.10), `--gss` (golden-section search for the framerate ratio), `--no-fix-framerate`, `--skip-infer-framerate-ratio`, `--vad` (default `subs_then_webrtc`; the .mov has no subtitle stream, so webrtc was used). Framerate correction is on by default.

| case | reference | wall (incl. uvx startup) | peak RSS | score | offset reported | scale | residual median | residual p90 | residual max |
|---|---|---|---|---|---|---|---|---|---|
| (a) +3.7 s | .mov | 2.16 s | 144 MiB | 10212 | -3.640 s | 1.000 | 0.060 s | 0.060 s | 0.060 s |
| (b) +2 s + 25/23.976 | .mov | 1.28 s | 95 MiB | 10211 | -1.860 s | 0.959 | 0.058 s | 0.058 s | 0.058 s |
| (b) with `--gss` | .mov | 1.48 s | 193 MiB | 10211 | -1.860 s | 0.959 | 0.058 s | 0.058 s | 0.058 s |
| (a) +3.7 s | 16 kHz WAV | 0.82 s | 100 MiB | 10515 | -3.650 s | 1.000 | 0.050 s | 0.050 s | 0.050 s |
| (b) +2 s + 25/23.976 | 16 kHz WAV | 0.84 s | 95 MiB | 10514 | -1.870 s | 0.959 | 0.048 s | 0.048 s | 0.048 s |
| control (unmodified ref) | .mov | n/m | n/m | 10206 | +0.060 s | 1.000 | 0.060 s* | | |

\* For the control, the residual is just the offset ffsubsync applied to an already-correct file.

Notes:
- No run was skipped by `--skip-sync-on-low-quality`. All scores are positive (about 10.2k-10.5k). The score is not normalized, so it can't be compared across inputs.
- The ~50-60 ms residual is constant. It equals the offset ffsubsync applies to the unmodified reference (+0.060 s), so it reflects webrtc-VAD vs reference-SRT timing, not a failure to undo the distortion. After subtracting that bias, offset and drift were recovered to within about 10 ms.
- Case (b): 0.959 is about 23.976/25 = 0.95904, and offset -1.86 s is about -2.0 * 0.959 (the offset is applied after scaling). `--gss` gave the same answer as the default framerate-ratio search here.
- RSS is from `/usr/bin/time -l` around `uvx`. These runs are short and uvx/ffmpeg child accounting may be partial, so treat RSS as approximate.

### 2c. alass on case (b): not run

- The latest kaegi/alass GitHub release is v2.0.0 (2019-10-10). Its only assets are `alass-linux64` and `alass-windows64.zip`, with **no macOS/arm64 binary**.
- `cargo` is not installed (`cargo not found`, no `~/.cargo/bin`).
- Skipped as instructed. For reference, `brew info alass` shows a Homebrew bottle `alass: stable 2.0.0 (bottled)`, not installed. Nothing was installed.

## 3. Speech-to-text (10-min clip, 600 s)

### Commands
```
# parakeet-mlx (default: sentence segmentation, greedy, bf16, 120 s chunks / 15 s overlap)
uvx --python 3.12 --from parakeet-mlx parakeet-mlx tos_10min_16k.wav --output-dir out/parakeet_run{1,2} --output-format all
# subtitle-style segmentation variant
uvx --python 3.12 --from parakeet-mlx parakeet-mlx tos_10min_16k.wav --output-dir out/parakeet_subtitle_style --output-format srt --max-words 12 --max-duration 6 --silence-gap 0.6

# mlx-whisper, CLI defaults (temperature 0, condition_on_previous_text=True) + word timestamps
uvx --python 3.12 --from mlx-whisper mlx_whisper tos_10min_16k.wav --model mlx-community/whisper-large-v3-turbo --language en --task transcribe -f all --word-timestamps True --verbose False -o out/whisper_run{1,2}
# mlx-whisper, anti-hallucination variant
uvx ... mlx_whisper ... (same as above) --condition-on-previous-text False --hallucination-silence-threshold 2 -o out/whisper_nocond
```
Library-level timing scripts (to separate load from inference): `scripts/time_parakeet.py`, `scripts/time_whisper.py`, `scripts/time_whisper2.py`.

### Speed

| system | run | wall | RTF (audio/wall) | peak RSS |
|---|---|---|---|---|
| parakeet-tdt-0.6b-v3 | CLI run 1 (incl. 2.5 GB model download) | 230.73 s | - | 3,200 MiB |
| | CLI run 2 (cached: uvx + import + load + infer) | 6.92 s | 87x | 769 MiB |
| | subtitle-style CLI run (cached) | 6.71 s | 89x | 770 MiB |
| | in-process: import 0.14 s, load 0.48 s, transcribe 6.02 s / 5.97 s (2 calls) | 6.0 s infer | **~100x** | 781 MiB |
| whisper-large-v3-turbo | CLI run 1, defaults (incl. 1.6 GB model download) | 211.56 s | - | 3,251 MiB |
| | CLI run 2, defaults (cached) | 25.42 s | 24x | 1,981 MiB |
| | CLI no-cond + halluc-thr 2 (cached) | 20.79 s; rerun 20.64 s (identical SRT) | 29x | 1,912 MiB |
| | in-process API, no-cond + thr 2 (2 calls, model cached in-process) | 36.93 s / 36.71 s | 16x | 1,975 MiB |
| | in-process API, defaults (1 call, after a separate load_model) | 69.46 s | 8.6x | 3,606 MiB (2 model copies) |
| | in-process: import 0.56 s, standalone `load_model` 0.29 s (from disk cache) | | | |

Notes:
- Model load from local cache is under 0.5 s for both models. Cached-run wall time is almost all inference.
- **The mlx-whisper CLI and Python API defaults differ.** The CLI's `--temperature` defaults to a single `0` (cli.py:87), so there is no temperature fallback. `transcribe()` defaults to `temperature=(0.0, 0.2, ..., 1.0)` with fallback (transcribe.py:67). That is why the API runs were slower (37 s vs 21 s with the same other options) and produced different segments (78 vs 95). The STT quality numbers below come from the **CLI** outputs.
- Download portions of run 1 took about 3.5-4 min per model on this connection. RSS figures don't necessarily include all MLX unified-memory GPU allocations.

### Accuracy and timing quality

Reference: the 76 SRT cues, 332 words after normalization (the "Fourty years later" caption removed). Normalization: lowercase, delete apostrophes, replace every other non-alphanumeric run with a space, then split on whitespace. Script: `scripts/eval_stt.py`.
- **WER all-text**: whole hypothesis vs whole reference.
- **WER in-cue-window**: only hypothesis words whose midpoint falls within ±1 s of some reference cue, which drops the unsubtitled pre-roll chatter and hallucinations in gaps.
- **Coverage (segment)**: % of reference cues overlapped by any SRT segment.
- **Coverage (word)**: % of reference cues containing at least one hypothesis word midpoint.
- **Cue-start error**: earliest hypothesis word starting in [cue start - 1 s, cue end], minus cue start, over cues that have such a word.

| system | hyp words | WER all-text (own / jiwer) | WER in-cue-window ±1 s | cues covered (SRT segment) | cues covered (word ts) | cue-start err median / p90 |
|---|---|---|---|---|---|---|
| parakeet-tdt-0.6b-v3 (default) | 301 | 27.1% / 27.1% | 27.1% | 80.3% | 75.0% | 0.40 s / 0.96 s (n=62) |
| parakeet, subtitle-style segmentation | 301 | 27.1% / 27.1% | 27.1% | 80.3% | 75.0% | same (same words; 98 cues instead of 65) |
| whisper-large-v3-turbo (CLI defaults) | 471 | **112.0%** / 112.0% | 74.4% | 86.8% | 81.6% | 0.58 s / 0.98 s (n=65) |
| whisper-large-v3-turbo (no-cond + halluc-thr 2) | 370 | 26.2% / 26.2% | **17.5%** | **97.4%** | **96.1%** | 0.36 s / 0.90 s (n=75) |

Observations (all visible in the output files):
- **Whisper with CLI defaults hallucinated badly.** From about 1:20 to 6:20 the output is mostly the repeated segment "I'm not." (dozens of times), and the action climax (about 7:10-9:10) is mostly repeated "No!". The real dialogue in those spans is lost, hence 112% WER. Turning off `condition_on_previous_text` and setting `hallucination_silence_threshold=2` removed the loops. The remaining issues are "Ah!"/"Oh, no!" fillers during action scenes, an extra "You're a jerk, Tom." at 29.9 s, and a trailing "I'm out." The output is deterministic: the rerun gave a byte-identical SRT.
- **Parakeet produced no hallucinated loops, but dropped speech.** Its output has gaps over 15 s at 78-117 s, 159-191 s, 249-293 s, 392-419 s and 434-506 s. Of the 15 reference cues with no Parakeet word inside them, most are short shouts or interjections ("Thom.", "Vivacissimo!", "Whoaaa!" x2, "Nooooo!", "RAAAAAAAAH!", "I'm-", "Come on!", "You know.") plus "I'm sorry.", "Good ad-lib.", "Memory overwrite, 90%." and "Speed it up, Thom!". It also merged or garbled lines in the climax ("Now my ball. Wild set. Out of time, round of time.").
- For Parakeet, windowing did not change WER. The hypothesis is shorter than the reference (301 vs 332 words), so the 9 pre-roll words were aligned as substitutions for words that would otherwise count as deletions, at no extra cost.
- Both models write "Tom" for "Thom" and render stylized cues literally or differently ("Could have gone worse" vs "Coulda" vs "Could'a"). Some WER comes from the reference's style, not from recognition errors.
- Cue-start error is about 0.4 s median for both models. Part of this comes from the reference cues being on round 0.5/1.0 s boundaries, so it is a coarse proxy.

### 5 aligned examples (hypothesis words with midpoint in [cue start - 0.1 s, cue end + 0.1 s]; spread evenly across the cues where some system has 2 or more word edits)

Window slicing cuts words at cue boundaries, so a trailing or leading fragment (e.g. "Look,", "We're", "only") is partly a windowing artifact.

| cue | reference | parakeet (default) | whisper (CLI defaults) | whisper (no-cond + thr 2) |
|---|---|---|---|---|
| 23.0-24.5 s | You're a jerk, Thom. | You're a jerk, Tom. Look, | You're a jerk, Tom. Look, | You're a jerk, Tom. Look, |
| 203.5-206.5 s | We're on in one! All systems go! Yeah you, go! | We're only one. All systems go. | not. | only one. All systems go! |
| 321.0-323.0 s | You have your robotics... | You have your | I'm not. I'm | You have your robotics. |
| 387.0-389.0 s | You forgot me on earth. | You forgot me on earth. | I'm not. You got me on earth. | You forgot me on Earth. |
| 566.0-567.0 s | Could'a gone worse. | Could have gone | (nothing) | Coulda gone worse. |

## Failures and deviations

- `uv`/`uvx` mise shims failed outside the repo: `mise ERROR No version is set for shim: uv ... mise use -g uv@0.13.4`. I used the absolute binary path instead and did not change any mise config.
- alass was not run: no macOS binary on the GitHub release and no cargo (details in 2c).
- With huggingface-hub 2.2.0, HF downloads go to a shared `hub/blobs/` directory, not inside `models--*/blobs`. Deleting `models--mlx-community--parakeet-tdt-0.6b-v3` alone freed nothing, and free space fell to 3.8 GiB before the mistake was caught. Deleting `hub/blobs` fixed it. Free space never went below 3 GiB.
- Disk free at the start was 7.5 GiB, not the expected ~9.6 GiB.

## Files kept in /tmp/stremio-plus-plus-bench/

- `out/reference_TOS-en.srt`, `out/broken_*.srt`, `out/ffsubsync_*.srt`
- `out/parakeet_run{1,2}/` (srt/vtt/txt/json; run1 and run2 SRTs are identical), `out/parakeet_subtitle_style/`
- `out/whisper_run{1,2}/` (identical SRTs), `out/whisper_nocond/`, `out/whisper_nocond_rerun/`
- `logs/` (raw stdout/stderr of every run, plus `eval_stt.txt`), `scripts/` (srtlib, break, residual, eval_stt, timing scripts)

## Cleanup

| deleted | size |
|---|---|
| `dl/tears_of_steel_720p.mov` | 372 MB (355 MiB) |
| `dl/tos_10min_16k.wav`, `dl/tos_full_16k.wav` | 19.2 MB + 23.5 MB |
| HF cache (`/tmp/.../hf`): parakeet-tdt-0.6b-v3 weights (2.3 GiB) and whisper-large-v3-turbo weights (1.5 GiB) | ~3.8 GiB |
| uv cache created for this run (`/tmp/.../uvcache`, via `uv cache clean`: "Removed 53944 files (2.6GiB)") | 2.6 GiB |

Total freed: about 6.8 GiB. Disk free (`df -h ~`): **7.5 GiB at the start, 3.8 GiB at the lowest point, 7.3 GiB at the end.** The remaining ~0.2 GiB difference is not in the scratch dir (now 860 KiB), `~/.cache/uv` (unchanged at 79M) or `~/.cache/huggingface` (doesn't exist). `tmutil listlocalsnapshots /` lists no snapshots. The cause wasn't determined; it is probably unrelated system activity.
