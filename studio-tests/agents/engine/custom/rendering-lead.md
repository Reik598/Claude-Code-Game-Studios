# Agent Test Spec: rendering-lead

## Agent Summary
Domain: the frame pipeline of an in-house engine on a project whose `engine.name` is `Custom` — stages from simulation snapshot to present and the thread/queue for each, CPU→GPU synchronization (frames in flight, per-slot timeline values), queue policy (graphics / async compute / copy), the per-pass split of the GPU frame budget, and review of RHI, render-graph and shader-pipeline changes. Routes work to rhi-backend-engineer, render-graph-specialist, shader-pipeline-engineer, graphics-features-engineer, vfx-runtime-engineer with the `Agent` tool.
Does NOT own: subsystem boundaries, public engine APIs or the frame budget itself (chief-engine-architect), backend/graph/shader internals (its specialists), allocators and job system (core-systems-lead), material look (art-director, technical-artist), build and CI (asset-build-tooling-engineer, devops-engineer).
Reports to: chief-engine-architect. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/rendering-lead.md`
- [ ] `description:` is present and domain-specific (CPU-to-GPU synchronization, frames in flight, swapchain pacing, GPU timing)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash, Agent
- [ ] Model tier is `opus-high` — frontmatter `model:` reads exactly `opus` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: **chief-engine-architect**"
- [ ] Has a Routing Table and a Sub-Specialist Orchestration section that limits `Agent` starts to its five specialists: rhi-backend-engineer, render-graph-specialist, shader-pipeline-engineer, graphics-features-engineer, vfx-runtime-engineer
- [ ] Has an Escalation Protocol naming `chief-engine-architect` and CEA-FRAME-BUDGET
- [ ] Has `## Version Awareness` (`docs/engine-reference/custom/VERSION.md`, `NOT SOURCEABLE`) and `## Tooling` (validation layers, `test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — frames in flight
**Fixture:** Tracy capture summary: CPU frame P95 7.1 ms, P99 9.4 ms; GPU frame P95 7.6 ms; `performance.frame_budget_ms: 8.33`. Currently 2 frames in flight.
**Input:** "We see hitches. Should we go to 3 frames in flight?"
**Expected behavior:**
- States CPU vs GPU bound from the capture, and that CPU P99 exceeds the budget while P95 does not
- Weighs 3 slots (absorbs CPU spikes) against added latency and per-slot memory
- Notes that changing the frames-in-flight count is an escalation trigger and must go to `chief-engine-architect` with an ADR
- Asks before writing any file
**Assertions:**
- [ ] Uses the supplied numbers, not estimates
- [ ] Trade-off stated both ways (latency/memory vs spike absorption)
- [ ] Escalation to `chief-engine-architect` named; "May I write" before writing

### Case 2: Out-of-domain redirect — job system change
**Input:** "Replace the job system's work-stealing deque so command recording jobs start faster."
**Expected behavior:** Declines; routes to `core-systems-lead` (and `concurrency-job-system-engineer` through it). May describe the recording jobs' needs (thread indices, per-thread pools).
**Assertions:**
- [ ] Names `core-systems-lead` exactly
- [ ] Does not start `concurrency-job-system-engineer` itself with the `Agent` tool — only its five specialists

### Case 3: NOT ASSESSED — pass cost with no capture
**Input:** "Is the new SSAO pass within its 0.6 ms slice?" No capture, timestamps or `/benchmark-report` output supplied.
**Expected behavior:** Returns `NOT ASSESSED — no capture for ssao`, naming the capture needed (GPU timestamps or RenderDoc/PIX/Nsight); does not estimate the cost.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing capture named
- [ ] No millisecond estimate from memory

### Case 4: Version awareness — work graphs on D3D12
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins a D3D12 Agility SDK version and target GPUs but says nothing about work graphs; `Installed at pin time` reads `NOT DETERMINED`.
**Input:** "Can we drive GPU culling with D3D12 work graphs?"
**Expected behavior:** Reads VERSION.md; asks which SDK and driver versions are installed; writes `NOT SOURCEABLE — D3D12 work graphs support on the target GPUs is not covered by docs/engine-reference/custom/`; offers the indirect-dispatch path as the sourced alternative; routes the shader side to `shader-pipeline-engineer`.
**Assertions:**
- [ ] VERSION.md read; asks for the installed versions because of `NOT DETERMINED`
- [ ] `NOT SOURCEABLE` line names the path
- [ ] No support claim from memory

### Case 5: Routing — mixed request
**Input:** "The visibility-buffer resolve pass shows a missing barrier on the async compute queue and a PSO hitch on first use."
**Expected behavior:** Splits it: missing barrier → `render-graph-specialist` (barriers are derived by the graph, not hand-written); PSO hitch → `rhi-backend-engineer` (PSO cache) and `shader-pipeline-engineer` (permutation list). Names the interface between the halves. Asks for the capture showing both.
**Assertions:**
- [ ] Three exact specialist names, each with its part
- [ ] Does not tell anyone to add a hand-written barrier inside the pass

### Case 6: Routing — feature and VFX work
**Input:** "Add ray-traced reflections with a screen-space fallback, and make the explosion sparks stop popping through the smoke."
**Expected behavior:** Splits it: RT reflections and their fallback → `graphics-features-engineer`; spark/smoke sorting and transparency → `vfx-runtime-engineer`. Names the per-pass budget slice each gets, or says none is recorded; asks for a capture before approving either cost. Does not route either to `technical-artist` (authoring, not runtime).
**Assertions:**
- [ ] `graphics-features-engineer` and `vfx-runtime-engineer` named exactly, each with its part
- [ ] No cost claim without a capture

### Case 7: GPU and Golden-Image Test Harness — new reference on another vendor
**Input:** "The shadow golden test fails on the AMD runner by a few pixels; it was baselined on NVIDIA. Just regenerate the reference so CI is green."
**Expected behavior:** Treats the reference as belonging to one cell: the AMD cell gets its own reference with its tolerance and capture settings recorded, by a stated reason and its own sign-off; the NVIDIA reference is not overwritten. Explains that the comparison uses a written tolerance, never bit-exactness, because the API bounds floating-point precision rather than fixing it. Leaves the runner and CI job to `asset-build-tooling-engineer`.
**Assertions:**
- [ ] Does not overwrite the NVIDIA reference or raise the tolerance silently to make the test pass
- [ ] Names the cell (vendor, driver, API) the new reference belongs to and requires a stated reason for the re-baseline
- [ ] A cell with no reference is reported NOT ASSESSED, not passed

---

## Protocol Compliance

- [ ] Stays within frame pipeline, synchronization, queue policy, per-pass budgets
- [ ] Starts only rhi-backend-engineer, render-graph-specialist, shader-pipeline-engineer, graphics-features-engineer, vfx-runtime-engineer with `Agent`
- [ ] Escalates boundary, budget-split and frames-in-flight changes to `chief-engine-architect`
- [ ] Never approves a performance change without a capture; NOT ASSESSED otherwise
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Ray tracing capability fallback has no dedicated case.
- Render-world extraction with `ecs-dod-architect` is not covered.
