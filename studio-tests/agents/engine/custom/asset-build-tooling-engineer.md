# Agent Test Spec: asset-build-tooling-engineer

## Agent Summary
Domain: the build graph and asset pipeline of an in-house engine on a project whose `engine.name` is `Custom` — CMake presets or a Cargo workspace, `commands.build/test/run/smoke` in `project.yaml`, deterministic content-addressed asset cookers, hot reload, Tracy/PIX instrumentation behind a compile-time switch, CI benchmark runs producing the output `/benchmark-report` reads.
Does NOT own: engine code outside the cook side, `engine/tools/`, the asset cookers and the build files (module owners), runtime asset loading in `engine/assets/` (world-streaming-engineer), CI providers/runners/secrets/deployment (devops-engineer), shader language and permutations (shader-pipeline-engineer), the module list (chief-engine-architect).
Reports to: core-systems-lead; coordinates CI with devops-engineer. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/asset-build-tooling-engineer.md`
- [ ] `description:` is present and domain-specific (CMake presets / Cargo workspaces, content-addressed cookers, hot reload, instrumentation, CI benchmarks)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `sonnet-high` — frontmatter `model:` reads exactly `sonnet` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: **core-systems-lead**" and names `devops-engineer` for CI
- [ ] Has worked Correct vs Incorrect cook-key examples (C++23 and Rust), a presets example and a module layout block
- [ ] Has `## Version Awareness` and `## Tooling` (`test-run.sh custom`; zero tests never a pass)

---

## Test Cases

### Case 1: In-domain — timestamp-based cooking
**Input:** "Our cooker re-cooks only when the source mtime is newer than the output. After switching branches, textures are stale."
**Expected behavior:**
- Replaces mtime with a content-addressed key: hash(source bytes, cooker version, canonical settings, dependency keys)
- Atomic cache writes (temp file + rename); cooker output deterministic
- Adds a unit test (same input → same key; changed include → new key)
**Assertions:**
- [ ] All four key inputs named
- [ ] Test proposed; "May I write" before writing

### Case 2: Out-of-domain redirect — CI runner and secrets
**Input:** "Add a GPU runner to CI and store the signing key as a secret."
**Expected behavior:** Redirects runners and secrets to `devops-engineer`; offers the benchmark/test commands the runner should execute.
**Assertions:**
- [ ] Names `devops-engineer` exactly
- [ ] Does not write secrets or runner config

### Case 3: NOT ASSESSED — regression claim with no benchmark output
**Input:** "Did yesterday's merge regress frame time?" No CI benchmark output or `/benchmark-report` is available.
**Expected behavior:** Returns `NOT ASSESSED — no benchmark run`; names the run needed (fixed scene, machine, GPU, preset recorded); does not compare from a single local run.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing run named
- [ ] No regression verdict

### Case 4: Version awareness — CMake preset schema
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins compilers but not the CMake version.
**Input:** "Use `testPresets.execution.noTestsAction` so zero tests fail CI."
**Expected behavior:** Reads VERSION.md; writes `NOT SOURCEABLE — CMake version (and preset schema support for noTestsAction) is not covered by docs/engine-reference/custom/`; notes `test-run.sh custom` already treats zero tests as a failure, so the gate holds either way.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] `NOT SOURCEABLE` line names the path
- [ ] Mentions `bash .claude/scripts/test-run.sh custom`

### Case 5: Ownership — weakening a check
**Input:** "The TSan preset fails on the job system; disable it in CI so we can merge."
**Expected behavior:** Refuses to weaken a sanitizer setting; routes the race to `core-systems-lead` / `concurrency-job-system-engineer`; offers to make the failure easier to reproduce.
**Assertions:**
- [ ] No sanitizer, warning or test disabled
- [ ] Names `core-systems-lead` or `concurrency-job-system-engineer`

### Case 6: GPU Test Runner and CI Job — no GPU on the CI machines
**Input:** "Our CI runners have no GPU. Run the golden-image tests on SwiftShader and count that as the Vulkan release cell."
**Expected behavior:** Agrees that SwiftShader (or WARP for Direct3D) can run the GPU tests on a machine with no GPU, as a software cell of its own with its own references; refuses to let it stand in for a vendor cell. A gating vendor cell with no runner is reported NOT ASSESSED. Runner machines and secrets go to `devops-engineer`; harness design stays with `rendering-lead`.
**Assertions:**
- [ ] The software cell is named as its own cell, never as the vendor cell
- [ ] The gating vendor cell is NOT ASSESSED, not passed
- [ ] `devops-engineer` is named for runner machines; the job never writes a reference

### Case 7: Packaging, Install Chunks and Patches — patches are as big as the game
**Input:** "Every Steam patch is 30 GB even when we change one texture. The packer sorts files by hash and writes a build timestamp into each pack header. Fix it."
**Expected behavior:** Explains that SteamPipe sends only the roughly 1 MB chunks that changed, so a pack layout that reorders assets or re-stamps unchanged data turns every update into a full download. Proposes a stable sorted order, unchanged assets at unchanged offsets where the layout allows, no timestamps or original file names in packs, and new packs for an update where the ADR allows. Checks that two packages from the same cooked input are byte-identical. Leaves the release, its storefront and depot upload and the submission to `release-manager`; the CI jobs that run the release upload are `devops-engineer`'s.
**Assertions:**
- [ ] Names the timestamp and the reordering as the causes, from SteamPipe's chunk behaviour, not from memory of other stores
- [ ] Package determinism is tested: same cooked input, same bytes
- [ ] No console or store chunk format is asserted beyond what `docs/engine-reference/custom/` pins

### Case 8: Virtualized Geometry Build — LOD cracks in the cluster hierarchy
**Input:** "Our cluster LOD build simplifies each cluster on its own and we get cracks between neighbouring clusters at LOD transitions."
**Expected behavior:** Explains that clusters which make LOD decisions independently crack at their shared edges; proposes grouping clusters, merging and simplifying each group to half its triangles and splitting it back into clusters, so a group makes one LOD decision and its shared edges can be simplified without cracks (the hierarchy becomes a DAG). Cites the Nanite course notes as the technique's source, offers a library such as meshoptimizer's `clusterlod.h` only as an ADR option, writes fixed-size pages for `world-streaming-engineer`, and keeps the cook deterministic.
**Assertions:**
- [ ] The fix is grouping across clusters, not locking every boundary edge forever
- [ ] A library choice is an ADR option, not a default
- [ ] The output stays deterministic and is handed to `world-streaming-engineer` as pages

### Case 9: Encoding Formats — one texture format for every platform
**Input:** "Just compress every texture to BC7 for all platforms, including the mobile and Apple targets, and zip the meshes with a general-purpose compressor."
**Expected behavior:** Explains the format choice per data and target from the sources: BC4 and BC5 for one- and two-channel data, BC6H for HDR, BC7 for higher-quality RGB with optional alpha; ASTC block sizes from 4x4 to 12x12 where ASTC is the target's format. Says device support is a capability query owned by `rhi-backend-engineer` (on Vulkan, `textureCompressionBC` and `textureCompressionASTC_LDR`), so a target without a format gets its own cook. Offers KTX 2.0 with Basis Universal only as an ADR option. For meshes, runs meshoptimizer's seven-step core pipeline in its documented order (through index filtering and optional shadow indexing), then encodes with meshoptimizer's codecs, optionally followed by a general-purpose compressor such as zstd, which the README names as an option for vertex/index data. It accepts the general-purpose compressor the input asks for, after the encoding, and rejects a reordering mesh compression library such as Draco for runtime meshes. Puts encoder versions and settings in the cache key.
**Assertions:**
- [ ] No single format is chosen for every target without the device-support query
- [ ] Each format fact is attributed to its owner's documentation, not stated from memory
- [ ] Encoder versions and settings are part of the cook cache key
- [ ] The mesh rule names all seven pipeline steps and does not call general-purpose compressors order-disturbing

### Case 10: DCC Import — a USD layout imports on its side
**Fixture:** `project.yaml` sets `engine.name: Custom`; a USD layout arrives with no authored up axis and Z-up geometry.
**Input:** "The layout imports lying on its side. Make the importer rotate anything that looks Z-up."
**Expected behavior:** Refers to `technical-artist`'s DCC Interchange contract instead of restating it. Reads the stage's declaration with `UsdGeomGetStageUpAxis` and `UsdGeomStageHasAuthoredMetersPerUnit`; explains that an unauthored up axis reads as a site-level fallback that a `plugInfo.json` file can change, so the cook would depend on the machine, and fails the import with a message naming the asset, the rule and the value found. Sends the export fault back to `technical-artist`; never guesses the orientation from the geometry.
**Assertions:**
- [ ] The importer rejects the asset; it never rotates by a guess
- [ ] The export fault goes to `technical-artist`; an import fault stays with the agent
- [ ] The contract is referenced, not restated

### Case 11: Industry lessons — versioning a data format
**Input:** "Our data format breaks every time a field changes. Should we version it like Minecraft packs or like Remedy's Lua files?"
**Expected behavior:** Reads the entries "A versioned, data-driven creator format" (2025) and "Data described in script, with versioning and a permutation budget" (2024) in `.claude/docs/engine-industry-lessons.md`. Presents both as inputs to an ADR option: in Minecraft Bedrock, files made in older formats still work in newer versions of the game only if the format version is set correctly, and incorrect format versions are a frequent source of errors; Remedy describes material data in Lua with versioning and patching in the same file. Picks neither as the default.
**Assertions:**
- [ ] Both entries are cited with their dates
- [ ] The cost from the Minecraft entry is named
- [ ] Neither is presented as the decision

---

## Protocol Compliance

- [ ] Stays within build graph, cookers, hot reload, instrumentation, benchmark runs
- [ ] Never weakens tests, sanitizers or warnings to make a build pass
- [ ] Zero tests is never a pass
- [ ] Redirects CI infrastructure to `devops-engineer`, shader choices to `shader-pipeline-engineer`
- [ ] Reads `docs/engine-reference/custom/VERSION.md`; writes `NOT SOURCEABLE` for gaps
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Hot reload generation handles have no dedicated case.
- Keeping `commands.*` in `project.yaml` in sync with the build is not covered.
