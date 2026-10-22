# Used when no Stremio account is connected (or it lists no stream addon we can use).
DEFAULT_ADDONS = ("https://torrentio.strem.fun",)
FETCH_TIMEOUT_S = 8.0
OWN_ADDON_ID = "io.github.fum4.stremio-plus-plus"
# Addons whose streams never are torrents or debrid links worth repackaging.
SKIP_ADDON_IDS = frozenset({"org.stremio.local", "org.stremio.watchhub", "org.stremio.youtube"})
# Highest resolution to pick (the owner's Samsung plays 4K HEVC; config page later).
MAX_HEIGHT = 2160
# Release words the TV can't play inside HLS (or at all): never picked.
UNPLAYABLE = ("av1", "3d", "hsbs", "cam", "hdcam", "telesync", "hdts", " ts ", "screener",
              "xvid", "divx", ".avi")  # fmt: skip
# Dolby Vision: profile 5 has no HDR10 base layer; picked only when nothing else exists.
DOLBY_VISION = ("dolby vision", "dovi", ".dv.", " dv ", "[dv]", "dv hdr", "hdr dv")
# Whole words only: uploader names like "Wolfmax4k" are not resolutions.
RESOLUTIONS = (("2160p", 2160), ("4k", 2160), ("uhd", 2160), ("1440p", 1440), ("1080p", 1080),
               ("1080i", 1080), ("720p", 720), ("576p", 576), ("480p", 480))  # fmt: skip
# A release this well seeded starts and plays smoothly; below it, quality yields to seeders.
HEALTHY_SEEDERS = 25
# Torrentio flags non-English audio with country flags (none = English only); these words mark
# dubbed releases on addons that don't.
ENGLISH_FLAGS = ("🇬🇧", "🇺🇸")
FOREIGN_WORDS = ("castellano", "latino", "vostfr", "truefrench", "dublado", "[cap.", " dub ")
# Torrentio's Cloudflare front answers 403 to httpx's default user agent.
USER_AGENT = "stremio-plus-plus/0.3"
