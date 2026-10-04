# Migration lessons

These lessons apply to modern and legacy Rails migrations. The toolkit is self-contained;
use the application you are converting and its locked runtime as the behavioral reference.
App-specific probes and compatibility code must be implemented and verified in that app.

| Area | Reusable lesson |
|---|---|
| Migration state | Pin an immutable reference, retain runtime evidence, verify bidirectional persisted compatibility and record deliberate differences |
| Golden vectors | Frame reference probes, record provenance and test production code against actual Ruby/gem behavior |
| Schema | Derive records from the live adapter with explicit keys/nullability; avoid unsafe universal positional decoders |
| Routing | Preserve route order, constraints and defaults across legacy and modern registries |
| Browser parity | Name UI states and use narrow masks that preserve semantic signed identities |
| Mutations | Start from equal isolated snapshots and compare persisted writes and captured effects beyond responses |
| Transactions | Share transaction ownership; test cancellation, callback/outbox consistency and post-commit file cleanup |
| Benchmarks | Use actual workloads, frozen builds, alternating rounds, error counts and explicit measurement scope |
| Capacity | Loopback, CPU quotas and one user's sockets do not establish real-hardware, TLS or unique-user capacity |
| Release gates | Local HTTP checks do not substitute for browser, staging or rollback evidence |
| Dependencies | Trim unused features and asset-processing copies, with unchanged-output validation |

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

App-specific Rust compatibility implementations need runtime vectors before reuse;
this toolkit does not bundle a universal Rails runtime library. A safe future extraction would give Ruby/serialization/HTTP primitives
stable crates and regenerate their vectors across deployed runtime versions. This first version
keeps the migration machinery independent and makes that boundary explicit.

## Legacy runtime and oracle findings

The following behaviors were observed in legacy fixtures using Ruby 1.9.3-p551,
Rails 2.3.18 and JSON 1.8.0. Treat them as probe targets, not assumptions about every
Rails 2 application or patched gem.

- Rails SafeBuffer values can invoke a legacy `to_json` override inside
  `JSON.pretty_generate`, changing non-BMP text even when the helper returned correct
  UTF-8 bytes. The exporter copies String subclasses to plain Strings recursively and
  reports Ruby patchlevel. Byte-sensitive probes should use hex/base64 and check bytes
  before JSON transport.
- Setting `ActionController::Base.allow_forgery_protection` after application controllers
  load may leave their inherited copies unchanged. Configure and verify concrete fixture
  controllers and inspect a real form. Do not assume the base-class setter enabled CSRF;
  the test environment may disable it by default.
- A legacy CSRF failure may reset the session rather than raise. Filters that run afterwards
  can restore authentication from saved-login cookies. Probe the loaded implementation and
  every affected authentication path.
- A lowest-priority controller/action route can recognize requests rejected by a resource
  route's verb. Direct `recognize_path` HEAD behavior can differ from HTTP normalization.
  Exported route counts do not prove recognition: capture both layers, formats and
  unsupported actions.
- Registry unavailability need not force a newer runtime. Build the exact upstream Ruby
  release with compatible OpenSSL and the unchanged locked gems where possible. Record
  build dependencies and runtime evidence; a local build is not the production image.
- Temporary-directory quotas can break compilers despite abundant repository disk space.
  Keep scratch/cache paths explicit and isolated. Old Ruby Makefiles may need output
  directories created before parallel extension builds; keep such setup outside the
  pinned reference.

## Fixture reset and legacy password compatibility

- Rails 2.3 `Fixtures.create_fixtures` caches loaded fixtures. Call `Fixtures.reset_cache`
  before each HTTP reset, release the reset thread's ActiveRecord connection, and assert
  baseline counts. Otherwise deletion scenarios can make later tests compare matching
  404s and untouched rows. Require expected statuses and observed changes; equal snapshots
  alone do not prove a mutation ran.
- Account `before_save` callbacks can run on `update_attribute`. An observed legacy account
  model converted plaintext passwords to bcrypt on any save, while rotating tokens only
  on creation or password changes. Probe both behaviors independently in your model.
- Rust bcrypt 0.17 defaults to `$2b$`; bcrypt-ruby 2.1.4 cannot parse that version.
  For that compatibility contract, use
  `hash_with_result(...).format_for_version(Version::TwoA)` and verify the result with
  the actual Ruby gem. Before masking salted hashes, check algorithm, cost, password
  verification and rollback readability.
- Direct legacy RJS serialization can truncate non-BMP codepoints via `pack("n*")`.
  Exporter transport and application output are different contracts: fixing the oracle
  envelope must not silently change JavaScript semantics.
- Dirty tracking affects timestamps: a typed boolean assignment equal to its old value
  may leave `updated_at` unchanged. A failed validation can leave dirty content on a Ruby
  object; a later `update_attribute` can save it without validation. Exercise controller
  sequences as well as isolated model saves.
- Application patches can narrow `String#blank?` to ASCII whitespace and NBSP. Boolean
  columns can cast blank strings to NULL and accept only an explicit true-value set.
  Capture scalar rules before using Rust defaults.
- Mutation comparison requires an observed change on each side by default.
  `expect_change = false` covers intentional no-op/rejection scenarios whose adapters
  also assert response status and unchanged-state invariants.

## Connection ownership and measurement

- A callback can exhaust a bounded MySQL pool if its caller retains a connection and
  re-enters the pool after commit. Drop the connection before the next lookup or pass
  the existing transaction/connection through nested work. Exercise more concurrent
  writes than the pool's capacity and verify distinct record IDs; sequential tests
  cannot expose all contention risks.
- Verification failures identify the configured gate while keeping captured boot output
  private. RJS fixture requests must carry the browser's actual `Accept: text/javascript`;
  unsupported HTML negotiation can return 406 after a successful mutation and misrepresent
  the behavior being rehearsed.
- Benchmark SQL commands as well as latency. mysql_async 0.36.2's default zero inactive TTL
  retains only the configured minimum; a zero minimum can close every returned connection.
  Retaining lazy connections within the existing cap avoids churn. Count handshake/metadata
  SELECTs and Prepare separately from application Execute, and retain before/after release
  measurements plus parity.

Record evidence in the generated port's `vectors/`, `reference-tools/`, conversion plan
and `parity/results/`. Keep HTTP, mutation, browser, mail, drain and bidirectional rollback
results scoped to the fixtures actually exercised; local results do not establish
production deployment parity.
