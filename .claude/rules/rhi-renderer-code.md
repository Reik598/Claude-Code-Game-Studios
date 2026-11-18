---
paths:
  - "engine/rhi/**"
  - "engine/renderer/**"
  - "engine/vfx/**"
  - "engine/xr/**"
  - "crates/rhi/**"
  - "crates/renderer/**"
  - "crates/vfx/**"
  - "crates/xr/**"
---

# RHI and Renderer Code Rules

For a project that builds its own engine (`engine.name: Custom`). The RHI is
owned by `rhi-backend-engineer`, the render graph by `render-graph-specialist`,
rendering features in `engine/renderer/features/` (lighting, GI, shadows, ray
tracing, post-processing, upscalers, sky, water) by
`graphics-features-engineer`, and GPU particles and decals in `engine/vfx/` by
`vfx-runtime-engineer`; all report to `rendering-lead`. XR (OpenXR or a
platform runtime, an ADR option) in `engine/xr/` is owned by
`platform-engineer` with `rendering-lead`; its swapchain and frame submission
go through the RHI and follow every rule below.
On any other engine, ignore this file.

- The RHI is the only code that calls Vulkan, Direct3D 12 or Metal. The
  renderer, and everything above it, uses RHI types only
- Every GPU resource has one owner and a known lifetime; destruction is
  deferred until the GPU has finished with the frame that used it (a fence or
  timeline value per frame in flight), never freed on the CPU's say-so
- Barriers and layout transitions come from the render graph's declared reads
  and writes, not hand-placed in passes. A pass that declares no access to a
  resource does not touch it; a buffer the GPU reads draw or dispatch arguments
  from is declared as an indirect-command read
- Command recording is multithreaded through per-thread command pools or
  allocators; a pool is never shared across threads without an annotated lock
- Pipelines (PSOs) are created through the pipeline cache, ahead of the frame
  that draws with them; a pipeline compiled on first use in the frame is a
  hitch and a bug
- Descriptors go through the bindless heap and its indices; no per-draw
  descriptor-set allocation in the frame
- No heap allocation per frame in recording or submission (`engine-code.md`'s
  hot-path rule applies)
- Every backend call that returns a result is checked. Device loss
  (`VK_ERROR_DEVICE_LOST`, `DXGI_ERROR_DEVICE_REMOVED`) is a recoverable
  state, not an assert: record the breadcrumbs, destroy the device and every
  object created from it, and recreate them; exit cleanly, with the report,
  only if creating a new device fails too (`rhi-backend-engineer.md`, All
  backends)
- A console backend sits behind the same RHI interface. The SDK licence
  decides where it lives: by default a private repository with no public CI;
  public placement only when the licence is shown to allow it and the user
  confirms. No console SDK fact is written in this repository
  (`rhi-backend-engineer.md`, Console Backends and NDA Placement)
- Every pass and resource has a debug name, and GPU markers wrap every pass, so
  RenderDoc, PIX and Nsight captures read without guessing
- An API fact (a limit, a required feature, an extension, a version) comes from
  `docs/engine-reference/custom/` or the API's own specification, cited; a fact
  neither covers is written `NOT SOURCEABLE — <what> is not covered by
  docs/engine-reference/custom/`
- Frame time is measured against `performance.frame_budget_ms` with GPU
  timestamps, before and after every change to a pass

## Features and VFX (`engine/renderer/features/`, `engine/vfx/`)

- A feature or VFX system is a set of render-graph passes. It never records
  commands outside the graph or calls the RHI's backend types
- Each feature has a GPU time budget from config, a quality setting that scales
  it, and an off switch; its cost is measured on the target hardware tiers
- Upscalers and vendor libraries (DLSS, FSR, XeSS and the like) are ADR
  options behind one engine interface, never called from a pass directly
- GPU particle counts, decal counts and overdraw have fixed caps from config;
  emission past a cap is dropped and counted, never grown into new buffers
  mid-frame. Effect content is authored with `technical-artist`

## Examples

**Correct** (declared access, copied captures, deferred destruction):

```cpp
graph.add_pass("shadow_depth", [&](pass_builder& b) {
    b.write(shadow_map, access::depth_write);   // the graph places the barrier
    b.read(instance_buffer, access::vertex_shader);
    b.read(indirect_args, access::indirect_command); // the GPU reads draw arguments from it
}, [indirect_args, draw_count = draw_count_](command_list& cmd, const pass_resources& r) {
    // runs at graph execution, after this function returned: handles and values are copied
    cmd.draw_indexed_indirect(r.buffer(indirect_args), draw_count);
});

device.destroy_deferred(std::move(old_buffer));  // freed when the frame's fence signals
```

**Incorrect**:

```cpp
vkCmdPipelineBarrier(cmd, /* ... */);            // VIOLATION: Vulkan call outside engine/rhi/, hand-placed barrier
auto pso = device.create_pipeline(desc);         // VIOLATION: pipeline compiled mid-frame
vkDestroyBuffer(dev, old_buffer, nullptr);       // VIOLATION: freed while a frame in flight may still read it
```

**Correct** (a feature as graph passes, capped VFX) — Rust:

```rust
pub fn add_passes(&self, graph: &mut RenderGraph, cfg: &BloomConfig) {
    if !cfg.enabled { return; } // off switch from config
    let chain = self.bloom_chain; // the execute closure runs later: copy the handle
    graph.add_pass("bloom_downsample", |b| {
        b.read(self.scene_color, Access::ComputeShader);
        b.write(chain, Access::ComputeWrite);
    }, move |cmd, r| cmd.dispatch(r.groups(chain)));
}
```

**Incorrect**:

```cpp
void particle_system::emit(std::uint32_t count)
{
    particles_.resize(particles_.size() + count);  // VIOLATION: grows past the cap, allocates mid-frame
    vendor_upscaler_evaluate(native_cmd_, &params_); // VIOLATION: vendor SDK called from a pass, not behind the engine interface
}
```
