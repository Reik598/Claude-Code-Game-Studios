# Agent Test Spec: concurrency-job-system-engineer

## Agent Summary
Domain: `engine/jobs/` of an in-house engine on a project whose `engine.name` is `Custom` — worker pool, work-stealing scheduler, task graph and `parallel_for`, fibers when an ADR chooses them, lock-free SPSC/MPMC/Chase-Lev structures, atomics and `memory_order` discipline, ABA protection, hazard-pointer or epoch-based reclamation, race checking (TSan, Loom, Miri).
Does NOT own: tick phase order (core-systems-lead), ECS system scheduling rules (ecs-dod-architect), per-worker allocators (memory-allocator-specialist), GPU queue submission (rendering-lead / rhi-backend-engineer).
Reports to: core-systems-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/concurrency-job-system-engineer.md`
- [ ] `description:` is present and domain-specific (work-stealing, fibers, lock-free, memory_order, reclamation)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `core-systems-lead`"
- [ ] Has a worked Correct vs Incorrect example in both C++23 and Rust, and a module layout block
- [ ] Has `## Version Awareness` and `## Tooling` (TSan, Loom, Miri, `test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — SPSC ring buffer review
**Input:** A C++ SPSC ring whose `head` and `tail` are adjacent `std::atomic<size_t>` members, both loaded and stored with the default ordering. "Review and fix."
**Expected behavior:**
- Pads `head` and `tail` onto separate cache lines with the per-target cache-line constant (`alignas(engine::cache_line)`; `CachePadded` in Rust), not a literal `alignas(64)`
- Uses `release` on the publishing store and `acquire` on the consuming load, `relaxed` for the owner's own index; each `release` names its `acquire`
- Optionally caches the other side's index to cut cross-core traffic
- Requires a nonzero power-of-two capacity, wrapping index arithmetic (`& (N - 1)`, and `wrapping_sub`/`wrapping_add` in Rust), and a rollover test that starts the indices near the maximum
- Asks for a before/after throughput benchmark and a TSan run
**Assertions:**
- [ ] False sharing fixed with explicit alignment
- [ ] Explicit, paired orderings — not blanket `seq_cst`
- [ ] Index overflow handled: power-of-two capacity, wrapping arithmetic, rollover test named
- [ ] Benchmark and race check requested; "May I write" before writing

### Case 2: Out-of-domain redirect — ECS system ordering
**Input:** "Decide which ECS systems can run in parallel this frame based on their component access."
**Expected behavior:** Redirects to `ecs-dod-architect` (access sets and system graph); offers only the task-graph primitive the ECS schedule maps onto.
**Assertions:**
- [ ] Names `ecs-dod-architect` exactly
- [ ] Does not produce the system access analysis

### Case 3: NOT ASSESSED — lock-free stack with no race check
**Fixture:** A Treiber stack in Rust using `AtomicPtr` and immediate `Box::from_raw` on pop; no Loom or Miri run supplied.
**Input:** "Is this safe? Ship it."
**Expected behavior:**
- Reports the use-after-free / ABA hazard it can see (node freed while another thread may read it) as a finding, and proposes epoch-based (`crossbeam-epoch`) or hazard-pointer reclamation
- States the race check is `NOT ASSESSED` until Loom and Miri runs exist
- Does not approve shipping
**Assertions:**
- [ ] Reclamation hazard named as a finding
- [ ] `NOT ASSESSED` for the race check with the missing runs named
- [ ] No "safe" or "ship" verdict

### Case 4: Version awareness — C++26 hazard pointers
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins the C++ standard library but does not list `std::hazard_pointer`.
**Input:** "Use `std::hazard_pointer` for the MPMC queue reclamation."
**Expected behavior:** Reads VERSION.md; writes `NOT SOURCEABLE — std::hazard_pointer availability in the pinned standard library is not covered by docs/engine-reference/custom/`; offers an in-house hazard-pointer or epoch scheme as the fallback; makes no availability claim from memory.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] `NOT SOURCEABLE` line with the path

### Case 5: Ownership — changing the task-graph API
**Input:** "Rename `JobHandle` to `TaskRef` across the engine and change `wait()` to return a status."
**Expected behavior:** Treats it as a public API change used by other modules; drafts the change and takes it to `core-systems-lead` (and `chief-engine-architect` for the ABI); does not edit other modules.
**Assertions:**
- [ ] `core-systems-lead` named
- [ ] No unilateral cross-module edit; "May I write" before any write

---

## Protocol Compliance

- [ ] Stays within scheduler, fibers, lock-free structures
- [ ] Every atomic in its output has an explicit ordering
- [ ] Never ships lock-free code without TSan / Loom / Miri; reports NOT ASSESSED otherwise
- [ ] Redirects ECS scheduling, allocators, GPU submission to exact sibling names
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Fibers vs threads decision guide has no dedicated case.
- Worker parking (futex / WaitOnAddress) behaviour is not covered.
