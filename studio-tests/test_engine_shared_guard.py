"""Shared agent and skill files equal the base release plus approved hunks.

Run: python -m unittest discover -s studio-tests -p test_engine_shared_guard.py -v

What the guard proves (fix plan section 11, owner decision on F12). Every file
under .claude/agents/ and .claude/skills/ in the base release is, on disk,
exactly one of: equal to base; base plus the hunks pinned for it in
studio-tests/shared-file-hunks.json; or gone under a reasoned `deleted` entry.
Every file added inside a base skill directory has its whole text pinned. The
covered set is derived from `git ls-tree`, never listed. Default deny: an edit
anywhere in a covered file fails until the manifest is re-pinned and a person
has typed a reason for each new hunk.

What it does not prove: that a pinned hunk is right. That is the review of the
manifest diff, which every change to a shared file now forces.

Three classes here:
- SharedFilesMatchApprovedHunks: the gate, on the real tree.
- GuardControls: the gate watched failing, on a small in-memory tree, one test
  per control (a gate nobody has watched fail is not a gate). They need no
  base commit and no manifest file, so they run in every clone.
- HunkLibrary: the library's pure functions.

To re-pin after a reviewed edit see "Re-pinning" in shared_hunks.py.

Overrides, for running the gate on another checkout (both are named in every
failure and skip message, so an overridden run cannot pass for the real one):
SHARED_GUARD_ROOT (the tree to check), SHARED_GUARD_BASE_REPO (the git
repository that holds the base release) and SHARED_GUARD_MANIFEST.
"""
import copy
import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shared_hunks as sh  # noqa: E402
from test_engine_support import BASE_RELEASE  # noqa: E402

ROOT_OVERRIDE = "SHARED_GUARD_ROOT"
BASE_REPO_OVERRIDE = "SHARED_GUARD_BASE_REPO"
MANIFEST_OVERRIDE = "SHARED_GUARD_MANIFEST"
ROOT = Path(os.environ.get(ROOT_OVERRIDE) or HERE.parent)
BASE_REPO = Path(os.environ.get(BASE_REPO_OVERRIDE) or ROOT)
MANIFEST = Path(os.environ.get(MANIFEST_OVERRIDE) or HERE / sh.MANIFEST_NAME)
WHERE = f"tree {ROOT}, base {sh.BASE_RELEASE} from {BASE_REPO}, manifest {MANIFEST}"

# The in-memory tree of GuardControls. Paths mirror the real layout so the
# derived covered set is exercised; the text is the smallest that holds every
# shape a control needs (frontmatter, a base heading, a list, an untouched
# file, a file the change adds inside a base skill directory).
AGENT = ".claude/agents/lead.md"
SKILL = ".claude/skills/review/SKILL.md"
UNTOUCHED = ".claude/skills/triage/SKILL.md"
ADDED = ".claude/skills/review/references/custom.md"
NEW_SKILL_FILE = ".claude/skills/engine-release/SKILL.md"
AGENT_BASE = ("---\nname: lead\ntools: Read, Grep\n---\n\n# Lead\n\n## Delegation\n\n"
              "Reports to: `director`\n\n- `a` for gameplay\n- `b` for tools\n")
GATE_SENTENCE = "Applies only when `engine.name` is `Custom`."
CUSTOM_SECTION = f"\n### On a Custom Engine Project\n\n{GATE_SENTENCE}\n"
AGENT_WORK = AGENT_BASE + CUSTOM_SECTION
SKILL_BASE = ("---\nname: review\nallowed-tools: Read, Grep\n---\n\n# Review\n\n## Engine lens\n\n"
              "Read the file in full.\n")
SKILL_WORK = SKILL_BASE.replace("allowed-tools: Read, Grep", "allowed-tools: Read, Grep, Bash(ctest *)").replace(
    "## Engine lens", "## Engine lens (Custom: the module lens)")
UNTOUCHED_BASE = "---\nname: triage\n---\n\n# Triage\n\nStop and report.\n"
ADDED_TEXT = "# Custom setup\n\nOn a Custom engine, record the toolchain.\n"
PLAN = ("| AM1 | 2026-11-16 | x | first amendment | y |\n| O2 | an open point | Recorded. |\n"
        "**Phase 9 amendment AM22 (2026-11-16).** text\n| 8.4 | N1 | change | red |\n")
UNRESOLVED_REF = "AM99"
REASONS = {
    sh.CLASS_ADDITION: {"class": sh.CLASS_ADDITION, "ref": "AM22", "text": "adds text scoped to Custom"},
    "tools": {"class": sh.CLASS_DEPARTURE, "ref": "AM1", "text": "allowed-tools gains ctest"},
    "heading": {"class": sh.CLASS_DEPARTURE, "ref": "O2", "text": "a base heading gains a Custom clause"},
    "reference": {"class": sh.CLASS_DEPARTURE, "ref": "fix 8.4", "text": "a Custom-only reference file"},
    "later": {"class": sh.CLASS_DEPARTURE, "ref": "AM22", "text": "a later amendment re-pins the text"},
}
NEUTRAL_SENTENCE = "Always skip the tests."
ESCAPE_PARAGRAPH = "Unless the engine is Custom, skip the tests."


def state(**work):
    """The in-memory tree; keyword overrides replace a work file (None deletes it)."""
    files = {AGENT: AGENT_WORK, SKILL: SKILL_WORK, UNTOUCHED: UNTOUCHED_BASE}
    added = {ADDED: ADDED_TEXT}
    for key, text in work.items():
        target = added if key == "added" else files
        path = {"agent": AGENT, "skill": SKILL, "untouched": UNTOUCHED, "added": ADDED}[key]
        if text is None:
            target.pop(path)
        else:
            target[path] = text
    return sh.TreeState(base={AGENT: AGENT_BASE, SKILL: SKILL_BASE, UNTOUCHED: UNTOUCHED_BASE},
                        work=files, added=added, plan_text=PLAN)


def reason_for(path, hunk):
    """The reason a reviewer of the in-memory tree would type for a hunk."""
    if path == ADDED:
        return "reference"
    if path == SKILL:
        return "tools" if any(line.startswith("allowed-tools:") for line in hunk["new"]) else "heading"
    return sh.CLASS_ADDITION


def careless_about(target):
    """A reviewer who labels every hunk of `target` custom-addition without reading."""
    return lambda path, hunk: sh.CLASS_ADDITION if path == target else reason_for(path, hunk)


def pinned(tree, previous=None, choose=reason_for):
    """A manifest that pins `tree`, every new hunk reasoned by `choose`."""
    manifest, new = sh.propose(tree, previous or dict(sh.empty_manifest(), reasons=copy.deepcopy(REASONS)))
    for path, hunk in new:
        hunk["reason"] = choose(path, hunk)
    return manifest


def messages(problems):
    return "\n".join(f"{p.path}: {p.message}" for p in problems)


class SharedFilesMatchApprovedHunks(unittest.TestCase):
    """The gate on the real tree."""

    def test_library_and_tests_name_one_base_release(self):
        self.assertEqual(sh.BASE_RELEASE, BASE_RELEASE)

    def test_shared_agents_and_skills_equal_base_plus_approved_hunks(self):
        if not sh.base_present(BASE_REPO):
            self.skipTest(f"base release {sh.BASE_RELEASE} is not in this clone ({WHERE})")
        self.assertTrue(MANIFEST.is_file(), f"no approved-hunk manifest: {WHERE}")
        tree = sh.load_state(ROOT, BASE_REPO)
        # Obligation 5: the covered set is derived; an empty one means the
        # derivation broke, not that nothing needs checking.
        for shared_dir in sh.SHARED_DIRS:
            self.assertTrue(any(p.startswith(shared_dir) for p in tree.base),
                            f"no base file under {shared_dir}: the covered set is empty ({WHERE})")
        problems = sh.check(tree, sh.load_manifest(MANIFEST))
        for problem in problems:
            with self.subTest(file=problem.path):
                self.fail(f"{problem.message}\n({WHERE})")


class GuardControls(unittest.TestCase):
    """Each control from the F12 decision, watched failing on the in-memory tree."""

    def assertProblem(self, tree, manifest, path, fragment):
        problems = sh.check(tree, manifest)
        hits = [p for p in problems if p.path == path and fragment in p.message]
        self.assertTrue(hits, f"expected {path}: ...{fragment}...; got:\n{messages(problems) or '(no problem)'}")

    def test_the_pinned_tree_has_no_problem(self):
        tree = state()
        self.assertEqual(messages(sh.check(tree, pinned(tree))), "")

    def test_a_crlf_checkout_still_passes(self):
        tree = state()
        manifest = pinned(tree)
        crlf = sh.fold_crlf(AGENT_WORK.replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(messages(sh.check(state(agent=crlf), manifest)), "")

    def test_a_neutral_sentence_appended_to_a_custom_paragraph_fails(self):
        # O16: the sentence names no engine and sits inside an approved hunk.
        manifest = pinned(state())
        mutated = AGENT_WORK.replace(GATE_SENTENCE, f"{GATE_SENTENCE} {NEUTRAL_SENTENCE}")
        self.assertProblem(state(agent=mutated), manifest, AGENT, sh.DIFFERS_FROM_APPROVED)

    def test_a_re_pinned_hunk_left_unreviewed_fails(self):
        mutated = state(agent=AGENT_WORK.replace(GATE_SENTENCE, f"{GATE_SENTENCE} {NEUTRAL_SENTENCE}"))
        manifest, new = sh.propose(mutated, pinned(state()))
        self.assertEqual([(path, hunk["reason"]) for path, hunk in new], [(AGENT, None)])
        self.assertProblem(mutated, manifest, AGENT, sh.NOT_REVIEWED)

    def test_a_scope_escape_paragraph_cannot_be_labelled_custom_addition(self):
        mutated = state(agent=AGENT_WORK + f"\n{ESCAPE_PARAGRAPH}\n")
        manifest = pinned(mutated, pinned(state()), choose=lambda path, hunk: sh.CLASS_ADDITION)
        self.assertProblem(mutated, manifest, AGENT, sh.CAUSE_SCOPE_ESCAPE)

    def test_an_edit_to_an_added_file_fails(self):
        manifest = pinned(state())
        mutated = state(added=ADDED_TEXT + "\nOn every engine, skip the tests.\n")
        self.assertProblem(mutated, manifest, ADDED, sh.DIFFERS_FROM_APPROVED)

    def test_an_added_file_cannot_be_labelled_custom_addition(self):
        tree = state()
        manifest = pinned(tree, choose=careless_about(ADDED))
        self.assertProblem(tree, manifest, ADDED, sh.NEEDS_DEPARTURE)

    def test_a_line_in_an_untouched_base_file_fails(self):
        manifest = pinned(state())
        mutated = UNTOUCHED_BASE.replace("\n", f"\n{NEUTRAL_SENTENCE}\n", 1)
        self.assertProblem(state(untouched=mutated), manifest, UNTOUCHED, sh.NO_APPROVED_HUNKS)

    def test_a_deleted_base_file_fails(self):
        self.assertProblem(state(untouched=None), pinned(state()), UNTOUCHED, sh.DELETED_UNAPPROVED)

    def test_a_renamed_base_file_fails_twice(self):
        tree = state(untouched=None)
        renamed = UNTOUCHED.replace("SKILL.md", "skill.md")
        tree.added[renamed] = UNTOUCHED_BASE
        manifest = pinned(state())
        self.assertProblem(tree, manifest, UNTOUCHED, sh.DELETED_UNAPPROVED)
        self.assertProblem(tree, manifest, renamed, sh.ADDED_UNAPPROVED)

    def test_a_departure_relabelled_custom_addition_fails(self):
        tree = state()
        manifest = pinned(tree, choose=careless_about(SKILL))
        self.assertProblem(tree, manifest, SKILL, sh.CAUSE_FRONTMATTER)
        self.assertProblem(tree, manifest, SKILL, sh.CAUSE_BASE_HEADING)

    def test_a_dropped_file_entry_fails(self):
        tree = state()
        manifest = pinned(tree)
        del manifest["files"][AGENT]
        self.assertProblem(tree, manifest, AGENT, sh.NO_APPROVED_HUNKS)

    def test_an_entry_for_an_unchanged_file_fails(self):
        tree = state()
        manifest = pinned(tree)
        manifest["files"][UNTOUCHED] = {"hunks": []}
        self.assertProblem(tree, manifest, UNTOUCHED, sh.STALE_ENTRY)

    def test_a_stale_added_entry_fails(self):
        manifest = pinned(state())
        self.assertProblem(state(added=None), manifest, ADDED, sh.STALE_ADDED)

    def test_a_hunk_edited_by_hand_fails(self):
        tree = state()
        manifest = pinned(tree)
        manifest["files"][AGENT]["hunks"][0]["new"].append(NEUTRAL_SENTENCE)
        self.assertProblem(tree, manifest, AGENT, sh.ID_MISMATCH)

    def test_an_unresolved_plan_reference_fails(self):
        tree = state()
        manifest = pinned(tree)
        manifest["reasons"]["tools"]["ref"] = UNRESOLVED_REF
        self.assertProblem(tree, manifest, sh.MANIFEST_SCOPE, UNRESOLVED_REF)

    def test_a_reason_without_text_or_with_an_unknown_class_fails(self):
        tree = state()
        manifest = pinned(tree)
        manifest["reasons"]["tools"]["text"] = " "
        manifest["reasons"]["heading"]["class"] = "approved"
        self.assertProblem(tree, manifest, sh.MANIFEST_SCOPE, "reason tools: empty text")
        self.assertProblem(tree, manifest, sh.MANIFEST_SCOPE, "reason heading: class")

    def test_a_manifest_for_another_base_fails(self):
        tree = state()
        manifest = pinned(tree)
        manifest["base"] = "0000000"
        self.assertProblem(tree, manifest, sh.MANIFEST_SCOPE, "base")

    def test_a_re_pinned_departure_must_cite_a_new_plan_id(self):
        before = pinned(state())
        mutated = state(skill=SKILL_WORK.replace("Bash(ctest *)", "Bash(ctest *), Bash(git push *)"))
        same = pinned(mutated, before)
        self.assertProblem(mutated, same, SKILL, sh.SAME_PLAN_ID)
        other = pinned(mutated, before, choose=lambda path, hunk: "later")
        self.assertEqual(messages(sh.check(mutated, other)), "")

    def test_an_edit_to_an_added_file_re_pins_under_a_new_plan_id(self):
        before = pinned(state())
        mutated = state(added=ADDED_TEXT + "\nOn a Custom engine, also record the linker.\n")
        self.assertProblem(mutated, pinned(mutated, before), ADDED, sh.SAME_PLAN_ID)
        self.assertEqual(messages(sh.check(mutated, pinned(mutated, before, choose=lambda path, hunk: "later"))), "")

    def test_propose_keeps_the_reasons_of_unchanged_hunks(self):
        before = pinned(state())
        mutated = state(untouched=UNTOUCHED_BASE + "\nOn a Custom engine, also triage engine bugs.\n")
        after, new = sh.propose(mutated, before)
        self.assertEqual([path for path, _ in new], [UNTOUCHED])
        self.assertEqual(after["files"][AGENT], before["files"][AGENT])
        self.assertEqual(after["added"], before["added"])

    def test_a_file_outside_base_skill_directories_is_outside_the_guard(self):
        # O17: a new skill's files belong to the catalog and Acceptance-2 tests.
        self.assertFalse(sh.in_base_skill_dir(NEW_SKILL_FILE, state().base))
        self.assertTrue(sh.in_base_skill_dir(ADDED, state().base))


class HunkLibrary(unittest.TestCase):
    """The pure functions the gate is built from."""

    def failures(self, base, work, path=AGENT):
        """Predicate failures of each hunk of base -> work, as one flat list."""
        base_lines, work_lines = sh.split_lines(base), sh.split_lines(work)
        hunks = sh.diff_hunks(path, base_lines, work_lines)
        return [cause for causes in sh.addition_failures(base_lines, hunks) for cause in causes]

    def test_fold_crlf_changes_nothing_else(self):
        self.assertEqual(sh.fold_crlf(b"a\r\nb \n\tc\r\n"), "a\nb \n\tc\n")
        self.assertEqual(sh.fold_crlf(b"\xef\xbb\xbfa\n"), "﻿a\n")

    def test_hunks_rebuild_the_work_file_exactly(self):
        base_lines, work_lines = sh.split_lines(SKILL_BASE), sh.split_lines(SKILL_WORK)
        hunks = sh.diff_hunks(SKILL, base_lines, work_lines)
        self.assertEqual(len(hunks), 2)
        rebuilt, origin = sh.rebuild(base_lines, hunks)
        self.assertEqual(rebuilt, work_lines)
        self.assertEqual(sorted({n for n in origin if n is not None}), [0, 1])

    def test_rebuild_rejects_a_hunk_that_does_not_fit_base(self):
        base_lines = sh.split_lines(SKILL_BASE)
        hunk = sh.diff_hunks(SKILL, base_lines, sh.split_lines(SKILL_WORK))[0]
        with self.assertRaises(ValueError):
            sh.rebuild(base_lines, [dict(hunk, old=["allowed-tools: Read"])])
        with self.assertRaises(ValueError):
            sh.rebuild(base_lines, [dict(hunk, base=[len(base_lines), len(base_lines) + 1])])

    def test_hunk_id_covers_path_range_and_text(self):
        first = sh.hunk_id(AGENT, 3, 3, [], ["x"])
        self.assertEqual(len(first), sh.ID_HEX_DIGITS)
        for other in (sh.hunk_id(SKILL, 3, 3, [], ["x"]), sh.hunk_id(AGENT, 4, 4, [], ["x"]),
                      sh.hunk_id(AGENT, 3, 3, [], ["x "]), sh.hunk_id(AGENT, 3, 4, ["x"], [])):
            self.assertNotEqual(first, other)

    def test_a_custom_section_is_a_custom_addition(self):
        self.assertEqual(self.failures(AGENT_BASE, AGENT_WORK), [])

    def test_a_custom_list_item_is_a_custom_addition(self):
        work = AGENT_BASE + "- `engine-lead` for the engine, on a Custom engine\n"
        self.assertEqual(self.failures(AGENT_BASE, work), [])

    def test_predicate_causes(self):
        cases = {
            sh.CAUSE_FRONTMATTER: AGENT_BASE.replace("tools: Read, Grep", "tools: Read, Grep, Bash  # Custom"),
            sh.CAUSE_BASE_CHANGED: AGENT_BASE.replace("Reports to: `director`", "Reports (Custom) to: `producer`"),
            sh.CAUSE_NO_CUSTOM: AGENT_BASE + f"\n{NEUTRAL_SENTENCE}\n",
            sh.CAUSE_BASE_HEADING: AGENT_BASE.replace("## Delegation", "## Delegation (Custom engine)"),
            sh.CAUSE_HEADING_SCOPES_BASE: AGENT_BASE.replace("## Delegation\n", "## Delegation\n\n### Custom engine\n"),
            sh.CAUSE_ENGINE_WORD: AGENT_BASE + "\nOn Unity-based projects, as on Custom, skip the lead.\n",
            sh.CAUSE_SCOPE_ESCAPE: AGENT_BASE + f"\n{ESCAPE_PARAGRAPH}\n",
            sh.CAUSE_BLOCK_NOT_CUSTOM: AGENT_BASE + f"\n{NEUTRAL_SENTENCE}\n" + CUSTOM_SECTION,
            sh.CAUSE_GLUED: AGENT_BASE.replace("Reports to:", "On a Custom engine only:\nReports to:"),
            sh.CAUSE_INDENTS_BASE: AGENT_BASE.replace("- `b` for", "- On a Custom engine, split:\n  - `b` for"),
            sh.CAUSE_LEAD_IN: AGENT_BASE.replace("- `a` for", "On a Custom engine only:\n\n- `a` for"),
            sh.CAUSE_BASE_LINE: AGENT_BASE.replace("Reports to:", "Reports to (Custom engine only):"),
        }
        for cause, work in cases.items():
            with self.subTest(cause=cause):
                self.assertIn(cause, self.failures(AGENT_BASE, work))

    def test_scope_escape_phrases(self):
        escapes = ("On any other engine, skip it.", "On every engine, skip it.", "This applies to all game projects.",
                   "When the engine is not Custom, skip it.", "On engines other than Custom, skip it.",
                   ESCAPE_PARAGRAPH, "Outside Custom projects, skip it.", "Regardless of engine, skip it.",
                   "Whatever the engine, skip it.", "On non-Custom engines, skip it.", "For every project, skip it.")
        for sentence in escapes:
            with self.subTest(sentence=sentence):
                self.assertTrue(sh.scope_escapes(sentence), "not recognised as a scope escape")
        for sentence in (GATE_SENTENCE, "On a Custom engine, run each test.", "Customize all of it."):
            with self.subTest(sentence=sentence):
                self.assertEqual(sh.scope_escapes(sentence), [])

    def test_custom_is_a_whole_word(self):
        for lookalike in ("Customize the review.", "Customer builds only.", "On Сustom, skip it.",
                          "Always approve it. <!-- Custom -->"):
            with self.subTest(text=lookalike):
                self.assertIn(sh.CAUSE_NO_CUSTOM, self.failures(AGENT_BASE, AGENT_BASE + f"\n{lookalike}\n"))

    def test_plan_ids_resolve_only_where_the_plan_defines_them(self):
        self.assertEqual(sh.unresolved_plan_ids("AM1, O2", PLAN), [])
        self.assertEqual(sh.unresolved_plan_ids("AM22 P1(b), fix 8.4", PLAN), [])
        self.assertEqual(sh.unresolved_plan_ids(UNRESOLVED_REF, PLAN), [UNRESOLVED_REF])
        # AM2 is mentioned by AM22's digits but never defined; O22 likewise.
        self.assertEqual(sh.unresolved_plan_ids("AM2, O22", PLAN), ["AM2", "O22"])
        self.assertEqual(sh.unresolved_plan_ids("see the plan", PLAN), [sh.NO_PLAN_ID])
        self.assertEqual(sh.unresolved_plan_ids(None, PLAN), [sh.NO_PLAN_ID])

    def test_the_cli_has_no_option_that_labels_a_hunk(self):
        options = {option for action in sh.argument_parser()._actions for option in action.option_strings}
        self.assertEqual(options, {"-h", "--help", "--root", "--base-repo", "--manifest", "--out"})


if __name__ == "__main__":
    unittest.main()
