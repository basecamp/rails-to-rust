---
name: rails-cutover
description: Prepare deployment and rollback for a compatible Rust replacement of a Rails app. Use for release gates, staging checks, old-session continuity and an authorized cutover, not general feature implementation.
---

# Rails Rust Cutover

Review the compatibility ledger and its evidence before the cutover plan. Distinguish locally
implemented code, local parity, staging smoke/soak and deployed production. A browser crash or
missing private service blocks that coverage; do not relabel HTTP tests as a replacement.

Use the deployment's real roles, env names, readiness/drain behavior, proxies, job claims,
scheduled-work ownership and observability. Keep a reference image and matching data/storage
snapshot available for rollback. Verify Rails reads rows, cookies and storage Rust wrote,
including migrations/auxiliary tables and every identity database. A source-code revert alone
is not a data rollback plan.

Rehearse on isolated copies: sign in on Rails, switch to Rust, submit old forms, mutate/create/
delete through Rust, switch back to Rails, continue sessions and inspect persisted data,
search/outboxes, mail, files and queued work. Exercise graceful shutdown with an in-flight
request, external call and claimed job; prove drain/retry and schedule leadership behavior.

Review resources/startup under realistic concurrency, errors/metrics/log redaction and app
health semantics. Confirm deliberate differences, retired endpoints and schema changes have
explicit product decisions and a rollback consequence. Run the configured verify gates and
record release artifacts/revisions. Keep the README factual about what has actually shipped.

Prepare concrete deployment/rollback commands and results for review. Execute publication or
production changes only within the user's actual authorization; successful local validation
does not expand it. Keep external notifications under the same authorization boundary.
