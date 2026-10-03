from __future__ import annotations

import hashlib
import os
import platform
import statistics
import time

from .common import Error, generated_path, git, json_text, project, run, write


def benchmark(root, before, after, *, rounds=6, timeout=180, compare_output=False, output="bench/results/comparison.json", force=False):
    root, config = project(root)
    if rounds < 2 or rounds % 2:
        raise Error("use an even number of at least two rounds for balanced run order")
    if not all(isinstance(cmd, list) and cmd and all(isinstance(arg, str) for arg in cmd) for cmd in [before, after]):
        raise Error("benchmark commands must be nonempty argv arrays")
    results = {"before": [], "after": []}
    hashes = set()
    for number in range(rounds + 1):
        order = ["before", "after"] if number % 2 == 0 else ["after", "before"]
        for side in order:
            started = time.perf_counter()
            stdout = run(before if side == "before" else after, cwd=root, timeout=timeout)
            seconds = time.perf_counter() - started
            digest = hashlib.sha256(stdout).hexdigest()
            hashes.add(digest)
            if number:
                results[side].append({"seconds": seconds, "stdout_sha256": digest, "pair": number, "order": order})
    if compare_output and len(hashes) != 1:
        raise Error("benchmark stdout differs; no speedup result was accepted")
    try:
        revision = git(root, "rev-parse", "HEAD")
        dirty = bool(git(root, "status", "--porcelain"))
    except Error:
        revision, dirty = None, True
    value = {"version": 1, "kind": "process-benchmark", "reference_sha": config["project"]["reference_sha"],
             "candidate_revision": revision, "candidate_dirty": dirty, "machine": platform.platform(),
             "cpu_count": os.cpu_count(), "commands": {"before": before, "after": after},
             "warmup_pairs": 1, "rounds": results,
             "median_seconds": {side: statistics.median(row["seconds"] for row in rows) for side, rows in results.items()},
             "output_checked": compare_output,
             "limits": "Whole-process wall time, not HTTP throughput, latency, CPU cost, socket capacity or deployment readiness."}
    write(generated_path(root, output), json_text(value), force=force)
    return value
