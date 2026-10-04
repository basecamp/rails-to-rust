# Verification layers

Use increasingly realistic evidence; a layer proves its own scope, not every higher layer.

| Layer | Evidence |
|---|---|
| Ruby/gem contracts | Reference-produced vectors plus independent properties |
| Model operations | Equal initial state, mutations, final rows/outboxes/files/effects |
| HTTP/API | Expected statuses, selected headers, bytes or narrowly normalized bodies |
| Browser | Same seeded state, UI actions, DOM/layout/assets and chosen screenshot matrix |
| Realtime | Protocol frames, membership authorization, revocation and churn |
| Operations | Startup, drain, durability, staging behavior and rollback continuity |

## Browser fixtures

Maintain named states with source/route coverage, user roles, seeded labels, paths, browser cells,
steps, expected outcomes and mutations. Explicitly include empty/populated, private/public,
unauthorized, error and mobile states. An inventory existence check without running steps is not
an interaction test. Use the same fonts/assets/browser version; freeze clocks and animations
where possible and wait for meaningful app readiness, not a fixed delay or network-idle alone.

Reset independently before each mutating capture. Parallel browser workers need isolated fixture
instances, ports, DB names, storage directories and external captures. Reusing one shared seed
lets tests erase each other's changes and can manufacture visual differences. Clock, workers,
polling and cached launchbars can create nondeterminism even on a frozen DB.

Value/pixel masks must identify actual random presentation values without hiding content,
record identity, layout, signing purpose or authorization. Decode signed identities to semantic
record/purpose placeholders only when explicitly justified; test that another record still
compares differently. Keep per-case exceptions and their Known differences entry reviewable.
Never repair a screenshot mismatch by blanket removing whole areas of the page.

## Writes, jobs and integrations

Compare committed rows and auxiliary identity databases, file manifests/checksums, queues,
search outboxes/index protocol, captured SMTP/webhooks and callback sequence. Start each side
from the same snapshot. Test create/update/delete and failures/cancellation. Equal success
responses can conceal missing owner records, stale counters or effects emitted before commit.

Use the reference's real mail parsers, encodings, XML/RJS/Atom/iCal serializers and integration
forks. Local captures establish protocol/state parity; a staging smoke test establishes contact
with the actual service. Neither should be reported as the other.

## Realtime and continuity

Use distinct users and memberships, not one signed-in cookie on many sockets. Subscribe,
revoke membership/deactivate/ban, attempt delivery, reconnect and resubscribe. Include slow
clients, backpressure, failed subscriptions and disconnect flags. Check large-room per-user
DB reads and unread notifications separately from shared-room broadcast throughput.

Retain old browser tabs across Rails->Rust and Rust->Rails switches: sessions, CSRF, signed
links and persisted data all need both directions. Security-sensitive behavior also needs
independent rejection properties. A framework oracle can carry an app-specific exception;
porting it must not accidentally widen that exception.

## Security and portable provenance

Capture unsafe legacy behavior as evidence, then pair compatibility checks with independent
security properties. Test a missing/invalid CSRF token together with a valid persistent-login
cookie: resetting a session is insufficient if a later filter restores authentication. Reordering
and mobile requests may omit form tokens; protect them while supplying same-origin headers,
and prove headers are not attached to off-origin requests. Record any old-tab reload requirement.

Validate account hosts against a configured domain and build sensitive email origins from
trusted domain/port/scheme configuration. Check attacker suffixes, nested account labels,
malformed authority text and forwarded headers; rejection must leave rows and mail unchanged.
Document deliberate security differences per case rather than globally masking authorization,
status codes or effects until the old and new implementations appear equal.

Runtime provenance should identify versions and revision suffixes without embedding developer
home paths or private bundle layout. Exercise the real exporter, retain stable installed
basenames, and regenerate vectors from the reference instead of hand-editing expected values.
For an unprivileged container, inspect its configured user and run the image: assert actual
UID/GID, file permissions and meaningful readiness, not just a `USER` line in the Dockerfile.

## Completion

Report pass/fail/ignored/fixture-skipped counts, exact revisions and supported matrix. Required
fixtures fail closed in CI. A browser launch failure is unfinished browser coverage, even if
all HTTP comparisons pass. Keep local implementation, local audit, staging soak and deployed
status separate. Do not silently expand the compatibility bar beyond the user's chosen goal.
