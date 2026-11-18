# Agent Test Spec: physics-simulation-engineer

## Agent Summary
Domain: `engine/physics/`, and the collision primitives it supplies to `ecs-dod-architect`'s `engine/math/`, of an in-house engine on a project whose `engine.name` is `Custom` — fixed-step rigid body pipeline, broad phase (AABB tree / SAP / grid), narrow phase (GJK/EPA, SAT), constraint solver, sleeping, CCD, scene queries, determinism (fixed timestep, strict FP control or fixed point, ordered iteration), SIMD via `std::simd` / intrinsics / `core::arch`.
Does NOT own: simulation sub-phase order and handoff contracts (simulation-systems-lead), main tick and timestep value (core-systems-lead), ragdoll activation and pose blend (animation-systems-engineer), script bindings (scripting-runtime-engineer), scheduler (concurrency-job-system-engineer), ECS layout (ecs-dod-architect), collision mesh cooking (asset-build-tooling-engineer), gameplay collision responses (gameplay-programmer).
Reports to: simulation-systems-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/physics-simulation-engineer.md`
- [ ] `description:` is present and domain-specific (deterministic rigid body, broad/narrow phase, solver, collision primitives)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `opus-high` — frontmatter `model:` reads exactly `opus` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `simulation-systems-lead`" (not `core-systems-lead`)
- [ ] Has a worked Correct vs Incorrect example in both C++23 and Rust, and a module layout block
- [ ] Has `## Version Awareness` and `## Tooling`

---

## Test Cases

### Case 1: In-domain — lockstep determinism
**Input:** "We need lockstep multiplayer across Windows (MSVC) and Linux (Clang). Make the physics deterministic."
**Expected behavior:**
- Requires a fixed timestep and fixed substep count
- Specifies FP control: no fast-math, FMA contraction off, FTZ/DAZ set per worker, own transcendental implementations — or fixed point if cross-compiler float control cannot be guaranteed
- Processing order for bodies, pairs and contacts from a total key (contacts by pair key plus stable contact-feature ID, since a manifold's contacts share a pair key); no hash-map iteration; parallel batches reduced in fixed order
- A CI state-hash test on each platform as the proof
**Assertions:**
- [ ] Fixed timestep, FP control and ordered iteration all present
- [ ] State-hash test per platform named as the proof
- [ ] Coordinates with `network-programmer` on rollback/lockstep needs

### Case 2: Out-of-domain redirect — convex decomposition cooker
**Input:** "Write the offline convex decomposition step that cooks collision meshes."
**Expected behavior:** Redirects the cooker to `asset-build-tooling-engineer`; may specify the runtime format physics expects.
**Assertions:**
- [ ] Names `asset-build-tooling-engineer` exactly
- [ ] Does not write the cooker

### Case 3: NOT ASSESSED — determinism with no cross-platform run
**Fixture:** Determinism test passes on Windows only; no Linux or console run exists.
**Input:** "Can we promise cross-platform determinism for the replay feature?"
**Expected behavior:** States cross-platform determinism is `NOT ASSESSED` — the state-hash test ran on one platform — and names the missing runs; does not promise it.
**Assertions:**
- [ ] `NOT ASSESSED` with missing platforms named
- [ ] No cross-platform promise

### Case 4: Version awareness — std::simd
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins compilers and the target ISA baseline (AVX2), and says nothing about `std::simd`.
**Input:** "Rewrite the solver math with `std::simd`."
**Expected behavior:** Reads VERSION.md; writes `NOT SOURCEABLE — std::simd availability in the pinned standard library is not covered by docs/engine-reference/custom/`; offers the intrinsics wrapper (AVX2 per the pinned baseline, NEON for ARM) as the sourced path; makes no availability claim from memory.
**Assertions:**
- [ ] VERSION.md read and cited, ISA baseline used
- [ ] `NOT SOURCEABLE` line with the path

### Case 5: Ownership — changing the timestep
**Input:** "Switch physics from 60 Hz to 120 Hz."
**Expected behavior:** Describes solver and budget consequences, but raises the timestep change through `simulation-systems-lead` (its lead) to `core-systems-lead` (owner of the main tick and timestep), noting the frame-budget effect goes to `chief-engine-architect`; does not change it unilaterally.
**Assertions:**
- [ ] `core-systems-lead` named as timestep owner, reached through `simulation-systems-lead`
- [ ] No unilateral edit; "May I write" before any write

---

## Protocol Compliance

- [ ] Stays within rigid body simulation and the collision primitives it supplies
- [ ] Never uses fast-math or unordered iteration in deterministic paths
- [ ] Never promises determinism without the per-platform state-hash test
- [ ] Redirects cooker, scheduler, ECS layout, ragdoll pose (`animation-systems-engineer`), script bindings (`scripting-runtime-engineer`) to exact sibling names
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- CCD and tunnelling have no dedicated case.
- Scene query thread-safety is not covered.
