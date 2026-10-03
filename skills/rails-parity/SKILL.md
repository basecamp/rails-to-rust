---
name: rails-parity
description: Verify a Rails-to-Rust migration using HTTP, browser, persisted-state, cookie, job and realtime comparisons. Use when implementing or reviewing compatibility evidence, not ordinary app tests.
---

# Rails Rust Parity

Start with an explicit compatibility bar and a named inventory. Include each implemented route,
role, empty/populated state, format, error case and meaningful mutation. State which browser,
viewport, theme and language cells are required; not every application needs pixel parity.

`parity` compares expected HTTP statuses, selected headers and bodies without following
redirects. Default byte equality is intentionally strict. Two matching error pages cannot pass
a case expecting success. Empty inventories, transport errors, absent cookies, truncated bodies
and unconfigured mutation reset commands fail. Its reports are HTTP evidence, not browser proof.

Each side of a mutation must start from an independent copy of the same seed. Use mutation-diff
with app-specific reset/action/snapshot adapters for DB rows, storage, outboxes, captured mail
and webhooks. Include every relevant database. Verify initial snapshots match before treating
final-state equality as evidence. Inject callback errors/cancellation and inspect rollback;
compare post-commit effects as well as visible responses.

Do not normalize away differences globally. Per-case masks need a reason and must retain record
identity, purpose, expiry, authorization and relative ordering/time relationships. A valid token
for a different record must still differ. Unknown causes stay failures; a broad mask is not a fix.

Run Rails->Rust and Rust->Rails session/form/data continuity, including old tabs and key rotation.
Pair reference equality with independent security invariants so two implementations agreeing
on a dangerous outcome do not prove safety. For detailed browser, job, storage and realtime
procedures, read [verification.md](references/verification.md).

Record raw evidence, exact revisions/runtime, seed identity, pass/fail/skip counts and unresolved
cases. Required fixtures should fail when absent. Compile-only tests, mocks and partial route
coverage cannot establish completion. Finish with configured verify gates and state the checks
that still require a browser, external dependency, staging environment or rollback rehearsal.
