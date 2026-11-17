# /engine-release — Phase 6: Release Roles, Branch Plan, Verdict and Record

> Part of `/engine-release`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 6: Release Roles, Branch Plan, Verdict and Record

**In this file:**

- 6a The tag, branch, LTS and hotfix plan — as text
- 6b `release-manager` sign-off
- 6c The verdict, first match wins
- 6d The release record

### 6a. The tag, branch, LTS and hotfix plan — as text

The policy is `release-manager`'s (On a Custom Engine Project): a release
branch per minor; selected releases marked LTS with a stated support window;
engine fixes land on `main` first and are cherry-picked to the release branch.

**Release from `main` (major or minor).** Plan, on the candidate hash from
Phase 1:

```bash
git tag -a engine-vX.Y.0 <candidate-hash> -m "Engine X.Y.0"
git branch release/engine-X.Y engine-vX.Y.0
git push <remote> engine-vX.Y.0 release/engine-X.Y
```

**Patch on a release branch.** The tag goes on the release branch's head
(`engine-vX.Y.Z`); no new branch. Each fix in range must also be on `main`:

- A commit made with `git cherry-pick -x` carries `(cherry picked from commit
  <hash>)`; check that hash is on `main` with
  `git branch --list main --contains <hash>`.
- No such line → ask the user where the fix is on `main`. Unanswered →
  `NOT ASSESSED — <hash> has no recorded counterpart on main`.
- A fix that is only on the release branch → release blocker: it returns as a
  regression in the next minor.

**LTS (`--lts`).** The support window comes from an ADR or the user (Grep
`docs/architecture/` for it, else ask). None → `LTS support window NOT SET`,
and the LTS check is `NOT ASSESSED`; the release itself can be tagged without
the LTS mark only if the user drops `--lts`.

**Hotfix policy, written into the record:** `Engine hotfixes land on main
first and are cherry-picked with -x to release/engine-X.Y; each patch is tagged
engine-vX.Y.Z on the release branch.` (A game hotfix follows `/hotfix`, which
tags the game, not the engine.)

`<remote>` is the remote the project pushes releases to — the record says to
replace it; this skill does not read remotes.

**Print these commands in the record and in the conversation. Never run
them.** The user runs them after READY TO TAG.

### 6b. `release-manager` sign-off

Spawn `release-manager` via Agent with: the version and CEA's result, the
commit, ADR and `/api-review` inventory, the changelog draft, the migration
guide status, the integration result, each game team's answer, and the 6a
plan. Ask it to return APPROVE, CONCERNS or REJECT on the first line and the
reason, or NOT ASSESSED naming a missing input. Nothing returned →
`release-manager: NOT ASSESSED — no sign-off returned`.

### 6c. The verdict

First match wins:

1. **NOT READY** — any release blocker: the integration test FAIL; a game team
   reported a failing build; a public-surface commit whose newest
   `/api-review` is NEEDS REVISION or REJECTED; a required migration guide not
   written; a non-fix change in a patch range; a patch fix only on the release
   branch; candidate implementation governed by an unaccepted ADR;
   `chief-engine-architect` or `release-manager` returned CONCERNS or
   REJECT.
2. **NOT ASSESSED** — no blocker, and any check is `NOT ASSESSED`: a commit
   with no `/api-review`, a game team with no confirmation, an integration
   result other than PASS or FAIL, HEAD differs from candidate, a dirty build
   input, an unresolved ADR dependency, a DRAFT migration guide, an
   unresolved version, a sign-off not returned, `LTS support window NOT SET`
   under `--lts`, a fix with no recorded counterpart on `main`. Name each.
3. **READY TO TAG** — every check met: integration PASS on a clean tree, every
   public-surface commit covered by an APPROVED `/api-review`, the migration
   guide written or not needed, every game team confirmed, the version agreed,
   and both release roles returned APPROVE.

**NOT ASSESSED ranks below NOT READY and above READY TO TAG.** A known blocker
is more actionable than an unknown, and a release whose game teams never
confirmed has not shown it integrates.

**The verdict line names every NOT ASSESSED check:**

> `Verdict: NOT ASSESSED — game team "arena": no confirmation; commit 3f2a… has no /api-review`

### 6d. The release record

```markdown
# Engine Release — [version]
Generated: [date]   Previous: [tag | first engine release]   Candidate: [full hash]   Branch: [main | release/engine-X.Y]

## Verdict
[NOT READY | NOT ASSESSED | READY TO TAG] — [every blocker and every NOT ASSESSED check, with its reason]

## Version
[version] — [major | minor | patch] — chief-engine-architect: [APPROVE / CONCERNS / REJECT / NOT ASSESSED — reason]; reason: [CEA's reason]
[or: Version: NOT ASSESSED — <argument> vs <CEA's>]

## Checks
| Check | Result | Evidence |
|-------|--------|----------|
| API reviews cover every public-surface commit | [met / NOT READY / NOT ASSESSED — reason] | [report paths] |
| Migration guide | [written / not needed / NOT READY — missing / NOT ASSESSED — DRAFT] | [path] |
| Integration test of game/ | [PASS / FAIL / NOT ASSESSED — rule row or missing build evidence] | test-run.sh custom: [rule], [count], build_exit/build_timed_out or Cargo compilation |
| Candidate checkout and build inputs | [matched and clean / NOT ASSESSED — reason] | candidate hash, tested HEAD, git status |
| Governing ADRs Accepted | [met / NOT READY — unaccepted ADR / NOT ASSESSED — dependency unclear] | ADR and implementation paths |
| Game-team sign-off | [all confirmed / NOT READY / NOT ASSESSED — n unconfirmed] | table below |
| Patch fixes on main | [met / NOT READY / NOT ASSESSED / not a patch] | |
| LTS | [not requested / window until <date> / NOT ASSESSED — LTS support window NOT SET] | [ADR or user] |
| release-manager | [APPROVE / CONCERNS / REJECT / NOT ASSESSED — reason] | |

## Public-Surface Commits
| Commit | Files | /api-review | Verdict |
|--------|-------|-------------|---------|

## Game Teams
| Team | Build | Answer |
|------|-------|--------|
| [team] | [build] | [passes / fails / NOT ASSESSED — no confirmation] |

## Changelog
[the 2e draft]

## Tag and Branch Plan — run by the user, not by this skill
[the 6a commands, with <remote> to replace]
Hotfix policy: [the 6a line]

## Not Assessed
- [every check that did not run, its reason, and what would let it run]
```

Show the verdict, the Checks table and every `NOT ASSESSED` line, then ask:
*"May I write this release record to
`production/releases/engine/engine-release-[version].md`?"* Write only after a
yes, creating the folder if it is absent. On no, the record stays in the
conversation and the closing line says it was not written.

Close the run with the verdict line, the record path (or `not written — the user
declined`), and Phase 7's next step, then:
Run status: **COMPLETE** — engine release record produced. That word says the
record was produced; the verdict says whether the release can be tagged. The
other outcomes are the stops in SKILL.md and 2a.

---
