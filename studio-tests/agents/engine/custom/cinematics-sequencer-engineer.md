# Agent Test Spec: cinematics-sequencer-engineer

## Agent Summary
Domain: `engine/cinematics/`, `engine/camera/` and the editor-only `engine/editor/cinematics/` of an in-house engine on a project whose `engine.name` is `Custom` — sequence asset format, timeline tracks (transform, property, animation, audio, event, camera cut), the evaluator and player, deterministic scrubbing, camera manager (view targets, blends, cuts, shake), key edits as editor transactions, offline render-to-movie.
Does NOT own: sim sub-phase order (simulation-systems-lead), pose evaluation and anim graph (animation-systems-engineer), mixer (audio-engine-engineer), transaction/serialization format (editor-architect), timeline panel widgets (editor-ui-framework-engineer), temporal history and motion blur (graphics-features-engineer via rendering-lead), shot content (narrative-director).
Reports to: editor-architect; runtime evaluation coordinated with simulation-systems-lead and animation-systems-engineer. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/cinematics-sequencer-engineer.md`
- [ ] `description:` is present and domain-specific (timeline tracks, scrubbing, camera cuts, render-to-movie)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash (no `Agent`)
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "Reports to:" names `editor-architect`
- [ ] `## Collaboration Protocol` matches memory-allocator-specialist.md except the step-2 questions
- [ ] Has a worked Correct vs Incorrect example in C++23 and Rust and a `## Module Layout` block
- [ ] Has `## Measure First`, `## Common Questions / Decision Guides`, `## Anti-Patterns`, `## Version Awareness`, `## Tooling` (`test-run.sh custom`), `## What This Agent Must NOT Do`, `## Coordination`
- [ ] `editor-architect.md` Routing Table has a row routing to `cinematics-sequencer-engineer`; `simulation-systems-lead.md` Coordination lists it

---

## Test Cases

### Case 1: In-domain — scrubbing gives a different pose than playing
**Input:** "In the sequencer, scrubbing to 0:12 puts the door in a different place than playing to 0:12. The transform track adds `velocity * dt` every update."
**Expected behavior:**
- Identifies integration of deltas as the cause; state must be a function of (sequence, time)
- Proposes evaluating keys at `t` in integer ticks, no accumulation; events over `(prev, cur]` windows while playing, `[t0, cur]` on the first update after a play from stop, jump or scrub, `(prev, cur]` again on resume from pause; none on scrub unless flagged
- Proposes an integration test: evaluate at `t` directly vs play to `t` at two step sizes, compare state hashes
- Asks "May I write this to [filepath]?" before writing
**Assertions:**
- [ ] Names delta integration / float accumulation as the cause
- [ ] Integer tick time and pure evaluation proposed
- [ ] A scrub-determinism test proposed
- [ ] Any event window it proposes fires a key at the start tick once and a key at a pause tick once: never `(prev, cur]` alone from a stop, never `[t, cur]` on resume from pause
- [ ] Approval asked before any write

### Case 2: Out-of-domain redirect — blend in the anim graph
**Input:** "The character's walk-to-idle blend during the cutscene pops. Fix the blend tree."
**Expected behavior:** Redirects the blend tree to `animation-systems-engineer`; may check that the sequencer's animation track sends clip and weight requests at the right time and in the right sub-phase.
**Assertions:**
- [ ] Names `animation-systems-engineer` exactly
- [ ] Does not edit the anim graph

### Case 3: NOT ASSESSED — cinematic "too slow" with no capture
**Input:** "The intro cinematic is over budget, optimise the sequencer." No capture, benchmark or `/benchmark-report` output; no cinematics budget slice recorded.
**Expected behavior:** States the cost is `NOT ASSESSED` because there is no capture, and "budget NOT SET" for the missing slice; asks for a Tracy/Superluminal capture or benchmark scene with the shot's binding count; proposes no optimisation as the fix before evidence.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing capture named
- [ ] Missing budget reported as NOT SET, not assumed
- [ ] No code change proposed as the fix before evidence

### Case 4: Version awareness — EXR output library
**Fixture:** `docs/engine-reference/custom/VERSION.md` exists, `Installed at pin time: NOT DETERMINED`, and no image library is listed.
**Input:** "Make render-to-movie write multi-layer EXR using the latest OpenEXR API."
**Expected behavior:** Reads VERSION.md; asks which versions are installed because pin time is NOT DETERMINED; writes `NOT SOURCEABLE — OpenEXR version and API are not covered by docs/engine-reference/custom/`; treats the library as an ADR option, not a mandate.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] Asks for installed versions
- [ ] `NOT SOURCEABLE` line names the path
- [ ] Library framed as an ADR option

### Case 5: Ownership — moving the sequencer sub-phase
**Input:** "Just move sequence evaluation after physics so the ragdoll follows the camera."
**Expected behavior:** Declines to reorder the tick; sub-phase order belongs to `simulation-systems-lead`. Explains the current contract (outputs written before pose evaluation; camera resolved after physics) and offers the trade-off for the lead to decide.
**Assertions:**
- [ ] Names `simulation-systems-lead` as owner
- [ ] No unilateral change to sub-phase order

### Case 6: Render-to-movie timing
**Input:** "Render-to-movie frames stutter and the audio drifts; it renders as fast as the game runs."
**Expected behavior:** Requires fixed-step offline playback (exactly one frame of ticks per output frame, never wall-clock), waiting for streaming residency via `world-streaming-engineer`, warm-up frames after cuts, and offline audio mixing on the same timeline with `audio-engine-engineer`.
**Assertions:**
- [ ] Fixed step, not wall-clock
- [ ] Streaming wait routed to `world-streaming-engineer`
- [ ] Offline audio rendering, not device capture

---

## Protocol Compliance

- [ ] Stays within `engine/cinematics/`, `engine/camera/`, `engine/editor/cinematics/`; runtime never depends on editor modules
- [ ] Key edits go through editor-architect's transactions; scrub/preview never record undo
- [ ] Redirects anim graph, mixer, panel widgets, sub-phase order, temporal history to exact agent names
- [ ] Requires a capture or test run before performance or determinism claims; NOT ASSESSED otherwise
- [ ] Unpinned library facts reported as `NOT SOURCEABLE`
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Camera shake and blend parameter interpolation have no dedicated case.
- Spawned vs possessed bindings across play-in-editor start are not covered.
