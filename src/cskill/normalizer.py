"""Normalize raw bash commands into stable, reusable patterns.

Rules were derived from ~1,600 real commands collected from local Claude Code
sessions (see normalization.md, generated into the cache dir). The goal: two
commands doing the same thing with different arguments map to the same string.

Placeholders are small and consistent:
  paths            some/path/file.<ext>   (files)  /  some/path/dir  (dirs)
  quoted strings   'pattern'
  line ranges      '1,5p'
  counts (-N)      20
  ports            3000
  commit hashes    abc1234
  UUIDs            <uuid>
  heredoc bodies   <<'EOF' ... EOF
"""

import re

# Filenames kept verbatim — `cat package.json` is itself a pattern, distinct
# from reading an arbitrary file.
WELL_KNOWN_FILES = {
    "package.json", "tsconfig.json", "README.md", "LICENSE", "Makefile",
    "bun.lock", "bun.lockb", "package-lock.json", "yarn.lock",
    "pyproject.toml", "requirements.txt", "Cargo.toml", ".gitignore",
    "CLAUDE.md", "SKILL.md", "index.html", "vite.config.ts", "settings.json",
}

_HEREDOC_RE = re.compile(r"<<-?\s*'?(\w+)'?.*?\n\1", re.DOTALL)
_URL_RE = re.compile(r"https?://[^\s'\"|)>]+")
_LOCALHOST_RE = re.compile(r"https?://(?:localhost|127\.0\.0\.1)(?::\d+)?[^\s'\"|)>]*")
_SED_RANGE_RE = re.compile(r"'(\d+),(\d+)p'|\"(\d+),(\d+)p\"")
_SED_LINE_RE = re.compile(r"'(\d+)p'|\"(\d+)p\"")
_HASH_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
_UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
# Absolute (incl. ~) or multi-segment relative path tokens.
_PATH_RE = re.compile(r"(?:~?/|\.{1,2}/)[\w@.+\-/*]+|\b[\w@.+\-]+(?:/[\w@.+\-/*]+)+")
_QUOTED_RE = re.compile(r"'[^']+'|\"[^\"]+\"")
_COUNT_FLAG_RE = re.compile(r"((?:head|tail)\s+-c?n?\s*|-(?:n|m|A|B|C)\s*)(\d+)")
_ENV_PREFIX_RE = re.compile(r"^(?:\w+=\S+\s+)+")


def _placeholder_path(match: re.Match) -> str:
    token = match.group(0)
    # Don't re-mangle placeholders or pattern-bearing tokens.
    if token.startswith("/dev/") or "localhost" in token or "example.com" in token or token.startswith("some/path"):
        return token
    base = token.rstrip("/").rsplit("/", 1)[-1]
    if base in WELL_KNOWN_FILES:
        return base
    if "*" in base:
        ext = base.rsplit(".", 1)[-1] if "." in base.lstrip(".") else None
        return f"some/path/*.{ext}" if ext and ext != base else "some/path/*"
    if "." in base.lstrip("."):
        return f"some/path/file.{base.rsplit('.', 1)[-1]}"
    return "some/path/dir"


def split_segments(command: str) -> list:
    """Split a compound command on top-level `&&`, `;` and newlines.

    Pipelines (`|`, `||`) stay intact — `cmd | head -20` is itself a pattern.
    Quote-aware so separators inside strings don't split.
    """
    segments, buf, quote = [], [], None
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == quote and command[i - 1] != "\\":
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n and command[i + 1] == "\n":
            buf.append(" ")
            i += 2
            continue
        if ch == "\n" or ch == ";":
            segments.append("".join(buf))
            buf = []
            i += 1
            continue
        if ch == "&" and i + 1 < n and command[i + 1] == "&":
            segments.append("".join(buf))
            buf = []
            i += 2
            continue
        buf.append(ch)
        i += 1
    segments.append("".join(buf))
    return [s.strip() for s in segments if s.strip()]


def normalize_segment(seg: str) -> str:
    """Apply placeholder rules to one simple command / pipeline."""
    seg = _ENV_PREFIX_RE.sub("", seg)
    # An absolute interpreter path is the same pattern as the bare command.
    head, _, rest = seg.partition(" ")
    if "/" in head and not head.startswith(("./", "some/path")):
        seg = head.rsplit("/", 1)[-1] + (" " + rest if rest else "")
    # Order matters: specific (ranges, urls, ids) before generic (quotes, paths).
    seg = _SED_RANGE_RE.sub("'1,5p'", seg)
    seg = _SED_LINE_RE.sub("'5p'", seg)
    seg = _LOCALHOST_RE.sub("http://localhost:3000/", seg)
    seg = _URL_RE.sub(lambda m: m.group(0) if "localhost:3000" in m.group(0) else "https://example.com/path", seg)
    seg = _UUID_RE.sub("<uuid>", seg)
    seg = _HASH_RE.sub("abc1234", seg)
    seg = _PATH_RE.sub(_placeholder_path, seg)
    seg = _QUOTED_RE.sub(lambda m: m.group(0) if m.group(0)[1:-1] in ("pattern", "1,5p", "5p", "EOF") else "'pattern'", seg)
    seg = _COUNT_FLAG_RE.sub(lambda m: m.group(1) + "20", seg)
    seg = re.sub(r":\d{4,5}\b", ":3000", seg)  # bare ports (e.g. --port 5174)
    seg = re.sub(r"\bsleep \d+\b", "sleep 2", seg)
    seg = re.sub(r"\s+", " ", seg).strip()
    return seg


# Segments that carry no reusable signal on their own.
_NOISE_HEADS = {"echo", "true", "exit", "#"}


_HEAD_OK_RE = re.compile(r"^[A-Za-z_./~]")


def normalize_command(command: str) -> list:
    """Raw bash command -> list of normalized pattern strings."""
    # Collapse heredoc bodies before splitting, or their lines become bogus segments.
    command = _HEREDOC_RE.sub("<<'EOF' ... EOF", command)
    patterns = []
    for seg in split_segments(command):
        head = seg.split(None, 1)[0] if seg.split() else ""
        if head in _NOISE_HEADS or head.startswith("#") or head == "EOF" or not _HEAD_OK_RE.match(head):
            continue
        norm = normalize_segment(seg)
        if norm and len(norm) <= 200:  # over-long one-offs are not patterns
            patterns.append(norm)
    return patterns


NORMALIZATION_DOC = """\
# cskill normalization rules

Raw bash commands from session logs are normalized into stable patterns before
aggregation, so two commands doing the same thing with different arguments
count as one pattern. Rules were derived from real collected data.

## Splitting

Compound commands are split on top-level `&&`, `;`, and newlines. Pipelines
(`|`, `||`) are kept intact — `cmd | head -20` is a meaningful pattern.
Pure `echo` segments and comments are dropped as noise.

## Placeholders

| Class of value          | Placeholder                |
|-------------------------|----------------------------|
| File path               | `some/path/file.<ext>`     |
| Directory path          | `some/path/dir`            |
| Glob path               | `some/path/*.<ext>`        |
| Quoted string / pattern | `'pattern'`                |
| sed line range          | `'1,5p'`                   |
| Count flags (`-n N`, `head -N`, `-A/-B/-C N`) | `20`  |
| Port number             | `3000`                     |
| Localhost URL           | `http://localhost:3000/`   |
| Other URL               | `https://example.com/path` |
| Git commit hash         | `abc1234`                  |
| UUID                    | `<uuid>`                   |
| Heredoc body            | `<<'EOF' ... EOF`          |

Well-known filenames (`package.json`, `README.md`, `tsconfig.json`, ...) are
kept verbatim, since reading them is a distinct pattern from reading an
arbitrary file. Leading environment-variable assignments are stripped.
`chmod` modes and shell redirections (`2>&1`, `2>/dev/null`) are preserved —
they are part of the pattern's meaning.
"""
