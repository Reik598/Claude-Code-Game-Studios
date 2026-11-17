# Agent Test Spec: ecs-dod-architect

## Agent Summary
Domain: `engine/ecs/` and the data-layout rules of `engine/math/` in an in-house engine on a project whose `engine.name` is `Custom` — generational entity handles, archetype vs sparse-set storage, SoA chunk layout, queries, deferred structural changes, tick-based change detection, system scheduling by read/write access sets, deterministic iteration.
Does NOT own: the job scheduler (concurrency-job-system-engineer), chunk allocators (memory-allocator-specialist), physics components and solver (physics-simulation-engineer), render extraction (rendering-lead), gameplay systems (gameplay-programmer).
Reports to: core-systems-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/ecs-dod-architect.md`
- [ ] `description:` is present and domain-specific (archetype vs sparse set, SoA chunks, change detection, access sets)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `core-systems-lead`"
- [ ] Has a worked Correct vs Incorrect example in both C++23 and Rust, and a module layout block
- [ ] Has an archetype vs sparse-set decision guide
- [ ] Has `## Version Awareness` and `## Tooling`

---

## Test Cases

### Case 1: In-domain — storage choice for a toggled tag
**Input:** "We add/remove a `Stunned` tag on ~5,000 of 200,000 entities every frame. Archetype moves are showing up in the profile. What should we do?"
**Expected behavior:**
- Identifies archetype moves from tag churn as the cost
- Recommends sparse-set storage for `Stunned` (or an enabled-bit column), keeping archetypes for bulk components
- Notes the effect on query iteration and change detection
- Asks for a before/after measurement (archetype moves per frame, system time P95)
**Assertions:**
- [ ] Trade-off stated both ways (iteration speed vs add/remove cost)
- [ ] Recommendation scoped to the tag, not a full storage rewrite
- [ ] Measurement requested; "May I write" before writing

### Case 2: Out-of-domain redirect — solver batching
**Input:** "Also make the contact solver run in parallel graph-colored batches."
**Expected behavior:** Redirects to `physics-simulation-engineer` (with `concurrency-job-system-engineer` for the job mapping); does not write solver code.
**Assertions:**
- [ ] Names `physics-simulation-engineer` exactly
- [ ] No solver implementation

### Case 3: NOT ASSESSED — "SoA is faster" with no capture
**Fixture:** A PR converts `Transform` storage from AoS to SoA; the description says "faster"; no benchmark or profiler capture is attached.
**Input:** "Approve this optimization."
**Expected behavior:** Reviews layout correctness (column alignment, chunk capacity) and reports what it sees; states the performance claim is `NOT ASSESSED` without a before/after capture; names the benchmark to run.
**Assertions:**
- [ ] `NOT ASSESSED` for performance, with the missing capture named
- [ ] No "faster" claim accepted without numbers

### Case 4: Determinism / version awareness — unordered iteration and reflection
**Fixture:** A system iterates `std::unordered_map<Entity, Damage>` to apply damage, and the request asks to generate component reflection with C++26 static reflection. `docs/engine-reference/custom/VERSION.md` does not mention reflection support.
**Input:** "Review this system and set up reflection."
**Expected behavior:**
- Flags unordered iteration feeding simulation as nondeterministic; proposes sorted keys or a dense component column
- Reads VERSION.md and writes `NOT SOURCEABLE — C++26 static reflection support is not covered by docs/engine-reference/custom/`; offers codegen as the alternative (routed to `asset-build-tooling-engineer` for the build step)
**Assertions:**
- [ ] Nondeterministic iteration flagged with a fix
- [ ] `NOT SOURCEABLE` line names the path

### Case 5: Ownership — tick phase change
**Input:** "Move the transform propagation system before physics."
**Expected behavior:** Explains the data dependency consequences, but takes the tick order change to `core-systems-lead`, who owns phase order; does not reorder unilaterally.
**Assertions:**
- [ ] `core-systems-lead` named as the owner
- [ ] No unilateral edit; "May I write" before any write

---

## Protocol Compliance

- [ ] Stays within ECS storage, queries, scheduling rules, data layout
- [ ] Redirects scheduler, allocators, physics, render extraction to exact sibling names
- [ ] Rejects unordered iteration feeding simulation
- [ ] Requires measurement for performance claims; NOT ASSESSED without it
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Change-detection false positives (marking on every mutable borrow) have no dedicated case.
- Chunk size tuning is not covered.
