---
name: rails-oracle
description: Capture Rails and Ruby compatibility contracts from an application’s actual pinned runtime for a Rust migration. Use for golden vectors, live schema/routes, cookie continuity and reference fixture setup.
---

# Rails Runtime Oracle

Use the locked Rails runtime and the pinned reference checkout. Read the relevant app source
and installed gem implementation, then run a probe inside that runtime. Do not silently switch
to local Ruby, a newer Rails version, public documentation, or Rust-produced expected values.

## Set up reproducible evidence

Configure `oracle.command` in migration.toml as argv, with the proper runner for this app:
modern Rails uses rails runner; Rails 2.3 uses script/runner. Container commands must forward
RAILS_TO_RUST_EXPORT and RAILS_TO_RUST_REFERENCE_SHA. Verify the mounted source/image really
matches the declared commit; the supplied SHA field is not an attestation by itself.

Use test-only secrets, isolated copies of every database and storage service, deterministic
labels, a controlled clock and captured external services. Do not mutate reference source to
make a probe easier. Add probe scripts beside the port and mount/run them against the reference.
Required seeds/services must make tests fail when absent, not return early as successful tests.

Run `oracle runtime`, `oracle schema` and `oracle routes`. The exporter handles legacy and
Journey-era registries, preserves route order, and exports live schema columns/indexes.
Supplement it for each additional database, adapter-specific type/constraint/collation,
mounted endpoint and dynamic constraint. Generators are consumers of evidence, not validators
of every semantic contract.

## Write a custom contract probe

Emit one framed JSON envelope with version=1, kind, reference_sha, actual runtime metadata and
a nonempty data array of input/expected cases. Keep byte values explicit (hex/base64) and retain
float/time/decimal precision, array order, encoding metadata and exceptional outcomes.
Separate round-trip readers/writers from independent property tests. Include boundary/negative
cases and capture both Rails reading Rust output and Rust reading Rails output where persisted
contracts are involved.

Use `oracle KIND --script reference-tools/probe.rb`, then `generate contract-test KIND` with
the vector and test output paths. Wire the test adapter to production Rust code; generated
unimplemented adapters fail deliberately. Inspect [contracts.md](references/contracts.md)
for the non-obvious signing, serialization, encoding and storage cases found in both ports.
