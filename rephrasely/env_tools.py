"""Helpers for loading and persisting environment variables from YAML."""

from __future__ import annotations

import os
import platform
import re
import subprocess
from pathlib import Path

import yaml


def load_env_from_yaml(yaml_path: str | os.PathLike) -> dict[str, str]:
    """Load a flat mapping of environment variables from a YAML file."""
    path = Path(yaml_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping of KEY: VALUE")

    env_vars = {str(key): "" if value is None else str(value) for key, value in data.items()}
    invalid_keys = [key for key in env_vars if not re.fullmatch(r"[A-Z0-9_]+", key)]
    if invalid_keys:
        raise ValueError(f"Invalid env var names: {invalid_keys}")

    return env_vars


def set_env_variables(env_vars: dict[str, str], persist: bool = True) -> None:
    """Set environment variables for the current process and optionally persist them."""
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"Set {key} (in-process)")

        if not persist:
            continue

        if platform.system() == "Windows":
            subprocess.run(["setx", key, value], capture_output=True, text=True, shell=True, check=True)
            print(f"Persisted {key} via setx")
        else:
            rc_path = _detect_shell_rc()
            _ensure_export_line(rc_path, key, value)
            print(f'Persisted {key} in "{rc_path}"')


def write_env_file(env_vars: dict[str, str], path: str | os.PathLike) -> None:
    """Write environment variables to a KEY=VALUE file."""
    env_path = Path(path).expanduser().resolve()
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(f"{key}={value}" for key, value in env_vars.items()) + "\n", encoding="utf-8")
    env_path.chmod(0o600)
    print(f"Environment file written to {env_path}")


def _detect_shell_rc() -> Path:
    """Return the most likely shell startup file for persistent exports."""
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if "zsh" in shell:
        return home / ".zshrc"
    if "bash" in shell:
        return home / ".bashrc"
    return home / ".profile"


def _ensure_export_line(rc_path: Path, key: str, value: str) -> None:
    """Insert or replace a shell export line in a startup file."""
    rc_path.touch(exist_ok=True)
    content = rc_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^export\s+{re.escape(key)}=.*$", re.MULTILINE)
    new_line = f'export {key}="{value}"'

    if pattern.search(content):
        content = pattern.sub(new_line, content)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += new_line + "\n"

    rc_path.write_text(content, encoding="utf-8")
