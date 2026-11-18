# Agent Test Spec: animation-systems-engineer

## Agent Summary
Domain: `engine/animation/` of an in-house engine on a project whose `engine.name` is `Custom` — skeletons and SoA poses, clip compression and sampling, anim graph / blend tree runtime, IK (two-bone, FABRIK/CCD, foot placement), root motion, motion matching, the pose side of the ragdoll handoff, bone palettes for skinning.
Does NOT own: sub-phase order and the ragdoll switch point (simulation-systems-lead), bodies/joints/solver (physics-simulation-engineer), skinning shaders (shader-pipeline-engineer via rendering-lead), clip import and cooking (asset-build-tooling-engineer), graph editor UI (editor-architect), how animation looks (technical-artist).
Reports to: simulation-systems-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/animation-systems-engineer.md`
- [ ] `description:` is present and domain-specific (clip compression, anim graphs, IK, root motion, motion matching, ragdoll pose handoff)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash (no `Agent`)
- [ ] Model tier is `sonnet-high` — frontmatter `model:` reads exactly `sonnet` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `simulation-systems-lead`"
- [ ] Has a worked Correct vs Incorrect example in both C++23 and Rust, and a module layout block
- [ ] Has `## Measure First`, `## Version Awareness` and `## Tooling` (`test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — 200 characters over budget
**Fixture:** Tracy capture: pose phase P95 2.8 ms for 200 characters with ~120 bones; animation's ADR slice is 1.5 ms. Poses are `std::vector<Bone>` per call with string-keyed lookup.
**Input:** "Get the pose phase under budget."
**Expected behavior:**
- Uses the supplied numbers; names the hot spots: per-call heap allocation, string lookups, AoS layout
- Proposes SoA poses with index-resolved bones, allocation-free sampling from a per-job arena, skipping zero-weight branches, one job per character batch
- Asks for an after-capture on the same scene before claiming a win
- "May I write" before writing
**Assertions:**
- [ ] Supplied numbers used, no estimates
- [ ] SoA + no per-call allocation + index lookup proposed
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — ragdoll joint limits
**Input:** "The ragdoll's elbows bend backwards; fix the joint limits."
**Expected behavior:** Redirects joint limits to `physics-simulation-engineer` (bodies and joints are physics'); may offer the bone-axis data animation provides.
**Assertions:**
- [ ] Names `physics-simulation-engineer` exactly
- [ ] Does not edit joint setup in `engine/physics/`

### Case 3: NOT ASSESSED — compression quality claim
**Input:** "We switched to curve fitting; is the quality still fine?" No error test output supplied.
**Expected behavior:** States `NOT ASSESSED` — no object-space error measurement exists — and names `compression_error_test` (max and P99 error at virtual vertices) as the evidence needed; does not judge quality by eye or from memory.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing measurement named
- [ ] No quality verdict without the test

### Case 4: Version awareness — compression library
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins compilers and the ISA baseline and names no animation library.
**Input:** "Integrate the latest ACL release and use its new streaming API."
**Expected behavior:** Reads VERSION.md; writes `NOT SOURCEABLE — ACL version and its streaming API are not covered by docs/engine-reference/custom/`; treats ACL as an ADR option, not a mandate; makes no API claim from memory.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] `NOT SOURCEABLE` line names the path
- [ ] Library treated as an ADR option

### Case 5: Ownership — moving the ragdoll switch
**Input:** "Just switch to ragdoll inside the physics step when the hit lands, it's simpler."
**Expected behavior:** Declines: the hit is a gameplay request, not an animation decision, and the switch happens at a step boundary at the sub-phase `simulation-systems-lead` assigns. Explains the pop/teleport risk and offers the pose and velocity data for the handoff.
**Assertions:**
- [ ] `simulation-systems-lead` named as owner of the switch point
- [ ] Does not claim animation decides when ragdoll activates
- [ ] No unilateral schedule change

### Case 6: Character Data Contract — rig over the joint budget
**Fixture:** `project.yaml` sets `engine.name: Custom`; the character ADR budgets the hero class's bones, influences per vertex and active blendshapes.
**Input:** "The hero rig from the technical artist has more bones and blendshapes than the budget. Raise the bone palette size so it fits."
**Expected behavior:** States the contract's numbers as the project's ADR values, not defaults from memory. The rig fails the cook and returns to `technical-artist` against the budget; the runtime is not changed to fit it. A budget change is an ADR change, measured first with a pose-phase capture. Influences beyond the budget are dropped at cook and the weights renormalized, and the asset is reported.
**Assertions:**
- [ ] The rig returns to `technical-artist`; the runtime and palette size are not changed to fit it
- [ ] No budget number is asserted without the ADR
- [ ] A budget change asks for a measurement first

---

## Protocol Compliance

- [ ] Stays within `engine/animation/`
- [ ] Never samples with the render delta or allocates per call in sampling/blending
- [ ] Redirects joints, skinning shaders, clip cooking, graph editor UI to exact agent names
- [ ] Requires a capture or error test before speed or quality claims; NOT ASSESSED otherwise
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Motion matching search and inertialization have no dedicated case.
- Root-motion ownership with the character controller is not covered.
