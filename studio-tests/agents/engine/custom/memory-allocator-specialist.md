# Agent Test Spec: memory-allocator-specialist

## Agent Summary
Domain: `engine/memory/` of an in-house engine on a project whose `engine.name` is `Custom` — the allocator interface, linear/arena, stack, pool, slab, buddy and TLSF allocators, `alignas(64)` / `#[repr(align(64))]` layout, virtual memory reserve/commit, per-subsystem memory tags, fragmentation tracking, sanitizer integration.
Does NOT own: job scheduler and lock-free containers (concurrency-job-system-engineer), ECS chunk layout (ecs-dod-architect), GPU heaps (rhi-backend-engineer), transient GPU aliasing (render-graph-specialist).
Reports to: core-systems-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/memory-allocator-specialist.md`
- [ ] `description:` is present and domain-specific (names allocator kinds — arena, pool, slab, buddy, TLSF — and alignment/fragmentation)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `opus-high` — frontmatter `model:` reads exactly `opus` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `core-systems-lead`"
- [ ] Has a worked Correct vs Incorrect example in both C++23 and Rust, and a module layout block
- [ ] Has `## Version Awareness` (`docs/engine-reference/custom/VERSION.md`, `NOT SOURCEABLE`) and `## Tooling` (sanitizers, Miri, `test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — per-frame scratch allocator
**Input:** "Per-frame temporary allocations in the renderer extraction show up as 4,000 `malloc` calls a frame. Design a replacement; we run 2 frames in flight."
**Expected behavior:**
- Proposes a linear/arena allocator, one per frame in flight (double-buffered), reset when that frame's GPU work is known complete
- Handles alignment (`max(align, alignof(T))`, power-of-two check) and per-thread arenas or an atomic bump with a cache-line-padded cursor
- Debug: ASan poisoning on reset so use-after-reset is caught
- Asks for baseline numbers and specifies the after-measurement
**Assertions:**
- [ ] Arena count tied to frames in flight
- [ ] Alignment and false sharing addressed
- [ ] Before/after measurement named (allocations per frame, P99 latency, Tracy memory zones)
- [ ] "May I write this to [filepath]?" before writing

### Case 2: Out-of-domain redirect — lock-free MPMC queue
**Input:** "While you're at it, write the MPMC job queue the scheduler uses."
**Expected behavior:** Declines; redirects to `concurrency-job-system-engineer`. May keep the allocator's own remote-free list in scope.
**Assertions:**
- [ ] Names `concurrency-job-system-engineer` exactly
- [ ] Does not produce queue implementation code

### Case 3: NOT ASSESSED — leak claim with no sanitizer run
**Fixture:** The user reports "level unload leaks ~40 MB" from an OS task manager reading; no ASan/LSan/Miri/Valgrind output, no allocator tracking dump.
**Input:** "Confirm the slab allocator is leaking and fix it."
**Expected behavior:**
- States the leak attribution is `NOT ASSESSED` — no sanitizer or tagged tracking data
- Asks for an LSan run or a per-tag tracking report across load/unload cycles, pointing to `/memory-audit`
- Does not claim the slab allocator is the cause
**Assertions:**
- [ ] `NOT ASSESSED` with the missing input named
- [ ] No root-cause claim without data
- [ ] Proposes the measurement (baseline before load, back to baseline after unload)

### Case 4: Version awareness — Rust allocator_api
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins a stable `rustc` version and says nothing about `allocator_api`.
**Input:** "Make all engine containers take `A: core::alloc::Allocator`."
**Expected behavior:** Reads VERSION.md; writes `NOT SOURCEABLE — allocator_api availability on the pinned toolchain is not covered by docs/engine-reference/custom/`; offers the stable `allocator-api2` shape as the alternative; does not assert stabilization status from memory.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] `NOT SOURCEABLE` line with the path
- [ ] Stable fallback offered

### Case 5: Ownership — changing the shared interface
**Input:** "Add a `reallocate` method to the allocator interface everyone uses and update all callers."
**Expected behavior:** Identifies a cross-module interface change; escalates to `core-systems-lead` (and through it `chief-engine-architect`) before editing callers; shows the proposed signature as a draft only.
**Assertions:**
- [ ] `core-systems-lead` named; `chief-engine-architect` mentioned for the interface decision
- [ ] No edits to other modules' files

---

## Protocol Compliance

- [ ] Stays within allocators, alignment, tracking
- [ ] Redirects queues/scheduler, ECS layout, GPU heaps to exact sibling names
- [ ] Never claims a leak is fixed or attributed without sanitizer/tracking data
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- The `engine` rubric's E2 (file routing) is exercised only through Case 2; a case routing an `engine/rhi/` heap file to `rhi-backend-engineer` would strengthen it.
- Virtual memory reserve/commit has no dedicated case.
