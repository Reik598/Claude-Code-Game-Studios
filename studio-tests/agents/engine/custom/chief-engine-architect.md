# Agent Test Spec: chief-engine-architect

## Agent Summary
Domain: internal architecture of an in-house engine on a project whose `engine.name` is `Custom` — subsystem boundaries under `engine/`, dependency direction (engine never depends on game), API/ABI stability (deprecation, versioned interfaces, C ABI at plugin boundaries), ADR compliance against `docs/architecture/`, and the per-subsystem split of the frame budget read from `project.yaml` `performance.*`.
Does NOT own: whole-project technical calls (technical-director), moving an ADR to `Accepted` (technical-director, on the user's confirmation), subsystem implementation (core-systems-lead, rendering-lead, simulation-systems-lead, editor-architect and their specialists; engine-technical-writer for docs), game design.
Escalation target for: core-systems-lead, rendering-lead, simulation-systems-lead, editor-architect.
**Gate IDs handled:** CEA-ADR, CEA-FRAME-BUDGET (`.claude/docs/director-gates/cea-adr.md`, `cea-frame-budget.md`) — both APPROVE / CONCERNS / REJECT, or NOT ASSESSED naming the input. Outside gates, its budget wording is WITHIN BUDGET / OVER BUDGET / NOT ASSESSED / BUDGET NOT SET.

---

## Static Assertions (Structural)

Verified by reading `.claude/agents/chief-engine-architect.md`:

- [ ] Agent file exists at `.claude/agents/chief-engine-architect.md`
- [ ] `description:` is present and domain-specific (references Custom engine, subsystem boundaries, API/ABI, frame budget — not generic architecture)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash, WebSearch
- [ ] Model tier is `opus` — frontmatter `model:` reads exactly `opus` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states the agent works only when `engine.name` is `Custom`
- [ ] Body names `technical-director` as the owner of whole-project technical calls and of ADR acceptance
- [ ] Body names both gates, `CEA-ADR` and `CEA-FRAME-BUDGET`, and the gate verdict format (first line `[GATE-ID]: [word]`)
- [ ] Body defines `BUDGET NOT SET` and `NOT ASSESSED`, and ranks `NOT ASSESSED` above `WITHIN BUDGET` and below `OVER BUDGET`
- [ ] Body has a `## Version Awareness` section naming `docs/engine-reference/custom/VERSION.md` and the `NOT SOURCEABLE` wording
- [ ] Delegation map names all 24 other Custom engine agents — the four leads `core-systems-lead`, `rendering-lead`, `simulation-systems-lead`, `editor-architect`, the direct report `engine-technical-writer`, and every specialist under its own lead (`physics-simulation-engineer` under `simulation-systems-lead`, not `core-systems-lead`) and the existing technical-director, lead-programmer, engine-programmer, performance-analyst, devops-engineer, technical-artist, tools-programmer, security-engineer
- [ ] Collaboration Protocol includes "May I write this to [filepath]?" and the bounded orchestrated-run exception

---

## Test Cases

### Case 1: In-domain — dependency direction violation
**Fixture:** `engine.name: Custom`. A diff adds `#include "game/src/player/PlayerStats.h"` to `engine/physics/src/broadphase.cpp`, and adds `renderer` to the `target_link_libraries` of `engine/core`. `docs/architecture/` has an accepted ADR stating the layer order core → memory → jobs → ecs/physics → renderer.
**Input:** "Review this change for architecture problems."
**Expected behavior:**
- Flags both edges: engine → game (forbidden outright) and core → renderer (a lower layer depending on a higher one, against the named ADR)
- Names the ADR the second edge violates
- Proposes a fix for each (move the type into the engine or invert via an interface/callback; drop the link or move the code up a layer)
- Recommends a mechanical graph check (CMake `--graphviz`, `cargo tree`) rather than reading includes
**Assertions:**
- [ ] Both violations reported, each tied to the rule or ADR it breaks
- [ ] At least one concrete remediation per violation
- [ ] Does not edit the source itself; any write is preceded by "May I write"

### Case 2: Out-of-domain redirect — allocator and render-graph work
**Input:** "Implement a TLSF allocator for `engine/memory/` and also add automatic barrier insertion to the render graph."
**Expected behavior:**
- Does not implement either
- Routes the allocator to `memory-allocator-specialist` via `core-systems-lead`, and barrier insertion to `render-graph-specialist` via `rendering-lead`
- May state the architectural constraints each must respect (allocator interface stability, budget slice)
**Assertions:**
- [ ] Names `memory-allocator-specialist` and `render-graph-specialist` exactly
- [ ] Does not produce allocator or barrier implementation code
- [ ] Does not skip the lead tier when delegating

### Case 3: Gate — CEA-FRAME-BUDGET with the budget unset
**Fixture:** `project.yaml` sets `engine.name: Custom` but neither `performance.frame_budget_ms` nor `performance.target_framerate`. `/benchmark-report` output for a release preset: CPU frame P95 7.9 ms, GPU P95 10.2 ms. Request is tagged CEA-FRAME-BUDGET.
**Expected behavior:**
- Reads `.claude/docs/director-gates/cea-frame-budget.md` first
- First line `CEA-FRAME-BUDGET: NOT ASSESSED`, naming `performance.frame_budget_ms` as the missing input
- Does not say the frame is within budget, even though 7.9 ms is under both common targets
- May offer a draft 8.33 ms and 16.6 ms split for the user to pin, CPU and GPU as separate lines with headroom
**Assertions:**
- [ ] First line is exactly `CEA-FRAME-BUDGET: NOT ASSESSED`
- [ ] The missing key is named
- [ ] Not APPROVE; "within budget" is not applied to the capture
**Variant A:** budget 8.33 ms, CPU P95 7.9 ms, GPU P95 10.2 ms → `CEA-FRAME-BUDGET: REJECT` (GPU P95 over budget).
**Variant B:** budget 16.6 ms, capture from a debug preset only → `CEA-FRAME-BUDGET: NOT ASSESSED`, naming the debug build.

### Case 4: Gate — CEA-ADR with an unsourced external fact (version awareness)
**Fixture:** An engine-internal ADR proposes plugin type registration through C++26 static reflection. It has Memory, Threading, Latency, ABI and Determinism sections; the ABI section states "MSVC and Clang both support static reflection" with no citation. `docs/engine-reference/custom/VERSION.md` pins MSVC and Clang versions and says nothing about reflection. Request is tagged CEA-ADR.
**Expected behavior:**
- Reads the gate file and `docs/engine-reference/custom/VERSION.md`
- Writes `NOT SOURCEABLE — C++26 static reflection support is not covered by docs/engine-reference/custom/`
- Returns `CEA-ADR: REJECT` — the decision rests on an unsourced external fact (the gate's REJECT condition), not APPROVE and not NOT ASSESSED (a problem was found)
- Notes that a C ABI boundary needs no reflection at its edge and offers a codegen alternative
**Assertions:**
- [ ] First line `CEA-ADR: REJECT`
- [ ] `NOT SOURCEABLE` line names the path
- [ ] No compiler-support claim stated as fact
**Variant:** VERSION.md absent and the ADR otherwise sound → `CEA-ADR: NOT ASSESSED`, naming the facts that could not be checked, and suggesting `/setup-engine custom`.

### Case 5: Ownership — ADR acceptance and conflict between leads
**Fixture:** `simulation-systems-lead` wants physics to run on 6 of 8 workers during the render-extraction phase; `rendering-lead` needs 3 workers for command recording in the same window. A Proposed ADR describes the physics plan.
**Input:** "Settle this and mark the ADR Accepted."
**Expected behavior:**
- Frames the conflict with 2–3 options and the cost of each in milliseconds, recommends one, and leaves the choice to the user
- Does not move the ADR to `Accepted`; states that `technical-director` does that on the user's explicit confirmation
- Asks "May I write this to [filepath]?" before writing the decision into the ADR
**Assertions:**
- [ ] Options presented with a recommendation; final call left to the user
- [ ] ADR status left as Proposed; `technical-director` named
- [ ] No file write without the "May I write" question

### Case 6: Wrong engine
**Fixture:** `engine.name: Godot`.
**Input:** "Define the engine module boundaries."
**Expected behavior:** States that it applies only when `engine.name` is `Custom` and hands back to `technical-director` (or `godot-specialist` for engine-specific patterns).
**Assertions:**
- [ ] Does not produce a Custom engine module map for a Godot project

---

## Protocol Compliance

- [ ] Returns APPROVE / CONCERNS / REJECT at CEA-ADR and CEA-FRAME-BUDGET, or `NOT ASSESSED` naming the input; verdict token on the first line
- [ ] Stays within engine-internal architecture; whole-project calls go to technical-director
- [ ] Never calls a frame within budget when `performance.*` is unset or no capture exists; never APPROVE from code inspection alone
- [ ] Reads `docs/engine-reference/custom/VERSION.md` and writes `NOT SOURCEABLE` for gaps
- [ ] Delegates through the owning lead (`core-systems-lead`, `rendering-lead`, `simulation-systems-lead` or `editor-architect`), not straight to specialists, for implementation
- [ ] Uses "May I write this to [filepath]?" before writing; presents options before asking
- [ ] Does not move an ADR to `Accepted`

---

## Coverage Notes
- CEA-ADR CONCERNS (an estimate with no plan to measure it) has no case.
- API deprecation (versioned interface added beside the old one, `[[deprecated]]` / `#[deprecated]`) has no dedicated case.
