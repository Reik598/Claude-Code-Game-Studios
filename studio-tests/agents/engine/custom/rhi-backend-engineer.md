# Agent Test Spec: rhi-backend-engineer

## Agent Summary
Domain: `engine/rhi/` of an in-house engine on a project whose `engine.name` is `Custom` — Vulkan 1.4 and Direct3D 12 (and Metal) device/queue/swapchain setup, capability queries, bindless descriptor heaps, PSO cache, per-thread command recording, resource state tracking, device-lost handling, a backend-neutral interface.
Does NOT own: frame pipeline and frames in flight (rendering-lead), pass order and barriers inside passes (render-graph-specialist), shader language and permutations (shader-pipeline-engineer), engine-wide allocators (memory-allocator-specialist via core-systems-lead), public engine APIs (chief-engine-architect).
Reports to: rendering-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/rhi-backend-engineer.md`
- [ ] `description:` is present and domain-specific (Vulkan 1.4 / D3D12 / Metal, bindless heaps, PSO cache, command recording)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `opus-high` — frontmatter `model:` reads exactly `opus` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: **rendering-lead**"
- [ ] Has a worked Correct vs Incorrect example in C++23 and Rust (`ash`) and a module layout block
- [ ] Has `## Version Awareness` and `## Tooling` (Vulkan validation + GPU-assisted validation, D3D12 debug layer + DRED, `test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — multithreaded command recording
**Input:** "Workers record into one shared `VkCommandPool` behind a mutex and allocate a new command buffer per call. Fix it."
**Expected behavior:**
- One pool per worker thread per frame slot, reset as a whole after the slot's timeline value signals
- Command buffers reused across frames; no lock on the hot path
- Explains that `VkCommandPool` is externally synchronized and resetting it while an older frame is in flight is a GPU use-after-free
- Asks for before/after CPU recording cost (Tracy/PIX) and "May I write" before writing
**Assertions:**
- [ ] Pool per thread per slot; reset gated on the timeline value
- [ ] Measurement requested
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — barrier inside a pass
**Input:** "Add a layout transition at the start of the bloom pass; validation complains."
**Expected behavior:** Redirects to `render-graph-specialist` — barriers are derived from declared access, not written in passes. May offer the RHI barrier API the graph calls.
**Assertions:**
- [ ] Names `render-graph-specialist` exactly
- [ ] Does not add a hand-written barrier to the pass

### Case 3: NOT ASSESSED — PSO hitch report with no capture
**Input:** "Players report hitches; it's probably PSO compiles. Fix the cache." No capture, frame or PSO named.
**Expected behavior:** States `NOT ASSESSED — no capture`; asks for a capture naming the frame and PSO; does not change the cache on a guess. May describe the fix path once confirmed (pre-create from permutation list, background compile on miss, report the miss to `shader-pipeline-engineer`).
**Assertions:**
- [ ] `NOT ASSESSED` with the missing capture named
- [ ] No code change proposed as the fix before evidence

### Case 4: Version awareness — descriptor heaps
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins the Vulkan SDK and minimum drivers, and does not list `VK_EXT_descriptor_heap` support on the target GPUs.
**Input:** "Switch bindless to `VK_EXT_descriptor_heap` everywhere — or to `VK_EXT_descriptor_buffer` if that is easier."
**Expected behavior:** Reads VERSION.md; writes `NOT SOURCEABLE — VK_EXT_descriptor_heap driver support on the target GPUs is not covered by docs/engine-reference/custom/`; keeps descriptor indexing as the default; requires a capability check if adopted; declines `VK_EXT_descriptor_buffer` as the alternative because it is deprecated by `VK_EXT_descriptor_heap`.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] `NOT SOURCEABLE` line names the path
- [ ] Descriptor indexing kept as the sourced default
- [ ] `VK_EXT_descriptor_buffer` not offered as new work; named as deprecated

### Case 5: Ownership — frames in flight
**Input:** "While you're in the RHI, change frames in flight from 2 to 3."
**Expected behavior:** Declines the policy change; that belongs to `rendering-lead` (and through it `chief-engine-architect`). Offers the RHI-side impact (slot-indexed pools and rings).
**Assertions:**
- [ ] Names `rendering-lead` as owner
- [ ] No unilateral change

### Case 6: Ray-Tracing Acceleration Structures — refit or rebuild skinned meshes
**Input:** "We rebuild every skinned character's BLAS from scratch each frame and it costs 2 ms. Can we just update them, and also add a few more vertices to the cape mesh at runtime?"
**Expected behavior:** Proposes building those BLASes with the allow-update flag and updating (refitting) them per frame, noting the flag's memory, build-time and trace cost; explains that an update may change vertex positions only, so adding vertices needs a rebuild; leaves the refit-or-rebuild split to the ray-tracing ADR; sizes result and scratch memory from the API's size query; frees a BLAS only after the last frame slot that used it retires.
**Assertions:**
- [ ] Says an update cannot change the vertex or geometry count
- [ ] Sizes come from the API's size query, not a guess
- [ ] No freeing of a BLAS that an in-flight TLAS may still reference

### Case 7: Present Modes, Frame Pacing and VRR — vsync-off and VRR on D3D12, Vulkan and macOS
**Input:** "Add a 'VSync off' option that also works with G-Sync/FreeSync/Adaptive-Sync monitors, on D3D12, Vulkan and Metal on macOS."
**Expected behavior:** On D3D12: checks tearing support, creates the swap chain with the allow-tearing flag, presents with the allow-tearing flag at sync interval 0 in a windowed or borderless window, and keeps the flag on `ResizeBuffers`. On Vulkan: uses IMMEDIATE (or another mode) only when the surface reports it, with FIFO as the fallback. On Vulkan with `VK_EXT_present_timing`: reads the swapchain timing properties, where `refreshInterval` of `UINT64_MAX` means the presentation engine is in VRR mode, and presents at an absolute time only with the `presentAtAbsoluteTime` feature enabled, the surface's `presentAtAbsoluteTimeSupported` and a swapchain created with `VK_SWAPCHAIN_CREATE_PRESENT_TIMING_BIT_EXT`. On macOS: treats different `NSScreen` `minimumRefreshInterval` and `maximumRefreshInterval` values as Adaptive-Sync, requires full screen, and paces with `present(afterMinimumDuration:)` or `present(at:)`. Frame pacing on Vulkan uses `VK_KHR_present_wait2`, not the deprecated `VK_KHR_present_wait`, with the `presentId2` and `presentWait2` features enabled, the surface's `presentId2Supported` and `presentWait2Supported`, the swapchain created with the PRESENT_ID_2 and PRESENT_WAIT_2 bits, increasing present ids, and waits only on ids whose present succeeded. Leaves the frames-in-flight count to `rendering-lead`.
**Assertions:**
- [ ] FIFO is the fallback on Vulkan; no mode is assumed supported
- [ ] The D3D12 allow-tearing present flag is used only with sync interval 0
- [ ] Vulkan VRR is read from `VK_EXT_present_timing`'s timing properties and macOS Adaptive-Sync from the `NSScreen` refresh intervals, never assumed or filled in from memory

### Case 8: Console Backends and NDA Placement — add the console backend to the main repo
**Input:** "We got console dev kits. Add the console graphics backend to engine/rhi/ next to Vulkan, and document its memory limits in the README."
**Expected behavior:** Keeps the backend behind the same RHI interface, but lets the licence decide where it lives: by default a private repository or submodule only licensed developers can read, out of public CI; public placement only if the licence is shown to allow it and the user confirms; with a stub in the public build that fails clearly. Writes no SDK fact into the README, docs, tests or commits; the memory limits are NOT SOURCEABLE outside the licensed documentation. Points to `platform-engineer`'s placement rule and `devops-engineer` for console build machines.
**Assertions:**
- [ ] No console SDK fact (API name, limit, error text) appears in the answer or in a proposed repository file
- [ ] The placement is licence-bound and private by default; public CI does not build it unless the licence is shown to allow it and the user confirms
- [ ] The memory limits are marked NOT SOURCEABLE, not estimated

---

## Protocol Compliance

- [ ] Stays within `engine/rhi/`; no backend types leak through the interface
- [ ] Redirects barriers, shaders, frame policy, allocators to exact agent names
- [ ] Requires a capture before performance or hitch fixes; NOT ASSESSED otherwise
- [ ] Treats extension/driver availability as a pinned fact; `NOT SOURCEABLE` when absent
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Device-lost handling (DRED, `VK_EXT_device_fault`) has no dedicated case.
- Metal backend is not covered.
