---
name: perf-regression-triage
description: "Triage a /benchmark-report regression — confirm with a re-run, plan a bisect over builds and commits, attribute it to a subsystem and owner, open a bug in /bug-report format, track it to a measured fix."
argument-hint: "<benchmark-report.md> [--confirm <benchmark-report.md>] [--good <commit>] [--bad <commit>] [--first-bad <commit>] | track <BUG-ID> <benchmark-report.md>"
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Bash(git rev-parse *), Bash(git rev-list *), Bash(git log *), Bash(git show *), Bash(bash "*/.claude/skills/perf-regression-triage/../../hooks/yaml-helper.sh" resolve_config *)
model: sonnet
---

!`bash "${CLAUDE_SKILL_DIR}/../../hooks/yaml-helper.sh" resolve_config --keys engine,perf_budgets,automation`

Resolved above — use as-is. No block → defaults in
`.claude/docs/config-resolution.md`.

# Perf Regression Triage

> **Explicit invocation only** (`disable-model-invocation: true`): this skill
> runs when the user types `/perf-regression-triage`. Claude does not start it from context or
> through the Skill tool; another skill that needs it prints the command for
> the user. It runs on any engine and is oriented to a Custom one.

Every `AskUserQuestion` call follows `.claude/docs/automation-modes.md`
(collaborative asks always · guided major-only · autonomous logs and proceeds;
`automation_always_ask` categories always prompt).

A triage flow from the first failing benchmark run to a named owner —
**confirm, bisect, attribute, hand over** — and then tracking until a
measurement shows the fix. It reads what `/benchmark-report` measured; it never
measures, estimates or edits code.

**Its triage rules are its own**, on every engine:

- **Confirm on the same machine.** One run is not a regression: only a re-run
  on the same machine, preset and GPU/driver confirms it (Phase 2).
- **NOT REPRODUCED stays open.** A re-run that shows no regression makes it
  NOT REPRODUCED, kept open as unconfirmed — never closed as noise.
- **No assumed SLA.** The response time for a confirmed regression is the
  project's record (`producer` sets it); none recorded → `regression SLA NOT
  SET`, never assume one.

On Custom these are the steps of `performance-analyst`'s Perf-regression
triage (`.claude/agents/performance-analyst.md`, On a Custom Engine Project),
which that agent applies only on a Custom engine; on any other engine this
skill applies them itself.

**Which projects.** It runs on **any engine** — Web, Godot, Unity, Unreal or
Custom — whenever there is `/benchmark-report` output with a regression line;
it does not refuse on a non-Custom engine. What changes with the engine is
Phase 4's routing: on Custom, the engine module decides the lead; on any other
engine, the system decides the owner. The run says which, once:
`Routing: <Custom engine leads | owners on <engine>>`.

It never runs `git bisect`, `git checkout` or any command that changes the
working tree. The bisect is a plan, printed for the user to run.

## Insufficient input — check this before triaging anything

1. List the inputs: the regression report, the confirmation report, the
   last-good and first-bad commits or builds, the first bad commit if a bisect
   was run, the budget split, the regression SLA.
2. Record each `FOUND` or `ABSENT`.
3. A step whose input is ABSENT reads **`NOT ASSESSED — <reason>`** in the
   bug's triage section. It is never left out.
4. No report path given and none found → stop: **`NOT ASSESSED — no
   regression report`**, and say how to make one: `/benchmark-report <capture>
   --baseline <earlier report or capture> --threshold <percent>`.

**One run is not a regression.** A report that says REGRESSION has shown one
run was slower than the baseline. Until a re-run on the same machine, preset
and GPU/driver shows it again, the regression is unconfirmed.

---

## Phase 1: Read the Regression

Argument starts with `track` → go to Phase 6.

No path → Glob `production/qa/benchmarks/benchmark-*.md`, list the newest
with their `Regression result:` line, and ask which to triage.

Read the report's `Regression result:` line (`/benchmark-report`,
`references/report.md`). Not this skill's input to triage when:

| The report | Stop with |
|---|---|
| has no `Regression result:` line | `NOT ASSESSED — <path> is not /benchmark-report output`; run `/benchmark-report` with `--baseline` and `--threshold` |
| reads `NO REGRESSION` | `NO REGRESSION — nothing to triage` |
| reads `NOT ASSESSED — <reason>` | `NOT ASSESSED — the report did not establish a regression (<reason>)` |

`REGRESSION` → record from the report: each regressed metric with baseline,
current, Δ ms and Δ %; the baseline path; the threshold; the Inputs table
(build configuration, platform/GPU, resolution, scene); the affected
subsystems and the budget result. Every later number cites this report.

---

## Phase 2: Confirm

`--confirm <path>` → read it. It confirms when **all** hold:

- It is `/benchmark-report` output against **the same baseline** and **the
  same threshold**.
- Its Inputs match the first report's build configuration, platform/GPU,
  resolution and scene; a difference or an `unknown` on either side is named.
- It is a different capture from the first report's.

Then: `REGRESSION` on at least one of the same metrics → **CONFIRMED**;
`NO REGRESSION` → **NOT REPRODUCED** (kept open as unconfirmed — the rule
above); anything else, or a condition above not met →
`Confirmation: NOT ASSESSED — <reason>`.

No `--confirm` → print the re-run to make: capture the same scene on the same
machine, preset and GPU/driver, then
`/benchmark-report <new capture> --baseline <same baseline> --threshold <same>`,
and ask for its path. No answer, or `autonomous` mode → `Confirmation: NOT
ASSESSED — no re-run`, and continue: the bug is still opened, as unconfirmed.

---

## Phase 3: Bisect Plan

**Read `references/bisect-and-bug.md` now and follow it** — the bisect plan,
the attribution routing and the bug draft are in that file, not here. Read it
again if the conversation was compacted or resumed during this phase.

---

## Phase 4: Attribute

Follow `references/bisect-and-bug.md`, section 4.

---

## Phase 5: Open the Bug

**One regression, one bug.** First Grep `production/qa/bugs/` for a
`## Perf Regression Triage` section that cites this regression report. Found
→ this run updates that bug instead of opening another: show the changed triage
lines, ask *"May I update `production/qa/bugs/[bug file]` with this triage?"*,
and add a Tracking entry for what changed (confirmed, attributed).

Otherwise follow `references/bisect-and-bug.md`, section 5. The bug is drafted in
`/bug-report`'s template and written to `production/qa/bugs/` only after
*"May I write this to `production/qa/bugs/BUG-[NNNN].md`?"*. On no, stop:
the draft stays in the conversation, and the closing line says no bug was
written.

---

## Phase 6: Track to a Measured Fix — `track <BUG-ID> <report>`

1. Find the bug by number as `/bug-report verify` does (Glob
   `production/qa/bugs/BUG-*.md`); none → stop: `No bug <BUG-ID> in
   production/qa/bugs/`. Read its `## Perf Regression Triage` section; none →
   stop: `NOT ASSESSED — <BUG-ID> has no triage section; it was not opened by
   /perf-regression-triage`.
2. Read the new report. It measures the fix only when it uses the bug's
   **baseline** and **threshold** and matches its Inputs; otherwise
   `Fix measurement: NOT ASSESSED — <difference>`.
3. Its `Regression result:` decides: `NO REGRESSION` → `measured fixed in
   <report>`; `REGRESSION` → `still regressed in <report>`, with the deltas;
   `NOT ASSESSED` → `not measured (<reason>)`.
4. Show the tracking entry, then ask: *"May I update
   `production/qa/bugs/[bug file]` with this tracking entry?"* — appended to
   the triage section's Tracking list. The bug's Status is not changed here.

`measured fixed` is not closed: verification and closing are
`/bug-report verify` and `/bug-report close`.

---

## Phase 7: Verdict and Next Steps

The triage verdict, first match wins:

1. **CONFIRMED** — the re-run reproduced the regression. Suffix the
   attribution: `— attributed to <owner> (<commit>)` or `— attribution NOT
   ASSESSED (<reason>)`.
2. **NOT ASSESSED** — confirmation did not run or did not hold (Phase 2), or
   the input was not a regression (Phase 1). Name the reason.
3. **NOT REPRODUCED** — the re-run showed `NO REGRESSION`.

**NOT ASSESSED ranks below CONFIRMED and above NOT REPRODUCED.** A confirmed
regression is the actionable result; an unconfirmed one has not shown it is
noise. Every verdict line also names each other step that did not run —
bisect, attribution, budget slice, SLA:

> `Verdict: CONFIRMED — attribution NOT ASSESSED (bisect not run); budget slice NOT ASSESSED (no split recorded); regression SLA NOT SET`

In track mode the verdict is the tracking result: `measured fixed`, `still
regressed`, or `NOT ASSESSED — <reason>`.

Next steps:

- **CONFIRMED, attributed** → the owner fixes or reverts; on Custom, a fix that
  changes the main tick or frame graph goes through `/team-frame-pipeline`;
  otherwise `/dev-story`. After the fix, a new capture and
  `/perf-regression-triage track <BUG-ID> <new report>`.
- **CONFIRMED, not attributed** → run the printed bisect, then
  `/perf-regression-triage <report> --first-bad <commit>` to attribute.
- **NOT ASSESSED** → make the re-run the verdict names, then run this skill
  again with `--confirm`.
- **NOT REPRODUCED** → the bug stays open as unconfirmed; one more re-run, or
  `/bug-triage` to decide whether to keep it.
- **measured fixed** → `/bug-report verify <BUG-ID>`, then
  `/bug-report close <BUG-ID>`.
- Allocator time in the regressed zones → `/memory-audit`; memory growth →
  its memory-track export to `memory-allocator-specialist` on Custom
  (`performance-analyst` on another engine).

### Rules
- Every number cites a `/benchmark-report` file by path.
- Suspects are not an attribution; only a first bad commit attributes.
- An unset budget, split or SLA is named as unset, never filled in.
- Nothing is filed outside this repository: when the cause is in a vendor's
  engine or library, the draft for their tracker goes under the bug's Notes,
  as `/bug-report` does.
