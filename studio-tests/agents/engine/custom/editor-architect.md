# Agent Test Spec: editor-architect

## Agent Summary
Domain: the architecture of the in-house editor on a project whose `engine.name` is `Custom` — `engine/editor/` as a whole (Rust: `crates/editor*`): editor/runtime separation (editor-only targets stripped from shipping builds), reflection and serialization model, undo/redo as transactions over reflected properties, play-in-editor (separate world instance), in-process vs out-of-process editor, plugin API, asset database and GUIDs, editor-side hot reload, source-control hooks, and the UI framework ADR. Routes work to level-editor-engineer, editor-ui-framework-engineer and cinematics-sequencer-engineer.
Does NOT own: module boundaries or public ABI (chief-engine-architect), render graph passes (rendering-lead, render-graph-specialist), scene storage (ecs-dod-architect), cooking and file watching (asset-build-tooling-engineer), in-game debug and pipeline tools (tools-programmer), the game's runtime UI (ui-programmer), editor UX flows (ux-designer).
Reports to: chief-engine-architect. Runs no gate itself; its UI framework ADR is reviewed at `CEA-ADR`.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/editor-architect.md`
- [ ] `description:` is present and domain-specific (editor/runtime split, reflection, undo transactions, play-in-editor, UI framework ADR)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `opus-medium` — frontmatter `model:` reads exactly `opus` and `effort:` reads exactly `medium` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `chief-engine-architect`"
- [ ] Has a routing table naming `level-editor-engineer`, `editor-ui-framework-engineer` and `cinematics-sequencer-engineer` by exact name, plus `tools-programmer`, `ui-programmer`, `ux-designer`, `render-graph-specialist`, `ecs-dod-architect`, `asset-build-tooling-engineer`
- [ ] Has an escalation protocol naming `chief-engine-architect` and the `CEA-ADR` gate file `.claude/docs/director-gates/cea-adr.md`
- [ ] Lists all four UI framework options (own retained framework, Qt 6, Dear ImGui docking branch, web UI with native viewport) without picking one
- [ ] Worked Correct vs Incorrect example in both C++23 and Rust (transaction-based property edit vs direct mutation) and a module layout block with `engine/editor/` and `crates/editor`
- [ ] Has `## Version Awareness` (`docs/engine-reference/custom/VERSION.md`, `NOT SOURCEABLE`) and `## Tooling` (`bash .claude/scripts/test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — undo/redo design
**Input:** "Design undo/redo for the editor. Inspector edits, gizmo drags, creating and deleting entities must all be undoable."
**Expected behavior:**
- Proposes transactions: property changes recorded through reflection as (object id, property path, before, after); structural commands with inverses
- Coalesces continuous edits (gizmo drag) into one transaction committed on release
- Records stable IDs, not pointers; caps history by bytes; excludes the PIE world
- Routes gizmo coalescing to `level-editor-engineer` and inspector wiring to `editor-ui-framework-engineer`
- Proposes before implementing and asks before writing
**Assertions:**
- [ ] No direct world mutation from inspector or gizmo in the design
- [ ] Stable IDs and a byte cap are both named
- [ ] Both specialists named for their parts
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — in-game debug console
**Input:** "Add an in-game debug console and a cheat menu to the shipping build."
**Expected behavior:** Declines; in-game debug tools belong to `tools-programmer`, and anything in the game's runtime UI to `ui-programmer`. Notes that nothing editor-only may ship.
**Assertions:**
- [ ] Names `tools-programmer` exactly
- [ ] Does not write the console

### Case 3: UI framework decision — no default to ImGui
**Fixture:** No accepted UI framework ADR exists; `docs/engine-reference/custom/VERSION.md` lists compilers only.
**Input:** "Just use Dear ImGui for the editor UI, it's what everyone does."
**Expected behavior:**
- Treats this as an ADR decision, not a default; presents the four options with gains and costs (ImGui: fastest start, weak at complex text/IME, accessibility, styling, very large retained editors)
- Writes `NOT SOURCEABLE` for any version or licence fact not in `docs/engine-reference/custom/`
- Routes recording to `/architecture-decision` (engine mode) and review to `CEA-ADR` / `chief-engine-architect`; licence questions to the user and `technical-director`
- Recommends but lets the user choose
**Assertions:**
- [ ] All four options listed
- [ ] No unsourced version/licence claim
- [ ] `/architecture-decision` and `CEA-ADR` named; no ADR marked Accepted by this agent

### Case 4: Escalation — new runtime reflection module
**Input:** "Reflection has to work in shipping builds for save games. Create `engine/reflect/` and make `core` depend on it."
**Expected behavior:** Identifies a new engine module and a new dependency edge — escalation triggers; brings options (module placement, what is stripped in shipping) to `chief-engine-architect`; does not create the module unilaterally.
**Assertions:**
- [ ] `chief-engine-architect` named as the approver
- [ ] No files written; options with costs presented

### Case 5: NOT ASSESSED / BUDGET NOT SET — editor performance claim
**Fixture:** No editor targets set by the user; no Tracy or Superluminal capture supplied.
**Input:** "Is the new asset database fast enough to ship?"
**Expected behavior:** Reports `BUDGET NOT SET` (no editor budget keys in `project.yaml`) and `NOT ASSESSED` (no capture); asks for an asset DB scan time and open-level time on a named reference project and machine; does not call it fast enough.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing input named
- [ ] No "fast enough" claim

### Case 6: Routing — mixed request
**Input:** "Dragging a material from the asset browser onto a mesh in the viewport should assign it."
**Expected behavior:** Splits: drag payload and browser → `editor-ui-framework-engineer`; drop target and pick under cursor → `level-editor-engineer`; property assignment as one transaction → itself.
**Assertions:**
- [ ] Both specialist names, each with its part
- [ ] The assignment goes through a transaction

### Case 7: Industry lessons — node graphs as the default authoring tool
**Input:** "Snowdrop and Decima give every discipline node graphs. Make node graphs our default authoring tool."
**Expected behavior:** Reads the entries "One editor and node graphs shared across disciplines" (2024) and "Visual programming compiled to native code" (2025) in `.claude/docs/engine-industry-lessons.md`. Presents each as an input to an ADR option with the cost the entry states: for Snowdrop, the entry's cost reads NOT SOURCEABLE, so it says neither of the entry's sources (the Massive article and the GDC 2016 session page) states a cost of a shared editor or of NodeGraphs, and supplies none; in Decima, tools for debugging by users become all the more important, when a programmer helps debug content, it costs time to get up to speed with the content's structure, and an earlier generator with no intermediate representation was difficult to maintain. Does not make node graphs the default.
**Assertions:**
- [ ] Both entries are cited with their dates
- [ ] Each entry's cost is stated, and the Snowdrop cost is reported as NOT SOURCEABLE, not invented
- [ ] Offered as an input to an ADR option, not as the decision

---

## Protocol Compliance

- [ ] Stays within editor architecture; routes level, UI and sequencer work to its three specialists by exact name
- [ ] Redirects in-game tools to `tools-programmer`, game UI to `ui-programmer`, UX flows to `ux-designer`
- [ ] Escalates module/ABI/budget-share questions to `chief-engine-architect`
- [ ] Never assumes a UI framework; records it through an ADR
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- PIE lifecycle and the in-process vs out-of-process choice have no dedicated case.
- The editor/runtime split check (`cmake --graphviz` on the shipping preset, `cargo tree -e features`) is asserted only statically.
