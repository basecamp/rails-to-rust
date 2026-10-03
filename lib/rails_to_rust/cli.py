from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .common import Error, json_text, write


def parser():
    p = argparse.ArgumentParser(prog="rails-to-rust", description="Agent tooling for evidence-driven Rails to Rust ports")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--project", default=".", help="port root containing migration.toml")
    commands = p.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="create a Rust port with a pinned Rails submodule and local skills")
    initialize.add_argument("source", help="local Git checkout of the Rails app")
    initialize.add_argument("destination")
    initialize.add_argument("--name")
    initialize.add_argument("--rust-version", default="1.98.1")
    inventory = commands.add_parser("inspect", help="inventory source files without booting or changing Rails")
    inventory.add_argument("source")
    inventory.add_argument("--output", help="save JSON instead of printing it")
    inventory.add_argument("--force", action="store_true")
    oracle = commands.add_parser("oracle", help="capture live Rails contracts through the configured reference runner")
    oracle.add_argument("kind", nargs="?", default="runtime")
    oracle.add_argument("--script", help="custom framed-JSON Ruby oracle script")
    oracle.add_argument("--output")
    oracle.add_argument("--force", action="store_true")
    generate = commands.add_parser("generate", help="generate Rust code from reference-produced contracts")
    generators = generate.add_subparsers(dest="generator", required=True)
    for name, source, output in [("records", "vectors/schema.json", "crates/db/src/generated.rs"),
                                  ("routes", "vectors/routes.json", "crates/routes/src/generated.rs")]:
        child = generators.add_parser(name)
        child.add_argument("--from", dest="source", default=source)
        child.add_argument("--output", default=output)
        child.add_argument("--force", action="store_true")
        if name == "records":
            child.add_argument("--table", dest="tables", action="append", help="select an application table; repeat for multiple tables")
    test = generators.add_parser("contract-test", help="generate a deliberately failing test adapter for input/expected vectors")
    test.add_argument("kind")
    test.add_argument("--from", dest="source", required=True)
    test.add_argument("--output", required=True)
    test.add_argument("--force", action="store_true")
    for name, default in [("parity", "parity/results/http.json"), ("mutation-diff", "parity/results/mutation.json"),
                          ("verify", "parity/results/verification.json")]:
        child = commands.add_parser(name)
        child.add_argument("--output", default=default)
        child.add_argument("--force", action="store_true")
        if name == "verify":
            child.add_argument("--partial", action="store_true", help="verify completed slices while other contracts remain unfinished")
    commands.add_parser("doctor", help="report missing configuration and compatibility evidence")
    bench = commands.add_parser("benchmark", help="compare whole-process wall time with balanced alternating runs")
    bench.add_argument("--before", required=True, help="JSON argv array for baseline command")
    bench.add_argument("--after", required=True, help="JSON argv array for candidate command")
    bench.add_argument("--rounds", type=int, default=6)
    bench.add_argument("--timeout", type=int, default=180)
    bench.add_argument("--compare-output", action="store_true")
    bench.add_argument("--output", default="bench/results/comparison.json")
    bench.add_argument("--force", action="store_true")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            from .project import initialize
            value = initialize(args.source, args.destination, name=args.name, rust_version=args.rust_version)
        elif args.command == "inspect":
            from .inventory import inspect
            value = inspect(args.source)
            if args.output:
                write(Path(args.output), json_text(value), force=args.force)
                value = {"output": str(Path(args.output)), "counts": value["counts"], "reference_sha": value["reference_sha"]}
        elif args.command == "oracle":
            from .oracle import capture
            value = capture(args.project, args.kind, force=args.force, script=args.script, output=args.output)
        elif args.command == "generate":
            from . import generate
            if args.generator == "contract-test":
                value = generate.contract_test(args.project, args.kind, args.source, args.output, force=args.force)
            elif args.generator == "records":
                value = generate.records(args.project, args.source, args.output, force=args.force, tables=args.tables)
            else:
                value = generate.routes(args.project, args.source, args.output, force=args.force)
        elif args.command in {"parity", "mutation-diff"}:
            from .parity import compare, mutation_diff
            value = (compare if args.command == "parity" else mutation_diff)(args.project, output=args.output, force=args.force)
        elif args.command in {"doctor", "verify"}:
            from .checks import doctor, verify
            value = doctor(args.project) if args.command == "doctor" else verify(args.project, output=args.output, force=args.force, partial=args.partial)
        else:
            from .benchmark import benchmark
            value = benchmark(args.project, json.loads(args.before), json.loads(args.after), rounds=args.rounds,
                              timeout=args.timeout, compare_output=args.compare_output, output=args.output, force=args.force)
        print(json_text(value), end="")
        return 1 if value.get("passed") is False or value.get("ready") is False else 0
    except (Error, ValueError, KeyError, TypeError, OSError) as error:
        print(f"rails-to-rust: {error}", file=sys.stderr)
        return 2
