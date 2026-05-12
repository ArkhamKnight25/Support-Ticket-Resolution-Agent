import os
from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_files(directory: str | Path, extensions: tuple[str, ...] = ()) -> list[Path]:
    p = Path(directory)
    if not p.exists():
        return []
    files = [f for f in p.rglob("*") if f.is_file()]
    if extensions:
        files = [f for f in files if f.suffix.lower() in extensions]
    return files
