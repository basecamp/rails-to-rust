---
name: rails-to-rust
description: Convert Rails applications into Rust using a pinned running reference, compatibility contracts, generators and parity evidence. Use for planning or carrying out a migration, not ordinary Rust feature work.
---

# Rails to Rust

Use the project-local `bin/rails-to-rust` toolkit and the pinned Rails application to build
a Rust replacement with an explicit compatibility bar. Read `AGENTS.md`, `migration.toml`,
`plans/contracts.json` and the current plan first. Existing user choices take precedence.

## Select the current phase

The initializer installs all of these skills together under `.agents/skills/`:

- Use [rails-inventory](../rails-inventory/SKILL.md) to discover app scope, dependencies and the compatibility bar.
- Use [rails-oracle](../rails-oracle/SKILL.md) to boot the reference and record actual runtime contracts.
- Use [rails-port](../rails-port/SKILL.md) to implement a complete vertical slice or domain area.
- Use [rails-parity](../rails-parity/SKILL.md) to compare behavior, browser interactions, writes and integrations.
- Use [rails-performance](../rails-performance/SKILL.md) for measured simplification and capacity work.
- Use [rails-cutover](../rails-cutover/SKILL.md) when preparing deployment and rollback.

## Start or resume

For a new port, run `rails-to-rust init SOURCE DEST --name app` from the toolkit's bin directory.
For an existing initialized port, continue from its evidence and unresolved contracts; do not
restart the migration or regenerate valid vectors merely because context was lost.

Build the runtime/fixtures, then sessions/data/routing contracts, then one useful vertical slice.
Complete the remaining areas and their end-to-end evidence before treating the app as deployable.
A compiling scaffold, a count of translated files, or all-green tests without required fixtures
is not evidence of a working replacement. The starter intentionally returns HTTP 501.

Choose the existing database, storage and integration topology first. Framework decisions follow
measured needs and compatibility. Campfire's SQLite and Rails 8 architecture is one example;
Backpack's MySQL and Rails 2.3 LTS architecture is another. Read the active phase's references,
not every reference at once.

## Keep durable state

Update the conversion plan and contract ledger after each completed area: reference source
locations, actual runtime versions, implemented behavior, test command/result, evidence paths,
known differences and the next unresolved work. Use pending, implemented and verified honestly;
not-applicable needs a concrete reason. Keep README focused on the current state and differences.

Keep reusable primitives shared, domain policy app-owned, and reference/ immutable. Generated
code stays separate from model/controller behavior. Benchmark before/after changes and preserve
raw results. Finish with `doctor` and the configured `verify` gates, stating which browser,
realtime, external-service and rollback checks were actually exercised.

This workflow provides implementation guidance, not authorization to change production, publish
repositories or contact other people. Follow the user's authorized scope for those operations.
