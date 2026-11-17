# Agent Test Spec: lighting-artist

## Agent Summary
Domain: scene lighting, exposure, tone mapping, colour grading, lightmap and probe bake settings, and the look-dev scene and record, on every engine.
Does NOT own: lighting direction (art-director), lighting shaders (technical-artist), renderer or engine code (the engine-side partner for the project's engine).
Reports to: art-director. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] `description:` field is present and domain-specific (references lighting / exposure / tone mapping / grading / bake settings) and does not start with `Custom:`
- [ ] `tools:` list includes Read, Write, Edit, Glob, Grep — does NOT include Bash (`disallowedTools: Bash`)
- [ ] Model tier is `inherit` — frontmatter `model:` reads exactly `inherit` (tiers: `.claude/docs/model-tiers.md`)
- [ ] "What This Agent Must NOT Do" names `art-director` for lighting direction and `technical-artist` for lighting shaders
- [ ] The Engine-Side Partners table has one row per engine: Custom (`graphics-features-engineer` through `rendering-lead`), Godot, Unity and Unreal (that engine's own specialists), Web (`lead-programmer`, with the reason); no Custom agent is named outside the Custom row

---

## Test Cases

### Case 1: Lighting and Look-Dev — exposure for a walk from a dark interior to a bright exterior
**Fixture:** `project.yaml` sets `engine.name: Unreal`; the art bible asks that the exterior feel blinding for a moment after the cave; the project has not extended the auto exposure luminance range.
**Input:** "Set the exposure for the cave exit."
**Expected behavior:**
- Proposes a locked exposure for the look-dev captures and an auto exposure range for play, per area (cave, exit, exterior)
- States that Unreal's Min Brightness and Max Brightness are in cd/m² in this project, because the luminance range is not extended to EV100, and names the unit with every value it records
- Does NOT set Min Brightness equal to Max Brightness for play, since that turns auto exposure off; uses equal values only where a locked exposure is wanted
- Judges the result after tone mapping, at the exposure each area uses, and records the values in the look-dev record
- Takes a question about what the engine supports to `unreal-specialist`
**Assertions:**
- [ ] Every exposure value carries its unit
- [ ] No number is presented as an engine fact without a source; the chosen values are recorded as project settings

### Case 2: Direction asked of the lighting artist
**Fixture:** `project.yaml` sets `engine.name: Godot`; `design/art/art-bible.md` exists and has no lighting-mood section yet.
**Input:** "Decide the lighting mood for the whole game."
**Expected behavior:**
- Does NOT decide the mood: states that lighting direction belongs to `art-director`
- Offers 2-4 mood options with their trade-offs for `art-director` to decide, each tied to the art bible's existing palette and pillars
- Once direction exists, offers to light one area from it as a look-dev test
**Assertions:**
- [ ] No lighting direction is written to the art bible by this agent
- [ ] `art-director` is named as the owner of lighting direction

### Case 3: Lighting shader asked
**Fixture:** `project.yaml` sets `engine.name: Unity` with HDRP.
**Input:** "Write a custom shader for god rays through the window."
**Expected behavior:**
- Does NOT write the shader: states that lighting shaders are `technical-artist`'s
- Hands over what the shader needs from lighting: the look it must reach, the reference images, and the light and exposure values of the area
- Names `unity-shader-specialist` for a render pipeline (HDRP) question, and checks first whether a built-in HDRP feature already gives the look before a new shader is asked for
**Assertions:**
- [ ] No shader code is produced
- [ ] `technical-artist` is named for the shader

### Case 4: Custom engine — a grading stage the renderer lacks
**Fixture:** `project.yaml` sets `engine.name: Custom`; the renderer has tone mapping but no colour grading stage.
**Input:** "Grade the night levels blue, as the art bible says."
**Expected behavior:**
- Takes the request for the missing grading stage to `graphics-features-engineer` through `rendering-lead`, stating what the stage must do (apply a 3D LUT after tone mapping is settled, with a neutral identity LUT)
- Builds the grade itself as a 3D LUT from the art bible's direction, ready for when the stage exists
- Writes no renderer code
**Assertions:**
- [ ] The route names `rendering-lead` and `graphics-features-engineer`
- [ ] No renderer or shader code is produced

### Case 5: Web — baked lighting with no engine specialist
**Fixture:** `project.yaml` sets `engine.name: Web`; the project renders 3D with a JavaScript library and has no lightmap support yet.
**Input:** "Bake the lighting for the museum level."
**Expected behavior:**
- Takes the missing lightmap support to `lead-programmer`, stating that Web has no specialist set
- Records per area which lights would be baked, mixed or real-time and the bake settings it needs, and takes the lightmap memory budget from the project's budgets rather than inventing one
- Does NOT name a Custom engine agent or a Godot, Unity or Unreal specialist
**Assertions:**
- [ ] `lead-programmer` is the only engine-side partner named
- [ ] No Custom agent is named

### Case 6: Light values in the project's units
**Fixture:** `project.yaml` sets `engine.name: Godot`; the project has not enabled physical light units.
**Input:** "Make the street lamps as bright as real sodium lamps, in lumens."
**Expected behavior:**
- Checks which units the project's lights use before giving a value, and states that Godot uses arbitrary units unless the project enables physical light units
- Offers the choice: enable physical light units (a project-wide change, for the user and `art-director` to decide) or match the look in the project's arbitrary units against a reference
- Does NOT mix lumen values with arbitrary units, and records the chosen units in the look-dev record
- Takes a question about the setting to `godot-specialist`
**Assertions:**
- [ ] The units question is settled before any value is given
- [ ] No project-wide setting is changed without the user's yes

---

## Protocol Compliance

- [ ] Stays within declared domain (scene lighting, exposure, tone mapping, grading, bake settings, look-dev)
- [ ] Redirects lighting direction to `art-director` and lighting shaders to `technical-artist`
- [ ] Routes engine work to the partner its table names for the project's `engine.name`
- [ ] Records every value with its unit in the look-dev record; an unsourced value is a project setting, never an engine fact
- [ ] Shows the values and the files it would write, and writes only after the user's yes
- [ ] Produces no shader, renderer or engine code

---

## Coverage Notes
- Cases 1 and 3-6 cover one engine route each (Unreal, Unity, Custom, Web, Godot); Case 2 covers the direction limit
- Case 1 is titled after the agent's `### Lighting and Look-Dev` section (`test_phase7_sections_have_spec_cases`)
- The routes are checked as text in the agent's table; live routing in a session is not run here
