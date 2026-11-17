---
paths:
  - "assets/shaders/**"
  - "**/*.gdshader"
  - "Assets/**/*.{shader,hlsl,cginc,compute,shadergraph}"
  - "Shaders/**"
  - "**/*.{usf,ush}"
  - "engine/shaders/**"
  - "crates/shaders/**"
  - "**/*.slang"
---

# Shader Code Standards

All shader files, in every engine, must follow these standards to maintain
visual quality, performance, and cross-platform compatibility.

## Naming Conventions
- File naming: `[type]_[category]_[name].[ext]`
  - `spatial_env_water.gdshader` (Godot)
  - `SG_Env_Water` (Unity Shader Graph)
  - `M_Env_Water` (Unreal Material)
- Custom engine (`engine.name: Custom`): `[stage-or-kind]_[name].[hlsl|slang]`
  instead — the stage or kind is `vs`, `ps`, `cs`, `ms`, `as`, `rgen`, … or
  `common` (`cs_cull_instances.slang`, `ps_gbuffer_opaque.hlsl`); see
  "A project's own engine" below
- Use descriptive names that indicate the material purpose
- Prefix with the engine's shader type — Godot `spatial_`, `canvas_`, `particles_`,
  `post_`; Unity `SG_` (Shader Graph); Unreal `M_`, `MI_` (instance), `MF_` (function)

## Code Quality
- All uniforms/parameters must have descriptive names and appropriate hints
- Group related parameters (Godot: `group_uniforms`, Unity: `[Header]`, Unreal: Category)
- Comment non-obvious calculations (especially math-heavy sections)
- No magic numbers — use named constants or documented uniform values
- Include authorship and purpose comment at the top of each shader file

## Performance Requirements
- Document the target platform and complexity budget for each shader
- Use appropriate precision: `half`/`mediump` on mobile where full precision isn't needed
- Minimize texture samples in fragment shaders
- Avoid dynamic branching in fragment shaders — use `step()`, `smoothstep()` and
  `mix()` (Godot, GLSL) or `lerp()` (HLSL: Unity, Unreal)
- Custom engine (`engine.name: Custom`): the dynamic-branching bullet above is
  for the other engines; a runtime branch or a permutation is chosen per
  feature, see "A project's own engine" below
- No texture reads inside loops
- Custom engine (`engine.name: Custom`): the "No texture reads inside loops"
  bullet above is for the other engines; a loop that samples textures is
  allowed under the limits in "A project's own engine" below
- Two-pass approach for blur effects (horizontal then vertical)

## Cross-Platform
- Test shaders on minimum spec target hardware
- Provide fallback/simplified versions for lower quality tiers
- Document which render pipeline the shader targets (Forward/Deferred, URP/HDRP, Forward+/Mobile/Compatibility)
- Do not mix shaders from different render pipelines in the same directory

## Variant Management
- Minimize shader variants — each variant is a separate compiled shader
- Document all keywords/variants and their purpose
- Use feature stripping where possible to reduce build size
- Log and monitor total variant count per shader

## A project's own engine (`engine/shaders/`, `.hlsl`, `.slang`)

- Shaders are HLSL compiled with DXC, or Slang compiled with slangc, as the
  project chose at `/setup-engine custom`; the compiler version is the one in
  `docs/engine-reference/custom/VERSION.md`
- File naming: `[stage-or-kind]_[name].[hlsl|slang]` (`cs_cull_instances.slang`,
  `ps_gbuffer_opaque.hlsl`); shared code in `common/` includes or modules
- Shaders are compiled offline by the build into bytecode (SPIR-V, DXIL,
  Metal library), never at runtime in the frame
- Bindings come from reflection of the compiled shader, not hand-copied
  constants in C++ or Rust; a binding layout change is caught at build time
- Permutations are declared in one place, counted at build, and each one has
  a reason; an unused permutation is removed
- A runtime branch or a permutation is chosen per feature from a GPU capture
  of both, within the project's permutation-count budget
- A loop that samples textures (a ray march, a filter kernel) has a fixed or
  config-capped sample count, and its GPU time is measured against the
  feature's budget with a GPU capture
- GPU-driven culling and visibility-buffer passes document their input and
  output buffers and the workgroup size, with the reason for that size
