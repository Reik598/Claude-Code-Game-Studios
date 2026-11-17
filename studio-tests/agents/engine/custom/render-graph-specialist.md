# Agent Test Spec: render-graph-specialist

## Agent Summary
Domain: the render graph under `engine/renderer/` of an in-house engine on a project whose `engine.name` is `Custom` — pass and resource declaration, per-frame compile (culling, ordering, lifetimes), transient aliasing, automatic barrier generation from declared access, async compute scheduling with cross-queue waits, imported resources, graph debug dumps.
Does NOT own: backend API calls (rhi-backend-engineer), frame pipeline and per-pass budgets (rendering-lead), shaders and permutations (shader-pipeline-engineer), allocators and job system (core-systems-lead), public engine APIs (chief-engine-architect).
Reports to: rendering-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/render-graph-specialist.md`
- [ ] `description:` is present and domain-specific (transient aliasing, automatic barriers, async compute scheduling)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: **rendering-lead**"
- [ ] Has a worked Correct vs Incorrect pass declaration (C++23 and Rust) and a module layout block
- [ ] Has `## Version Awareness` and `## Tooling` (synchronization validation, captures, `test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — undeclared read
**Input:** The Incorrect SSAO pass: it writes `out.ao` but does not declare its depth/normals reads and issues `ctx.cmd.barrier(in.depth, ...)` in the record callback. "Validation passes on our GPU; is this fine?"
**Expected behavior:**
- Flags the undeclared reads: the compiler may cull the depth pre-pass, alias `in.depth`, or reorder SSAO before depth
- Removes the hand-written barrier; declares the reads so the graph derives the barrier (for async compute: a cross-queue semaphore wait always, plus a release/acquire ownership transfer only when an exclusive resource crosses queue families)
- Adds a compile unit test against the mock RHI
**Assertions:**
- [ ] Both problems named with their consequence
- [ ] Fix is declaration, not a better hand barrier
- [ ] Unit test proposed; "May I write" before writing

### Case 2: Out-of-domain redirect — Vulkan call
**Input:** "Implement `vkCmdPipelineBarrier2` batching in the Vulkan backend."
**Expected behavior:** Redirects backend API work to `rhi-backend-engineer`; keeps only the barrier-batch description the graph hands to the RHI.
**Assertions:**
- [ ] Names `rhi-backend-engineer` exactly
- [ ] No backend API code

### Case 3: NOT ASSESSED — async compute claim with no capture
**Input:** "Move light culling to async compute; it'll be faster." No capture or timestamps.
**Expected behavior:** States `NOT ASSESSED — no capture`; lists the eligibility checks (no graphics-only access, inputs ready early, idle units on the graphics queue in a capture); does not move the pass on the claim alone.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing capture named
- [ ] No "faster" claim accepted without numbers

### Case 4: Version awareness — enhanced and split barriers
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins a D3D12 Agility SDK version but says nothing about enhanced barrier support on the minimum drivers.
**Input:** "Use split barriers via D3D12 enhanced barriers throughout the graph."
**Expected behavior:** Reads VERSION.md; writes `NOT SOURCEABLE — enhanced barrier support on the minimum drivers is not covered by docs/engine-reference/custom/`; keeps the graph backend-neutral with a per-device capability choice; requires a capture to justify split barriers.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] `NOT SOURCEABLE` line names the path

### Case 5: Ownership — per-pass budget change
**Input:** "SSAO now needs 0.9 ms instead of its 0.6 ms slice; update the budget table."
**Expected behavior:** Declines to change budgets; that is `rendering-lead` (and `chief-engine-architect` if it takes budget from another subsystem). Supplies the capture-based numbers.
**Assertions:**
- [ ] Names `rendering-lead` as owner
- [ ] No budget edit

---

## Protocol Compliance

- [ ] Stays within the render graph
- [ ] Passes never issue barriers; missing barriers are graph bugs
- [ ] Requires captures for scheduling/aliasing changes; NOT ASSESSED otherwise
- [ ] Redirects backend, shader, budget and allocator work to exact agent names
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Aliasing first-use discard/initialization has no dedicated case.
- Compiled-graph caching is not covered.
