---
paths:
  - "engine/physics/**"
  - "engine/animation/**"
  - "engine/sequencer/**"
  - "engine/sim/**"
  - "engine/cinematics/**"
  - "engine/camera/**"
  - "crates/sim/**"
  - "crates/physics/**"
  - "crates/animation/**"
  - "crates/cinematics/**"
  - "crates/sequencer/**"
  - "crates/camera/**"
---

# Simulation Code Rules

For a project that builds its own engine (`engine.name: Custom`). Physics is
owned by `physics-simulation-engineer`, animation by
`animation-systems-engineer`; both report to `simulation-systems-lead`, which
agrees the simulation tick order with `core-systems-lead`.
On any other engine, ignore this file.

## Determinism

- The simulation steps at a fixed timestep from config, driven by an
  accumulator. The renderer interpolates between the last two states; it never
  changes the step size
- Simulation time is `step_index * fixed_dt`. No wall clock in a step:
  no `std::chrono::*_clock::now()`, no `Instant::now()`, no frame delta
- Iteration order is stable and defined: bodies, contacts, constraints and
  bones are processed in an order derived from stable IDs. Never iterate a hash
  map in a step, and never let a parallel reduction combine results in
  completion order — partition the work, then combine in partition order
- Floating-point behaviour is pinned per target and recorded in an ADR: no
  fast-math, FP contraction off per compiler (GCC/Clang `-ffp-contract=off`;
  MSVC from VS 2022 `/fp:precise` without `/fp:contract`; clang-cl
  `/fp:precise` plus `/clang:-ffp-contract=off`, or `/fp:strict`; confirm the
  effective flags in `compile_commands.json`), the same
  flush-to-zero / denormal mode set on every thread that runs a step
  (`engine-code.md` owns where that is set). Transcendental functions the
  result depends on come from the engine's own math, not the platform's libm
- Randomness comes from a seeded generator owned by the simulation and advanced
  only by the step; never `rand()` or a thread-local RNG
- A determinism test runs the same input twice (and across targets where the
  ADR claims cross-platform determinism) and compares a state hash per step

## Layout and memory

- Hot data is structure-of-arrays, aligned for the widest SIMD lane width the
  ADR targets, and padded to a lane multiple so the loop has no scalar tail
  branch in the middle of the data
- No heap allocation per step: broad-phase pairs, contact manifolds, solver
  islands and pose buffers live in storage reserved at init or in the frame
  arena (`engine-code.md`'s hot-path rule)
- Every SIMD path keeps a scalar reference and a test comparing the two
  (`ecs-math-code.md`)

## Ragdoll and physics hand-off

- One owner per bone per step. Animation owns the pose until hand-off; physics
  owns the bodies after it. Both never write the same bone transform in one step
- Hand-off happens at one defined point in the tick (after animation sampling,
  before the physics step), passes pose and per-bone velocities, and is declared
  in the public interface of both modules. Blending back to animation is an
  explicit reverse hand-off, not physics stopping writing
- The hand-off contract (who owns what, when, in which space and units) is an
  ADR; a change to it goes through `simulation-systems-lead`

## Cinematics and camera (`engine/cinematics/`, `engine/camera/`; alias `engine/sequencer/`)

Owned by `cinematics-sequencer-engineer`. Its authoring UI lives under
`engine/editor/` and follows `editor-code.md`.

- Tracks evaluate at one defined point in the tick, in a stated track order,
  from the sequence time — never from the wall clock
- Evaluating the same sequence at the same time gives the same result whether
  it was reached by playing or by scrubbing for continuously evaluated poses
  and properties; a test seeks to a time both ways and compares those values.
  Event tracks use explicit crossed-time windows during playback; scrub suppresses
  gameplay events by default. Test forward, reverse, loop and seek event policies
  separately; event history is not required to equal playback history
- A track writes only what it declares (a transform, a camera cut, an event);
  a property another system owns that step is a conflict reported at bind
  time, not a last-writer-wins race

## Examples

**Correct** — C++23:

```cpp
void physics_world::advance(double frame_seconds)
{
    // Clamp the catch-up (a config value) so a long frame cannot start a
    // spiral of steps that each make the next frame longer.
    accumulator_ += std::min(frame_seconds, config_.max_catch_up_s);
    while (accumulator_ >= config_.fixed_dt) {
        step(step_index_++, config_.fixed_dt);     // time comes from the index
        accumulator_ -= config_.fixed_dt;
    }
}

void physics_world::step(std::uint64_t index, float dt)
{
    contacts_.clear();                             // capacity reserved at init
    broad_phase_.find_pairs(bodies_sorted_by_id_, contacts_);
    solver_.solve(contacts_, dt, rng_.fork(index)); // seeded by the step
}
```

Rust:

```rust
pub fn step(&mut self, index: u64, dt: f32) {
    self.contacts.clear(); // Vec reserved in new(), never grows past capacity
    self.broad_phase.find_pairs(&self.bodies_by_id, &mut self.contacts);
    let partials: [Impulse; PARTITIONS] = self.solve_partitions(dt, index);
    self.apply(partials.iter().fold(Impulse::ZERO, |a, p| a + *p)); // fixed order
}
```

**Incorrect**:

```cpp
void physics_world::update()
{
    const float dt = clock::now() - last_;          // VIOLATION: wall clock, variable step
    std::vector<contact> contacts;                  // VIOLATION: heap per step
    for (auto& [id, body] : body_map_) integrate(body, dt); // VIOLATION: hash-map order
}
```

```rust
let total: Impulse = islands.par_iter().map(solve).reduce(|| Impulse::ZERO, |a, b| a + b);
// VIOLATION: float sum in an unspecified grouping (rayon) — results can differ run to run
```
