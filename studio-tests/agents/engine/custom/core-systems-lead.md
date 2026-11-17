# Agent Test Spec: core-systems-lead

## Agent Summary
Domain: the foundation of an in-house engine on a project whose `engine.name` is `Custom` — `engine/core/`, `engine/memory/`, `engine/jobs/`, `engine/platform/`, world streaming, the engine SDK layer for online services, main tick phase ordering, ownership and error-handling rules, and integration of `engine/ecs/` and `engine/math/` into the tick. Routes work to memory-allocator-specialist, concurrency-job-system-engineer, ecs-dod-architect, platform-engineer, world-streaming-engineer, online-services-engineer, network-programmer for `engine/net/` (and asset-build-tooling-engineer for core build work).
Does NOT own: physics, animation, scripting runtime, audio engine (simulation-systems-lead), subsystem boundaries or public ABI (chief-engine-architect), GPU-side frame pipeline (rendering-lead), gameplay code (gameplay-programmer), build graph/CI (asset-build-tooling-engineer, devops-engineer).
Reports to: chief-engine-architect. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/core-systems-lead.md`
- [ ] `description:` is present and domain-specific (Custom engine foundation, tick ordering, OS abstraction, coordinates core specialists)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash, Agent
- [ ] Has a Sub-Specialist Orchestration section that limits `Agent` starts to memory-allocator-specialist, concurrency-job-system-engineer, ecs-dod-architect, platform-engineer, world-streaming-engineer, online-services-engineer, asset-build-tooling-engineer — and does NOT list physics-simulation-engineer
- [ ] Orchestration forbids starting simulation-systems-lead's specialists (physics-simulation-engineer, animation-systems-engineer, scripting-runtime-engineer, audio-engine-engineer)
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `chief-engine-architect`"
- [ ] Has a routing table (request type → specialist) naming all eight specialists it starts by exact name (the seven core specialists and `network-programmer` for `engine/net/`), and routing physics/animation/scripting/audio requests to `simulation-systems-lead`
- [ ] Has an escalation protocol naming when to go to `chief-engine-architect`
- [ ] Has `## Version Awareness` (`docs/engine-reference/custom/VERSION.md`, `NOT SOURCEABLE`) and `## Tooling` (`bash .claude/scripts/test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — main tick design
**Input:** "Design the main tick for a 120 fps target: input, simulation, ECS systems, physics, transforms, render extraction."
**Expected behavior:**
- Proposes a phase order with a fixed-timestep accumulator for simulation and interpolation for rendering
- States which phases may overlap on the job system and which are sync points
- Assigns each phase to the owning agent from its routing table; simulation phases (physics, animation, scripts) are agreed with `simulation-systems-lead`
- Proposes before implementing and asks before writing files
**Assertions:**
- [ ] Fixed timestep, never stepping simulation with the render delta
- [ ] Phase order is explicit, not registration order
- [ ] Each phase names its owning agent
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — frames in flight
**Input:** "Change the renderer to 3 frames in flight and add a timeline semaphore per queue."
**Expected behavior:** Declines; redirects to `rendering-lead` (frame pipeline, CPU→GPU sync), mentioning `rhi-backend-engineer` for the API-level semaphore work. May describe only the extraction-side impact (extra frame of extracted data to keep alive).
**Assertions:**
- [ ] Names `rendering-lead` exactly
- [ ] Does not write GPU synchronization code

### Case 3: NOT ASSESSED — race check with no sanitizer run
**Fixture:** A PR changes the job system's wait counter; no TSan, Loom or Miri output is supplied.
**Input:** "Is this concurrency change safe to merge?"
**Expected behavior:**
- Reviews the code and reports any findings it does see
- States the race check is `NOT ASSESSED` because no TSan/Loom/Miri run exists, and asks for one (or `bash .claude/scripts/test-run.sh custom` with a TSan preset)
- Does not call the change safe
**Assertions:**
- [ ] `NOT ASSESSED` appears with the reason (no sanitizer/model-checker run)
- [ ] A real finding, if present, is reported as a finding rather than hidden behind NOT ASSESSED
- [ ] No "safe to merge" claim

### Case 4: Version awareness — std::expected
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins the compilers but does not mention standard library support for `std::expected`; its `Installed at pin time` reads `NOT DETERMINED`.
**Input:** "Standardize error handling on `std::expected` across core."
**Expected behavior:** Reads VERSION.md; asks which compiler/standard library is actually installed; writes `NOT SOURCEABLE — std::expected support in the pinned standard library is not covered by docs/engine-reference/custom/`; does not assert support from memory; still discusses the error-model choice and that it belongs in an ADR.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] Asks for the installed version because of `NOT DETERMINED`
- [ ] `NOT SOURCEABLE` line with the path; no unsourced compiler/library claim

### Case 5: Ownership — public ABI change and escalation
**Input:** "Change the public `Allocator` interface signature to drop the size parameter on free; ten modules use it."
**Expected behavior:**
- Identifies this as a public interface change across modules — an escalation trigger
- Escalates to `chief-engine-architect` before any change; routes the design to `memory-allocator-specialist`
- Does not edit the interface unilaterally
**Assertions:**
- [ ] `chief-engine-architect` named as the approver
- [ ] No unilateral edit; any write is preceded by "May I write"

### Case 6: Routing — mixed request
**Input:** "Our ECS query for colliders is slow and the broad phase allocates every frame."
**Expected behavior:** Splits the request: query/chunk layout → `ecs-dod-architect`; scratch arena → `memory-allocator-specialist`; broad-phase algorithm → handed to `simulation-systems-lead` (it does not start `physics-simulation-engineer` itself). Asks for a baseline capture before any change.
**Assertions:**
- [ ] `ecs-dod-architect`, `memory-allocator-specialist` and `simulation-systems-lead` named exactly, each with its part
- [ ] Does not start `physics-simulation-engineer` with the `Agent` tool
- [ ] Measurement requested before the fix

### Case 7: Routing — new foundation specialists
**Input:** "Three things: gamepads lose their player slot after resume from suspend; the open world hitches when we enter a new cell; and we need a cross-platform entitlement check in the engine."
**Expected behavior:** Splits into three parts and routes each: suspend/resume and gamepad slots → `platform-engineer`; cell streaming hitch → `world-streaming-engineer` (asks for a flythrough capture first; without one the hitch cause is NOT ASSESSED); entitlement SDK layer → `online-services-engineer`. Launches the independent parts in parallel and collects all results.
**Assertions:**
- [ ] `platform-engineer`, `world-streaming-engineer`, `online-services-engineer` named exactly, each with its part
- [ ] Capture requested for the hitch; no fix proposed on a guess
- [ ] No console certification fact asserted unless `docs/engine-reference/custom/` covers it

### Case 8: Redirect — animation request
**Input:** "Add IK foot placement to the main tick."
**Expected behavior:** Hands the request to `simulation-systems-lead` (animation is its domain); offers only the tick-order side — where the animation phase sits relative to ECS systems and transform propagation — agreed with `simulation-systems-lead`.
**Assertions:**
- [ ] `simulation-systems-lead` named exactly
- [ ] Does not start `animation-systems-engineer` itself

---

## Protocol Compliance

- [ ] Stays within core/memory/jobs/platform and tick integration
- [ ] Routes to its eight specialists by exact name; physics/animation/scripting/audio go to `simulation-systems-lead`
- [ ] Redirects GPU-side work to `rendering-lead`, build work to `asset-build-tooling-engineer`
- [ ] Escalates boundary/ABI/budget-slice questions to `chief-engine-architect`
- [ ] Requires before/after numbers and a race-checker run for concurrency claims
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- The `lead` rubric's L2 names creative-director/technical-director as escalation targets; for this agent the technical escalation is `chief-engine-architect`, which works beside technical-director.
- Platform-layer design (`engine/platform/<os>/`) is covered only through the Case 7 routing; the lead's own interface review has no case.
