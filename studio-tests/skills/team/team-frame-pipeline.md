# Skill Test Spec: /team-frame-pipeline

## Skill Summary

Orchestrates the engine frame team for a change to the main tick or frame graph
on a project whose `engine.name` is `Custom`: Phase 1 framing
(chief-engine-architect) → Phase 2 impact proposals in parallel
(core-systems-lead, ecs-dod-architect, simulation-systems-lead,
rendering-lead) → Phase 3 conflict resolution, ADRs and CEA-ADR (through
`/architecture-decision --engine-internal`) → Phase 4 implementation by
specialists → Phase 5 verification (`bash .claude/scripts/test-run.sh custom`
rule row; `/benchmark-report` with a baseline and its threshold, printed for the
user to run because that skill is user-invoked only, then its report read) →
Phase 6 CEA-FRAME-BUDGET and sign-off. Phase 0 resolves `engine`, `perf_budgets`, `review_mode`, `automation`,
`team.size` and `workflow`. **Engine check first:** anything other than
`engine: Custom` refuses with the exact "did not run" message and verdict
`NOT ASSESSED — engine.name is not Custom`, spawning nothing. An unset budget
makes every budget row `NOT ASSESSED — performance.frame_budget_ms unset` and
Phase 1 asks whether to set it; 8.33/16.6 ms are never assumed. `solo` and
`lean` skip both CEA gates and say so; `full` runs both. The active set is
announced before Phase 1 (`individual`: chief-engine-architect + one lead;
`small`: full pipeline; `studio`: + specialists under each lead + adversarial
pass). Agents write named `production/engine/` paths under the bounded
exception; implementation files are asked for once as a set. A Proposed ADR
blocks Phase 4. Verdict, first match wins: NEEDS WORK → BLOCKED → NOT ASSESSED →
COMPLETE (a known failure outranks a blocker, which the verdict line still names); zero tests (`custom:ctest-zero`, `custom:cargo-zero`,
`custom:no-test-command`, `custom:0`) are NOT ASSESSED, never a pass.

---

## Static Assertions (Structural)

- [ ] Has required frontmatter fields: `name`, `description`, `argument-hint`, `user-invocable`, `allowed-tools`; `model: sonnet`
- [ ] Has ≥2 phase headings; Phases 1–6 in `references/pipeline.md`
- [ ] Phase 0's engine check comes before anything is spawned and quotes the refusal text with `NOT ASSESSED — engine.name is not Custom`
- [ ] Contains verdict keywords: NEEDS WORK, BLOCKED, NOT ASSESSED, COMPLETE, in that order — NEEDS WORK before BLOCKED; NOT ASSESSED ranks below both and above COMPLETE
- [ ] `allowed-tools` has no Write and no Edit (the orchestrator writes no file) and grants `test-run.sh custom` exactly, never `custom*`
- [ ] `argument-hint` includes `--threshold` and `--story`; the Phase 5 `/benchmark-report` command carries `--threshold`, `--story` and `--module`, and is printed for the user, never run with the Skill tool
- [ ] Names both gates, CEA-ADR and CEA-FRAME-BUDGET, with the `review_mode` rule (solo and lean skip, full runs) and the skip notes
- [ ] Never assumes 8.33 or 16.6 ms when the budget is unset
- [ ] Contains "File Write Protocol"; the orchestrator writes no file itself; the path table names `production/engine/[change]-frame.md`, `-impact-[agent].md`, `-resolved.md`
- [ ] States that `/story-done` reads `production/engine/` (perf evidence for a `Frame pipeline: yes` engine story), so the record is kept
- [ ] Error Recovery Protocol present (verify artifact on disk, BLOCKED surfaced, partial report)
- [ ] Requires a one-line active-set announcement before Phase 1
- [ ] Team Composition and Phase 2 name `simulation-systems-lead` (physics, animation, scripting, audio inside the fixed step); `physics-simulation-engineer` appears only as a Phase 4 specialist reached through it
- [ ] Phase 5 reads the `test-run.sh custom` rule row, not the exit code, and lists every `custom:*` rule in its verdict mapping
- [ ] Has a Next Steps section (`/code-review`, `/memory-audit`, `/benchmark-report`, `/architecture-decision accept`)

---

## Director Gate Checks

- **Full mode**: CEA-ADR (run by `/architecture-decision` in Phase 3 when a new ADR is needed) and CEA-FRAME-BUDGET (Phase 6)
- **Lean mode**: both skipped — neither is a PHASE-GATE; notes `CEA-FRAME-BUDGET skipped — Lean mode` (and `/architecture-decision` reports its own CEA-ADR skip)
- **Solo mode**: both skipped; `CEA-FRAME-BUDGET skipped — Solo mode`
- The pipeline's own `AskUserQuestion` decision points run at every `review_mode`

---

## Fixture Defaults

Every case's `project.yaml` sets `modes.rigor: minimal` and
`modes.automation: collaborative`, with no `project.local.yaml`, unless its own
Fixture says otherwise. Rules: `studio-tests/CLAUDE.md` §
Fixture defaults. Unless a case says otherwise, `engine.name: Custom` and
`performance.frame_budget_ms: 8.33` are also set, and all 24 Custom engine
agent files exist.

---

## Test Cases

### Case 1: Happy Path — full review, small team, COMPLETE

**Fixture:**
- `modes.review_mode: full`, `team.size: small`
- Accepted ADRs cover jobs, ECS scheduling and the frame graph
- `--baseline production/qa/benchmarks/captures/before.csv` (release preset)
- After implementation: `test-run.sh custom` → `custom:ctest-pass`; the user runs the printed `/benchmark-report` and gives its report path → `WITHIN BUDGET`; CEA-FRAME-BUDGET → APPROVE

**Input:** `/team-frame-pipeline split physics into two job waves --baseline production/qa/benchmarks/captures/before.csv --threshold 5 --story production/epics/physics/story-002.md`

**Expected behavior:**
1. Phase 0: engine Custom → continue; budget 8.33 ms; announces the active set (all agents in Team Composition)
2. Phase 1: chief-engine-architect writes `production/engine/[change]-frame.md`; gate `[A] Proceed / [B] Revise / [C] Stop`
3. Phase 2: four `Agent` calls issued before waiting for any; each writes its impact file
4. Phase 3: resolved order and budget table in `[change]-resolved.md`; no new ADR needed
5. Phase 4: specialists return file lists; one "May I have [agents] change these [N] files?" ask; then writes
6. Phase 5: rule row `custom:ctest-pass`; prints `/benchmark-report <capture> --baseline <before> --threshold 5 --subsystems <zones> --story <story> --module <module>` for the user (it is user-invoked only), asks for the report path and reads it
7. Phase 6: CEA-FRAME-BUDGET spawned with the gate file path → APPROVE
8. Verdict COMPLETE, naming anything that did not run

**Assertions:**
- [ ] Phase 2 agents launched in parallel
- [ ] One ask for the whole implementation file set
- [ ] CEA-FRAME-BUDGET prompt tells the agent to read `.claude/docs/director-gates/cea-frame-budget.md` first
- [ ] Verdict COMPLETE only with ctest-pass + WITHIN BUDGET + APPROVE

---

### Case 2: Engine Not Custom — refusal, nothing spawned

**Fixture:**
- `engine.name: Unity`

**Input:** `/team-frame-pipeline move animation sampling to async compute`

**Expected behavior:**
1. Phase 0 reads `engine: Unity` and refuses before spawning anything:
   `/team-frame-pipeline did not run: it needs engine.name: Custom, and this project's engine is Unity.` plus the agents line and the pointer to `/perf-profile`, `/team-polish` or `/setup-engine`
2. Verdict `NOT ASSESSED — engine.name is not Custom`
3. No reduced pipeline runs

**Assertions:**
- [ ] No `Agent` call
- [ ] Refusal text names the engine and the alternatives
- [ ] Verdict exactly `NOT ASSESSED — engine.name is not Custom`

**Variant:** `engine.name` unset → the same refusal with `unset`.

---

### Case 3: Budget Unset — NOT ASSESSED rows, ask to set it

**Fixture:**
- `engine.name: Custom`, no `performance` block

**Input:** `/team-frame-pipeline add a GPU-driven culling pass before the depth prepass`

**Expected behavior:**
1. Every budget row reads `NOT ASSESSED — performance.frame_budget_ms unset`; agents are told so in their briefs
2. Phase 1 asks whether to set it (`/project-settings performance.frame_budget_ms=8.33` or `16.6`) before continuing
3. If the user continues without setting it, CEA-FRAME-BUDGET (at `full`) returns NOT ASSESSED and the run cannot be COMPLETE

**Assertions:**
- [ ] Neither 8.33 nor 16.6 ms is assumed
- [ ] The user is asked before Phase 2
- [ ] Final verdict is not COMPLETE while the budget is unset

---

### Case 4: Zero Tests and No Capture — NOT ASSESSED, not COMPLETE

**Fixture:**
- `review_mode: solo`; pipeline runs to Phase 5
- `test-run.sh custom` → `custom:ctest-zero`
- The user has no capture of the changed frame

**Input:** `/team-frame-pipeline reorder transform propagation before render extraction`

**Expected behavior:**
1. Phase 5 reads the rule row: `custom:ctest-zero` → NOT ASSESSED (zero tests are never a pass)
2. Benchmark: `benchmark NOT ASSESSED — no capture of the changed frame`
3. Phase 6: `CEA-FRAME-BUDGET skipped — Solo mode`
4. Verdict line: `NOT ASSESSED — tests NOT ASSESSED (custom:ctest-zero); benchmark NOT ASSESSED (no capture); CEA-FRAME-BUDGET skipped (Solo mode)`

**Assertions:**
- [ ] Exit code 0 is not read as a pass
- [ ] Verdict NOT ASSESSED, each reason named
- [ ] The gate skip is named on the verdict line

---

### Case 5: Proposed ADR — BLOCKED before Phase 4

**Fixture:**
- `review_mode: full`; Phase 3 finds a decision no Accepted ADR covers (moving physics onto async compute workers)
- `/architecture-decision --engine-internal` writes `ADR-0042` as Proposed; CEA-ADR returns CONCERNS

**Input:** `/team-frame-pipeline run broad phase during GPU submission`

**Expected behavior:**
1. Phase 3 runs `/architecture-decision` with the Skill tool in engine mode; it runs CEA-ADR itself
2. ADR-0042 is Proposed → Phase 4 does not start
3. Verdict BLOCKED, naming ADR-0042 and the next step `/architecture-decision accept ADR-0042`

**Assertions:**
- [ ] No implementation file written
- [ ] Verdict BLOCKED with the ADR named
- [ ] The orchestrator does not accept the ADR itself

---

### Case 6: `team.size: individual` — collapse announced

**Fixture:**
- `team.size` unset (resolves to `individual`); the change starts in the frame graph

**Input:** `/team-frame-pipeline add a transient history buffer for TAA`

**Expected behavior:**
1. Announces: `Active set (team.size: individual): chief-engine-architect, rendering-lead.` and `Not spawned this run: core-systems-lead, ecs-dod-architect, simulation-systems-lead, ... — consulted through rendering-lead.`
2. Phase 2 spawns only rendering-lead; its file notes the consulted areas
3. Phase 4 specialists are not spawned; rendering-lead implements
4. The report names the unspawned agents as consulted, not as authors

**Assertions:**
- [ ] Announcement before Phase 1, filled from the skill's own lists
- [ ] No agent outside the active set spawned
- [ ] Report names consulted agents

---

### Case 7: No Argument — usage

**Input:** `/team-frame-pipeline`

**Expected behavior:** Prints the usage line and stops without spawning agents or reading files.

**Assertions:**
- [ ] Usage text shown; no `Agent` call; no file read

---

### Case 8: Verdict precedence — configured omissions, explicit failures, unrun checks

**Fixture:** pipeline runs to sign-off; vary one input per run.
- Run A: `team.size: individual`, `review_mode: lean`; `custom:ctest-pass`; `/benchmark-report` → `WITHIN BUDGET` with `Regression result: NO REGRESSION`
- Run B: `review_mode: full`; `custom:ctest-pass`; `WITHIN BUDGET`; CEA-FRAME-BUDGET → NOT ASSESSED (no per-subsystem rows in the report)
- Run C: `review_mode: full`; `custom:ctest-pass`; `WITHIN BUDGET`; CEA-FRAME-BUDGET → CONCERNS, user picks `Accept and proceed`
- Run D: `review_mode: solo`; `test-run.sh custom` → `rule timeout`
- Run E: `review_mode: solo`; `test-run.sh custom` → `rule runner-unavailable`
- Run F: `review_mode: full`; `--baseline` given; `custom:ctest-pass`; verdict word `WITHIN BUDGET` but `Regression result: NOT ASSESSED — captures not comparable (debug vs release)`

**Input:** `/team-frame-pipeline split physics into two job waves`

**Expected behavior:**
1. Run A: agents outside the `individual` active set and the skipped CEA-FRAME-BUDGET are configured omissions — named on the verdict line, not BLOCKED, not NEEDS WORK → `COMPLETE — CEA-FRAME-BUDGET skipped (Lean mode); not spawned at team.size individual: ...`
2. Run B: `NOT ASSESSED`, naming CEA-FRAME-BUDGET's missing input — never NEEDS WORK
3. Run C: `COMPLETE`, listing the accepted concerns
4. Run D: `NOT ASSESSED — tests NOT ASSESSED (timeout)`
5. Run E: `NOT ASSESSED — tests NOT ASSESSED (runner-unavailable)`
6. Run F: `NOT ASSESSED`, naming the regression result — the verdict word alone is not read

**Assertions:**
- [ ] No run is BLOCKED because `team.size` left an agent out or `review_mode` skipped a gate
- [ ] NEEDS WORK appears only on an explicit adverse result (test failure rule, OVER BUDGET, REGRESSION, REJECT, or CONCERNS the user chose to revise)
- [ ] CEA-FRAME-BUDGET NOT ASSESSED gives NOT ASSESSED, not NEEDS WORK
- [ ] COMPLETE does not require CEA-FRAME-BUDGET approval when `review_mode` skipped it, and does when it ran
- [ ] `timeout` and `runner-unavailable` are NOT ASSESSED, never a pass and never a test failure
- [ ] Variant — `custom:ctest-failed` and a CEA-FRAME-BUDGET agent error in one run: `NEEDS WORK`, and the verdict line also names the blocker; never BLOCKED
- [ ] Variant — `modes.automation: autonomous`, `--baseline` given with no `--threshold` and no `Threshold:` line in the baseline: nothing asked; `regression NOT ASSESSED — no threshold given with the baseline` on the verdict line

---

### Case 9: Frame graph in a registered Rust crate

**Fixture:** Custom engine with frame graph in `crates/renderer/`, jobs in
`crates/jobs/`, and module ownership recorded in the module map.

**Input:** `/team-frame-pipeline change the renderer queue dependencies`

**Expected behavior:** Resolves crate roots before delegation. The Phase 4
proposed file list may name these registered crate paths, with their owners;
asks approval for that exact set and writes only approved paths. Uses the same
test, capture and gate rules as the `engine/` layout. No write is granted by
being inside a crate alone.

---

## Protocol Compliance

- [ ] Engine check runs before anything else; a non-Custom engine is refused by name, never run reduced
- [ ] Budget never assumed; unset budget is NOT ASSESSED and asked about
- [ ] Gates follow `review_mode`; each skip is named on the verdict line
- [ ] Phase 2 agents launched in parallel; each brief carries the budget (or its NOT ASSESSED line) and ADR IDs
- [ ] Named `production/engine/` paths written under the bounded exception; implementation files asked for once as a set
- [ ] A Proposed ADR blocks implementation
- [ ] Verdict read from the `test-run.sh custom` rule row; zero tests never a pass
- [ ] Ends with the Next Steps section

---

## Coverage Notes

- `team.size: studio` (specialists under each lead, adversarial pass) has no dedicated case.
- A missing agent file (`.claude/agents/<name>.md`) → BLOCKED is not exercised.
- CEA-FRAME-BUDGET CONCERNS → `Revise flagged items` (NEEDS WORK) and `Discuss further` are not covered; `Accept and proceed` is (Case 8, Run C).
