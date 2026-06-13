"""Config file at ~/.config/cskill/config.json — created with defaults on first run.

Schema (flat, all tuneables live here, nothing is hardcoded downstream):
  projects_dir    str  where Claude Code stores session JSONL files
  cache_dir       str  cskill's local cache (per-session files + index)
  skill_dir       str  directory the generated skill is installed into
  skill_filename  str  name of the skill file inside skill_dir
  min_frequency   int  patterns seen fewer times than this are dropped
  max_patterns    int  hard cap on patterns emitted into the skill file
  package_name    str  NPM package name used for update checks
"""

from pathlib import Path

from cskill.utils import atomic_write_json, expand, read_json

CONFIG_PATH = Path.home() / ".config" / "cskill" / "config.json"

DEFAULTS = {
    "projects_dir": "~/.claude/projects",
    "cache_dir": "~/.cache/cskill",
    "skill_dir": "~/.claude/skills/cskill",
    "skill_filename": "SKILL.md",
    "min_frequency": 3,
    "max_patterns": 50,
    "package_name": "@jayf0x/cskill",
}


def load_config() -> dict:
    """Load config, creating it with defaults on first run.

    Unknown keys are preserved; missing keys are filled from DEFAULTS so old
    config files keep working after upgrades.
    """
    existing = read_json(CONFIG_PATH, default=None)
    cfg = dict(DEFAULTS)
    if isinstance(existing, dict):
        cfg.update(existing)
    if existing != cfg:
        atomic_write_json(CONFIG_PATH, cfg)
    return cfg


def projects_dir(cfg: dict) -> Path:
    return expand(cfg["projects_dir"])


def cache_dir(cfg: dict) -> Path:
    return expand(cfg["cache_dir"])


def skill_path(cfg: dict) -> Path:
    return expand(cfg["skill_dir"]) / cfg["skill_filename"]
