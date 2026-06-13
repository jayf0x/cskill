"""CLI entry point: subcommand dispatch via argparse."""

import argparse
import subprocess
import sys

from cskill import __version__
from cskill import config as config_mod
from cskill.collector import collect
from cskill.installer import install, write_skill
from cskill.registry import check_update


def cmd_run(cfg: dict, args) -> int:
    projects_root = config_mod.projects_dir(cfg)
    if not projects_root.is_dir():
        print(f"No Claude Code session data found at {projects_root}", file=sys.stderr)
        return 1
    cache_root = config_mod.cache_dir(cfg)

    summary = collect(cfg, projects_root, cache_root)
    print(f"Sessions parsed: {summary['parsed']} (skipped {summary['skipped']} cached)")
    print(f"Commands extracted: {summary['new_commands']} new | "
          f"unique patterns: {summary['unique_patterns']}")
    print("\nTop 10 patterns:")
    for pattern, count in summary["top"]:
        print(f"  {count:>4}x  {pattern}")

    if not args.yes:
        try:
            answer = input("\nApply to skill? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if answer not in ("y", "yes"):
            print("Skipped. Run `cskill apply` later to write the skill file.")
            return 0
    return cmd_apply(cfg, args)


def cmd_apply(cfg: dict, _args) -> int:
    path = write_skill(cfg)
    print(f"Skill written: {path}")
    return 0


def cmd_install(cfg: dict, _args) -> int:
    return install(cfg)


def cmd_update(cfg: dict, _args) -> int:
    print(check_update(cfg["package_name"]))
    return 0


def cmd_show(cfg: dict, _args) -> int:
    cache_root = config_mod.cache_dir(cfg)
    print(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["open", str(cache_root)], check=False)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cskill",
        description="Mine bash command patterns from Claude Code sessions into a skill cheatsheet.",
    )
    parser.add_argument("--version", action="version", version=f"cskill {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="collect patterns, then optionally apply to the skill")
    p_run.add_argument("-y", "--yes", action="store_true", help="apply without prompting")
    p_run.set_defaults(func=cmd_run)

    sub.add_parser("apply", help="regenerate the skill file from the existing cache").set_defaults(func=cmd_apply)
    sub.add_parser("install", help="install the skill file into the Claude Code skill location").set_defaults(func=cmd_install)
    sub.add_parser("update", help="check the NPM registry for a newer version").set_defaults(func=cmd_update)
    sub.add_parser("show", help="print and open the cache directory").set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    cfg = config_mod.load_config()
    return args.func(cfg, args)
