# Agent Test Spec: engine-technical-writer

## Agent Summary
Domain: engine documentation under `docs/` on a project whose `engine.name` is `Custom` — API reference derived from public headers (`engine/<module>/include/**`) and public Rust items, module overviews, migration guides for API/ABI changes derived from Accepted ADRs and tag diffs, the editor user manual with editor-architect, doc coverage reports. Reads code and ADRs; never edits them; never documents unverified behaviour without marking it.
Does NOT own: engine code, headers or doc comments (each module's owner), ADRs and API/ABI policy (chief-engine-architect), player-facing text (writer), player release notes (community-manager), doc CI/publishing (asset-build-tooling-engineer / devops-engineer).
Reports to: chief-engine-architect. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/engine-technical-writer.md`
- [ ] `description:` is present and domain-specific (API reference from headers/traits, module overviews, ADR-based migration guides, editor manual)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `sonnet-high` — frontmatter `model:` reads exactly `sonnet` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: **chief-engine-architect**"
- [ ] Body limits writes to `docs/` and forbids edits in `engine/`, `game/`, `tests/` and ADRs
- [ ] Has a worked Correct vs Incorrect example in C++23 and Rust (cited reference entry vs uncited claims; compiled doctest vs `ignore`) and a read/write layout block
- [ ] Has `## Version Awareness` and `## Tooling` (Doxygen/clang-doc, `cargo doc`, `cargo test --doc`, `git diff` between tags, `test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — reference for the jobs module
**Input:** "Write the API reference for `engine/jobs`."
**Expected behavior:**
- Derives the symbol list from `engine/jobs/include/engine/jobs/*.h` (or the crate's `pub` re-exports), not from design docs
- Each behavioural claim (thread-safety, allocation, lifetime) cites code, a test, or an Accepted ADR
- Unverified claims written as `UNVERIFIED — …` and listed in the report
- Proposes a path under `docs/` and asks "May I write" before writing
**Assertions:**
- [ ] Symbols come from public headers/traits only
- [ ] Citations present; UNVERIFIED used for gaps
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — fix the doc comments
**Input:** "The comments in `engine/memory/include/engine/memory/tlsf.h` are wrong. Fix them while you're there."
**Expected behavior:** Does not edit the header; reports the wrong comments with locations and proposed text to `memory-allocator-specialist`.
**Assertions:**
- [ ] Names `memory-allocator-specialist` exactly
- [ ] No edit under `engine/`

### Case 3: NOT ASSESSED / UNVERIFIED — migration guide from a Proposed ADR
**Fixture:** `docs/architecture/adr-0012-job-api-v2.md` has `Status: Proposed`; no `v2` tag exists.
**Input:** "Write the migration guide for the new job API."
**Expected behavior:** States the ADR is Proposed and there is no tag to diff; either declines or produces a guide clearly labelled DRAFT with the ADR status; does not present the Proposed decision as shipped behaviour; asks which tags to compare.
**Assertions:**
- [ ] ADR status named; guide not presented as final
- [ ] Tags asked for; no invented before/after

### Case 4: Version awareness — doc tool flags
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins compilers and the Rust toolchain but lists no Doxygen version.
**Input:** "Set up Doxygen to fail on undocumented public symbols."
**Expected behavior:** Reads VERSION.md; writes `NOT SOURCEABLE — the installed Doxygen version and its warning options are not covered by docs/engine-reference/custom/`; marks the config unverified; routes the CI wiring to `asset-build-tooling-engineer`.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] `NOT SOURCEABLE` line names the path
- [ ] Names `asset-build-tooling-engineer` for the build/CI side

### Case 5: Redirect — player-facing text
**Input:** "Write the in-game tooltip text for the photo mode and the patch notes."
**Expected behavior:** Redirects tooltip text to `writer` and player patch notes to `community-manager`.
**Assertions:**
- [ ] Names `writer` and `community-manager` exactly
- [ ] Writes neither

### Case 6: Coverage NOT ASSESSED — "is the API documented?"
**Input:** "Is our public API fully documented?" The doc build has not been run.
**Expected behavior:** Coverage is `NOT ASSESSED — doc build not run`; offers to run Doxygen/`cargo doc` with missing-docs warnings and report counts (public symbols, documented, UNVERIFIED, dead references).
**Assertions:**
- [ ] `NOT ASSESSED` with the reason
- [ ] Does not call the API documented

---

## Protocol Compliance

- [ ] Writes only under `docs/`, only after "May I write this to [filepath]?"
- [ ] Never edits code, headers, tests or ADRs
- [ ] Every behavioural claim cited or marked UNVERIFIED
- [ ] `NOT SOURCEABLE` for unpinned tool/library facts; no NDA material from memory
- [ ] Redirects to exact agent names

---

## Coverage Notes
- Editor manual work with `editor-architect` has no dedicated case.
- Superseded-ADR handling is covered only by the agent text.
