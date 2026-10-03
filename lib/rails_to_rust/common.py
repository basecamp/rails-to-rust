from __future__ import annotations

import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import tomllib

KIT = Path(__file__).resolve().parents[2]
BEGIN = "--- RAILS_TO_RUST_JSON_BEGIN ---"
END = "--- RAILS_TO_RUST_JSON_END ---"


class Error(Exception):
    pass


def run(argv, *, cwd=None, env=None, timeout=60):
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Error(f"could not run {argv[0]}: {error}") from error
    if result.returncode:
        # Reference boot logs can contain credentials. Do not print their contents.
        raise Error(f"{argv[0]} exited with status {result.returncode}")
    return result.stdout


def git(root, *args):
    return run(["git", "-C", str(root), *args]).decode().strip()


def json_text(value):
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def write(path, content, *, force=False):
    path = Path(path)
    data = content.encode() if isinstance(content, str) else content
    if path.exists():
        if path.read_bytes() == data:
            return
        if not force:
            raise Error(f"{path} exists with different contents; use --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep scratch files beside their destination, including when /tmp is quota limited.
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        file.write(data)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def project(root):
    root = Path(root).resolve()
    try:
        config = tomllib.loads((root / "migration.toml").read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise Error(f"invalid migration.toml in {root}: {error}") from error
    if config.get("version") != 1:
        raise Error("unsupported migration.toml version")
    return root, config


def inside(root, relative):
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise Error(f"path escapes project: {relative}")
    return candidate


def generated_path(root, relative):
    candidate = inside(root, relative)
    if candidate.is_relative_to((root / "reference").resolve()):
        raise Error("generators must not modify reference/")
    return candidate


def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise Error(f"invalid JSON in {path}: {error}") from error


def command(template, **values):
    if not isinstance(template, list) or not template or not all(isinstance(arg, str) for arg in template):
        raise Error("configure a nonempty command array in migration.toml; no shell or runtime fallback is used")
    def replace(match):
        name = match.group(1)
        if name not in values:
            raise Error(f"unknown command placeholder: {name}")
        return values[name]
    return [re.sub(r"\{([A-Za-z_]\w*)\}", replace, arg) for arg in template]
