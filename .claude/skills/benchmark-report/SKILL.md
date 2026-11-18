---
name: benchmark-report
description: "Frame-time report from profiler captures or benchmark output — P50/P95/P99, CPU vs GPU bound, hotspots, cache-miss counters, regression vs a baseline."
argument-hint: "[capture-or-output-path ...] [--baseline <path>] [--threshold <percent>] [--subsystems <zone,...>] [--story <story-path>] [--module <module>]"
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion, Bash(wc *), Bash(bash .claude/scripts/frame-stats.sh *), Bash(bash "*/.claude/skills/benchmark-report/../../hooks/yaml-helper.sh" resolve_config *), Bash(bash "*/.claude/skills/benchmark-report/../../hooks/yaml-helper.sh" get_effective_yaml_key *)
model: sonnet
---

!`bash "${CLAUDE_SKILL_DIR}/../../hooks/yaml-helper.sh" resolve_config --keys perf_budgets,engine,automation,workflow`

Resolved above — use as-is. No block → defaults in
`.claude/docs/config-resolution.md`.

# Benchmark Report

> **Explicit invocation only** (`disable-model-invocation: true`): this skill
> runs when the user types `/benchmark-report`. Claude does not start it from context or
> through the Skill tool; another skill that needs it prints the command for
> the user. It runs on any engine and is oriented to a Custom one.

Every `AskUserQuestion` call follows `.claude/docs/automation-modes.md`
(collaborative asks always · guided major-only · autonomous logs and proceeds;
`automation_always_ask` categories always prompt).

`/perf-profile` reads code and names *candidate* hotspots. This skill reads what
a run **measured** — a profiler capture or a benchmark's output — and reports
the numbers in it. It never estimates a number the capture does not hold.

**Who it is for.** It works on any project that has captures. Its profiler list
(Tracy, PIX, RenderDoc, Nsight, Superluminal, `perf`, VTune) and its counter
section (cache misses, LLC, branches) are oriented to a project that builds its
own engine (`engine.name: Custom`). On Godot, Unity, Unreal or Web, a capture
exported as text by that engine's profiler still gives the frame-time sections;
expect the counter section to be `NOT ASSESSED`, and say so rather than leave it
out.

## Insufficient input — check this before producing any report

**If the inputs this skill needs do not exist, the answer is "could not run" —
not a filled-in report.** Check first, and stop if the check fails.

1. List the inputs this run reads: each capture or output path given, the
   baseline, and the frame budget from the block above.
2. For each, record `FOUND` or `ABSENT` — not "assumed present".
3. If an input a section needs is ABSENT, that section is
   **`NOT ASSESSED — <reason>`**. Do not estimate it, do not infer it from an
   adjacent artifact, and do not leave a cell for the reader to fill.
4. If **no capture or benchmark output** is readable, stop and report
   **`NOT ASSESSED — no capture`** as the whole verdict, naming what was looked
   for and how to produce one (Phase 1).

**A verdict of `NOT ASSESSED` is a success.** It is the correct answer when there
is nothing measured. The failure it prevents: a report that reads
"P95 6.1 ms — within budget" when no capture was read, or when the budget was
never set.

**Absence of evidence is never evidence of absence.** A capture with no GPU
timestamps has not shown the frame is CPU-bound; a capture with no hardware
counters has not shown the cache behaviour is fine.

---

## Phase 1: Find the Inputs

Read the arguments: one or more paths (files or folders), `--baseline <path>`,
`--threshold <percent>`, `--subsystems <zone,...>` — the profiler zones of the
subsystems a change affects, whose own percentiles a consumer such as
CEA-FRAME-BUDGET judges against their budget slices (Phase 3f). Without it, the
per-subsystem section reads `NOT ASSESSED — no affected subsystems named`.

`--story <story-path>` and `--module <module>` say what the measurement is
evidence for. They are written as the report's `Story:` and `Module:` header
lines (the module as its spec path, `docs/architecture/modules/<module>.md`),
which `/story-done` matches when it closes an engine story whose
`Frame pipeline: yes` line asks for perf evidence. Neither given → both lines
read `none`, and no story can cite the report by them.

**No path given:** glob `tests/benchmarks/**`,
`production/qa/benchmarks/captures/**`, the module-local bench roots of
`.claude/docs/custom-engine-layout.md` (`engine/**/benches/**`,
`crates/**/benches/**`, `game/**/benches/**`) and Criterion's saved estimates,
`target/criterion/**/new/estimates.json` (skip the rest of `target/`: build
output, not results), for capture or output files. List what was found with
size and date, and ask which to read. Found nothing: stop with
`NOT ASSESSED — no capture`, and say how to make one — run the project's
benchmark target (`tests/benchmarks/` on a Custom project) or record a profiler
capture of the scene, then re-run with its path.

For each path, classify it by its extension and its first lines (read them;
never classify by the name alone):

| Kind | Examples | Read as |
|---|---|---|
| **Frame-time capture, text** | a profiler's CSV or JSON export with one row per frame; a Chrome-trace JSON | frame times, and zones if present |
| **Counter output, text** | `perf stat` output, a VTune CSV report | hardware counters |
| **Hotspot output, text** | `perf report` or `perf script` text, a zone-statistics export, a VTune hotspots CSV | ranked functions or zones |
| **Microbenchmark output** | Google Benchmark JSON, Criterion `estimates.json`, `cargo bench` text | per-benchmark times — not frame times |
| **Binary capture** | `.tracy`, `.wpix`, `.rdc`, `.nsys-rep`, `.etl` and similar | **not readable here** |

**A binary capture is `NOT ASSESSED — binary capture, export it to text`.** Ask
the user to export it with the profiler's own exporter (CSV, JSON or text) and
re-run with the export. Do not guess its contents from its size or name. The
export command for each tool is `NOT SOURCEABLE — <profiler> export is not
covered by docs/engine-reference/custom/` unless that folder documents it; never
write one from memory.

**A text file whose columns you cannot identify** (no header naming a frame
time, a zone or a counter): ask which column holds what. Never pick the column
that looks plausible.

Record per input: path, kind, frame or sample count, and the build
configuration, platform, GPU, resolution and scene where the file states them —
`unknown` where it does not.

---

## Phase 2: Resolve the Frame Budget

From the `perf_budgets` line above:

- `frame_budget_ms` set → that is the budget, source `performance.frame_budget_ms`.
- Only `target_framerate` set → budget `1000 / target_framerate` ms, and the
  report says it was derived.
- Both set and they disagree by more than 0.1 ms → use `frame_budget_ms`, and
  report the disagreement by name.
- Both unset → **`Frame budget: NOT ASSESSED — performance.frame_budget_ms and
  performance.target_framerate unset`**. Report the percentiles; compare them
  to nothing. Never fall back to 16.6 ms or 8.33 ms: an unset budget is not a
  budget that was met.

Then read what a violation means, as one plain command:

```bash
bash "${CLAUDE_SKILL_DIR}/../../hooks/yaml-helper.sh" get_effective_yaml_key performance.enforce
```

`warn` or empty (the default) reports an over-budget result as a finding;
`block` makes it release-stopping, and the report says so; `off` reports the
values without raising them as findings. Any other value: say so and treat it
as `warn` (the same rule as `/perf-profile`).

---

## Phase 3: Measure

**Read `references/statistics.md` now and follow it** — the percentile method,
CPU vs GPU bound per frame, hotspots and hardware counters are in that file, not
here. Read it again if the conversation was compacted or resumed during this
phase.

---

## Phase 4: Regression vs Baseline

A baseline is a capture of the same scene on the same build configuration and
hardware, or a previous report from this skill
(`production/qa/benchmarks/benchmark-*.md`).

- `--baseline` given → use it.
- None given → glob `production/qa/benchmarks/benchmark-*.md`; if one exists,
  ask whether the newest is the baseline. Never use it without that answer: a
  baseline of another scene makes every delta meaningless.
- None at all → **`Regression: NOT ASSESSED — no baseline`**.

**Comparable or not.** Compare the Phase 1 metadata. A known difference in build
configuration, platform, GPU, resolution or scene makes the comparison
**`Regression: NOT ASSESSED — captures not comparable (<the difference>)`**.
Metadata that is `unknown` on either side is listed beside the deltas.

**Threshold.** `--threshold <percent>` is the regression line. It has no
project setting and no default. Without it, ask (options: 2 %, 5 %, 10 %,
deltas only); in `autonomous` mode, or on "deltas only", report the deltas and
write **`Regression: NOT ASSESSED — no threshold given`**.

For P50, P95, P99 and max frame time — and the CPU frame and GPU frame
percentiles (Phase 3b) and each named subsystem's (Phase 3f) when both sides
have them — and for each microbenchmark, report
baseline, current, and the delta in ms and in percent. A metric worse by more
than the threshold is a **regression**. Max frame time is reported but never
calls a regression alone: one hitch is one sample.

**The regression result is its own line**, apart from the budget result
(`references/report.md`): `REGRESSION`, `NO REGRESSION`, or
`NOT ASSESSED — <reason>`. A consumer that needs the comparison — a gate that
judges a change against its baseline — reads this line, not the verdict word.
`NOT ASSESSED — no baseline` on the first capture of a scene (no `--baseline`,
and no earlier `benchmark-*.md` found) is the **first-baseline exemption**:
there is nothing to compare yet, and consumers that accept a first baseline
say so; every other reason is a gap.

---

## Phase 5: Write the Report

**Read `references/report.md` now and follow it** — the report template and the
verdict rules are in that file. Read it again if the conversation was compacted
or resumed during this phase.

Show the summary (verdict, the `Budget result` and `Regression result` lines,
the four percentiles against the budget, the CPU and GPU frame P95, the top
three hotspots, every `NOT ASSESSED` line) in conversation, then ask:
*"May I write this benchmark report to
`production/qa/benchmarks/benchmark-[date]-[HHMM]-[scene-slug].md`?"* —
the time and a short slug of the scene or benchmark set keep two runs of one
day apart (a confirmation re-run for `/perf-regression-triage` is usually the
same day). Glob the path first: this skill **never overwrites** a report,
because an earlier one may be the baseline or the evidence a bug cites. When it
exists, propose the same name with `-2` (then `-3`, …) and say why. Write only
after a yes, and create the folder if it is absent. On no, the report stays in
the conversation and the closing line says it was not written.

Keep every `NOT ASSESSED` line in the written file. A report whose gaps are
edited out on the way to disk reads, later, as a complete measurement.

---

## Phase 6: Next Steps

- `OVER BUDGET` or `REGRESSION` → run `/perf-profile [system]` on the top
  hotspot's system for code-level candidates; then `/team-frame-pipeline` when
  the fix changes the main tick or frame graph (Custom only), or `/dev-story`
  for a local fix.
- A hotspot in an allocator → `/memory-audit`. Memory that grows across the
  capture is measured by neither skill: its profiler memory-track export goes
  to `memory-allocator-specialist` on Custom (`performance-analyst` on another
  engine).
- `NOT ASSESSED` → supply what was missing: a text export of the capture, the
  budget (`/project-settings performance.frame_budget_ms=…`), a baseline, a
  threshold, or a capture with counters or GPU timestamps — then re-run
  `/benchmark-report`.
- `WITHIN BUDGET` → keep this report as the next run's baseline
  (`--baseline production/qa/benchmarks/benchmark-[date]-[HHMM]-[scene-slug].md`).

### Rules
- Every number in the report comes from an input file, cited by path.
- Percentiles are computed from the samples by `.claude/scripts/frame-stats.sh`,
  never read off a chart, guessed or counted in context.
- A section with no data says `NOT ASSESSED — <reason>`; it is never left out.
- This skill measures. It does not edit code, captures or `project.yaml`.
