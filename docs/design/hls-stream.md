# The Stremio++ source: HLS with subtitles inside the stream

## Why
An external subtitle track is fetched **once per selection** (stremio-core, through server.js
`/subtitles.vtt`): lines generated after that load never reach the screen, so AI subtitles
needed an off/on toggle. In an HLS stream the player fetches the subtitle **segments lazily**,
a few seconds ahead of playback, so lines generated while the episode plays arrive on their own.

## What the TV does (Samsung, Stremio Theater, tested 2026-10-22)
| Test | Result |
|---|---|
| 5-min H.264 + AAC stereo + WebVTT rendition, `DEFAULT=YES,AUTOSELECT=YES` | plays; subtitles shown from the first second with the menu on **Off**; segments fetched ~10 s ahead; a seek to 4:00 keeps them in sync |
| 4K HEVC Main 10 + E-AC-3 5.1 in fMP4 | never starts (spinner over the poster) |
| same in MPEG-TS, E-AC-3 copied (stream type 0x87, ATSC) | video, **no sound** |
| same, audio → AC-3 5.1 640k | video + 5.1 sound |
| same, E-AC-3 copied with DVB signalling (`mpegts_flags=system_b`: type 0x06 + descriptor) | video + original 5.1 sound |

The player's subtitle menu does not list in-stream renditions; it shows only addon tracks.

## How it works
- **Entry** (`app/stream_routes.py`, `app/picker.py`, `sources/`): the stream resource asks every
  stream addon in the user's Stremio collection (auth key from the account setup; Torrentio
  without one), ranks the candidates and answers **one** entry. The torrent is only started when
  the player opens it (`POST /{ih}/create` with the addon's trackers, like Stremio clients).
- **Repackaging** (`stream/`): one ffmpeg per session, video copied, audio copied when the TV
  plays it in HLS (AAC, AC-3, E-AC-3, MP3) and Dolby Digital 5.1 otherwise; the segment muxer
  cuts at the first keyframe after each 6 s boundary. Timestamps keep the source's (`-copyts`,
  +10 s), so a restart after a seek lines up with the earlier segments and the WebVTT
  `X-TIMESTAMP-MAP` is a constant. The producer runs ≤ 20 segments ahead (SIGSTOP), keeps 5
  behind, restarts on a seek, and stops after 5 idle minutes.
- **Subtitles** (`app/subtitle_switch.py`): segments are empty until the viewer picks
  *Romanian (AI)* in the menu. That track's fetch is the switch: from then on segments carry the
  generated lines, and the SRT answered covers exactly the segments already buffered empty, so
  lines show at once and never twice. Another addon's track appears in the server log
  (`-> GET /subtitles.vtt?from=…`) and switches ours off; Stremio's **Off** sends nothing.
- **Generation**: until the track is picked, only the 2 minutes ahead of the playhead are
  generated (`PRIME_S`), so an episode watched with human subtitles costs a few windows.
- **Playback events**: our reads are tagged, so the log tracker never sees an HLS episode
  played; video segment requests are reported to the same handlers (pins, next-episode
  prefetch, subtitle playhead).

## Limits
- Dolby Vision without an HDR10 base layer, AV1, 3D: ranked last / refused.
- Switching *off* shows the lines already buffered (~10–30 s).
- Cuts follow keyframes, so a segment can be 2–14 s; EXTINF stays nominal (6 s).
- Debrid links are played directly from the link; subtitles for them read the link too.
