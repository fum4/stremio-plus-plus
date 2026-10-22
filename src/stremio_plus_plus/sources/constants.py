# Used when no Stremio account is connected (or it lists no stream addon we can use).
DEFAULT_ADDONS = ("https://torrentio.strem.fun",)
FETCH_TIMEOUT_S = 8.0
OWN_ADDON_ID = "io.github.fum4.stremio-plus-plus"
# Addons whose streams never are torrents or debrid links worth repackaging.
SKIP_ADDON_IDS = frozenset({"org.stremio.local", "org.stremio.watchhub", "org.stremio.youtube"})
# Highest resolution to pick (the owner's Samsung plays 4K HEVC; config page later).
MAX_HEIGHT = 2160
# Release words the TV can't play inside HLS (or at all): never picked.
UNPLAYABLE = ("av1", "3d", "hsbs", "cam", "hdcam", "telesync", "hdts", " ts ", "screener")
# Dolby Vision: profile 5 has no HDR10 base layer; picked only when nothing else exists.
DOLBY_VISION = ("dolby vision", "dovi", ".dv.", " dv ", "[dv]", "dv hdr", "hdr dv")
RESOLUTIONS = (("2160", 2160), ("4k", 2160), ("uhd", 2160), ("1440", 1440), ("1080", 1080),
               ("720", 720), ("576", 576), ("480", 480))  # fmt: skip
# Torrentio's Cloudflare front answers 403 to httpx's default user agent.
USER_AGENT = "stremio-plus-plus/0.3"
