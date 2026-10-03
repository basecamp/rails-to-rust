# @@NAME@@ in Rust

Use the `$rails-to-rust` skill in `.agents/skills/rails-to-rust/SKILL.md`.
The pinned reference is `reference/` at `@@SHA@@`; configuration is `migration.toml`.
`bin/rails-to-rust` provides this port's self-contained copy of the migration tools.

- Read the actual Ruby and loaded gem source for behavior. Generate expectations from that
  runtime; never hand-author oracle results, silently use a different Ruby, or edit reference/.
- Preserve databases, byte encodings, stored class names, storage keys, signed/encrypted cookies,
  URLs, frontend assets and production environment contracts unless deliberately changed.
  Prove Rails can read Rust's writes and cookies after rollback, including old forms and CSRF.
- Choose the parity bar explicitly. Record deliberate differences under README's "Known
  differences" and narrowly scoped evidence/masks. Never normalize authorization or record IDs away.
- Inventory filters and model callbacks before porting actions. Carry the caller's transaction
  through callbacks; defer external side effects to the correct commit boundary.
- Keep reusable Ruby semantics and Rails compatibility behavior in shared leaf crates. Domain
  code remains app-owned. Use the existing DB backend and an explicit driver; do not add an ORM
  or replace deployment services without evidence and an authorized product decision.
- Every area moves from pending to implemented to verified with reproducible evidence in
  plans/contracts.json. Unconfigured runners, absent seeds and skipped checks are incomplete.
- Rust dependencies belong in root workspace.dependencies. Tests live beside code; vectors come
  from the reference runtime. Measure before/after performance under bench/results/.
- cargo fmt, strict Clippy and workspace tests should pass. The scaffold returning 501 is
  intentional; green compilation alone does not prove a port works. Run bin/rails-to-rust verify
  for the configured migration gates and report missing fixture-dependent coverage explicitly.
