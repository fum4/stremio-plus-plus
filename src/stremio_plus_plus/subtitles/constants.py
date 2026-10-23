LABEL = "Romanian (AI)"
LANG = "ron"
SAMPLE_RATE = 16000
# Window sizing (scheduler.py): one window of L s costs ~STEP_FIXED_S + STEP_PER_S·L, measured
# on the M4 host (docs/research/subtitle-latency.md). Conservative: Whisper and Claude overlap.
STEP_FIXED_S = 8.0
STEP_PER_S = 0.3
FIRST_WINDOW_S = 15.0  # > STEP_FIXED_S / (1 - STEP_PER_S) ≈ 11 s, or windows never grow
MIN_WINDOW_S = 15.0
MAX_WINDOW_S = 120.0
# A subtitle file request that finds nothing yet waits this long for the first window instead
# of answering with the placeholder straight away (the player fetches once per track selection).
# Hard ceiling: the TV fetches through server.js /subtitles.vtt, which gives up on the source
# after ~10 s and answers 500 ("failed to load external subtitles"), measured on the pinned
# server: 8 s delay → 200, 11 s → 500 at 10.2 s (docs/research/stremio-internals.md).
FIRST_ANSWER_WAIT_S = 7.0
OVERLAP_S = 2.0
# Until the viewer picks our track, only this much ahead of the playhead is generated: picking
# it then shows lines at once, and an episode watched with other subtitles costs a few windows.
PRIME_S = 120.0
MAX_LINE_CHARS = 42
MAX_LINES = 2
AUDIO_TIMEOUT_S = 600
# TV reads past this fraction of the file are the player fetching the MKV index, not the playhead.
TAIL_READ_FRACTION = 0.98
MAX_WINDOW_FAILURES = 3
# A failed file/window (e.g. a slow torrent timing out the audio read) is retried on the next
# subtitles request (the viewer re-selecting the track), at most this often.
RETRY_FAILED_AFTER_S = 60.0
