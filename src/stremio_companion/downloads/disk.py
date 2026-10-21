import shutil
from pathlib import Path


def free_bytes(path: Path) -> int:
    probe = path if path.exists() else path.parent
    return shutil.disk_usage(probe).free
