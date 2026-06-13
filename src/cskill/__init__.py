"""cskill — mine bash command patterns from Claude Code sessions into a skill cheatsheet."""

import os

# Version is injected by the Node wrapper from package.json; the fallback is
# only used when running the Python core directly.
__version__ = os.environ.get("CSKILL_VERSION", "0.1.0")
