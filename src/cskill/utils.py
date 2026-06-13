"""Shared helpers: atomic writes, path expansion."""

import json
import os
from pathlib import Path


def expand(path: str) -> Path:
    """Expand ~ and env vars into an absolute Path."""
    return Path(os.path.expandvars(path)).expanduser()


def atomic_write_text(path: Path, text: str) -> None:
    """Write text to path via a .tmp sibling + rename (atomic on POSIX)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def atomic_write_json(path: Path, data) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
