"""Install the skill file into the Claude Code skill location.

Convention (from the kronny reference): user skills live at
~/.claude/skills/<name>/SKILL.md with YAML frontmatter. Path and filename are
config-driven.
"""

from cskill import cache as cache_mod
from cskill import config as config_mod
from cskill.generator import generate_skill_file
from cskill.registry import check_update
from cskill.utils import atomic_write_text


def write_skill(cfg: dict) -> str:
    """Regenerate the skill file from the cache; returns the install path."""
    cache_root = config_mod.cache_dir(cfg)
    totals = cache_mod.aggregate(cache_root)
    sessions = cache_mod.cached_session_count(cache_root)
    path = config_mod.skill_path(cfg)
    atomic_write_text(path, generate_skill_file(totals, cfg, sessions))
    return str(path)


def install(cfg: dict) -> int:
    path = config_mod.skill_path(cfg)
    already = path.exists()
    installed_path = write_skill(cfg)
    if already:
        print("Skill already installed — refreshed from cache.")
        print(check_update(cfg["package_name"]))
    print(f"Installed: {installed_path}")
    totals = cache_mod.aggregate(config_mod.cache_dir(cfg))
    if not totals:
        print("Cache is empty — run `cskill run` to collect patterns.")
    return 0
