# Sources and lessons

Inspected on 2026-10-03:

- `once-campfire-rust` at `195457bc5e96b696e7530536ced0a67234ba4bac`.
- `backpack-rust` at `76d5c81ba658b536bbf8bccb80592b378fe85e74`.
- `tadalist` at `9ba3a612405d13615e0c498116950131ac8625ce` (ported with local fixture verification).

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

## Tadalist conversion findings

Observed against Ruby 1.9.3-p551, Rails 2.3.18, JSON 1.8.0 and the locked private MySQL fork. These are runtime findings, not assumptions about every Rails 2 application.

- Rails SafeBuffer values can invoke a legacy `to_json` override inside `JSON.pretty_generate`, changing non-BMP text even when the original helper returned correct UTF-8 bytes. The exporter now copies String subclasses to plain Strings recursively and reports Ruby patchlevel. Custom byte-sensitive probes should still use hex/base64 and check bytes before JSON transport.
- Setting `ActionController::Base.allow_forgery_protection` after application controllers loaded did not change their inherited copies. A fixture-only harness must configure and verify the concrete controllers; inspect a real form and reject the assumption that the base-class setter enabled CSRF. Test environment disables CSRF by default.
- This Rails 2.3.18 resets the session on an unverified CSRF request rather than raising. Filter ordering matters: saved-login cookies run afterwards and can restore authentication. Probe the loaded implementation and each affected authentication path.
- The lowest-priority default controller/action route can recognize requests rejected by a resource route's verb. Direct `recognize_path` HEAD behavior also differs from HTTP HEAD normalization. Exported route counts do not prove route recognition: capture both layers, formats and unsupported actions.
- Private registry unavailability need not force a newer runtime. Building the exact upstream Ruby release with compatible OpenSSL and the unchanged locked gems booted this pinned source and passed all 119 source tests. Record build dependencies and runtime evidence; do not claim the locally built runtime is the production image.
- Compilers and legacy build tools can fail on a temporary-directory quota despite abundant repository disk space. Keep build scratch/cache paths explicit and isolated. Old Ruby Makefiles may also need output directories created before parallel extension builds; such setup belongs outside the pinned reference.

Evidence lives in `tadalist-rust/vectors/{runtime,schema,routes,routing,sessions,helpers}.json`, its `reference-tools/` probes and conversion plan. The port also records HTTP, mutation, account/mail, browser, SMTP/drain and bidirectional rollback evidence under `tadalist-rust/parity/results/`; their fixture scope does not establish production deployment parity.

### Tadalist: validate the fixture reset and legacy password reader

Source: Tadalist `9ba3a612405d13615e0c498116950131ac8625ce`.

- Rails 2.3 `Fixtures.create_fixtures` caches loaded fixtures. Call `Fixtures.reset_cache`
  before every HTTP reset, release the reset thread's ActiveRecord connection, and assert
  baseline account/list/item counts. Otherwise a deletion scenario can make later tests
  compare matching 404s and untouched rows, producing false positives. Require action-specific
  expected statuses and observed changes; equal snapshots alone do not prove a mutation ran.
- Account `before_save` callbacks run even on `update_attribute(:email_address, ...)`.
  A present legacy plaintext password becomes bcrypt on any save, while tokens rotate only
  on creation or `password_changed?`. Preserve both behaviors independently.
- Rust bcrypt 0.17 defaults to `$2b$`; pinned bcrypt-ruby 2.1.4 cannot parse that version.
  Use `hash_with_result(...).format_for_version(Version::TwoA)`, then verify candidate
  hashes with the actual Ruby gem. Do not merely mask salted hashes as nondeterministic:
  check algorithm, cost, password verification, and Rails rollback readability first.

Evidence: `tadalist-rust/parity/exercise.py`, `reference-tools/server.rb`, and
`crates/db/src/lib.rs`. These are local fixture findings; they do not establish deployment parity.

- Direct Rails RJS serialization truncates non-BMP codepoints via `pack("n*")`.
  Exporter transport and application output are different contracts: fixing the
  oracle envelope must not silently change the app's JavaScript semantics.
- Dirty tracking affects timestamps: a typed boolean assignment equal to its old
  value does not update the row's `updated_at`. Conversely, a failed item validation
  can leave dirty content on the Ruby object; the controller's later `move_to_bottom`
  calls `update_attribute`, saving that content without validation. Exercise controller
  sequences as well as isolated model saves.
- This app's patched `String#blank?` accepts ASCII whitespace and NBSP, not all Unicode
  whitespace. Its boolean column casts blank strings to NULL and recognizes only its
  explicit true-value set. Capture these scalar rules before using Rust defaults.
- Mutation comparison now requires an observed change on each side by default. An
  explicitly configured `expect_change = false` covers intentional no-op/rejection
  scenarios whose adapters also assert response status and unchanged-state invariants.

- A MySQL callback can exhaust a bounded pool if its caller still owns a connection and
  re-enters the pool after commit. Drop the connection before the next app lookup, or
  pass the existing transaction/connection through nested work. Tadalist now exercises
  16 concurrent creates with its eight-connection pool and verifies distinct record IDs;
  sequential fixture tests alone did not expose this contention risk.
- Verification failures identify the configured gate (format, lint, test or rollback)
  while keeping captured boot output private. This avoids mistaking a rollback adapter
  failure for a source-test failure. RJS fixture requests must carry the browser's actual
  `Accept: text/javascript`; negotiating an unsupported HTML response can return 406
  after a successful mutation and misrepresent the behavior being rehearsed.
- Benchmark SQL commands as well as response latency. mysql_async 0.36.2's default
  zero inactive TTL retains only the configured minimum; `PoolConstraints::new(0, 8)`
  closed every returned connection in this app, creating six fresh connections per list
  read. Retaining up to eight lazy connections avoids that churn while preserving the
  eight-connection cap. Record handshake/metadata SELECTs and Prepare separately from
  application Execute counts, and retain before/after release measurements plus parity.
