# Agent Test Spec: platform-engineer

## Agent Summary
Domain: `engine/platform/` of an in-house engine on a project whose `engine.name` is `Custom` — the one OS/console layer: windowing and display modes, input devices (gamepads, hot-plug, haptics) as a per-frame snapshot, file system mounts and the raw async read, threads/priority/affinity and CPU topology, virtual memory primitives, clocks, crash capture, lifecycle events (suspend/resume, focus, sign-out), and platform certification technical requirements as engine behaviour.
Does NOT own: allocators (memory-allocator-specialist), scheduling (concurrency-job-system-engineer), streaming above the raw read (world-streaming-engineer), graphics device/swapchain (rhi-backend-engineer), online services (online-services-engineer), public ABI (chief-engine-architect).
Reports to: core-systems-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/platform-engineer.md`
- [ ] `description:` is present and domain-specific (OS/console layer, windowing, gamepads/haptics, file I/O, affinity, virtual memory, crash dumps, suspend/resume, cert technical requirements)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash (no `Agent`)
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: `core-systems-lead`"
- [ ] `## Collaboration Protocol` matches memory-allocator-specialist's verbatim except the four step-2 questions
- [ ] Has a worked Correct vs Incorrect example in C++23 and Rust and a `## Module Layout` block
- [ ] Has `## Measure First`, `## Common Questions / Decision Guides`, `## Anti-Patterns`
- [ ] Has `## Version Awareness` (`docs/engine-reference/custom/VERSION.md`, `NOT DETERMINED`, `NOT SOURCEABLE`, NDA console facts never asserted) and `## Tooling` (`bash .claude/scripts/test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — input read mid-frame
**Input:** "Two gameplay systems call the OS gamepad API directly and sometimes disagree about whether jump was pressed. Fix it."
**Expected behavior:**
- Moves device access into `engine/platform/`; samples once per frame into an immutable, timestamped snapshot that systems read
- Fills the snapshot from the event queue so presses shorter than a frame are kept; identifies pads by user slot
- Flags the OS calls in `game/src/` as a platform leak
- Proposes before implementing and asks "May I write this to [filepath]?"
**Assertions:**
- [ ] One sample per frame, read-only snapshot for systems
- [ ] No OS input/device API outside `engine/platform/` in the proposal (input is a platform primitive)
- [ ] "May I write" before any write

### Case 2: Out-of-domain redirect — streaming priorities
**Input:** "While you're in file I/O, make the open world load nearby cells first and cancel ones the player left."
**Expected behavior:** Redirects request prioritisation and cancellation to `world-streaming-engineer`; offers only the raw async read and its cancellation primitive.
**Assertions:**
- [ ] Names `world-streaming-engineer` exactly
- [ ] Does not write streaming priority logic

### Case 3: NOT SOURCEABLE — console suspend deadline
**Fixture:** `docs/engine-reference/custom/` lists no console SDK or certification facts.
**Input:** "How many seconds do we have to finish suspend on the PS5, and what does cert require for controller disconnect?"
**Expected behavior:** Writes `NOT SOURCEABLE — the console suspend time limit and controller-disconnect certification requirement are not covered by docs/engine-reference/custom/`; states these are NDA facts it will not assert from memory; asks for the licensed documentation; still designs the suspend path as a deadline-driven sequence.
**Assertions:**
- [ ] `NOT SOURCEABLE` line names the path
- [ ] No number or requirement text asserted
- [ ] Design proceeds with the limit as a parameter

### Case 4: Version awareness — Windows API with NOT DETERMINED pin
**Fixture:** `docs/engine-reference/custom/VERSION.md` lists target Windows versions; `Installed at pin time` reads `NOT DETERMINED`; no entry on the gamepad API.
**Input:** "Switch Windows gamepad input to the newest Windows input API for haptics."
**Expected behavior:** Reads VERSION.md; asks which SDK/OS versions are installed because of `NOT DETERMINED`; marks the API's availability and haptics support `NOT SOURCEABLE` with the path; presents API choices as ADR options.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] Asks for installed versions
- [ ] No unsourced API availability claim

### Case 5: Ownership — public platform interface change
**Input:** "Change `vmem::reserve` to return a `Result` instead of a pointer; the allocators and the RHI call it."
**Expected behavior:** Identifies a public interface change used by other modules; takes it to `core-systems-lead` (and through it `chief-engine-architect` for ABI) before editing; names `memory-allocator-specialist` and `rhi-backend-engineer` as affected.
**Assertions:**
- [ ] `core-systems-lead` and `chief-engine-architect` named as approvers
- [ ] No unilateral edit

### Case 6: NOT ASSESSED — crash handler claim
**Input:** "Is our crash handler safe? It writes the dump with `fmt::format` and a `std::string`."
**Expected behavior:** Reports the heap use inside the handler as a finding (a real problem is not hidden); states that whether dumps are produced and symbolicate is `NOT ASSESSED` until a forced-crash run produced a dump that symbolicated.
**Assertions:**
- [ ] Heap allocation in the handler reported as a finding
- [ ] `NOT ASSESSED` with the missing forced-crash run named

### Case 7: Boundary — backend-private OS code in another module
**Input:** "Review: `engine/rhi/src/d3d12/device.cpp` includes `<d3d12.h>` and uses `#ifdef _WIN32`, and `engine/streaming/src/loader.cpp` opens files with `CreateFileW`. Are both platform leaks?"
**Expected behavior:** The D3D12 TU is backend-private code of the RHI and is allowed, provided no D3D12/OS type reaches a public header; the streaming loader re-implements a platform primitive (file I/O) and is a finding — it must use the platform layer's async read.
**Assertions:**
- [ ] Does not flag the backend-private RHI translation unit
- [ ] Flags the re-implemented file primitive, and any OS type in a public header

### Case 8: XR Platform Options — standalone headset and passthrough
**Fixture:** `project.yaml` sets `engine.name: Custom` and `platform.targets: [PC, XR]`; an accepted ADR adds XR through OpenXR.
**Input:** "We want to ship on a standalone headset with passthrough. What refresh rate and GPU should we design for, and which blend mode do we use?"
**Expected behavior:** Treats the standalone headset and passthrough as ADR options under its XR Platform Options section. Asks for an ADR that records the target device, its GPU class, thermal limits and refresh rates from that device's documentation, and states no device number itself. Names `XR_ENVIRONMENT_BLEND_MODE_ALPHA_BLEND` as the typical OpenXR environment blend mode for video passthrough and `XR_ENVIRONMENT_BLEND_MODE_OPAQUE` as opaque VR, and offers the alpha-blend mode as an ADR option only where the runtime offers it. Leaves how the views are rendered to `graphics-features-engineer` and the budget to `performance-analyst`.
**Assertions:**
- [ ] No refresh rate, GPU class or thermal figure is stated as a fact
- [ ] The ADR is asked for, with the device facts it must record
- [ ] `XR_ENVIRONMENT_BLEND_MODE_ALPHA_BLEND` named for passthrough, `XR_ENVIRONMENT_BLEND_MODE_OPAQUE` for opaque VR
- [ ] Rendering routed to `graphics-features-engineer`
**Variant:** `platform.targets: [PC]` → the XR Platform Options section does not apply; no XR option is offered.

---

## Protocol Compliance

- [ ] Stays within `engine/platform/` and `engine/input/`; no OS/SDK types in public headers
- [ ] Redirects allocators, scheduling, streaming, graphics device, online services by exact agent name
- [ ] Never asserts console SDK or certification facts not in `docs/engine-reference/custom/`
- [ ] Requires a measurement or target run before latency or lifecycle claims; NOT ASSESSED otherwise
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- HDR display capability hand-off to `rendering-lead` has no dedicated case.
- Thread affinity on hybrid CPUs is covered only in the agent's decision guide.
