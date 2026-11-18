---
paths:
  - "src/ai/**"
  - "Assets/**/{AI,Ai,ai}/**/*.cs"
  - "Source/**/{AI,Ai,ai}/**/*.{h,cpp}"
  - "engine/ai/**"
  - "game/src/ai/**"
  - "crates/ai/**"
---

# AI Code Rules

- AI update budget: 2ms per frame maximum — profile to verify
- All AI parameters must be tunable from data files (behavior tree weights, perception ranges, timers)
- AI must be debuggable: implement visualization hooks for all AI state (paths, perception cones, decision trees)
- AI should telegraph intentions — players need time to read and react
- Prefer utility-based or behavior tree approaches over hard-coded if/else chains
- Group AI must support formation, flanking, and role assignment from data
- All AI state machines must log transitions for debugging
- Never trust AI input from the network without validation

## On a Custom engine (`engine/ai/`, `game/src/ai/`)

Owned by `ai-programmer`. The 2 ms budget above is the default; the project's
value comes from config and is measured against `performance.frame_budget_ms`.

- AI runs as ECS systems or jobs that declare what they read and write
  (`ecs-math-code.md`); pathfinding and perception queries run on the job
  system, batched, never as a blocking call on the game thread
- No heap allocation per frame in a decision or query (`engine-code.md`):
  open lists, path buffers and blackboards come from pools reserved at init
- AI that affects simulation state follows `simulation-code.md`: seeded
  randomness owned by the step, stable iteration order, no wall clock
- Debug visualisation draws through the engine's debug-draw passes and is
  compiled out of shipping builds

```cpp
path_requests_.push({.agent = e, .goal = goal});   // batched, solved by a job
auto path = navmesh_.find_path_now(start, goal);   // VIOLATION: blocking query on the game thread
```

```rust
let choice = self.rng.next_weighted(&weights);     // seeded, owned by the step
let choice = rand::random::<f32>();                // VIOLATION: unseeded, breaks replays
```
