# Memory Invariants

<!-- Custom-engine projects only (engine.name: Custom). Lives at
     docs/architecture/memory-invariants.md. session-start.sh re-injects the
     FIRST 40 LINES after every compaction, so the hard rules go first, one line
     each, and the rationale goes below the fold. Owner: memory-allocator-specialist,
     reviewed by core-systems-lead; a change here needs an ADR (CEA-ADR). -->

**Last updated**: [date] · **ADRs**: [ADR-XXXX, …] · **Target**: [platforms]

## Hard rules (keep this block under 30 lines)

1. No general-purpose heap allocation on the game, render or audio thread after
   load, except through [named allocator]. Per-frame scratch: [frame arena, N per frame in flight].
2. Ownership: every allocation has exactly one owner named in its type
   ([unique handle / arena lifetime / pool handle]); raw pointers never own.
3. Lifetimes: arena memory never outlives its reset ([frame / level / app]);
   handles are generation-checked ([N]-bit generation).
4. Cross-thread data: [immutable after publish / owned by one job / message passed];
   no shared mutable state without the primitive named in [ADR].
5. Alignment: hot per-thread state and atomics padded to `engine::cache_line`
   (the per-target constant, concurrency-job-system-engineer).
6. GPU memory: sub-allocated from [heap strategy]; nothing freed while a frame
   in flight may still read it ([N] frames in flight).
7. Budgets (peak, per platform): see the table below; exceeding one is a bug.
8. Debug builds: guard bytes + fill patterns + per-tag leak report at shutdown;
   sanitizer runs: [ASan/LSan/TSan or Miri] in CI on [cadence].

## Memory budgets

| Tag / subsystem | Allocator | Steady (MB) | Peak (MB) | Platform | Source of the number |
|---|---|---|---|---|---|
| [e.g. renderer transient] | [render-graph aliasing heap] | | | | [capture / estimate] |
| [e.g. streaming pool] | [buddy] | | | | |
| **Total** | | | | | must fit `performance.memory_ceiling_mb` |

A number with no source is an estimate and is marked so; `/memory-audit` and
`/benchmark-report` replace estimates with measurements.

## Allocator map

| Allocator | Kind (linear / pool / slab / buddy / TLSF) | Thread model | Reset / free pattern | Owner module |
|---|---|---|---|---|
| | | | | |

## Rationale and exceptions

[Why each hard rule exists, the ADR behind it, and every accepted exception
with its expiry: "audio decoder may allocate during voice start until ADR-00NN lands".]
