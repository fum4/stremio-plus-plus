# Query tag on every request the companion makes to the server, so the watch tracker can tell
# our own reads (pin, audio extraction) from the TV's in the server log.
COMPANION_TAG = "src=companion"
REQUEST_TIMEOUT_S = 10.0
CACHE_SUBDIR = "stremio-cache"
# Where server.js serves HTTPS once remoteHttps is set (the TV's server URL uses it).
HTTPS_PORT = 12470
# Hashing reads the file's first and last 64 KiB, which may first have to be downloaded.
OPENSUB_HASH_TIMEOUT_S = 120.0
# server.js /subtitles.vtt gives up on fetching an addon's subtitle source after ~10 s and
# answers 500 (measured, docs/research/stremio-internals.md § Subtitle proxy).
SUBTITLE_PROXY_TIMEOUT_S = 10.0
# Starting a torrent answers once its metadata (file list) arrives from peers.
CREATE_TIMEOUT_S = 60.0
PEERS_MIN = 40  # Stremio clients' peerSearch defaults
PEERS_MAX = 150
