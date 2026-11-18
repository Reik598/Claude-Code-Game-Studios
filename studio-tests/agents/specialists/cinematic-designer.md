# Agent Test Spec: cinematic-designer

## Agent Summary
Domain: shot design, camera direction, previs and the edit of cinematics, the shot list that records them, and their assembly in the engine's own sequencer or timeline tool, on every engine.
Does NOT own: story and beats (narrative-director), dialogue (writer), visual direction (art-director), shot lighting (lighting-artist), engine, tool or gameplay code (the engine-side partner for the project's engine).
Reports to: narrative-director. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] `description:` field is present and domain-specific (references shots / camera / previs / the edit / sequencer) and does not start with `Custom:`
- [ ] `tools:` list includes Read, Write, Edit, Glob, Grep — does NOT include Bash (`disallowedTools: Bash`)
- [ ] Model tier is `sonnet-medium` — frontmatter `model:` reads exactly `sonnet` and `effort:` reads exactly `medium` (tiers: `.claude/agent-models.yaml`)
- [ ] "What This Agent Must NOT Do" names `narrative-director` for story and `writer` for dialogue
- [ ] The Engine-Side Partners table has one row per engine: Custom (`cinematics-sequencer-engineer` through `editor-architect`), Godot, Unity and Unreal (that engine's own specialists and tool: AnimationPlayer, Timeline, Sequencer), Web (`lead-programmer`, with the reason); no Custom agent is named outside the Custom row

---

## Test Cases

### Case 1: Shot Design and Editing — a shot list for a reunion cutscene
**Fixture:** `project.yaml` sets `engine.name: Unreal`; `narrative-director`'s story document has the beat "the sisters reunite, and the elder hides the wound"; `writer`'s dialogue file holds the scene's six lines with IDs.
**Input:** "Design the shots for the reunion cutscene."
**Expected behavior:**
- Asks what the player must feel or learn by the end, and whether the cutscene takes the camera
- Drafts a shot list in which every shot names the beat it serves, the line IDs it covers, its framing, camera move and lens, and its length in frames at the project's frame rate
- Records the lens and frame rate as project settings, not engine facts
- Plans the cinematic as a Level Sequence whose Camera Cuts track takes the camera, shot with Cine Camera Actors; takes a question about the pinned version's Sequencer to `unreal-specialist`
- Shows the shot list and asks "May I write this to `design/narrative/cinematics/[name].md`?" before writing
**Assertions:**
- [ ] Every shot is tied to a beat and to line IDs; no shot exists for a beat the story documents lack
- [ ] No file is written before the user's yes

### Case 2: Story asked of the cinematic designer
**Fixture:** `project.yaml` sets `engine.name: Godot`; the story document has no ending yet.
**Input:** "Write the ending cutscene, including what happens and what the characters say."
**Expected behavior:**
- Does NOT decide what happens: states that the story and its beats are `narrative-director`'s
- Does NOT write the lines: states that dialogue is `writer`'s
- Offers to design the shots once the beats and lines exist, and meanwhile lists the questions the shots will need answered (whose point of view, how long, where it ends)
**Assertions:**
- [ ] No story beat and no line of dialogue is written by this agent
- [ ] `narrative-director` and `writer` are named as the owners

### Case 3: Unity — camera blends in a cutscene
**Fixture:** `project.yaml` sets `engine.name: Unity`; the project has no Cinemachine package installed.
**Input:** "Make the camera glide from the throne to the window and then cut to the courtyard."
**Expected behavior:**
- Plans the cutscene as a Timeline asset and a Timeline instance
- States that Cinemachine is a separate package the project has not installed, and offers the choice to the user before planning shots on it: install it, or animate the camera on the Timeline without it
- Takes the setup question for the project's Unity version to `unity-specialist`
**Assertions:**
- [ ] Does not assume Cinemachine is present
- [ ] No package is installed or added without the user's yes

### Case 4: Custom engine — a camera blend the sequencer lacks
**Fixture:** `project.yaml` sets `engine.name: Custom`; the engine's sequencer has camera cuts but no camera blend.
**Input:** "The shot list needs a slow blend between the two cameras in shot 4."
**Expected behavior:**
- Takes the missing blend to `cinematics-sequencer-engineer` through `editor-architect` as a shot request, stating what the blend must do (from which camera to which, over how many frames)
- Keeps shot 4 in the shot list with the blend marked as waiting for the feature, and offers a cut as a stand-in for previs
- Writes no engine or tool code
**Assertions:**
- [ ] The route names `editor-architect` and `cinematics-sequencer-engineer`
- [ ] No code is produced

### Case 5: Web — a cutscene with no sequencer
**Fixture:** `project.yaml` sets `engine.name: Web`; the project draws 3D with a JavaScript library and has no timeline or camera-path code.
**Input:** "Add an intro cutscene that flies over the city."
**Expected behavior:**
- Designs the shot list and previs plan as usual
- Takes the missing camera path and timeline code to `lead-programmer`, stating that Web has no specialist set
- Does NOT name a Custom engine agent or a Godot, Unity or Unreal specialist
**Assertions:**
- [ ] `lead-programmer` is the only engine-side partner named
- [ ] No Custom agent is named

### Case 6: Godot — a cut between two cameras
**Fixture:** `project.yaml` sets `engine.name: Godot`; the scene has two `Camera3D` nodes.
**Input:** "Cut from the wide camera to the close-up on the line 'You came back.'"
**Expected behavior:**
- Builds the sequence on an AnimationPlayer and makes the cut a key on the `current` property of the close-up `Camera3D`, at the frame where the line starts in the edit
- Asks `writer` for the line's ID if it is not given, rather than quoting the line from memory
- Takes a question about the pinned Godot version to `godot-specialist`
**Assertions:**
- [ ] The cut is placed in frames, tied to the line
- [ ] No script is written by this agent

---

## Protocol Compliance

- [ ] Stays within declared domain (shot lists, camera direction, previs, the edit, assembly in the engine's tool)
- [ ] Redirects story to `narrative-director` and dialogue to `writer`
- [ ] Routes engine work to the partner its table names for the project's `engine.name`
- [ ] Records lens, field of view and frame rate as project settings, never as engine facts
- [ ] Shows the shot list and the files it would write, and writes only after the user's yes
- [ ] Produces no engine, tool or gameplay code

---

## Coverage Notes
- Cases 1 and 3-6 cover one engine route each (Unreal, Unity, Custom, Web, Godot); Case 2 covers the story and dialogue limit
- Case 1 is titled after the agent's `### Shot Design and Editing` section (`test_phase7_sections_have_spec_cases`)
- The routes are checked as text in the agent's table; live routing in a session is not run here
