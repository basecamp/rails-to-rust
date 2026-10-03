# Parity fixtures

Add real cases to cases.json; an empty inventory fails. Each case has id, method, path,
expected_status, headers, body and comparison (bytes, text or json). GET/HEAD cases can share
read-only seeded servers. Mutations require reset_command configured in migration.toml;
each side starts from an independently restored seed. Use mutation-diff for post-write state.
Cookies come from a case's cookie_env variable and are not included in result artifacts.

The HTTP comparator checks selected headers and bodies without following redirects. It does
not prove browser interaction, pixel parity, WebSockets or rollback. Add app-specific browser,
channel and bidirectional continuity checks as described by the installed rails-parity skill.
