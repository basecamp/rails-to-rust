# @@NAME@@ in Rust

An agent-driven port of the Rails application pinned in `reference/`.

Status: scaffold created; application behavior has not been ported.

```sh
bin/rails-to-rust doctor
cargo run -p @@NAME@@          # listens on loopback:7070, returns 501 until ported
```

Read [AGENTS.md](AGENTS.md) and use `$rails-to-rust`. Configure the reference runner
in `migration.toml`, then capture contracts with `bin/rails-to-rust oracle`.
Track implementation and evidence in [plans/contracts.json](plans/contracts.json).

## Known differences

None approved yet. The incomplete scaffold is not a deployable replacement.
