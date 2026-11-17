---
paths:
  - "src/ui/**"
  - "Assets/**/{UI,Ui,ui}/**/*.cs"
  - "Source/**/{UI,Ui,ui}/**/*.{h,cpp}"
  - "engine/ui/**"
  - "game/src/ui/**"
  - "crates/ui/**"
---

# UI Code Rules

- UI must NEVER own or directly modify game state — display only, use commands/events to request changes
- All UI text must go through the localization system — no hardcoded user-facing strings
- Support both keyboard/mouse AND gamepad input for all interactive elements
- All animations must be skippable and respect user motion/accessibility preferences
- UI sounds trigger through the audio event system, not directly
- UI must never block the game thread
- Scalable text and colorblind modes are mandatory, not optional
- Test all screens at minimum and maximum supported resolutions

## On a Custom engine (`engine/ui/`, `game/src/ui/`)

Game UI is implemented by `ui-programmer`. The editor's own UI is
`editor-code.md`'s, not this rule's.

- The runtime UI framework in `engine/ui/` renders through render-graph passes
  (`rhi-renderer-code.md`); it makes no graphics API calls of its own
- Text goes through the engine's shaping and font pipeline, so localization,
  right-to-left scripts and IME input work without special cases in game code
- Layout and per-frame UI updates allocate nothing per frame
  (`engine-code.md`); UI time per frame has a budget from config
- `game/src/ui/` reads game state through events and view models and sends
  commands back; it never includes `engine/*/src/` internals

```cpp
button.on_click([&] { commands_.push(cmd::open_inventory{}); }); // request, not mutation
player_.inventory.items.clear();                                 // VIOLATION: UI writes game state
```

```rust
label.set_text(loc.get("hud.ammo", &[("count", ammo.into())])); // localized
label.set_text(format!("Ammo: {ammo}"));                        // VIOLATION: hardcoded string, allocates per frame
```
