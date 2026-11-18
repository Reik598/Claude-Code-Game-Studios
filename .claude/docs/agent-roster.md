# Agent Roster

The following 77 agents are available (25 of them only on a Custom engine). Each has a dedicated definition file in
`.claude/agents/`. Use the agent best suited to the task at hand. When a task
spans multiple domains, the coordinating agent (usually `producer` or the
domain lead) should delegate to specialists.

Which model and effort an agent runs on is set by the `model:` and `effort:`
lines in its own file, which `.claude/agent-models.yaml` writes;
`model-tiers.md` lists the agents per tier. No agent runs on the session's
model unless a project's `overrides:` gives it `session`.

## Tier 1 -- Leadership Agents
| Agent | Domain | When to Use |
|-------|--------|-------------|
| `creative-director` | High-level vision | Major creative decisions, pillar conflicts, tone/direction |
| `technical-director` | Technical vision | Architecture decisions, tech stack choices, performance strategy |
| `producer` | Production management | Sprint planning, milestone tracking, risk management, coordination |

## Tier 2 -- Department Lead Agents
| Agent | Domain | When to Use |
|-------|--------|-------------|
| `game-designer` | Game design | Mechanics, systems, progression, economy, balancing |
| `lead-programmer` | Code architecture | System design, code review, API design, refactoring |
| `art-director` | Visual direction | Style guides, art bible, asset standards, UI/UX direction |
| `audio-director` | Audio direction | Music direction, sound palette, audio implementation strategy |
| `narrative-director` | Story and writing | Story arcs, world-building, character design, dialogue strategy |
| `qa-lead` | Quality assurance | Test strategy, bug triage, release readiness, regression planning |
| `release-manager` | Release pipeline | Build management, versioning, changelogs, deployment, rollbacks |
| `localization-lead` | Internationalization | String externalization, translation pipeline, locale testing |

## Tier 3 -- Specialist Agents
| Agent | Domain | When to Use |
|-------|--------|-------------|
| `systems-designer` | Systems design | Specific mechanic implementation, formula design, loops |
| `level-designer` | Level design | Level layouts, pacing, encounter design, flow |
| `economy-designer` | Economy/balance | Resource economies, loot tables, progression curves |
| `gameplay-programmer` | Gameplay code | Feature implementation, gameplay systems code |
| `engine-programmer` | Engine systems | Core engine, rendering, physics, memory management |
| `ai-programmer` | AI systems | Behavior trees, pathfinding, NPC logic, state machines |
| `network-programmer` | Networking | Netcode, replication, lag compensation, matchmaking |
| `tools-programmer` | Dev tools | Editor extensions, pipeline tools, debug utilities |
| `ui-programmer` | UI implementation | UI framework, screens, widgets, data binding |
| `technical-artist` | Tech art | Shaders, VFX, optimization, art pipeline tools |
| `lighting-artist` | Lighting and look-dev | Scene lighting, exposure, tone mapping, grading, bake settings |
| `sound-designer` | Sound design | SFX design docs, audio event lists, mixing notes |
| `writer` | Dialogue/lore | Dialogue writing, lore entries, item descriptions |
| `cinematic-designer` | Cinematic design | Shot lists, camera, previs, the edit of cinematics |
| `world-builder` | World/lore design | World rules, faction design, history, geography |
| `qa-tester` | Test execution | Writing test cases, bug reports, test checklists |
| `performance-analyst` | Performance | Profiling, optimization recs, memory analysis |
| `devops-engineer` | Build/deploy | CI/CD, build scripts, version control workflow |
| `analytics-engineer` | Telemetry | Event tracking, dashboards, A/B test design |
| `ux-designer` | UX flows | User flows, wireframes, accessibility, input handling |
| `xr-experience-designer` | VR experience design | VR comfort and locomotion options, play space, world scale, hand and controller interaction |
| `prototyper` | Rapid prototyping | Throwaway prototypes, mechanic testing, feasibility validation |
| `security-engineer` | Security | Anti-cheat, exploit prevention, save encryption, network security |
| `accessibility-specialist` | Accessibility | WCAG compliance, colorblind modes, remapping, text scaling |
| `live-ops-designer` | Live operations | Seasons, events, battle passes, retention, live economy |
| `community-manager` | Community | Patch notes, player feedback, crisis comms, community health |

## Engine-Specific Agents (use the set matching your engine)

### Engine Leads

| Agent | Engine | When to Use |
| ---- | ---- | ---- |
| `unreal-specialist` | Unreal Engine 5 | Blueprint vs C++, GAS overview, UE subsystems, Unreal optimization |
| `unity-specialist` | Unity | MonoBehaviour vs DOTS, Addressables, URP/HDRP, Unity optimization |
| `godot-specialist` | Godot 4 | GDScript patterns, node/scene architecture, signals, Godot optimization |

### Unreal Engine Sub-Specialists

| Agent | Subsystem | When to Use |
| ---- | ---- | ---- |
| `ue-gas-specialist` | Gameplay Ability System | Abilities, gameplay effects, attribute sets, tags, prediction |
| `ue-blueprint-specialist` | Blueprint Architecture | BP/C++ boundary, graph standards, naming, BP optimization |
| `ue-replication-specialist` | Networking/Replication | Property replication, RPCs, prediction, relevancy, bandwidth |
| `ue-umg-specialist` | UMG/CommonUI | Widget hierarchy, data binding, CommonUI input, UI performance |

### Unity Sub-Specialists

| Agent | Subsystem | When to Use |
| ---- | ---- | ---- |
| `unity-dots-specialist` | DOTS/ECS | Entity Component System, Jobs, Burst compiler, hybrid renderer |
| `unity-shader-specialist` | Shaders/VFX | Shader Graph, VFX Graph, URP/HDRP customization, post-processing |
| `unity-addressables-specialist` | Asset Management | Addressable groups, async loading, memory, content delivery |
| `unity-ui-specialist` | UI Toolkit/UGUI | UI Toolkit, UXML/USS, UGUI Canvas, data binding, cross-platform input |

### Godot Sub-Specialists

| Agent | Subsystem | When to Use |
| ---- | ---- | ---- |
| `godot-gdscript-specialist` | GDScript | Static typing, design patterns, signals, coroutines, GDScript performance |
| `godot-csharp-specialist` | C# / .NET | .NET patterns, [Signal] delegates, async, nullable types, type-safe node access |
| `godot-shader-specialist` | Shaders/Rendering | Godot shading language, visual shaders, particles, post-processing |
| `godot-gdextension-specialist` | GDExtension | C++/Rust bindings, native performance, custom nodes, build systems |

## Custom Engine (build your own)

Used only when `engine.name` is `Custom` — the project builds its own engine
under `engine/` and the game on it under `game/`. Specialists report to their
lead, the leads to `chief-engine-architect`. `chief-engine-architect` owns
engine-internal technical decisions; `technical-director` keeps the
project-wide technical call (`coordination-rules.md`).

| Agent | Tier | Domain | When to Use |
| ---- | ---- | ---- | ---- |
| `chief-engine-architect` | Director | Engine architecture | Subsystem boundaries, API/ABI stability, ADR compliance, frame budgets (8.33 / 16.6 ms), engine technical conflicts |
| `core-systems-lead` | Lead | Core runtime | Concurrency, memory and platform abstraction; coordinates the allocator, job-system, ECS, platform, world-streaming, online-services, build and network specialists (`network-programmer` for `engine/net/`) |
| `rendering-lead` | Lead | Frame pipeline | GPU submission, CPU→GPU sync, frames in flight; coordinates the RHI, render-graph, shader, graphics-features and VFX specialists |
| `memory-allocator-specialist` | Specialist | Allocators | Linear/arena, pool, slab, buddy, TLSF allocators, alignment, fragmentation tracking |
| `concurrency-job-system-engineer` | Specialist | Job system | Lock-free structures, work-stealing scheduler, fiber task graphs |
| `ecs-dod-architect` | Specialist | ECS / data layout | Archetype or sparse-set ECS, SoA layouts, query scheduling |
| `rhi-backend-engineer` | Specialist | Graphics API backends | Vulkan 1.4 / D3D12 / Metal RHI, bindless heaps, PSO cache, multithreaded command recording |
| `render-graph-specialist` | Specialist | Render graph | Transient resource aliasing, automatic barriers, async compute scheduling |
| `shader-pipeline-engineer` | Specialist | Shader toolchain | HLSL/Slang compilation, reflection, permutations, GPU-driven culling, visibility buffer |
| `physics-simulation-engineer` | Specialist | Physics | Deterministic rigid body, broad/narrow phase, collision primitives; reports to `simulation-systems-lead` |
| `asset-build-tooling-engineer` | Specialist | Build and cooking | CMake/Cargo build graph, hot-reload asset cookers, the Tracy/PIX instrumentation build switch, CI benchmarks |
| `platform-engineer` | Specialist | Platform layer | Windowing, input devices and haptics, file I/O, threads and affinity, virtual memory, crash handling, suspend/resume, console SDK layer (NDA facts never asserted) |
| `world-streaming-engineer` | Specialist | World streaming | Async I/O, streaming priorities, world-partition runtime cells, LOD/HLOD, streaming pool budgets, load-time targets |
| `online-services-engineer` | Specialist | Online services | Identity, matchmaking and lobbies, sessions, entitlements, cloud saves, telemetry upload, backend SDK abstraction; coordinates `network-programmer` |
| `graphics-features-engineer` | Specialist | Graphics features | Lighting and GI, shadows, ray-traced features, post-processing, temporal AA and upscalers, HDR output, terrain/sky/water/atmosphere |
| `vfx-runtime-engineer` | Specialist | VFX runtime | GPU particles, decals, the VFX runtime graph, sorting and transparency, VFX budgets |
| `simulation-systems-lead` | Lead | Runtime simulation | Physics and animation in the fixed step, scripting runtime, audio engine (fixed step generates audio events; mixing runs on the device callback's own clock); sim tick order with `core-systems-lead`; coordinates its four specialists |
| `animation-systems-engineer` | Specialist | Animation | Skeletal animation runtime, compression, blend trees and anim graphs, IK, root motion, motion matching, ragdoll hand-off |
| `scripting-runtime-engineer` | Specialist | Scripting runtime | Gameplay framework on the ECS, scripting VM or embedded language (an ADR choice), visual scripting runtime, hot reload, sandboxing, bindings |
| `audio-engine-engineer` | Specialist | Audio engine | Mixer, DSP graph, spatialization, streaming and decoding, voice management, middleware or in-house (an ADR choice) |
| `engine-technical-writer` | Specialist | Engine docs | API reference from headers and traits, module overviews, migration guides from ADRs, editor user docs; reports to `chief-engine-architect` |
| `cinematics-sequencer-engineer` | Specialist | Cinematics and camera | Timeline evaluation, scrubbing, camera cuts, offline movie output; reports to editor-architect and coordinates runtime with simulation-systems-lead |
| `editor-architect` | Lead | Engine editor | Editor architecture, reflection/serialization, undo/redo transactions, play-in-editor, plugins, the editor UI-framework ADR (own retained UI / Qt 6 / Dear ImGui / web UI); coordinates the three editor specialists |
| `level-editor-engineer` | Specialist | Level editor | Viewport, picking, gizmos, outliner, prefabs, world partition |
| `editor-ui-framework-engineer` | Specialist | Editor UI | Docking, property inspector, asset browser, IME/DPI/accessibility on the ADR-chosen framework |

`engine-programmer`, `performance-analyst`, `devops-engineer`,
`technical-artist` and `tools-programmer` stay in a Custom project and work
with these agents; `tools-programmer` keeps in-game debug tools and the
standalone pipeline and batch tools (`tools/asset-pipeline/` and the other
`tools/` rows of `.claude/docs/custom-engine-layout.md` that name it;
`tools/ci/`, `tools/build/` and `tools/cook/` are
`asset-build-tooling-engineer`'s), the editor is `editor-architect`'s.