# /team-frame-pipeline — Pipeline (Phases 1 to 6)

> Part of `/team-frame-pipeline`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Pipeline

**In this file:**

- Phase 1: Frame the change
- Phase 2: Impact proposals (parallel)
- Phase 3: Resolve conflicts, ADRs and CEA-ADR
- Phase 4: Implementation
- Phase 5: Verification
- Phase 6: Frame budget gate (CEA-FRAME-BUDGET) and sign-off

### Phase 1: Frame the change

Before spawning, gather once: the change description, the ADRs that govern the
tick, jobs, ECS, simulation (physics, animation, scripting, audio) and frame graph (registry first —
`docs/registry/architecture.yaml` — then those ADRs by section), and
`docs/architecture/memory-invariants.md` if it exists.

**Baseline capture.** `--baseline <capture>` names a capture of the current
frame before the change. Without it, ask for one (or for permission to proceed
without). Proceeding without one is allowed, and Phase 5 then reports
`regression NOT ASSESSED — no baseline capture`.

**Regression threshold.** A baseline needs a threshold, or the comparison
cannot call a regression (`/benchmark-report` has no default). Take
`--threshold <percent>`; else, when the baseline is a `/benchmark-report`
report, its `Threshold:` line (say it was read from there); else ask for it
together with the baseline (2 %, 5 %, 10 %). In `autonomous` mode with none
given or recorded, nothing is asked: Phase 5 reports
`regression NOT ASSESSED — no threshold given with the baseline`, and the
verdict line says so.

Delegate to **chief-engine-architect**:
- State the change: which stage of the tick or which frame-graph passes it
  touches, and what it must not touch (subsystem boundaries, public engine API)
- Allocate the frame budget: ms per thread and per GPU queue the change may use,
  against the Phase 0 budget (or its NOT ASSESSED line)
- List the governing ADRs and whether each is Accepted; name any decision the
  change needs that no ADR covers
- Output: `production/engine/[change]-frame.md`, opening with two header
  lines: `Story: <--story path | none>` and `Module: <the spec path of each
  changed module, docs/architecture/modules/<module>.md, comma-separated>`.
  `/story-done` matches an engine story's perf evidence on these lines.

**Gate**: present the framing via `AskUserQuestion` — `[A] Proceed to impact
proposals` / `[B] Revise the framing` / `[C] Stop here`.

### Phase 2: Impact proposals (parallel)

Spawn all four at once (the active set permitting), each with Phase 1's framing
inline. Each proposes, for its area: the new position in the tick or frame
graph, the sync points (fences, barriers, job dependencies, locks) it adds or
removes, the ms per frame on which thread or queue, the data it reads and
writes and when, and the risks — and writes
`production/engine/[change]-impact-[agent].md`.

- **core-systems-lead** — thread and job-graph placement, contention, memory on the tick, platform differences
- **ecs-dod-architect** — system order, query scheduling and read/write sets, structural changes and when they apply, SoA layout
- **simulation-systems-lead** — fixed-step placement and interpolation, determinism (what must not change order), and where physics, animation and scripting run inside the step and where it emits audio events (mixing stays on the audio callback's own clock)
- **rendering-lead** — passes added or moved, CPU→GPU sync, frames in flight, async-compute overlap, resource lifetimes across frames

An agent outside the active set is consulted through the active lead, whose file
says so; the report names it as consulted, not spawned.

### Phase 3: Resolve conflicts, ADRs and CEA-ADR

Delegate to **chief-engine-architect** with the four proposals' summaries and
paths:
- List every conflict — two writers of the same data in one stage, an ordering
  one proposal needs and another breaks, a sync point that serialises work
  another proposal parallelised, a sum of per-thread costs over the allocation
- Resolve each within the ADRs, or name the ADR that must change or be written
- Produce the resolved tick or frame-graph order and the budget table (ms per
  thread and queue, summed against the budget)
- Output: `production/engine/[change]-resolved.md`

**A decision no Accepted ADR covers** → run `/architecture-decision` with the
Skill tool, in engine mode (`--engine-internal`); it runs the CEA-ADR gate
itself at the resolved `review_mode` (`solo` and `lean` skip it, and it says so).
The new ADR is `Proposed`, and **Phase 4 does not start on a Proposed ADR** —
the run stops BLOCKED until `/architecture-decision accept ADR-NNNN`.

**Gate**: present the resolved order, budget table and unresolved conflicts via
`AskUserQuestion` — `[A] Proceed to implementation` / `[B] Revise` /
`[C] Stop here`. An unresolved conflict is put to the user, never decided by
this orchestrator.

### Phase 4: Implementation

Assign each item of the resolved plan to its specialist (the active set
permitting): `memory-allocator-specialist` (allocators, arenas),
`concurrency-job-system-engineer` (job graph, sync primitives),
`ecs-dod-architect` (ECS systems, layouts), and through
`simulation-systems-lead`: `physics-simulation-engineer` (physics step),
`animation-systems-engineer` (animation sampling), `scripting-runtime-engineer`
(script ticks), `audio-engine-engineer` (audio update and mixer hand-off);
`rhi-backend-engineer` (command recording, queues, fences),
`render-graph-specialist` (passes, barriers, aliasing),
`shader-pipeline-engineer` (shaders), `graphics-features-engineer` (lighting,
shadows, post passes), `vfx-runtime-engineer` (particle simulation passes), `asset-build-tooling-engineer` (the
profiler build switch and the benchmark target in `tests/benchmarks/`).
Each specialist places the zones of its own stages.

Each first returns its file list; ask once for the whole set (File Write
Protocol). Each writes or updates tests in its registered test targets,
including crate unit/integration tests or `tests/`
(`.claude/rules/test-standards.md`), and adds profiler zones around new stages so
Phase 5 can measure them.

### Phase 5: Verification

1. **Tests** — run:
   ```bash
   bash .claude/scripts/test-run.sh custom
   ```
   Read the `rule` row, never the exit code alone. `custom:ctest-pass` and
   `custom:cargo-pass` pass; `custom:ctest-failed`, `custom:cargo-failed`,
   `custom:cargo-compile-failed`, `custom:build-failed` and `custom:nonzero`
   fail; `custom:no-test-command`, `custom:ctest-zero` and `custom:cargo-zero`
   are NOT ASSESSED — **zero tests are never a pass**; `custom:0` cannot tell a
   run of zero tests from a full one, so it is NOT ASSESSED too, and the report
   says why. `timeout` (the build or the tests did not finish),
   `runner-unavailable` (the command did not start) and `-` (no row fits) are
   NOT ASSESSED as well — nothing was verified, and nothing failed either.
2. **Benchmark** — ask the user for a capture of the changed frame (the scene
   the baseline used). `/benchmark-report` is user-invoked only
   (`disable-model-invocation: true`), so this pipeline cannot start it: print
   the command for the user to type, then ask for the path of the report it
   wrote and read that report:
   `/benchmark-report <capture> --baseline <baseline capture> --threshold <percent> --subsystems <zones> --story <story-path> --module <module>`,
   where `<zones>` are the profiler zones of the subsystems the resolved plan
   changes (the Phase 3 budget table's rows) — CEA-FRAME-BUDGET judges each
   affected subsystem against its slice and needs their percentiles. Take its
   verdict word as it reports it, and read its `Budget result` and
   `Regression result` lines apart: with a `--baseline`, a regression result of
   `NOT ASSESSED` is a gap of its own even when the verdict word reads
   `WITHIN BUDGET`. No capture → `benchmark NOT ASSESSED — no capture of
   the changed frame`; no report path back (in `autonomous` mode nothing is
   asked) → `benchmark NOT ASSESSED — /benchmark-report not run (user-invoked
   only)`.
3. At `team.size: studio`, the adversarial pass: brief **chief-engine-architect**
   with the resolved plan and both results — "find the frame where it breaks"
   (a hitch, a race at a sync point, a determinism break) — and record that the
   pass ran.

### Phase 6: Frame budget gate (CEA-FRAME-BUDGET) and sign-off

**Review mode check** — apply before spawning CEA-FRAME-BUDGET
(`.claude/docs/director-gates.md`):
- `solo` → skip. Note: `CEA-FRAME-BUDGET skipped — Solo mode`.
- `lean` → skip (not a PHASE-GATE). Note: `CEA-FRAME-BUDGET skipped — Lean mode`.
- `full` → spawn as normal.

Spawn `chief-engine-architect` via `Agent`:
- Gate: **CEA-FRAME-BUDGET** — the `Agent` prompt instructs the agent to read
  `.claude/docs/director-gates/cea-frame-budget.md` FIRST (do not read it here).
  The gate file missing → the gate is `NOT ASSESSED — gate definition
  .claude/docs/director-gates/cea-frame-budget.md not found`, never skipped as
  if it had passed.
- Context: the frame budget and its source, the resolved budget table
  (`production/engine/[change]-resolved.md`), the `/benchmark-report` path and
  verdict with its `Budget result` and `Regression result` lines, the affected
  subsystems passed to `--subsystems`, the `test-run.sh custom` rule row, and
  the governing ADR IDs.
- Await the verdict before sign-off. Handle all four outcomes as
  `director-gates.md` says: approve → continue; concerns → `AskUserQuestion`
  with `Revise flagged items` / `Accept and proceed` / `Discuss further`
  (`Revise` → NEEDS WORK; `Accept` → the accepted concerns are listed and count
  as approval for COMPLETE); reject → NEEDS WORK with the blockers; NOT ASSESSED
  → name the missing input (the run is then NOT ASSESSED, not NEEDS WORK).

**Sign-off.** Collect every phase's result and give the verdict by the rules in
SKILL.md's Output section, naming each skipped gate, unspawned agent and
NOT ASSESSED check on the verdict line.

---
