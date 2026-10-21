# Query tag on every request the companion makes to the server, so the watch tracker can tell
# our own reads (pin, audio extraction) from the TV's in the server log.
COMPANION_TAG = "src=companion"
REQUEST_TIMEOUT_S = 10.0
CACHE_SUBDIR = "stremio-cache"
# Hashing reads the file's first and last 64 KiB, which may first have to be downloaded.
OPENSUB_HASH_TIMEOUT_S = 120.0
