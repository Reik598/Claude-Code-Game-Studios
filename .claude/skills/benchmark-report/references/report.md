# /benchmark-report — Phase 5: Report and Verdict

> Part of `/benchmark-report`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 5: Report and Verdict

**In this file:**

- The verdict, first match wins
- The report template

### The verdict

The verdict is decided by two checks — the **frame budget** (P95 against the
budget, Phase 3a) and the **regression** check (Phase 4). Each has its own
result line, written above the verdict word so neither hides behind the other:

- **Budget result** — `OVER BUDGET`, `WITHIN BUDGET`, or
  `NOT ASSESSED — <reason>` (no frame-time capture, budget unset).
- **Regression result** — `REGRESSION`, `NO REGRESSION`, or
  `NOT ASSESSED — <reason>` (no baseline, captures not comparable, no
  threshold). `NOT ASSESSED — no baseline` on a scene's first capture is the
  first-baseline exemption (SKILL.md Phase 4); the line still says it.

**A consumer that needs the comparison reads the Regression result line**, not
the verdict word: a frame-budget gate against a baseline, or
`/team-frame-pipeline` when it passed `--baseline`. The verdict word below
summarises both lines for a reader who wants one word; it does not replace them.

The other sections (CPU and GPU frame percentiles, CPU vs GPU, hotspots,
per-subsystem timings, counters) are reported, and each one that did not run is
named on the verdict line, but they do not change the verdict word. A consumer
that judges them — CEA-FRAME-BUDGET judges the CPU frame, the GPU frame and each
affected subsystem — reads those sections and treats each `NOT ASSESSED` one as
its own gap.

First match wins:

1. **OVER BUDGET** — the Budget result is `OVER BUDGET`. At
   `performance.enforce: block` add `— release-stopping`; at `off` add
   `— informational (performance.enforce: off)`.
2. **REGRESSION** — the Regression result is `REGRESSION`. When 1 also applies,
   the verdict is `OVER BUDGET, REGRESSION`.
3. **NOT ASSESSED** — no failure above, and the Budget result is
   `NOT ASSESSED`. Name each reason.
4. **WITHIN BUDGET** — the Budget result is `WITHIN BUDGET` and the Regression
   result is not `REGRESSION`. Its verdict line names the Regression result when
   it is `NOT ASSESSED`.

**NOT ASSESSED ranks below OVER BUDGET and REGRESSION and above WITHIN
BUDGET.** A known miss is more actionable than an unknown, and a run that never
compared against a budget has not shown the frame fits one.

**Every verdict line names what did not run.** For example:

> `Verdict: WITHIN BUDGET — regression NOT ASSESSED (no baseline); counters NOT ASSESSED (no hardware counter data); CPU vs GPU NOT ASSESSED (no GPU timestamps in captures/frame.csv)`

A plain `WITHIN BUDGET` is reachable only when every section ran.

### The report template

```markdown
# Benchmark Report — [scene or benchmark set]
Generated: [date]   Engine: [engine.name, or unset]
Story: [--story path | none]
Module: [docs/architecture/modules/<module>.md from --module | none]

## Verdict
Budget result: [OVER BUDGET | WITHIN BUDGET | NOT ASSESSED — reason]
Regression result: [REGRESSION | NO REGRESSION | NOT ASSESSED — reason]
[OVER BUDGET | REGRESSION | OVER BUDGET, REGRESSION | NOT ASSESSED | WITHIN BUDGET] — [every NOT ASSESSED section, with its reason]

## Inputs
| Path | Kind | Samples | Build config | Platform / GPU | Resolution | Scene |
|------|------|---------|--------------|----------------|------------|-------|
| [path] | [frame-time / counters / hotspots / microbenchmark / binary — not read] | [N] | [value / unknown] | [value / unknown] | [value / unknown] | [value / unknown] |

## Frame Budget
Budget: [X ms — performance.frame_budget_ms | X ms — derived from performance.target_framerate | NOT ASSESSED — both unset]
Enforcement: [warn | block | off]

## Frame Time   (nearest-rank, N = [n], [k] warm-up frames dropped: [why / none])
| Metric | Value (ms) | vs budget |
|--------|-----------|-----------|
| P50 | | [OK / OVER by X ms / NOT ASSESSED] |
| P95 | | |
| P99 | | |
| Max | | |
| Mean | | |
Frames over budget: [n] ([%])

## CPU vs GPU
[CPU-bound X % · GPU-bound Y % · balanced Z % · unclassified W % — overall and among over-budget frames]
[or: NOT ASSESSED — reason]

| Side | P50 (ms) | P95 (ms) | P99 (ms) | P95 vs budget |
|------|----------|----------|----------|---------------|
| CPU frame | | | | [OK / OVER by X ms / NOT ASSESSED] |
| GPU frame | | | | |
[each side with no series: NOT ASSESSED — reason]

## Affected Subsystems   (--subsystems: [list | none named])
| Subsystem / zone | Side (CPU / GPU) | Timing basis and source phase | P50 (ms) | P95 (ms) | P99 (ms) | Frames | Frames without the zone |
|------------------|------------------|-------------------------------|----------|----------|----------|--------|-------------------------|
[budget-comparable wall-clock timings only; optional aggregate work is separate and never substituted for these percentiles]
[each named subsystem with only aggregate data: NOT ASSESSED — wall-clock timing unavailable]
[each named subsystem not in the capture: NOT ASSESSED — zone not in <path>]
[or: NOT ASSESSED — no affected subsystems named | no zone data in <path>]

## Hotspots
| # | Zone / function | Thread | Total ms | ms/frame (mean / P95) | % of frame | Calls | Location |
|---|-----------------|--------|----------|-----------------------|------------|-------|----------|
[or: NOT ASSESSED — reason]

## Hardware Counters
| Counter | Count | Rate | Scope |
|---------|-------|------|-------|
[each absent counter: NOT ASSESSED — <counter> not in <path>]

## Microbenchmarks
| Benchmark | Median | Spread | Unit | Iterations |
|-----------|--------|--------|------|------------|
[or: none given]

## Regression vs Baseline
Baseline: [path | NOT ASSESSED — no baseline | NOT ASSESSED — captures not comparable (difference)]
Threshold: [X % | NOT ASSESSED — no threshold given]
Result: [REGRESSION | NO REGRESSION | NOT ASSESSED — reason]   (the same line as under Verdict)
| Metric | Baseline | Current | Δ ms | Δ % | Regression? |
|--------|----------|---------|------|-----|-------------|

## Findings
1. [What the numbers show, each citing the row above it comes from]

## Not Assessed
- [Every section that did not run, its reason, and what would let it run]
```

Close the run with the verdict line, the report path (or `not written — the user
declined`), and Phase 6's next step for that verdict, then:
Run status: **COMPLETE** — benchmark report generated. That word says the report
was produced; the verdict line above is what the numbers say. The only other
outcome is the `NOT ASSESSED — no capture` stop in SKILL.md.

---
