# rails-to-rust

A self-contained agent toolkit for migrating Rails applications to Rust.
The CLI is Python 3.11+ with no third-party dependencies; run `bin/rails-to-rust --help`.

- Skills live in `skills/`; the entry point is `skills/rails-to-rust/SKILL.md`.
- Keep reference behavior separate from Rust scaffolding. Generators must not invent oracle
  outputs or modify the reference checkout. Unsupported contracts should fail explicitly.
- Support both legacy and current Rails. SQLite/current Rails conventions are not universal:
  legacy apps may use MySQL, RJS and Marshal cookie serialization.
- Preserve source order, raw encoding, nullability and primary keys in generated contracts.
  Human decisions such as feature retirement, frontend redesign or deployment remain explicit.
- `python3 -m unittest discover -s tests -v` runs the toolkit tests. Validate generated Rust
  and Ruby as well when changing their generators. Test refusal paths and observed behavior,
  not copies of generator formatting.
- Keep the README short and current. Detailed migration advice belongs in skill references.
- `docs/lessons.md` records generalized migration lessons. Keep guidance self-contained;
  do not name, link to or require access to private source repositories.
