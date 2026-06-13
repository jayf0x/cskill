"""Parse Claude Code session JSONL files and extract normalized bash patterns.

Schema (validated against real ~/.claude/projects data): each JSONL line is an
event; assistant events carry `message.content` as a list of blocks, and Bash
invocations are blocks of `{"type": "tool_use", "name": "Bash",
"input": {"command": ...}}`. Subagent JSONL files under
<session-id>/subagents/ use the same shape and are included.
"""

import json
from collections import Counter
from pathlib import Path

from cskill import cache
from cskill.normalizer import NORMALIZATION_DOC, normalize_command
from cskill.utils import atomic_write_text


def extract_commands(jsonl_path: Path) -> list:
    """Raw Bash commands from one session file, in order."""
    commands = []
    try:
        with jsonl_path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = entry.get("message")
                if not isinstance(message, dict):
                    continue
                content = message.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "tool_use"
                        and block.get("name") == "Bash"
                    ):
                        command = (block.get("input") or {}).get("command")
                        if command:
                            commands.append(command)
    except OSError:
        pass
    return commands


def collect(cfg: dict, projects_root: Path, cache_root: Path) -> dict:
    """Incrementally parse all sessions; returns a summary dict."""
    index = cache.load_index(cache_root)
    index.setdefault("sessions", {})
    parsed = skipped = command_count = 0

    for jsonl_path in sorted(projects_root.rglob("*.jsonl")):
        key = cache.session_key(jsonl_path, projects_root)
        stat = jsonl_path.stat()
        if cache.is_cached(index, key, stat):
            skipped += 1
            continue
        patterns = Counter()
        for raw in extract_commands(jsonl_path):
            command_count += 1
            for pattern in normalize_command(raw):
                patterns[pattern] += 1
        cache.save_session(cache_root, key, patterns)
        index["sessions"][key] = {
            "mtime": stat.st_mtime,
            "size": stat.st_size,
            "patterns": len(patterns),
        }
        parsed += 1

    cache.save_index(cache_root, index)
    atomic_write_text(cache_root / "normalization.md", NORMALIZATION_DOC)

    totals = cache.aggregate(cache_root)
    return {
        "parsed": parsed,
        "skipped": skipped,
        "new_commands": command_count,
        "total_sessions": len(index["sessions"]),
        "unique_patterns": len(totals),
        "top": totals.most_common(10),
    }
