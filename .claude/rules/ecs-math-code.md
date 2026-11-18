---
paths:
  - "engine/ecs/**"
  - "engine/math/**"
  - "crates/ecs/**"
  - "crates/math/**"
---

# ECS and Math Code Rules

For a project that builds its own engine (`engine.name: Custom`).
On any other engine, ignore this file.

## ECS

- Components are plain data: no virtual functions, no owning pointers, no
  behaviour. Logic lives in systems
- Component storage is laid out for the systems that read it (archetype
  chunks or sparse sets, structure of arrays where a system reads one field of
  many entities); the layout choice is recorded in an ADR
- Every system declares the components and shared resources (singletons,
  event queues, the command buffer it appends to) it reads and writes. The
  scheduler runs systems 1 and 2 in parallel only when W1 ∩ (R2 ∪ W2) = ∅ and
  W2 ∩ (R1 ∪ W1) = ∅: no write overlaps the other's reads or writes. Two readers
  may share. A system that touches anything it did not declare is a bug
- Entity handles are generational: a stale handle fails a lookup, it never
  reads a reused slot
- Structural changes (create, destroy, add or remove a component) during
  iteration go through a command buffer applied at a sync point
- No heap allocation per frame in a query or a system (`engine-code.md`)

## Math

- Math types are value types with explicit layout and alignment
  (`alignas(16)` for SIMD vectors in C++, `#[repr(C)]`/`#[repr(align(16))]` in
  Rust); the handedness, row/column-major order and units are stated once, in
  an ADR, and every type's doc comment names them
- Results that must match across machines (lockstep, replays, deterministic
  physics) do not use fast-math, fused multiply-add or platform intrinsics whose
  results differ between targets, unless an ADR records the trade
- Every SIMD path has a scalar reference implementation and a unit test that
  compares the two
- Floating-point comparisons in tests use a stated tolerance, never `==`
- Each math function states its accuracy in its doc comment: a ULP bound or a
  tolerance, as the numerics ADR records it (`ecs-dod-architect`, Numerics). A
  math function with neither is a review finding

## Examples

**Correct** (plain data, declared access):

```cpp
struct velocity { float3 value; };               // plain data
void integrate(query<write<position>, read<velocity>> q, float dt)
{
    for (auto [pos, vel] : q) pos.value += vel.value * dt;
}
```

```rust
#[repr(C, align(16))]
pub struct Vec4 { pub x: f32, pub y: f32, pub z: f32, pub w: f32 }
```

**Incorrect**:

```cpp
struct enemy_component {                          // VIOLATION: behaviour and ownership in a component
    virtual void update(float dt);
    std::unique_ptr<path> current_path;
};
world.destroy(entity);                            // VIOLATION: structural change during iteration
```
