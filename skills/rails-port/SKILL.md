---
name: rails-port
description: Implement Rails application behavior in Rust against captured reference contracts, including transactions, controllers, templates, assets, jobs and integrations. Use during a migration’s implementation phase.
---

# Port Rails Behavior

Start with the active contract, its Ruby implementation, and observed inputs/outputs. Implement
one complete vertical slice through route, authentication/authorization, model mutation,
rendering and side effects. Do not turn generic Rust idiom preferences into behavior changes.

Use `generate records` for storage-shaped structs and `generate routes` for the ordered route
contract table. Wire modules into the chosen crates and DB adapter. They do not implement
framework callbacks, route recognition or typecasting; test those separately. Unsupported types
require an explicit codec, not a guessed fallback.

Keep Ruby primitives separate from Rails contracts and domain policy; vectors should test the
code production actually uses. Share transaction ownership and repeated compatibility semantics
rather than building an ORM. Add pooling/caching/rendering abstractions when the app's contracts
or measured hot paths justify them, and centralize dependency versions in the workspace.

Preserve controller filter order and inherited concerns, source route precedence, format
negotiation, params, redirects, cookies and error responses. Read gem code when defaults matter.
Choose library features explicitly; do not rewrite HTTP/TLS/HTML parsers just to reduce counts.

For database callbacks, cancellations and side effects, read
[implementation.md](references/implementation.md). It also covers MySQL encodings, SQLite
writer/read paths, templates/RJS/assets, jobs, storage and realtime. Use only the relevant parts.

After implementation, run the matching reference vectors and a real end-to-end operation.
Record deliberately changed behavior under Known differences and its affected tests/masks.
Move the contract to implemented first, then verified only after its meaningful checks ran.
Unported handlers, ignored tests and fixture skips remain visible in the progress report.
