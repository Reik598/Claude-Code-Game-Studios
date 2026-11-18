# Custom engine layout: the modules

For project coverage, optional capabilities and engine/game handoffs, read
`.claude/docs/engine-development-coverage.md` before planning a new module.

> Read on demand, not imported: `.claude/docs/directory-structure.md` (imported by
> `CLAUDE.md` into every session) only points here. Applies when `engine.name` is
> `Custom`. Keep this table in step with the `paths:` of `.claude/rules/*.md`.

On `Custom` the engine sits in `engine/`, one folder per module (C++:
`engine/<module>/include/` + `src/`; Rust: one crate per module under `engine/<module>/` or `crates/<module>/`). These are the
module names the path rules in `.claude/rules/` match — a module under another
name needs explicit rule globs before use. For each table row, `crates/<module>/`
uses the same owner and rules as `engine/<module>/`; editor crates named
`editor-*` or `editor_*` use `editor-code.md`. Record any other layout in the
module map and update rule paths before implementing:

Engine-wide rule: `engine-api-code.md` (`engine/**`, `crates/**`) loads for every
module below, beside the module's Path rule: module dependencies, no `game/`
use, public API deprecation and `/api-review`, no OS or SDK type in a public
header.

| Module | Holds | Path rule | Owner agent | Lead |
|---|---|---|---|---|
| `engine/core/` | foundation types, logging, asserts, containers, cvars, runtime module loading | `engine-code.md` | `core-systems-lead` | `chief-engine-architect` |
| `engine/memory/` | allocators, arenas, pools, tracking | `engine-code.md` | `memory-allocator-specialist` | `core-systems-lead` |
| `engine/jobs/` | job system, scheduler, fibers | `engine-code.md` | `concurrency-job-system-engineer` | `core-systems-lead` |
| `engine/platform/` | OS and console layer: windowing, input devices, threads, file system, crash handling | `engine-code.md` | `platform-engineer` | `core-systems-lead` |
| `engine/input/` | action mapping, input contexts, rebinding, device abstraction, haptics | `engine-code.md` | `platform-engineer` | `core-systems-lead` |
| `engine/ecs/` | entity storage, queries, system scheduling | `ecs-math-code.md` | `ecs-dod-architect` | `core-systems-lead` |
| `engine/math/` | vectors, matrices, SIMD primitives | `ecs-math-code.md` | `ecs-dod-architect` (physics supplies collision primitives) | `core-systems-lead` |
| `engine/io/` | async file I/O: the request queue and the DirectStorage / `io_uring` backends; the OS read primitive stays in `engine/platform/` (`platform-engineer`) | `streaming-io-code.md` | `world-streaming-engineer` | `core-systems-lead` |
| `engine/streaming/` | world streaming, cells, LOD/HLOD residency | `streaming-io-code.md` | `world-streaming-engineer` | `core-systems-lead` |
| `engine/assets/` | asset formats, loading, cooking runtime side | `streaming-io-code.md` | `world-streaming-engineer` | `core-systems-lead` |
| `engine/media/` | optional: video playback, platform codecs, audio/video sync | `streaming-io-code.md` | `platform-engineer` | `core-systems-lead` |
| `engine/rhi/` | graphics API backends (Vulkan, Direct3D 12, Metal) | `rhi-renderer-code.md` | `rhi-backend-engineer` | `rendering-lead` |
| `engine/renderer/` | frame graph, passes | `rhi-renderer-code.md` | `render-graph-specialist` | `rendering-lead` |
| `engine/renderer/features/` | lighting, GI, shadows, ray tracing, post, upscalers, sky, water | `rhi-renderer-code.md` | `graphics-features-engineer` | `rendering-lead` |
| `engine/vfx/` | GPU particles, decals, VFX runtime | `rhi-renderer-code.md` | `vfx-runtime-engineer` | `rendering-lead` |
| `engine/xr/` | optional: OpenXR or platform XR runtime, XR swapchain and frame submission | `rhi-renderer-code.md` | `platform-engineer` | `core-systems-lead` |
| `engine/shaders/` | HLSL / Slang sources, permutations | `shader-code.md` | `shader-pipeline-engineer` | `rendering-lead` |
| `engine/physics/` | rigid body, collision, queries | `simulation-code.md` | `physics-simulation-engineer` | `simulation-systems-lead` |
| `engine/animation/` | skeletal runtime, anim graphs, IK | `simulation-code.md` | `animation-systems-engineer` | `simulation-systems-lead` |
| `engine/sim/` | fixed-step scheduling and simulation handoffs | `simulation-code.md` | `simulation-systems-lead` | `chief-engine-architect` |
| `engine/camera/` | camera manager, blends, shake | `simulation-code.md` | `cinematics-sequencer-engineer` | `editor-architect` |
| `engine/cinematics/` (legacy alias `engine/sequencer/`) | cinematics runtime: tracks, evaluation, camera cuts, render-to-movie | `simulation-code.md` (its editor UI under `engine/editor/`: `editor-code.md`) | `cinematics-sequencer-engineer` | `editor-architect` |
| `engine/scripting/` | gameplay framework runtime, VM, bindings | `scripting-code.md` | `scripting-runtime-engineer` | `simulation-systems-lead` |
| `engine/audio/` | mixer, DSP graph, spatialization | `audio-code.md` | `audio-engine-engineer` | `simulation-systems-lead` |
| `engine/net/` | transport, replication | `network-code.md` | `network-programmer` | `core-systems-lead` |
| `engine/online/` | accounts, matchmaking, sessions, cloud saves | `network-code.md` | `online-services-engineer` | `core-systems-lead` |
| `engine/ui/` | runtime UI framework | `ui-code.md` | `ui-programmer` | `lead-programmer` |
| `engine/ai/` | navigation, behaviour runtime | `ai-code.md` | `ai-programmer` | `lead-programmer` |
| `engine/editor/` (Rust: `crates/editor-*/`, `crates/editor_*/`) | the editor: viewport, inspector, asset browser, undo | `editor-code.md` | `editor-architect` | `chief-engine-architect` |
| `engine/tools/` | asset cookers, derived-data cache, build and profiling tools | `tools-code.md` | `asset-build-tooling-engineer` | `core-systems-lead` |

Outside `engine/`:

| Path | Holds | Path rule | Owner agent | Lead |
|---|---|---|---|---|
| `game/src/` | the game's code | `gameplay-code.md` (+ `ai-code.md`, `network-code.md`, `ui-code.md` for `game/src/ai/`, `net/`, `ui/`) | `gameplay-programmer`; `ai/` → `ai-programmer`, `net/` → `network-programmer`, `ui/` → `ui-programmer` | `lead-programmer` |
| `game/scripts/` | game scripts | `scripting-code.md` | `gameplay-programmer` | `lead-programmer` |
| `game/data/` | game data | `data-files.md` (JSON) | `systems-designer` | none — a design role outside the engine hierarchy; escalation paths in `systems-designer.md` |
| `tests/`; module-local `engine/**/tests/`, `game/**/tests/`, `crates/**/tests/`; module-local `engine/**/benches/`, `game/**/benches/`, `crates/**/benches/` | unit, integration, benchmarks | `test-standards.md` | `qa-lead` | none — `qa-lead` reports to `producer` and `technical-director`, outside the engine hierarchy |
| `/CMakeLists.txt`, `/CMakePresets.json`, `/Cargo.toml`, `/Cargo.lock`, `/rust-toolchain.toml` (project root); `cmake/**/*.cmake`; `engine/**/CMakeLists.txt`, `engine/**/*.cmake`, `engine/**/Cargo.toml`; `crates/**/Cargo.toml`, `crates/**/*.cmake`; `game/**/CMakeLists.txt`, `game/**/*.cmake`, `game/**/Cargo.toml` | build files | `build-files.md` | `asset-build-tooling-engineer` | `core-systems-lead` |
| `third_party/`, `external/`, `vendor/` | third-party code | `third-party.md` | `security-engineer` | none — `security-engineer` reviews and escalates to `technical-director`; it reports to no engine lead |
| `tools/` | any other tool, in a folder without a row of its own | none — `tools/` exists on every engine, so a glob for all of it would load on all of them | `asset-build-tooling-engineer` | `core-systems-lead` |
| `tools/ci/`, `tools/build/`, `tools/cook/` | CI and build scripts, and the cook-side tools that drive the cookers in `engine/tools/` | `tools-code.md` | `asset-build-tooling-engineer` | `core-systems-lead` |
| `tools/asset-pipeline/`, `tools/validators/`, `tools/reports/` | standalone pipeline and batch tools, data validators, report generators | `tools-code.md` | `tools-programmer` | `lead-programmer` |
| `tools/editor/` | editor tools outside `engine/` | `editor-code.md` | `editor-architect` | `chief-engine-architect` |

A project needs only the modules it builds; the list is the set of names the
rules recognise, not a required set. The owner is the agent that writes and
reviews code there; it reports to the agent in the Lead column, and
`chief-engine-architect` owns the boundaries between modules. A Lead of `none`
says why the owner sits outside the engine's hierarchy. These two tables are the
one statement of path → rule → owner → lead: other files refer here instead of
keeping a copy, and a path with no row has no owner until one is added.

**Precedence rule, for overlapping rows.** A path that more than one row covers
takes the Path rule of every row that covers it: rules are cumulative, as their
globs load them (`engine/audio/tests/mixer_test.cpp` takes `audio-code.md` and
`test-standards.md`; `engine/audio/CMakeLists.txt` takes `audio-code.md` and
`build-files.md`). Its Owner and Lead come from the most specific row. Every
other row, a module's Rust `crates/` forms included, beats the tests row and the
build-files row, whatever their lengths (`crates/editor-ui/Cargo.toml` and
`crates/editor-ui/tests/x.rs` are the editor's). Between rows of the same kind,
a path written without a wildcard (`engine/audio/`) beats one with `*`, and
then the longer path wins (`engine/renderer/features/` over `engine/renderer/`,
`tools/editor/` over `tools/`). So the tests and build-files rows add their rule
to a module's files without changing who owns them; they decide the owner only
for files no other row covers (`tests/unit/`, the root `CMakeLists.txt`).

## Resolving source roots for workflows

For setup, API/memory audits and releases, resolve the project's module map
against its CMake targets or Cargo workspace members before selecting paths.
Engine source roots include the mapped modules under `engine/`, `crates/` or
the project's declared layout; game members remain consumer code. Record the
resolved roots. A missing `engine/` directory is valid when mapped engine crates
exist. Resolve a short module name through this map; an ambiguous or unmapped
name needs an explicit path before proceeding.

Release inventory also includes shared build inputs: root manifests and
lockfiles, toolchain and preset files, and build scripts, shader sources or
cookers the targets use. Derive those paths from the actual manifests and
includes. Keep these inputs in candidate cleanliness checks even when they sit
outside an engine source root. Source audits use the resolved roots for both
file discovery and evidence freshness checks.

## Generating CODEOWNERS

The Owner agent column is CODEOWNERS-ready, but agents are not GitHub accounts:
map each owner agent to the person or team who acts for it, then write one
line per row, for example `/engine/rhi/ @your-org/rendering`. GitHub uses the
**last** matching line, so put a sub-folder after its parent
(`/engine/renderer/features/` after `/engine/renderer/`). Writing
`.github/CODEOWNERS` is a project change: ask before creating it.
