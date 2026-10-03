---
name: rails-inventory
description: Inventory a Rails application for a Rust port, including implicit framework contracts, legacy dependencies and release constraints. Use before choosing the migration architecture or splitting implementation areas.
---

# Rails Migration Inventory

Read the app before designing its replacement. Run `bin/rails-to-rust inspect reference`
and inspect the resulting source inventory, then read routes, database config, initializers,
models/concerns, filters, helpers, background jobs, plugins and deployment scripts. The static
inventory only supplies locations and counts; derive actual behavior from the running reference.

## Record the compatibility boundary

Preserve the existing database(s), text encodings, persisted class/enum values, timestamp
precision, external keys, cookies, authentication flows, routes, API formats, assets and
configuration unless the user has deliberately chosen a change. Distinguish retirement from
unfinished implementation. Record chosen differences and rollback consequences explicitly.

Determine the actual Ruby/Rails versions from locked runtime evidence. List loaded gems and
private forks, not just Gemfile declarations. Inventory framework-generated endpoints, external
systems, scheduled jobs, mail ingress/egress, search, realtime, storage and deployment roles.
A private gem source or unsupported runtime is a setup task, not permission to invent behavior.

Select the UI bar: equivalent behavior, normalized DOM, byte-exact responses, or pixel parity
on a named browser/viewport/theme/language matrix. Do not impose Campfire's pixel requirement
on an application whose user chose Backpack-style interaction parity.

## Deliver a usable plan

Group domain areas around complete operations and transaction ownership. Keep shared contracts
(sessions, params, routes, escaping, time) ahead of dependent controllers. Map every route and
state to its owner, including mobile/API/admin/error/unauthorized states. A route table alone
does not cover empty/populated, role, browser or mutation states.

Add uncertain assumptions and their probes to the plan. Create isolated fixture/service setup
and define how each layer will be tested. Carry state in the contract ledger and record any
missing evidence. Use [architecture.md](references/architecture.md) when selecting crate and
service boundaries; it explains which decisions transfer between the two example ports.
