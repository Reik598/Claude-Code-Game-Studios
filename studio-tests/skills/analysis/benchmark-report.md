# Skill Test Spec: /benchmark-report

## Skill Summary

`/benchmark-report` reads what a run **measured** — a profiler capture exported
as text, `perf stat` / VTune counter output, a hotspot export, or microbenchmark
output (Google Benchmark JSON, Criterion `estimates.json`, `cargo bench`) — and
reports frame-time P50/P95/P99/max/mean (nearest-rank), CPU-bound vs GPU-bound
per frame, hotspots, hardware counters (L1, LLC, branches, IPC), microbenchmarks,
and regression against a baseline. It resolves `perf_budgets`, `engine`,
`automation` and `workflow` from the config block injected at its top, and
`performance.enforce` with `get_effective_yaml_key`. Every input is recorded
`FOUND` or `ABSENT` before any report; no readable capture stops the run with
`NOT ASSESSED — no capture`. A binary capture (`.tracy`, `.wpix`, `.rdc`,
`.nsys-rep`, `.etl`) is `NOT ASSESSED — binary capture, export it to text`, and
the export command is `NOT SOURCEABLE` unless `docs/engine-reference/custom/`
documents it. An unset budget is `NOT ASSESSED` — never 16.6 or 8.33 ms. Verdict,
first match wins: OVER BUDGET (P95 over budget) → REGRESSION (over threshold) →
NOT ASSESSED → WITHIN BUDGET; every verdict line names what did not run. Above the
verdict word it writes a `Budget result` line and a separate `Regression result`
line (`REGRESSION` / `NO REGRESSION` / `NOT ASSESSED — <reason>`), so a consumer
that needs the comparison reads the regression result rather than the verdict
word; `NOT ASSESSED — no baseline` on a scene's first capture is the
first-baseline exemption. It reports CPU frame and GPU frame P50/P95/P99 apart
from the whole frame, and P50/P95/P99 per subsystem for the zones named with
`--subsystems` (`NOT ASSESSED — no affected subsystems named` without it). It computes the
statistics with the read-only helper `.claude/scripts/frame-stats.sh` (never by
sorting or counting rows in context), writes `Story:` and `Module:` header lines
from `--story` and `--module` for `/story-done`, asks
"May I write this benchmark report to
`production/qa/benchmarks/benchmark-[date]-[HHMM]-[scene-slug].md`?", never overwrites an existing report (it proposes a `-2` suffix), and
keeps every `NOT ASSESSED` line in the file. It is user-invoked only
(`disable-model-invocation: true`). Run status COMPLETE means the report was produced. Works on any
engine; on a non-Custom engine the counter section is expected to be
`NOT ASSESSED` and is named, not dropped. No director gates.

---

## Static Assertions (Structural)

- [ ] Has required frontmatter fields: `name`, `description`, `argument-hint`, `user-invocable`, `allowed-tools`; `model: sonnet`; `disable-model-invocation: true`
- [ ] Has ≥2 phase headings (Phases 1–6), with Phase 3 in `references/statistics.md` and Phase 5's template and verdict in `references/report.md`
- [ ] Contains verdict keywords: OVER BUDGET, REGRESSION, NOT ASSESSED, WITHIN BUDGET — and states NOT ASSESSED ranks below OVER BUDGET and REGRESSION and above WITHIN BUDGET
- [ ] Contains the "Insufficient input" block: inputs recorded FOUND/ABSENT; `NOT ASSESSED — no capture` as the whole verdict when nothing is readable
- [ ] States the percentile method (nearest-rank, `ceil(k/100 × N)`) and that P95 decides the budget row
- [ ] The report template has `Budget result:` and `Regression result:` lines under `## Verdict`, a CPU frame / GPU frame percentile table, and an `## Affected Subsystems` table; `argument-hint` includes `--subsystems`
- [ ] Never falls back to 16.6 or 8.33 ms when both budget keys are unset
- [ ] Contains "May I write" naming `production/qa/benchmarks/benchmark-[date]-[HHMM]-[scene-slug].md`, and never overwrites an existing report
- [ ] Computes N, P50/P95/P99, max, mean and the over-budget count with `bash .claude/scripts/frame-stats.sh`; `allowed-tools` grants it and has no `sort` or `file`
- [ ] With no path, globs `tests/benchmarks/**`, `production/qa/benchmarks/captures/**`, `engine/**/benches/**`, `crates/**/benches/**`, `game/**/benches/**` and `target/criterion/**/new/estimates.json`
- [ ] The report template has `Story:` and `Module:` header lines; `argument-hint` includes `--story` and `--module`
- [ ] Has a next-step handoff (Phase 6: `/perf-profile`, `/team-frame-pipeline`, `/dev-story`, `/memory-audit`, `/project-settings`)
- [ ] `allowed-tools` has no Edit and no general Bash — the skill does not edit code, captures or `project.yaml`

---

## Director Gate Checks

None. The skill measures; `CEA-FRAME-BUDGET` consumes its output but is run by
`/team-frame-pipeline`, not here.

---

## Fixture Defaults

Every case's `project.yaml` sets `modes.rigor: minimal` and
`modes.automation: collaborative`, with no `project.local.yaml`, unless its own
Fixture says otherwise. Rules: `studio-tests/CLAUDE.md` §
Fixture defaults.

---

## Test Cases

### Case 1: Happy Path — CSV capture over budget, CPU-bound

**Fixture:**
- `project.yaml`: `engine.name: Custom`, `performance.frame_budget_ms: 8.33`; `performance.enforce` unset
- `production/qa/benchmarks/captures/city.csv`: header `frame,cpu_ms,gpu_ms,present_wait_ms`, 1,200 rows; release preset, RTX-class GPU, 2560×1440, scene `city` stated in a comment line; P95 of `cpu_ms`-critical frame time is 9.1 ms; GPU time shorter than CPU in most over-budget frames, with GPU idle between submissions
- No baseline, no counter file

**Input:** `/benchmark-report production/qa/benchmarks/captures/city.csv --threshold 5`

**Expected behavior:**
1. Inputs recorded: capture FOUND (frame-time, N = 1,200), baseline ABSENT, budget 8.33 ms from `performance.frame_budget_ms`
2. Percentiles computed by nearest-rank with `frame-stats.sh city.csv <column> 8.33`; method named
3. P95 9.1 ms > 8.33 ms → OVER; frames-over-budget count and share reported
4. CPU vs GPU classified per frame; over-budget frames mostly CPU-bound
5. Hotspots `NOT ASSESSED — no zone or sample data`; counters `NOT ASSESSED — no hardware counter data`; `Regression result: NOT ASSESSED — no baseline` (first-baseline exemption, still written); CPU frame and GPU frame P50/P95/P99 reported from `cpu_ms` and `gpu_ms` apart from the whole-frame row; `Subsystems: NOT ASSESSED — no affected subsystems named`
6. Verdict: `OVER BUDGET — regression NOT ASSESSED (no baseline); hotspots NOT ASSESSED (...); counters NOT ASSESSED (...)`
7. Asks "May I write this benchmark report to `production/qa/benchmarks/benchmark-[date]-[HHMM]-[scene-slug].md`?"
8. Phase 6 points to `/perf-profile` and `/team-frame-pipeline`

**Assertions:**
- [ ] Every number cites `city.csv`
- [ ] Verdict word is OVER BUDGET and the line names each NOT ASSESSED section
- [ ] `Budget result: OVER BUDGET` and `Regression result: NOT ASSESSED — no baseline` both appear under `## Verdict`
- [ ] CPU frame and GPU frame percentiles are computed from their own columns, never copied from the whole-frame row
- [ ] No hotspot or counter is inferred from frame times
- [ ] "May I write" precedes any write; NOT ASSESSED lines kept in the written file

---

### Case 2: No Capture — whole verdict NOT ASSESSED

**Fixture:**
- `engine.name: Custom`, budget set
- `tests/benchmarks/` and `production/qa/benchmarks/captures/` hold no capture or output file

**Input:** `/benchmark-report`

**Expected behavior:**
1. Phase 1 globs both folders and finds nothing
2. Stops with `NOT ASSESSED — no capture`, naming what was looked for and how to make one (run the benchmark target in `tests/benchmarks/`, or record a profiler capture and re-run with its path)
3. No report, no percentiles, no "May I write"

**Assertions:**
- [ ] Whole verdict `NOT ASSESSED — no capture`
- [ ] No filled-in template and no write prompt
- [ ] Says how to produce a capture

---

### Case 3: Budget Unset — no 16.6 / 8.33 fallback

**Fixture:**
- `project.yaml`: `engine.name: Custom`, no `performance` block
- A valid frame-time CSV with P95 6.1 ms

**Input:** `/benchmark-report captures/frame.csv`

**Expected behavior:**
1. Budget line: `Frame budget: NOT ASSESSED — performance.frame_budget_ms and performance.target_framerate unset`
2. Percentiles reported; every `vs budget` cell `NOT ASSESSED — budget unset`
3. Verdict NOT ASSESSED (not WITHIN BUDGET), naming the unset budget
4. Phase 6 suggests `/project-settings performance.frame_budget_ms=…`

**Assertions:**
- [ ] Verdict is NOT ASSESSED, never WITHIN BUDGET, although 6.1 ms is under both common targets
- [ ] Neither 16.6 nor 8.33 ms appears as the budget
- [ ] Budget-setting next step named

**Variant:** only `performance.target_framerate: 120` set → budget 8.33 ms reported as derived from `target_framerate`.

---

### Case 4: Binary Capture Only — export required, NOT SOURCEABLE export command

**Fixture:**
- `engine.name: Custom`, budget 16.6 ms
- `captures/run.tracy` (binary) is the only input
- `docs/engine-reference/custom/VERSION.md` exists and does not document Tracy's export tool

**Input:** `/benchmark-report captures/run.tracy`

**Expected behavior:**
1. Classifies `run.tracy` as a binary capture: `NOT ASSESSED — binary capture, export it to text`
2. Asks the user to export with the profiler's own exporter; writes `NOT SOURCEABLE — Tracy export is not covered by docs/engine-reference/custom/` instead of an export command from memory
3. No readable capture → whole verdict `NOT ASSESSED — no capture`
4. Does not guess frame times from file size or name

**Assertions:**
- [ ] No export command written from memory
- [ ] `NOT SOURCEABLE` line names the path
- [ ] No numbers reported

---

### Case 5: Regression vs Baseline — threshold and comparability

**Fixture:**
- `engine.name: Custom`, budget 8.33 ms
- `captures/after.csv` (release, GPU A, 1440p, scene `city`), P95 7.9 ms
- `captures/before.csv` (release, GPU A, 1440p, scene `city`), P95 7.2 ms
- Variant: `before.csv` was captured on a debug preset

**Input:** `/benchmark-report captures/after.csv --baseline captures/before.csv --threshold 5`

**Expected behavior:**
1. P95 7.9 ≤ 8.33 → OK against budget
2. P95 delta +0.7 ms (+9.7 %) > 5 % → REGRESSION
3. Verdict: `REGRESSION — ...` naming any section that did not run
4. Max frame time reported but does not by itself call a regression
5. Variant: build configuration differs → `Regression result: NOT ASSESSED — captures not comparable (build config: debug vs release)`, on its own line under `## Verdict`; the budget check still ran (P95 OK), so `Budget result: WITHIN BUDGET` and the verdict is `WITHIN BUDGET — regression NOT ASSESSED (captures not comparable ...)`, never REGRESSION on incomparable data

**Assertions:**
- [ ] Deltas in ms and percent for P50, P95, P99, max
- [ ] Verdict REGRESSION in the main run
- [ ] Variant reports the comparability difference by name
- [ ] Variant writes the `Regression result` line as NOT ASSESSED separately from the `Budget result` line — a consumer reading only the regression result sees the gap

---

### Case 6: No Threshold in Autonomous Mode

**Fixture:**
- `modes.automation: autonomous`; baseline and capture comparable; no `--threshold`

**Input:** `/benchmark-report captures/after.csv --baseline captures/before.csv`

**Expected behavior:** No question asked (autonomous); deltas reported; `Regression: NOT ASSESSED — no threshold given`; no default threshold invented.

**Assertions:**
- [ ] No 2 %/5 %/10 % threshold applied silently
- [ ] Regression line is NOT ASSESSED and named on the verdict line

---

### Case 7: Non-Custom Engine — runs, counters named NOT ASSESSED

**Fixture:**
- `engine.name: Godot`, budget 16.6 ms
- A Godot profiler frame-time CSV export; no counter output

**Input:** `/benchmark-report captures/godot_frames.csv`

**Expected behavior:** Runs (the skill works on any engine with captures); frame-time sections reported; `Counters: NOT ASSESSED — no hardware counter data` stays in the report and on the verdict line.

**Assertions:**
- [ ] The skill does not refuse on a non-Custom engine
- [ ] Counter section is present as NOT ASSESSED, not omitted

---

### Case 8: Affected subsystems — per-subsystem percentiles for the named set

**Fixture:**
- `engine.name: Custom`, budget 8.33 ms
- `captures/zones.json`: a Chrome-trace export with per-frame zones `Physics::Step` (worker threads) and `Render::Shadows` (GPU queue `graphics`), 600 frames; `Animation::Sample` does not appear

**Input:** `/benchmark-report captures/zones.json --subsystems Physics::Step,Render::Shadows,Animation::Sample`

**Expected behavior:**
1. Per frame, derive each named subsystem's budget-comparable wall-clock duration from phase boundaries and dependencies; P50/P95/P99 by nearest-rank, with the frame count and the count of frames without the zone. Sum parallel work only in a separately labelled aggregate-work column.
2. `Animation::Sample: NOT ASSESSED — zone not in captures/zones.json`; the section is named incomplete on the verdict line
3. No zone is matched by a similar-looking name

**Assertions:**
- [ ] `## Affected Subsystems` has a P50/P95/P99 row for `Physics::Step` and `Render::Shadows`
- [ ] The missing subsystem is a named NOT ASSESSED line, not dropped
- [ ] Variant — no `--subsystems`: the section reads `NOT ASSESSED — no affected subsystems named`

---

### Case 9: Story evidence and a same-day re-run

**Fixture:** `engine.name: Custom`, budget 8.33 ms; a capture of scene `city`;
`production/qa/benchmarks/benchmark-2026-11-17-1030-city.md` already exists.

**Input:** `/benchmark-report captures/city2.csv --story production/epics/render/story-004.md --module renderer` at 10:30

**Expected behavior:** the report's header reads
`Story: production/epics/render/story-004.md` and
`Module: docs/architecture/modules/renderer.md`; the proposed path
`benchmark-2026-11-17-1030-city.md` exists, so it proposes
`benchmark-2026-11-17-1030-city-2.md` and says why. Without `--story`/`--module`
both lines read `none`.

**Assertions:**
- [ ] `Story:` and `Module:` lines are in the written header
- [ ] The existing report is never overwritten

---

### Case 10: Crate-local Criterion output found with no path

**Fixture:** a Rust engine with `crates/jobs/benches/` and
`target/criterion/submit/new/estimates.json`; `tests/benchmarks/` absent.

**Input:** `/benchmark-report`

**Expected behavior:** the default glob lists the Criterion estimates and the
crate-local bench files and asks which to read; it never stops with
`NOT ASSESSED — no capture`, and it skips the rest of `target/`.

**Assertions:**
- [ ] `target/criterion/submit/new/estimates.json` is offered
- [ ] No other `target/` file is listed

---

## Protocol Compliance

- [ ] Four workers each run 2 ms concurrently inside a 2 ms phase: the CPU phase is 2 ms, never 8 ms; aggregate work may be shown separately as 8 ms
- [ ] Only summed worker durations, without phase boundaries or clock correlation: subsystem timing is NOT ASSESSED, never compared to its wall-clock budget

- [ ] Records every input FOUND or ABSENT before producing a report
- [ ] Every number comes from an input file cited by path; percentiles computed, not guessed
- [ ] An unset budget is NOT ASSESSED; no 16.6/8.33 ms fallback
- [ ] Applies `performance.enforce` (`block` → release-stopping, `off` → informational)
- [ ] Every verdict line names each section that did not run
- [ ] Asks "May I write" naming `production/qa/benchmarks/benchmark-[date]-[HHMM]-[scene-slug].md`; never overwrites; keeps NOT ASSESSED lines in the file
- [ ] Ends with the Phase 6 next step for the verdict
- [ ] Does not edit code, captures or `project.yaml`

---

## Coverage Notes

- `performance.enforce: block` (verdict suffix `— release-stopping`) is not exercised by its own case.
- Microbenchmark-only input (frame budget `NOT ASSESSED — not frame-time data`) has no dedicated case.
- Tick columns with no stated frequency are not covered.
