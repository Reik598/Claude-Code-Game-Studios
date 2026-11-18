# Engine development: ownership and acceptance

Read when planning a Custom-engine project, introducing a module, or reviewing
coverage. The baseline is the same as game development: specifications, Accepted
ADRs, implementation stories, scoped owners, tests and review before completion.
Use `.claude/docs/custom-engine-layout.md` for actual paths and aliases.
Research and limitations: `docs/research/aaa-engine-support-2026/report.md`.

## Responsibilities

| Capability | Accountable roles | Acceptance evidence |
|---|---|---|
| Architecture and engine/game boundary | chief-engine-architect, technical-director, lead-programmer | module specs, dependency checks, Accepted ADRs, API review |
| Core, memory, jobs, ECS and math | core-systems-lead and its specialists | allocator edge cases, sanitizer runs, scheduler stress, bounded storage, determinism at the declared scope |
| Platform, input, lifecycle, media and XR | platform-engineer (XR runtime) with rendering/audio leads; graphics-features-engineer for XR rendering | target-specific builds, suspend/resume, device loss, input mapping and crash capture tests |
| XR experience design: comfort, locomotion, world scale, interaction | xr-experience-designer via game-designer, on any engine whose `platform.targets` contains `XR`; on Custom it requests features from platform-engineer (XR runtime) and graphics-features-engineer (XR rendering) | comfort options as project settings, comfort playtests and VR test evidence on a target headset (qa-lead) |
| RHI, frame graph, shader pipeline, graphics and VFX | rendering-lead and its five specialists; asset-build-tooling-engineer for the GPU test runner | validation-layer runs, cross-queue tests, reference images, shader/PSO budgets, optimized captures |
| Lighting and look-dev | lighting-artist via art-director, on any engine (art-director keeps lighting direction, technical-artist lighting shaders); on Custom it requests lighting features from graphics-features-engineer | per-scene light, exposure, grading and bake settings recorded against the art bible, and captures art-director reviews |
| Physics, animation, scripting and audio | simulation-systems-lead and its four specialists | handoff tests, simulation state hashes where promised, sandbox threat tests, device-deadline captures |
| Cinematics and camera | cinematics-sequencer-engineer via editor-architect | seek/event-window tests, temporal-history reset, frame-accurate offline output |
| Cinematic design: shots, camera, previs and edit | cinematic-designer via narrative-director, on any engine (story stays with narrative-director, dialogue with writer); on Custom it requests sequencer features from cinematics-sequencer-engineer | shot lists and previs narrative-director approves, and the cut played back in the engine's sequencer |
| AI/navigation runtime | ai-programmer via lead-programmer | path query budgets, streamed nav data, planner/debugger tests; gameplay owns authored decisions |
| Replication and online services | network-programmer, online-services-engineer | protocol compatibility, authority/replay, loss/latency tests, service failures and security review |
| Runtime UI and text | ui-programmer (owns the text stack in engine/ui/; editor-ui-framework-engineer consumes it under an ADR), localization-lead, accessibility-specialist | shaping, fallback, IME, localization, screen-reader and scaling tests |
| Editor and content authoring | editor-architect, level-editor-engineer, editor-ui-framework-engineer, technical-artist | undo/redo, persistence, PIE isolation, picking, accessibility and source-control conflict tests |
| Assets, cookers, cache and streaming | asset-build-tooling-engineer, world-streaming-engineer, devops-engineer | reproducible cook, cache invalidation, corrupt-input tests, peak residency and load-time captures |
| Build, distribution and engine releases | devops-engineer, release-manager, engine-technical-writer | platform/API/config matrix, installed artifacts and symbols, candidate-bound consumer tests, migration and team sign-off |
| QA, performance and security | qa-lead, qa-tester, performance-analyst, security-engineer | nonzero test counts, stress/soak, benchmark baselines, sanitizer/fuzz receipts, dependency/license inventory |

Which agent owns a module, and which lead it reports to, is stated once, in the
Owner and Lead columns of `.claude/docs/custom-engine-layout.md`; the roles above
name who is accountable for a capability and never pair a module with another
owner.

These are responsibility assignments, not proof of implementation. Several roles
may be performed by one agent at small team sizes; their checks still apply.
Console SDK compliance requires the project's authorized SDK and target tests.

## Optional capabilities need an explicit decision

Destruction, cloth, vehicles and hair simulation belong to
physics-simulation-engineer via simulation-systems-lead; hair rendering belongs
to graphics-features-engineer via rendering-lead. Their content cooking goes to
asset-build-tooling-engineer and authoring to editor-architect. Terrain and
procedural-world work similarly spans graphics, streaming, physics and editor
owners. Scope, data contracts, budgets and target support require an ADR before
implementation. Deferred features stay visible as deferred in the module map.

Neural inference is optional. When required, chief-engine-architect assigns a
module owner and records runtime/model pins, supported operators and devices,
model provenance, memory/latency budgets, fallback, security boundary and
CPU/GPU execution placement. Rendering-lead owns graph integration; simulation
owners define determinism consequences; security-engineer reviews model inputs.
No generative-AI feature or dedicated job title is a universal AAA requirement.

## Handoffs and workflow parity

| Change | Required interaction | Workflow and evidence |
|---|---|---|
| New subsystem | owner → lead → chief-engine-architect | module spec + `/architecture-decision` engine mode, `/architecture-review`, stories with acceptance criteria |
| Implementation | `/dev-story` → module owner through lead | red/green test evidence, configured build, `/code-review`, `/story-done` |
| Public engine API | engine owner ↔ lead-programmer and game consumer | `/api-review`, deprecation/migration guide, consumer integration test |
| Tick or frame graph | core ↔ simulation ↔ rendering leads | `/team-frame-pipeline`, `/benchmark-report`, CEA-FRAME-BUDGET |
| Animation/ragdoll | animation ↔ physics | single step-boundary ownership, spaces/units and velocity transfer tests |
| Asset format | cooker ↔ streaming ↔ editor | versioning, cache-key inputs, failure/upgrade tests and memory budget |
| Cinematics | sequencer ↔ animation/audio/renderer/streaming | event policy, media clocks, camera cuts, history reset and offline-readback tests |
| Optimization | `/team-polish` → measured hotspot owner | comparable before/after captures, `/perf-regression-triage` |
| Engine delivery | release-manager ↔ writer ↔ game teams | `/engine-release`, exact tested candidate, migration guide and sign-off |

At each handoff record input/output ownership, units/space, thread or queue,
lifetime, synchronization, failure policy and the test proving the contract.
A missing measurement is NOT ASSESSED. A static prompt audit cannot establish
that Claude follows these instructions in a live session; retain behavioral
specs and run end-to-end scenarios before asserting operational parity.
