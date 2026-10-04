# Initial validation — 2026-10-03

The toolkit was exercised against real modern and legacy Rails applications, as well as
portable fixtures. These results describe export/code-generation coverage; reproducing
live checks requires your own application and its exact reference runtime.

| Reference runtime | Runtime/schema/routes exported | Generated records compiled | Ordered route contracts compiled |
|---|---|---:|---:|
| Legacy app: Ruby 2.5.9, Rails 2.3.18 LTS, MySQL | Yes | 49 tables | 473 routes |
| Modern app: Ruby 3.4.10, Rails 8.2.0.alpha, SQLite | Yes | 17 tables | 178 routes |

Legacy probes ran read-only against a local parity reference container,
with that fixture's normal startup overrides. Modern probes used a copy of the pinned
source mounted read-only, a copied seed database, test-only secret and isolated writable
storage/log/tmp mounts. The exporters never changed the original source checkouts.

The emitted schema and route envelopes were fed into the toolkit generators. All four
resulting Rust modules compiled with Rust 1.98.1. This validates contract export and code
emission; it does not establish application behavior, route recognition or model typecasting.

A real application-source initialization also produced a self-contained starter whose Rust
binary compiled and passed strict Clippy. Its observed response was HTTP 501, and it drained
and exited normally on Ctrl-C. Its empty unit-test suite does not count as application parity.
A fresh starter's doctor command correctly reports incomplete migration gates.

The **24 behavioral toolkit tests** pass with Python's standard unittest runner. They cover
source inventory, pinned init/self-contained tools, path confinement, overwrite refusal,
keys/nullability/types, stale vectors, route order/escaping, oracle framing, dirty-reference
refusal, golden-test adapters, expected HTTP statuses, bodies/headers/redirects, JSON identity,
mutation reset/snapshots, narrow normalization configuration, truncation and benchmark errors.
All seven skills pass the skill-creator validator and their reference links resolve.
The generated Ruby exporter passes `ruby -c` as well as both live runtime tests.

Raw test/probe outputs and cloned smoke-test fixtures stay under ignored target/ directories.
The committed documentation records their scope without publishing fixture databases, loaded
private-gem paths, cookies, secrets or application response bodies.

## Reproduce the portable checks

```sh
python3 -m unittest discover -s tests -v
ruby -c templates/reference-tools/export.rb
```

For live exports, initialize a port, configure its isolated runner, and run oracle
runtime/schema/routes, then generate records/routes. Compile the emitted modules or wire
them into the intended crates. The exact reference runtime and fixture services are required;
absence is setup work, not a substitute runtime or a passing check.
