# Implementing the contracts

## Databases and callbacks

Keep SQL explicit and use the real database driver. Define pool/blocking behavior for the actual
backend: SQLite blocking calls must not occupy asynchronous runtime threads without bounds;
MySQL's async pool is not a SQLite reader queue. Cache statements where useful. Query selected
columns explicitly. Positional decoding needs an order check/fallback for SELECT *, joins,
partial rows and migrated installations; do not assume schema.rb order matches every install.

Pass transaction ownership into nested model callbacks. Every save/destroy/counter/history/
outbox statement joins the caller's transaction, and a closed/escaped transaction view fails
rather than silently autocommitting. Inject failure between dependent writes. Drop/cancel the
owner and prove rollback. Account creation must not leave an account without its owner.

Order touch/unread/indexing/history/dependent-destroy work like Rails. Defer physical file
deletions and irreversible external effects to the intended commit boundary; remove new files
on rollback when appropriate. Cross-database/service writes need explicit ordered/compensating
semantics, not an illusion of one shared transaction. Destruction and account incineration should
reuse the same transaction-aware model behavior rather than duplicate cascade SQL.

## Controllers and rendering

Run filters in source order, including inherited concerns. Authentication, authorization, CSRF,
format negotiation and callbacks can change early responses. Exercise unauthorized roles and
missing records as well as happy paths. Do not turn every early controller return into an error
string that changes Rails status/headers/flash/session effects.

Mirror view relative paths where it makes source cross-checking easier. Port helpers separately
and test their escaping. Rails ERB escaping, JSON-in-script escaping, content disposition and
JavaScript escaping are different contracts. Mark trusted HTML intentionally; do not make every
String safe to fit a template. Translate ERB/RJS/Builder/Jbuilder according to the actual
frontend response protocol. A textarea or rich-text value cannot be handled with ordinary
attribute escaping just because the happy-path screenshot matches.

Preserve frontend assets from the reference/gems at locked versions. Generated digests/importmaps
or concatenated legacy bundles need reference output checks. Port-owned overrides live outside
reference/ and explicitly shadow logical paths. Byte regexes can remove expensive Latin-1
conversions in build-time asset processing, but preserve exclusions, nested matches and comment
boundaries; this is a build speed gain, not a request throughput claim.

## Jobs, storage and realtime

Keep claims/durability/retry/leadership boundaries explicit. Test once-per-cluster schedules,
SIGTERM while a job is claimed, idle shutdown and in-flight integration calls. Bounded queues
and workers replace service plumbing only when they preserve the app's required behavior.

Storage APIs may be public behind signed URLs even when upload endpoints require auth. Do not
make downloads require login as a convenience change. Maintain metadata, checksum and variant
identity. Media tools need their actual native limits and byte/geometry/vector tests.

Cable requires welcome/ping/confirm/reject, identifier serialization, perform and reconnect flags,
not merely a WebSocket upgrade. Verify authorization, revocation and resubscription for every
channel, including stock channels patched by the app. Shared precompressed broadcast frames
can be a major win, but unique-user bookkeeping, backpressure and protocol limits remain.

Outbound clients must preserve redirects/timeouts/host and IP policy. SSRF protections require
independent tests, not solely oracle agreement. Capture SMTP, webhooks, search and external API
protocols locally; optional unavailable services stay visible as unverified coverage.
