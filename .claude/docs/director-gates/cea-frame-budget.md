> Gate definition. The spawning skill passes this file's path to the director agent; the AGENT reads it — the parent session should not.

# CEA-FRAME-BUDGET — Frame Budget Review of a Tick or Frame-Graph Change

Agent: `chief-engine-architect` | Model tier: Opus | Domain: Frame budgets, CPU/GPU frame time per subsystem

**Applies only when** `engine.name` is `Custom`. On any other engine, do not
spawn this gate.

**Trigger**: Before a change to the engine's main tick (update order, job
graph, simulation step) or to the frame graph (render passes, queues, frames
in flight) is accepted — from `/team-frame-pipeline`, or from any skill
reviewing such a change.

**Context to pass**:
- The change: story or ADR path and the changed file paths
- `performance.frame_budget_ms` and `performance.target_framerate` from
  `project.yaml`, or "unset"
- The per-subsystem budget split (path to the architecture document or ADR
  that records it), or "none recorded"
- `/benchmark-report` output for the build with the change — and for the
  baseline without it, if one exists — or "none"
- The affected subsystems (the `--subsystems` list the report was run with),
  or "none named"
- For each capture: tool (Tracy, PIX, RenderDoc, Nsight, perf, VTune,
  Superluminal or benchmark output), machine and GPU, build preset

**Prompt**:
> "Review whether this change keeps the frame within budget. Use only the
> numbers in the `/benchmark-report` output you were given — never an
> estimate of your own. Read its `CPU vs GPU` table for CPU frame and GPU
> frame P50, P95 and P99, its `Affected Subsystems` table for each affected
> subsystem's P50, P95 and P99, and its `Regression result` line for the
> comparison — not the verdict word, which does not carry them. Check CPU frame time and GPU frame time separately
> against `performance.frame_budget_ms`, and each affected subsystem's P50,
> P95 and P99 against its slice of the budget. Check that the captures come
> from an optimized build (a release or profile preset, not a debug build) and
> that baseline and change were captured on the same machine and preset.
> Compare against the baseline when there is one, and say whether the frame
> is CPU-bound or GPU-bound before and after. Return APPROVE (CPU and GPU
> frame P95 within budget and every affected subsystem's P95 within its
> slice), CONCERNS [P95 within budget but P99 over, a regression the story or
> ADR did not allow for, the bound flipping between CPU and GPU, or no
> baseline so a regression could not be measured], or REJECT [CPU or GPU
> frame P95 over `performance.frame_budget_ms`, or an affected subsystem's
> P95 over its slice]."

**Verdicts**: APPROVE / CONCERNS / REJECT

**NOT ASSESSED when** (see `director-gates.md`, Standard Verdict Format):
- No `/benchmark-report` output or capture for the build with the change —
  name the capture that is needed
- `performance.frame_budget_ms` is unset
- The only captures come from a debug build, or from different machines or
  presets for baseline and change, so no comparison holds
- No per-subsystem budget split is recorded and the whole frame is within
  budget — the per-subsystem part could not be judged
- The report's CPU frame or GPU frame row is missing or reads `NOT ASSESSED`,
  and the side that is present is within budget — one side of the frame was
  never measured
- An affected subsystem has no P50/P95/P99 row in the report (no
  `--subsystems` list, or its zone not in the capture) and nothing measured is
  over — name each subsystem with no row
- A baseline exists but the report's `Regression result` reads
  `NOT ASSESSED` for a reason other than `no baseline` (captures not
  comparable, no threshold given)

A known breach outranks a gap: a CPU or GPU frame P95, or an affected
subsystem's P95, over its budget is REJECT even when another column or the
split is missing. Never return APPROVE from code inspection alone, nor from the
report's verdict word alone.
