# cskill

> 🚧 DEPRICATED 🚧 : Now became a skill [https://github.com/jayf0x/claude-skills/tree/main/plugins/local-commands](https://github.com/jayf0x/claude-skills/tree/main/plugins/local-commands).

Mines bash command patterns from your local Claude Code session data and
maintains a markdown cheatsheet skill, so Claude Code agents stop
rediscovering the same shell patterns in every session.

macOS only. Requires Node 18+ and Python 3.9+ (stdlib only — no Python deps).

## Install

```bash
npm install -g @jayf0x/cskill
cskill install   # writes the skill file to ~/.claude/skills/cskill/SKILL.md
cskill run       # collect patterns and apply them
```

## Quickstart

```bash
cskill run        # parse ~/.claude/projects, show top patterns, prompt to apply
cskill run -y     # same, no prompt
cskill apply      # regenerate the skill file from cache (no collection)
cskill install    # (re)install the skill; checks NPM for updates if present
cskill update     # current vs latest published version
cskill show       # print + open the cache directory
```

## What it does

```
~/.claude/projects/*.jsonl        Claude Code session logs
        ↓ collect                 extract Bash tool calls, normalize, cache
~/.cache/cskill/                  one JSON per session + index (incremental)
        ↓ apply                   aggregate, categorize, generate markdown
~/.claude/skills/cskill/SKILL.md  the cheatsheet skill Claude Code loads
```

Commands are normalized before counting — `sed -n '42,87p' src/Button.tsx`
and `sed -n '10,30p' lib/utils.py` both become `sed -n '1,5p'
some/path/file.<ext>` and count as one pattern. Full rules in
`~/.cache/cskill/normalization.md` (generated on collect).

## Config

Created on first run at `~/.config/cskill/config.json`:

| Key | Default | Meaning |
|---|---|---|
| `projects_dir` | `~/.claude/projects` | session data location |
| `cache_dir` | `~/.cache/cskill` | local cache |
| `skill_dir` | `~/.claude/skills/cskill` | skill install directory |
| `skill_filename` | `SKILL.md` | skill file name |
| `min_frequency` | `3` | drop patterns seen fewer times |
| `max_patterns` | `50` | cap on emitted patterns |
| `package_name` | `@jayf0x/cskill` | used for update checks |

## Design decisions

- **Node is a pass-through.** `bin/cskill.js` finds `python3`, sets
  `PYTHONPATH` to the bundled `src/`, injects the package version via
  `CSKILL_VERSION`, and forwards args + exit code. All logic is Python.
- **Skill file is `SKILL.md` with YAML frontmatter**, not a bare `cskill.md` —
  that's the convention Claude Code actually discovers under
  `~/.claude/skills/<name>/SKILL.md`. The location is config-driven.
- **Sessions are keyed by path relative to `projects_dir`** (sanitized), not
  by bare session ID, so subagent JSONL files and same-ID files in different
  projects can't collide. Incremental collection skips files whose
  mtime+size are unchanged.
- **Compound commands are split** on top-level `&&`/`;`/newlines; pipelines
  stay intact because `cmd | head -20` is itself a pattern. Heredoc bodies
  are collapsed first. Pure `echo` segments and comments are dropped.
- **All cache and skill writes are atomic** (`.tmp` + rename).
- **No publish tooling included** — `npm publish` from a clean checkout is
  the release process; `files` whitelists `bin`, `src`, `README.md`, `LICENSE`.

## License

[MIT](LICENSE)
