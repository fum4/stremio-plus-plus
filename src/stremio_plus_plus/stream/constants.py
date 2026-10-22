# Nominal segment length. Video is copied, so real cuts land on the first keyframe at or after
# each nominal boundary (ffmpeg segment muxer); EXTINF stays nominal, timestamps stay exact.
SEGMENT_S = 6.0
# Every output timestamp is the source's plus this, so the first B-frames never go negative.
TS_OFFSET_S = 10.0
MPEGTS_HZ = 90_000
# Audio the TV plays inside HLS (Samsung, verified 2026-10-22): passed through untouched.
# E-AC-3 needs DVB-style signalling (stream type 0x06 + descriptor, ffmpeg `system_b`): with the
# ATSC type 0x87 the Samsung played the video in silence.
COPY_AUDIO = frozenset({"aac", "ac3", "eac3", "mp3"})
SYSTEM_B_AUDIO = frozenset({"eac3"})
# Everything else (DTS, TrueHD, FLAC, Opus…) becomes Dolby Digital at its ceiling.
FALLBACK_AUDIO_CODEC = "ac3"
FALLBACK_AUDIO_BITRATE = "640k"
FALLBACK_AUDIO_MAX_CHANNELS = 6
VIDEO_CODECS = frozenset({"h264", "hevc"})
# Producer pacing: keep at most this many finished segments ahead of the newest request
# (SIGSTOP beyond it) and delete those this far behind it.
MAX_AHEAD_SEGMENTS = 20
KEEP_BEHIND_SEGMENTS = 5
# A request this far past what the producer has written restarts it there (a seek).
RESTART_GAP_SEGMENTS = 4
# How long a segment request may wait for the producer (a torrent may still be fetching pieces).
SEGMENT_WAIT_S = 45.0
POLL_S = 0.2
# Sessions untouched this long are stopped (paused playback resumes with a restart).
IDLE_STOP_S = 300.0
PROBE_TIMEOUT_S = 120.0
# A run that failed this recently at the requested segment isn't relaunched (bad link, missing
# file): the request fails instead of spawning ffmpeg every poll.
FAILED_RETRY_S = 10.0
STOP_TIMEOUT_S = 5.0  # SIGTERM, then SIGKILL
# A replaced run's directory outlives it a little: a response may still be streaming from it.
OLD_RUN_GRACE_S = 60.0
# The player buffers subtitle segments ahead; while subtitles are off, they're served empty.
VTT_EMPTY = "WEBVTT\nX-TIMESTAMP-MAP=MPEGTS:{mpegts},LOCAL:00:00:00.000\n\n"
