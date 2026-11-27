"""Load a project-local .env file without overriding the parent process environment."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import MutableMapping

_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_env_file(path: str | Path, environ: MutableMapping[str, str] | None = None) -> int:
    """Load KEY=VALUE entries; existing process environment values always win.

    This supports a small, predictable dotenv subset using only the standard
    library. Values may be single- or double-quoted. No interpolation or
    command substitution is performed.
    """
    target = Path(path)
    if not target.is_file():
        return 0

    destination = os.environ if environ is None else environ
    loaded = 0
    try:
        lines = target.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise ValueError(f"Could not read environment file: {target}") from exc

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"Invalid .env entry on line {line_number}: expected KEY=VALUE")

        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not _ENV_NAME.fullmatch(name):
            raise ValueError(f"Invalid .env variable name on line {line_number}")

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()

        if name not in destination:
            destination[name] = value
            loaded += 1
    return loaded


__all__ = ["load_env_file"]
