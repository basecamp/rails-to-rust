# Rails to Rust

Skills and generators for agents converting Rails applications into compatible Rust
applications, including modern Rails and Rails 2.3 LTS apps. The toolkit and its guidance
are self-contained; use your own application as the pinned reference.

```sh
bin/rails-to-rust init ../my-rails-app ../my-app-rust --name my_app
cd ../my-app-rust
# Ask your agent: Use $rails-to-rust to convert this application.
```

The new repository includes a pinned `reference/` submodule, Rust starter, migration
plan and contract ledger, installed skills under `.agents/skills/`, and its own copy
of the toolkit. Python 3.11+ and Git are needed; the toolkit has no Python dependencies.
Rust, Rails and fixture services are needed for their respective checks.

| Command | Purpose |
|---|---|
| `inspect SOURCE` | Inventory models, controllers, views, frontend and compatibility review points |
| `oracle runtime\|schema\|routes` | Capture contracts from the actual configured Rails runtime |
| `generate records\|routes\|contract-test` | Produce Rust records, ordered route tables and golden-test adapters |
| `parity` | Compare expected statuses, selected headers and HTTP bodies |
| `mutation-diff` | Compare persisted state and captured effects from independently reset fixtures |
| `benchmark` | Record balanced before/after process timings and raw rounds |
| `doctor` / `verify` | Check evidence and execute gates; `verify --partial` checks work in progress |

The entry skill guides inventory, reference setup, contracts, vertical slices,
parity, performance and cutover. Specialized skills cover each phase. Generated
application behavior starts at HTTP 501; agents implement it against Rails evidence.
This is a migration toolkit, not an automatic Ruby transpiler or a shared Rust Rails framework.

[Commands and configuration](docs/commands.md) · [Lessons](docs/lessons.md) · [Validation](docs/validation.md)

```sh
python3 -m unittest discover -s tests -v
```
