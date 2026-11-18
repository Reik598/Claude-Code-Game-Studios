# /benchmark-report — Phase 3: Measure

> Part of `/benchmark-report`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 3: Measure

**In this file:**

- 3a Frame-time percentiles
- 3b CPU-bound vs GPU-bound per frame, and CPU and GPU frame percentiles
- 3c Hotspots
- 3d Hardware counters: cache misses, LLC, branches
- 3e Microbenchmarks
- 3f Per-subsystem timings for the named affected set

Every subsection either reports numbers read from an input, with its path, or
reads `NOT ASSESSED — <reason>`. None is left out of the report.

### 3a. Frame-time percentiles

Input: a frame-time capture (Phase 1). None → `Frame time: NOT ASSESSED — no
frame-time capture` (a microbenchmark or counter file is not one).

1. Take the frame-time column, in milliseconds. Convert other units (µs, ns,
   ticks with a stated frequency) and say which conversion was applied. A tick
   column with no stated frequency is `NOT ASSESSED — tick frequency unknown`.
2. Drop warm-up frames only when the capture marks them (a load or warm-up
   zone, a frame range the user names). Say how many were dropped and why; never
   drop outliers to improve a number.
3. Compute the numbers with the helper, as one plain command — never by
   sorting or counting the rows in context:

   ```bash
   bash .claude/scripts/frame-stats.sh <capture.csv> <column> [budget-ms] [--skip <warm-up rows>] [--scale <factor>]
   ```

   `<column>` is the header name (or its number) of the column step 1 chose;
   `--scale` applies step 1's conversion (`0.001` for µs, `0.000001` for ns);
   `--skip` drops step 2's marked warm-up rows when they are the first ones;
   the budget is Phase 2's, left out when it is unset. It prints `n`, `p50`,
   `p95`, `p99`, `max`, `mean` and, with a budget, `over_budget` and
   `over_share`, by the **nearest-rank** method: Pk is the value at rank
   `ceil(k/100 × N)` in ascending order. Report those values and name the
   method. An exit of 2 prints why on stderr (an unknown column, a value that
   is not a number, with its line) and no numbers: that section is
   `NOT ASSESSED — <the reason it printed>`. A capture the helper cannot read
   (JSON, a quoted field holding a comma): ask for a CSV export of the column;
   without one, the section is `NOT ASSESSED — no CSV export of <path>`.
4. N below 100 → report the numbers and flag `low sample count (N)`: a P99 of
   fewer than 100 frames is one frame.
5. Against the budget (Phase 2), per percentile: `OK` (≤ budget), `OVER`
   (> budget, with the gap in ms), or `NOT ASSESSED — budget unset`. Also report
   the count and share of frames over budget (`over_budget`, `over_share`).

**P95 decides the budget row.** P50 over budget means the frame is over budget
most of the time; P95 over budget means at least one frame in twenty misses; P99 or max
over budget with P95 under is reported as hitching, a finding, not an
over-budget verdict.

### 3b. CPU-bound vs GPU-bound per frame

Needs, per frame, both a CPU frame time (the critical path: the main or game
thread, and the render-submission thread where they are separate) and a GPU
frame time (GPU timestamp queries, or the profiler's GPU track).

- No GPU timing in the capture → `CPU vs GPU: NOT ASSESSED — no GPU timestamps
  in <path>`. Never call a frame CPU-bound because GPU time is missing.
- Both present → per frame: **GPU-bound** when the GPU time is the longer of the
  two and the CPU shows a wait on the GPU (a present, fence or swap-chain wait
  zone) in that frame; **CPU-bound** when the CPU critical path is the longer and
  the GPU shows idle time between submissions; **balanced** within 5 % of each
  other; **unclassified** when neither wait marker is in the capture — say so.
- Report the share of frames in each class, overall and among the over-budget
  frames. The over-budget frames' class is the one that says where to work.

**CPU frame and GPU frame percentiles.** A frame-budget review checks each side
against the budget on its own, so report them apart from the whole-frame row:
the CPU frame time series (the critical path above) and the GPU frame time
series (first GPU timestamp to last of the frame, across every queue the
capture records — overlap between queues is not summed), each with P50, P95
and P99 by 3a's nearest-rank method (`frame-stats.sh` on that column) and 3a's `OK` / `OVER` / `NOT ASSESSED`
against the budget. A side with no series in the capture is
`CPU frame: NOT ASSESSED — no CPU frame time in <path>` or
`GPU frame: NOT ASSESSED — no GPU timestamps in <path>`; never copy the
whole-frame percentiles into either side.

### 3c. Hotspots

Input: zones in a frame-time capture, or a hotspot output. None →
`Hotspots: NOT ASSESSED — no zone or sample data`.

- Rank by total time across the capture, and separately across the
  over-budget frames when there are any. Top 10 each.
- Per entry: zone or function name, thread, total ms, ms per frame (mean and
  P95), share of the frame, call count, and `file:line` when the capture records
  a source location — `source location not recorded` when it does not. Never
  look a location up by name and present it as the capture's.
- A sampling profiler's percentages are of samples, not of time: say which.

### 3d. Hardware counters: cache misses, LLC, branches

Input: counter output (`perf stat`, VTune, or counters exported from the
capture). Report each counter the file holds, as raw count and as a rate
(per 1000 instructions, or misses ÷ references), with the scope it was measured
over (whole process, one thread, one zone):

| Counter | Present? |
|---|---|
| L1 data cache misses | value, or `absent` |
| Last-level cache (LLC) misses and references | value, or `absent` |
| Branch misses and branches | value, or `absent` |
| Instructions and cycles (IPC) | value, or `absent` |

**Each absent counter is named:** `Counters: NOT ASSESSED — <counter> not in
<path>`. No counter output at all → `Counters: NOT ASSESSED — no hardware
counter data` (the usual result for an engine profiler capture alone). Do not
infer cache behaviour from frame times or from the code.

Counter names differ per CPU vendor and tool. Use the name the file prints;
mapping one tool's event name onto another is `NOT SOURCEABLE` unless
`docs/engine-reference/custom/` documents it.

### 3e. Microbenchmarks

Input: microbenchmark output. Per benchmark: name, the time per iteration the
file reports (its median and spread when it has repetitions, else its single
value), unit, and iteration count. One repetition → flag `single run, no
spread`; two → flag `2 runs, spread not assessed` (under 3 the spread is not
judged). These are not frame times: the frame-budget row stays
`NOT ASSESSED — not frame-time data` unless a frame-time capture was also
given.

### 3f. Per-subsystem timings for the named affected set

Input: the `--subsystems` list (Phase 1) and zone data in a frame-time capture.
No list → `Subsystems: NOT ASSESSED — no affected subsystems named`; zones
absent from the capture → `Subsystems: NOT ASSESSED — no zone data in <path>`.

For each named subsystem:

1. Match it to the capture's zones by the exact zone name given — ask when a
   name matches none or several; never pick the zone that looks closest.
2. Read the budget's timing definition from `docs/architecture/frame-budget.md`
   or its ADR. Report wall-clock critical-path duration for CPU phases and the
   elapsed GPU interval across participating queues for GPU phases. Use an
   enclosing phase zone or correlated start/end timestamps with the dependency
   information needed by that definition. Do not sum parallel thread or queue
   durations: four concurrent 2 ms jobs are not an 8 ms critical-path phase.
   Sum within a serial phase only when the trace proves its work is sequential;
   nested instances count once. Optional summed thread/queue time is labelled
   `aggregate work`, in a separate column, never compared to a wall-clock budget.
   If only aggregate durations are available or the clock correlation or budget
   definition is unknown, that subsystem's budget-comparable timing is
   `NOT ASSESSED — wall-clock timing unavailable`; retain the observed work.
3. Report P50, P95 and P99 of each series by 3a's nearest-rank method
   (`frame-stats.sh` on the series when the capture holds it as a per-frame
   CSV column; otherwise `NOT ASSESSED — no per-frame <zone> column in <path>`
   — ask for that export), the frame
   count it covers, and how many frames had no such zone (those count as 0 ms,
   and the count is reported so a sparse subsystem is visible).
4. A named subsystem not found in the capture is its own line:
   `<subsystem>: NOT ASSESSED — zone not in <path>`. The section is complete
   only when every named subsystem has its percentiles.

This section reports times only. The per-subsystem budget split lives in the
project's architecture record, and the gate that holds it compares the two.

---
