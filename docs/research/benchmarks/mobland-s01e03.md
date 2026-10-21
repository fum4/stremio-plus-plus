# Phase-0 STT test: MobLand S01E03 "Plan B", first 10 min

Machine: "Batman", MacBook Pro M4 Pro, 48 GB, macOS 15.3 (Darwin 24.3.0). Date: 2026-10-21.
Source: live torrent streamed by the local Stremio server
`http://127.0.0.1:11470/6778f903610f20668ecdacea68162e974f0201a8/2`
(the release is "MobLand (2025) S01 2160p AMZN WEB-DL x265 HEVC 10bit DDP 5.1 Vyndros"). The streaming server was not touched.

## Tool versions actually used
| tool | version |
|---|---|
| ffmpeg / ffprobe | 9.0.2 (/opt/homebrew/bin) |
| uv | 0.13.4 |
| Python (uv tool envs) | 3.12 (/opt/homebrew/opt/python@3.12) |
| ffsubsync | 0.5.1 |
| mlx-whisper | 0.4.3 (mlx 0.32.4, huggingface-hub 2.2.0, numpy 2.5.4, torch 2.14.1, tiktoken 0.14.0) |
| model | mlx-community/whisper-large-v3-turbo @ a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb (1.5 GB on disk) |
| scoring | /tmp/stremio-plus-plus-stt/scripts/score.py (stdlib only, system python3 -I) |

Environment: `UV_CACHE_DIR=/tmp/stremio-plus-plus-stt/uvcache HF_HOME=/tmp/stremio-plus-plus-stt/hf`.

## 1. Probe and audio extraction
ffprobe result: matroska. Container start_time **0.000**, duration 2833.70 s.
| idx | type | codec | layout | lang | default | title |
|---|---|---|---|---|---|---|
| 0 | video | hevc | | | yes | |
| 1 | audio | eac3 | 5.1(side), 6 ch | eng | **no** | |
| 2 | subtitle | subrip | | eng | no | United States |
| 3 | subtitle | subrip | | eng | no | United States (SDH) |

Audio choice: stream 1, picked by the language=eng rule. It is the only audio track, it is not marked default, and it is not commentary. start_time is 0 and all streams start at 0, so no offset compensation was needed (ffmpeg would have applied a non-zero start_time anyway, because we read from the container start).

```
ffmpeg -nostdin -v error -rw_timeout 30000000 -t 600 -i "$URL" \
  -map 0:a:0 -af "pan=mono|c0=FC" -ar 16000 -c:a pcm_s16le centre.wav \
  -map 0:a:0 -ac 1               -ar 16000 -c:a pcm_s16le downmix.wav
```
This took **2 s** for both WAVs (600.00 s each, 19.2 MB each). The first 10 min were fully downloaded.

**Failure to note:** my first attempt added the two embedded subtitle tracks as extra outputs to the same ffmpeg command (input `-t 600`). The audio reached about 598 s, then ffmpeg **hung for more than 5 min with no progress, and `-rw_timeout` never fired**. I had to kill it. Running audio-only (above) and subtitles-only separately (output `-t 600`: `-map 0:2 -c:s srt -t 600 …`) each finished in 2 s. My best guess is that the sparse subtitle streams kept the demuxer reading past 600 s into the part of the file that isn't downloaded, where the server stalls the connection without closing it. Lessons: don't mix subtitle outputs with an input-side `-t` on a partial torrent, and add a wall-clock watchdog, because `rw_timeout` alone did not catch the stall.

## 2. Reference subtitles and the "sync on real content" benchmark
OpenSubtitles v3 addon: `…/tt31510819:1:3/videoHash=1e894d1e08d0e2b7&videoSize=3560556831.json` returned 69 subs. The no-hash query returned the **same** list, so the hash did not narrow anything. There were 5 English entries. I downloaded 3:
| OS id | file id | notes |
|---|---|---|
| 13056791 | 1961629543 | plain, `<i>` tags, 823 cues (221 in 0–600 s) |
| 13056785 | 1961629537→1961629538 | same timings/text as 1961629543 without italics (duplicate) |
| 13056790 | 1961629542 | SDH-ish (speaker labels `[Harry]`), 936 cues |

`…/file/1961630908` (the track the TV loaded) is **Romanian, not English** (`Îmi pare rău, Arch.`), with 739 cues. That is worth checking in the companion's language-selection logic.

I also extracted the MKV's embedded English tracks (s2 regular, s3 SDH). They are in sync by construction. s2 has cue timings identical to OS 1961629543 within 0–600 s, so the OS sub is a rip of this exact release.

ffsubsync 0.5.1 against centre.wav (candidates clipped to cues starting before 600 s), with `--skip-sync-on-low-quality`. Each run took about 1 s. No candidate was skipped for low quality.
| candidate | default: score / offset / scale | `--no-fix-framerate`: score / offset |
|---|---|---|
| OS 1961629543 (eng) | 15304.8 / **-0.410 s** / 1.001 | 15180 / **-0.100 s** |
| OS 1961629538 (eng) | 15304.8 / -0.410 s / 1.001 | (same file) |
| OS 1961629542 (eng SDH-ish) | 14872.2 / -0.440 s / 1.001 | 14721 / -0.350 s |
| OS 1961630908 (ron) | 33014 / -0.060 s / 1.000 | 33014 / -0.060 s |
| embedded s2 (in sync by definition) | 14872.2 / -0.440 s / 1.001 | 14721 / -0.350 s |
| embedded s3 SDH (in sync) | 14107.0 / -0.380 s / 1.001 | 14054 / -0.060 s |
| embedded s2 vs downmix.wav | – | 7984 / -0.100 s |

**Sync benchmark verdict:** none of the references needed shifting. ffsubsync still "corrected" subs that are perfectly in sync by 0.06–0.44 s. By default it also picked a spurious 1.001 (24/23.976) framerate scale, which drifts by about 0.6 s over 600 s. The score is not comparable across files: the Romanian sub scores 2× higher just because its cues are longer. Implications: treat ffsubsync offsets under about 0.5 s as noise, and prefer `--no-fix-framerate` unless we have evidence of a framerate mismatch. The STT word timings independently confirm that the unshifted reference fits best (see the cue-start error table).

Reference used for scoring: OS 1961629543 after `ffsubsync --no-fix-framerate` (-0.10 s), clipped to 0–600 s. That gives 197 non-empty cues and 1145 words after SDH cleaning. Saved as `reference-os13056791-synced-0-600.en.srt`.

## 3. STT
```
uvx --python 3.12 --from mlx-whisper mlx_whisper {centre,downmix}.wav \
  --model mlx-community/whisper-large-v3-turbo --language en --task transcribe \
  --condition-on-previous-text False --hallucination-silence-threshold 2 \
  --word-timestamps True -f srt --output-dir out --output-name stt_<name>
```
Timing (wall clock, including uv env startup and model load):
| step | time |
|---|---|
| uv env creation for mlx-whisper (36 pkgs, first time; torch included, uv cache grew to 2.0 GB) | 27 s |
| model download (`snapshot_download`, 1.5 GB, while the torrent was competing for bandwidth) | **162 s** |
| (a) centre, first run (weights cached, cold) | 53.9 s |
| (a) centre, cached runs | **40.2 s, 39.9 s** (≈15× real time) |
| (b) downmix, cached runs | **25.0 s, 25.0 s** (≈24× real time) |
| peak RSS | ≈2.1–2.2 GB |

Output was bit-identical across repeated runs (deterministic). Downmix was consistently faster than centre. My hypothesis, not verified: the hallucination-silence-threshold logic re-seeks more often on the centre track, which has more long quiet gaps. Even with the model cached, mlx_whisper still hits the HF Hub on each run ("Fetching 4 files"). Set `HF_HUB_OFFLINE=1` for offline/production use.

## 4. Scores (reference = OS 1961629543 synced, 0–600 s; text lowercased, punctuation and apostrophes stripped, SDH removed)
| metric | centre (FC) | downmix (-ac 1) |
|---|---|---|
| ref words / hyp words | 1145 / 1140 | 1145 / 1311 |
| **WER** (S/D/I) | **13.7%** (80/41/36) | 30.9% (86/51/217) |
| WER, hyp words within ±1 s of a ref cue | **12.5%** (I=22) | 14.1% (I=24) |
| ref cues covered by an STT segment | **197/197 (100%)** | 194/197 (98.5%) |
| cue-start error, first word of cue matched (n) | 165 cues | 159 cues |
| median / p90 abs | 0.28 s / 0.60 s | 0.27 s / 0.66 s |
| median signed (STT − ref) | +0.215 s | +0.210 s |
| nearest-segment-start error median / p90 | 0.34 s / 1.35 s | 0.33 s / 1.04 s |

Sensitivity to the reference: scored against the unshifted OS sub (= embedded s2 timings), WER is unchanged and cue-start error improves (centre: median 0.19 s, p90 0.54 s, signed +0.10 s; downmix: 0.20 / 0.51 / +0.10 s). Against the default ffsubsync output (-0.41 s, scale 1.001): centre 0.28 / 0.60 / +0.22 s. So whisper's word onsets are about 0.1 s after the original cue starts, which is normal because cues lead speech slightly. The ffsubsync "correction" made the alignment slightly worse.

Hallucinations and loops:
- **centre:** 2 segments with no reference cue within ±1 s: `[94.9] BELL RINGS` (caption-style hallucination over a sound effect) and `[439.3] Thank you.` (the classic whisper hallucination, here during the music bed). No repetition loops.
- **downmix:** 14 out-of-cue segments from 413.6 to 466.8 s, all **transcribed song lyrics** from a music cue (one 20 s run-on segment, then "alone, alone, alone, alone", "it's back, it's back, it's back, it's back, it's back", "I'm gonna hit your business" ×3). These are not in the reference, account for almost all of downmix's 217 insertions, and two segments trigger the repetition flag. The centre channel removes this music almost completely. That is the main argument for FC extraction.
- Both tracks have a few one-word spill-overs at cue edges ("one", "were", "dad").

8 aligned examples where the outputs differ (66 of 197 cues differ; hyp words whose midpoint falls within ±0.3 s of the cue are shown, so neighbouring words can leak in):
```
[010.2-012.1] REF: Fentanyl. Yes or no?
   centre : fentanyl yes or no one
   downmix: fentanyl yes or no
[055.6-058.1] REF: I'm gonna descend on the Cotswolds
   centre : tonight then im going to descend on the cotswolds like a plague
   downmix: tonight im going to descend on the cotswolds like a plague
[116.4-117.8] REF: What? What's going on?
   centre : what whats going on
   downmix: gina what whats going on come on
[134.7-136.5] REF: It's a mess. Kerry next door WhatsApped me some photos.
   centre : its a mess kerry next door whats happening some photos
   downmix: its a mess kerry next door but sent me some photos
[156.2-157.2] REF: Paul, where's Harry?
   centre : idea oh wheres harry
   downmix: not dead hold on wheres harry
[285.2-287.3] REF: I see. Is that for me?
   centre : i see is that for me were
   downmix: i see is that for me
[472.1-473.8] REF: Come here, you bollocks. Come here.
   centre : come here you ballerks come here
   downmix: come here you ballacks come here you
[495.4-496.8] REF: Okay.
   centre : dad okay
   downmix: okay
```
Common substitution classes in both: "gonna" vs "going to" (the reference normalises verbatim speech), British slang and names ("bollocks", "Maeve"→"Maverlea"), numbers ("one hundred percent"). Much of the remaining ~12% WER is subtitle condensation, not ASR error.

## Observations / recommendations
1. **Use FC (centre) extraction for 5.1.** It gives the same in-cue accuracy (12.5% vs 14.1%), but downmix transcribes music lyrics, which more than doubles total WER (13.7% → 30.9%) and produces repetition. Centre is about 1.6× slower here (40 s vs 25 s per 10 min), which is still about 15× real time.
2. large-v3-turbo on MLX: about 40 s per 10 min of audio with the model cached; full 47 min episode ≈ 3–3.5 min (extrapolated). The first-time cost is dominated by the 1.5 GB model download plus 2 GB of uv deps (torch).
3. ffsubsync on real in-sync content reports 0.06–0.44 s offsets and a bogus 1.001 scale by default. Use `--no-fix-framerate` and ignore offsets under 0.5 s.
4. OpenSubtitles hash/size params did not change the result list. The track the TV actually loaded (1961630908) is Romanian.
5. Partial-torrent reads: audio-only `-t 600` was instant. Mixing subtitle outputs caused an indefinite stall that `-rw_timeout` did not catch, so a wall-clock watchdog is needed.

## Files (kept)
- `/tmp/stremio-plus-plus-stt/mobland-s01e03-first10min.en.srt` – best STT (centre)
- `/tmp/stremio-plus-plus-stt/reference-os13056791-synced-0-600.en.srt` – reference used
- `out/` – all STT SRT/JSON/logs and score outputs; `subs/` – candidates, ffsubsync outputs and logs; `scripts/` – srtlib.py, score.py, env.sh
- WAVs deleted. Per the coordinator's change of plan, HF_HOME (model) and the uv cache/env were **kept** for the follow-up test.
