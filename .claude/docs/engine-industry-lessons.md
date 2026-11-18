# Engine Industry Lessons

Applies only when `engine.name` is `Custom`; on any other engine, ignore this file.

This file records published lessons for design decisions, not architectures to copy. Each lesson is an input to an ADR option, never a default: an ADR that cites one names the lesson's cost beside its gain and measures the option against this project's own budgets.

Each lesson is dated. A talk describes the engine as it was when the talk was given, not as it is today. Every fact below is a claim in `docs/research/aaa-engine-support-2026/claims.jsonl`, backed by the studio's own published talk, proceedings page, documentation or blog. A principle known only from secondary reporting is left out. Game titles and engine names identify the source and nothing more.

## Frostbite (EA)

### Frame graph: passes and transient resources declared per frame

**Principle (2017):** The frame is a graph that holds render passes and resources as nodes. Frostbite builds it from scratch every frame, because the rendering configuration may change dynamically (player actions, cut-scenes). Rendering features are implemented in a decoupled and modular way while keeping efficiency, and one goal of the re-architecture behind it was that passes no longer baby-sit memory allocation and aliasing.

**Problem it solved:** A World Renderer re-architecture in 2016 set out to address accumulated technical debt and to improve extensibility and maintainability.

**Cost:** Rebuilding the graph every frame assumes the setup phase is relatively cheap, with a relatively small number of render passes and resources. The price the talk names is a template-heavy setup API.

**Source:** Yuriy O'Donnell, "FrameGraph: Extensible Rendering Architecture in Frostbite", GDC 2017 slides with speaker notes and the GDC Vault session page (ledger sources `frostbite-framegraph-gdc2017`, `gdcvault-framegraph-2017`).

## Naughty Dog engine

### Fiber-based jobs and frame-centric data lifetime

**Principle (2015):** Jobs run on fibers and can yield to other jobs in the middle of execution. The engine design is frame-centric: per-frame data such as FrameParams greatly simplifies data lifetime and memory management, and the talk sums up that a frame-centric design simplifies the engine.

**Problem it solved:** The PS3 job system ran jobs to completion without ever yielding, and in the multi-frame engine every programmer was solving the same problem.

**Cost:** With fibers, system synchronization primitives can no longer be used, so atomic spin locks are used almost everywhere. A fiber switched in the middle of a function can wake up with the wrong thread-local storage (TLS) pointer.

**Source:** Christian Gyrling, "Parallelizing the Naughty Dog Engine Using Fibers", GDC 2015 slides and the GDC Vault session page (ledger sources `naughtydog-fibers-gdc2015`, `gdcvault-naughtydog-fibers-2015`).

## id Tech (id Software)

### Few shaders: coherent branching over permutations

**Principle (2016):** An initial requirement of this id Tech iteration was "no shader permutations insanity": about 100 shaders and about 350 pipeline states. Lighting uses the same shader for all static geometry, and the talk recommends static or coherent branching. The team tried as much as possible to mitigate potentially time-consuming work and keep it simple.

**Problem it solved:** Given the relatively short development time and a substantial catch-up to do, the team had to pick its fights carefully.

**Cost:** The talk's lighting slides ask to keep an eye on VGPR pressure and to minimize nested loops and the worst-case path.

**Source:** Tiago Sousa and Jean Geffroy, "The Devil Is in the Details: idTech 666", SIGGRAPH 2016 Advances in Real-Time Rendering course, slides and speaker notes (ledger source `idsoftware-doom-siggraph2016`).

### GPU triangle culling and merged indirect draws

**Principle (2020):** The renderer culls triangles early on the GPU in a compute prepass, which removes about 70% of submitted triangles in a typical scene. It then merges the surviving triangles of multiple models into a single indirect index buffer; a single draw call for many models lowers CPU setup cost.

**Problem it solved:** DOOM Eternal has 3 times the on-screen triangle count of DOOM (2016), and issuing draw calls has a significant CPU cost.

**Cost:** Merged geometry has to use the same pipeline state, and the merging relies on a completely bindless GPU pipeline.

**Source:** Jean Geffroy, Axel Gneiting and Yixin Wang, "Rendering the Hellscape of DOOM Eternal", SIGGRAPH 2020 Advances in Real-Time Rendering course (ledger source `idsoftware-doometernal-siggraph2020`).

## Decima (Guerrilla Games)

### Streaming over a content graph

**Principle (2023):** Content subgraphs are separated by streaming links, and streaming strategies hold customizable logic for different domains. Files are reference counted, so no object is ever loaded more than once. The talk, published in 2023, describes Horizon Zero Dawn as shipped.

**Problem it solved:** The earlier Killzone loading system could not load content around the player dynamically.

**Cost:** A content graph must always be loaded fully, and opening and closing so many files is costly.

**Source:** Guerrilla Games, "Streaming the World of Horizon Zero Dawn", slides linked from the guerrilla-games.com page of 21 March 2023 (ledger source `guerrilla-streaming-hzd`).

### Visual programming compiled to native code

**Principle (2025):** A node graph's intermediate representation is forwarded to a language-specific backend that generates code (C++ or shader code), and generated C++ is linked into a dynamic library that can be hot-reloaded. The talk says visual programming made the studio's developers more independent from programmers.

**Problem it solved:** Content creators can't be expected to recompile the game just because of changes to some content.

**Cost:** As programmers step back, tools for debugging by users become all the more important, and when a programmer helps debug content, it costs time to get up to speed with the content's structure. An earlier generator that combined analysis and code generation, with no intermediate representation, was difficult to maintain.

**Source:** Bryan Keiren, "Nodes and Native Code: DECIMA's Visual Programming for Every Discipline", slides with speaker notes linked from the guerrilla-games.com page of 14 July 2025 (ledger source `guerrilla-nodes-native-2025`).

## Northlight (Remedy)

### Data described in script, with versioning and a permutation budget

**Principle (2024):** For Alan Wake 2, Remedy's technical vision for materials was to describe data and its use in Lua instead of C++, with versioning and patching in the same file. In the talk's technical design for shaders, the script file is pure Lua and patching is based on version number. The permutations of engine-provided shaders are a flat list, avoiding programmatic generation, and dynamic branching is preferred over a highly specific compile-time feature set.

**Problem it solved:** Patching between material data versions was error prone and time consuming.

**Cost:** The talk keeps the amount of permutations to a minimum to keep compile times and pipeline state changes low; Alan Wake 2 has about 2500 shaders.

**Source:** Tatu Aalto, "Modernizing geometry rendering in Alan Wake 2", REAC 2024 slides (ledger source `remedy-reac2024-aw2`, a file of about 248 MB).

## Snowdrop (Ubisoft Massive)

### One editor and node graphs shared across disciplines

**Principle (2024):** The original idea behind Snowdrop was to unify the look and feel of the different editors the studio used to create its games, and its NodeGraphs have proved a crucial tool for quick iterations. A GDC 2016 talk on The Division's AI highlights the positive effects of a tool shared by programmers and designers.

**Problem it solved:** One peril of bigger, more involved games is presenting that complexity to designers.

**Cost:** NOT SOURCEABLE — neither the Massive article nor the GDC 2016 session page states a cost of a shared editor or of NodeGraphs. The article's closing note, that "creative" solutions used when shipping The Division made their way into Snowdrop and stayed there and that 10 years later confused developers still sometimes ask about them, is not tied to either.

**Source:** Massive Entertainment, "Snowdrop Engine – Dream Architects", blog article of 11 December 2024, and Jonas Gillberg, "AI Behavior Editing and Debugging in 'Tom Clancy's The Division'", GDC 2016 Vault session page (ledger sources `massive-snowdrop-dream-architects`, `gdcvault-division-ai-2016`).

## Minecraft Bedrock (Mojang and Microsoft)

### A versioned, data-driven creator format

**Principle (2025):** Files made in older formats still work in newer versions of the game, but only if the format version is set correctly. A pack's `min_engine_version` helps the game identify whether any backwards compatibility is needed.

**Problem it solved:** The data stored in JSON files can grow or change over time; `format_version` lets the game load and parse them accurately.

**Cost:** Incorrect format versions are a frequent source of errors.

**Source:** Microsoft and Mojang, Minecraft Creator documentation, "Version Disambiguation" and "Add-Ons Reference: manifest.json" (ledger sources `mc-version-disambiguation`, `mc-pack-manifest`).

### One engine unified across platforms

**Principle (2017):** In 2017, with version 1.2.0, Pocket Edition became Minecraft: Bedrock Edition, unifying the various non-Java releases across platforms. Mojang calls the result a unified Minecraft that can be played on most devices.

**Problem it solved:** Versions of the game that could not play together. Mojang's 2017 FAQ calls a version that can play together with the others simply Minecraft, and gives the original Java PC version and all other isolated versions "Edition" names. Its stated aim was that the update would give more players the chance to connect in more ways, including cross-platform play.

**Cost:** The creator documentation warns that as content becomes more complex, it becomes less playable for certain audiences, and that low-end devices may only be able to render a six or eight-chunk radius.

**Source:** Microsoft and Mojang, Minecraft Creator documentation, "Differences between Minecraft Bedrock Edition and Minecraft Java Edition" and "Designing Gameplay for Various Devices"; Mojang, "Better Together FAQ", minecraft.net, 20 September 2017 (ledger sources `mc-bedrock-vs-java`, `mc-designing-for-devices`, `mc-better-together-faq`).

### Chunked worlds from seed and coordinates

**Principle (2025):** World generation combines the level seed and the three-dimensional XYZ coordinates of a block to generate a set of smoothly changing noise values, and biomes attempt to place their attached features chunk-by-chunk.

**Problem it solved:** NOT SOURCEABLE — the Mojang and Microsoft pages behind this lesson describe how seeded, chunk-by-chunk generation works and how creators use it, but none states the problem it was built to solve.

**Cost:** As of version 1.18, Bedrock and Java have seed parity (the same seed generates the same landscape), but only as long as the seed value is 9 or fewer characters. Feature placement order is not guaranteed within each pass. With a custom height range in a behavior pack, no more world generation takes place.

**Source:** Microsoft and Mojang, Minecraft Creator documentation, "Biome JSON and Overview", "Introduction to Features", "Survival Spawn Creation" and "World Generation Overview" (ledger sources `mc-biome-overview`, `mc-features-intro`, `mc-survival-spawn`, `mc-world-generation`).
