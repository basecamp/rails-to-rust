from __future__ import annotations

import shutil
from .common import Error, command, generated_path, json_text, load_json, project, run, write
from .oracle import check_reference
from .parity import cases_from, compare


def doctor(root):
    root, config = project(root)
    checks = []
    def check(name, action):
        try:
            action()
            checks.append({"check": name, "passed": True})
        except (Error, KeyError) as error:
            checks.append({"check": name, "passed": False, "reason": str(error)})
    check("pinned, unchanged reference", lambda: check_reference(root, config))
    def runner():
        argv = command(config["oracle"].get("command"), project=str(root), reference=str(root / "reference"),
                       script=str(root / "reference-tools/export.rb"), kind="runtime", reference_sha=config["project"]["reference_sha"])
        if not shutil.which(argv[0]):
            raise Error(f"oracle executable {argv[0]} is not on PATH")
    check("configured reference runner", runner)
    check("nonempty HTTP parity inventory", lambda: cases_from(generated_path(root, config["parity"]["cases"])))
    check("rollback rehearsal configured", lambda: command(config["checks"].get("rollback"), project=str(root)))
    def evidence():
        ledger = load_json(root / "plans/contracts.json")
        if ledger.get("reference_sha") != config["project"]["reference_sha"] or not ledger.get("contracts"):
            raise Error("contract ledger must match the pinned reference and contain contracts")
        ids = set()
        for contract in ledger["contracts"]:
            if contract.get("id") in ids or not contract.get("id"):
                raise Error("contract IDs must be unique and nonempty")
            ids.add(contract["id"])
            if contract.get("status") not in {"pending", "implemented", "verified", "not-applicable"}:
                raise Error(f"{contract['id']}: invalid contract status")
            if contract["status"] in {"pending", "implemented"}:
                raise Error(f"{contract['id']}: {contract['status']}, not verified")
            if contract["status"] == "not-applicable":
                if not contract.get("reason"):
                    raise Error(f"{contract['id']}: not-applicable requires a reason")
            else:
                if not contract.get("evidence"):
                    raise Error(f"{contract['id']}: verified requires evidence")
                for path in contract["evidence"]:
                    if not generated_path(root, path).is_file():
                        raise Error(f"{contract['id']}: evidence file is missing: {path}")
    check("contract evidence ledger", evidence)
    return {"version": 1, "kind": "migration-preflight", "ready": all(row["passed"] for row in checks),
            "checks": checks, "limits": "Preflight validates configuration and evidence links; verify executes gates. Neither authorizes deployment."}


def verify(root, *, output="parity/results/verification.json", force=False):
    root, config = project(root)
    preflight = doctor(root)
    if not preflight["ready"]:
        raise Error("migration preflight is incomplete; run doctor for the missing gates")
    checks = []
    for name in ["format", "lint", "test", "rollback"]:
        argv = command(config["checks"].get(name), project=str(root))
        run(argv, cwd=root, timeout=config["checks"].get("timeout_seconds", 900))
        checks.append({"check": name, "passed": True})
    parity = compare(root, output="parity/results/verification-http.json", force=force)
    checks.append({"check": "http-parity", "passed": parity["passed"]})
    value = {"version": 1, "kind": "migration-verification", "reference_sha": config["project"]["reference_sha"],
             "passed": all(row["passed"] for row in checks), "checks": checks,
             "limits": "Configured gates only. Review browser/realtime/integration evidence and deployment constraints separately."}
    write(generated_path(root, output), json_text(value), force=force)
    return value
