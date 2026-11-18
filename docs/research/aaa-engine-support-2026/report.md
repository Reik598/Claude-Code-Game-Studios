# AAA engine-development support audit, 2026

Research retrieved 15 November 2026; report assembled 16 November 2026.
Scope: Claude Code Game Studios agent framework, including the uncommitted
Custom-engine additions. This is a capability assessment, not engine certification.

## Executive Summary

The repository contains a substantial custom-engine development framework, but
the presence of agent definitions cannot establish complete AAA production
support. The defensible target is coverage of responsibilities, their boundaries,
and the evidence required to accept their work. Ubisoft describes core-engine
work through performance, modularity and scalability; EA describes Frostbite
through runtime and authoring disciplines; Guerrilla demonstrates the connection
between streaming, memory and asset conversion. Together these support a broad
capability model rather than a mandatory one-to-one mapping of job titles to
agents. [1][3][5]

The initial repository inspection found owners for core systems, jobs, memory,
ECS, platform integration, rendering, animation, physics, audio, scripting,
streaming, assets and editor tooling. Existing game-development roles also cover
engine AI, networking, UI, QA, security and release work. The new cinematics
agent existed but was not consistently registered in setup, roster and test
catalogue. That is an integration failure even though its instruction file is
present. These are initial observations; final repair and test results belong
to the implementation audit, not this research report.

The strongest current organizational evidence is Ubisoft's Snowdrop tools
vacancy: agent-assisted development still requires specifications, acceptance
criteria, editor stability and validation before multiple game teams receive
changes. Epic's automation and installed-build documentation independently
reinforce the need for layered tests and a usable delivered engine product.
[2][8][9] Accordingly, this framework should promise structured assistance with
engine development, while withholding claims about build success, performance,
platform readiness or release approval until the corresponding evidence exists.
Optional capabilities such as cloth, vehicles, hair and neural inference need
explicit owners and activation criteria; they need not become separate agents.

## Introduction

The user asked whether the repository supports AAA game-engine development in
2026 alongside game development, and whether Copilot's five fix batches are
finished. This report supplies the external baseline and maps it onto the
repository. It does not implement an engine or reproduce a studio's private
organization chart. “AAA” has no universal role checklist in the sources reviewed.
The working definition here is a reusable engine serving demanding productions,
with controlled runtime cost, reliable content creation, supported platforms and
repeatable releases to game teams.

Research used primary employer vacancies, engine documentation and studio
technical-talk abstracts. Four independent organizational sources appear:
Ubisoft, EA, Guerrilla and Epic. Multiple Epic pages describe different systems
but are not counted as independent corroboration of an industry-wide claim.
Historical talks establish enduring engineering responsibilities; retrieval in
2026 does not make them newly introduced technology. A live vacancy describes
one employer's current expectations, not every studio's operating model.

Local evidence comprises `.claude/docs/custom-engine-layout.md`, the agent
roster, affected agent definitions, setup and gate instructions, and the test
catalogue. These files describe intended behavior. They do not show that Claude
successfully followed every instruction in a real project. Keep that distinction
when assessing a green static check or a completed documentation change.

## Main Analysis

### 1. Engine teams own reusable systems and their production constraints

Ubisoft's core-engine vacancy emphasizes maintainable systems, compatibility,
performance and scalability. EA's engine description spans audio, animation,
cinematics, scripting, physics, destruction, rendering and effects. Guerrilla's
packaging talk connects runtime loading with memory allocation and content
conversion. These examples support the inference that a useful engine framework
must cover both subsystems and the contracts between them. [1][3][5]

The repository's division between `chief-engine-architect`, domain leads and
specialists is a plausible way to organize that work. Existing
`ai-programmer`, `network-programmer` and `ui-programmer` roles can serve engine
development when their reusable runtime responsibilities are explicit. Splitting
every specialty into another agent would not itself resolve ambiguous ownership.
The important question is who accepts changes to a boundary, and which other
owner must validate the effect.

The following map reflects agent names present during inspection. It records
coverage and acceptance expectations, not executed implementation or tests.
The module table and each agent's Custom section are the local evidence.

| Capability | Existing accountable roles | Required boundary/evidence |
|---|---|---|
| Engine architecture and public contracts | `chief-engine-architect`, `technical-director` | Engine-internal versus project-wide decisions; API/ABI and migration review |
| Foundation, jobs, memory, ECS | `core-systems-lead`, `concurrency-job-system-engineer`, `memory-allocator-specialist`, `ecs-dod-architect` | Allocation lifetime, scheduling dependencies, races and determinism tests |
| OS, input, crash and lifecycle | `platform-engineer` | Device/user lifecycle, symbolized crash path, platform-specific smoke tests |
| Graphics backend and frame scheduling | `rendering-lead`, `rhi-backend-engineer`, `render-graph-specialist` | Queue ownership, barriers, lifetime and validation-clean captures |
| Shaders and visual features | `shader-pipeline-engineer`, `graphics-features-engineer`, `vfx-runtime-engineer` | Cook/cache keys, feature fallbacks, GPU budgets and reference images |
| Physics, animation and cinematics | `simulation-systems-lead`, `physics-simulation-engineer`, `animation-systems-engineer`, `cinematics-sequencer-engineer` | Tick ownership, pose transfer, replay scope and scrub/event tests |
| Scripting and gameplay framework | `scripting-runtime-engineer`, `gameplay-programmer` | Runtime bindings, reload lifetime, trust model and game API separation |
| Audio runtime | `audio-engine-engineer`, `audio-director` | Device deadlines, voice/stream limits and content integration |
| Streaming and asset conversion | `world-streaming-engineer`, `asset-build-tooling-engineer` | Residency, cancellation, cache correctness and reproducible cook output |
| AI/navigation and networking | `ai-programmer`, `network-programmer`, `online-services-engineer` | Runtime versus authored behaviors; transport/replication versus service identity |
| Editor, runtime UI and text | `editor-architect`, `level-editor-engineer`, `editor-ui-framework-engineer`, `ui-programmer`, `localization-lead` | Undo/serialization, automation commands, text/input/accessibility and shipping isolation |
| Verification and performance | `qa-lead`, `qa-tester`, `performance-analyst`, engine leads | Harness implementation, target matrix, regressions, sanitizer and GPU evidence |
| Release, dependencies and documentation | `release-manager`, `devops-engineer`, `security-engineer`, `engine-technical-writer` | Consumer builds, package provenance, compatibility and upgrade documentation |

This map should be tested against actual routing. For example, a cinematic
timeline request must reach the sequencer owner and its editor collaborator,
and a multiplayer transport change must not be mistaken for a matchmaking
service change. A module can be listed and still be effectively unsupported
when setup never selects its agent or a skill never delegates work to it.

### 2. Authoring and delivery infrastructure are part of the engine

Guerrilla's content packaging work addresses deterministic analysis, incremental
updates and the tradeoff between duplication on disk and efficient loading.
Epic documents reusable derived data and dependency-aware build automation.
These sources support explicit responsibility for asset conversion, caching,
distribution and iteration time; runtime rendering alone is insufficient.
[5][7][13]

The existing `asset-build-tooling-engineer` and `world-streaming-engineer`
provide appropriate owners, with `devops-engineer` owning execution
infrastructure. Their contract should identify source inputs, cooker/compiler
versions, target settings, output schema and cache invalidation. A cache hit
must reproduce the output that a valid fresh cook would produce. The runtime
side must identify cancellation, loading failure and memory-pressure behavior.
Those are proposed acceptance expectations derived from the capabilities,
not measurements made in this repository.

Shared infrastructure also introduces a security boundary. Epic explicitly
describes Zenserver as unauthenticated and suitable for trusted environments,
directing untrusted deployments toward another solution. The general lesson is
to assign cache trust, provenance and access controls jointly to the tooling
and security owners. Do not copy a vendor's configuration example without
matching its assumptions. [14]

Editor work is equally substantial. The Snowdrop vacancy describes ownership
of a major editor system, adherence to UX architecture, command-level automation
and controlled deployment across game productions. The repository's editor
architecture, level-editor and UI-framework split is credible if operations
remain transactional, serializable, automatable and testable. Those acceptance
properties matter more than the number of editor specialists. [2]

### 3. Runtime integration needs explicit cross-domain contracts

Epic's audio description separates audio rendering from the game-facing sound
selection work and explains buffering, underruns and platform differences.
This supports a separate audio deadline rather than treating all work as a
sum of frame phases. The repository's audio owner should coordinate with
platform lifecycle, streaming and gameplay without allowing unrelated work
to make callback execution unbounded. [10]

Guerrilla's HTN talk shows that AI includes reusable planner implementation,
generated code and in-game diagnosis. Epic's replication design separates
replicated state from gameplay and assigns filtering and priority to the
replication system. These are examples of engine-level AI and network
responsibilities that existing roles can own, provided game-specific behaviors
and authority policies remain separate concerns. [6][11]

Physics/animation handoff is another concrete acceptance point. The local
animation definition names pose transfer, velocities, step-boundary changes
and renderer skinning data. A ragdoll request from gameplay does not give
animation permission to redefine physics ownership. Similarly, render-graph
lifetimes cannot be validated by CPU pass order alone when queues overlap.
The initial fix batches address these contracts; final verification must
inspect the examples and exercise the relevant scenario rather than search
only for the corrected vocabulary.

Destruction, cloth and vehicles were explicitly deferred behind an ADR in the
inspected physics role. That is honest scope control, but cannot substantiate a
claim that those systems are implemented. A useful framework must still route
such requests to `simulation-systems-lead`, then assign physics, animation,
assets and rendering responsibilities. Hair likewise spans simulation,
rendering and content feedback in EA's example. No separate hair agent is
required when those owners and acceptance evidence are explicit. [4]

### 4. Verification and consumer releases determine practical support

Epic documents unit, feature, stress and screenshot-comparison tests, and
separately documents distributing installed engine builds to team members who
do not compile the engine. Ubisoft's editor role demands validation before
production use. Taken together, these sources support treating an engine as a
product with consumers, rather than marking it ready because source files or
instructions exist. [2][8][9]

The repository's `qa-lead` Custom section already distinguishes low-level,
determinism, golden-image, GPU-validation, sanitizer and benchmark evidence.
Its `release-manager` section distinguishes engine releases from game
releases and asks consuming teams to confirm integration builds. These are
useful requirements. They still need executable harnesses and retained outputs
in each engine project. A test catalogue entry is a specification, not a test
result; an unavailable target runner is unassessed, not passed.

The following acceptance matrix preserves both sides of the requested scope.
These are checks to perform, not claims that this research agent executed them.

| Area | Custom-engine acceptance | Existing game-development parity |
|---|---|---|
| Setup and selection | Every registered engine owner can be selected and reached; unsupported toolchains are reported | Web/Godot/Unity/Unreal setup retains engine-specific choices |
| Paths and rules | C++ and Rust module layouts activate the intended domain rules | Game paths keep gameplay, UI, network and asset rules |
| Architecture and story routing | Engine changes reach engine owners and the right architecture/frame gates | Game feature changes retain design and gameplay review |
| Build and tests | Failed builds, missing runners and zero tests cannot produce a success claim | Existing runners and their exit-status handling remain intact |
| Performance and security | Missing CPU/GPU/subsystem captures or sanitizer/fuzz evidence is explicit | Vendor-engine projects are not falsely required to produce custom-engine artifacts |
| Releases | API, ABI, asset-format and consumer compatibility are assessed | Game release checks, audience and approvals remain available |
| Optional capabilities | Selection records owner, integration contracts and evidence; deferred means deferred | Unneeded engine features do not block a game workflow |

Neural inference is an optional capability worth making routable in a 2026
framework. Epic's NNE documentation exposes different runtime providers and
CPU/GPU execution choices. The inferred ownership is `ai-programmer` for
runtime integration, with animation or rendering owning its use in their
systems, build tooling owning model conversion and security reviewing model
provenance. This is a recommended extension of responsibility, not a claim that
all of it was already present. The retrieved documentation marks NNE beta;
adoption needs project requirements and measured budgets. [12]

## Synthesis & Insights

The evidence supports three levels of completeness. **Coverage** means a
capability has an owner and documented boundaries. **Operational support** means
setup, rules, skills and tests can route and verify work. **Production proof**
means a real engine project has built and exercised the result on its required
platforms and workloads. The first two are realistic outcomes for this
repository; the third belongs to each consuming project. This distinction is
an analytical model synthesized from the sources, not an industry standard.

For the original batches, initial inspection found A1's alignment, render-graph,
cache and Cargo corrections in the files; A2's audio and SPSC corrections and
named optional simulation scope; A3's expanded existing roles and cinematics
definition; B's new rules and module ownership table; and C1's evidence-aware
build, benchmark and security language. These observations establish that work
was performed, not that every defect was fixed. The unregistered cinematics
agent demonstrates why the integration layer needs its own audit.

No batch should be labelled complete solely from this report. A1/A2 need
technical example review and executable checks where feasible. A3/B need
registry, ownership, path and handoff consistency. C1 needs failure-path tests:
missing evidence and unsuccessful builds must prevent positive conclusions.
Game-development parity must be checked at the same time, because a new Custom
branch can otherwise accidentally replace a vendor-engine path.

## Limitations & Caveats

This is a public-source, bounded review. It does not establish private console
certification requirements, SDK access, proprietary security controls or a
studio's complete staffing structure. Employer vacancies are selective and may
close. Engine documentation is living material; platform choices, command
flags and feature maturity must be checked against a project's pinned version.
Historical talk abstracts demonstrate production concerns without exposing all
implementation details.

The retrieved EA hair page displays 3 November 2026; that date is recorded as
displayed and is not independent proof of original publication or first
shipping use. It is used only as evidence of the collaboration described in
its text, not as evidence that hair technology originated in 2026. Other enduring disciplines should not be marketed as newly
required in 2026. Likewise, an agent-assisted workflow in one current Snowdrop
vacancy does not establish industry-wide adoption.

No commercial engine build, hardware benchmark, console run or live Claude
behavioral session was performed by this research task. Local mappings refer
to inspected files in an evolving uncommitted changeset. The parent audit owns
final code changes, tests and completion status. Documentation validation checks
report structure and source accessibility; it cannot establish technical
correctness or certify readiness.

## Recommendations

Finish integration before enlarging the roster: reconcile setup, agent
catalogue, ownership tables, rules, delegations and behavioral specs. Add a
check that fails when an advertised owner cannot be reached or a registered
module is uncovered. Keep engine/game paths and vendor-engine setup distinct,
and exercise those branches with disposable fixtures.

Make optional capabilities discoverable through existing owners. Record
whether destruction, cloth, vehicles, hair or inference are selected, deferred
or excluded for a project. Selection should trigger an ADR, budgets, runtime
and authoring responsibilities, and acceptance evidence. Do not create a
specialist solely to make a checklist longer.

Use narrowly worded completion claims. “Role and workflow coverage checked”
can follow a structural audit. “Behavior verified” needs the relevant
scenario results. “Engine builds,” “within budget,” and “ready for release”
need actual build, capture and consumer evidence. Preserve missing evidence as
visible work rather than converting it into a favorable verdict.

## Bibliography

[1] Ubisoft (undated). "Engine Programmer (Far Cry)". [Employer vacancy](https://www.ubisoft.com/en-us/company/careers/search/744000140270589-engine-programmer-far-cry-). Retrieved 2026-11-15.

[2] Ubisoft (undated). "Senior UX and Core Tools C++ Engineer [Snowdrop]". [Employer vacancy](https://jobs.smartrecruiters.com/ubisoft2/744000160823460). Retrieved 2026-11-15.

[3] Electronic Arts (undated). "The Engine". [Frostbite](https://www.ea.com/frostbite/engine?isLocalized=true). Retrieved 2026-11-15.

[4] Electronic Arts (2026, displayed date). "Frostbite Hair Rendering and Simulation Part 1". [Engineering article](https://www.ea.com/frostbite/news/frostbite-hair-rendering-and-simulation). Retrieved 2026-11-15.

[5] Guerrilla (2023). "Space-Efficient Content Packaging for Horizon Forbidden West". [Technical talk](https://www.guerrilla-games.com/read/space-efficient-content-packaging-for-horizon-forbidden-west). Retrieved 2026-11-15.

[6] Guerrilla (2024). "HTN Planning in Decima". [Technical talk](https://www.guerrilla-games.com/read/htn-planning-in-decima). Retrieved 2026-11-15.

[7] Epic Games (undated). "BuildGraph for Unreal Engine". [Documentation](https://dev.epicgames.com/documentation/unreal-engine/buildgraph-for-unreal-engine). Retrieved 2026-11-15.

[8] Epic Games (undated). "Create an Installed Build". [Documentation](https://dev.epicgames.com/documentation/unreal-engine/create-an-installed-build-of-unreal-engine). Retrieved 2026-11-15.

[9] Epic Games (undated). "Automation Test Framework". [Documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/automation-test-framework-in-unreal-engine). Retrieved 2026-11-15.

[10] Epic Games (undated). "Audio Mixer Overview". [Documentation](https://dev.epicgames.com/documentation/unreal-engine/audio-mixer-overview-in-unreal-engine?lang=en-US). Retrieved 2026-11-15.

[11] Epic Games (undated). "Introduction to Iris". [Documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/introduction-to-iris-in-unreal-engine). Retrieved 2026-11-15.

[12] Epic Games (undated). "Neural Network Engine Overview". [Documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/neural-network-engine-overview-in-unreal-engine). Retrieved 2026-11-15.

[13] Epic Games (undated). "Setting up an Unreal Engine Studio the Epic Way". [Studio workflow guidance](https://dev.epicgames.com/community/learning/tutorials/8JYW/epic-for-indies-setting-up-an-unreal-engine-studio-the-epic-way). Retrieved 2026-11-15.

[14] Epic Games (undated). "Zenserver as Shared DDC". [Documentation](https://dev.epicgames.com/documentation/unreal-engine/set-up-zen-storage-server-as-shared-ddc-for-unreal-engine?lang=en-US). Retrieved 2026-11-15.

## Methodology Appendix

Queries covered core-engine vacancies, Snowdrop tools, Frostbite disciplines,
Decima asset pipelines and AI, plus Epic build, test, audio, networking and
inference documentation. Search snippets were expanded into page text where
available; unrelated secondary reporting was excluded from the evidence set.
The source registry preserves URLs, publisher, date status and retrieval method.
The evidence ledger stores one short quotation per source, within 25 quoted
words per source, and the claim ledger separates observations from inferences.

Repository mapping used existing owner definitions rather than inferred job
titles. Recommended acceptance checks are explicitly prospective. No claim of
comprehensive behavioral validation follows from reading a file. Source
accessibility and report-structure validator outcomes are recorded in
`run_manifest.json`; the implementation task records its own executed checks.
Artifacts stay in this repository under the user's machine-change constraints;
no HTML/PDF export or GUI launch is needed for this code-review deliverable.
