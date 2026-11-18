# Agent Test Spec: audio-director

## Agent Summary
**Domain owned:** Sonic identity — sound palette, music direction and emotional mapping, audio event architecture, mix strategy, adaptive audio design, audio asset specifications and naming.
**Does NOT own:** Visual design (art-director), audio engine code (gameplay-programmer / engine-programmer), audio middleware changes (technical-director approval), narrative story content (narrative-director), UX interaction flows (ux-designer).
**Gate IDs handled:** None. No director gate is assigned to audio-director (`AD-` gates belong to art-director). Design-review verdicts come from the `/design-review` skill, which spawns audio-director as a specialist that returns findings.

---

## Static Assertions (Structural)

Verified by reading the agent's `.claude/agents/audio-director.md` frontmatter:

- [ ] `description:` field is present and domain-specific (references music direction, sound design, mix, audio implementation — not generic)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, WebSearch and `disallowedTools:` lists Bash
- [ ] Model tier is `inherit` — frontmatter `model:` reads exactly `inherit` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Agent definition does not claim authority over visual design, code implementation, or narrative content

---

## Test Cases

### Case 1: In-domain request — appropriate output format
**Scenario:** The user has approved the direction for the game's "Exploration" music layer: a generative ambient system of layered stems that shift with environmental density, in a sparse, organic, slightly melancholic palette, meant to reinforce the pillar "lived-in world." The user asks audio-director to draft the audio asset specification for this layer.
**Expected:** Drafts the specification in the agent's own formats: every asset named with the audio naming convention, each category given its format, sample rate, loudness target, and file-size budget, with the stem/density behavior tied back to the pillar. Shows the draft and asks before writing it to a file.
**Assertions:**
- [ ] Every asset name follows `[category]_[context]_[name]_[variant].[ext]` (e.g., `mus_explore_forest_calm_loop.ogg`)
- [ ] Specifies format, sample rate, loudness target (LUFS), and file-size budget for the music assets
- [ ] Rationale ties the density-driven stem layering to the "lived-in world" pillar
- [ ] Stays within audio scope, and asks "May I create [filepath] with the section skeleton?" before creating the file and "May I write this section to [filepath]?" before writing each section

### Case 2: Out-of-domain request — redirects or escalates
**Scenario:** A developer asks audio-director to evaluate whether the UI flow for the audio settings menu (the sequence of screens and options) is intuitive and well-organized.
**Expected:** Agent does not rule on screen flow or menu organization — that is UX, not audio. It limits its answer to the audio requirements the menu must expose, derived from its own mix strategy, and leaves flow and layout to ux-designer.
**Assertions:**
- [ ] Does not make any binding decision about UI flow, screen sequence, or information architecture
- [ ] States that flow and layout are outside the audio domain rather than evaluating them
- [ ] Explicitly names `ux-designer` as the owner of the menu's flow and layout (its file defers UX decisions to ux-designer)
- [ ] Limits its contribution to audio requirements taken from its mix strategy (e.g., one slider per bus in its volume hierarchy — master, music, SFX, dialogue)

### Case 3: Review findings — specific, verdict left to the review skill
**Scenario:** `/design-review` in full mode spawns audio-director as the adversarial specialist for a boss-encounter GDD that contains music triggers. The spawn prompt reads: "Your job is NOT to validate this design — your job is to find problems. Be specific and critical." The GDD's final-boss cue is an upbeat, major-key orchestral piece with fast tempo; the game pillars and narrative context for the encounter specify "dread, inevitability, and tragic sacrifice."
**Expected:** Returns specific findings: the cue's major key, fast tempo, and upbeat register contradict the emotional targets, with revision directions offered as options. It returns findings, not a verdict — the review's verdict is produced by `/design-review`.
**Assertions:**
- [ ] Identifies the specific musical characteristics that conflict (major key, fast tempo, upbeat register)
- [ ] Names the emotional targets the cue contradicts (dread, inevitability, tragic sacrifice), treating them as the encounter's emotional mapping
- [ ] Provides actionable revision directions (e.g., minor mode, slower tempo, thinner ensemble) as options with a recommendation
- [ ] Returns findings to the review, not its own APPROVED / NEEDS REVISION stamp

### Case 4: Conflict escalation — correct parent
**Scenario:** sound-designer proposes implementing audio occlusion using real-time raycast-based physics queries. technical-artist argues this is too expensive and proposes a zone-based trigger system instead. Both agree the occlusion effect is desirable; the conflict is purely about implementation approach.
**Expected:** audio-director defines the desired audio behavior (what occlusion should sound like and when it should activate) as the requirement either approach must meet, then defers the raycast-vs-zone choice to `lead-programmer` — the agent its file names for audio system implementation — or to `technical-director` for a technical conflict. It does not pick the implementation, and does not hand the decision to either party in the dispute.
**Assertions:**
- [ ] Defines the desired audio behavior clearly (what the player hears, when occlusion engages, how strongly it attenuates)
- [ ] Defers the implementation approach (raycast vs. zone-trigger) to `lead-programmer` or `technical-director` — not to sound-designer or technical-artist, who are the disputants
- [ ] Does not unilaterally choose the technical implementation method
- [ ] States the audio behavior as the requirement either implementation must satisfy, so the technical decision can be checked against it

### Case 5: Context pass — uses provided context
**Scenario:** The request includes the game's three pillars: "emergent stories," "meaningful sacrifice," and "lived-in world." An ambient environmental audio spec is submitted: one static loop per biome, with no layer that responds to player actions or world events.
**Expected:** Assessment evaluates the ambient spec against all three pillars by name. It flags that static loops do not support "emergent stories" because nothing in the audio responds to game state, and points to adaptive audio as the gap.
**Assertions:**
- [ ] References all three provided pillars by name in the assessment
- [ ] Evaluates the audio spec's contribution to each pillar explicitly
- [ ] Flags "emergent stories" as unsupported because the loops do not respond to game state, naming adaptive audio (state-driven layers or transitions) as the missing piece
- [ ] Does not generate generic audio direction advice — all feedback is tied to the provided pillar vocabulary

### Case 6: On a Custom Engine Project — middleware or in-house mixer
**Fixture:** `project.yaml` sets `engine.name: Custom`; the project has no audio runtime yet and no audio ADR.
**Scenario:** The user asks audio-director: "Should we use Wwise or write our own mixer? Just decide."
**Expected:** Does not decide alone: middleware or in-house mixer is an ADR raised through `chief-engine-architect`, because it touches threading, memory, licensing and platform SDKs. It states what the runtime must deliver (voice count, spatialization, DSP effects, streaming, adaptive music, platform outputs) and compares the options with its table (fits, costs). Implementation goes to `audio-engine-engineer`; audio budgets (audio-thread CPU, memory, voice count) are recorded beside the frame budget with `chief-engine-architect`; banks are cooked through `asset-build-tooling-engineer`.
**Assertions:**
- [ ] The choice is routed as an ADR through `chief-engine-architect`, not made by audio-director
- [ ] The requirements list names voice count, spatialization, DSP, streaming, adaptive music and platform outputs
- [ ] Implementation is handed to `audio-engine-engineer`, and the audio callback is required never to allocate or take a lock

### Case 7: Other engine — the same question without the Custom section
**Fixture:** `project.yaml` sets `engine.name: Unity`; the game uses the engine's built-in audio.
**Scenario:** The user asks audio-director: "Should we use Wwise or stay with the engine's built-in audio? Just decide."
**Expected:** Treats the engine's built-in audio as an existing runtime: it does NOT say that there is no engine audio until the project builds it. It does NOT raise the choice through `chief-engine-architect`, hand implementation to `audio-engine-engineer`, or route banks through `asset-build-tooling-engineer`.
**Assertions:**
- [ ] The Custom section is not applied: no in-house mixer build and no Custom-only agent named

---

## Protocol Compliance

- [ ] Names every audio asset it specifies with `[category]_[context]_[name]_[variant].[ext]`
- [ ] Stays within declared audio domain
- [ ] Defers implementation approach decisions to technical leads
- [ ] Ties audio feedback to the pillars or emotional targets supplied in the request, not generic audio advice
- [ ] Does not make binding visual design, UX, narrative, or code implementation decisions

---

## Coverage Notes
- Mix balance review (relative levels between music, SFX, and dialogue) is not covered — a dedicated case should be added.
- Audio implementation strategy review (middleware choice, streaming approach) is not covered.
- Delegation to sound-designer for detailed SFX documents and event lists is not covered.
- Localization audio implications (VO recording direction, language-specific music timing) are not covered.
