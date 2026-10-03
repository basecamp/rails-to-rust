from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import re

from .common import Error, git

CATEGORIES = {
    "controllers": "app/controllers", "models": "app/models", "views": "app/views",
    "helpers": "app/helpers", "jobs": "app/jobs", "channels": "app/channels",
    "mailers": "app/mailers", "services": "app/services", "lib": "lib",
    "frontend": "app/javascript", "assets": "app/assets", "plugins": "vendor/plugins",
}
HINTS = {
    "callbacks": r"\b(?:before|after|around)_(?:save|create|update|destroy|commit|rollback|validation)\b",
    "controller_filters": r"\b(?:before_filter|before_action|around_filter|around_action|skip_before_action|skip_before_filter)\b",
    "transactions": r"\btransaction\b", "external_work": r"\b(?:deliver|deliver_later|perform_later|enqueue|Resque|Sidekiq)\b",
    "sessions": r"\b(?:session|cookies|MessageVerifier|MessageEncryptor|CookieStore)\b",
    "storage": r"\b(?:has_one_attached|has_many_attached|ActiveStorage|Paperclip|S3|attachment_fu)\b",
}


def inspect(source):
    source = Path(source).resolve()
    if not (source / "config/routes.rb").is_file():
        raise Error(f"{source} is not a Rails app: config/routes.rb is missing")
    try:
        sha = git(source, "rev-parse", "HEAD")
        dirty = bool(git(source, "status", "--porcelain", "--untracked-files=no"))
    except Error:
        sha, dirty = None, None
    files, hints, counts, formats = [], [], Counter(), Counter()
    for category, directory in CATEGORIES.items():
        for path in sorted((source / directory).rglob("*")):
            if not path.is_file() or not path.resolve().is_relative_to(source):
                continue
            data = path.read_bytes()
            relative = path.relative_to(source).as_posix()
            files.append({"path": relative, "category": category, "bytes": len(data),
                          "lines": len(data.splitlines()), "sha256": hashlib.sha256(data).hexdigest()})
            counts[category] += 1
            if category == "views":
                formats[path.suffix or "extensionless"] += 1
            if path.suffix == ".rb":
                for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
                    for kind, pattern in HINTS.items():
                        if re.search(pattern, line):
                            hints.append({"kind": kind, "path": relative, "line": number})
    lock = (source / "Gemfile.lock").read_text() if (source / "Gemfile.lock").exists() else ""
    rails = re.search(r"^    rails \(([^)]+)\)", lock, re.M)
    ruby = (source / ".ruby-version").read_text().strip() if (source / ".ruby-version").exists() else None
    database = (source / "config/database.yml").read_text() if (source / "config/database.yml").exists() else ""
    adapters = sorted(set(re.findall(r"^\s*adapter:\s*[\"']?([a-zA-Z0-9_]+)", database, re.M)))
    encodings = sorted(set(re.findall(r"^\s*encoding:\s*[\"']?([a-zA-Z0-9_-]+)", database, re.M)))
    return {"version": 1, "kind": "source-inventory", "reference_sha": sha, "tracked_changes": dirty,
            "ruby_version": ruby, "rails_version": rails.group(1) if rails else None,
            "database_adapters": adapters, "database_encodings": encodings,
            "counts": dict(sorted(counts.items())), "view_formats": dict(sorted(formats.items())),
            "files": files, "review_hints": hints,
            "limits": ["Static hints are not runtime behavior or route coverage.",
                       "Database ERB, environment overrides, engines and loaded gems need a running oracle."]}


def summary(data):
    counts = "\n".join(f"| {name} | {count} |" for name, count in data["counts"].items())
    formats = ", ".join(f"{kind}: {count}" for kind, count in data["view_formats"].items()) or "none"
    return f"""# Source inventory

Reference commit: `{data['reference_sha'] or 'not a Git checkout'}`.
Ruby: `{data['ruby_version'] or 'unknown'}`. Rails: `{data['rails_version'] or 'unknown'}`.
Literal database adapters: {', '.join(data['database_adapters']) or 'unknown'}.
Literal database encodings: {', '.join(data['database_encodings']) or 'unknown'}.
View formats: {formats}.

| Area | Files |
|---|---:|
{counts}

This inventory identifies source files and review starting points. It does not prove
behavior, discover every plugin, resolve database ERB, or replace live route/schema exports.
See `inventory.json` for file hashes and callback/filter/session/storage review locations.
"""
