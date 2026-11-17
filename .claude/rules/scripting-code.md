---
paths:
  - "engine/scripting/**"
  - "game/scripts/**"
  - "crates/scripting/**"
---

# Scripting Code Rules

For a project that builds its own engine (`engine.name: Custom`). The scripting
runtime and its bindings in `engine/scripting/` are owned by
`scripting-runtime-engineer` (reports to `simulation-systems-lead`). The
language or VM (Lua, Luau, C#, WASM, an in-house one) is an ADR choice.
Scripts in `game/scripts/` are gameplay code: their values come from
`game/data/`, as `gameplay-code.md` requires.
On any other engine, ignore this file.

## Binding safety

- Scripts hold generational handles to native objects, never raw pointers or
  references. A handle to a destroyed object fails its lookup and raises a
  script error; it never reads freed memory
- A native reference handed to a script is valid only for that call. Nothing
  borrowed is kept across a yield, a coroutine resume or a frame
- Every binding validates its arguments (type, range, handle liveness) before
  touching native state. A bad script call is a script error, never a crash
- Native exceptions and panics do not cross the binding boundary: convert to a
  script error at the boundary

## Sandbox — no ambient authority

- Scripts get no file, network, process, environment or OS access by default.
  Anything they may do is a capability the engine passes in explicitly. In Lua
  that means these are absent: `io`; `os` except `os.clock`, `os.time`,
  `os.date` and `os.difftime`; `load`, `loadfile` and `dofile` (Lua does not
  check binary chunks, and a crafted one can crash the interpreter);
  `string.dump`; `package` (`package.loadlib`, `package.searchers`,
  `package.cpath`) and `require` of native modules; `debug`; and, for
  untrusted code, `collectgarbage`. In WASM only the declared imports exist
- A Lua deny list keeps first-party scripts honest; it is not a security
  boundary. Untrusted mods need enforceable isolation chosen by ADR: a
  separate process with OS-level restrictions, or a WASM runtime
- Untrusted scripts (mods, downloaded content) also run with instruction and
  memory limits, and a script that exceeds them is stopped and reported

## Time budget

- The VM's time per frame, including garbage collection, has a budget from
  config. GC runs incrementally in bounded steps; a full collection never runs
  inside a frame unless an ADR says so
- A script that runs past its budget is interrupted or yields, and the overrun
  is reported with the script name. Script time is measured, per script, in the
  profiler

## Hot reload

- Reload serialises the old module's state, loads the new code, and migrates
  the state through a versioned schema. A field that cannot be migrated is
  reported, not silently reset
- A reload that fails to compile or migrate keeps the old code running.
  References to old functions (callbacks, timers, event subscriptions) are
  rebound or dropped, never left dangling

## Deterministic order

- Script systems run in a declared order (priority, then a stable ID), and
  events dispatch to subscribers in subscription order. Never in hash-table or
  load order
- Scripts that run in the simulation step follow `simulation-code.md`: no
  wall clock, seeded randomness owned by the step

## Examples

**Correct** — C++23 binding:

```cpp
script_result bind_set_health(script_vm& vm, entity_handle h, float value)
{
    auto* health = world_.try_get<health_component>(h);  // generational lookup
    if (!health) return vm.error("set_health: entity no longer exists");
    if (!(value >= 0.0f)) return vm.error("set_health: value must be >= 0");
    health->current = value;
    return script_result::ok();
}
```

Rust:

```rust
fn set_health(ctx: &mut ScriptCtx, h: EntityHandle, value: f32) -> Result<(), ScriptError> {
    let health = ctx.world.get_mut::<Health>(h).ok_or(ScriptError::DeadEntity(h))?;
    if !(value >= 0.0) { return Err(ScriptError::Range("set_health", value)); }
    health.current = value;
    Ok(())
}
```

**Incorrect**:

```cpp
vm.push_userdata(&enemy);                    // VIOLATION: raw pointer, dangles when the enemy dies
vm.open_library(lua_lib::os);                // VIOLATION: ambient OS access for every script
vm.collect_garbage_full();                   // VIOLATION: unbounded GC inside the frame
```

```rust
let ptr: *mut Enemy = &mut world.enemies[i];
vm.set_global("target", ptr as usize); // VIOLATION: raw pointer exposed to script
for (_, s) in &self.scripts_by_name { s.update(); } // VIOLATION: HashMap order
```
