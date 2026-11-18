---
name: team-frame-pipeline
description: "Orchestrate the engine frame team — chief-engine-architect, core-systems-lead, ecs-dod-architect, simulation-systems-lead, rendering-lead — for a change to the main tick or frame graph. Custom engine only."
argument-hint: "[tick or frame-graph change description] [--baseline <capture>] [--threshold <percent>] [--story <story-path>] [--review full|lean|solo]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Agent, AskUserQuestion, Skill, Bash(bash .claude/scripts/test-run.sh custom), Bash(bash "*/.claude/skills/team-frame-pipeline/../../hooks/yaml-helper.sh" resolve_config *)
model: sonnet
---
# Team Frame Pipeline

**Argument check:** If no change description is provided, output:
> "Usage: `/team-frame-pipeline [tick or frame-graph change description] [--baseline <capture>] [--threshold <percent>] [--story <story-path>] [--review full|lean|solo]` — describe the change to the main tick or frame graph (e.g., `move animation sampling to async compute`, `split physics into two job waves`)."
Then stop immediately without spawning any subagents or reading any files.

When this skill is invoked with a valid argument, orchestrate the engine frame
team through a structured pipeline.

**Decision Points:** At each phase transition, use `AskUserQuestion` to present
the user with the subagent's proposals as selectable options. Write the agent's
full analysis in conversation, then capture the decision with concise labels.
In `collaborative` mode, the user must approve before moving to the next phase.
In `guided` mode the pipeline advances automatically unless a phase is BLOCKED;
in `autonomous` mode it runs end to end, recording each phase outcome via
`log_decision`. Decisions in `automation_always_ask` categories
(`is_always_ask_category` helper) always prompt regardless of mode. See
`.claude/docs/automation-modes.md`.

## Phase 0: Resolve Config

!`bash "${CLAUDE_SKILL_DIR}/../../hooks/yaml-helper.sh" resolve_config --keys engine,perf_budgets,review_mode,automation,team.size,workflow`

Resolved above — use as-is; `--review` overrides `review_mode`. No block →
defaults in `.claude/docs/config-resolution.md`.

**Engine check — first, before anything is spawned.** This pipeline exists only
for a project that builds its own engine. Read the `engine:` line above:

- `engine: Custom` → continue.
- Anything else, or unset → **refuse, and say so** — never fall through silently
  and never run a reduced pipeline:

  > `/team-frame-pipeline did not run: it needs engine.name: Custom, and this project's engine is <value | unset>.`
  > `Its agents (chief-engine-architect, core-systems-lead, ecs-dod-architect, simulation-systems-lead, rendering-lead and their specialists) own engine internals, which <engine> provides itself.`
  > `For a frame-time problem on <engine>, run /perf-profile or /team-polish; to change the engine, run /setup-engine.`

  Then stop. Verdict: **NOT ASSESSED — engine.name is not Custom**.

**Frame budget.** From the `perf_budgets` line: `frame_budget_ms`, else
`1000 / target_framerate` (say it was derived). Both unset → every budget row in
this run reads `NOT ASSESSED — performance.frame_budget_ms unset`, the agents
are told so, and Phase 1 asks the user whether to set it
(`/project-settings performance.frame_budget_ms=8.33` or `16.6`) before
continuing. Never assume 8.33 or 16.6 ms.

`review_mode` decides whether the two chief-engine-architect gates run —
**CEA-ADR** (through `/architecture-decision`, Phase 3) and
**CEA-FRAME-BUDGET** (Phase 6) — by the rule in `.claude/docs/director-gates.md`:
`solo` skips both, `lean` skips both (neither is a PHASE-GATE), `full` runs both.
The pipeline's own decision points below run at every `review_mode`.

`automation` drives the Decision Points note above.

**Source roots.** Resolve the module map against build manifests using
`.claude/docs/custom-engine-layout.md`, Resolving source roots for workflows.
Mapped Rust `crates/<module>/` roots use the same ownership and evidence rules.
Pass the actual roots in every brief and Phase 4's exact proposed file list.

**`team.size`**: which agents are active (orthogonal to review_mode gate-depth and workflow docs).
- **`individual`** (default): `chief-engine-architect` + the one lead whose area the change starts in (`core-systems-lead` for the tick, jobs or memory; `simulation-systems-lead` for physics, animation or scripting inside the fixed step, or the audio engine (whose events the fixed step emits; mixing runs on the audio device callback's own clock); `rendering-lead` for the frame graph). The other Phase 2 agents are consulted through that lead, not spawned; Phase 4's specialists are not spawned, and the lead implements.
- **`small`**: the full Team Composition pipeline below, as documented.
- **`studio`**: full pipeline + each lead may hand parts of its Phase 2 proposal to its own specialists (`core-systems-lead` → `memory-allocator-specialist`, `concurrency-job-system-engineer`; `simulation-systems-lead` → `physics-simulation-engineer`, `animation-systems-engineer`, `scripting-runtime-engineer`, `audio-engine-engineer`; `rendering-lead` → `rhi-backend-engineer`, `render-graph-specialist`, `shader-pipeline-engineer`, `graphics-features-engineer`, `vfx-runtime-engineer`) + an adversarial review pass: Phase 5's verification brief to `chief-engine-architect` says "your job is not to confirm this holds — find the frame where it breaks", and the report says the pass ran.
A non-core agent needed at `individual` routes through the nearest active core agent with an informational note. **"Phase gate" means any phase that ends in an `AskUserQuestion` decision point this pipeline itself lists** — a transition under Decision Points above, or a **Gate** step written into the pipeline below — **whatever the `automation` mode.** `guided` and `autonomous` change how a gate is passed (it auto-advances, or is recorded with `log_decision`), not whether it is one, so bounded-exception condition (3) below holds at it in every mode. This active-set scoping applies throughout the pipeline below: any phase that names an agent outside the active set routes through the nearest core agent rather than spawning it.

**Announce the active set before Phase 1 — never let the collapse be silent.**
Before spawning anything, state in one line which agents this run will actually
spawn, and which the pipeline below names but will **not** spawn at the resolved
`team.size`:

> `Active set (team.size: <resolved>): <the agents listed for that size above>.`
> `Not spawned this run: <every other agent this pipeline names> — consulted`
> `through <nearest active core agent>. Raise team.size (or modes.rigor) to widen.`

Fill it from the `team.size` list directly above and the agents this file's own
pipeline names — not from an example. At `individual`, the Phase 2 proposals of
the agents not spawned are named in the report as consulted, not written by them.

## Team Composition
- **chief-engine-architect** — Frames the change, owns the frame budget, ADR compliance and subsystem boundaries; resolves conflicts between the proposals; final say on engine technical conflicts
- **core-systems-lead** — Threads, job graph, memory and platform impact: sync points, contention, allocation on the tick
- **ecs-dod-architect** — System ordering, query scheduling, archetype and SoA layout impact
- **simulation-systems-lead** — Physics, animation and scripting inside the fixed step, and the audio engine (audio events emitted by the step; mixing on the device callback, never on the step): fixed-step ordering, determinism, interpolation; agrees the sim tick order with core-systems-lead
- **rendering-lead** — Frame-graph passes, CPU→GPU sync, frames in flight, queue use
- **Implementation specialists** (Phase 4) — `memory-allocator-specialist`, `concurrency-job-system-engineer`, `ecs-dod-architect`, `physics-simulation-engineer`, `animation-systems-engineer`, `scripting-runtime-engineer`, `audio-engine-engineer`, `rhi-backend-engineer`, `render-graph-specialist`, `shader-pipeline-engineer`, `graphics-features-engineer`, `vfx-runtime-engineer`, `asset-build-tooling-engineer` (the profiler build switch and benchmark targets)

## How to Delegate

Use the `Agent` tool to spawn each team member as a subagent:
- `subagent_type: chief-engine-architect` — Framing, conflict resolution, budget sign-off
- `subagent_type: core-systems-lead` — Threading, jobs, memory, platform impact
- `subagent_type: ecs-dod-architect` — ECS ordering and data-layout impact; ECS implementation
- `subagent_type: simulation-systems-lead` — Fixed-step impact (physics, animation, scripting, and the audio events the step emits); routes implementation to its specialists
- `subagent_type: rendering-lead` — Frame-graph and GPU sync impact
- `subagent_type: [specialist]` — Phase 4 implementation, one per area the resolved plan assigns

**Brief each agent — do not dump context.** Read the shared inputs **once** and pass a distilled brief inline: the lines each agent actually needs, never a file path for a document you have already read (an agent handed a path re-reads the whole file). Pass a path only for a document you have not read and only that agent needs. Every brief carries the frame budget (or its NOT ASSESSED line) and the governing ADR IDs.

**End every agent prompt with a return contract:** "Write your full output to `[path]` — that named path is your write authorisation under the bounded exception below, so write it without a separate approval prompt. Return **only** (1) the path written, (2) a ≤5-bullet summary of decisions, (3) any BLOCKED/CONCERNS items, one line each. Do not restate the documents you read." **Implementation files are the exception:** an agent writing code first returns the files it will create or change, and writes them only after you have asked once for the set and the user said yes (File Write Protocol).

| Phase / agent | Writes to |
|---|---|
| 1 chief-engine-architect | `production/engine/[change]-frame.md` |
| 2 core-systems-lead, ecs-dod-architect, simulation-systems-lead, rendering-lead | `production/engine/[change]-impact-[agent].md`, one each |
| 3 chief-engine-architect | `production/engine/[change]-resolved.md` |
| 4 specialists | Mapped engine roots (including `crates/<module>/`), game and test roots — only the files the Phase 4 approval lists; outside the bounded exception, asked once for the set |
| 5 verification | this skill's report; `/benchmark-report` writes its own after asking |

> **`/story-done` reads `production/engine/`** — it is this pipeline's record of
> one change, and the perf evidence `/story-done` looks for when it closes an
> engine story whose `Frame pipeline: yes` line puts it on the frame pipeline;
> say so when reporting, so the record is kept. An ADR the change needs is
> written by `/architecture-decision` to `docs/architecture/`, not here.

> **Why this does not violate the Collaboration Protocol.** `CLAUDE.md` requires an agent to ask "May I write this to [filepath]?" before Write/Edit. A subagent spawned here writes **without** asking, and that is a deliberate, bounded exception rather than an oversight. The exception holds only when all three are true: (1) the path is one **you** named in the prompt, so the user approved the destination when they approved the phase; (2) it is a new artifact under `production/`, `docs/` or `tests/`, never an edit to existing source or config; (3) the phase that produced it is itself gated by an `AskUserQuestion` before the pipeline advances. Outside those three, the agent must ask. **Do not "fix" this by asking per subagent** — a prompt per agent per phase makes an orchestrator unusable, which is why the exception exists.

Launch Phase 2's agents in parallel: their inputs are independent (Phase 1's
frame), so issue every `Agent` call before waiting for any result.

## Pipeline

**Read `references/pipeline.md` now and follow it** — Phases 1 to 6 are in that
file, not here. Read it again if the conversation was compacted or resumed
during the pipeline.

## Error Recovery Protocol

**First, verify the artifact.** If the return contract named a path, check the
path exists before treating the phase as done — **a named artifact that is not
on disk is a failed phase, however fluent the response reads.** Resume the agent
naming the unmet contract; the context is usually still there.

If any spawned agent returns BLOCKED, errors, or cannot complete: **surface it
immediately, don't proceed past a dependency it blocks, and always produce a
partial report.** A skipped agent's section stays a named gap — never fill it
with content of your own. Full procedure: `.claude/docs/error-recovery-protocol.md`.

Common blockers:
- An agent file is missing (`.claude/agents/<name>.md`) → name it; that agent's phase is BLOCKED, never run by another agent under its name
- ADR status is Proposed → do not implement; once it is decided, accept it with `/architecture-decision accept ADR-NNNN`
- Two proposals conflict and chief-engine-architect cannot resolve them within the ADRs → stop at the Phase 3 gate and put both to the user
- Frame budget unset → Phase 0's rule; never invent one

## File Write Protocol

All file writes are delegated to sub-agents spawned via `Agent`, under two rules:

- **Framing, proposals and the resolved plan** — the path table's destinations
  under `production/engine/` — follow the **bounded exception** above.
- **Implementation files** — Phase 4's changes in the resolved engine, game and
  test roots — are outside that exception. Each implementing agent first returns
  the files it will create or change with a one-line summary each; ask once for
  the whole set ("May I have [agents] change these [N] files?") and have them
  write only after a yes. An edit to an existing file is always on that list.

This orchestrator writes no file itself.

## Output

A summary report: the change, the resolved tick or frame-graph order, the
budget table (ms per thread or queue against the frame budget), the
implementation per specialist, the test result (`test-run.sh custom` rule), the
`/benchmark-report` verdict, the CEA-ADR and CEA-FRAME-BUDGET outcomes, and open
issues with owners.

Verdict, first match wins. **Configured omissions are not failures**: an agent
the resolved `team.size` leaves out of the active set, and a gate the resolved
`review_mode` skips, are named on the verdict line and never change the verdict
word. Only an unexpected failure blocks or fails the run.

- **NEEDS WORK** — an explicit adverse result came back from any phase that
  ran: the tests failed (`custom:ctest-failed`, `custom:cargo-failed`,
  `custom:cargo-compile-failed`, `custom:build-failed`, `custom:nonzero`),
  `/benchmark-report` returned `OVER BUDGET` or `REGRESSION`, CEA-FRAME-BUDGET
  returned REJECT, or it returned CONCERNS and the user chose
  `Revise flagged items`. Nothing that merely could not be measured lands here.
  A known failure outranks a blocker: when a phase was also blocked, the
  verdict stays NEEDS WORK and its line names the blocker as well
  (`NEEDS WORK — custom:ctest-failed; also BLOCKED: CEA-FRAME-BUDGET agent errored`).
- **BLOCKED** — no adverse result above, and a phase could not complete; an
  agent in the active set was missing (`.claude/agents/<name>.md` absent) or
  errored and was not recovered; or an ADR the change needs is still Proposed.
  Partial report with each unresolved item, named on the verdict line. An agent
  outside the active set is not missing.
- **NOT ASSESSED** — no result above, but the verification could not establish
  the change. Name each: the tests did not run or proved nothing
  (`custom:no-test-command`, `custom:ctest-zero`, `custom:cargo-zero`; `custom:0`,
  which cannot tell zero tests from many; `timeout`, the build or test run did
  not finish; `runner-unavailable`, the command did not start; `-`, no row of
  the ladder fits); no capture of the changed frame; `/benchmark-report`
  returned `NOT ASSESSED`; a `--baseline` was given but its regression result is
  `NOT ASSESSED` (captures not comparable, no threshold); the frame budget is
  unset; or CEA-FRAME-BUDGET, when required, returned NOT ASSESSED or its gate
  file was missing.
- **COMPLETE** — tests passed (`custom:ctest-pass` or `custom:cargo-pass`),
  `/benchmark-report` returned `WITHIN BUDGET`, and **when CEA-FRAME-BUDGET is
  required** (`review_mode: full`) it returned APPROVE, or CONCERNS the user
  took with `Accept and proceed` (the accepted concerns are listed). When
  `review_mode` skips the gate, COMPLETE does not wait for it — the skip is
  named instead. A regression check with no baseline at all, run with the
  user's Phase 1 permission, is named, not counted against COMPLETE.

**Every verdict line names what did not run** — a gate skipped by `review_mode`
(`CEA-FRAME-BUDGET skipped — Solo mode`), a regression check with no baseline,
agents not spawned at this `team.size`. For example:
`Verdict: COMPLETE — CEA-FRAME-BUDGET skipped (Lean mode); regression NOT ASSESSED (no baseline capture)`.

## Next Steps

- Run `/code-review` on the changed engine code before closing stories.
- Run `/memory-audit` with a sanitizer run when the change touched allocators, job lifetimes or ownership.
- Keep the `/benchmark-report` written in Phase 5 as the baseline for the next frame change.
- If an ADR was drafted: `/architecture-decision accept ADR-NNNN` once it is settled, then `/architecture-review` in a fresh session.
