# Architecture choices that transfer

The reusable part is the evidence-driven migration process and compatibility leaves, not a
single application framework. Reusing an audited primitive can save work; importing a whole
port carries app policy, runtime version assumptions and dependencies along with it.

| Concern | Campfire | Backpack | Decision for a new app |
|---|---|---|---|
| Reference runtime | Current Rails, modern Ruby | Rails 2.3 LTS, Ruby 2.5, private forks | Read locked runtime and gem implementation |
| Data | SQLite/WAL, single writer | MySQL app and identity databases | Preserve actual backends and raw connection encoding |
| Sessions | Modern signing/encryption metadata | Marshal CookieStore and SignalId signatures | Probe derivation, serialization, purpose, expiry and rotation |
| Views | ERB/Askama, Turbo/Stimulus, Action Text | ERB, RJS, Builder, Prototype, Textile | Ship existing frontend; port its actual rendering protocol |
| Jobs | In-process queues | DB-backed claims/schedules, separate roles | Derive durability/leadership from app semantics |
| Storage | Active Storage disk/variants | Legacy S3/depot paths, ImageMagick replacement | Preserve keys, checksums and existing derived objects |
| UI evidence | Browser matrix/pixel parity | Interaction and normalized response parity | Choose with the user; no universal pixel requirement |

A reasonable crate boundary is Ruby semantics -> Rails compatibility -> HTTP/DB/views/storage
adapters -> application domain and executable. Add routes/assets/jobs/integrations as their
actual size and dependencies justify them. Avoid creating ten empty crates up front.

Keep shared dependency versions centralized. Native parsing/TLS/compression crates are often
simpler than replacing them with custom code. Framework removal is worthwhile when it removes
real unused work; a clean unused-dependency audit is not proof every dependency is the best fit.

Check compatibility before retiring Redis, caches, workers or other deployment services.
Backpack's cache removal and job leadership are app-specific measured decisions. They do not
establish that every Rails cache or queue can disappear.

A domain map needs ownership of transactions and external effects. Separate databases and
services cannot be made atomic by nesting helper functions: state ordered commits, outbox or
compensation behavior explicitly. Splitting by directory alone can miss that boundary.
