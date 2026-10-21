VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".m4v", ".mov", ".webm", ".ts")
# Never let downloads push the disk below this; the cleanup evicts down to it too.
MIN_FREE_BYTES = 3 * 1024**3
STALE_AFTER_S = 7 * 24 * 3600
PIN_SWEEP_INTERVAL_S = 30.0
COMPLETE_PROGRESS = 0.999
