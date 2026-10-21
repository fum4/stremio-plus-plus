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
FIRST_ANSWER_WAIT_S = 20.0
OVERLAP_S = 2.0
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
TRANSLATE_MODEL = "claude-haiku-5-5"
MAX_LINE_CHARS = 42
MAX_LINES = 2
CONTEXT_CUES = 15
# Subscription guardrails (owner's Claude plan): one call at a time, hard hourly cap.
MAX_CLAUDE_CALLS_PER_HOUR = 120
CLAUDE_TIMEOUT_S = 180
AUDIO_TIMEOUT_S = 600
# TV reads past this fraction of the file are the player fetching the MKV index, not the playhead.
TAIL_READ_FRACTION = 0.98
MAX_WINDOW_FAILURES = 3
# A failed file/window (e.g. a slow torrent timing out the audio read) is retried on the next
# subtitles request (the viewer re-selecting the track), at most this often.
RETRY_FAILED_AFTER_S = 60.0
