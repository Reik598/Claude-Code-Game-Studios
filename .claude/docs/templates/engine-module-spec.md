# Engine Module Spec: [Module Name]

<!-- Custom-engine projects only (engine.name: Custom). The engine-side
     counterpart of a GDD: one per engine module (engine/<module>/), in
     docs/architecture/modules/<module>.md. Decisions go to ADRs
     (/architecture-decision, engine mode); this spec states what the module
     must do and how it is held to it. Owner: the module's specialist; reviewed
     by its lead and chief-engine-architect. -->

## Document Status
- **Version**: [n] · **Last Updated**: [date] · **Author**: [agent/person]
- **Owner agent**: [e.g. render-graph-specialist] · **Lead**: [e.g. rendering-lead]
- **ADRs**: [ADR-XXXX, …] · **Status**: Draft | Reviewed | Accepted

## 1. Purpose
[Two or three sentences: what the module provides and what it explicitly does not.]

## 2. Public Interface
| Header / trait | Type or function | Stability (stable / experimental / internal) | Since |
|---|---|---|---|
| `engine/<module>/include/...` (C++) or `engine/<module>/src/lib.rs` (Rust crate) | | | |
ABI rule for this module: [C ABI at the plugin boundary? versioned structs?]

## 3. Dependencies
- Depends on: [modules, third-party libraries with pinned versions in `docs/engine-reference/custom/VERSION.md`]
- Depended on by: [modules] — the engine never depends on `game/`.

## 4. Threading Model
[Which threads/jobs call in; what is thread-safe; sync primitives; contention points.]

## 5. Memory
[Allocators used (see `memory-invariants.md`), lifetimes, steady and peak footprint per platform.]

## 6. Performance Budget
[Rows this module owns in `frame-budget.md`; worst-case inputs; scaling limits (e.g. 100k entities).]

## 7. Determinism and Platform Matrix
[Deterministic? under which conditions. Platforms × graphics APIs supported; known gaps.]

## 8. Failure Modes
[Device lost, out of memory, corrupt asset, timeout — what the module does, and what it reports.]

## 9. Tuning Knobs
[Data-driven values, where they live, safe ranges.]

## 10. Test Plan and Acceptance Criteria
<!-- On Custom this spec stands in for a GDD: /create-epics makes one epic per
     spec, and each story /create-stories writes quotes one of these criteria
     (/story-readiness checks it does). A frame-budget slice in section 6 makes
     the module's stories `Frame pipeline: yes`. -->
- Unit: `tests/unit/<module>/` — [cases]
- Integration: `tests/integration/<module>/` — [cases]
- Benchmarks: `tests/benchmarks/<module>/` — [threshold per benchmark]
- Done when: [testable criteria; each names the test or capture that proves it]

## 11. Consumer and Handoff Contracts
[Engine/game and subsystem consumers; input/output units and coordinate spaces,
thread/queue, lifetime, synchronization, failure policy and contract tests.
For Rust, name the actual workspace member path and registered test targets.]

## Open Questions
[Each with an owner and the ADR it would become.]
