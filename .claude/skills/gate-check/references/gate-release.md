> Gate definition, loaded by `/gate-check` for the target stage only.
> Never load the other five — one gate applies per invocation.


# Gate: Polish → Release


**Required Artifacts:**
- [ ] All features from milestone plan are implemented
- [ ] Content is complete (all levels, assets, dialogue referenced in design documents exist)
- [ ] Localization strings are externalized (no hardcoded player-facing text in the code root)
- [ ] QA test plan exists (`/qa-plan` output in `production/qa/`)
- [ ] QA sign-off report exists (`/team-qa` output — APPROVED or APPROVED WITH CONDITIONS)
- [ ] All Must Have story test evidence is present (Logic/Integration: test files pass; UI: retained screenshots of each screen touched; Visual/Feel: retained screenshots plus lead sign-off — both in `production/qa/evidence/`, and no `qa.level` waives either)
- [ ] Smoke check passes cleanly (PASS verdict) on the release candidate build — a full run, not a `quick` one labelled `(quick — …)`
- [ ] No test regressions from previous sprint (test suite passes fully)
- [ ] Balance data has been reviewed (`/balance-check` run)
- [ ] Release checklist completed (`/release-checklist` run)
- [ ] Store metadata prepared (if applicable)
- [ ] Changelog / patch notes drafted

**Quality Checks:**
- [ ] Full QA pass signed off by `qa-lead`
- [ ] All tests passing
- [ ] Performance targets met across all target platforms
- [ ] No known open S1 Critical, S2 High or S3 Medium bugs
- [ ] No open CRITICAL or HIGH findings in the newest `production/security/security-audit-*.md` whose **Scope** is `full`, as updated by any later `quick` report (the re-run `/security-audit` prescribes after remediation). A later `network`, `save` or `input` report adds its open findings but never clears a category it did not scan — any open CRITICAL or HIGH finding means not ready (a blocker). No `full`-scope audit report means the check could not run: this item is NOT ASSESSED, never passed. A report whose release recommendation is itself NOT ASSESSED makes this item NOT ASSESSED too
- [ ] Accessibility basics covered (remapping, text scaling if applicable)
- [ ] Localization verified for all target languages — every translated locale being shipped has a `/localize qa` verdict of PASS or PASS WITH CONDITIONS (`production/localization/loc-qa-[locale]-[date].md`). A FAIL blocks that locale; the others may still ship. A locale with no QA report, or whose QA reported NOT ASSESSED (nobody has played it), has not been verified: this item is NOT ASSESSED, never passed. The source locale (`en`, per `/localize`) is not a target language and needs no `/localize qa` report; a game that ships only its source locale marks this item N/A and says so
- [ ] Legal requirements met (EULA, privacy policy, age ratings if applicable)
- [ ] Build compiles and packages cleanly

## Workflow tier reductions

The checklist above is the **`full` baseline**. At lower tiers apply the
reduction for the resolved tier; items not named keep their status above.
Reductions only ever *relax* a requirement — `workflow_overrides` is the
only thing that adds one.

- **`full`** — all features + content complete + localization + QA sign-off + smoke (PASS) + no open S1–S3 bugs all required
- **`standard`** — content-complete audit + QA sign-off + localization → recommended; **all features + smoke + no open S1 Critical bugs** required; open S2 High and S3 Medium bugs → recommended
- **`minimal`** — only **smoke + no open S1 Critical bugs** required; everything else **drops**

## Custom engine additions

**Applies only when the resolved `engine` line reads `Custom`** (any case). On
any other engine, or with no engine set, skip this block and print one line in
the report's checklist: `Custom engine additions: skipped — engine is <name |
unset>`. On Custom these items are added to the checklist above. Reviewer for
this block: `chief-engine-architect`, through gate **CEA-FRAME-BUDGET** on the
release candidate's captures per target platform (Section 4b) — this is how
"Performance targets met across all target platforms" is checked for the
engine. The platform and documentation items are produced with
`platform-engineer` and `engine-technical-writer`; this gate reads their
output and spawns neither.

**Required Artifacts (Custom):**
- [ ] **`/memory-audit` on the release candidate is CLEAN, or its risks are
      accepted.** The newest `production/qa/memory/memory-audit-*.md`, run
      against the release-candidate build:
      - `DEFECTS FOUND` → **Blocker**
      - `RISKS FOUND` → CONCERNS, one per risk; the stage advances only if the
        user accepts each one, recorded under `### Accepted Risks` (Section 6)
      - `NOT ASSESSED` → this item is NOT ASSESSED; no acceptance overrides it
      - `CLEAN` → passes; each section its verdict line names as NOT ASSESSED
        (e.g. data races, no TSan output) is a CONCERNS line of its own
      - A report older than the release candidate's newest change under
        `engine/` describes another build → NOT ASSESSED: "audit predates the
        release candidate"
- [ ] **Graphics validation layers clean.** For each graphics API marked
      supported in the ADRs' `## Platform / Graphics-API Matrix`, a run of the
      release candidate with that API's validation enabled (Vulkan validation
      layers, the Direct3D 12 debug layer with GPU-based validation, Metal API
      validation), its log retained in `production/qa/evidence/`. Any validation
      error → **Blocker**; warnings → CONCERNS; an API with no run → NOT
      ASSESSED for that API, named.
- [ ] **Platform technical requirements checked** (with `platform-engineer`).
      A checklist per target platform in `production/releases/`, each row
      citing its source. A requirement the project cannot source — a console
      holder's requirements are not in `docs/engine-reference/custom/` and are
      never filled from memory — reads `NOT SOURCEABLE — <requirement> is not
      covered by docs/engine-reference/custom/`, and that platform's item is NOT
      ASSESSED, never PASS. A failed row → **Blocker**.
- [ ] **Engine API docs and migration guides** (with `engine-technical-writer`).
      The API reference for the public headers or traits exists under
      `docs/engine/api/` (or the layout the project already uses). Derive the
      ABI/API breaks from the Accepted ADRs whose `## ABI / API Stability`
      section records a source or binary break since the last release; each
      needs a migration guide under `docs/engine/migration/`. A break with no
      guide is a **Blocker**; a doc that describes behaviour nobody verified in
      code is CONCERNS.
- [ ] **Symbols uploaded and crash reporting works.** Debug symbols (PDB,
      DWARF, dSYM) for the release-candidate build are stored on the symbol
      server or crash service with its build ID, and a deliberate test crash of
      that build produced a symbolicated report. No such test crash on record →
      MANUAL CHECK NEEDED until the person answers; "not yet" is a Blocker.

**Tier reductions (Custom).** Reductions only relax:
- **`full`** — every item above required
- **`standard`** — `/memory-audit`, validation layers, symbols and crash
  reporting required; platform requirements and engine docs → recommended
- **`minimal`** — `/memory-audit` (not `DEFECTS FOUND`) and symbols plus crash
  reporting required; everything else → recommended

A report that exists still counts at every tier: validation errors or a
`DEFECTS FOUND` audit are Blockers wherever the item is only recommended.
