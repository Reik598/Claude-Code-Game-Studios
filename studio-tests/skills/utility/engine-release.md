# Skill Test Spec: /engine-release

## Skill Summary

`/engine-release` prepares an engine version for the game teams on a Custom
engine project. It refuses, with an announcement and
`NOT ASSESSED — engine.name is not Custom`, on any other engine. It finds the
previous engine tag (scheme `engine-vX.Y.Z` unless a record names another), the
candidate commit and range, checks the tree is clean, and inventories commits,
Accepted ADRs and the `/api-review` reports covering every public-surface commit.
`chief-engine-architect` decides the semver bump (major for API/ABI or
asset-format breaks, minor for features, patch for fixes only); a differing
version argument is put to the user. It drafts an engine-facing changelog citing
commits and ADRs, has `engine-technical-writer` build the migration guide
between two named tags (no notes, no release), runs
`bash .claude/scripts/test-run.sh custom` and reads its `rule` row (zero tests is
never a pass), collects each game team's confirmation (unconfirmed →
NOT ASSESSED), gets `release-manager`'s sign-off, and prints — never runs — the
tag, release-branch and push commands with the LTS and hotfix policy. Verdict,
first match wins: NOT READY → NOT ASSESSED → READY TO TAG. It asks "May I write"
before the migration guide and the record at
`production/releases/engine/engine-release-[version].md`.

---

## Static Assertions (Structural)

- [ ] Has required frontmatter fields: `name`, `description`, `argument-hint`, `user-invocable`, `allowed-tools`; `model: sonnet`; `disable-model-invocation: true`
- [ ] Has ≥2 phase headings (Phases 0–7), with Phase 2 in `references/inventory.md` and Phase 6 in `references/record.md`
- [ ] Contains verdict keywords: NOT READY, NOT ASSESSED, READY TO TAG — and states NOT ASSESSED ranks below NOT READY and above READY TO TAG
- [ ] Phase 0 refuses on any engine other than `Custom` (or unset) with an announcement, before anything is read or spawned
- [ ] `allowed-tools` has no Edit; its git commands are read-only (`git log`, `git rev-parse`, `git tag --list`, `git branch --list`, `git status`) — no `git tag <name>`, `git branch <name>`, `git push`, `git checkout`, `git cherry-pick`
- [ ] States that tag, branch and push commands are printed for the user and never run, in every `modes.automation`
- [ ] Contains "May I write" naming `docs/engine/migration/` and `production/releases/engine/`
- [ ] Has a next-step handoff (Phase 7: `/api-review`, `/engine-release`)

---

## Director Gate Checks

None. `chief-engine-architect`, `engine-technical-writer` and `release-manager`
are the release's own roles, not director gates; they run at every
`review_mode`, and the run says so once.

---

## Fixture Defaults

Every case's `project.yaml` sets `modes.rigor: minimal` and
`modes.automation: collaborative`, with no `project.local.yaml`, unless its own
Fixture says otherwise. Rules: `studio-tests/CLAUDE.md` §
Fixture defaults. Every case also sets `engine.name: Custom`, C++ with
`commands.build` and `commands.test: ctest --preset debug --output-on-failure`,
and a clean working tree, unless it says otherwise.

---

## Test Cases

### Case 1: Happy Path — minor release, all checks met

**Fixture:**
- Tags `engine-v0.7.0`; 14 engine commits since, 2 touch `engine/renderer/include/`
- `production/qa/api-reviews/api-review-…-bindless.md` covers both commits, verdict APPROVED (additive only)
- ADR-0015 Accepted in range, no API break
- `test-run.sh custom` → `rule custom:ctest-pass`, tests include `tests/integration/game_boot_test.cpp`
- The user names one game team, in-repo `game/`, and confirms its integration build passes on the candidate

**Input:** `/engine-release`

**Expected behavior:**
1. `Release roles run at every review_mode — not director gates.` printed
2. Candidate = `HEAD`, full hash recorded; tree clean
3. CEA returns `minor` with reason and APPROVE; user confirms `0.8.0`
4. Migration guide: `not needed — no breaking or deprecating change`
5. Changelog lines cite commits/ADR-0015; no performance claim without a `/benchmark-report`
6. `release-manager` APPROVE; verdict READY TO TAG
7. Record prints `git tag -a engine-v0.8.0 <hash> …`, `git branch release/engine-0.8 engine-v0.8.0`, `git push <remote> …` — none run
8. Asks "May I write this release record to `production/releases/engine/engine-release-0.8.0.md`?"

**Assertions:**
- [ ] No tag, branch or push command executed
- [ ] Tag planned on the recorded candidate hash
- [ ] Verdict READY TO TAG only with every check met

---

### Case 2: Non-Custom Engine — refuses with announcement

**Fixture:** `engine.name: Unreal`

**Input:** `/engine-release 1.0.0`

**Expected behavior:** prints `/engine-release did not run: it needs engine.name: Custom, and this project's engine is Unreal.` and the two following lines (pointing to `/release-checklist` / `/team-release` and `/setup-engine`); stops with `NOT ASSESSED — engine.name is not Custom`.

**Assertions:**
- [ ] The refusal is announced and names the engine
- [ ] No git command, agent or write

---

### Case 3: Breaking Change With No Migration Guide — NOT READY

**Fixture:**
- An APPROVED `/api-review` covers a `removal` in `engine/jobs/include/…`
- `engine-technical-writer` drafts a guide; the user declines to write it

**Input:** `/engine-release 1.0.0`

**Expected behavior:** CEA returns `major`; Phase 3 shows the guide and asks "May I write the migration guide to `docs/engine/migration/engine-v0.9.0-to-engine-v1.0.0.md`?"; on no → blocker; verdict NOT READY naming the missing guide.

**Assertions:**
- [ ] Verdict NOT READY — no notes, no release
- [ ] Version decided by CEA, confirmed by the user

---

### Case 4: Could Not Assess — zero tests, unreviewed commit, unconfirmed team

**Fixture:**
- `test-run.sh custom` → `rule custom:ctest-zero`
- One public-surface commit has no `/api-review` report
- A second game team "arena" named by the user gives no answer

**Input:** `/engine-release`

**Expected behavior:** integration `NOT ASSESSED — zero tests is never a pass`; `NOT ASSESSED — no /api-review for <hash>`; arena `NOT ASSESSED — no confirmation`; no blocker → verdict NOT ASSESSED naming all three.

**Assertions:**
- [ ] Verdict NOT ASSESSED — never READY TO TAG
- [ ] Each gap named on the verdict line and under `## Not Assessed`
- [ ] Variant: also `rule custom:ctest-failed` → verdict NOT READY, gaps still listed
- [ ] Variant: the test command exits 2 and the helper prints `rule custom:nonzero` → integration FAIL, verdict NOT READY — never NOT ASSESSED

---

### Case 5: Autonomous Mode — still no tag, teams unconfirmed

**Fixture:** `modes.automation: autonomous`; otherwise Case 1

**Input:** `/engine-release 0.8.0`

**Expected behavior:** no questions; every game team `NOT ASSESSED — no confirmation` with the mode named as the reason; commands printed, not run; verdict NOT ASSESSED.

**Assertions:**
- [ ] Autonomous mode does not run `git tag`, `git branch` or `git push`
- [ ] Autonomous mode does not turn missing confirmations into sign-offs

---

### Case 6: Patch on a Release Branch — fix not on main

**Fixture:**
- `release/engine-0.8` with two fixes since `engine-v0.8.0`; one carries `(cherry picked from commit abc123)` and `abc123` is on `main`; the other has no trailer and the user says it is not on `main`

**Input:** `/engine-release 0.8.1 --patch-of release/engine-0.8`

**Expected behavior:** tag planned on the release branch head; first fix met via `git branch --list main --contains abc123`; second → blocker (returns as a regression in the next minor); verdict NOT READY; hotfix policy line in the record.

**Assertions:**
- [ ] No `git cherry-pick` run; the fix is routed to `main` first
- [ ] Variant: `--lts` with no support window in an ADR or from the user → `LTS support window NOT SET`, LTS check NOT ASSESSED

---

### Case 7: Dirty Working Tree

**Fixture:** uncommitted changes under `engine/renderer/src/`; `test-run.sh custom` would pass

**Input:** `/engine-release 0.8.0`

**Expected behavior:** Phase 1 names the uncommitted paths; integration result is `NOT ASSESSED — working tree differs from the candidate`; verdict cannot be READY TO TAG.

**Assertions:**
- [ ] A passing run on a dirty tree is not recorded as PASS for the candidate

---

### Case 8: Crate-only engine — include all engine build inputs

**Fixture:** `engine.name: Custom`; root Cargo workspace members are
`crates/core`, `crates/renderer` and `game`; the module map marks the first two
as engine crates. No `engine/` directory. Since the previous tag, a commit
changes `crates/renderer/src/lib.rs`, another changes the root `Cargo.lock`,
and a third changes `game/`. API review covers the renderer commit.

**Input:** `/engine-release 0.8.0`

**Expected behavior:** Derives engine roots from the module map and workspace;
does not stop for the missing `engine/`. Inventories the renderer and lockfile
commits, retaining the game-only change as context. A local modification to
either crate or a root build input makes integration NOT ASSESSED. With a clean
tree, continues with the candidate-bound consumer-test and sign-off checks;
the presence of crates alone never makes it READY TO TAG.

**Assertions:**
- [ ] Engine crate changes and root build/dependency changes appear in inventory
- [ ] `engine/` is not required when mapped engine crates exist
- [ ] No mutation of git refs or the checkout

---

### Case 9: Passing CTest output without a candidate build

**Fixture:** Clean candidate checkout; `commands.build` unset; CTest finds a
previously built consumer test. Helper reports `build -` (skipped), then
`custom:ctest-pass`. A second run uses Cargo, whose nonzero passing tests compile
the workspace. All other release checks are supplied.

**Input:** `/engine-release 0.8.0`

**Expected behavior:** CTest run is NOT ASSESSED: no affirmative candidate-build
evidence, even though the existing test binary passed. Names the missing build
command and asks for a rebuild and rerun. Cargo's successful test compilation
is affirmative build evidence. Neither changes the candidate cleanliness or
game-consumer coverage requirements.

**Assertions:**
- [ ] The CTest run reads `NOT ASSESSED — no affirmative candidate-build evidence` and names the unset `commands.build`
- [ ] The Cargo run's compiled, nonzero passing tests count as candidate-build evidence
- [ ] Neither run waives the clean-candidate or consumer-test checks

---

### Case 10: Rust consumer tests outside `tests/integration/`

**Fixture:** Root workspace maps engine crates and consumer package `sample-client`
at `game/`. Its integration target is `game/tests/boot.rs`; no root
`tests/integration/` exists. `cargo test --workspace` builds the clean candidate.
The run log identifies the consumer test target with three executed passing tests.

**Input:** `/engine-release 0.8.0`

**Expected behavior:** Resolves the consumer package/targets from manifests,
checks their selection and candidate-bound execution evidence, and accepts the
consumer result without requiring `game` in the command or a C++ directory.
Variant: `--exclude sample-client`, or only engine tests execute, or the consumer
has zero tests → consumer integration NOT ASSESSED despite aggregate passing tests.

**Assertions:**
- [ ] Consumer targets come from the workspace manifests; `game/tests/boot.rs` with three executed passing tests is accepted
- [ ] No root `tests/integration/` directory and no literal `game` in the command is required
- [ ] Each variant reads `NOT ASSESSED — consumer targets not verified (…)` naming the consumer — package `sample-client` or its `boot` target — despite aggregate passing tests

---

### Case 11: `/api-review` coverage is matched by pinned hash

**Fixture:** `production/qa/api-reviews/api-review-2026-11-01-jobs.md` is
APPROVED with `Range: main..feature`, `Base:`/`Head:` full hashes and
`Reviewed commits: A B`. After the review, an unreviewed commit `C` that removes
a public declaration was merged to `main`; a second report has
`Range: M..HEAD` and no `Base:`/`Head:`/`Reviewed commits:` lines.

**Input:** `/engine-release 0.8.0`

**Expected behavior:** `A` and `B` are covered; `C` reads
`NOT ASSESSED — no /api-review for <C>`; the second report covers nothing and
reads `NOT ASSESSED — report range not pinned (<path>)`. No report's `Range:` is
re-run with `git log`.

**Assertions:**
- [ ] A commit counts as covered only when its full hash is on a `Reviewed commits:` line
- [ ] The later unreviewed merge is never covered by the earlier APPROVED report
- [ ] Variant — squash merge: `A` and `B` were squashed into `S` on `main`; `S` is not covered until `/api-review S^..S` reviews it

---

## Protocol Compliance

- [ ] `--patch-of` selects a candidate different from checked-out HEAD: integration stays NOT ASSESSED, no tests are attributed to that candidate and no checkout is performed
- [ ] Root CMake/Cargo files, toolchain presets, lockfiles or project.yaml changed while engine/game/tests are clean: integration stays NOT ASSESSED
- [ ] Code in the candidate implements a Proposed ADR, including an ADR unchanged in the release range: NOT READY, never excluded from the release by its document status

- [ ] Engine check first; refusal announced on non-Custom
- [ ] Every input FOUND or ABSENT; each missing check `NOT ASSESSED — <reason>`
- [ ] Never runs `git tag`, `git branch <name>`, `git push`, `git checkout`, `git merge` or `git cherry-pick`
- [ ] Asks "May I write" before the migration guide and the release record
- [ ] Every changelog line cites a commit or ADR
- [ ] Ends with the Phase 7 next step for the verdict

---

## Coverage Notes

- A version argument that disagrees with CEA's bump is not exercised by its own case.
- First engine release (no previous tag) is not covered.
- Pre-1.0 bump rule taken from an ADR vs asked from the user is not covered.
