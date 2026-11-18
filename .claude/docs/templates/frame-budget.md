# Frame Budget

<!-- Custom-engine projects only (engine.name: Custom). Lives at
     docs/architecture/frame-budget.md. Owner: chief-engine-architect; each
     lead owns its rows. The total comes from project.yaml
     (performance.target_framerate, performance.frame_budget_ms) — this file
     splits it, never restates a different total. Checked by the CEA-FRAME-BUDGET
     gate against /benchmark-report output. -->

**Target**: [120 fps → 8.33 ms | 60 fps → 16.6 ms] (from `project.yaml`) ·
**Reference hardware**: [CPU / GPU / platform per column] · **Last measured**: [date, capture]

## Whole frame — measured, not summed

| Measure | Budget (ms) | P50 | P95 | P99 | Source capture |
|---|---|---|---|---|---|
| CPU frame (critical path, frame start → present submitted) | = `frame_budget_ms` | | | | |
| GPU frame (first command of the frame → last queue done) | = `frame_budget_ms` | | | | |

These two rows are the pass/fail numbers. They come from whole-frame timings
in the capture. The rows below say where the time goes; their P99s are never
added up to make a frame P99 — slow outliers in different phases rarely land in
the same frame, and phases on different threads or queues overlap.

## CPU — critical path per frame

Phases on the main tick's dependency chain, in order. Job-parallel phases count
by their wall time on the critical path, not their summed thread time.

| Phase (main tick order) | Thread(s) / jobs | Budget (ms) | P99 measured (ms) | Owner |
|---|---|---|---|---|
| Input + platform events | main | | | platform-engineer |
| Scripting / gameplay | jobs | | | scripting-runtime-engineer |
| Animation | jobs | | | animation-systems-engineer |
| Physics (N fixed steps) | jobs | | | physics-simulation-engineer |
| ECS systems (other) | jobs | | | ecs-dod-architect |
| Streaming completion handling (on the tick) | main / jobs | | | world-streaming-engineer |
| Render extraction + command recording | render thread + jobs | | | rendering-lead |
| **Headroom** (≥ 10 % recommended) | | | | chief-engine-architect |
| **Critical path total** | | = `frame_budget_ms` | | |

## Independent threads — own deadlines, not on the critical path

These run beside the frame on their own clocks. Each is held to its own
deadline; none is added to the CPU total. A row here moves into the table above
only if the tick waits on it.

| Thread | Deadline | Budget (share of deadline) | Worst case measured | Owner |
|---|---|---|---|---|
| Audio device callback | buffer period (buffer size ÷ sample rate) | [e.g. ≤ 50 %] | | audio-engine-engineer |
| I/O and decompression | load-time targets from config | [throughput / latency] | | world-streaming-engineer |
| [other: network, telemetry upload] | | | | |

## GPU — per queue

Graphics, async compute and copy queues overlap. Each queue's rows sum to that
queue's busy time; the GPU frame row above is the measured span across all
queues, which is less than the sum when async work overlaps.

| Pass / pass group | Queue (graphics / async compute / copy) | Overlaps with | Budget (ms) | P99 measured (ms) | Owner |
|---|---|---|---|---|---|
| Depth prepass / visibility | graphics | | | | rendering-lead |
| Shadows | | | | | graphics-features-engineer |
| Lighting / GI / ray tracing | | | | | graphics-features-engineer |
| VFX / transparency | | | | | vfx-runtime-engineer |
| Post / upscaling | | | | | graphics-features-engineer |
| UI | | | | | ui-programmer |
| **GPU frame (measured span, not a sum)** | all | | = `frame_budget_ms` | | |

## Rules

- A change that moves a row over budget needs a trade elsewhere or an ADR that
  raises this row and lowers another; the total does not grow.
- The verdict reads the whole-frame CPU and GPU rows. Per-row P99s locate a
  problem; they never add up to a frame P99.
- "Measured" means a capture named in the header, a release build, and the
  reference hardware. Debug captures do not count (`/benchmark-report` says NOT ASSESSED).
- Rows with no measurement say `not measured`, never `0`.

## XR — display-locked frame

Applies only when `platform.targets` in `project.yaml` contains `XR` (matched
without regard to case); on any other project, ignore this section.

**Refresh rate**: [from `performance.target_framerate`, or `unset`] · **XR runtime**: [per the XR ADR]

- The budget, how each missed display deadline is counted and which captures
  count are stated in `performance-analyst`, "VR Frame Budgets"; this section
  does not restate them. With `performance.target_framerate` unset, the XR
  frame is NOT ASSESSED.
- **Frame submission (OpenXR).** OpenXR says only frames whose
  `xrBeginFrame` and `xrEndFrame` both succeed are composed. A second
  `xrBeginFrame` with no `xrEndFrame` between returns `XR_FRAME_DISCARDED`,
  and the frame begun before it is forfeited.
- **After a miss.** If more than one frame interval has passed since
  `xrWaitFrame` last returned, `xrWaitFrame` may return immediately or block
  until the beginning of the next frame interval. The runtime may change the throttling of
  `xrWaitFrame` in response to frame submission.
- What the display shows after a missed display deadline (a repeated frame, a
  reprojected one, or something else) is runtime-defined: `NOT SOURCEABLE` —
  the OpenXR core specification does not state it. Take it from the runtime
  vendor's documentation for the target, never from memory.

| XR measure | Value | Source capture |
|---|---|---|
| Missed display deadlines in the capture | [count, or `not measured`] | |
| Frames discarded (`XR_FRAME_DISCARDED`) | [count, or `not measured`] | |
