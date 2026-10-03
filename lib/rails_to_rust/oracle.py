from __future__ import annotations

import os

from .common import BEGIN, END, Error, command, generated_path, git, json_text, project, run, write
import json


def check_reference(root, config):
    expected = config["project"]["reference_sha"]
    reference = root / "reference"
    if git(reference, "rev-parse", "HEAD") != expected:
        raise Error("reference HEAD differs from migration.toml; repin and regenerate evidence deliberately")
    if git(reference, "status", "--porcelain"):
        raise Error("reference checkout is dirty; oracle evidence requires the unchanged pinned source")
    return expected


def capture(root, kind, *, force=False, script=None, output=None):
    root, config = project(root)
    sha = check_reference(root, config)
    settings = config["oracle"]
    script = generated_path(root, script or "reference-tools/export.rb")
    if not script.is_file():
        raise Error(f"missing oracle script: {script}")
    argv = command(settings.get("command"), project=str(root), reference=str(root / "reference"),
                   script=str(script), kind=kind, reference_sha=sha)
    env = dict(os.environ, RAILS_TO_RUST_EXPORT=kind, RAILS_TO_RUST_REFERENCE_SHA=sha)
    # Docker/compose runners must explicitly forward these variables (see docs/commands.md).
    stdout = run(argv, cwd=root / settings.get("working_directory", "reference"), env=env,
                 timeout=settings.get("timeout_seconds", 180)).decode()
    if stdout.count(BEGIN) != 1 or stdout.count(END) != 1:
        raise Error("oracle must emit exactly one framed JSON document; no fallback expectations were written")
    try:
        text = stdout.split(BEGIN, 1)[1].split(END, 1)[0]
        value = json.loads(text)
    except (ValueError, IndexError) as error:
        raise Error("oracle emitted invalid JSON") from error
    if value.get("version") != 1 or value.get("kind") != kind or value.get("reference_sha") != sha:
        raise Error("oracle provenance does not match the pinned reference and requested contract")
    runtime = value.get("runtime", {})
    if not runtime.get("ruby_version") or not runtime.get("rails_version"):
        raise Error("oracle must identify its actual Ruby and Rails runtime")
    if not value.get("data"):
        raise Error("oracle exported no cases/data; empty evidence is not a passing contract")
    check_reference(root, config)
    path = generated_path(root, output or f"vectors/{kind}.json")
    write(path, json_text(value), force=force)
    return {"output": str(path), "kind": kind, "reference_sha": sha, "runtime": runtime}


def vector(root, path, expected):
    root, config = project(root)
    from .common import load_json
    value = load_json(generated_path(root, path))
    if value.get("version") != 1 or value.get("kind") != expected:
        raise Error(f"expected a version-1 {expected} oracle envelope")
    if value.get("reference_sha") != config["project"]["reference_sha"]:
        raise Error("vector reference SHA differs from migration.toml")
    if not isinstance(value.get("data"), list) or not value["data"]:
        raise Error("oracle data must be a nonempty list")
    return root, value
