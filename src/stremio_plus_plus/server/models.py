"""What the companion needs to know about the Stremio streaming server's engines."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TorrentFile:
    index: int
    name: str
    length: int


@dataclass(frozen=True)
class Engine:
    info_hash: str
    name: str
    files: tuple[TorrentFile, ...]
    downloaded: int
    download_speed: float
    peers: int

    def file(self, index: int) -> TorrentFile | None:
        return self.files[index] if 0 <= index < len(self.files) else None
