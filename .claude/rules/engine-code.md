---
paths:
  - "src/core/**"
  - "Assets/**/{Core,core}/**/*.cs"
  - "Source/**/{Core,core}/**/*.{h,cpp}"
  - "engine/core/**"
  - "engine/memory/**"
  - "engine/jobs/**"
  - "engine/platform/**"
  - "engine/input/**"
  - "crates/core/**"
  - "crates/memory/**"
  - "crates/jobs/**"
  - "crates/platform/**"
  - "crates/input/**"
---

# Engine Code Rules

- ZERO allocations in hot paths (update loops, rendering, physics) — pre-allocate, pool, reuse
- All engine APIs must be thread-safe OR explicitly documented as single-thread-only
- Profile before AND after every optimization — document the measured numbers
- Engine code must NEVER depend on gameplay code (strict dependency direction: engine <- gameplay)
- Every public API must have usage examples in its doc comment
- Changes to public interfaces require a deprecation period and migration guide
- Use RAII / deterministic cleanup for all resources
- All engine systems must support graceful degradation
- Before writing engine API code, consult `docs/engine-reference/` for the current engine version and verify APIs against the reference docs

## A project's own engine (`engine/`, `engine.name: Custom`)

- No heap allocation in a hot path (the frame tick, job bodies, the render
  and physics steps): use a frame arena, a pool or storage reserved at init.
  Allocators come from `engine/memory/`, never a global `new`/`malloc` or a
  `Vec`/`Box` made per frame
- Every type shared across threads states how: Clang thread-safety
  annotations in C++ (`GUARDED_BY`, `REQUIRES`, `EXCLUDES` on a
  `CAPABILITY`-annotated mutex, built with `-Wthread-safety`), or the
  `Send`/`Sync` bounds in Rust. An `unsafe impl Send`/`Sync` carries a
  `// SAFETY:` comment naming the invariant
- Ownership is explicit in every signature: C++ owns through
  `std::unique_ptr`/handles and borrows through references and `std::span`, never
  an owning raw pointer; Rust owns by value and borrows by reference, with
  `unsafe` blocks commented with `// SAFETY:`
- The rules that hold in every engine module (module dependencies, no `game/`
  use, public API deprecation and `/api-review`, no OS or SDK type in a public
  header) are in `engine-api-code.md`

### Platform layer (`engine/platform/`)

Owned by `platform-engineer` (reports to `core-systems-lead`).

- OS platform primitives (windowing, threads and affinity, file system,
  virtual memory, timers, input devices, crash handling) are implemented only
  in `engine/platform/`; every other module uses the platform layer's types for
  them
- A backend that is itself platform- or API-specific may use its own SDK in
  backend-private code: the D3D12 or Metal backend's `.cpp`/`.mm` files under
  `engine/rhi/src/`, an online-services provider under `engine/online/src/`, an
  audio device backend. In Rust, `#[cfg(target_os = …)]` or a backend feature
  gates such a module; the gate never appears in a non-backend module
- Console SDK material under NDA (headers, libraries, documentation, sample
  code, cert requirement text) is never committed to this repository and never
  quoted in a rule, doc or comment. A console fact not in
  `docs/engine-reference/custom/` is `NOT SOURCEABLE`
- Suspend and resume are handled states: on suspend the engine stops
  submitting GPU work, flushes saves and pauses audio and network within the
  platform's deadline; on resume it revalidates devices, network sessions and
  sign-in state before the game continues
- Per-thread floating-point and denormal modes are set by the platform layer
  on threads the engine creates, when it creates them, so the simulation and
  audio threads all run the same mode (`simulation-code.md`,
  `audio-code.md`). A callback thread a device API owns gets no such hook: the
  platform layer provides an RAII guard that sets the mode at callback entry
  and restores the previous one on exit

### Input (`engine/input/`)

Owned by `platform-engineer`; accessibility requirements come from
`accessibility-specialist`.

- Game code binds to actions in input contexts, never to raw keys, buttons or
  device IDs; every action can be rebound, and bindings are data, not code
- Device events reach the game as engine input types from `engine/platform/`;
  no OS or SDK input type appears in `engine/input/`'s public API
- Input is sampled once per tick at a defined point and timestamped, so the
  simulation reads the same input on every replay

## Examples

**Correct** (zero-alloc hot path) — Godot:

```gdscript
# Pre-allocated array reused each frame
var _nearby_cache: Array[Node3D] = []

func _physics_process(delta: float) -> void:
    _nearby_cache.clear()  # Reuse, don't reallocate
    _spatial_grid.query_radius(position, radius, _nearby_cache)
```

Unity:

```csharp
private readonly Collider[] _nearbyCache = new Collider[64];  // allocated once

void FixedUpdate()
{
    int count = Physics.OverlapSphereNonAlloc(transform.position, radius, _nearbyCache);
}
```

Unreal:

```cpp
// TArray member, reserved once; Reset() keeps the allocation
void UProximityComponent::TickComponent(float DeltaTime, ELevelTick TickType,
                                        FActorComponentTickFunction* ThisTickFunction)
{
    NearbyCache.Reset();
    SpatialGrid->QueryRadius(GetComponentLocation(), Radius, NearbyCache);
}
```

Custom engine, C++23 (frame arena, annotated shared state, explicit ownership):

```cpp
void proximity_system::tick(const spatial_grid& grid, frame_arena& arena)
{
    // Bump allocation from the frame arena, reset once per frame: no heap
    std::span<entity_id> nearby = arena.allocate_array<entity_id>(max_nearby_);
    const std::size_t count = grid.query_radius(origin_, radius_, nearby);
    process(nearby.first(count));
}

class job_queue {
public:
    void push(job j) EXCLUDES(mutex_);
private:
    mutex mutex_;                                // CAPABILITY("mutex") wrapper
    ring_buffer<job, 1024> jobs_ GUARDED_BY(mutex_);
};

std::unique_ptr<texture, gpu_deleter> load_texture(std::string_view path);  // caller owns
```

Custom engine, Rust (storage reserved at init, ownership in the types):

```rust
pub struct ProximitySystem {
    origin: Vec3,
    radius: f32,
    nearby: Box<[EntityId]>, // allocated once, in new()
}

impl ProximitySystem {
    pub fn tick(&mut self, grid: &SpatialGrid) {
        let count = grid.query_radius(self.origin, self.radius, &mut self.nearby);
        process(&self.nearby[..count]);
    }
}

pub struct JobQueue {
    jobs: Mutex<RingBuffer<Job, 1024>>, // the Mutex owns the data it guards
}
```

**Incorrect** (allocating in hot path):

```gdscript
func _physics_process(delta: float) -> void:
    var nearby: Array[Node3D] = []  # VIOLATION: allocates every frame
    nearby = get_tree().get_nodes_in_group("enemies")  # VIOLATION: tree query every frame
```

Custom engine, C++23:

```cpp
void proximity_system::tick(const spatial_grid& grid)
{
    std::vector<entity_id> nearby;                // VIOLATION: heap allocation every frame
    grid.query_radius(origin_, radius_, nearby);
}

texture* load_texture(const char* path);          // VIOLATION: owning raw pointer, who frees it?
int pending_jobs_;                                // VIOLATION: written by several threads, no annotation, not atomic
```

Custom engine, Rust:

```rust
pub fn tick(&mut self, grid: &SpatialGrid) {
    let nearby: Vec<EntityId> = grid.query_radius_vec(self.origin, self.radius); // VIOLATION: allocates every frame
}

static mut PENDING_JOBS: usize = 0; // VIOLATION: shared mutable state, no synchronisation
unsafe impl Sync for JobQueue {}    // VIOLATION: no // SAFETY: comment naming the invariant
```

Custom engine, platform layer:

```cpp
// engine/renderer/src/swapchain.cpp
#include <windows.h>                              // VIOLATION: OS primitive outside engine/platform/, not a backend
```

```rust
// engine/ecs/src/world.rs
use windows_sys::Win32::System::Threading::*;    // VIOLATION: OS binding in a non-backend module
```
