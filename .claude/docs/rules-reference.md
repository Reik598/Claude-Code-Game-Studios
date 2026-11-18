# Path-Specific Rules

Rules in `.claude/rules/` carry `paths:` frontmatter. Claude Code loads a
path-scoped rule **when it READS a file matching one of those globs** — not on
every tool use, and not when it creates one.

Three consequences, and none of them are optional reading:

1. **Reading, not editing.** A rule scoped to a gameplay folder reaches the
   model when a file there is opened. An agent that writes a brand-new file in that
   directory without opening an existing one never sees it. Most work in this
   framework creates files rather than reads them, so this is the common case,
   not the corner case.
2. **Context, not enforcement.** A loaded rule is guidance the model weighs, the
   same as `CLAUDE.md`. Anything that must hold regardless of what the model
   decides belongs in a hook — `.claude/hooks/` already enforces JSON validity
   and commit shape that way.
3. **A rule with no `paths:` loads every session**, at the same priority as
   `.claude/CLAUDE.md`. That is the lever for a rule that must always apply; it
   costs context in every session, so it is a deliberate trade, not a default.

Where a rule duplicates guidance an agent definition already carries, the two
must agree. Contradicting instructions are resolved arbitrarily, so a rule and
an agent stating different versions of the same standard is worse than either
alone.

To see which rules actually load, and why, wire the `InstructionsLoaded` hook —
`.claude/hooks/log-instructions.sh` records every instruction file and its load
reason (`session_start`, `path_glob_match`, `nested_traversal`, `include`,
`compact`) to `production/session-logs/instructions-loaded.log`.

**Globs match regardless of case.** Claude Code 2.1.282 matches `paths:`
gitignore-style and case-insensitively (observed; the docs do not say), so
`Assets/**/UI/**` also matches a Godot project's `assets/ui/` art. That is why
the Unity and Unreal code globs below name their file types.

Paths are listed Godot · Unity · Unreal, then a Custom project's (one that builds its own engine, `engine/` and `game/`). Folder names are shown in one case;
each rule's own globs list the case variants (`{AI,Ai,ai}`).

| Rule File | Path Pattern | Enforces |
| ---- | ---- | ---- |
| `gameplay-code.md` | `src/gameplay/**` · `Assets/**/Gameplay/**/*.cs` · `Source/**/Gameplay/**/*.{h,cpp}` · `game/src/**` | Data-driven values, delta time, gameplay systems hold no UI references (UI under `game/src/ui/` follows `ui-code.md`) |
| `engine-code.md` | `src/core/**` · `Assets/**/Core/**/*.cs` · `Source/**/Core/**/*.{h,cpp}` · `engine/core/**`, `engine/memory/**`, `engine/jobs/**`, `engine/platform/**`, `engine/input/**` | Zero allocs in hot paths, thread safety (annotations on a Custom engine), explicit ownership, API stability; on Custom, OS primitives only in `engine/platform/` (backend-private SDK code allowed), no NDA console material, suspend/resume, rebindable input actions |
| `engine-api-code.md` | — · — · — · `engine/**`, `crates/**` | Custom only, every engine module: module dependencies per ADR, `engine/` never uses `game/`, deprecation window with migration note and `/api-review`, no OS or SDK type in a public header, `NOT SOURCEABLE` for facts outside `docs/engine-reference/custom/` |
| `rhi-renderer-code.md` | — · — · — · `engine/rhi/**`, `engine/renderer/**` (incl. `engine/renderer/features/**`), `engine/vfx/**`, `engine/xr/**` | Custom only: graphics API calls confined to the RHI, render-graph barriers (incl. indirect-argument reads), deferred GPU destruction, PSO cache, debug names; features and VFX as budgeted, capped graph passes; XR submission through the RHI |
| `ecs-math-code.md` | — · — · — · `engine/ecs/**`, `engine/math/**` | Custom only: plain-data components, declared read/write access (incl. shared resources) gating parallel systems, generational handles, math layout and determinism |
| `simulation-code.md` | — · — · — · `engine/physics/**`, `engine/animation/**`, `engine/sequencer/**` | Custom only: deterministic fixed-step simulation (stable order, pinned FP, no wall clock), SoA layouts, no per-step heap, ragdoll hand-off contract; sequencer tracks evaluated at a defined tick point, scrub-deterministic |
| `audio-code.md` | — · — · — · `engine/audio/**` | Custom only: real-time audio callback (no locks, allocation, I/O or logging), bounded lock-free command queues, release/acquire snapshots, lock-free atomics, denormals, latency budget, voice caps |
| `streaming-io-code.md` | — · — · — · `engine/streaming/**`, `engine/assets/**`, `engine/io/**`, `engine/media/**` | Custom only: asynchronous, cancellable, prioritised I/O; streaming pool budgets; asset formats validated as untrusted input with versions and checksums; media decoded off the game and render threads |
| `scripting-code.md` | — · — · — · `engine/scripting/**`, `game/scripts/**` | Custom only: handle-based bindings, sandbox with no ambient authority, VM and GC time budget, hot-reload state migration, deterministic script order |
| `editor-code.md` | — · — · — · `engine/editor/**`, `tools/editor/**` | Custom only: editor compiled out of shipping builds (explicit shipping package and features, checked with the exact shipping command), every mutation an undoable transaction, non-blocking UI thread, generated reflection, viewport through the renderer |
| `tools-code.md` | — · — · — · `engine/tools/**`, `tools/ci/**`, `tools/build/**`, `tools/cook/**`, `tools/asset-pipeline/**`, `tools/validators/**`, `tools/reports/**` | Custom only: deterministic cook output, complete cache keys, versioned formats and trace schemas, no editor dependency in cookers, CLI exit codes |
| `build-files.md` | — · — · — · `/CMakeLists.txt`, `/CMakePresets.json`, `/Cargo.toml`, `/Cargo.lock`, `/rust-toolchain.toml` (project root only), `cmake/**/*.cmake`, and `CMakeLists.txt`, `*.cmake`, `Cargo.toml` under `engine/**`, `game/**` (`crates/**`: `Cargo.toml`, `*.cmake`) | Custom only: target-based CMake, presets, no global flags or source globs; Cargo workspace with real crate roots, additive features; pinned inputs; build-time budget, PCH/unity-build and include hygiene |
| `third-party.md` | — · — · — · `third_party/**`, `external/**`, `vendor/**` | Custom only: license file and pinned version, source URL and hash per dependency; local changes as patch files, never in place; `security-engineer` review; containment behind one wrapper |
| `ai-code.md` | `src/ai/**` · `Assets/**/AI/**/*.cs` · `Source/**/AI/**/*.{h,cpp}` · `engine/ai/**`, `game/src/ai/**` | Performance budgets, debuggability, data-driven params |
| `network-code.md` | `src/networking/**` · `Assets/**/Network(ing)/**/*.cs` · `Source/**/Network(ing)/**/*.{h,cpp}` · `engine/net/**`, `engine/online/**`, `game/src/net/**` | Server-authoritative, versioned messages, security; on Custom, no secrets in code, TLS, timeouts and backoff, one platform-services interface |
| `ui-code.md` | `src/ui/**` · `Assets/**/UI/**/*.cs` · `Source/**/UI/**/*.{h,cpp}` · `engine/ui/**`, `game/src/ui/**` | No game state ownership, localization-ready, accessibility |
| `design-docs.md` | `design/gdd/**` | Required sections per `modes.workflow` (8 at `full`, 5 at `standard`), formula format, edge cases |
| `narrative.md` | `design/narrative/**` | Lore consistency, character voice, canon levels |
| `data-files.md` | `assets/data/**/*.json` · `Assets/**/Data/**/*.json` · `Content/**/Data/**/*.json` · `game/data/**/*.json` | JSON validity, naming conventions, schema rules |
| `test-standards.md` | `tests/**` · `Assets/Tests/**/*.cs` · `Source/**/Tests/**/*.{h,cpp}` · `engine/**/tests/**`, `game/**/tests/**`, `engine/**/benches/**`, `crates/**/benches/**`, `game/**/benches/**` | Test naming (CTest and `cargo test` on Custom, benchmarks with thresholds), coverage requirements, fixture patterns |
| `prototype-code.md` | `prototypes/**` | One-shot browser games (values in `config.js`, seeded randomness, plays offline) and throwaway engine or paper prototypes (relaxed standards, README, hypothesis documented) |
| `shader-code.md` | `assets/shaders/**`, `**/*.gdshader` · `Assets/**/*.{shader,hlsl,cginc,compute,shadergraph}` · `Shaders/**`, `**/*.{usf,ush}` · `engine/shaders/**`, `crates/shaders/**`, `**/*.slang` | Naming conventions, performance targets, cross-platform rules |
| `scene-files.md` | `**/*.tscn`, `**/*.tres` · `**/*.unity`, `**/*.prefab`, `Assets/**/*.asset` · — | Hand-edit limits for editor-written scene and asset files; Unreal `.uasset`/`.umap` are binary, and `settings.json` denies edits to them |
| `agent-memory.md` | `.claude/agent-memory/**` | The one place an agent may write unasked — and why a temporary absence must never be recorded as a durable fact |
| `skill-authoring.md` | `.claude/skills/**`, `.claude/agents/**` | A check must be able to report that it did not run — the five obligations for verdicts, defaults, skips, sourcing and derived coverage |

Each engine-facing rule loads on all three editor engines:

- **Code rules** (`gameplay`, `engine`, `ai`, `network`, `ui`) match
  `Assets/**/<System>/**/*.cs` and `Source/**/<System>/**/*.{h,cpp}` (`Core`,
  `AI`, `Networking`/`Network`, `UI` for the others).
- **`data-files.md`** matches `Assets/**/Data/**/*.json` and `Content/**/Data/**/*.json`
  — JSON only, so C# or C++ in a `Data/` folder does not pick up its file-naming rule.
- **`shader-code.md`** matches shader files by type: `.gdshader`, `.shader`,
  `.hlsl`, `.cginc`, `.compute`, `.shadergraph`, `.usf`, `.ush`, plus `Shaders/**`.
- **`test-standards.md`** matches `Assets/Tests/**/*.cs` and `Source/**/Tests/**/*.{h,cpp}`.
- **Custom** (a project that builds its own engine) has its own globs under `engine/<module>/`,
  `game/`, `tools/editor/` and the tool folders `tools/ci/`, `tools/build/`, `tools/cook/`,
  `tools/asset-pipeline/`, `tools/validators/` and `tools/reports/`. `rhi-renderer-code.md`, `ecs-math-code.md`,
  `simulation-code.md`, `audio-code.md`, `streaming-io-code.md`, `scripting-code.md`,
  `editor-code.md` and `tools-code.md` load only there. Every module in the Custom layout is covered:
  `core`, `memory`, `jobs`, `platform`, `input` (`engine-code.md`); `rhi`, `renderer`, `vfx`, `xr`;
  `ecs`, `math`; `shaders`; `physics`, `animation`, `sequencer`; `audio`; `streaming`, `assets`,
  `io`, `media`; `scripting`; `editor`; `tools`; `net`, `online`; `ui`; `ai`; and
  `engine-api-code.md` (`engine/**`, `crates/**`) loads beside each module's rule. Owner agents per
  module: `.claude/docs/custom-engine-layout.md`. Inline `#[cfg(test)]` modules sit in `src/`
  and load the module's rule, not `test-standards.md`.
  Rust `crates/<module>/` aliases load the same subsystem rules; `crates/editor-*`
  and `crates/editor_*` load editor rules. Simulation includes `sim`, `cinematics`
  and `camera` as well as the legacy `sequencer` alias. Any other custom layout
  needs explicit globs before implementation.
- **Overlaps on Custom, by design.** `game/src/ai/`, `game/src/ui/` and `game/src/net/`
  load both `gameplay-code.md` (via `game/src/**`) and their system rule; the two
  agree (data-driven values, no direct UI references, UI changes state only through
  commands). A `.slang` file under `engine/vfx/` or `engine/renderer/` loads both
  `shader-code.md` and `rhi-renderer-code.md`.
- **`scene-files.md`** is the exception: Godot and Unity scene and asset files are text and have
  rules; Unreal's are binary, so a deny rule blocks edits instead of a rule guiding them.

> **`skill-authoring.md` is the odd one out and deliberately so.** Every other
> rule here scopes a *game* directory; that one scopes the **framework's own**
> authoring paths. It exists because one failure shape kept recurring across
> unrelated subsystems — a step that could not run producing output
> indistinguishable from a step that ran and found nothing. The same mistake in
> nine places is a missing design rule, not nine mistakes.
