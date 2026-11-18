---
paths:
  - "engine/editor/**"
  - "tools/editor/**"
  - "crates/editor/**"
  - "crates/editor-*/**"
  - "crates/editor_*/**"
---

# Editor Code Rules

For a project that builds its own engine (`engine.name: Custom`). Editor
architecture, reflection, undo/redo and play-in-editor are owned by
`editor-architect`; viewport, picking, gizmos and the outliner by
`level-editor-engineer`; docking, the property inspector and the asset browser
by `editor-ui-framework-engineer`. In-game debug tools and the standalone
pipeline and batch tools (`tools/asset-pipeline/` and the layout's other
`tools/` rows that name it) stay with `tools-programmer`. On any other engine,
ignore this file.

## Never in a shipping build

- Editor modules are excluded from shipping targets at compile time. In CMake
  the editor targets exist only when an editor option is on, and the shipping
  preset turns it off. In Cargo the editor is its own crate, or code behind an
  `editor` feature that is in no `default` feature set a shipping crate pulls
  in. A Cargo profile only changes codegen settings (optimisation, debug info,
  LTO); it never turns a feature off. The shipping build therefore selects its
  package and features explicitly — for example
  `cargo build --profile shipping -p game --no-default-features --features shipping` —
  and never builds with `--workspace`, which compiles the editor and can unify
  its features into runtime crates. The exact command is recorded as the
  project's shipping command
- Runtime modules never depend on editor modules. Editor-only data and code in
  a runtime module sit behind the same compile-time guard
  (`#if ENGINE_WITH_EDITOR`, `#[cfg(feature = "editor")]`), never a runtime flag
- A build check runs that exact shipping command (not a similar one) and
  confirms the result contains no editor symbols; on Cargo it also checks
  `cargo tree -e normal,features --target <shipping target> -p game
  --no-default-features --features shipping` for any editor crate or `editor`
  feature (`-e features` alone adds dev-dependencies, and without `--target`
  the tree is filtered to the host platform). It fails when one appears

## Every mutation is a transaction

- Every change a user can see or save (a property edit, a move, a create, a
  delete, a reparent) goes through the transaction system and records undo
  data. UI code never writes to an object's fields directly
- One user action is one transaction: a drag is one undo step, not one per
  mouse move. A cancelled action rolls back fully
- Play-in-editor runs on a copy of the world; nothing it changes leaks into
  the edited world without an explicit, undoable apply

## The UI thread never blocks

- Imports, cooks, light bakes, searches and saves run as jobs with progress and
  a cancel button. The UI thread never waits on a file, a job, a process or the
  network
- Results come back to the UI thread through a queue drained once per UI frame

## Reflection stays in sync

- Reflection metadata (fields, types, ranges, tooltips) is generated from the
  source (attributes, macros, derive macros or a code generator), not a
  hand-maintained list beside it
- A test walks every reflected type and fails when a serialised field has no
  metadata or metadata names a field that does not exist
- Serialised editor data carries a version, and a change to a reflected type's
  layout comes with a migration

## The viewport uses the engine renderer

- The editor viewport renders through the engine's renderer and render graph.
  Gizmos, grids, selection outlines and picking are render-graph passes
- The editor makes no graphics API calls of its own; `rhi-renderer-code.md`
  applies to anything it adds

## Examples

**Correct** — C++23:

```cpp
void inspector::on_value_changed(entity_handle e, const field_info& f, const value& v)
{
    auto tx = transactions_.begin("Set " + f.display_name); // one undo step
    tx.set_field(e, f, v);                                   // records old and new value
    tx.commit();
}
```

Rust:

```rust
#[cfg(feature = "editor")]
pub mod editor_hooks; // compiled only into editor builds

fn on_value_changed(&mut self, e: EntityHandle, f: &FieldInfo, v: Value) {
    let mut tx = self.transactions.begin(format!("Set {}", f.display_name));
    tx.set_field(e, f, v);
    tx.commit();
}
```

**Incorrect**:

```cpp
void inspector::on_value_changed(entity_handle e, float v)
{
    world_.get<transform>(e).scale = v;          // VIOLATION: direct write, no undo
    auto bytes = read_file_sync(asset_path_);    // VIOLATION: blocks the UI thread
}
// engine/renderer/src/scene.cpp
#include "editor/selection.hpp"                  // VIOLATION: runtime depends on the editor
```

```rust
if settings.is_editor { editor::draw_gizmos(); } // VIOLATION: runtime flag, editor code ships
```
