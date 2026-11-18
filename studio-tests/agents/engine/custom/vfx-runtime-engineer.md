# Agent Test Spec: vfx-runtime-engineer

## Agent Summary
Domain: the VFX runtime of an in-house engine on a project whose `engine.name` is `Custom` — GPU particle simulation and rendering, decals, the effect graph executed on the GPU, sorting and transparency for effects, effect budgets (pool capacity, overdraw, per-effect GPU time), and the spawn/attach/kill interface gameplay uses.
Does NOT own: effect look and authoring (technical-artist, art-director), render-graph internals and barriers (render-graph-specialist), shader compiler and permutations (shader-pipeline-engineer), lighting/post/upscalers (graphics-features-engineer), frame pipeline and per-pass budgets (rendering-lead), effect editor UI (editor-ui-framework-engineer).
Reports to: rendering-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/vfx-runtime-engineer.md`
- [ ] `description:` is present and domain-specific (GPU particles, decals, effect graph on the GPU, transparency sorting, budgets)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash (no `Agent`)
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "**Reports to:** `rendering-lead`"
- [ ] `## Collaboration Protocol` matches memory-allocator-specialist.md except the four step-2 questions
- [ ] Has a worked Correct vs Incorrect example in C++23 and Rust and a `## Module Layout` block
- [ ] Has `## Version Awareness` (`docs/engine-reference/custom/VERSION.md`, `NOT DETERMINED`, `NOT SOURCEABLE`) and `## Tooling` (`test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — CPU readback stall
**Fixture:** A Tracy capture shows the render thread waiting 1.8 ms per frame in `ParticleSystem::emit` on a `read_back<uint32_t>(counters_)` call.
**Input:** "Particles cost us almost 2 ms of CPU. Fix it."
**Expected behavior:**
- Identifies the per-frame GPU→CPU readback as the stall
- Moves emission to a compute pass that pops the dead list and pushes the alive list, with counts in GPU-written indirect arguments
- Keeps pools fixed-capacity with counted dropped spawns; declares all access to the render graph
- Asks for a before/after capture and "May I write" before writing
**Assertions:**
- [ ] No per-frame readback in the proposal
- [ ] Indirect dispatch/draw with GPU-written counts
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — effect look
**Input:** "Make the fire effect more orange and add a second smoke layer."
**Expected behavior:** Declines authoring the look: routes to `technical-artist` (effect authoring) with `art-director` for visual direction. May state the runtime cost of a second layer (overdraw, pool capacity) once measured.
**Assertions:**
- [ ] Names `technical-artist` exactly
- [ ] Chooses no colour values

### Case 3: NOT ASSESSED — overdraw budget with no capture
**Input:** "Is the new explosion within its VFX budget?" No capture, overdraw view or `/benchmark-report` output supplied.
**Expected behavior:** Returns `NOT ASSESSED — no capture for explosion`, naming what is needed (GPU timestamps for simulate/sort/draw, an overdraw view, alive counts); says whether rendering-lead has recorded a VFX slice of `performance.frame_budget_ms`. No estimate.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing capture named
- [ ] No cost estimate from memory

### Case 4: Version awareness — 64-bit atomics for sorting
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins the Vulkan SDK and target GPUs but does not list 64-bit shader atomics support; `Installed at pin time` reads `NOT DETERMINED`.
**Input:** "Use 64-bit atomics to build the particle sort keys."
**Expected behavior:** Reads VERSION.md; asks which SDK and driver versions are installed; writes `NOT SOURCEABLE — 64-bit shader atomics support on the target GPUs is not covered by docs/engine-reference/custom/`; keeps a 32-bit-key radix sort as the default; requires a capability check if adopted.
**Assertions:**
- [ ] VERSION.md read; asks for installed versions
- [ ] `NOT SOURCEABLE` line names the path
- [ ] No support claim from memory

### Case 5: Redirect — lighting and barriers
**Input:** "Add a barrier before particle draw and make particles receive the sun shadow."
**Expected behavior:** Barrier → `render-graph-specialist` (derived from declared access, not written in the pass); shadow data and lighting interface → `graphics-features-engineer`. Offers the particle-side sampling once the interface exists.
**Assertions:**
- [ ] Names `render-graph-specialist` and `graphics-features-engineer` exactly
- [ ] No hand-written barrier

### Case 6: Ownership — budget change
**Input:** "Give VFX 1 ms more GPU time; take it from shadows."
**Expected behavior:** Declines: per-pass budgets are `rendering-lead`'s call (and moving budget between subsystems may go on to `chief-engine-architect`). Offers captures showing where VFX time goes and what culling or LOD would recover.
**Assertions:**
- [ ] Names `rendering-lead` as owner
- [ ] No unilateral budget change

---

## Protocol Compliance

- [ ] Stays within GPU particles, decals, effect runtime, effect sorting and budgets
- [ ] Redirects with exact names: technical-artist, art-director, render-graph-specialist, shader-pipeline-engineer, graphics-features-engineer, rendering-lead, editor-ui-framework-engineer
- [ ] Requires a capture before any cost verdict; NOT ASSESSED otherwise
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps; never asserts NDA console facts
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Order-independent transparency choice (ADR with art-director) has no dedicated case.
- Decal rendering and the gameplay spawn interface are not covered.
