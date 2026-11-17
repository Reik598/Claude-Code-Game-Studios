# Skill Test Spec: /architecture-decision

## Skill Summary

`/architecture-decision` authors one Architecture Decision Record (ADR). It has
three entry modes: normal authoring (`/architecture-decision [title]`),
`retrofit <path>` (adds missing sections to an existing ADR without touching the
rest), and `accept <ADR-id>` (the only path that moves an ADR from `Proposed` to
`Accepted`). When retrofit asks for a missing Status and the user answers
`Accepted`, it writes `Proposed` and hands the ADR to acceptance mode.

Normal authoring loads engine context first (`docs/engine-reference/[engine]/VERSION.md`,
plus a knowledge-gap warning for MEDIUM/HIGH-risk domains), picks the next ADR
number, checks `docs/registry/architecture.yaml` for binding stances, then
presents its assumptions as a confirm/adjust `AskUserQuestion` (Status is always
`Proposed` and is never asked). It then drafts the whole ADR from its template in
one pass, has the primary engine specialist validate it (Step 5.5), runs the
TD-ADR gate in `full` review mode only (Step 5.6), runs a GDD sync check that
always reports, and asks once — "May I write it?" — before writing
`docs/architecture/adr-[NNNN]-[slug].md`. A separate approval covers the registry
update. The closing output tells the user to run `/architecture-review` in a
fresh session and `/architecture-decision accept ADR-NNNN` when the decision is
settled. Authoring never sets `Accepted` and never unblocks stories.

---

## Static Assertions (Structural)

Checked against the SKILL.md by `/skill-test spec` — no fixture needed.

- [ ] Has required frontmatter fields: `name`, `description`, `argument-hint`, `user-invocable`, `allowed-tools`
- [ ] Has ≥2 phase headings
- [ ] Contains status/verdict keywords: `Proposed`, `Accepted`, and the TD-ADR outcomes `CONCERNS` / `REJECT`
- [ ] Contains "May I write" collaborative protocol language (whole-ADR write approval and registry approval)
- [ ] Has a next-step handoff at the end (`/architecture-review`, `accept ADR-NNNN`)
- [ ] Documents gate behavior: engine specialist validation, then TD-ADR in full mode; TD-ADR skipped in lean/solo with a named note
- [ ] Documents that authoring always produces `Proposed` and only acceptance mode sets `Accepted` — retrofit's `Accepted` answer is routed through it
- [ ] Mentions the engine version stamp from `docs/engine-reference/` (Engine Compatibility table)

---

## Director Gate Checks

Review mode comes from the resolved `review_mode` (`modes.review_mode` in
`project.yaml`); `--review full|lean|solo` overrides it for one run.

In `full` mode: after the draft is generated, the primary engine specialist
validates it (Step 5.5), then `technical-director` spawns with gate TD-ADR
(Step 5.6). The two run in that order, not in parallel. On CONCERNS the
concerns are shown verbatim and the user picks `Revise flagged items` /
`Accept and proceed` / `Discuss further`; on REJECT the draft is revised before
the write approval. No verdict changes the ADR's Status.

In `lean` mode: TD-ADR is skipped (it is not a PHASE-GATE). Output notes
"TD-ADR skipped — Lean mode." The engine specialist validation still runs.

In `solo` mode: TD-ADR is skipped. Output notes "TD-ADR skipped — Solo mode."
The engine specialist validation still runs.

In every mode the written ADR has `Status: Proposed`.

---

## Fixture Defaults

Every case's `project.yaml` sets `modes.rigor: minimal` and
`modes.automation: collaborative`, with no `project.local.yaml`, unless its own
Fixture says otherwise. Rules: `studio-tests/CLAUDE.md` §
Fixture defaults.

---

## Test Cases

### Case 1: Happy Path — New rendering ADR, full mode, TD-ADR approves

**Fixture:**
- `project.yaml` has `engine.name: Godot` and `modes.review_mode: full`
- `docs/engine-reference/godot/VERSION.md` exists and marks the pinned version HIGH risk; `breaking-changes.md` lists a Rendering change
- `docs/architecture/` contains `adr-0001-*.md` and `adr-0002-*.md`; none covers rendering
- `docs/registry/architecture.yaml` exists with no stance touching rendering
- `design/gdd/visual-effects.md` exists; the user confirms it as the GDD driving the decision, and its names match the ADR's Key Interfaces
- The engine specialist finds only minor notes; TD-ADR returns APPROVE

**Input:** `/architecture-decision rendering-approach`

**Expected behavior:**
1. Step 1 reads `VERSION.md` first and displays the ENGINE KNOWLEDGE GAP WARNING for the Rendering domain
2. Step 2 scans `docs/architecture/` and assigns ADR-0003
3. Step 3a reads the registry before any existing ADR
4. Step 4 presents assumptions (problem, 2–3 alternatives, GDD linkage, dependencies, `Status: Proposed`) as a confirm/adjust `AskUserQuestion`; no ADR is generated until the user confirms
5. Step 5 drafts the full template, including the Engine Compatibility table (engine, domain, knowledge risk, references consulted)
6. `godot-specialist` validates the draft; minor notes go into the Risks section
7. `technical-director` then spawns with gate TD-ADR and returns APPROVE
8. GDD sync check prints `GDD sync: checked 1 referenced GDD(s), no naming inconsistencies.` — never silent
9. "ADR draft is complete. May I write it?" — on yes, writes `docs/architecture/adr-0003-rendering-approach.md` with `Status: Proposed`
10. Registry candidates are shown and "May I update `docs/registry/architecture.yaml` with these [N] new stances?" is asked separately
11. Closing output includes the fixed notice to run `/architecture-review` in a fresh session, and "Run `/architecture-decision accept ADR-0003` when the decision is settled"

**Assertions:**
- [ ] `VERSION.md` is read before any other step, and the knowledge-gap warning is shown for the HIGH-risk domain
- [ ] Assumptions are confirmed via `AskUserQuestion` before the ADR is generated; Status is shown as `Proposed`, never asked
- [ ] The engine specialist validation runs before TD-ADR (sequential, not parallel)
- [ ] One "May I write" approval covers the whole ADR; the file is `docs/architecture/adr-0003-rendering-approach.md`
- [ ] The written ADR has `Status: Proposed` even though TD-ADR returned APPROVE
- [ ] The GDD sync check reports the clean result for `visual-effects.md` in one line
- [ ] The registry update has its own approval prompt, separate from the ADR write
- [ ] Closing output contains the fresh-session `/architecture-review` notice and the `accept ADR-0003` command

---

### Case 2: Failure Path — TD-ADR returns CONCERNS

**Fixture:**
- Same as Case 1, but TD-ADR returns CONCERNS: "Alternatives do not address the mobile renderer"
- One point stays unresolved after revision (which renderer to target on mobile)

**Input:** `/architecture-decision rendering-approach`

**Expected behavior:**
1. TD-ADR spawns with the draft, engine version, domain and related ADRs
2. The CONCERNS are shown to the user verbatim with the standard options from `director-gates.md`: `Revise flagged items` / `Accept and proceed` / `Discuss further`
3. The user picks `Revise flagged items`; only then are the Decision or Alternatives sections revised (Step 5.6)
4. The unresolved point is presented as its own `AskUserQuestion` with options from the review plus "Different approach — I'll describe it"
5. The write approval is still asked; nothing is written before it
6. The ADR is written with `Status: Proposed`

**Assertions:**
- [ ] TD-ADR receives the ADR draft/path, engine version and domain as context
- [ ] The CONCERNS are shown verbatim and the user chooses Revise / Accept / Discuss — the draft is not revised before that choice
- [ ] Each unresolved decision is a separate `AskUserQuestion` with a free-text escape option
- [ ] The ADR is written only after the "May I write" approval, with `Status: Proposed`

---

### Case 3: Lean and Solo Modes — TD-ADR skipped; checks that cannot run say so

**Fixture:**
- Scenario (a): `project.yaml` has `modes.review_mode: lean` and `engine.name: Godot`
- Scenario (b): same project, invoked with `--review solo`
- Scenario (c): invoked with `--review solo` on a project with no engine configured — `engine.name` unset and `.claude/docs/technical-preferences.md` still `[TO BE CONFIGURED]`; at Step 1's prompt the user carries on without running `/setup-engine`
- `design/gdd/` holds no GDD, so the ADR's GDD Requirements Addressed names none

**Input:** (a) `/architecture-decision save-format` (b) and (c) `/architecture-decision save-format --review solo`

**Expected behavior:**
1. (a) and (b): the engine specialist validation (Step 5.5) runs
2. (a) Output notes "TD-ADR skipped — Lean mode." and proceeds to the GDD sync check
3. (b) and (c): Output notes "TD-ADR skipped — Solo mode." and proceeds to the GDD sync check
4. (c) No engine specialist is spawned, and the output records `Engine validation: NOT ASSESSED — no engine configured (engine.name unset in project.yaml)`
5. The GDD sync check prints `GDD sync: NOT ASSESSED — [the ADR names no GDDs]`, not the clean one-line result
6. "May I write it?" is still asked before the file is written
7. The ADR is written with `Status: Proposed`

**Assertions:**
- [ ] `technical-director` is not spawned in lean or solo mode
- [ ] The skip note names the gate and the mode ("TD-ADR skipped — Lean mode." / "— Solo mode.")
- [ ] The `--review solo` argument overrides the resolved `review_mode` for the run
- [ ] (a) and (b): the engine specialist validation still runs
- [ ] (c) With no engine configured, the output says engine validation was NOT ASSESSED instead of passing silently
- [ ] With no GDD named, the GDD sync check reports NOT ASSESSED, not a clean result
- [ ] "May I write" is asked before the file is written, and Status is `Proposed`

---

### Case 4: Edge Case — Proposed decision contradicts a registered stance

**Fixture:**
- `docs/registry/architecture.yaml` records an interface contract: `damage_delivery → signal pattern (ADR-0003)`
- ADR-0003 is Accepted
- The user states the proposal when invoking the skill, before Step 1: the decision is to deliver damage by direct method calls

**Input:** `/architecture-decision damage-pipeline`, with that description in the same message

**Expected behavior:**
1. Step 3a reads the registry before opening any existing ADR, and presents the relevant stances as locked constraints under "Existing Architectural Stances (must not contradict)"
2. Still in Step 3a — right after the stances, before Step 4's assumptions prompt — the skill surfaces the conflict: "⚠️ Conflict: This ADR proposes [X], but ADR-0003 established that [Y]…"
3. It offers three options: (1) align with the existing stance, (2) supersede ADR-0003 with an explicit replacement, (3) explain why this case is an exception
4. It does not proceed to Step 4 until the conflict is resolved or accepted as an intentional exception
5. If the user chooses to supersede: at the registry step the old entry is set to `status: "superseded_by: ADR-[NNNN]"` (quoted) and the new entry is added — the existing entry is not otherwise modified

**Assertions:**
- [ ] The registry is read before any existing ADR file
- [ ] The conflict warning names ADR-0003 and offers exactly the three options above
- [ ] The confirm/adjust assumptions prompt (Step 4) does not appear until the conflict is resolved
- [ ] On supersede, the old registry entry is marked `superseded_by`, not edited or deleted

---

### Case 5: Acceptance Mode — Status moves to Accepted only through `accept`

**Fixture:**
- `docs/architecture/adr-0005-physics-layers.md` exists with `Status: Proposed`
- Scenario (a): its `## ADR Dependencies` lists `Depends On: ADR-0002`, and ADR-0002 is `Proposed`
- Scenario (b): its only dependency is ADR-0001, which is `Accepted`; three files under `production/epics/*/story-*.md` name `ADR-0005` and are Blocked — two in the header form `/create-stories` writes (`> **Status**: Blocked`), one as `**Status:** Blocked`
- `modes.automation` is `autonomous`

**Input:** `/architecture-decision accept ADR-0005`

**Expected behavior:**
1. The skill globs `docs/architecture/adr-0005-*.md` and reads the single match
2. (a) It refuses and names the blocker: ADR-0005 depends on ADR-0002, which is still Proposed; no file is edited
3. (b) It finds the stories to unblock before asking, then asks "Accept ADR-0005 — [title]? …" with the count ("3 stories become Ready"), options `[A] Yes — accept it` / `[B] Not yet — leave it Proposed`
4. (b) The prompt fires even though automation is `autonomous`
5. (b) On yes: edits `## Status` to `Accepted`, leaves an existing `## Date` unchanged (adding one only if absent), moves the three stories from `Blocked` to `Ready`, and reports the ADR and each story that moved

**Assertions:**
- [ ] (a) Acceptance is refused when a dependency is not `Accepted`, naming ADR-0002; nothing is written
- [ ] (b) The confirmation prompt states how many stories will become Ready
- [ ] (b) The confirmation prompt appears in `autonomous` automation mode
- [ ] (b) Status becomes `Accepted` and the three stories move to `Ready` only after the user confirms
- [ ] Stories are matched only under `production/epics/`
- [ ] (b) All three stories are found — the Blocked grep matches `> **Status**: Blocked` and `**Status:** Blocked`, not only the literal `Status: Blocked`

---

### Case 5b: Acceptance Mode — a story that names the ADR only as a successor is left out

**Fixture:**
- `docs/architecture/adr-0005-physics-layers.md` exists with `Status: Proposed`
  and a `## ADR Dependencies` section whose only dependency, ADR-0001, is `Accepted`
- Three stories under `production/epics/` are `> **Status**: Blocked`:
  - `story-001.md`: blocked because ADR-0005 is Proposed
  - `story-002.md`: blocked with "BLOCKED: ADR-0003 is Superseded — point the
    story at ADR-0005 (edit its ADR field …) before implementing"; ADR-0005 is
    named only as the successor of ADR-0003
  - `story-003.md`: blocked for an unrelated reason that names no ADR-0005
- The user answers `[A] Yes — accept it`

**Input:** `/architecture-decision accept ADR-0005`

**Expected behavior:**
1. The dependency check passes
2. The Blocked-story grep returns all three files; only `story-001.md` names
   ADR-0005 as the reason it is blocked. `story-002.md` is left out because it
   names ADR-0005 only as the successor to point at: it is still governed by
   ADR-0003, and accepting ADR-0005 does not re-point it
3. The confirmation prompt says "1 story becomes Ready", not 2 or 3
4. On yes: `## Status` becomes `Accepted`; only `story-001.md` moves from
   `Blocked` to `Ready`; the report lists the ADR and that one story

**Assertions:**
- [ ] The stories-to-unblock count in the prompt is 1
- [ ] `story-002.md` stays `Blocked`, unedited, and is not in the report of what moved
- [ ] `story-003.md` stays `Blocked`, unedited
- [ ] `story-001.md` becomes `Ready` only after the user confirms

---

### Case 6: Retrofit — Missing Status answered `Accepted`

**Fixture:**
- `docs/architecture/adr-0004-input-mapping.md` exists with Context, Decision, Consequences, Engine Compatibility and GDD Requirements Addressed, but no `## Status` and no `## ADR Dependencies`
- ADR-0001 is `Accepted`
- One file under `production/epics/*/story-*.md` names `ADR-0004` and has `> **Status**: Blocked`

**Input:** `/architecture-decision retrofit docs/architecture/adr-0004-input-mapping.md`

**Expected behavior:**
1. The retrofit block lists Status (BLOCKING), ADR Dependencies (HIGH) and Date (MEDIUM — the fixture has no `## Date` and no `## Last Verified`) as missing, then asks "Shall I add the 3 missing sections? I will not modify any existing content."
2. Asked for the current status, the user answers "Accepted" — the decision is already in force; asked for dependencies, the user answers "Depends On: ADR-0001"
3. The skill appends `## Status` as `Proposed`, the ADR Dependencies section and `## Date` (today, noted as the retrofit date); no existing section changes
4. It then runs acceptance mode on ADR-0004: the dependency check passes (ADR-0001 is Accepted), the blocked story is found, and "Accept ADR-0004 — [title]? …" is asked with "1 story becomes Ready"
5. On yes: `## Status` becomes `Accepted`, the `## Date` the retrofit added is kept, and the story moves from `Blocked` to `Ready`

**Assertions:**
- [ ] Only the missing sections are appended; existing sections are untouched
- [ ] The retrofit answer `Accepted` is never written straight into `## Status`; `Accepted` appears only after acceptance mode's dependency check and confirmation
- [ ] The confirmation prompt names the story count, as in Case 5
- [ ] Variant — the user declines "Shall I add the 3 missing sections?": no section is written, `## Date` included

---

### Case 7: Engine Mode on Custom — six sections, domain lead, CEA-ADR beside TD-ADR

**Fixture:**
- `project.yaml`: `engine.name: Custom`, `modes.review_mode: full`, `performance.frame_budget_ms: 8.33`
- `docs/engine-reference/custom/VERSION.md` exists; it does not record the Vulkan driver limit the decision depends on
- `.claude/docs/director-gates/cea-adr.md` exists
- The user approves every prompt

**Input:** `/architecture-decision Job system: work-stealing with continuations`

**Expected behavior:**
1. Before Step 1: `Engine mode: on (engine.name: Custom)`; `references/engine-mode.md` is read
2. Step 1 reads `docs/engine-reference/custom/`, not a vendor reference; the domain is Jobs
3. Step 4's confirm/adjust prompt includes the frame budget (8.33 ms, from `performance.frame_budget_ms`) and the threads/queues the decision runs on
4. The ADR has `## Memory`, `## Threading`, `## Latency & Frame Budget`, `## ABI / API Stability`, `## Determinism` and `## Platform / Graphics-API Matrix` directly after `## Performance Implications`, in that order — each filled or `N/A — <why>`; an unknown value is `UNKNOWN — …` and listed under Validation Criteria
5. The driver limit is written `NOT SOURCEABLE — … is not covered by docs/engine-reference/custom/` and added to Validation Criteria
6. Step 5.5 spawns `core-systems-lead` (the Jobs domain lead), not a vendor engine specialist
7. Step 5.6 spawns TD-ADR and CEA-ADR together (both `Agent` calls before waiting); the CEA-ADR prompt tells `chief-engine-architect` to read `.claude/docs/director-gates/cea-adr.md` first; the stricter verdict decides
8. Status is `Proposed`; "May I write" once for the ADR

**Assertions:**
- [ ] All six sections present, in order, none silently omitted
- [ ] Step 5.5's helper is `core-systems-lead`
- [ ] Both TD-ADR and CEA-ADR run in full mode, issued in parallel
- [ ] The CEA-ADR call passes every field `cea-adr.md` lists: the draft content (no file is written yet), `engine.name` and the stack, `frame_budget_ms` and `target_framerate`, the `VERSION.md` path, the `memory-invariants.md` path or "none", and related ADRs — so the gate never returns NOT ASSESSED for an input the skill had
- [ ] The written ADR carries `CEA-ADR: <verdict> (<date>)` under `## Status`, the verdict being the one the run ended on
- [ ] The NOT SOURCEABLE line names the path; no driver value from memory
- [ ] Status `Proposed`

---

### Case 8: Engine Mode — budget unset, Solo mode, no VERSION.md

**Fixture:**
- `project.yaml`: `engine.name: Custom`, `modes.review_mode: solo`, no `performance` block
- No `docs/engine-reference/custom/VERSION.md`

**Input:** `/architecture-decision Render graph transient aliasing`

**Expected behavior:**
1. Step 1 says `Engine reference: NOT SOURCEABLE — docs/engine-reference/custom/VERSION.md not found`, writes Knowledge Risk `HIGH — no pinned reference`, and continues — it does not send the user to `/setup-engine`
2. Step 4 states the budget as `NOT ASSESSED — unset`; no 8.33 or 16.6 ms is guessed
3. The Latency & Frame Budget section's budget line is `NOT ASSESSED — performance.frame_budget_ms unset`; no percentage share is written; the Step 5.7 summary repeats `Frame budget: NOT ASSESSED — performance.frame_budget_ms unset`
4. Step 5.5 spawns `rendering-lead` (Renderer domain)
5. Output notes `TD-ADR skipped — Solo mode.` and `CEA-ADR skipped — Solo mode.`

**Assertions:**
- [ ] No guessed budget and no "% of budget" values
- [ ] Both skip notes appear
- [ ] `/setup-engine` is not recommended while `engine.name` is set

**Variant — `--engine-internal` on Godot:** see Case 10.

---

### Case 9: Non-Custom engine without the flag — engine mode stays off

**Fixture:** As Case 1 (Godot, full mode).

**Input:** As Case 1.

**Expected behavior:** No `Engine mode:` line; none of the six engine-mode sections in the ADR; Step 5.5 spawns `godot-specialist`; only TD-ADR runs — CEA-ADR is neither spawned nor mentioned.

**Assertions:**
- [ ] Case 1's assertions all still hold
- [ ] No engine-mode section, no CEA-ADR, no `chief-engine-architect` spawn

---

### Case 10: `--engine-internal` on a non-Custom engine — sections only, vendor review, no CEA-ADR

**Fixture:**
- `project.yaml`: `engine.name: Godot`, `modes.review_mode: full`, `performance.frame_budget_ms: 16.6`
- `docs/engine-reference/godot/VERSION.md` exists; `.claude/docs/director-gates/cea-adr.md` exists

**Input:** `/architecture-decision GDExtension pathfinding memory --engine-internal`

**Expected behavior:**
1. Before Step 1: `Engine mode: sections only (--engine-internal on Godot) — vendor reference, Godot specialist, no CEA-ADR`; the flag is stripped from the title
2. Step 1 reads `docs/engine-reference/godot/` — not `docs/engine-reference/custom/`; the domains are Godot's, not the Custom engine's modules
3. Step 4 asks the two extra assumptions (frame budget 16.6 ms, threads or queues)
4. The ADR carries the six engine-mode sections after `## Performance Implications`; its Summary says it is engine-internal on a Godot project
5. Step 5.5 spawns `godot-specialist` — not `core-systems-lead`, `rendering-lead` or any Custom engine agent
6. Step 5.6 runs TD-ADR only and prints `CEA-ADR not run — engine.name is Godot, not Custom`; `chief-engine-architect` is not spawned
7. An unsourced fact is written `NOT SOURCEABLE — <what> is not covered by docs/engine-reference/godot/`

**Assertions:**
- [ ] No Custom engine agent and no `chief-engine-architect` spawn
- [ ] `docs/engine-reference/custom/` is not read
- [ ] The six sections are present, each filled or `N/A — <why>`
- [ ] The CEA-ADR skip is stated by name with its reason

**Variant — `modes.review_mode: solo`:** the same input on the same Godot fixture.
Output notes `TD-ADR skipped — Solo mode.` and prints `CEA-ADR not run — engine.name is Godot, not Custom`;
it never prints `CEA-ADR skipped — Solo mode.`, which is the full engine mode note (Custom only).
- [ ] The not-run line appears at `solo` too, and no CEA-ADR skip note does

---

### Case 11: Engine Mode on Custom — an Assets ADR goes to the layout's Lead

**Fixture:**
- `project.yaml`: `engine.name: Custom`, `modes.review_mode: lean`, `performance.frame_budget_ms: 16.6`
- `.claude/docs/custom-engine-layout.md` as shipped: `engine/assets/` has Owner `world-streaming-engineer` and Lead `core-systems-lead`

**Input:** `/architecture-decision Runtime asset format and load path`

**Expected behavior:**
1. Step 1 resolves the decision's module through `.claude/docs/custom-engine-layout.md`: `engine/assets/`
2. Step 5.5 spawns `core-systems-lead`, the row's Lead — not `chief-engine-architect`, and no vendor engine specialist
3. Output notes `TD-ADR skipped — Lean mode.` and `CEA-ADR skipped — Lean mode.`

**Assertions:**
- [ ] Step 5.5 spawns `core-systems-lead`
- [ ] `chief-engine-architect` is not spawned for Step 5.5 of a single-module decision
- [ ] The lead is read from the layout's row, not from a list kept in `references/engine-mode.md`

---

### Case 12: Engine Mode on Custom — a Cinematics ADR goes to the layout's Lead

**Fixture:**
- `project.yaml`: `engine.name: Custom`, `modes.review_mode: lean`
- `.claude/docs/custom-engine-layout.md` as shipped: `engine/cinematics/` has Owner `cinematics-sequencer-engineer` and Lead `editor-architect`

**Input:** `/architecture-decision Cinematics track evaluation order`

**Expected behavior:**
1. Step 1 resolves the module `engine/cinematics/` through the layout; it is not reported as an unknown domain
2. Step 5.5 spawns `editor-architect`, the row's Lead
3. A decision spanning `engine/cinematics/` and `engine/renderer/` would go to `chief-engine-architect` instead (the layout's boundary owner)

**Assertions:**
- [ ] Step 5.5 spawns `editor-architect`
- [ ] No Step 5.5 is skipped for want of a domain: every module with a layout row has a lead

---

### Case 13: Engine Mode on Custom — the module spec stands in for the GDD

**Fixture:**
- `project.yaml`: `engine.name: Custom`, `modes.review_mode: solo`
- `docs/architecture/modules/jobs.md` exists; its section 10 has two criteria, registered in
  `docs/architecture/tr-registry.yaml` as `TR-jobs-001` and `TR-jobs-002` (`system: jobs`,
  `gdd: docs/architecture/modules/jobs.md`)
- `design/gdd/jobs.md` is a game GDD for the player's professions, a different system with the
  same slug; its criterion is registered as `TR-jobs-003` (`system: jobs`, `gdd: design/gdd/jobs.md`)
- No `design/gdd/` file names the job system

**Input:** `/architecture-decision Job system: work-stealing with continuations`

**Expected behavior:**
1. Step 3 reads section 10 of `docs/architecture/modules/jobs.md` with `md-section.sh extract` and the two registry entries whose `gdd:` is the module spec, not `TR-jobs-003`
2. The ADR's `## GDD Requirements Addressed` table names `docs/architecture/modules/jobs.md` in its first column and `TR-jobs-001` and `TR-jobs-002` in the Requirement column
3. Step 5.7's sync check compares the ADR against the module spec and prints its one-line result, not `NOT ASSESSED` for want of a GDD

**Assertions:**
- [ ] The table lists `TR-jobs-001` and `TR-jobs-002` against the module spec
- [ ] The table does not list `TR-jobs-003`, the same-slug game GDD's entry
- [ ] The table is not the "Foundational — no GDD requirement" line while the module spec exists
- [ ] The GDD sync line counts the module spec

---

## Protocol Compliance

- [ ] Engine context (`VERSION.md`) is loaded first and stamped into the Engine Compatibility table
- [ ] Assumptions are confirmed via `AskUserQuestion` before the ADR is generated
- [ ] "May I write" is asked once for the whole ADR before writing; the registry update has its own approval
- [ ] TD-ADR runs only in full mode; lean/solo print a skip note naming the gate and mode
- [ ] TD-ADR CONCERNS are shown verbatim with `Revise flagged items` / `Accept and proceed` / `Discuss further`, never revised without the user's choice
- [ ] A TD-ADR `NOT ASSESSED` answer names the missing input and is never presented as an approval
- [ ] Authoring always writes `Status: Proposed`; `Accepted` is set only by acceptance mode after its dependency check and explicit user confirmation — directly through `accept`, or when retrofit hands it an `Accepted` answer
- [ ] Engine validation and the GDD sync check each report `NOT ASSESSED` when they cannot run, never a silent pass
- [ ] Authoring does not unblock stories; it lists the stories still waiting on the ADR
- [ ] Ends with next-step handoff: `/architecture-review` in a fresh session, and `/architecture-decision accept ADR-NNNN`

---

## Coverage Notes

- Retrofit is fixture-tested only for a missing Status answered `Accepted`
  (Case 6); the other answers (`Proposed`, `Deprecated`, `Superseded`) and the
  retrofit of Engine Compatibility and GDD Requirements Addressed are not.
- The acceptance-mode refusals for a missing `## Status`, an absent or `UNKNOWN`
  dependency section, and an already-Accepted or Superseded ADR are not
  individually fixture-tested.
- Of the GDD sync check's three outcomes, the one-line clean result (Case 1)
  and `NOT ASSESSED` (Case 3) are tested; the warning block and its
  three-option write approval are not.
- `team.size` and `docs.density` variations are not tested.
- ADR numbering is not independently fixture-tested beyond Case 1.
