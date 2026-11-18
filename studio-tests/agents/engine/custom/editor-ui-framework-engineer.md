# Agent Test Spec: editor-ui-framework-engineer

## Agent Summary
Domain: the in-house editor's UI layer on a project whose `engine.name` is `Custom` — `engine/editor/ui/` (Rust: `crates/editor-ui`) on whichever framework the accepted UI framework ADR picked: docking and layout persistence, the reflection-driven property inspector with custom drawers, the asset browser with thumbnails and search, menus and context menus, commands and keybindings, text input/IME, high-DPI and multi-monitor, accessibility, localization of editor strings, theming.
Does NOT own: the framework choice, reflection and transactions (editor-architect), viewport/picking/gizmos (level-editor-engineer), the game's runtime UI (ui-programmer), editor UX flows (ux-designer), in-game tools (tools-programmer).
Reports to: editor-architect. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/editor-ui-framework-engineer.md`
- [ ] `description:` is present and domain-specific (docking, property inspector with drawers, thumbnails, keybindings, IME, high-DPI, theming)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `sonnet-medium` — frontmatter `model:` reads exactly `sonnet` and `effort:` reads exactly `medium` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `editor-architect`"
- [ ] States the framework choice is `editor-architect`'s ADR and lists the four options without picking one
- [ ] Worked Correct vs Incorrect example in both C++23 and Rust (reflection-driven drawer through a transaction vs widget writing the component) and a module layout block with `engine/editor/ui/` and `crates/editor-ui`
- [ ] Has `## Version Awareness` (`docs/engine-reference/custom/VERSION.md`, `NOT SOURCEABLE`) and `## Tooling` (UI automation, golden-image tests, `test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — property inspector
**Fixture:** An accepted UI framework ADR exists.
**Input:** "Build the property inspector. It must handle 500 selected entities and custom editing for colour and curve fields."
**Expected behavior:**
- Builds the property tree from reflection; a drawer registry keyed by type and attribute for colour and curve
- Multi-selection shows mixed values and writes only changed fields
- Every edit goes through the editor's `set_property` transaction; sliders coalesce until release
- Refreshes on transaction notifications, not every frame
- Asks before writing files
**Assertions:**
- [ ] No widget writes components directly
- [ ] Mixed values handled
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — game HUD
**Input:** "Also build the in-game health bar and pause menu."
**Expected behavior:** Declines; the game's runtime UI belongs to `ui-programmer`.
**Assertions:**
- [ ] Names `ui-programmer` exactly
- [ ] Does not write HUD code

### Case 3: No accepted framework ADR
**Fixture:** No UI framework ADR exists in `docs/architecture/`.
**Input:** "Start the docking system in Qt."
**Expected behavior:** Says the framework is not chosen; does not pick Qt (or ImGui) itself; routes the decision to `editor-architect` (ADR via `/architecture-decision`); offers only framework-agnostic models (layout model, command registry) meanwhile.
**Assertions:**
- [ ] `editor-architect` named as owner of the choice
- [ ] No framework-specific code written

### Case 4: Framework limit — IME under Dear ImGui
**Fixture:** The accepted ADR picked Dear ImGui (docking branch); the editor must support Japanese asset names.
**Input:** "Make the asset rename field work with Japanese input."
**Expected behavior:** Flags the ADR-noted weakness at complex text/IME; handles composition events and caret-positioned candidate window where the backend allows; writes `NOT SOURCEABLE` for any framework-version IME capability not in `docs/engine-reference/custom/`; reports the limit to `editor-architect` if it cannot be met.
**Assertions:**
- [ ] Limitation surfaced, not hidden
- [ ] `NOT SOURCEABLE` for unsourced framework facts
- [ ] Composition handled as text events, not key-downs

### Case 5: NOT ASSESSED — accessibility claim
**Fixture:** No screen-reader or OS accessibility-inspector check has been run.
**Input:** "Mark the asset browser as accessible in the release notes."
**Expected behavior:** States accessibility is `NOT ASSESSED`; lists the check needed (keyboard reachability, focus order, accessibility tree in the OS inspector or a screen reader); mentions `accessibility-specialist`.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing check named
- [ ] No "accessible" claim

### Case 6: Keybinding conflict
**Input:** "Bind Ctrl+D to duplicate in the viewport and to delete in the asset browser."
**Expected behavior:** Both are commands with stable IDs and contexts; same chord in different contexts is allowed, within one context it is reported as a conflict; user remaps live in per-user config, not the repo.
**Assertions:**
- [ ] Commands invoked by ID through the registry
- [ ] Context-scoped conflict rule stated

---

## Protocol Compliance

- [ ] Never chooses the UI framework; defers to `editor-architect`'s ADR
- [ ] Every inspector edit goes through transactions
- [ ] Redirects game UI to `ui-programmer`, UX flows to `ux-designer`, viewport work to `level-editor-engineer`
- [ ] No accessibility or localization claim without a check
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Thumbnail generation and asset browser search have no dedicated case.
- High-DPI and multi-monitor are covered only statically and by golden images at 200 % scale.
