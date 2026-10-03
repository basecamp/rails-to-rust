from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .common import Error, command, generated_path, json_text, load_json, project, run, write


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, newurl):
        return None


def cases_from(path):
    envelope = load_json(path)
    cases = envelope.get("cases")
    if envelope.get("version") != 1 or not isinstance(cases, list) or not cases:
        raise Error("parity inventory must contain a nonempty version-1 cases list")
    seen = set()
    for case in cases:
        if not isinstance(case.get("id"), str) or not case["id"] or case["id"] in seen:
            raise Error("parity cases require unique nonempty IDs")
        seen.add(case["id"])
        path = case.get("path", "")
        if not path.startswith("/") or path.startswith("//") or urlsplit(path).scheme:
            raise Error(f"{case['id']}: path must be relative to the configured server")
        status = case.get("expected_status")
        if not isinstance(status, int) or isinstance(status, bool) or not 100 <= status <= 599:
            raise Error(f"{case['id']}: an explicit expected_status is required")
        if case.get("comparison", "bytes") not in {"bytes", "text", "json"}:
            raise Error(f"{case['id']}: comparison must be bytes, text or json")
        if case.get("comparison", "bytes") == "bytes" and case.get("normalizations"):
            raise Error("normalizations require an explicit text or json comparison")
        for mask in case.get("normalizations", []):
            if not mask.get("reason", "").strip() or not mask.get("pattern") or "replacement" not in mask:
                raise Error("each normalization needs a pattern, replacement and documented reason")
            try:
                re.compile(mask["pattern"])
            except re.error as error:
                raise Error(f"invalid normalization: {error}") from error
    return cases


def request(base, case, timeout):
    headers = dict(case.get("headers", {}))
    if case.get("cookie_env"):
        cookie = os.environ.get(case["cookie_env"])
        if not cookie:
            raise Error(f"{case['id']}: missing cookie environment variable {case['cookie_env']}")
        headers["Cookie"] = cookie
    body = case.get("body")
    if body is not None and not isinstance(body, str):
        raise Error("request body must be a string; set Content-Type explicitly")
    method = case.get("method", "GET").upper()
    query = Request(base.rstrip("/") + case["path"], data=body.encode() if body is not None else None,
                    headers=headers, method=method)
    try:
        response = build_opener(NoRedirects).open(query, timeout=timeout)
    except HTTPError as error:
        response = error  # 302/404/422 bodies and headers are part of the contract too.
    except (URLError, OSError) as error:
        raise Error(f"{case['id']}: transport failed: {type(error).__name__}") from error
    with response:
        limit = case.get("max_body_bytes", 2 * 1024 * 1024)
        data = response.read(limit + 1)
        if len(data) > limit:
            raise Error(f"{case['id']}: response exceeds max_body_bytes; no truncated comparison was accepted")
        selected = case.get("compare_headers", ["content-type", "location", "cache-control", "vary"])
        return {"status": response.code, "headers": {key.lower(): response.headers.get_all(key) for key in selected},
                "body": data}


def normalized(data, case):
    comparison = case.get("comparison", "bytes")
    if comparison == "bytes":
        return data
    try:
        text = data.decode(case.get("encoding", "utf-8"))
        for rule in case.get("normalizations", []):
            text = re.sub(rule["pattern"], rule["replacement"], text)
        return json.loads(text) if comparison == "json" else text
    except (UnicodeError, ValueError, LookupError) as error:
        raise Error(f"{case['id']}: response cannot be decoded as {comparison}") from error


def mutating(case):
    return case.get("mutates", False) or case.get("method", "GET").upper() not in {"GET", "HEAD", "OPTIONS"}


def compare(root, *, output="parity/results/http.json", force=False):
    root, config = project(root)
    settings = config["parity"]
    cases = cases_from(generated_path(root, settings["cases"]))
    for key in ["reference_url", "candidate_url"]:
        url = urlsplit(settings[key])
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise Error(f"{key} must be an HTTP(S) base URL without credentials, query or fragment")
    results = []
    for case in cases:
        responses = {}
        for side in ["reference", "candidate"]:
            if mutating(case):
                argv = command(settings.get("reset_command"), side=side, project=str(root), reference=str(root / "reference"))
                run(argv, cwd=root, timeout=180)
            responses[side] = request(settings[side + "_url"], case, settings.get("timeout_seconds", 15))
        left, right = responses["reference"], responses["candidate"]
        problems = []
        for side, response in responses.items():
            if response["status"] != case["expected_status"]:
                problems.append(f"{side} status {response['status']}, expected {case['expected_status']}")
        if left["headers"] != right["headers"]:
            problems.append("selected response headers differ")
        if normalized(left["body"], case) != normalized(right["body"], case):
            problems.append("response bodies differ")
        results.append({"id": case["id"], "passed": not problems, "problems": problems,
                        "status": {side: response["status"] for side, response in responses.items()},
                        "body_sha256": {side: hashlib.sha256(response["body"]).hexdigest() for side, response in responses.items()},
                        "normalizations": case.get("normalizations", [])})
    value = {"version": 1, "kind": "http-parity", "reference_sha": config["project"]["reference_sha"],
             "passed": all(result["passed"] for result in results), "cases": results,
             "limits": "HTTP evidence only; browser interaction, persisted mutation state, realtime and rollback require separate checks."}
    write(generated_path(root, output), json_text(value), force=force)
    return value


def mutation_diff(root, *, output="parity/results/mutation.json", force=False):
    root, config = project(root)
    settings = config.get("mutations", {})
    commands = mutation_commands(root, config)
    before, after = {}, {}
    for side in ["reference", "candidate"]:
        argv = commands[side]
        run(argv["reset_command"], cwd=root, timeout=180)
        before[side] = snapshot(root, argv["snapshot_command"])
    if before["reference"] != before["candidate"]:
        raise Error("mutation baseline states differ; neither action was run")
    for side in ["reference", "candidate"]:
        argv = commands[side]
        run(argv[side + "_command"], cwd=root, timeout=settings.get("timeout_seconds", 180))
        after[side] = snapshot(root, argv["snapshot_command"])
    changed = {side: after[side] != before[side] for side in ["reference", "candidate"]}
    problems = []
    if after["reference"] != after["candidate"]:
        problems.append("post-mutation states differ")
    if settings.get("expect_change", True):
        problems.extend(f"{side} action produced no observed state change" for side, observed in changed.items() if not observed)
    passed = not problems
    value = {"version": 1, "kind": "mutation-parity", "reference_sha": config["project"]["reference_sha"],
             "passed": passed, "baseline_equal": True, "changed": changed, "problems": problems,
             "state_sha256": {side: hashlib.sha256(json_text(state).encode()).hexdigest() for side, state in after.items()}}
    write(generated_path(root, output), json_text(value), force=force)
    return value


def mutation_commands(root, config):
    # Validate the complete protocol before executing any reset or mutation.
    settings = config.get("mutations", {})
    commands = {}
    for side in ["reference", "candidate"]:
        commands[side] = {key: command(settings.get(key), side=side, project=str(root), reference=str(root / "reference"))
                          for key in ["reset_command", "snapshot_command", side + "_command"]}
    return commands


def snapshot(root, argv):
    try:
        value = json.loads(run(argv, cwd=root, timeout=180))
    except ValueError as error:
        raise Error("snapshot_command must emit deterministic JSON, including rows and captured side effects") from error
    if not isinstance(value, dict) or not value:
        raise Error("snapshots must be nonempty JSON objects naming the observed state")
    return value
