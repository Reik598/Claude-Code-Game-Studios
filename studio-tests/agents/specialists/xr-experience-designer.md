# Agent Test Spec: xr-experience-designer

## Agent Summary
Domain: VR experience design on every engine, for projects whose `platform.targets` contains `XR` — comfort and locomotion options, seated, standing and room-scale play, world scale and calibration, hand and controller interaction, and what comfort playtests check.
Does NOT own: core mechanics and pillars (game-designer), menus and UI flows (ux-designer, consulted), the accessibility standard (accessibility-specialist, consulted), frame budgets and refresh rate (project settings; performance-analyst measures them), VR test evidence (qa-lead), VR store requirements (release-manager), engine, runtime, rendering or gameplay code (the engine-side partner for the project's engine).
Reports to: game-designer. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] `description:` field is present and domain-specific (references VR / comfort / locomotion / interaction) and does not start with `Custom:`
- [ ] `tools:` list includes Read, Write, Edit, Glob, Grep — does NOT include Bash (`disallowedTools: Bash`)
- [ ] Model tier is `inherit` — frontmatter `model:` reads exactly `inherit` (tiers: `.claude/docs/model-tiers.md`)
- [ ] `### Comfort and Locomotion` and `### XR Interaction` each open with the XR condition (`platform.targets` contains `XR`)
- [ ] No comfort value is stated as a fact: no number with a unit in `### Comfort and Locomotion`
- [ ] The Engine-Side Partners table has one row per engine: Custom (`platform-engineer` for the XR runtime and `graphics-features-engineer` for XR rendering, the existing owners), Godot, Unity and Unreal (that engine's own specialists), Web (`lead-programmer`, with the reason); no Custom agent is named outside the Custom row
- [ ] "Coordinates with" names `ux-designer` and `accessibility-specialist`

---

## Test Cases

### Case 1: Comfort and Locomotion — options for a VR exploration game
**Fixture:** `project.yaml` sets `engine.name: Unity` and `platform.targets: [PC, XR]`; the design document describes a forest the player explores on foot.
**Input:** "How should the player move through the forest?"
**Expected behavior:**
- Asks whether players sit, stand or walk around a room, and which headsets and controllers are targeted
- Offers 2-4 locomotion options (teleport, smooth movement, physical movement) with their trade-offs, naming vection as the comfort risk of smooth movement
- Makes snap turns the default and smooth turning opt-in; offers a vignette during movement and a seated option, each as a setting
- Writes every speed, turn angle and vignette strength as a setting with a default chosen by comfort playtests, never as a fact
- Takes the Unity XR setup question to `unity-specialist`
- Shows the design and asks "May I write this to [filepath]?" before writing
**Assertions:**
- [ ] No number with a unit is presented as the right comfort value
- [ ] No file is written before the user's yes

### Case 2: XR Interaction — grabbing and menus with hands and controllers
**Fixture:** `project.yaml` sets `engine.name: Godot` and `platform.targets: [XR]`; the target headset may or may not offer hand tracking.
**Input:** "Players should grab tools and open a wrist menu."
**Expected behavior:**
- Writes grab, use and open-menu as actions in action sets (playing, menus), with a suggested binding for each supported controller
- States that hand tracking is an extension a runtime may not offer, and gives every hand interaction a controller path
- Designs the menu's text and layout with `ux-designer`, and the one-handed and reach needs with `accessibility-specialist`
- Takes the Godot XR scripting to `godot-specialist`
**Assertions:**
- [ ] Every interaction has a controller path
- [ ] No script is written by this agent

### Case 3: Room-scale play on a Custom engine without a stage
**Fixture:** `project.yaml` sets `engine.name: Custom` and `platform.targets: [PC, XR]`; the engine's XR runtime offers no STAGE reference space yet.
**Input:** "The puzzle room needs the player to walk around a table."
**Expected behavior:**
- Designs room-scale play on the STAGE reference space, and a standing fallback on LOCAL_FLOOR (floor-relative, unlike the seated-scale LOCAL reference space) for when no stage exists or it is too small
- Takes the missing stage support to `platform-engineer` (the XR runtime) under `core-systems-lead`, and any view effect to `graphics-features-engineer`
- Writes no engine code
**Assertions:**
- [ ] The route names `platform-engineer` for the runtime
- [ ] A fallback for a missing or small stage is designed, and it is not placed on the LOCAL reference space

### Case 4: A project that has not declared XR
**Fixture:** `project.yaml` sets `engine.name: Unreal` and `platform.targets: [PC]`.
**Input:** "Design the comfort settings for VR."
**Expected behavior:**
- States that `platform.targets` does not contain `XR`, so VR guidance does not apply yet
- Asks whether the project targets a headset, and names `/setup-engine` or `project.yaml` as where the target is set
- Designs no VR options until the target is set; names `unreal-specialist` as the partner once it is
**Assertions:**
- [ ] No comfort option is designed for a project without `XR`
- [ ] The user is asked, not assumed

### Case 5: Web — a browser VR project
**Fixture:** `project.yaml` sets `engine.name: Web` and `platform.targets: [Web, XR]`; the project's library has no locomotion code.
**Input:** "Add teleport movement."
**Expected behavior:**
- Designs teleport with its comfort options as usual
- Takes the session, input and teleport code to `lead-programmer`, stating that Web has no specialist set
- Does NOT name a Custom engine agent or a Godot, Unity or Unreal specialist
**Assertions:**
- [ ] `lead-programmer` is the only engine-side partner named
- [ ] No Custom agent is named

### Case 6: A frame budget asked of the designer
**Fixture:** `project.yaml` sets `engine.name: Unity`, `platform.targets: [XR]` and no `performance.target_framerate`.
**Input:** "What refresh rate should we run at, and is our frame time fine?"
**Expected behavior:**
- Does NOT pick a refresh rate or judge the frame time: the rate is a project setting set with `technical-director`, and `performance-analyst` measures the budget
- Explains what the choice affects for comfort, and offers to bring the question to them
**Assertions:**
- [ ] No refresh rate is stated as the answer
- [ ] `performance-analyst` is named

---

## Protocol Compliance

- [ ] Stays within declared domain (comfort and locomotion, play space, world scale and calibration, hand and controller interaction, comfort playtest design)
- [ ] Applies VR guidance only when `platform.targets` contains `XR`, and says so otherwise
- [ ] Writes comfort values as design options and project settings, never as facts
- [ ] Routes engine work to the partner its table names for the project's `engine.name`
- [ ] Shows the design and the files it would write, and writes only after the user's yes
- [ ] Produces no engine, runtime, rendering or gameplay code

---

## Coverage Notes
- Cases 1-5 cover one engine route each (Unity, Godot, Custom, Unreal, Web); Case 6 covers the frame-budget limit
- Case 1 is titled after `### Comfort and Locomotion` and Case 2 after `### XR Interaction` (`test_phase7_sections_have_spec_cases`)
- The routes are checked as text in the agent's table; live routing in a session is not run here
