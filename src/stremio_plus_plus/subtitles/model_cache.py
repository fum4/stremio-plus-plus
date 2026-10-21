"""Is the Whisper model on disk, and downloading it with progress for the setup UI.

Progress is the size of the repo's blobs in the Hugging Face cache (partial files included)
against the total from the Hub's file metadata; when that can't be measured the UI shows an
indeterminate bar rather than a wrong number.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import structlog
from huggingface_hub import (  # pyright: ignore[reportMissingTypeStubs]
    HfApi,
    constants,
    snapshot_download,  # pyright: ignore[reportUnknownVariableType]
)

log = structlog.get_logger()
State = Literal["idle", "running", "done", "failed"]


def _repo_dir(model: str) -> Path:
    return Path(constants.HF_HUB_CACHE) / f"models--{model.replace('/', '--')}"


def is_cached(model: str) -> bool:
    try:
        snapshot_download(model, local_files_only=True)
    except Exception:  # LocalEntryNotFoundError and friends: not (fully) there
        return False
    return True


def _bytes_on_disk(model: str) -> int:
    blobs = _repo_dir(model) / "blobs"
    return sum(f.stat().st_size for f in blobs.iterdir() if f.is_file()) if blobs.is_dir() else 0


def _download(model: str) -> None:
    snapshot_download(model)


def _total_bytes(model: str) -> int | None:
    info = HfApi().model_info(model, files_metadata=True)
    sizes = [s.size for s in info.siblings or [] if s.size]
    return sum(sizes) or None


@dataclass
class ModelDownload:
    model: str = ""
    state: State = "idle"
    total: int | None = None
    error: str | None = None
    _task: asyncio.Task[None] | None = None

    def start(self, model: str) -> None:
        if self.state == "running" and self.model == model:
            return
        self.model, self.state, self.total, self.error = model, "running", None, None
        self._task = asyncio.create_task(self._run(model), name="model-download")

    def view(self) -> dict[str, object]:
        done = self.state == "done" or (self.state != "running" and is_cached(self.model))
        return {
            "model": self.model,
            "state": "done" if done else self.state,
            "total": self.total,
            "downloaded": _bytes_on_disk(self.model) if self.model else 0,
            "error": self.error,
        }

    async def _run(self, model: str) -> None:
        try:
            self.total = await asyncio.to_thread(_total_bytes, model)
            await asyncio.to_thread(_download, model)
            self.state = "done"
            log.info("whisper_model_downloaded", model=model)
        except Exception as exc:
            self.state, self.error = "failed", str(exc)[:300]
            log.warning("whisper_model_download_failed", model=model, error=self.error)
