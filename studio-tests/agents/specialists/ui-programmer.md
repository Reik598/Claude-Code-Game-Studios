# Agent Test Spec: ui-programmer

## Agent Summary
Domain: Menu screens, HUDs, inventory screens, dialogue boxes, UI framework code, and data binding.
Does NOT own: UX flow and interaction design, including UI animation timing (ux-designer), visual style direction (art-director).
No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] `description:` field is present and domain-specific (references menus / HUDs / UI framework / data binding)
- [ ] `tools:` list includes Read, Write, Edit, Bash, Glob, Grep
- [ ] Model tier is `inherit` — frontmatter `model:` reads exactly `inherit` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Agent definition does not claim authority over UX flow design or visual art direction

---

## Test Cases

### Case 1: In-domain request — appropriate output
**Input:** The UX spec at `design/ux/inventory-flow.md` defines five slot states: default, hover, selected, empty-slot, locked-slot. Request: "Implement the inventory screen from the UX spec in `design/ux/inventory-flow.md`."
**Expected behavior:**
- Reads the UX spec before producing any code
- Produces implementation using the project's configured UI framework (UI Toolkit, UGUI, UMG, or Godot Control nodes)
- Implements every state the spec defines (default, hover, selected, empty-slot, locked-slot) — none dropped, none invented
- Binds inventory data to UI elements via the project's data model, not hardcoded values
- Includes doc comments on public UI API per coding standards

### Case 2: Out-of-domain request — redirects correctly
**Input:** "Design the inventory interaction flow — what happens when the player equips, drops, or combines items."
**Expected behavior:**
- Does NOT produce interaction flow design or user flow diagrams
- Explicitly states that UX flow design belongs to `ux-designer`
- Redirects the request to `ux-designer`
- Notes that once the flow spec is ready, it can implement it

### Case 3: Custom animation coordination
**Input:** "The item selection in the inventory needs a custom bounce animation when selected."
**Expected behavior:**
- Recognizes that the bounce's feel (duration, easing curve, overshoot) is UI interaction and visual design, which it implements but does not design
- Checks the UX spec it is implementing for those values first; does NOT invent them if they are absent
- Asks the spec owner — `ux-designer` for interaction timing, `art-director` for visual style — for the missing values
- Once the values are provided, binds the animation to the selection state, skippable and respecting the player's motion preference

### Case 4: Ambiguous UX spec — flags back
**Input:** The UX spec states "show item details on selection" but does not define what happens when an empty slot is selected.
**Expected behavior:**
- Identifies the ambiguity in the spec (empty slot selection state is undefined)
- Does NOT make an arbitrary implementation decision for the undefined state
- Flags the ambiguity back to `ux-designer` with the specific question: "What should the detail panel show when an empty inventory slot is selected?"
- Any options it offers (e.g., hide the panel / show a placeholder) go to ux-designer as part of the question — none is implemented before the answer

### Case 5: Context pass — engine UI toolkit
**Input:** Engine context provided: project uses Godot 4.6 with Control node UI. Request: "Implement a scrollable item list for the inventory."
**Expected behavior:**
- Uses Godot's `ScrollContainer` + `VBoxContainer` + `ItemList` (or equivalent) pattern, not Canvas or UGUI
- Does NOT produce Unity UGUI or Unreal UMG code for a Godot project
- Checks the engine version reference (4.6) for any Control node API changes from 4.4/4.5 before using specific APIs
- Produces GDScript or C# code consistent with the project's configured language

### Case 6: On a Custom Engine Project — localized main menu
**Fixture:** `project.yaml` sets `engine.name: Custom`; the runtime UI framework does not exist yet.
**Input:** "Build the main menu, with localized text including Arabic."
**Expected behavior:**
- Treats the runtime UI framework as its own to build: retained-mode or immediate-mode is an ADR
- Plans text shaping (e.g. HarfBuzz) with rasterization to a glyph atlas, bidirectional text and line breaking, with the library choices in an ADR
- Keeps that text stack in `engine/ui/` as its own; the editor (`editor-ui-framework-engineer`) consumes it through the interface an ADR records
- Draws the UI in a pass whose slot and budget come from `rendering-lead`, with UI shaders through `shader-pipeline-engineer`
- Works out localization with `localization-lead` and accessibility with `accessibility-specialist`; the UI reads game state through events, never by mutating ECS data
**Assertions:**
- [ ] The framework approach and libraries are ADRs
- [ ] The UI pass budget comes from `rendering-lead`
- [ ] The text stack is planned in `engine/ui/` as `ui-programmer`'s, with the editor consuming it

### Case 7: Other engine — the same menu without the Custom section
**Fixture:** `project.yaml` sets `engine.name: Godot`.
**Input:** "Build the main menu, with localized text including Arabic."
**Expected behavior:**
- Builds the menu with the engine's own UI system, checking version-specific API against `docs/engine-reference/godot/`
- Does NOT plan a runtime UI framework, a shaping-library ADR or a UI render pass, and does NOT name `rendering-lead` or `shader-pipeline-engineer`
**Assertions:**
- [ ] The Custom section is not applied: no in-house UI framework and no Custom-only agent named

---

## Protocol Compliance

- [ ] Stays within declared domain (menus, HUDs, UI framework, data binding)
- [ ] Redirects UX flow design to ux-designer
- [ ] Takes animation timing and easing from ux-designer / art-director specs rather than inventing them, and makes every animation skippable and motion-preference aware
- [ ] Flags ambiguous UX specs back to ux-designer rather than making arbitrary implementation decisions
- [ ] Returns structured output (implementation code, data binding patterns, state machine for UI states)
- [ ] Uses the correct engine UI toolkit for the project — never cross-engine code
- [ ] Asks "May I write this to [filepath]?" naming the file before writing

---

## Coverage Notes
- Inventory implementation (Case 1) should have a retained screenshot of each screen touched in `production/qa/evidence/`
- Animation coordination (Case 3) confirms the agent does not invent feel parameters without a spec
- Ambiguous spec (Case 4) verifies the agent routes spec gaps back to the authoring agent rather than guessing
