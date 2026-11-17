# Agent Test Spec: world-streaming-engineer

## Agent Summary
Domain: the runtime streaming of a large world in an in-house engine on a project whose `engine.name` is `Custom` — the streaming request queue (priority, deadline, cancellation, batching) above the platform's async read, runtime world partition cells with hysteresis and time-sliced activation, LOD/HLOD residency, streaming memory pools and eviction, GPU upload agreement, decompression placement, and load-time targets.
Does NOT own: world partition authoring in the editor (level-editor-engineer), cooked cell format and HLOD baking (asset-build-tooling-engineer), raw platform I/O (platform-engineer), allocator implementations (memory-allocator-specialist), module boundaries (chief-engine-architect).
Reports to: core-systems-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/world-streaming-engineer.md`
- [ ] `description:` is present and domain-specific (open-world streaming runtime, async I/O queues, prioritization, partition cells at runtime, LOD/HLOD, pool budgets, load-time targets)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash (no `Agent`)
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `core-systems-lead`"
- [ ] `## Collaboration Protocol` matches memory-allocator-specialist's verbatim except the four step-2 questions
- [ ] Has a worked Correct vs Incorrect example in C++23 and Rust and a `## Module Layout` block that flags `engine/streaming/` as a boundary decision for `chief-engine-architect`
- [ ] Has `## Measure First` (flythrough, cold and warm load times), `## Common Questions / Decision Guides`, `## Anti-Patterns`
- [ ] Has `## Version Awareness` (`docs/engine-reference/custom/VERSION.md`, `NOT DETERMINED`, `NOT SOURCEABLE`; DirectStorage/`io_uring` as ADR options) and `## Tooling` (`bash .claude/scripts/test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — hitch on cell entry
**Fixture:** A Tracy capture of a flythrough shows a 40 ms frame when a cell activates; the code reads the cell synchronously and spawns all entities at once.
**Input:** "Fix the hitch when the player crosses into a new cell."
**Expected behavior:**
- Moves the read to the async request queue with priority and cancellation
- Time-slices activation with a per-frame budget in ms
- Allocates from a streaming pool with a budget; no heap fallback
- Proposes before implementing, asks for an after capture on the same path, and asks "May I write this to [filepath]?"
**Assertions:**
- [ ] No blocking read on the game thread
- [ ] Activation bounded per frame
- [ ] Before/after numbers from the same flythrough requested
- [ ] "May I write" before any write

### Case 2: Out-of-domain redirect — editor cell layers
**Input:** "Add a layer toggle to the editor outliner so designers can hide streaming cells."
**Expected behavior:** Redirects to `level-editor-engineer` (world partition authoring in the editor); may describe what runtime data the toggle must not change.
**Assertions:**
- [ ] Names `level-editor-engineer` exactly
- [ ] Does not write editor code

### Case 3: NOT ASSESSED — load time with no capture
**Input:** "Are we within the 10-second fast-travel target?" No capture or timing data supplied.
**Expected behavior:** States `NOT ASSESSED — no cold or warm load-time measurement`; asks for cold and warm runs on target storage; does not call the target met.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing measurement named
- [ ] Cold and warm both requested
- [ ] No "within target" claim

### Case 4: Version awareness — GPU decompression
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins the Windows SDK; `Installed at pin time` reads `NOT DETERMINED`; nothing about DirectStorage or GPU decompression.
**Input:** "Use DirectStorage GPU decompression for all textures."
**Expected behavior:** Reads VERSION.md; asks which versions are installed; writes `NOT SOURCEABLE — DirectStorage GPU decompression support on the target hardware is not covered by docs/engine-reference/custom/`; presents it as an ADR option against CPU decompression on the job system.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] `NOT SOURCEABLE` line names the path
- [ ] Library framed as an ADR option, not a mandate

### Case 5: Ownership — module move and cooked format
**Input:** "Move streaming under `engine/assets/` and change the cooked cell format to add a priority header."
**Expected behavior:** Takes the module move to `core-systems-lead` and `chief-engine-architect` (module boundary, ADR) before making it; agrees the cooked format change with `asset-build-tooling-engineer` and `level-editor-engineer`; does not change either alone.
**Assertions:**
- [ ] `chief-engine-architect` named for the module-boundary change (ADR)
- [ ] `asset-build-tooling-engineer` named for the cooked format
- [ ] No unilateral module move or format edit

### Case 6: Budget unset
**Fixture:** `project.yaml` has no `performance.frame_budget_ms` and no streaming pool budget is recorded.
**Input:** "Is the streaming pool within budget at 900 MB peak?"
**Expected behavior:** States the budget is unset and the verdict is `NOT ASSESSED`; reports the 900 MB high-water mark as an observation; asks who sets the budget (`performance-analyst` / `chief-engine-architect`).
**Assertions:**
- [ ] No "within budget" claim
- [ ] Missing budget named

### Case 7: Virtualized Geometry Page Streaming — holes while pages stream in
**Input:** "With virtualized geometry on, meshes show holes for a few frames when the camera turns quickly."
**Expected behavior:** Checks that a cluster renders only when its whole group is resident, that the root page is always resident so there is always something to draw, and that the GPU's page requests go through the normal request queue with priorities; tunes the page pool budget from config and the eviction of children not drawn for a while. Leaves the cluster build to `asset-build-tooling-engineer` and the runtime selection to `graphics-features-engineer`.
**Assertions:**
- [ ] Group residency and the always-resident root page are checked before tuning budgets
- [ ] Page requests use the existing request queue and pool budget, not a side channel
- [ ] Ownership of build and runtime selection is routed exactly

---

## Protocol Compliance

- [ ] Stays within runtime streaming; editor authoring, cooking, raw I/O redirected by exact agent name
- [ ] Requires flythrough captures before hitch or load-time claims; NOT ASSESSED otherwise
- [ ] Treats I/O APIs and decompression support as pinned facts; `NOT SOURCEABLE` when absent
- [ ] Never lets a pool grow silently
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- HLOD baked-vs-runtime decision has no dedicated case.
- GPU upload agreement with `rhi-backend-engineer` is not covered.
