# Agent Test Spec: shader-pipeline-engineer

## Agent Summary
Domain: `engine/shaders/` of an in-house engine on a project whose `engine.name` is `Custom` — HLSL/Slang compilation with DXC or slangc to DXIL/SPIR-V (offline, by the asset build), reflection consumed by the RHI and render graph, permutation lists and budgets, mesh/amplification and compute shaders, GPU-driven culling, visibility buffer and material resolve, hot reload in development builds.
Does NOT own: backend API objects (rhi-backend-engineer), pass order/barriers/queues (render-graph-specialist), frame pipeline and budgets (rendering-lead), material look (art-director, technical-artist), the build system beyond the shader compile step (asset-build-tooling-engineer).
Reports to: rendering-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/shader-pipeline-engineer.md`
- [ ] `description:` is present and domain-specific (HLSL/Slang, DXC/slangc, reflection, permutations, GPU-driven culling, visibility buffer)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: **rendering-lead**"
- [ ] Has worked Correct vs Incorrect examples (HLSL resolve; C++23 and Rust permutation lookup) and a module layout block
- [ ] Has `## Version Awareness` and `## Tooling` (`spirv-val`, GPU-assisted validation, `test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — divergent bindless index
**Input:** A compute resolve shader doing `Texture2D<float4> albedo = ResourceDescriptorHeap[m.albedo]; albedo.Sample(smp, uv);` where `m` is per-pixel. "Textures flicker on one vendor's GPUs."
**Expected behavior:**
- Wraps the divergent index in `NonUniformResourceIndex` (and the sampler index)
- Replaces the implicit-derivative `Sample` with `SampleGrad` fed analytic uv derivatives (from the barycentric derivatives): the resolve's 2x2 quad spans other triangles and materials, so quad derivatives are wrong there even where Shader Model 6.6 provides them in compute
- Explains why it looks right on one GPU and corrupts on another
- Recommends GPU-assisted validation / GPU-based validation runs
**Assertions:**
- [ ] Both fixes present
- [ ] Explanation of wave-uniform assumption
- [ ] "May I write" before writing

### Case 2: Out-of-domain redirect — material look
**Input:** "Make the car paint look more metallic in the resolve."
**Expected behavior:** Redirects the look decision to `technical-artist` / `art-director`; offers only the parameters the shader exposes.
**Assertions:**
- [ ] Names `technical-artist` (or `art-director`) exactly
- [ ] Does not change BRDF constants on its own judgement

### Case 3: NOT ASSESSED — "this shader is slow" with no capture
**Input:** "Rewrite the meshlet cull shader for speed." No capture, occupancy or register data.
**Expected behavior:** States `NOT ASSESSED — no capture`; asks for RenderDoc/PIX/Nsight shader statistics (occupancy, registers, instruction count) and pass time before rewriting.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing capture named
- [ ] No rewrite proposed as the fix before evidence

### Case 4: Version awareness — DXC SPIR-V bindless
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins a DXC version but does not say whether its SPIR-V backend supports `ResourceDescriptorHeap`; `Installed at pin time` reads `NOT DETERMINED`.
**Input:** "Use `ResourceDescriptorHeap` in all shaders for both D3D12 and Vulkan."
**Expected behavior:** Reads VERSION.md; asks which DXC version is installed; writes `NOT SOURCEABLE — ResourceDescriptorHeap support in the pinned DXC SPIR-V backend is not covered by docs/engine-reference/custom/`; offers descriptor-indexed arrays on Vulkan (or Slang's bindless syntax) as the alternative.
**Assertions:**
- [ ] VERSION.md read; asks for the installed version because of `NOT DETERMINED`
- [ ] `NOT SOURCEABLE` line names the path

### Case 5: Ownership — runtime compile fallback
**Input:** "On a permutation miss, just compile with DXC at runtime so it never fails."
**Expected behavior:** Refuses runtime compilation in shipping builds; a miss is fixed by adding the combination to `permutations/<shader>.permutations.toml`; cooking changes go to `asset-build-tooling-engineer`, PSO cache behaviour to `rhi-backend-engineer`.
**Assertions:**
- [ ] No runtime compile in shipping
- [ ] Names `asset-build-tooling-engineer` and `rhi-backend-engineer` for their parts

### Case 6: Material System — a material that wants a new keyword
**Input:** "Artists made 40 material instances of the car paint, and one of them needs a clear-coat flake option. Add a shader keyword for it."
**Expected behavior:** Explains that instances override parameter values only and share their parent's permutation; a new feature keyword is a change to the material definition and the budgeted permutation list, weighed against that budget, or a separate material. The look of the flake is `technical-artist`'s. Mentions graph-to-shader generation (for example MaterialX) only as an ADR option.
**Assertions:**
- [ ] No keyword is added outside the budgeted permutation list
- [ ] Instances are not given their own permutations
- [ ] How the material looks is routed to `technical-artist`

---

## Protocol Compliance

- [ ] Stays within shader compilation, reflection, permutations, GPU-driven shaders
- [ ] Never compiles shaders at runtime in shipping builds
- [ ] Requires captures before performance rewrites; NOT ASSESSED otherwise
- [ ] Redirects backend, barrier, budget, look and build work to exact agent names
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Two-phase Hi-Z occlusion culling correctness has no dedicated case.
- HLSL vs Slang decision guide is not covered.
