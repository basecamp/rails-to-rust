---
name: rails-performance
description: Measure and simplify a Rails-to-Rust port using comparable production workloads and before/after evidence. Use for benchmark tables, profiling, dependency cuts or connection-capacity estimates.
---

# Rails Rust Performance

Establish functional parity for the measured operation first. Freeze before/after revisions
or images and use the same fixture data, actual user state, release settings and dependency
services. Benchmark application responses, not login redirects, error pages or an empty path
presented as a populated workload. Record expected statuses, transport/HTTP errors and workload.

For deterministic process/build-script comparisons use the toolkit benchmark command with
balanced even rounds and --compare-output when the output should match. It records process
wall time, not HTTP throughput. For servers use a suitable load generator with controlled
clients, warmup, alternating order, CPU placement and raw per-round measurements.

Measure throughput, latency percentiles, CPU per successful response, idle/peak memory,
startup readiness and image size where relevant. State process RSS/PSS versus container/cgroup
and socket/kernel memory, compressed versus unpacked images, and what is excluded. For DB work
record warmed query counts as well as timing. Avoid compiling or running another load test
during timed rounds. Repeat only when a changed workload or unresolved concern warrants it.

Find the actual hot path before simplifying libraries, pools, caches or allocation. Prefer
existing direct queries, cached statements, shared compatibility primitives and bounded
buffers. Preserve zlib SIMD/allocator behavior while trimming feature flags. Do not port
SQLite-specific WAL/pool wins to MySQL by analogy.

Read [measurement.md](references/measurement.md) for workload/capacity traps and the measured
optimizations that transferred between these ports. Keep raw before/after evidence under
bench/results and update tables with the current state, with micro and end-to-end gains separate.
Forecasts need labeled assumptions and a real target-hardware test; they are not benchmark wins.
