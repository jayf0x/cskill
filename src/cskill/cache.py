"""Local cache: one JSON file per session + one aggregated index.

Layout under cache_dir (default ~/.cache/cskill/):
  index.json                 {sessions: {key: {mtime, size, patterns: N}}, ...}
  sessions/<key>.json        {session: key, patterns: {pattern: count}}
  normalization.md           human-readable normalization rules

A session is keyed by its JSONL path relative to projects_dir, sanitized for
use as a filename. Incremental collection skips sessions whose mtime+size are
unchanged in the index. All writes are atomic (.tmp + rename).
"""

from collections import Counter
from pathlib import Path

from cskill.utils import atomic_write_json, read_json

INDEX_NAME = "index.json"
SESSIONS_SUBDIR = "sessions"


def session_key(jsonl_path: Path, projects_root: Path) -> str:
    try:
        rel = jsonl_path.relative_to(projects_root)
    except ValueError:
        rel = Path(jsonl_path.name)
    return str(rel.with_suffix("")).replace("/", "__")


def load_index(cache_root: Path) -> dict:
    idx = read_json(cache_root / INDEX_NAME, default={})
    return idx if isinstance(idx, dict) else {}


def save_index(cache_root: Path, index: dict) -> None:
    atomic_write_json(cache_root / INDEX_NAME, index)


def is_cached(index: dict, key: str, stat) -> bool:
    entry = index.get("sessions", {}).get(key)
    return bool(entry) and entry.get("mtime") == stat.st_mtime and entry.get("size") == stat.st_size


def save_session(cache_root: Path, key: str, patterns: Counter) -> None:
    atomic_write_json(
        cache_root / SESSIONS_SUBDIR / f"{key}.json",
        {"session": key, "patterns": dict(patterns)},
    )


def aggregate(cache_root: Path) -> Counter:
    """Sum pattern counts across all cached session files."""
    total = Counter()
    sessions_dir = cache_root / SESSIONS_SUBDIR
    if sessions_dir.is_dir():
        for f in sorted(sessions_dir.glob("*.json")):
            data = read_json(f, default={})
            for pattern, count in (data.get("patterns") or {}).items():
                total[pattern] += int(count)
    return total


def cached_session_count(cache_root: Path) -> int:
    sessions_dir = cache_root / SESSIONS_SUBDIR
    return sum(1 for _ in sessions_dir.glob("*.json")) if sessions_dir.is_dir() else 0
