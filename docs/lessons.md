# Sources and lessons

Inspected on 2026-10-03:

- `once-campfire-rust` at `195457bc5e96b696e7530536ced0a67234ba4bac`.
- `backpack-rust` at `76d5c81ba658b536bbf8bccb80592b378fe85e74`.

The toolkit was newly implemented around lessons from these sources; it does not copy an
entire app or bundle private Rails LTS gems. App-specific probes and compatibility code
must be adapted to the new app/runtime and verified there.

| Source tooling or finding | What this toolkit carries forward |
|---|---|
| Both AGENTS.md and conversion plans | Pinned immutable reference, runtime evidence, bidirectional persisted compatibility, explicit differences |
| Campfire reference-tools and golden vectors | Framed reference probes, provenance, production-code test adapters and actual Ruby/gem behavior |
| Backpack reference-tools/gen_schema.py and RecordRow | Live schema-derived records, explicit keys/nullability; no unsafe universal positional decoder |
| Backpack routes_dump.rb; Campfire campfire/routes.rb | Ordered route exports, constraints/defaults, legacy and modern route registries |
| Campfire parity/screens.yml and capture tests | Named UI states and narrow masks that preserve semantic signed identities |
| Backpack parity/bin/job-diff, mail-diff, email-diff | Equal isolated snapshots, persisted mutations and captured effects beyond response equality |
| Backpack plans/progress.md transaction audit | Shared transaction ownership, cancellation rollback, callback/outbox consistency, post-commit file cleanup |
| Both benchmark reports | Actual workloads, frozen images, alternating rounds, error counts and clear measurement scope |
| Campfire Pi estimate correction | Loopback/CPU quota/single-user capacity is not actual Pi/TLS/unique-user evidence |
| Backpack browser-coverage limitation | Local HTTP checks do not substitute for browser/staging/rollback release gates |
| Campfire dependency-cuts-20261002 | Feature trimming, byte-level asset processing and unchanged-output validation |

The skills are the maintained guidance. Their focused references hold the detailed lessons:
[architecture](../skills/rails-inventory/references/architecture.md),
[contracts](../skills/rails-oracle/references/contracts.md),
[implementation](../skills/rails-port/references/implementation.md),
[verification](../skills/rails-parity/references/verification.md),
[performance](../skills/rails-performance/references/measurement.md).

## What is reusable now

The CLI, runtime exporters, record/route/test generators, skills and comparison runners are
self-contained. Init vendors them into the new port so a future agent can keep working without
this checkout. Runtime-derived schema/export cases still require the actual app and fixture
services. Browser inventories, token probes, resets/snapshots and external stubs are necessarily
app-specific work; the skills explain how to build them and how to report missing evidence.

Existing Rust compatibility implementations are candidate source material, not a universal
Rails runtime library. A safe future extraction would give Ruby/serialization/HTTP primitives
stable crates and regenerate their vectors across deployed runtime versions. This first version
keeps the migration machinery independent and makes that boundary explicit.
