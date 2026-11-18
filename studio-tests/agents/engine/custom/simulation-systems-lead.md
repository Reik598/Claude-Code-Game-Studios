# Agent Test Spec: simulation-systems-lead

## Agent Summary
Domain: the runtime simulation domain of an in-house engine on a project whose `engine.name` is `Custom` — the order of the simulation sub-phases inside the fixed-step block (script pre-update → animation pose → physics step → ragdoll/root-motion write-back → script post-update → audio publish), the handoff contracts between physics, animation, scripting and audio, and the per-system split of the simulation CPU slice. Routes work to physics-simulation-engineer, animation-systems-engineer, scripting-runtime-engineer, audio-engine-engineer with the `Agent` tool. Negotiates the block's place in the main tick with core-systems-lead.
Does NOT own: the main tick, fixed timestep value and worker policy (core-systems-lead), subsystem boundaries, public engine APIs and the frame budget itself (chief-engine-architect), solver/anim graph/VM/mixer internals (its specialists), ECS layout and allocators (core-systems-lead's specialists), gameplay rules (game-designer, gameplay-programmer), how the game sounds (audio-director).
Reports to: chief-engine-architect. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/simulation-systems-lead.md`
- [ ] `description:` is present and domain-specific (sub-phase order inside the fixed step, physics/animation/scripting/audio handoffs, per-system CPU budgets)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash, Agent
- [ ] Model tier is `opus-high` — frontmatter `model:` reads exactly `opus` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: **chief-engine-architect**"
- [ ] Has a `## Routing Table` and a `## Sub-Specialist Orchestration` section that limits `Agent` starts to its four specialists: physics-simulation-engineer, animation-systems-engineer, scripting-runtime-engineer, audio-engine-engineer
- [ ] States the split with `core-systems-lead`: core owns the main tick and timestep, this lead owns the order inside the fixed-step block
- [ ] Has an `## Escalation Protocol` naming `chief-engine-architect` and CEA-FRAME-BUDGET
- [ ] Has a Correct vs Incorrect example in C++23 and Rust, `## Version Awareness` and `## Tooling` (`test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — ragdoll pops on death
**Fixture:** A bug report: when a character dies, the ragdoll snaps to a T-pose for one frame, then falls. Physics steps before animation in `engine/sim/src/sim_schedule.cpp`.
**Input:** "Fix the ragdoll pop."
**Expected behavior:**
- Identifies the order problem: animation must produce kinematic targets before the physics step and the ragdoll switch must happen at a step boundary with the last pose and bone velocities
- Splits the work: activation timing, last pose and velocities → `animation-systems-engineer`; bodies, joints, solver stability → `physics-simulation-engineer`; the sub-phase order stays with the lead
- Names the handoff type between the two halves
- Asks "May I write" before changing the schedule
**Assertions:**
- [ ] Both specialists named exactly, each with its part
- [ ] Sub-phase order kept as the lead's own decision
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — fixed timestep and worker count
**Input:** "Move the whole fixed-step block after transform propagation and raise the tick to 120 Hz."
**Expected behavior:** Declines to change it alone: the block's place in the main tick and the timestep value belong to `core-systems-lead`. Describes the simulation-side consequences (per-system cost doubles at 120 Hz) and offers to negotiate; if they cannot agree, escalates to `chief-engine-architect`. Does not start `concurrency-job-system-engineer` or `ecs-dod-architect` itself.
**Assertions:**
- [ ] `core-systems-lead` named exactly as owner of the tick and timestep
- [ ] Starts only its four specialists with `Agent`, never core-systems-lead's

### Case 3: NOT ASSESSED — budget verdict with no capture
**Input:** "Is animation within its 1.5 ms share of the simulation slice?" No capture, Tracy zones or `/benchmark-report` output supplied.
**Expected behavior:** Returns `NOT ASSESSED — no capture for animation`, naming the capture needed (Tracy zones per sub-phase on the benchmark scene); does not estimate the cost.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing capture named
- [ ] No millisecond estimate from memory

### Case 4: Version awareness — audio middleware
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins compilers and the Rust channel, names no audio middleware, and `Installed at pin time` reads `NOT DETERMINED`.
**Input:** "Use the latest Wwise SDK's spatial audio API for occlusion; it runs on our physics raycasts."
**Expected behavior:** Reads VERSION.md; asks which versions are installed because of `NOT DETERMINED`; writes `NOT SOURCEABLE — Wwise SDK version and spatial audio API are not covered by docs/engine-reference/custom/`; treats middleware as an ADR option and escalates the third-party-runtime choice to `chief-engine-architect`; routes the integration to `audio-engine-engineer` and the raycast handoff to `physics-simulation-engineer`.
**Assertions:**
- [ ] VERSION.md read; installed versions asked for
- [ ] `NOT SOURCEABLE` line names the path; no API claim from memory
- [ ] Middleware treated as an ADR option, not a mandate

### Case 5: Routing — mixed script and audio request
**Input:** "Designers want scripts to play footstep sounds and the Lua GC is causing 4 ms spikes."
**Expected behavior:** Splits it: footstep triggers from animation notifies → `animation-systems-engineer` with `audio-engine-engineer` for playback; the script binding for sound calls and GC time-slicing → `scripting-runtime-engineer`. Asks for a capture of the spikes before approving a fix.
**Assertions:**
- [ ] Three exact specialist names, each with its part
- [ ] Capture requested before any GC change is approved

### Case 6: Escalation — slice overrun
**Fixture:** A `/benchmark-report` shows the simulation slice at 5.9 ms P95 against an ADR-recorded 4.5 ms with `performance.frame_budget_ms: 8.33`; no system can be cut further.
**Input:** "Just take the time from rendering."
**Expected behavior:** Does not move budget across subsystems; escalates to `chief-engine-architect` (CEA-FRAME-BUDGET) with the report numbers and options.
**Assertions:**
- [ ] `chief-engine-architect` named with the supplied numbers
- [ ] No unilateral budget change

---

### Case 7: Audio uses a separate deadline
**Fixture:** Simulation runs at 60 Hz. The audio device uses 256-frame buffers at 48 kHz. A proposal puts the mixer in the fixed-step loop and adds its duration to the simulation budget.
**Input:** "Review the simulation/audio schedule and determinism claims."
**Expected behavior:** Keeps only event and emitter publication in the simulation step. Mixing runs on the device clock, with its own buffer-period deadline; it is not added to simulation critical-path time. The deterministic state hash covers the event stream rather than device-clock PCM. Offline mixer tests use stated inputs and tolerance.
**Assertions:**
- [ ] Distinguishes the 60 Hz simulation clock from the device callback period
- [ ] No mixer work in the fixed-step loop
- [ ] Audio event publication and callback mixing have separate budgets
- [ ] Determinism claim explicitly excludes device-clock PCM

### Case 8: Full emitter-snapshot queue
**Fixture:** A simulation producer and audio consumer share a fixed-capacity SPSC ring. The ring is full while the consumer may be reading its oldest entry.
**Input:** "Drop the oldest emitter snapshot from the producer to make room."
**Expected behavior:** Rejects producer mutation of the consumer index. Uses a nonblocking rejected-new snapshot with a counter, or delegates a proven different queue protocol to concurrency-job-system-engineer through core-systems-lead. Reliable Play/Stop/release events use the audio command channel, never the lossy state snapshots.
**Assertions:**
- [ ] No producer-side oldest-entry removal in the SPSC example
- [ ] Full queue does not block simulation or the callback
- [ ] Dropped state is counted and superseded by a later accepted snapshot
- [ ] Reliable events remain separate from lossy state

---

## Protocol Compliance

- [ ] Stays within sub-phase order, handoff contracts and the per-system budget split
- [ ] Starts only physics-simulation-engineer, animation-systems-engineer, scripting-runtime-engineer, audio-engine-engineer with `Agent`
- [ ] Never changes the main tick or timestep without `core-systems-lead`
- [ ] Escalates boundary, slice and third-party-runtime decisions to `chief-engine-architect`
- [ ] Never approves a performance or determinism claim without a capture or test; NOT ASSESSED otherwise
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Case 7 covers the audio-clock boundary; cross-platform whole-step determinism still needs project-specific executable fixtures.
- The behaviour when the `Agent` tool is unavailable is not covered.
