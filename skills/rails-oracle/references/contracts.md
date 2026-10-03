# Contracts easy to miss

## Ruby and serialization

String strip/to_i/to_f, CGI versus URL encoding, float formatting, JSON script escaping,
Marshal encoding ivars, object/symbol links, time nanoseconds and unknown object classes can
be externally observable. Use the deployed Ruby version. Do not replace Ruby's integer prefix
parsing with Rust parse(), or convert exact decimals/timestamps through floats. Preserve bytes
when a broken or Latin-1-tagged string contains UTF-8 byte sequences.

Golden vectors test the shared production implementation. If several crates copy a shim while
only one copy is checked, a green vector suite proves the wrong thing. Consolidate semantics
before adding copies. Do not generate expected values by running the Rust implementation.

## Signing, sessions and browser continuity

Signing digest and derivation digest are distinct settings. Probe iterations, salt/key length,
serializer, metadata envelope, purpose, expiration, base64/url escaping, encryption mode,
nonce/tag, key rotation and cookie attributes. Rails version alone does not determine them:
initializers and patched gems do. Modern JSON serializers and legacy Marshal are separate cases.

Test valid/wrong-secret/tampered/wrong-purpose/expired/future/rotated cases. Read Rails cookies
in Rust and Rails must accept Rust cookies. Render CSRF-protected forms on one implementation,
submit on the other, in both directions. Authentication cookie and CSRF secrets may be separate.
Some signed IDs are stored in old rich text: a public signature parser must not generalize an
app's narrowly intended legacy fallback to other classes or purposes.

## Data and routes

Live schema is primary-key/nullability/column-order evidence, not callback evidence. Include
STI names, integer enums, polymorphic types, association touch/counter effects, dirty-change
behavior and transaction boundaries. Dump models and plugin/identity schemas separately.
Timestamp bytes, precision and Ruby nil/false/empty conversions can be rollback contracts.

Legacy MySQL deployments can deliberately use a latin1 connection to transmit UTF-8 bytes.
Check Rails->Rust and Rust->Rails text with accents, emoji, CJK and invalid byte sequences.
Do not repair encodings as part of an otherwise drop-in replacement without a migration plan.

Rails recognizes in declaration order. Literal-looking routes can be shadowed by earlier
dynamic ones. Probe escaped segments, dots, slashes, format suffixes, trailing slashes, HEAD,
OPTIONS, wrong verbs, route recall and URL generation. Preserve Ruby regexp options and
constraints; Rust regex syntax or a generic router might not express them directly.

## Storage and outbound work

Active Storage variation digests can depend on a Ruby Marshal transformation hash; a JSON
rewrite changes object identity. Probe signed downloads, redirects/proxies, ranges, dispositions,
checksums, disk/S3 layout, variants/previews and loader security. Reuse existing derived objects.

Jobs/mail probes need pre/post state plus captured SMTP/webhooks/search/outbox effects, not only
return values. Include failures and retries. Dynamic loaded callbacks and private forks are
read from the actual gem/plugin source in the reference runtime.
