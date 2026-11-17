# /perf-regression-triage — Phases 3–5: Bisect, Attribute, Open the Bug

> Part of `/perf-regression-triage`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phases 3–5

**In this file:**

- 3 The bisect plan — builds first, then commits
- 4 Attribution, budget slice and SLA
- 5 The bug draft

### 3. The bisect plan — builds first, then commits

**The ends.** The last good and first bad commit (or build) — `--good` and
`--bad`, else ask: *which commit was the baseline captured on, and which the
regressed run?* `/benchmark-report` does not record commits, so this is never
inferred from the report. Check each with `git rev-parse --verify`. Unknown →
`Bisect: NOT ASSESSED — last-good and first-bad commits unknown`, and go to 4.

**The range.** `git rev-list --count <good>..<bad>` = N commits; a bisect takes
about ⌈log₂ N⌉ benchmark runs. Report both numbers.

**Builds first.** When CI keeps a build or a benchmark output per commit (ask;
Glob `production/qa/benchmarks/**` and `tests/benchmarks/**` for outputs named
by commit), bisect over those first: no build per step. Say which builds exist
in range and which are missing.

**Then commits.** Printed for the user — this skill does not run it:

```bash
git bisect start <bad> <good>
git bisect run <bisect script>
git bisect reset
```

The bisect script, drafted in the bug, does per commit: build with
`commands.build` (failed → `exit 125`, skip); run the benchmark the report came
from on the same machine and preset; compare each regressed metric with the
baseline plus the threshold; `exit 0` within it (good), `exit 1` over it (bad).
`git bisect run` reads 0 as good, 125 as skip and other codes from 1 to 127 as
bad. The benchmark command is the project's: ask for it; unknown → the draft
says `<benchmark command — not recorded; fill in before running>`. A noisy
benchmark runs several times per step and compares the median — the same way
the confirmation run was judged.

**Suspects.** `git log --oneline <good>..<bad> -- <paths>` over the paths of
the regressed subsystems. Custom: resolve each subsystem's roots through
`.claude/docs/custom-engine-layout.md`, Resolving source roots for workflows —
`engine/<module>/`, `crates/<module>/` and any alias the module map registers;
a crate-only engine has no `engine/` folder, so an `engine/`-only path list
finds nothing. Another engine: the code root's folders for that system. These are **suspects**, listed as such — not
an attribution.

### 4. Attribution, budget slice and SLA

**Attribution needs a first bad commit** — `--first-bad <commit>`, from the
bisect the user ran. None → `Attribution: NOT ASSESSED — bisect not run`; the
suspects stand in the bug as suspects.

`git show --stat --format='%H %an %s' <commit>` gives the changed paths. The
paths decide the owner:

**Custom** (`Routing: Custom engine leads`): resolve each changed path through
the Owner and Lead columns of `.claude/docs/custom-engine-layout.md`; a path
that several rows cover takes the Owner and Lead of its most specific row (the
layout's precedence rule), so `engine/audio/CMakeLists.txt` is the audio
module's, not the build files'. The bug goes to the path's Lead; where the Lead is `chief-engine-architect` (the owner is
itself a lead) or `none`, to the Owner. Paths whose rows name different leads go
to `chief-engine-architect`. A path with no row is
`Attribution: NOT ASSESSED — <path> has no row in custom-engine-layout.md`.

The lead assigns its specialist (allocators → `memory-allocator-specialist`,
scheduling and contention → `concurrency-job-system-engineer`, data layout →
`ecs-dod-architect`, as `performance-analyst` routes them).

**Any other engine** (`Routing: owners on <engine>`), as `performance-analyst`
routes them: rendering (LOD, occlusion, batching, atlasing) →
`technical-artist`; engine systems and hot-path code → `engine-programmer`; any
other system → the programmer who owns it; unclear or several systems →
`lead-programmer`.

**Budget slice.** Custom: Grep `docs/architecture/` for the per-subsystem
budget split — the record `CEA-FRAME-BUDGET` judges against. The attributed
subsystem's slice beside its P95 from the report's `Affected Subsystems` table.
No split → `Budget slice: NOT ASSESSED — no per-subsystem split recorded`; no
row for the subsystem in the report → `NOT ASSESSED — no subsystem timing in
<report>`. Another engine: `Budget slice: N/A — the per-subsystem split is a
Custom-engine record`, and the report's Budget result is quoted instead.

**SLA.** The response time for a confirmed regression is set with `producer`
(`performance-analyst`). Grep `production/` for a recorded regression SLA.
None → `regression SLA NOT SET`; never assume one.

### 5. The bug draft

Use `/bug-report`'s template (`.claude/skills/bug-report/SKILL.md`, Phase 2A),
filled from the reports:

- **Title**: `[metric] regressed [Δ ms] ([Δ %]) in [scene]`
- **Severity / Priority**: `/bug-triage`'s labels. Ask, showing the budget
  result and the deltas; suggest `S2-High` when the current Budget result is
  `OVER BUDGET` and `S3-Medium` when it is not. In `autonomous` mode, use the
  suggestion and log it as the skill's choice.
- **Category**: Performance · **Regression**: Yes · **Frequency**: from the
  confirmation (`Always` when confirmed; `Unknown — unconfirmed` otherwise)
- **System**: the attributed module or system, or `unattributed — suspects
  listed`
- **Environment**: the report's Inputs row, `unknown` cells kept
- **Reproduction Steps**: capture the scene on the stated machine and preset;
  run `/benchmark-report <capture> --baseline <baseline> --threshold <threshold>`
- **Expected / Actual**: each regressed metric within baseline + threshold /
  the measured value
- **Evidence**: both report paths with the delta rows
- **Technical Context**: the first bad commit's files, or the suspects

Then append:

```markdown
## Perf Regression Triage
**Triage owner**: performance-analyst until hand-over
**Verdict**: [CONFIRMED — … | NOT ASSESSED — … | NOT REPRODUCED]
**Regression report**: [path]   **Confirmation**: [path | NOT ASSESSED — reason]
**Baseline**: [path]   **Threshold**: [X %]
**Bisect**: [range, N commits, ~⌈log₂ N⌉ runs; builds available | NOT ASSESSED — reason]
[the printed commands and the bisect script draft]
**Suspects**: [commits, or none]
**First bad commit**: [hash | NOT ASSESSED — bisect not run]
**Owner**: [agent | NOT ASSESSED — not attributed]
**Budget slice**: [subsystem P95 vs slice | NOT ASSESSED — reason | N/A — reason]
**SLA**: [recorded target and source | regression SLA NOT SET]
### Tracking
- [date] opened — [verdict]
```

**Allocate the ID** as `/bug-report` does: Glob `production/qa/bugs/BUG-*.md`,
highest number plus 1, four digits (`BUG-0001` when none). Show the draft, then
ask *"May I write this to `production/qa/bugs/BUG-[NNNN].md`?"*. Write only
after a yes, creating the folder if it is absent.

Close the run with the triage verdict line, the bug path (or `not written — the
user declined`), and the next step from SKILL.md Phase 7, then:
Run status: **COMPLETE** — triage produced. That word says the triage ran; the
verdict line is what it found.

---
