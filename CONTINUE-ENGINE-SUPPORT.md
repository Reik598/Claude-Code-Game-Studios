# Continue the AAA engine-support work

## Current state — 17 November 2026, Phase 10 (one-pass review of S20)

This section is the only current status. The history below it is superseded
and kept for context only.

- **Nothing is committed.** The change is uncommitted in the worktree on `main`;
  the base release is `abc0de7`. No commit, push, PR, deployment or publication
  is authorised.
- **The plan** is `docs/research/aaa-engine-support-2026/fix-plan.md`
  (revision 4, amendments AM1–AM16 in its section 9, Phase 8 with AM17–AM19 in
  its section 10, Phase 9 with AM20–AM26 in its section 11, Phase 10 with
  AM27–AM31 in its section 12). Phases 1–9 were implemented, in the order 1, 2,
  3, 4, 7, 6, 5, 8, 9. In Phase 10 the seven fix lanes (routing,
  engine-agents-sim-editor, engine-agents-render-platform,
  authoring-and-workflow-skills, new-skills-and-permissions,
  scripts-hooks-permissions, records) have made their changes in the worktree;
  the main session made the plan edits the lanes sent it (AM31) and re-pinned
  the shared-file manifest (AM27), typing a reviewed reason for each of the 43
  new hunks. The Phase 10 critic (AAA-ENGINE-2026-P10) ended at round 2 with
  "Push: clear".
- **Per-phase harsh-critic results.** The reviews of Phases 1–8 ended with
  every finding resolved or recorded in the plan; the main session records each
  of those final results as "Push: clear" (the findings files carry no literal
  "Push:" line). Phase 9's review was held at round 4 with F12 escalated; the
  owner replaced the test F12 was about (AM27), and the P9 critic's round 5
  found F12 resolved by the replacement and ended with "Push: clear". Phase
  10's review ended at round 2 with "Push: clear". The findings files are in the session scratchpad
  (`…/scratchpad/aaa-engine/`), outside the repository, and may not survive a
  cleanup.

| Review (findings file) | Scope | Rounds | Findings | Outcome |
|---|---|---|---|---|
| AAA-ENGINE-2026 | the change as first submitted | 1 | F1–F6, all blocking | input to the fix plan |
| AAA-ENGINE-2026-PLAN | fix plan revisions 1–4 | 3 | F1–F21 | F1–F20 resolved or recorded in the plan; F21 (follow-up: whether the owner's "just keep going until we're done and a 9.5/10" is the changeset approval `CLAUDE.md` asks for) recorded in Phase 0, the owner's call |
| AAA-ENGINE-2026-IMPL | Phases 1–2 | 2 | F1–F6 | F1–F4 resolved; F5, F6 recorded as AM3, AM4 |
| AAA-ENGINE-2026-P3 | Phase 3 (and fix 3.4's Acceptance-8 review) | 3 | F1–F9 | all resolved |
| AAA-ENGINE-2026-P4 | Phase 4 | 2 | F1–F4 | all resolved |
| AAA-ENGINE-2026-P7AB | Phases 7a, 7b (Acceptance-8 review) | 2 | F1–F8 | F1–F6 resolved; F7 fixed in 7c (closed by P7C); F8 phase note corrected |
| AAA-ENGINE-2026-P7C | Phase 7c (Acceptance-8 review) | 2 | F1–F6 | all resolved |
| AAA-ENGINE-2026-P7D | Phase 7d (Acceptance-8 review) | 2 | F1–F4 | all resolved |
| AAA-ENGINE-2026-P6 | Phase 6 | 1 | none | clear |
| AAA-ENGINE-2026-P5 | Phase 5 | 3 | F1–F11 | all resolved |
| AAA-ENGINE-2026-P8 | Phase 8, both lanes (with Acceptance-8 review of 8.8, 8.9) | 3 | F1–F13 | F1–F11 resolved in round 2; F12 (this file) and F13 (the `--output` deny rule, AM19 revised) are follow-ups the main session fixed after round 2, confirmed resolved in round 3 |
| AAA-ENGINE-2026-P9 | Phase 9 (fixes 9.1–9.4 and AM20 to AM26), with the Acceptance-8 review of C124–C133 | 4 | F1–F15 | F1–F8 resolved in round 2; F9–F11 and F13–F15 resolved in round 3; F12 (the diff-based shared-file test) escalated at round 3 and still escalated at round 4. The owner decided on 2026-11-17 to replace that test with an approved-hunk guard (AM27); round 5, at S21, re-ran every F12 mutation against the new guard, found F12 resolved and ended "Push: clear" |
| AAA-ENGINE-2026-P10 | Phase 10 (section 12, AM27–AM31): the S20..S21 delta, the AM27 guard and its re-pin, then the S21..S22 delta | 2 | F1–F2 | F1 (the phase note's hunk counts) and F2 (follow-up: `/create-epics` selected a module's TR entries by `system:`) resolved in round 2; "Push: clear" |

- **Independent scores.** After Phases 1–7, an independent reviewer scored the
  change at snapshot S11 at **8.7 / 10** against the original acceptance
  criteria (deductions D1–D9; the owner's bar is 9.5). Phase 8 (fixes 8.1–8.9)
  addressed D1–D9 and passed its critic (AAA-ENGINE-2026-P8, round 3). A second
  score, at S15, was **9.2 / 10** (deductions N1–N5): Phase 9 (fixes 9.1–9.4)
  addressed N1, N2, N3 and the five O6 items. A third score, at S16, was
  **9.4 / 10** (`score-report-3.md`, P1–P4); Phase 9 also carries those fixes
  (AM22) and the critic findings that followed (AM23 to AM26). N3's first test
  (every glob added to a base-release rule is a Custom root) keeps one named
  exception, `shader-code.md`'s `**/*.slang`, with its reason (fix plan AM20).
  A fourth score, at S23 (after Phase 10 and both critics), was **9.5 / 10**
  (`score-report-4.md`): every earlier deduction fixed or disclosed; left are
  `frame-stats.sh`'s percentile rounding (no test case with a frame count that
  is not a multiple of 100), ledger claims not tied to their sentences by a
  test, and the recorded open points.
- **Phase 10** (fix plan section 12) replaced the per-phase delta reviews with
  one exhaustive pass over the whole change at snapshot S20 (`d98966c7`):
  fifteen finders reported 139 raw findings; triage found 128 real, 8 that
  needed a decision, 1 already recorded and 2 refuted. The eight decisions are
  D1–D8 (AM28; the owner answered D2, D4 and D6). AM27 replaces the diff-based
  shared-file test with the approved-hunk guard
  (`studio-tests/test_engine_shared_guard.py`), AM29 settles the two hunks its
  author marked for confirmation (the `/security-audit` Category 7 skip line is
  kept under O2 and disclosed), and AM30 fixes the `tools/` rows (D6).
- **Checks last observed.** Phase 10's lanes each ran only their own tests and
  the test files that touch their files, while the other lanes were still
  editing (lane notes in the session scratchpad, `aaa-engine/wf3/`). The full
  suite, `python -m unittest discover -s studio-tests -p 'test_*.py'`
  (interpreter
  `C:/Users/AlexanderPino/AppData/Local/Python/pythoncore-3.14-64/python.exe`,
  run with `-B`), passed on the finished Phase 10 tree after the re-pin, with
  none skipped; `python studio-tests/shared_hunks.py check` reports 0 problems.
  This file states no test count: the count is the `Ran` line
  that command prints, and `studio-tests/test_engine_phase8b.py` fails any test
  count written here that differs from the suite.
- **Review is not converged.** The per-phase critics each reviewed their own
  phase's scope; the only reviews of the change as a whole are the independent
  scores and the Phase 10 pass, and the plan's open points below remain
  open.

### Open points (fix plan section 8)

O7 is closed, O9 is closed by fix 8.6 (reviewed in AAA-ENGINE-2026-P8), and
O16 is closed by AM27 (confirmed by the P9 and P10 critics). Every other point
is open:

- **O1** — Custom-only rules still load by path on another engine whose paths
  coincide with Custom roots; only the "ignore this file" guard sentence
  stands between them, and that Claude obeys it is untested. Owner decision.
  The roots now include `tools/ci/`, `tools/build/`, `tools/cook/`,
  `tools/asset-pipeline/`, `tools/validators/` and `tools/reports/`
  (`tools-code.md`, AM28 D6 and AM30); the upgrade notes name each.
- **O2** — A3: the allowlisted output lines on other engines vs announced
  skips. Recommended; owner may overrule. The announced skips on other engines
  are the `artifact-check.sh` rows, the `/gate-check` checklist line, the
  `ENGINE_SKIPPED` line in `/next-step` and `/project-stage-detect`, and
  `/security-audit`'s Category 7 line (AM29(a)); the upgrade notes name each.
- **O3** — a wrapper test runner (`make test`, nextest) keeps generated Custom
  CI red. Follow-up.
- **O4** — no rule for `game/data/` non-JSON files, `.github/workflows/`,
  `docs/engine/`; no `**/*.hlsl` glob. No fix planned.
- **O5** — `/sprint-plan` scene-search gap on Web. No fix planned.
- **O6** — technical accuracy of the agent and rule bodies and skill
  references no review covered. Phase 8 fix 8.8 ran the accuracy read of every
  body no earlier review covered and fixed what it confirmed; the Phase 8
  critic re-checked those fixes against re-fetched sources. The five items that
  read could not confirm were resolved in Phase 9 (fix 9.4): four fixed against
  fetched primary sources and ledgered (C129–C133), the fifth
  (`benchmark-report/references/statistics.md`, the label for two repetitions)
  corrected without a source because it contradicted the file's own threshold.
  The P9 critic re-fetched those sources and matched every quote in its round
  1. Phase 10's accuracy finders found more, which the engine-agent lanes fixed
  and the records lane ledgered (C134–C167). The point stays open: bodies no
  reviewer read line by line remain (score report 2, "Not verified").
- **O8** — the name `engine-api-code.md` is a suggestion. Owner may rename.
- **O9** — closed: `/architecture-review` on Custom registers module-spec
  criteria as `TR-[module]-NNN` (fix 8.6).
- **O10** — virtualized geometry has no agent of its own. Owner may ask for it.
- **O11** — build and CI at scale; Phase 8 fix 8.9 adds the sourced "Build and
  CI at Scale" section to `devops-engineer.md` (reviewed in P8). Build-farm
  infrastructure itself stays project-specific.
- **O12** — that each ledger quote supports its sentence rests on the
  Acceptance-8 reviews, which now include Phase 8's (P8) and Phase 9's (P9);
  the Phase 10 critic re-fetched a sample of the Phase 10 additions (C134–C167:
  19 quotes from 13 sources, all verbatim), not every one.
- **O13** — the narrowed `build-files.md` globs no longer load for
  `tests/**/CMakeLists.txt` and `tools/**/CMakeLists.txt`. Owner may prefer
  the coverage.
- **O14** — base-release comparisons need commit `abc0de7`; where it is
  absent they skip, and a skip is not a pass.
- **O15** — on Custom, `/architecture-review` with module specs and no GDDs
  still reports NOT ASSESSED for the GDD class (AM18). AM28 D5 extends the
  point to `/create-architecture` and `/create-epics`: an engine-first project
  needs a game concept, a systems index and an architecture before its first
  epic. Whether a pure engine project should treat the GDD class as not
  applicable is the owner's call.
- **O16** — recorded in fix plan AM24(e) and section 8: the diff-based "added
  text names Custom" test cannot catch an engine-neutral sentence appended
  inside a Custom paragraph the change added. AM27 closes it once the
  approved-hunk guard lands: any appended sentence fails until it is re-pinned
  with a reviewed reason. Closed by AM27: the P9 critic (round 5) and the
  Phase 10 critic (round 1) confirmed the re-pinned guard on mutations. A
  careless `custom-addition` label at re-pin time can still approve such a
  sentence inside a Custom stretch; the label's predicate limits it and the
  re-pin is a reviewable diff (AM27).
- **O17** — files that are new outside base skill directories (the Custom
  agents and skills) are not covered by the AM27 approved-hunk manifest; the
  catalog tests and the Acceptance 2 checks cover them (AM28).

### Not shown by anything here

No live Claude skill or agent run, no engine build, no hardware or GPU run, no
console SDK. The tests check structure and the generated-CI helper, not
Claude's behaviour; the behavioural specs under `studio-tests/` are
specifications awaiting a live `/skill-test spec` run.

### Resume

1. Read the latest score report (session scratchpad
   `aaa-engine/score-report*.md`), the Phase 10 lane plan and lane notes
   (`aaa-engine/wf2/result.json`, `aaa-engine/wf3/`) and fix-plan sections
   8–12.
2. Score report 4 (S23, 9.5 / 10) names what would raise the score. Any later
   edit to a shared agent or skill file needs `shared_hunks.py propose` and a
   reviewed reason per new hunk (`studio-tests/README.md`).
3. Do not write a test count into this file unless it is the suite's own;
   `studio-tests/test_engine_phase8b.py` fails a count that differs.

Tool notes: `python` on `PATH` can resolve to the unusable Windows Store alias;
use the interpreter path above, and set `PATH` only for a process when a helper
probes for Python. Run it with `-B`: `-I` ignores `PYTHONDONTWRITEBYTECODE`.
Git Bash is `C:/Program Files/Git/bin/bash.exe`. The audio example check needs
`rustc` (last observed 1.93.0).

## History (superseded)

Before the fix plan, an earlier session finished a Copilot changeset (A1, A2,
A3, B, C1) and audited it: a parent integration pass (E01–E08), an independent
read-only critic (C01–C03, closure-checked) and a spec-delta reader (D01–D05,
closure-checked). The Gemini critic the user first asked for was cancelled at
the user's instruction ("stop using gemini, ask a critic"); no Gemini critique
exists. That audit recorded itself as converged over a 63-path snapshot. A
harsh-critic review of the whole change then found six blocking defects
(AAA-ENGINE-2026 F1–F6) and a gap review found more, so the fix plan replaced
that result. The audit record is
`docs/research/aaa-engine-support-2026/implementation-audit.md`; its snapshot,
`review-snapshot.json`, is marked superseded.
