"""Generate the skill markdown from aggregated cache data.

Categories are derived from the head token of each pattern; only categories
the data actually supports (>= min_frequency patterns present) are emitted.
"""

from collections import Counter
from datetime import datetime, timezone

# head token -> category title. Built from heads observed in real data;
# unmapped heads fall into "Other".
CATEGORIES = {
    "grep": "Searching code", "rg": "Searching code", "ag": "Searching code",
    "find": "Finding files",
    "cat": "Reading files", "sed": "Reading files", "head": "Reading files",
    "tail": "Reading files", "wc": "Reading files",
    "ls": "Listing directories", "tree": "Listing directories",
    "git": "Git",
    "gh": "GitHub CLI",
    "bun": "Build & packages", "bunx": "Build & packages",
    "npm": "Build & packages", "npx": "Build & packages",
    "yarn": "Build & packages", "pnpm": "Build & packages",
    "node": "Build & packages",
    "python3": "Python", "python": "Python", "pytest": "Python", "pip": "Python",
    "curl": "HTTP & dev servers", "wget": "HTTP & dev servers",
    "mkdir": "File management", "rm": "File management", "cp": "File management",
    "mv": "File management", "chmod": "File management", "touch": "File management",
    "ln": "File management", "cd": "File management",
}

# Category emission order (categories with no qualifying patterns are skipped).
CATEGORY_ORDER = [
    "Searching code", "Finding files", "Reading files", "Listing directories",
    "Git", "GitHub CLI", "Build & packages", "Python", "HTTP & dev servers",
    "File management", "Other",
]

_DESCRIPTIONS = [
    # (head, substring-of-pattern or None, description) — first match wins.
    ("grep", " -r", "Recursive content search"),
    ("grep", " -n", "Search with line numbers"),
    ("grep", None, "Search file contents"),
    ("rg", None, "Search file contents"),
    ("find", " -name", "Find files by name"),
    ("find", " -type", "Find files by type"),
    ("find", None, "Find files"),
    ("sed", "'1,5p'", "Print a line range from a file"),
    ("sed", " -i", "In-place text replacement"),
    ("sed", None, "Stream-edit text"),
    ("cat", "| grep", "Read a file filtered by pattern"),
    ("cat", "| head", "Read the start of a file"),
    ("cat", None, "Read a file"),
    ("head", None, "Read the start of a file"),
    ("tail", None, "Read the end of a file"),
    ("wc", None, "Count lines/words"),
    ("ls", " -la", "Detailed directory listing"),
    ("ls", None, "List a directory"),
    ("tree", None, "Directory tree"),
    ("git", "log", "Inspect commit history"),
    ("git", "diff", "Show changes"),
    ("git", "status", "Working tree status"),
    ("git", "add", "Stage changes"),
    ("git", "commit", "Commit changes"),
    ("git", "push", "Push to remote"),
    ("git", "branch", "List/manage branches"),
    ("git", "show", "Inspect a commit"),
    ("git", "checkout", "Switch branch/restore files"),
    ("git", None, "Git operation"),
    ("gh", "pr", "GitHub pull request via gh"),
    ("gh", "issue", "GitHub issue via gh"),
    ("gh", "repo", "GitHub repo info via gh"),
    ("gh", "api", "GitHub API call via gh"),
    ("gh", "release", "GitHub release via gh"),
    ("gh", None, "GitHub CLI operation"),
    ("bun", "test", "Run tests"),
    ("bun", "run build", "Build the project"),
    ("bun", "add", "Add a dependency"),
    ("bun", "install", "Install dependencies"),
    ("bun", "dev", "Start the dev server"),
    ("bun", None, "Bun command"),
    ("npm", "run build", "Build the project"),
    ("npm", "test", "Run tests"),
    ("npm", "pack", "Inspect package contents"),
    ("npm", None, "npm command"),
    ("npx", None, "Run a package binary"),
    ("bunx", None, "Run a package binary"),
    ("node", None, "Run a Node script"),
    ("python3", "-m pytest", "Run Python tests"),
    ("python3", "-m", "Run a Python module"),
    ("python3", "-c", "Run inline Python"),
    ("python3", None, "Run a Python script"),
    ("curl", "localhost", "Check a local dev server"),
    ("curl", None, "HTTP request"),
    ("mkdir", None, "Create a directory"),
    ("rm", None, "Remove files"),
    ("cp", None, "Copy files"),
    ("mv", None, "Move/rename files"),
    ("chmod", None, "Change file permissions"),
    ("cd", None, "Change directory"),
    ("ln", None, "Create a symlink"),
    ("touch", None, "Create an empty file"),
]


def _head(pattern: str) -> str:
    token = pattern.split(None, 1)[0] if pattern.split() else ""
    return token.rsplit("/", 1)[-1]  # /opt/.../python3 -> python3


def describe(pattern: str) -> str:
    head = _head(pattern)
    for h, needle, desc in _DESCRIPTIONS:
        if h == head and (needle is None or needle in pattern):
            return desc
    return f"`{head}` usage" if head else "Shell command"


def generate_markdown(totals: Counter, cfg: dict, session_count: int) -> str:
    min_freq = int(cfg["min_frequency"])
    max_patterns = int(cfg["max_patterns"])

    qualifying = [(p, n) for p, n in totals.most_common() if n >= min_freq][:max_patterns]

    by_category = {}
    for pattern, count in qualifying:
        category = CATEGORIES.get(_head(pattern), "Other")
        by_category.setdefault(category, []).append((pattern, count))

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# cskill — bash pattern reference",
        "<!-- generated by cskill — do not edit manually -->",
        f"<!-- updated: {timestamp} | sessions: {session_count} | patterns: {len(qualifying)} -->",
        "",
        "High-frequency bash patterns mined from this user's past Claude Code",
        "sessions. Placeholders: `some/path/file.ext` = any file, `'pattern'` =",
        "any search string, `20`/`3000` = any count/port. See normalization.md",
        "in the cskill cache for the full rules.",
        "",
    ]
    for category in CATEGORY_ORDER:
        entries = by_category.get(category)
        if not entries:
            continue
        lines.append(f"## {category}")
        for pattern, _count in entries:
            lines.append(f"- {describe(pattern)}: `{pattern}`")
        lines.append("")
    return "\n".join(lines)


SKILL_FRONTMATTER = """\
---
name: cskill
description: >
  Bash command patterns mined from this user's past Claude Code sessions.
  Consult before composing shell commands to reuse known-good local patterns
  for searching, reading files, git, GitHub CLI, builds, and dev servers.
---

"""


def generate_skill_file(totals: Counter, cfg: dict, session_count: int) -> str:
    return SKILL_FRONTMATTER + generate_markdown(totals, cfg, session_count)
