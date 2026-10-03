# rails-to-rust

An agent migration toolkit, learned from `once-campfire-rust` and `backpack-rust`.
The CLI is Python 3.11+ with no third-party dependencies; run `bin/rails-to-rust --help`.

- Skills live in `skills/`; the entry point is `skills/rails-to-rust/SKILL.md`.
- Keep reference behavior separate from Rust scaffolding. Generators must not invent oracle
  outputs or modify the reference checkout. Unsupported contracts should fail explicitly.
- Support both legacy and current Rails. Do not make Campfire's SQLite/Rails 8 conventions
  universal: Backpack uses Rails 2.3 LTS, MySQL, RJS and legacy cookie serialization.
- Preserve source order, raw encoding, nullability and primary keys in generated contracts.
  Human decisions such as feature retirement, frontend redesign or deployment remain explicit.
- `python3 -m unittest discover -s tests -v` runs the toolkit tests. Validate generated Rust
  and Ruby as well when changing their generators. Test refusal paths and observed behavior,
  not copies of generator formatting.
- Keep the README short and current. Detailed migration advice belongs in skill references.
- `docs/lessons.md` records the source revisions and the specific tooling/lessons adapted.
