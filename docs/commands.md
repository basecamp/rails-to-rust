# Commands

Run `bin/rails-to-rust --help`. In generated ports, the same command uses their
vendored copy of the toolkit. `--project DIR` precedes the command when outside
the port root. Files are written atomically; differing existing outputs require
`--force`. Generators cannot write into reference/ or escape the port root.

## Initialize and inventory

```sh
bin/rails-to-rust init /path/to/rails /path/to/app-rust --name app
bin/rails-to-rust inspect /path/to/rails --output /path/to/inventory.json
```

Init uses the source's Git HEAD, not uncommitted changes. It clones locally, checks
out that SHA detached, and uses the upstream origin in .gitmodules when available.
Without an origin, the submodule URL remains the local source path: set a portable
URL before sharing the port. Nothing is installed into global agent configuration.
Use `--rust-version X.Y.Z` to choose a different exact toolchain.

Source inventory is static. It does not execute database ERB or infer the complete
loaded route set, implicit callbacks or gem behavior. The runtime exporters do.

## Reference runtime

Build/start the reference with its exact Ruby, locked gems and app services. Use
isolated fixture databases, storage and captured external services. Keep private
gem credentials in your existing secret mechanism, not generated files. Configure
`oracle.command` as an argv array in migration.toml. There is no shell expansion.

A modern Rails app with a prepared local bundle:

```toml
[oracle]
command = ["bundle", "exec", "rails", "runner", "{script}"]
working_directory = "reference"
timeout_seconds = 180
```

Rails 2.3 uses `bundle exec ruby script/runner {script}` instead. A running Docker
reference whose working directory is /rails and whose /work mounts the port:

```toml
[oracle]
command = ["docker", "exec", "-e", "RAILS_TO_RUST_EXPORT={kind}", "-e", "RAILS_TO_RUST_REFERENCE_SHA={reference_sha}", "-w", "/rails", "my-fixture-reference", "bundle", "exec", "rails", "runner", "/work/reference-tools/export.rb"]
working_directory = "."
```

Pass the two environment variables explicitly to container runners; they are set
for native runners automatically. Customize the runner path for legacy Rails.
The container must run the pinned source, not an old image with a new SHA label.
For a custom oracle, use a runner with `{script}` mapped into the container rather
than the fixed example filename above.

```sh
bin/rails-to-rust oracle runtime
bin/rails-to-rust oracle schema
bin/rails-to-rust oracle routes
bin/rails-to-rust generate records
bin/rails-to-rust generate routes
```

Exports are framed JSON with kind, version, reference_sha, runtime and data. Schema
comes from the live adapter, not schema.rb regex inference. Run exports separately
for each application/identity database. Capture indexes and backend-specific
constraints/sequences/collations as supplemental probes. PostgreSQL arrays and
custom types need explicit codecs; unknown types fail record generation.

Use `generate records --table users --table messages` to select domain tables while
keeping internal/search tables in the captured schema contract.

Records are storage-shaped structs and column/key metadata. Wire the generated
module into the appropriate DB crate and implement the reference typecasting in
its driver adapter. The generator does not invent model class inflections, install
an ORM, implement callbacks, create migrations, or claim a decimal is a float.
Routes retain their complete export as JSON and their original order. Recognition,
URL helpers, mounted apps and callable constraints still need oracle-tested code.

Custom scripts use the same framing and emit a list of `{input, expected}` cases:

```sh
bin/rails-to-rust oracle cookie-signing --script reference-tools/cookies.rb
bin/rails-to-rust generate contract-test cookie-signing \
  --from vectors/cookie-signing.json --output crates/rails_compat/tests/cookies.rs
```

Add serde_json as a dev dependency and replace the generated run_case adapter.
Until wired to the real implementation, the test fails deliberately.

## HTTP parity

Configure both fixture server URLs and a cases file. An empty cases file fails.

```json
{
  "version": 1,
  "cases": [
    {
      "id": "signed-in-home",
      "method": "GET",
      "path": "/",
      "expected_status": 200,
      "cookie_env": "PARITY_COOKIE",
      "comparison": "bytes",
      "compare_headers": ["content-type", "cache-control", "vary"]
    }
  ]
}
```

Requests do not follow redirects. Two matching error pages do not pass a case
expecting 200. Bytes are exact by default. Text supports an explicit encoding;
JSON ignores object-key order, not array order or values. Optional normalizations
are per-case `{pattern, replacement, reason}` objects and only apply to text/JSON.
No global CSRF, timestamp, signed-ID or authorization masking is performed.

Use separate case inventories or commands when Rails and Rust need different
valid cookies. Cookies are read from the environment and never written to reports.
Bodies are hashed in reports, not dumped. Compare-header values are also kept out
of reports; the comparator still checks them exactly. Large-response cases can
increase max_body_bytes; truncated responses never count as equivalent.

GET actions can mutate state: mark them with `mutates: true`. Every mutating case
requires parity.reset_command, receiving `{side}`, to restore the reference or
candidate fixture copy before that side's request. Body parity alone does not
prove post-write data: follow it with state/side-effect comparisons.

## Mutation comparison

Configure a concrete operation and fixture-only adapters in migration.toml:

```toml
[mutations]
reset_command = ["python3", "parity/reset.py", "{side}"]
snapshot_command = ["python3", "parity/snapshot.py", "{side}"]
reference_command = ["python3", "parity/run-operation.py", "reference"]
candidate_command = ["python3", "parity/run-operation.py", "candidate"]
timeout_seconds = 180
```

These are app-specific adapters to implement, not preexisting scripts. Snapshot
commands emit deterministic JSON for stored rows, storage manifests, mail/webhook
captures and queue/search outboxes. Sort rows by their real keys. Include all
relevant databases; omit or normalize a value only through a documented decision.
The tool validates all commands before doing any reset, resets and snapshots both
independent fixtures, and requires equal starting states before either action runs.
It then executes each implementation and compares final snapshots. It reports
hashes, not sensitive fixture values. An empty snapshot is not meaningful evidence.
Both actions must produce an observed state change by default: matching no-op or
404 responses do not establish mutation parity. For an intentionally rejected/no-op
mutation scenario, set `[mutations] expect_change = false` explicitly and check its
HTTP status and rejection invariants in the action adapter.

## Performance

```sh
bin/rails-to-rust benchmark \
  --before '["./bench/before"]' --after '["./bench/after"]' \
  --rounds 6 --compare-output --output bench/results/rendering.json
```

This measures whole-process wall time after one warmup pair, alternating AB/BA.
It is useful for deterministic build scripts and microbenchmark executables.
It is not an HTTP load generator. Use a suitable load generator and the performance
skill for throughput, percentiles, CPU/request, memory, startup and real-user fanout.
Compile first, freeze images/revisions, and never infer hardware capacity from a
CPU-quota-limited loopback run. Pass secrets through environment variables, not
argv recorded in benchmark artifacts.

## Readiness

`doctor` reports configuration/evidence gaps and exits nonzero when incomplete.
For verified contracts, evidence files must exist. JSON evidence must identify the
pinned reference SHA; malformed JSON and unsuccessful `passed` or `ready` results
fail preflight. Narrative and browser artifacts still require review of their
results, revision and scope; file existence is not proof of their claims.

`verify` requires all contracts verified or explicitly not applicable, then runs
configured format/lint/tests, rollback rehearsal and HTTP parity. It also runs
mutation comparison whenever adapters are configured, the mutations contract is
applicable, or the HTTP inventory contains writes (including `mutates: true` GETs).
Read-only ports must mark the mutations contract not applicable with a reason.

Use `verify --partial` during migration. It permits pending/implemented contracts
and an unconfigured rollback rehearsal, runs the format/lint/tests and HTTP gates,
and includes configured rollback and mutation checks. Implemented/verified mutation
contracts and HTTP writes still require mutation adapters. Its report explicitly
says `scope: partial`; a passing slice is not evidence that the migration is complete.
All verified evidence is checked in both modes, and preflight errors list the gaps.

Configure fixture-dependent tests to fail when their seed or service is absent.
Do not substitute `true` for a required gate. The generated CI checks Rust only,
until fixture-enabled checks are added. Neither command publishes or deploys an app.
