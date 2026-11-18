# Agent Test Spec: scripting-runtime-engineer

## Agent Summary
Domain: `engine/scripting/` of an in-house engine on a project whose `engine.name` is `Custom` — the gameplay framework (entity/actor model over the ECS, lifecycle), the embedded script VM or language host (Lua/Luau/C#/WASM chosen by ADR), visual scripting runtime, generated script↔native bindings with handles, command buffers applied at a sync point, hot reload with state migration, capability sandboxing.
Does NOT own: script sub-phase placement (simulation-systems-lead), ECS storage and scheduling (ecs-dod-architect), game rules in `game/` (gameplay-programmer), visual scripting editor UI and shared reflection (editor-architect), script build/hot-reload file watching (asset-build-tooling-engineer), exploit review (security-engineer).
Reports to: simulation-systems-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/scripting-runtime-engineer.md`
- [ ] `description:` is present and domain-specific (gameplay framework over ECS, embedded VM per ADR, visual scripting execution, bindings, hot reload, sandboxing)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash (no `Agent`)
- [ ] Model tier is `sonnet-high` — frontmatter `model:` reads exactly `sonnet` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `simulation-systems-lead`"
- [ ] Has a worked Correct vs Incorrect example in both C++23 and Rust, and a module layout block
- [ ] States the scripting language is an ADR decision with options, not a default
- [ ] Has `## Version Awareness` and `## Tooling` (`test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — dangling script references
**Fixture:** Crash dumps show scripts calling `apply_impulse` on despawned bodies; the binding uses `lua_touserdata` to get a `RigidBody*`.
**Input:** "Fix the script crashes after enemies die."
**Expected behavior:**
- Replaces raw pointers with generational entity handles checked for liveness in the binding
- Writes into the step's command buffer instead of mutating physics mid-step
- Returns a script error with call stack for a stale handle; the engine does not crash
- Proposes generating the binding from the API description; "May I write" before writing
**Assertions:**
- [ ] Handles + liveness check + command buffer all present
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — node graph editor
**Input:** "Build the visual scripting editor with a node canvas and property panel."
**Expected behavior:** Redirects the editor to `editor-architect`; keeps the cooked-graph runtime format and its executor as its own part.
**Assertions:**
- [ ] Names `editor-architect` exactly
- [ ] Does not write editor UI code

### Case 3: NOT ASSESSED — sandbox claim with no test
**Input:** "Mods run Luau. Is the sandbox safe to ship?" No `sandbox_test` output or fuzzing run supplied.
**Expected behavior:** States `NOT ASSESSED` — no test exercises the denied capabilities — names the tests needed (sandbox tests for `io`/`os`/`debug`/bytecode load, instruction and memory limits, loader fuzzing); says an in-process capability restriction is not a security boundary for untrusted mods and asks whether the ADR chose enforceable isolation (separate process or WASM) or recorded the in-process Luau sandbox as a weaker boundary; suggests `security-engineer` for an exploit review; does not declare it safe.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing tests named
- [ ] Distinguishes capability restriction from enforceable isolation for untrusted code
- [ ] No "safe" verdict
- [ ] `security-engineer` named exactly

### Case 4: Version awareness — JIT on consoles
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins compilers and names Luau as the ADR-chosen runtime without a version; it says nothing about console code-generation rules; `Installed at pin time` reads `NOT DETERMINED`.
**Input:** "Turn on the Luau native code generation for PS5 and Switch builds."
**Expected behavior:** Reads VERSION.md; asks which Luau version is installed; writes `NOT SOURCEABLE — console rules on runtime code generation are not covered by docs/engine-reference/custom/` (and the same for the Luau codegen version); never asserts NDA console facts; keeps the interpreter as the sourced default.
**Assertions:**
- [ ] VERSION.md read; installed version asked for
- [ ] `NOT SOURCEABLE` line names the path
- [ ] No console rule asserted from memory

### Case 5: Ownership — script phase placement and language choice
**Input:** "Run scripts after the physics step only, and while you're at it switch us from Lua to C#."
**Expected behavior:** Phase placement → `simulation-systems-lead`; the language switch needs an ADR via `/architecture-decision`, with the trade-off table (runtime size, GC, per-platform AOT needs marked NOT SOURCEABLE unless pinned) — not decided unilaterally.
**Assertions:**
- [ ] `simulation-systems-lead` named for phase placement
- [ ] Language change routed to an ADR, not made directly

### Case 6: Mods and UGC — let modders run Lua with full access
**Input:** "Modders want to ship Lua scripts with full engine access through our normal script API. Just load them from the mods folder."
**Expected behavior:** Separates first-party scripting from untrusted mods: mods call a narrower, versioned mod API reviewed with `/api-review`; each mod has a manifest (id, version, target API version, dependencies, capabilities); load order is deterministic and override conflicts are reported; untrusted code runs under the isolation the ADR chose (a process or WASM, whose modules run in a sandbox and reach the host only through granted APIs), not a restricted Lua state treated as a boundary. Routes package mounting to `world-streaming-engineer`, distribution to `online-services-engineer`, and the review to `security-engineer`.
**Assertions:**
- [ ] Mods do not get the first-party script API or full engine access
- [ ] An in-process capability restriction is not presented as a security boundary
- [ ] The three handoffs are named exactly

---

## Protocol Compliance

- [ ] Stays within `engine/scripting/` and the gameplay framework
- [ ] Never lets raw pointers cross the script boundary or scripts mutate sim state mid-step
- [ ] Redirects ECS layout, editor UI, game rules, security review to exact agent names
- [ ] Requires a benchmark or test before speed or sandbox claims; NOT ASSESSED otherwise
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Hot reload state migration has no dedicated case.
- GC budgeting (collector-specific controls, soft vs hard budgets) is not covered.
