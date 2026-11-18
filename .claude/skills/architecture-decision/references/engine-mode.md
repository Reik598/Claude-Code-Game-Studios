# /architecture-decision — Engine Mode (engine-internal ADRs)

> Part of `/architecture-decision`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Engine mode

**When it is on.** Engine mode has two forms, and the run says which, once,
before Step 1:

- **Full engine mode** — the resolved `engine:` line reads `Custom` (with or
  without `--engine-internal`): `Engine mode: on (engine.name: Custom)`.
  Everything under "What changes" applies.
- **Engine sections only** — the user passed `--engine-internal` and the
  engine is not Custom (a native plugin, a GDExtension, a Unity native plugin,
  an Unreal C++ module): `Engine mode: sections only (--engine-internal on
  <engine>) — vendor reference, <engine> specialist, no CEA-ADR`. Only changes
  2 and 3 below apply: the ADR gets the six sections and Step 4 asks the two
  extra assumptions, because the decision still has memory, threading and
  frame costs. Step 1 keeps the vendor reference
  (`docs/engine-reference/<engine>/`), Step 5.5 keeps the vendor specialist
  (`godot-specialist`, `unity-specialist`, `unreal-specialist`, or
  `lead-programmer` on Web), and Step 5.6 does **not** run CEA-ADR — the run
  prints `CEA-ADR not run — engine.name is <engine>, not Custom`. The Custom
  engine agents and `docs/engine-reference/custom/` describe an engine this
  project does not build, so routing to them would review the ADR against the
  wrong facts. The ADR says it is engine-internal on `<engine>` in its Summary.

Off (engine not Custom and no flag): say nothing more and follow the normal
steps. `--engine-internal` with no engine configured is engine sections only
with Step 5.5's "no engine configured" rule.

**What changes** (full engine mode — all six; engine sections only — 2 and 3):

1. **Step 1** reads `docs/engine-reference/custom/` (the project's own pinned
   toolchain and dependency facts), not an engine vendor's reference. The
   decision's modules are the rows of `.claude/docs/custom-engine-layout.md`
   whose paths hold the code it governs — the layout is the one module list;
   keep no copy of it here. A module with no row there has no owner yet: say
   so and ask the user before going on.
2. **Step 4** adds two assumptions to the confirm/adjust prompt: the frame
   budget (the `perf_budgets` line) and which threads or queues the decision
   runs on.
3. **Step 5** adds the six required sections below to the ADR, after
   `## Performance Implications`.
4. **Step 5.5** spawns the engine lead resolved through
   `.claude/docs/custom-engine-layout.md` instead of an engine vendor
   specialist: the Lead of the most specific row that covers the decision's
   module (the layout's precedence rule), or that row's Owner where the Lead is
   `chief-engine-architect` or `none`. A decision that spans modules goes to
   `chief-engine-architect`, which owns the boundaries between them.
5. **Step 5.6** runs the **CEA-ADR** gate beside TD-ADR (5-generate.md).
6. **The module spec stands in for the GDD.** When
   `docs/architecture/modules/<module>.md` exists for a module the decision
   governs, Step 3 reads its section 10 ("Test Plan and Acceptance Criteria")
   with `bash .claude/scripts/md-section.sh extract` and the module's entries in
   `docs/architecture/tr-registry.yaml` (`TR-<module>-NNN`, the entries
   whose `gdd:` is `docs/architecture/modules/<module>.md`; a game GDD with
   the same slug shares `system:` and the sequence). The ADR's `## GDD Requirements Addressed` table
   names the module spec in its first column and each `TR-<module>-NNN` the
   decision covers in the Requirement column (`/architecture-review` traces a
   module criterion only through that table). With no registered entry, quote
   the criterion and say it is not registered yet. Step 5.7's sync check reads
   the module spec as it would a GDD. No module spec yet: write the table's
   foundational line and name the module the spec is missing for.

### The six required sections

Each is required. A section that does not apply is written as
`N/A — <why>`, never left out: a missing section and a section that does not
apply look the same to the next reader. A value the decision cannot yet know is
written as `UNKNOWN — <what would establish it>`, and listed under
Validation Criteria.

```markdown
## Memory
- **Allocation strategy**: [arena / pool / slab / TLSF / general heap / none — per allocation site]
- **Ownership**: [who creates, who owns, who frees; handle or pointer; lifetime bound to frame / level / process]
- **Footprint**: [steady-state MB and peak MB, and what drives the peak]
- **Hot-path allocations**: [none, or each one and why it is allowed]

## Threading
- **Threads and jobs that touch it**: [main / render / worker jobs / IO / GPU queues — read or write each]
- **Synchronisation**: [primitives used — atomics, locks, job dependencies, fences, barriers]
- **Contention**: [where two threads meet, and the expected wait]

## Latency & Frame Budget
| Work | Thread / queue | ms per frame | Share of budget |
|------|----------------|--------------|-----------------|
| [stage] | [thread or queue] | [ms] | [% of performance.frame_budget_ms] |
Frame budget: [X ms — performance.frame_budget_ms | NOT ASSESSED — performance.frame_budget_ms unset]
Latency added (input to photon, or simulation to present): [frames or ms, or none]

## ABI / API Stability
- **Public headers / traits affected**: [paths under engine/**/include (nested modules included) or the crate's pub items]
- **Break or compatible**: [source break / binary break / compatible]
- **Versioning**: [version bump, deprecation window, migration path for game/ code]

## Determinism
- **Must it be deterministic?**: [yes — replay / lockstep / tests; no — why]
- **What could break it**: [float order, thread scheduling, hash iteration order, platform math]
- **How it is kept**: [fixed step, ordered reduction, fixed-seed RNG, bit-exact math paths]

## Platform / Graphics-API Matrix
| Platform | Graphics API | Supported | Differences / fallbacks |
|----------|--------------|-----------|-------------------------|
| [Windows / Linux / macOS / console] | [Vulkan 1.4 / Direct3D 12 / Metal] | [yes / no / partial] | [feature fallback, e.g. no mesh shaders] |
```

**The budget row is wired, not decorative.** When `performance.frame_budget_ms`
is unset, the Latency section's budget line is `NOT ASSESSED`, and the Step 5.7
summary repeats it: `Frame budget: NOT ASSESSED — performance.frame_budget_ms
unset`. A share of a budget nobody set is not written as a percentage.

**Unsourced facts.** A driver, API or toolchain limit that the reference Step 1
read does not record — `docs/engine-reference/custom/` in full engine mode, the
vendor's `docs/engine-reference/<engine>/` in engine sections only — is written
`NOT SOURCEABLE — <what> is not covered by <that path>` and
added to Validation Criteria as something to measure. Never fill it from memory.

### Retrofit

In retrofit mode on an engine-internal ADR (engine mode on), each of the six
sections that is missing is **HIGH** — a reader cannot tell what the decision
costs on the frame or which threads it touches — and is added the same way as
the other missing sections, with the user's answers.

---
