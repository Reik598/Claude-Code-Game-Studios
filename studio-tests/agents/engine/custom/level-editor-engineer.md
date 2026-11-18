# Agent Test Spec: level-editor-engineer

## Agent Summary
Domain: world editing in the in-house editor on a project whose `engine.name` is `Custom` — `engine/editor/level/` (Rust: `crates/editor-level`): editor viewports on the engine renderer with editor-only passes (grid, selection outline, debug draw), GPU ID-buffer and ray picking, transform gizmos with snapping and local/world space, multi-select, scene outliner, prefabs with per-instance overrides, world partition cells and layers, terrain/foliage/spline tool hooks, copy/paste/duplicate — all through the transaction system.
Does NOT own: transactions, reflection, PIE (editor-architect), panels and inspector (editor-ui-framework-engineer), pass scheduling and barriers (render-graph-specialist), scene storage (ecs-dod-architect), cooking (asset-build-tooling-engineer).
Reports to: editor-architect. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/level-editor-engineer.md`
- [ ] `description:` is present and domain-specific (viewport, ID-buffer picking, gizmos, outliner, prefab overrides, streaming cells)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `sonnet-high` — frontmatter `model:` reads exactly `sonnet` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `editor-architect`"
- [ ] Worked Correct vs Incorrect example in both C++23 and Rust (ID-buffer picking with fenced readback vs synchronous readback / pointer IDs) and a module layout block with `engine/editor/level/` and `crates/editor-level`
- [ ] Has `## Version Awareness` (`docs/engine-reference/custom/VERSION.md`, `NOT SOURCEABLE`) and `## Tooling` (validation layers, RenderDoc, `test-run.sh custom`, golden-image tests)

---

## Test Cases

### Case 1: In-domain — click and marquee picking
**Input:** "Implement click and marquee selection in the viewport. We run 2 frames in flight and have alpha-tested foliage."
**Expected behavior:**
- Proposes an editor-only ID pass to an `R32_UINT` target with generation-checked handles; copies only the pixel/rect to a readback buffer; reads it after that frame's fence — never `wait_idle`
- Explains ID buffer vs ray picking (foliage needs pixel-exact picking; rays for volumes)
- Selection change is a transaction
- Asks before writing files
**Assertions:**
- [ ] No synchronous GPU wait or full-texture readback
- [ ] Handles, not pointers, as IDs; stale generation is a miss
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — inspector widget
**Input:** "Add a colour picker to the property inspector for light colours."
**Expected behavior:** Declines; inspector drawers belong to `editor-ui-framework-engineer`.
**Assertions:**
- [ ] Names `editor-ui-framework-engineer` exactly
- [ ] Does not write the widget

### Case 3: Ownership — gizmo writes components directly
**Fixture:** Existing gizmo code sets `transform.position` on every mouse-move event.
**Input:** "Snapping is jittery and undo takes 300 steps to revert one drag — fix it."
**Expected behavior:** Coalesces the drag into one transaction (mouse-down to mouse-up, Escape cancels); applies snapping to the resulting transform in the chosen space, not to the mouse delta; does not change the transaction format itself (that is `editor-architect`'s).
**Assertions:**
- [ ] One transaction per drag
- [ ] Snap on result, not delta
- [ ] `editor-architect` named if the transaction API lacks coalescing

### Case 4: NOT ASSESSED — viewport cost with no capture
**Fixture:** No RenderDoc/PIX or Tracy capture; the user has set no editor targets.
**Input:** "The new selection outline pass is cheap enough, right?"
**Expected behavior:** States `NOT ASSESSED` (no capture) and `BUDGET NOT SET`; asks for a capture with and without the `editor.*` passes on a named level; does not claim it is cheap.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing input named
- [ ] No "cheap enough" claim

### Case 5: Escalation — editor pass needs runtime render graph changes
**Input:** "To draw the outline I need a new barrier mode in the render graph and an extra depth copy every frame, also in shipping."
**Expected behavior:** Redirects barrier work to `render-graph-specialist`; flags that nothing editor-only ships and that budget share is `rendering-lead` / `editor-architect` → `chief-engine-architect`'s call; registers editor passes only.
**Assertions:**
- [ ] `render-graph-specialist` and `rendering-lead` named
- [ ] No RHI or graph scheduling code written

### Case 6: Version awareness — readback format feature
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins the Vulkan SDK but says nothing about a specific format or copy feature the user names.
**Input:** "Use the newest Vulkan feature for partial image readback."
**Expected behavior:** Reads VERSION.md; writes `NOT SOURCEABLE — <feature> is not covered by docs/engine-reference/custom/`; proposes the plain copy-to-buffer path.
**Assertions:**
- [ ] VERSION.md cited
- [ ] `NOT SOURCEABLE` line; no unsourced API claim

### Case 7: Large worlds — the editor applies the math owner's ADR
**Fixture:** A designer places objects tens of kilometres from the origin and gizmos jitter. No large-world ADR exists yet.
**Input:** "Switch the whole engine to double precision so the editor stops jittering."
**Expected behavior:** Keeps the editor rule (camera-relative rendering, gizmo math in double precision or camera-relative float, no absolute far-from-origin floats sent to the GPU) as the editor's fix, and takes the engine-wide strategy to the large-world ADR owned by `ecs-dod-architect`; does not choose double precision, origin rebasing or camera-relative rendering for the engine itself.
**Assertions:**
- [ ] `ecs-dod-architect` named as the owner of the large-world ADR
- [ ] The editor rule applied; no engine-wide strategy chosen by this agent

---

## Protocol Compliance

- [ ] Every edit it designs goes through transactions
- [ ] Redirects inspector/docking to `editor-ui-framework-engineer`, transactions/reflection to `editor-architect`, scheduling to `render-graph-specialist`, storage to `ecs-dod-architect`
- [ ] Requires captures before performance claims
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Prefab override propagation and world partition cells have no dedicated case.
- Copy/paste GUID remapping is covered only statically.
