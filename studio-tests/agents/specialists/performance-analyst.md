# Agent Test Spec: performance-analyst

## Agent Summary
Domain: Profiling, bottleneck identification, performance metrics tracking, and optimization recommendations.
Does NOT own: implementing optimizations (belongs to the appropriate programmer for that domain).
No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] `description:` field is present and domain-specific (references profiling / bottleneck analysis / performance metrics)
- [ ] `tools:` list includes Read, Write, Edit, Bash, Glob, Grep
- [ ] Model tier is `sonnet-high` — frontmatter `model:` reads exactly `sonnet` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Agent definition does not claim authority over implementing any optimization — explicitly identifies itself as analysis/recommendation only

---

## Test Cases

### Case 1: In-domain request — appropriate output
**Input:** "Analyze this frame time data: CPU 14ms, GPU 8ms, physics 6ms, draw calls 420, scripts 3ms."
**Expected behavior:**
- Identifies the primary bottleneck: the frame is CPU-bound (CPU 14ms vs GPU 8ms) — inside a 16.67ms (60fps) frame, but with under 3ms of headroom
- Breaks down contributors: physics (6ms, 43% of CPU time) is the top culprit
- Draw calls (420) flags as a secondary concern if the budget limit is lower (e.g., 200 draw calls per the project's `performance.draw_call_limit`)
- Produces a prioritized bottleneck report:
  1. Physics — 6ms, reduce simulation frequency or switch broadphase algorithm
  2. Draw calls — 420, implement batching or LOD
  3. Scripts — 3ms, profile hot paths
- Does NOT implement any of these optimizations

### Case 2: Out-of-domain request — redirects correctly
**Input:** "Implement the batching optimization to reduce draw calls from 420 to under 200."
**Expected behavior:**
- Does NOT produce implementation code for batching
- Explicitly states that implementing optimizations belongs to the owner of the system — `technical-artist`, whose rendering optimization covers batching (naming `engine-programmer` as well, for an engine-level rendering change the batching needs, is fine)
- Redirects the implementation to `technical-artist`, handing over its recommendation as the brief: the target (under 200 draw calls), estimated impact, and implementation cost

### Case 3: Regression identification
**Input:** "Performance dropped significantly after last week's commits. Frame time went from 10ms to 18ms."
**Expected behavior:**
- Compares profiles of a build from before the window (~10ms) and after it (~18ms); if no profile exists for either build, asks for or proposes the captures instead of guessing
- Localizes the 8ms delta to the frame-time categories that grew (gameplay logic, rendering, physics, AI, audio), not to a cause guessed from commit messages or diffs alone
- Names a suspect commit or system only when a profile supports it (e.g., profiles of builds inside the commit range) — never from commit messages or diffs alone
- Reports it under "Regressions Since Last Report" with the measured delta (10ms → 18ms) and the affected category, and recommends a fix owner rather than implementing the fix

### Case 4: Recommendation vs. code quality trade-off
**Input:** "The fastest optimization for the script bottleneck would be to inline all calls and remove abstraction layers."
**Expected behavior:**
- Surfaces the trade-off: inlining improves performance but reduces testability and violates the coding standard requiring unit-testable public methods
- Does NOT recommend the optimization without noting the code quality cost
- Escalates the trade-off to `technical-director`, the agent it reports to, for a decision
- Presents the options with their trade-offs — e.g., inlining only the hottest 2–3 methods, which keeps the public methods testable — rather than one all-or-nothing recommendation

### Case 5: Context pass — project performance budgets
**Input:** Performance budgets from the project config (`performance.*` in `project.yaml`) provided in context: Target 60fps, frame budget 16.67ms, draw calls max 200, memory ceiling 512MB. Request: "Review the current build profile."
**Expected behavior:**
- References the specific values from the provided context: 16.67ms, 200 draw calls, 512MB
- Compares current measurements against each threshold explicitly, in its Performance Report Format (Budget / Actual / Status tables for frame time and memory)
- Labels each metric's Status as OK or OVER based on the provided numbers
- Does NOT use different budget numbers than those provided in the context

### Case 6: On a Custom Engine Project — a benchmark regression
**Fixture:** `project.yaml` sets `engine.name: Custom`; a benchmark in `tests/benchmarks/` failed its threshold on last night's CI run; no regression response time is recorded; the bisect lands on a commit that changes only files under `engine/ui/`.
**Input:** "The frame got slower after last week's merges. Find out why and who fixes it."
**Expected behavior:**
- Confirms first: re-runs on the same machine, preset and GPU/driver; one noisy run is not a regression
- Bisects over CI build artifacts, then commits in the last good–bad range (`git bisect run` with the benchmark and its threshold)
- Attributes through `.claude/docs/custom-engine-layout.md`: the Lead of each changed path's row (the Owner where the Lead is `chief-engine-architect` or `none`; paths whose rows name different leads go to `chief-engine-architect`), so the `engine/ui/` commit goes to `lead-programmer`, the Lead of the `engine/ui/` row
- Does NOT pick the lead from a fixed list of engine leads that leaves out `lead-programmer`
- Hands over with the `/benchmark-report` before/after (P50/P95/P99, CPU and GPU separately), the commit and the budget slice it breaks
- Says "regression SLA NOT SET" rather than assuming a response time
**Assertions:**
- [ ] The regression is confirmed before it is bisected
- [ ] The regression goes to `lead-programmer`, the layout's Lead for `engine/ui/`
- [ ] "regression SLA NOT SET" is reported

### Case 7: Other engine — the same regression without the Custom section
**Fixture:** `project.yaml` sets `engine.name: Godot`; a frame-time capture got slower after last week's merges.
**Input:** "The frame got slower after last week's merges. Find out why and who fixes it."
**Expected behavior:**
- Profiles and reports with its normal workflow
- Does NOT attribute the regression to `core-systems-lead`, `rendering-lead`, `simulation-systems-lead`, `editor-architect` or `chief-engine-architect`, and does NOT route a budget change through `CEA-FRAME-BUDGET`
- Does NOT report "regression SLA NOT SET" as a Custom triage step
**Assertions:**
- [ ] The Custom section is not applied: no Custom engine lead, gate or Custom-only agent named

### Case 8: VR Frame Budgets — an average that hides missed frames
**Fixture**: `project.yaml` sets `engine.name: Custom`, `platform.targets: [PC, XR]`, `performance.target_framerate` and `performance.frame_budget_ms`; a headset capture averages under the budget but some frames finished after the display needed them.
**Input**: "Our VR capture averages under budget. Are we fine?"
**Expected behavior**:
- Takes the budget from `performance.frame_budget_ms` and the rate from `performance.target_framerate`, not from a figure assumed for the headset
- Counts each late frame as a missed display deadline and reports their number and when they occur beside P50/P95/P99, and does not pass the capture on its average
- On an OpenXR runtime, compares against the `predictedDisplayPeriod` the runtime reports
**Assertions**:
- [ ] The missed display deadlines are listed; the average does not decide the result
- [ ] No refresh rate is stated that the project's settings do not hold

### Case 9: VR Frame Budgets — refresh rate not set
**Fixture**: `project.yaml` sets `engine.name: Unity` and `platform.targets: [XR]`, and no `performance` block.
**Input**: "Profile the VR build against its budget."
**Expected behavior**:
- Reports the VR budget NOT ASSESSED because the refresh rate and budget are unset, and asks for them
- Does NOT assume a headset's refresh rate
**Assertions**:
- [ ] The verdict is NOT ASSESSED, not a pass

---

## Protocol Compliance

- [ ] Stays within declared domain (profiling, analysis, recommendations — not implementation)
- [ ] Redirects optimization implementation to the owner of the system (technical-artist for rendering optimizations such as batching, engine-programmer for engine systems) rather than implementing it
- [ ] Returns structured findings in its Performance Report Format (budget/actual/status tables, top bottlenecks with impact and recommendation, regressions)
- [ ] Escalates code-quality trade-offs to technical-director rather than deciding unilaterally
- [ ] Applies budget thresholds from provided context rather than assumed defaults
- [ ] Names who should implement each recommended optimization ("recommend and assign") instead of implementing it
- [ ] Asks "May I write this to [filepath]?" naming the file before writing

---

## Coverage Notes
- Frame time analysis (Case 1) output follows the agent's Performance Report Format; when run under `/perf-profile` or `/team-polish`, the report is written to `production/polish/`
- Regression case (Case 3) confirms the agent localizes the cause from profiles across builds, not just measures symptoms or guesses from diffs
- Code quality trade-off (Case 4) verifies the agent does not recommend optimizations that violate coding standards without flagging the conflict
