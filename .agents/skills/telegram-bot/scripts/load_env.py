"""Load variables from a .env file in the project root.

Existing shell environment variables take precedence (never overwritten).
"""

from __future__ import annotations

import os
from pathlib import Path


def find_env_file(start: Path | None = None) -> Path | None:
    """Walk up from start (default: cwd) looking for a .env file."""
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


def load_env(*, start: Path | None = None) -> Path | None:
    """Load key=value pairs from .env into os.environ. Returns the path loaded."""
    env_path = find_env_file(start)
    if env_path is None:
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value

    return env_path
