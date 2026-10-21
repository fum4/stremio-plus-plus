LABEL = "Romanian (AI)"
LANG = "ron"
SAMPLE_RATE = 16000
CHUNK_S = 120
# Before the playhead's full chunk, generate just this much from the playhead: first lines in
# seconds instead of after a whole chunk's audio has downloaded. Kept in memory, never stored.
LEAD_IN_S = 30
# A subtitle file request that finds nothing yet waits this long for the lead-in instead of
# answering with the placeholder straight away (the player fetches once per track selection).
FIRST_ANSWER_WAIT_S = 10.0
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
MAX_CHUNK_FAILURES = 3
# A failed file/chunk (e.g. a slow torrent timing out the audio read) is retried on the next
# subtitles request (the viewer re-selecting the track), at most this often.
RETRY_FAILED_AFTER_S = 60.0
