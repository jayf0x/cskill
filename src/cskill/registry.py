"""NPM registry version check (stdlib only)."""

import json
import urllib.error
import urllib.parse
import urllib.request

from cskill import __version__

REGISTRY = "https://registry.npmjs.org"


def latest_version(package_name: str, timeout: float = 5.0):
    """Latest published version string, or None if unreachable/unpublished."""
    url = f"{REGISTRY}/{urllib.parse.quote(package_name, safe='@')}/latest"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.load(resp).get("version")
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def _ver_tuple(v: str):
    parts = []
    for piece in v.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_update(package_name: str) -> str:
    """Human-readable update status."""
    latest = latest_version(package_name)
    current = __version__
    if latest is None:
        return f"cskill {current} — could not reach the NPM registry (or package not published yet)."
    if _ver_tuple(latest) > _ver_tuple(current):
        return (
            f"cskill {current} — newer version {latest} available.\n"
            f"Upgrade: npm install -g {package_name}@latest"
        )
    return f"cskill {current} — up to date (latest: {latest})."
