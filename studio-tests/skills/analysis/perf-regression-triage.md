# Skill Test Spec: /perf-regression-triage

## Skill Summary

`/perf-regression-triage` is a triage flow for a
regression that `/benchmark-report` found, with its own triage rules on every
engine (same-machine confirmation; NOT REPRODUCED kept open as unconfirmed;
`regression SLA NOT SET` when none is recorded) — `performance-analyst`'s
Perf-regression triage, which that agent applies only on Custom, cites the same
steps. It is user-invoked only (`disable-model-invocation: true`). It will: confirm it with a re-run against the
same baseline and threshold, plan a bisect (CI builds first, then commits —
`git bisect` printed, never run), attribute it from the first bad commit to an
owner, open a bug in `/bug-report`'s template with a `## Perf Regression Triage`
section, and track it until a new `/benchmark-report` shows NO REGRESSION. It
runs on **any engine** with `/benchmark-report` output — it does not refuse on a
non-Custom engine; only the routing differs (Custom: `core-systems-lead`,
`rendering-lead`, `simulation-systems-lead`, `editor-architect`,
`chief-engine-architect`; other engines: `technical-artist`, `engine-programmer`,
the system's owner, `lead-programmer`), and the run names which. Inputs that are
not a REGRESSION stop the run (`NO REGRESSION — nothing to triage`, or
`NOT ASSESSED — …`). Triage verdict, first match wins: CONFIRMED → NOT ASSESSED →
NOT REPRODUCED. Unset budget split → `NOT ASSESSED`; no recorded SLA →
`regression SLA NOT SET`. It asks "May I write" before writing
`production/qa/bugs/BUG-[NNNN].md` and "May I update" before a tracking entry,
and updates the existing bug for the same regression instead of opening a
second.

---

## Static Assertions (Structural)

- [ ] Has required frontmatter fields: `name`, `description`, `argument-hint`, `user-invocable`, `allowed-tools`; `model: sonnet`; `disable-model-invocation: true`
- [ ] States its triage rules itself (same machine, preset and GPU/driver; NOT REPRODUCED kept open as unconfirmed; `regression SLA NOT SET`), citing `performance-analyst` as their source only on Custom
- [ ] On Custom, suspects resolve each subsystem's roots through `custom-engine-layout.md`, Resolving source roots for workflows (`engine/<module>/`, `crates/<module>/`, aliases)
- [ ] Has ≥2 phase headings (Phases 1–7), with the bisect plan, routing and bug draft in `references/bisect-and-bug.md`
- [ ] Contains verdict keywords: CONFIRMED, NOT ASSESSED, NOT REPRODUCED — and states NOT ASSESSED ranks below CONFIRMED and above NOT REPRODUCED
- [ ] States it runs on any engine with `/benchmark-report` output and does not refuse on a non-Custom engine
- [ ] `allowed-tools` has no Agent and no general Bash; git access is `git rev-parse`, `git rev-list`, `git log`, `git show` only — no `git bisect` or `git checkout`
- [ ] Contains "May I write" naming `production/qa/bugs/BUG-[NNNN].md`
- [ ] Has a next-step handoff (Phase 7: `/team-frame-pipeline`, `/dev-story`, `/bug-report`, `/bug-triage`, `/memory-audit`)

---

## Director Gate Checks

None. The skill triages and hands over; `CEA-FRAME-BUDGET` is run by
`/team-frame-pipeline` on the fix, not here.

---

## Fixture Defaults

Every case's `project.yaml` sets `modes.rigor: minimal` and
`modes.automation: collaborative`, with no `project.local.yaml`, unless its own
Fixture says otherwise. Rules: `studio-tests/CLAUDE.md` §
Fixture defaults. Every case sets `engine.name: Custom` and
`performance.frame_budget_ms: 8.33` unless it says otherwise.

---

## Test Cases

### Case 1: Happy Path — confirmed, attributed, bug opened

**Fixture:**
- `production/qa/benchmarks/benchmark-2026-11-10.md`: `Regression result: REGRESSION`; GPU frame P95 7.2 → 8.0 ms (+11 %), threshold 5 %, baseline `benchmark-2026-11-01.md`; affected subsystem `lighting`
- `benchmark-2026-11-11.md`: same baseline, threshold and Inputs, a different capture, `REGRESSION` on GPU frame P95
- First bad commit `9c1e…` touches `engine/renderer/src/lighting/`
- `docs/architecture/frame-budget.md` gives `lighting` a 2.5 ms GPU slice; no regression SLA recorded in `production/`
- No bug in `production/qa/bugs/` cites the report; highest existing is `BUG-0006`

**Input:** `/perf-regression-triage production/qa/benchmarks/benchmark-2026-11-10.md --confirm production/qa/benchmarks/benchmark-2026-11-11.md --good 41ab… --bad 9f3d… --first-bad 9c1e…`

**Expected behavior:**
1. `Routing: Custom engine leads` printed
2. Confirmation holds → CONFIRMED
3. Bisect plan: `git rev-list --count` N and ~⌈log₂ N⌉ runs; commands printed
4. `git show --stat` → `rendering-lead`
5. Budget slice: `lighting` P95 vs 2.5 ms; `regression SLA NOT SET`
6. Bug drafted in `/bug-report`'s template, Category Performance, Regression Yes, plus the triage section; Severity asked with `S2-High`/`S3-Medium` suggestion
7. Asks "May I write this to `production/qa/bugs/BUG-0007.md`?"
8. Verdict `CONFIRMED — attributed to rendering-lead (9c1e…) — regression SLA NOT SET`

**Assertions:**
- [ ] Every number cites a report path
- [ ] No `git bisect` run
- [ ] ID allocated as highest + 1, four digits

---

### Case 2: Non-Custom Engine — runs, routes to owners

**Fixture:**
- `engine.name: Unity`; a REGRESSION report and a confirming report as in Case 1
- First bad commit changes `Assets/Scripts/Rendering/Occlusion.cs`

**Input:** `/perf-regression-triage <report> --confirm <report2> --first-bad <hash>`

**Expected behavior:** does not refuse; prints `Routing: owners on Unity`; owner `technical-artist` (occlusion); `Budget slice: N/A — the per-subsystem split is a Custom-engine record`, report's Budget result quoted.

**Assertions:**
- [ ] The skill runs on a non-Custom engine
- [ ] No Custom engine agent named as owner

---

### Case 3: Single Run — confirmation NOT ASSESSED, bug still opened

**Fixture:** a REGRESSION report; no `--confirm`; `modes.automation: autonomous`

**Input:** `/perf-regression-triage <report>`

**Expected behavior:** prints the re-run to make (`/benchmark-report <new capture> --baseline <same> --threshold <same>`); no question (autonomous); `Confirmation: NOT ASSESSED — no re-run`; bisect ends unknown → `NOT ASSESSED`; bug Frequency `Unknown — unconfirmed`; verdict NOT ASSESSED.

**Assertions:**
- [ ] One run is never reported CONFIRMED
- [ ] Verdict NOT ASSESSED, naming confirmation, bisect and attribution gaps
- [ ] Severity suggestion used and logged as the skill's choice in autonomous mode

---

### Case 4: Not a Regression — stops

**Fixture:**
- Variant A: report reads `Regression result: NO REGRESSION`
- Variant B: report reads `Regression result: NOT ASSESSED — no baseline`
- Variant C: a hand-written notes file with no `Regression result:` line

**Input:** `/perf-regression-triage <path>`

**Expected behavior:** A → `NO REGRESSION — nothing to triage`; B → `NOT ASSESSED — the report did not establish a regression (no baseline)`; C → `NOT ASSESSED — <path> is not /benchmark-report output` with the `/benchmark-report … --baseline … --threshold …` command. No bug drafted in any.

**Assertions:**
- [ ] No bug file or write prompt
- [ ] B is not treated as a regression

---

### Case 5: Re-run Not Reproduced — kept open as unconfirmed

**Fixture:** a REGRESSION report and a confirming report with the same baseline and threshold that reads `NO REGRESSION`

**Input:** `/perf-regression-triage <report> --confirm <report2>`

**Expected behavior:** verdict NOT REPRODUCED; bug still drafted with Frequency `Unknown — unconfirmed`; next step one more re-run or `/bug-triage`.

**Assertions:**
- [ ] The bug is not discarded
- [ ] Variant: the confirming report used a different threshold → `Confirmation: NOT ASSESSED — threshold differs`, verdict NOT ASSESSED (not NOT REPRODUCED)

---

### Case 6: Track Mode — measured fixed, not closed

**Fixture:** `BUG-0007` from Case 1; a new report with the bug's baseline and threshold, `NO REGRESSION`

**Input:** `/perf-regression-triage track BUG-0007 production/qa/benchmarks/benchmark-2026-11-14.md`

**Expected behavior:** `measured fixed in <report>`; asks "May I update `production/qa/bugs/BUG-0007.md` with this tracking entry?"; Status not changed; next step `/bug-report verify BUG-0007`.

**Assertions:**
- [ ] The bug is not closed or set to Verified by this skill
- [ ] Variant: the new report uses another baseline → `Fix measurement: NOT ASSESSED — <difference>`

---

### Case 7: Second Run Attributes the Same Regression

**Fixture:** `BUG-0007` exists with `First bad commit: NOT ASSESSED — bisect not run`, citing `benchmark-2026-11-10.md`

**Input:** `/perf-regression-triage production/qa/benchmarks/benchmark-2026-11-10.md --first-bad 9c1e…`

**Expected behavior:** finds `BUG-0007` by the cited report; asks "May I update `production/qa/bugs/BUG-0007.md` with this triage?"; adds a Tracking entry; no new `BUG-0008`.

**Assertions:**
- [ ] One regression, one bug

---

### Case 8: Same-day confirmation report does not overwrite the first

**Fixture:** `production/qa/benchmarks/benchmark-2026-11-17-0930-city.md` reads
`Regression result: REGRESSION`; the user makes the confirmation capture the same
day and runs `/benchmark-report captures/city-rerun.csv --baseline <same> --threshold <same>` at 11:15.

**Input:** `/perf-regression-triage production/qa/benchmarks/benchmark-2026-11-17-0930-city.md --confirm production/qa/benchmarks/benchmark-2026-11-17-1115-city.md`

**Expected behavior:** both reports exist side by side (the second was written
under its own time, never over the first); Phase 2 reads them as two different
captures and CONFIRMS on a regressed metric.

**Assertions:**
- [ ] The regression report the bug cites is still on disk after the re-run
- [ ] Confirmation is CONFIRMED, not `NOT ASSESSED — same capture`

---

### Case 9: Crate-only engine — suspects come from `crates/`

**Fixture:** `engine.name: Custom`; no `engine/` folder; the module map maps
`renderer` to `crates/renderer/`; a confirmed GPU regression in `lighting`.

**Input:** `/perf-regression-triage <report> --confirm <report2> --good v0.7.0 --bad HEAD`

**Expected behavior:** suspects are `git log --oneline v0.7.0..HEAD -- crates/renderer/`
(resolved through the layout's Resolving source roots), never an empty list from
`engine/renderer/`.

**Assertions:**
- [ ] Suspects list the commits under `crates/renderer/`

---

## Protocol Compliance

- [ ] Records each input FOUND or ABSENT
- [ ] Names the routing (Custom leads or owners on <engine>) once
- [ ] Suspects are never presented as the attribution
- [ ] Unset split and SLA named as unset, never filled in
- [ ] Asks "May I write" / "May I update" before any write; on no, nothing is written
- [ ] Never runs `git bisect`, `git checkout` or any command that changes the working tree
- [ ] Ends with the Phase 7 next step for the verdict

---

## Coverage Notes

- Bisecting over CI build artifacts (no build per step) has no dedicated case.
- A first bad commit spanning several engine modules (→ `chief-engine-architect`) is not covered.
- The bisect script's `exit 125` skip on a failed build is asserted only by reading the draft.
