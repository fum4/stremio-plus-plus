"""TV-control magic values. Credential files live under COMPANION_DATA_DIR, mode 600, per host."""

CLIENT_NAME = "stremio++"  # what the TV shows in its pairing prompt and device list
PAIR_TIMEOUT_S = 60.0  # how long a pairing waits for someone at the TV
KEY_DELAY_S = 0.4  # between keys: TV UIs drop presses that arrive faster
CONNECT_TIMEOUT_S = 10.0

# Samsung Tizen: wss, self-signed certificate. Verified on the owner's UE43TU7092 (Tizen 5.5).
WS_PORT = 8002
TOKEN_FILE = "tv-token"  # name kept from before the adapters so existing pairings stay valid

# LG webOS (SSAP): aiowebostv tries ws://:3000, then wss://:3001. Not verified on hardware.
WEBOS_PORT = 3000
WEBOS_KEY_FILE = "tv-webos-client-key"

# Android TV / Google TV (Android TV Remote protocol v2). Not verified on hardware.
ANDROIDTV_PORT = 6466  # remote; pairing is on 6467
ANDROIDTV_CERT_FILE = "tv-androidtv-cert.pem"
ANDROIDTV_KEY_FILE = "tv-androidtv-key.pem"

# Amazon Fire TV (Fire OS, Android-based): ADB over the network. Not verified on hardware.
FIRETV_PORT = 5555
FIRETV_KEY_FILE = "tv-firetv-adbkey"  # private key; the public half is `<file>.pub`
