# Skill Test Spec: /api-review

## Skill Summary

`/api-review` reviews a change to a Custom engine's public surface before
merge: C++ headers under any module's `include/` (`engine/**/include/`) and module interface units, Rust
items reachable from each engine crate's root, and the C ABI. It refuses, with a
three-line announcement and `NOT ASSESSED — engine.name is not Custom`, on any
other engine. It derives the surface from the repository (never a list),
classifies every changed public item (`breaking-abi`, `breaking-source`,
`removal`, `deprecation`, `additive`, `compatible`), and checks the deprecation
window from `.claude/rules/engine-api-code.md` (removal only after the number of
engine releases an ADR sets; no window recorded → `NOT ASSESSED`), the
deprecation message (replacement and removal release), an Accepted ADR for each
break, and the boundary rules (no OS/SDK type in a public header outside
`engine/platform/`, no `game/` dependency). `engine-technical-writer` drafts or
reviews the migration note; `chief-engine-architect` and the lead of each
affected module sign off — at every `review_mode` when anything breaks or
deprecates, only at `full` for additive-only changes (skip announced). Verdict,
first match wins: REJECTED → NEEDS REVISION → NOT ASSESSED → APPROVED. It asks
"May I write" before the migration note and before
`production/qa/api-reviews/api-review-[date]-[short-name].md`, and runs only
read-only `git` commands.

---

## Static Assertions (Structural)

- [ ] Has required frontmatter fields: `name`, `description`, `argument-hint`, `user-invocable`, `allowed-tools`; `model: sonnet`
- [ ] Has ≥2 phase headings (Phases 0–6), with Phase 2 in `references/surface.md` and the verdict and template in `references/report.md`
- [ ] Contains verdict keywords: REJECTED, NEEDS REVISION, NOT ASSESSED, APPROVED — and states NOT ASSESSED ranks below REJECTED and NEEDS REVISION and above APPROVED
- [ ] Phase 0 refuses on any engine other than `Custom` (or unset) with an announcement naming the engine, and stops before reading or spawning
- [ ] `allowed-tools` has no Edit and no general Bash: only `git diff`, `git log`, `git show`, `git merge-base`, `git rev-parse`, `git tag --list`, `git status` and the config helper
- [ ] Contains "May I write" naming `docs/engine/migration/` and `production/qa/api-reviews/`
- [ ] The public surface is derived (Glob `engine/**/include/**`, nested modules included; the workspace `Cargo.toml`), not enumerated
- [ ] Phase 1 pins the range: `Base:` and `Head:` full hashes (`git rev-parse`) and a `Reviewed commits:` list (`git log --format=%H`) in the report header
- [ ] Has a next-step handoff (Phase 6: `/engine-release`, `/architecture-decision`, `/api-review`)

---

## Director Gate Checks

None. The sign-offs are the skill's own review roles required by
`.claude/rules/engine-api-code.md`, not entries in `.claude/docs/director-gates.md`.
They run at every `review_mode` for breaking, deprecating or removal changes; for
additive-only changes they run at `full` and are skipped at `lean`/`solo` with
`Sign-off skipped — additive-only change, review_mode: <value>`.

---

## Fixture Defaults

Every case's `project.yaml` sets `modes.rigor: minimal` and
`modes.automation: collaborative`, with no `project.local.yaml`, unless its own
Fixture says otherwise. Rules: `studio-tests/CLAUDE.md` §
Fixture defaults. Every case also sets `engine.name: Custom` unless it says
otherwise.

---

## Test Cases

### Case 1: Happy Path — deprecation with replacement, signed off

**Fixture:**
- C++ engine; `engine/jobs/include/engine/jobs/scheduler.h` in range `main..HEAD` adds `submit_v2(...)` and marks `submit(...)` `[[deprecated("use submit_v2; removed in 0.9")]]`
- `docs/architecture/adr-0012-job-submit.md` is Accepted; its `## ABI / API Stability` records the deprecation and removal in 0.9
- Engine release tags `engine-v0.6.0`, `engine-v0.7.0`; no migration note yet
- `modes.review_mode` unset (resolves to solo under `rigor: minimal`)

**Input:** `/api-review main..HEAD --next 0.8.0`

**Expected behavior:**
1. Engine check passes; inputs listed FOUND/ABSENT
2. Rows: `submit_v2` `additive`; `submit` `deprecation` — message names replacement and removal release → no finding
3. `engine-technical-writer` returns a note citing ADR-0012; asks "May I write this migration note to `docs/engine/migration/engine-v0.7.0-to-0.8.0.md`?"
4. Sign-off runs although `review_mode` is solo (a deprecation is present): `chief-engine-architect` and `core-systems-lead` spawned in one message; both APPROVE
5. Verdict APPROVED; asks "May I write this API review to `production/qa/api-reviews/api-review-[date]-[short-name].md`?"

**Assertions:**
- [ ] Each row cites file:line from the diff
- [ ] Sign-off is not skipped at solo for a deprecating change
- [ ] Reviewers spawned in parallel; `core-systems-lead` chosen from the `jobs` module
- [ ] Verdict APPROVED only after both APPROVE and the note is written

---

### Case 2: Non-Custom Engine — refuses with announcement

**Fixture:**
- `engine.name: Godot`; a GDExtension under `src/native/` with changed headers

**Input:** `/api-review main..HEAD`

**Expected behavior:**
1. Phase 0 prints `/api-review did not run: it needs engine.name: Custom, and this project's engine is Godot.` plus the two following lines
2. Points to `/code-review` for the native plugin and `/setup-engine` to change engine
3. Stops: `NOT ASSESSED — engine.name is not Custom`; no git command, no agent, no write

**Assertions:**
- [ ] The refusal is announced, never silent, and names the engine
- [ ] No reduced review runs
- [ ] Same result when `engine.name` is unset (`unset` named)

---

### Case 3: Removal Before the Window — NEEDS REVISION

**Fixture:**
- `engine/core/include/engine/core/log.h` removes `log_legacy()`, deprecated in a commit contained only in tag `engine-v0.7.0`
- An Accepted ADR sets a deprecation window of 2 engine releases

**Input:** `/api-review main..HEAD`

**Expected behavior:**
1. Row `removal`; `git log -S` finds the deprecation commit; `git tag --list --contains` → 1 engine release shipped it deprecated
2. 1 < 2 → finding naming both numbers
3. Verdict NEEDS REVISION, even if a sign-off is APPROVE

**Assertions:**
- [ ] Release count and window both shown in the Deprecation and Removal table
- [ ] Verdict NEEDS REVISION, not APPROVED
- [ ] Next step: keep the deprecated API until the window ends, re-run `/api-review`

---

### Case 4: Could Not Assess — no window recorded, Rust reachability unknown

**Fixture:**
- Rust engine; `engine/ecs/src/query.rs` changes a `pub fn` signature; `lib.rs` has `pub use query::*`
- A deprecated item removed in `engine/math/src/vec.rs`; no ADR records a deprecation window
- No public-API listing supplied

**Input:** `/api-review main..HEAD`

**Expected behavior:**
1. `query.rs`: `NOT ASSESSED — reachability of engine/ecs/src/query.rs not decidable from source` (glob re-export); asks for a rustdoc-JSON or `cargo-public-api` listing, with its flags `NOT SOURCEABLE — … not covered by docs/engine-reference/custom/` when VERSION.md does not document them
2. Removal: `NOT ASSESSED — no deprecation window recorded`
3. No other finding → verdict NOT ASSESSED naming both reasons

**Assertions:**
- [ ] Verdict NOT ASSESSED — never APPROVED
- [ ] No cargo command written from memory
- [ ] Both gaps on the verdict line and under `## Not Assessed`
- [ ] Variant: the same fixture plus an `HWND` added to `engine/rhi/include/…` → verdict NEEDS REVISION (a known finding outranks the gaps), with the gaps still named

---

### Case 5: C ABI Struct Edited in Place — REJECTED

**Fixture:**
- `engine/core/include/engine/plugin_abi.h` adds a field in the middle of `EnginePluginApiV1` without a `V2`

**Input:** `/api-review main..HEAD`

**Expected behavior:**
1. Row `breaking-abi`; finding: versioned interfaces are added beside the old one, never edited in place
2. Reviewers told to treat it as REJECT
3. Verdict REJECTED; next step: add `EnginePluginApiV2` beside V1, or `/architecture-decision`

**Assertions:**
- [ ] Classified `breaking-abi`, not `additive`
- [ ] Verdict REJECTED regardless of other rows

---

### Case 6: Additive Only in Solo — skip announced

**Fixture:**
- Only new declarations in `engine/renderer/include/…`; `modes.review_mode: solo`

**Input:** `/api-review --working-tree`

**Expected behavior:**
1. `git diff HEAD` plus `git status --short` read; rows all `additive`
2. `Migration note: not needed — additive or compatible changes only`
3. `Sign-off skipped — additive-only change, review_mode: solo` printed and on the verdict line
4. Verdict `APPROVED — additive only; sign-off skipped (…)`

**Assertions:**
- [ ] The skip is in the output, not only implied
- [ ] Untracked public headers are included via `git status`
- [ ] Variant at `review_mode: full`: CEA and `rendering-lead` spawned

---

### Case 7: No Argument — range is asked, never assumed

**Fixture:** a feature branch with commits ahead of `main`

**Input:** `/api-review`

**Expected behavior:** proposes `$(git merge-base main HEAD)..HEAD`, offers `--working-tree`, and waits for the answer before reading any diff.

**Assertions:**
- [ ] No diff read before the user picks
- [ ] Not a git repository → `NOT ASSESSED — no change to review`

---

### Case 8: Registered module leads and crate aliases

**Fixture:** Breaking public APIs in `crates/camera/`, `engine/cinematics/`,
`engine/sequencer/`, and `engine/sim/`. The module map assigns camera/cinematics
to cinematics-sequencer-engineer, whose lead is editor-architect, and sim to
simulation-systems-lead. `modes.review_mode: solo`.

**Input:** `/api-review --working-tree`

**Expected behavior:** Resolves owners and leads from the module map and current
coordination records. Requests CEA, editor-architect and simulation-systems-lead
sign-off, deduplicated; coordinates any additional runtime handoff review through
the affected lead. Solo does not waive breaking-change sign-off. The same owner
rules apply to crate aliases. Unknown ownership is NOT ASSESSED until resolved,
rather than silently assigned CEA-only with a false claim that no lead exists.

**Assertions:**
- [ ] Records the path → owner → lead mapping, crate alias included, before spawning reviewers
- [ ] Requests chief-engine-architect, editor-architect and simulation-systems-lead once each
- [ ] Breaking-change sign-off runs at `review_mode: solo`; no `Sign-off skipped` line
- [ ] Variant — an unmapped path reads `NOT ASSESSED — reviewer ownership unresolved (<paths>)`, never CEA-only coverage

---

### Case 9: Nested module headers are public

**Fixture:** the change adds `engine/renderer/features/include/renderer/features/sky.h`
and removes a declaration from it; the layout maps `engine/renderer/features/`
to `graphics-features-engineer` (Lead `rendering-lead`).

**Input:** `/api-review --working-tree`

**Expected behavior:** the header is in the public surface (`engine/**/include/**`
reaches a nested module), the removal is classed, rendering-lead is asked to sign
off. A header under `engine/renderer/features/src/include/` is not public.

**Assertions:**
- [ ] The nested header is classed, never counted under `Changed files not public`
- [ ] Never `APPROVED — no public surface change` for this change

---

### Case 10: Range whose head is not the checkout — read at `<head>`, range pinned

**Fixture:** the checkout is on `main` at `M`; the user reviews `v0.7.0..feature`,
where `feature` adds `extern "C"` to a header that `main` does not have.

**Input:** `/api-review v0.7.0..feature`

**Expected behavior:** Phase 1 records `Base:` and `Head:` as full hashes and the
`Reviewed commits:` list. Phase 2 reads each file with `git show <head>:<path>`
and lists folders with `git show <head>:<dir>/`, so the `extern "C"` block is seen
and classed as ABI surface; the working tree is never read for this range.

**Assertions:**
- [ ] The report header has `Base:`, `Head:` (full hashes) and `Reviewed commits:`
- [ ] Every row comes from the `<head>` contents, not the `main` checkout
- [ ] Variant — `Range M..HEAD` on `main`: the hashes are pinned at review time, so a later `/engine-release` never re-resolves the range

---

### Case 11: Rust trait made not dyn-compatible, type parameter added

**Fixture:** in `crates/jobs/src/lib.rs`, the public trait `Job` gains a
defaulted generic method `fn map<T>(&self, t: T) {}`; the public trait `Sink`
gains a type parameter with no default (`Sink<T>`); a free fn's bound is loosened
from `T: Copy` to `T: Clone`.

**Input:** `/api-review --working-tree`

**Expected behavior:** `Job` → `breaking-source` (the generic method makes the
trait not dyn-compatible, so every `dyn Job` user breaks), never `additive`;
`Sink<T>` → `breaking-source`; the loosened bound → `compatible`. Breaking rows
take the sign-off at every `review_mode`.

**Assertions:**
- [ ] The defaulted generic method is `breaking-source`, not `additive — name-conflict risk`
- [ ] The type parameter without a default is `breaking-source`
- [ ] The loosened bound on a free fn is `compatible`

---

### Case 12: Deprecation window counts minor releases, not patch tags

**Fixture:** `engine::jobs::submit_legacy` carried `[[deprecated]]` from a commit
contained in `engine-v0.7.0`, `engine-v0.7.1` and `engine-v0.7.2`; the change
removes it; ADR-0012's window is "two minor releases".

**Input:** `/api-review --working-tree --next 0.8.0`

**Expected behavior:** releases shipped deprecated = 1 distinct minor version
(0.7), fewer than 2 → finding naming both numbers and the unit; verdict NEEDS
REVISION. An ADR reading "two versions" → `NOT ASSESSED — window unit not stated`.

**Assertions:**
- [ ] Patch tags add nothing beyond their minor version
- [ ] Variant — a unit the ADR does not state is NOT ASSESSED, never met

---

### Case 13: A reviewer returns NOT ASSESSED

**Fixture:** a deprecation with replacement and a written migration note; every
row OK; `chief-engine-architect` returns `NOT ASSESSED — ADR-0012 not provided`.

**Input:** `/api-review --working-tree`

**Expected behavior:** verdict rule 3 matches: `NOT ASSESSED`, naming the
reviewer and its reason; never APPROVED, never an undefined verdict.

**Assertions:**
- [ ] Verdict NOT ASSESSED with the reviewer's reason on the verdict line

---

## Protocol Compliance

- [ ] Engine check runs first and refuses with an announcement on non-Custom
- [ ] Records every input FOUND or ABSENT
- [ ] Classes come from the diff, never commit messages
- [ ] Every verdict line names each NOT ASSESSED item and each skip
- [ ] Asks "May I write" before the migration note and before the review report
- [ ] Never edits engine code, headers, ADRs or tests; never runs a mutating `git` command
- [ ] Ends with the Phase 6 next step for the verdict

---

## Coverage Notes

- A reviewer that returns nothing (`NOT ASSESSED — no sign-off returned`) has no dedicated case; one that returns NOT ASSESSED is Case 13.
- A migration note drafted from a Proposed ADR (DRAFT → NOT ASSESSED) is not exercised.
- C++ module interface units (`*.cppm`, `*.ixx`) are not covered by a case.
