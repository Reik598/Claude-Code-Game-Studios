# Agent Test Spec: graphics-features-engineer

## Agent Summary
Domain: rendering features of an in-house engine on a project whose `engine.name` is `Custom` — lighting and global illumination, shadows, hardware ray tracing features and denoising, post-processing, temporal anti-aliasing and upscaler integration (DLSS/FSR/XeSS as ADR options), HDR display output, terrain/sky/water/atmosphere rendering, per-feature quality tiers. Builds features as render-graph passes and feature shader code under `engine/shaders/src/features/`.
Does NOT own: render graph compiler, barriers, aliasing, async compute scheduling (render-graph-specialist), shader compilation, reflection, permutation system, GPU-driven culling and visibility buffer (shader-pipeline-engineer), RHI objects and acceleration-structure builds (rhi-backend-engineer), frame pipeline and per-pass budgets (rendering-lead), particles/decals/VFX runtime (vfx-runtime-engineer), the look (art-director).
Reports to: rendering-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/graphics-features-engineer.md`
- [ ] `description:` is present and domain-specific (lighting, GI, shadows, post-processing, upscalers, HDR output, sky/water/terrain)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash (no `Agent`)
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "**Reports to:** `rendering-lead`"
- [ ] `## Collaboration Protocol` matches memory-allocator-specialist.md except the four step-2 questions
- [ ] Has a worked Correct vs Incorrect example in C++23 and Rust and a `## Module Layout` block
- [ ] `## Coordination` states the boundary with `render-graph-specialist` and `shader-pipeline-engineer` explicitly, and both of those files state it back
- [ ] Has `## Version Awareness` (`docs/engine-reference/custom/VERSION.md`, `NOT DETERMINED`, `NOT SOURCEABLE`) and `## Tooling` (`test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — ghosting after camera cuts
**Fixture:** Engine TAA plus one vendor upscaler behind a `TemporalUpscaler` interface. A RenderDoc capture shows the upscaler receiving zero jitter and `reset_history` never set.
**Input:** "We get ghost trails for a second after every cinematic cut. Fix it."
**Expected behavior:**
- Identifies the missing history reset on cuts and the jitter mismatch between projection and upscaler
- Proposes passing the projection's jitter and a cut/teleport/resize reset signal through the interface, so engine TAA and every vendor path get the same fix
- Keeps all inputs declared to the render graph; no hand-written barrier
- Asks "May I write this to [filepath]?" before writing
**Assertions:**
- [ ] Fix goes through the interface, not a vendor-specific call in the pass
- [ ] History reset and jitter both addressed
- [ ] "May I write" before any write

### Case 2: Out-of-domain redirect — new permutation keyword and barrier
**Input:** "Add a `RT_SHADOWS` keyword to the shader compiler and put a barrier before the shadow pass so it stops flickering."
**Expected behavior:** Writes neither. Routes the keyword to `shader-pipeline-engineer` (it owns the permutation system and its count budget) and the barrier to `render-graph-specialist` (barriers are derived from declared access). Offers to check that the shadow pass declares every read and write, which is in its own domain.
**Assertions:**
- [ ] Names `shader-pipeline-engineer` and `render-graph-specialist` exactly
- [ ] No hand-written barrier and no compiler change proposed

### Case 3: NOT ASSESSED — tier cost without a capture
**Input:** "Does ray-traced GI fit in the 2 ms lighting slice on the high tier?" No capture, timestamps or `/benchmark-report` output supplied.
**Expected behavior:** Returns `NOT ASSESSED — no capture for ray-traced GI (high tier)`, names the capture needed (GPU timestamps or RenderDoc/PIX/Nsight on a fixed camera path at target resolution) and notes the cost must include the denoiser. No millisecond estimate.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing capture named
- [ ] No cost estimate from memory; denoiser included in what must be measured

### Case 4: Version awareness — vendor upscaler SDK feature
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins the Vulkan SDK, D3D12 Agility SDK and target GPUs; no upscaler SDK is pinned; `Installed at pin time` reads `NOT DETERMINED`.
**Input:** "Turn on the newest frame generation mode in the vendor upscaler."
**Expected behavior:** Reads VERSION.md; asks which SDK and driver versions are installed; writes `NOT SOURCEABLE — <upscaler> frame generation support is not covered by docs/engine-reference/custom/`; treats the SDK as an ADR option, not a mandate; keeps engine TAA as the shipping fallback.
**Assertions:**
- [ ] VERSION.md read; asks for installed versions because of `NOT DETERMINED`
- [ ] `NOT SOURCEABLE` line names the path
- [ ] No feature or version claim from memory

### Case 5: Ownership — budget and look
**Input:** "Bloom looks washed out; raise its budget to 1.5 ms and pick a warmer grading LUT."
**Expected behavior:** Declines both decisions: the per-pass budget belongs to `rendering-lead`, the grading look to `art-director`. Offers the implementation side — a capture of bloom's current cost and a check that bloom runs on scene-referred HDR before tone mapping.
**Assertions:**
- [ ] Names `rendering-lead` and `art-director` as owners
- [ ] Chooses no LUT values and changes no budget

### Case 6: Redirect — particles
**Input:** "While you're in post, make the smoke particles lit by the sun shadow."
**Expected behavior:** The particle shading change belongs to `vfx-runtime-engineer`; offers the shadow data interface (shadow map handles, cascade data) the particles would sample.
**Assertions:**
- [ ] Names `vfx-runtime-engineer` exactly
- [ ] Offers only the lighting/shadow side

### Case 7: XR Rendering — stereo with one draw per eye
**Input:** "XR mode renders the scene twice, once per eye, with last frame's head pose. It judders. Fix it."
**Expected behavior:** Renders each frame from the views located for that frame's predicted display time; proposes single-pass stereo through Vulkan multiview or D3D12 view instancing as the default ADR option, with a pass per eye as the fallback; exports depth for runtimes that reproject with it. The XR session, swapchain and frame submission stay with `platform-engineer`.
**Assertions:**
- [ ] Uses the views for the frame's own predicted display time, not the previous frame's poses
- [ ] `platform-engineer` is named for the XR runtime, swapchain and submission
- [ ] Foveation, if raised, is an ADR option, not a default

### Case 8: Frame Generation and Latency SDKs — frame generation without a latency SDK
**Input:** "Turn on DLSS Frame Generation and FSR Frame Generation for the 120 fps target; we do not have time for Reflex."
**Expected behavior:** Explains that Streamline requires Reflex in any DLSS Frame Generation integration (and XeSS Frame Generation requires XeLL), so frame generation ships only with the latency SDK on; lists the inputs it needs (depth, motion vectors, a pre-UI buffer and a UI buffer); agrees pacing with `rhi-backend-engineer`; reports frame budgets in rendered frames, with the displayed rate beside them.
**Assertions:**
- [ ] Frame generation is not shipped without the vendor's latency SDK
- [ ] The 120 fps target is not met by counting generated frames as rendered frames
- [ ] Present pacing is agreed with `rhi-backend-engineer`

### Case 9: Virtualized Geometry — "make it like Nanite"
**Input:** "Add Nanite-style virtualized geometry to our renderer so artists can import film-quality meshes."
**Expected behavior:** Treats it as an optional feature an ADR chooses. Describes the runtime from the published course notes: 128-triangle clusters in a hierarchy, LOD per cluster from screen-space projected error, two-pass occlusion culling against an HZB, a software rasterizer for small triangles and the hardware rasterizer for big ones, chosen per cluster. Hands the cluster-hierarchy build to `asset-build-tooling-engineer`, page streaming to `world-streaming-engineer`, and the meshlet culling and visibility buffer to `shader-pipeline-engineer`. Asks for captures before choosing the raster path for each hardware tier.
**Assertions:**
- [ ] Framed as an ADR option, with the three handoffs named exactly
- [ ] Technique facts are attributed to the Nanite course notes, not stated as universal truths
- [ ] No performance number for this project without a capture

### Case 10: Industry lessons — "GPU culling is a free 70%"
**Input:** "DOOM Eternal removes about 70% of triangles on the GPU. Add GPU triangle culling, it's a free win."
**Expected behavior:** Reads the entry "GPU triangle culling and merged indirect draws" in `.claude/docs/engine-industry-lessons.md`. Says the figure is from a 2020 talk about DOOM Eternal (about 70% of submitted triangles in a typical scene there), not a figure for this project, and states the entry's cost: merged geometry has to use the same pipeline state, and the merging relies on a completely bindless GPU pipeline. Routes GPU culling itself to `shader-pipeline-engineer`, as its redirects say, and offers the lesson as an input to an ADR option.
**Assertions:**
- [ ] The 70% figure is attributed to the 2020 talk, not promised for this project
- [ ] Both costs from the entry are named
- [ ] GPU culling is routed to `shader-pipeline-engineer`

---

## Protocol Compliance

- [ ] Stays within lighting, shadows, RT features, post, upscalers, HDR output, environment rendering
- [ ] Declares passes to the render graph; never writes barriers, queue choices or compiler changes
- [ ] Redirects with exact names: render-graph-specialist, shader-pipeline-engineer, rhi-backend-engineer, rendering-lead, vfx-runtime-engineer, art-director, technical-artist
- [ ] Requires a capture before any cost or quality verdict; NOT ASSESSED otherwise
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps; never asserts NDA console facts
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- HDR10 output calibration (paper-white, peak luminance) has no dedicated case.
- Terrain/water rendering and its streaming hand-off to world-streaming-engineer are not covered.
