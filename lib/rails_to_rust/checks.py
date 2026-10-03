from __future__ import annotations

import shutil
from .common import Error, command, generated_path, json_text, load_json, project, run, write
from .oracle import check_reference
from .parity import cases_from, compare, mutating, mutation_commands, mutation_diff


def load_contracts(root, config):
    ledger = load_json(root / "plans/contracts.json")
    if ledger.get("reference_sha") != config["project"]["reference_sha"] or not ledger.get("contracts"):
        raise Error("contract ledger must match the pinned reference and contain contracts")
    ids = set()
    for contract in ledger["contracts"]:
        name = contract.get("id")
        if not isinstance(name, str) or not name or name in ids:
            raise Error("contract IDs must be unique and nonempty")
        ids.add(name)
        status = contract.get("status")
        if status not in {"pending", "implemented", "verified", "not-applicable"}:
            raise Error(f"{name}: invalid contract status")
        if status == "not-applicable" and not contract.get("reason", "").strip():
            raise Error(f"{name}: not-applicable requires a reason")
        if status != "verified":
            continue
        evidence = contract.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise Error(f"{name}: verified requires evidence")
        for relative in evidence:
            path = generated_path(root, relative)
            if not path.is_file():
                raise Error(f"{name}: evidence file is missing: {relative}")
            # Structured evidence must identify the pin and must not claim failure.
            # Narrative/browser artifacts still require human review of their scope.
            if path.suffix.lower() == ".json":
                value = load_json(path)
                if not isinstance(value, dict) or value.get("reference_sha") != config["project"]["reference_sha"]:
                    raise Error(f"{name}: evidence reference SHA differs: {relative}")
                for result in ["passed", "ready"]:
                    if result in value and value[result] is not True:
                        raise Error(f"{name}: evidence {result} is not true: {relative}")
    return ledger["contracts"]


def doctor(root, *, partial=False):
    root, config = project(root)
    checks = []
    def check(name, action):
        try:
            value = action()
            checks.append({"check": name, "passed": True})
            return value
        except (Error, KeyError) as error:
            checks.append({"check": name, "passed": False, "reason": str(error)})
    check("pinned, unchanged reference", lambda: check_reference(root, config))
    def runner():
        argv = command(config["oracle"].get("command"), project=str(root), reference=str(root / "reference"),
                       script=str(root / "reference-tools/export.rb"), kind="runtime", reference_sha=config["project"]["reference_sha"])
        if not shutil.which(argv[0]):
            raise Error(f"oracle executable {argv[0]} is not on PATH")
    check("configured reference runner", runner)
    cases = check("nonempty HTTP parity inventory", lambda: cases_from(generated_path(root, config["parity"]["cases"])))
    ledger = check("contract evidence ledger", lambda: load_contracts(root, config))
    if not partial:
        def complete():
            if not any(row["id"] == "mutations" for row in ledger or []):
                raise Error("ledger must include a mutations contract, verified or not-applicable with a reason")
            for contract in ledger or []:
                if contract["status"] in {"pending", "implemented"}:
                    raise Error(f"{contract['id']}: {contract['status']}, not verified")
        check("all contracts complete", complete)
        check("rollback rehearsal configured", lambda: command(config["checks"].get("rollback"), project=str(root)))
    mutations = next((row for row in ledger or [] if row["id"] == "mutations"), None)
    mutation_required = bool(config.get("mutations")) or any(mutating(case) for case in cases or [])
    if mutations and mutations["status"] != "not-applicable":
        mutation_required = mutation_required or not partial or mutations["status"] in {"implemented", "verified"}
    if mutation_required:
        check("mutation comparison configured", lambda: mutation_commands(root, config))
    return {"version": 1, "kind": "migration-preflight", "scope": "partial" if partial else "complete",
            "ready": all(row["passed"] for row in checks), "mutation_required": mutation_required,
            "checks": checks, "limits": "Preflight checks configuration and structured evidence; narrative/browser evidence requires review. Neither authorizes deployment."}


def verify(root, *, output="parity/results/verification.json", force=False, partial=False):
    root, config = project(root)
    preflight = doctor(root, partial=partial)
    if not preflight["ready"]:
        reasons = "; ".join(row["reason"] for row in preflight["checks"] if not row["passed"])
        raise Error(f"migration preflight is incomplete: {reasons}")
    names = ["format", "lint", "test"]
    if not partial or config["checks"].get("rollback"):
        names.append("rollback")
    commands = [(name, command(config["checks"].get(name), project=str(root))) for name in names]
    checks = []
    for name, argv in commands:
        try:
            run(argv, cwd=root, timeout=config["checks"].get("timeout_seconds", 900))
        except Error as error:
            raise Error(f"{name} gate failed: {error}") from error
        checks.append({"check": name, "passed": True})
    parity = compare(root, output="parity/results/verification-http.json", force=force)
    checks.append({"check": "http-parity", "passed": parity["passed"]})
    if preflight["mutation_required"]:
        mutations = mutation_diff(root, output="parity/results/verification-mutation.json", force=force)
        checks.append({"check": "mutation-parity", "passed": mutations["passed"]})
    value = {"version": 1, "kind": "migration-verification", "reference_sha": config["project"]["reference_sha"],
             "scope": "partial" if partial else "complete", "passed": all(row["passed"] for row in checks), "checks": checks,
             "limits": "Configured gates only. Partial verification allows unfinished contracts and unconfigured rollback. Review browser/realtime/integration evidence and deployment constraints separately."}
    write(generated_path(root, output), json_text(value), force=force)
    return value
