from __future__ import annotations

from pathlib import Path
import re
import shutil

from .common import Error, KIT, git, json_text, run, write
from .inventory import inspect, summary

CONTRACTS = {
    "sessions": "Cookies, signing, encryption, CSRF, authentication and old browser tabs",
    "routing": "Ordered recognition, URL generation, verbs, formats and nested params",
    "data": "Schema, encodings, nullability, typecasting and bidirectional writes",
    "mutations": "Callbacks, transactions, cancellation, outbox and post-commit effects",
    "views": "Templates, helper escaping, frontend assets and browser interactions",
    "storage": "Existing keys, checksums, signatures, variants, ranges and downloads",
    "jobs": "Claims, retry, schedules, shutdown, mail and external integrations",
    "realtime": "Cable or polling, authorization, revocation and unique-user fanout",
    "operations": "Environment, readiness, deployment, metrics and rollback rehearsal",
}


def initialize(source, destination, *, name=None, rust_version="1.98.1"):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    inspect(source)  # Validate before creating anything.
    sha = git(source, "rev-parse", "HEAD")
    if destination.is_relative_to(source):
        raise Error("create the port outside the Rails source checkout")
    if destination.exists() and any(destination.iterdir()):
        raise Error("destination must be absent or empty")
    name = name or destination.name.removesuffix("-rust").replace("-", "_").lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise Error("--name must be a lowercase Rust package name using letters, digits and underscores")
    if not re.fullmatch(r"\d+\.\d+\.\d+", rust_version):
        raise Error("--rust-version must be an exact version")
    destination.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-b", "main", str(destination)])
    run(["git", "-c", "protocol.file.allow=always", "submodule", "add", str(source), "reference"], cwd=destination)
    run(["git", "checkout", "--detach", sha], cwd=destination / "reference")
    run(["git", "add", "reference"], cwd=destination)
    try:
        remote = git(source, "remote", "get-url", "origin")
    except Error:
        remote = None
    if remote and not re.search(r"https?://[^/]*@", remote):
        # Clone locally for speed; keep a portable upstream URL when one is known.
        run(["git", "config", "-f", ".gitmodules", "submodule.reference.url", remote], cwd=destination)
        run(["git", "-C", str(destination / "reference"), "remote", "set-url", "origin", remote])
        run(["git", "add", ".gitmodules"], cwd=destination)
    for template in sorted((KIT / "templates/project").rglob("*")):
        if template.is_file():
            relative = template.relative_to(KIT / "templates/project")
            text = template.read_text().replace("@@NAME@@", name).replace("@@SHA@@", sha).replace("@@RUST@@", rust_version)
            write(destination / relative, text)
    # The generated port owns its tools; it does not depend on this toolkit checkout.
    tool = destination / "tools/rails-to-rust"
    for directory in ["bin", "lib", "templates", "skills"]:
        shutil.copytree(KIT / directory, tool / directory, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(KIT / "skills", destination / ".agents/skills")
    for script in [tool / "bin/rails-to-rust", destination / "bin/rails-to-rust"]:
        script.chmod(0o755)
    (destination / "reference-tools").mkdir(exist_ok=True)
    for path in (KIT / "templates/reference-tools").glob("*.rb"):
        shutil.copy2(path, destination / "reference-tools" / path.name)
    inventory = inspect(destination / "reference")
    write(destination / "plans/inventory.json", json_text(inventory))
    write(destination / "plans/inventory.md", summary(inventory))
    write(destination / "plans/contracts.json", json_text({"version": 1, "reference_sha": sha,
          "contracts": [{"id": key, "description": description, "status": "pending", "evidence": []}
                        for key, description in CONTRACTS.items()]}))
    return {"project": str(destination), "name": name, "reference_sha": sha,
            "next": "Read AGENTS.md, configure the isolated reference runner in migration.toml, then use $rails-to-rust."}
