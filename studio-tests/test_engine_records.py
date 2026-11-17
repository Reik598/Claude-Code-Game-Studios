"""Phase 10, records lane: the release notes and the evidence ledger say what
the tree does.

Run: python -m unittest discover -s studio-tests -p test_engine_records.py -v

Fix plan section 12 (Phase 10) and its amendments AM27-AM30. Each test names
the lane item (R<n>, from the Phase 10 lane plan) or the plan decision it
checks. The notes are UPGRADING.md's and CHANGELOG.md's Unreleased sections;
"the other-engines passages" are UPGRADING's "Other engines" row and
CHANGELOG's "Also on every engine" paragraph, where a change that reaches
Godot, Unity, Unreal or Web is disclosed. These check text on disk, not a
Claude session.
"""
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import (  # noqa: E402
    BASE_RELEASE, GATE_CHECK_SKIP_LINE, RELEASE_NOTE_SECTIONS, ROOT, base_release_file, layout_rows, ledger, read)
from test_engine_phase8 import SETTINGS, denied  # noqa: E402
from test_engine_phase8b import (  # noqa: E402
    FIX_PLAN, PHASE_RANGE, PLAN_PHASE_SECTION, PLAN_SECTION, PLAN_SECTION_MENTION, PLAN_STATUS)
from test_engine_phase9 import ADDED_GLOB_EXCEPTIONS, rule_path_items  # noqa: E402

UPGRADING, CHANGELOG = "UPGRADING.md", "CHANGELOG.md"
OTHER_ENGINES_ROW = "| **Other engines** |"
ALSO_ON_EVERY_ENGINE = "Also on every engine"
# R10, AM29(a): the line /security-audit's Executive Summary prints on every
# other engine (security-audit/SKILL.md, Category 7).
SECURITY_AUDIT = ".claude/skills/security-audit/SKILL.md"
CATEGORY_7_SKIP = "Category 7 — skipped"
# R11: a skill that reads artifact-check.sh's ENGINE_SKIPPED rows names their
# count in its own output on every other engine.
ENGINE_SKIPPED = "ENGINE_SKIPPED"
SKILLS_DIR = ".claude/skills"
# R126: the gates whose "Custom engine additions" block prints nothing on
# another engine, and the qualifier the notes put on the skip line.
SILENT_GATES = (".claude/skills/gate-check/references/gate-systems-design.md",
                ".claude/skills/gate-check/references/gate-technical-setup.md")
SILENT_GATE_WORDING = "print nothing for it"
GATE_SKIP_QUALIFIER = "From the Technical Setup → Pre-Production gate on"
# R67: the headline's "unchanged" names its exceptions.
UNCHANGED_HEADLINE = re.compile(r"behaviour and verdicts are unchanged([^.;]*)")
HEADLINE_EXCEPTION = "except"
# R33, R66: a permission rule quoted in a claim.
QUOTED_RULE = re.compile(r"\b(?:Bash|PowerShell)\([^)]*\)")
CLAIMS = "docs/research/aaa-engine-support-2026/claims.jsonl"
# R18: commands the --output deny rules also refuse though they write nothing.
# The notes name each, and each is in fact denied (so the stated residual is
# the real one, not a guess).
OUTPUT_DENY_RESIDUAL = ("git log --output-indicator-new=+ HEAD", "git log -S--output", "git log --grep=--output")
OUTPUT_RESIDUAL_NAMED = ("--output-indicator-*", "-S--output", "--grep=--output")
PERMISSIONS_ROW = "| **Permissions** |"
PERMISSIONS_BULLET = "- **Permissions**"
# R71: the checks the notes say were run.
HOW_CHECKED_ROW = "| **How this was checked** |"
HOW_CHECKED_BULLET = "- **How this was checked**"
CHECK_FILES = re.compile(r"^(?:test_engine\w*|test_custom_ci|check_audio_examples)\.py$")
STUDIO_TESTS = "studio-tests"
# AM28 D2: three skills that run on every engine and are user-invoked only.
D2_SKILLS = ("benchmark-report", "memory-audit", "perf-regression-triage")
USER_INVOKED_ONLY = "disable-model-invocation: true"
# AM28 D4: the module-spec route needs workflow standard or full; at minimal
# /create-epics and /create-stories stop with this pointer.
ENGINE_STORIES_ROW = "| **Engine stories** |"
STORIES_BULLET = "- **Stories for engine work**"
D4_POINTER = "/project-settings modes.workflow=standard"
D4_TIERS = ("standard", "full", "minimal")
# AM28 D6, AM30: the layout's tools/ rows.
TOOLS_ROOT = "tools/"
ENGINE_LAYOUT_ROW = "| **Engine layout** |"
LAYOUT_BULLET = "- **One layout file**"
# The ledger: every claim that names a file names a heading or identifier in it.
MARKDOWN = ".md"
# R67 (second review): a base-release glob that covers a whole folder
# ("assets/shaders/**"); a named glob exception already loaded the rule for
# files in it, so the notes say "outside" those folders.
BASE_FOLDER_GLOB = re.compile(r"^([^*?{}\[\]]+/)\*\*$")
OUTSIDE = "outside"
# R64 (second review): the implementation audit's Phase 10 bullet states
# what the lanes left open. The ids are the rows the Phase 10 lane notes
# (aaa-engine/wf3/*.md, outside the repository) mark partial or blocked;
# R20 and R22-R32 are the guard-lane holes AM27 supersedes.
AUDIT = "docs/research/aaa-engine-support-2026/implementation-audit.md"
PHASE_10_BULLET = "- Phase 10 (section 12)"
PHASE_10_OPEN_ITEMS = ("R32", "R55", "R57", "R65", "R129", "R135")
PLAN_STATUS_ITEM = "R65"
GUARD_HOLES_SUPERSEDED = ("R20", "R22–R32", "AM27")
BLANKET_FIX_CLAIM = re.compile(r"\bfixed them\b")


def unreleased(path):
    """The Unreleased section of a release-notes file."""
    match = RELEASE_NOTE_SECTIONS[path].search(read(path))
    return match[0] if match else ""


def paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def flat(text):
    return " ".join(text.split())


def upgrading_row(start):
    return next((line for line in unreleased(UPGRADING).splitlines() if line.startswith(start)), "")


def changelog_block(start):
    """The CHANGELOG Unreleased paragraph, or list item, that starts with `start`."""
    text = unreleased(CHANGELOG)
    for paragraph in paragraphs(text):
        if paragraph.lstrip().startswith(start):
            return paragraph
        items = re.split(r"\n(?=- )", paragraph)
        for item in items:
            if item.lstrip().startswith(start):
                return item
    return ""


def other_engine_passages():
    return {UPGRADING: upgrading_row(OTHER_ENGINES_ROW), CHANGELOG: changelog_block(ALSO_ON_EVERY_ENGINE)}


def engine_skipped_paragraph(path):
    """The first paragraph of the Unreleased section that names ENGINE_SKIPPED
    (the paragraph test_engine_support.py checks the step ids in)."""
    return next((p for p in paragraphs(unreleased(path)) if ENGINE_SKIPPED in p), "")


def sentences(text):
    return re.split(r"(?<=[.;])\s+(?=[A-Z`/(])", flat(text))


def base_folder_roots(rule):
    """The folders a rule covered whole at BASE_RELEASE, or None without it."""
    base = base_release_file(f".claude/rules/{rule}.md")
    if base is None:
        return None
    return [m[1] for item in rule_path_items(base) if (m := BASE_FOLDER_GLOB.match(item))]


def plan_status_names_last_section_and_phase():
    """R65's check (test_engine_phase8b.py), as a value."""
    text = read(FIX_PLAN).replace("\r", "")
    status = PLAN_STATUS.search(text)
    if status is None:
        return False
    named_sections = {int(a or b) for a, b in PLAN_SECTION_MENTION.findall(status[0])}
    named_phases = {int(n) for n in PHASE_RANGE.findall(status[0])}
    return (max(map(int, PLAN_SECTION.findall(text))) in named_sections
            and max(map(int, PLAN_PHASE_SECTION.findall(text))) in named_phases)


def audit_bullet(start):
    """The implementation audit's list item that starts with `start`."""
    items = re.split(r"\n(?=- )", read(AUDIT).replace("\r", ""))
    return next((flat(item) for item in items if item.startswith(start)), "")


class OtherEngineDisclosures(unittest.TestCase):
    def test_category_7_skip_is_disclosed(self):
        # R10, AM29(a): kept under O2, so disclosed.
        self.assertIn(CATEGORY_7_SKIP, flat(read(SECURITY_AUDIT)), "the skill no longer prints the line")
        for path, passage in other_engine_passages().items():
            with self.subTest(path=path):
                self.assertTrue(passage, "no other-engines passage")
                self.assertIn(CATEGORY_7_SKIP, flat(passage))

    def test_engine_skipped_paragraph_names_every_skill_that_reports_it(self):
        # R11: derived from the skills that read ENGINE_SKIPPED.
        readers = sorted({p.relative_to(ROOT / SKILLS_DIR).parts[0]
                          for p in (ROOT / SKILLS_DIR).rglob("*.md") if ENGINE_SKIPPED in p.read_text(encoding="utf-8")})
        self.assertIn("next-step", readers, "re-check the derivation")
        for path in (UPGRADING, CHANGELOG):
            paragraph = flat(engine_skipped_paragraph(path))
            for skill in readers:
                with self.subTest(path=path, skill=skill):
                    self.assertIn(f"/{skill}", paragraph)

    def test_gate_check_skip_line_names_the_gates_that_print_it(self):
        # R126: two gates print nothing on another engine, so the notes say
        # from which gate on the line appears.
        for gate in SILENT_GATES:
            with self.subTest(gate=gate):
                self.assertIn(SILENT_GATE_WORDING, flat(read(gate)))
        for path in (UPGRADING, CHANGELOG):
            hits = [s for s in sentences(engine_skipped_paragraph(path)) if GATE_CHECK_SKIP_LINE in s]
            with self.subTest(path=path):
                self.assertTrue(hits, "the skip line is not named")
                for sentence in hits:
                    self.assertIn(GATE_SKIP_QUALIFIER, sentence)

    def test_unchanged_headline_names_its_exceptions(self):
        # R67: the notes list changes on other engines, so "unchanged" is
        # qualified where it is said.
        for path in (UPGRADING, CHANGELOG):
            found = UNCHANGED_HEADLINE.findall(flat(unreleased(path)))
            with self.subTest(path=path):
                self.assertTrue(found, "the headline sentence was not found")
                for tail in found:
                    self.assertIn(HEADLINE_EXCEPTION, tail)

    def test_named_glob_exceptions_are_disclosed(self):
        # R67: a glob added to a base rule that is not a Custom root loads on
        # every engine (AM20), so the other-engines passages name it.
        self.assertTrue(ADDED_GLOB_EXCEPTIONS)
        for path, passage in other_engine_passages().items():
            for _rule, glob in ADDED_GLOB_EXCEPTIONS:
                with self.subTest(path=path, glob=glob):
                    self.assertIn(f"`{glob}`", passage)

    def test_glob_exception_notes_name_the_folders_that_already_covered_it(self):
        # R67 (second review): at the base release shader-code.md already
        # loaded for every file under assets/shaders/ and Shaders/, so what
        # the added **/*.slang changes is a Slang file outside those folders.
        for rule, glob in ADDED_GLOB_EXCEPTIONS:
            roots = base_folder_roots(rule)
            if roots is None:
                self.skipTest(f"base release {BASE_RELEASE} is not in this clone (O14)")
            for path, passage in other_engine_passages().items():
                hits = [s for item in re.split(r"\n(?=- )", passage) for s in sentences(item) if f"`{glob}`" in s]
                with self.subTest(path=path, glob=glob):
                    self.assertTrue(hits, "the glob is not named")
                    for sentence in hits:
                        self.assertIn(OUTSIDE, sentence)
                        for root in roots:
                            self.assertIn(f"`{root}`", sentence)

    def test_user_invoked_all_engine_skills_are_disclosed(self):
        # AM28 D2: the three skills run on every engine, user-invoked only.
        for skill in D2_SKILLS:
            with self.subTest(skill=skill, check="frontmatter"):
                self.assertIn(USER_INVOKED_ONLY, read(f"{SKILLS_DIR}/{skill}/SKILL.md"))
        for path, passage in other_engine_passages().items():
            for token in [f"/{s}" for s in D2_SKILLS] + [USER_INVOKED_ONLY.split(":")[0]]:
                with self.subTest(path=path, token=token):
                    self.assertIn(token, passage)


class PermissionNotes(unittest.TestCase):
    def test_claims_quote_only_rules_the_settings_hold(self):
        # R33, R66: a ledger claim that quotes a permission rule quotes one
        # that .claude/settings.json holds.
        permissions = json.loads(read(SETTINGS))["permissions"]
        rules = set(permissions.get("allow", [])) | set(permissions.get("deny", []))
        quoted = [(c["claim_id"], r) for c in ledger("claims") for r in QUOTED_RULE.findall(c["claim"])]
        self.assertTrue(quoted, "no claim quotes a permission rule: re-check this test")
        for claim_id, rule in quoted:
            with self.subTest(claim=claim_id, rule=rule):
                self.assertIn(rule, rules)

    def test_permissions_notes_name_the_deny_residual(self):
        # R18: the --output deny rules also refuse read-only commands whose
        # text contains --output; the notes name the cases, and each is denied.
        deny = json.loads(read(SETTINGS))["permissions"]["deny"]
        for command in OUTPUT_DENY_RESIDUAL:
            with self.subTest(command=command):
                self.assertTrue(denied(command, deny), "the stated residual is not denied: re-check the notes")
        passages = {UPGRADING: upgrading_row(PERMISSIONS_ROW), CHANGELOG: changelog_block(PERMISSIONS_BULLET)}
        for path, passage in passages.items():
            self.assertTrue(passage, f"{path}: no Permissions passage")
            for token in OUTPUT_RESIDUAL_NAMED:
                with self.subTest(path=path, token=token):
                    self.assertIn(token, passage)


class CheckAndLayoutNotes(unittest.TestCase):
    def test_how_this_was_checked_names_every_check_file(self):
        # R71: every structural check file of the change is named.
        files = sorted(p.name for p in (ROOT / STUDIO_TESTS).iterdir() if CHECK_FILES.match(p.name))
        self.assertIn("test_custom_ci.py", files, "re-check the pattern")
        passages = {UPGRADING: upgrading_row(HOW_CHECKED_ROW), CHANGELOG: changelog_block(HOW_CHECKED_BULLET)}
        for path, passage in passages.items():
            self.assertTrue(passage, f"{path}: no 'How this was checked' passage")
            for name in files:
                with self.subTest(path=path, file=name):
                    self.assertIn(f"`{name}`", passage)

    def test_engine_stories_notes_name_the_workflow_tier(self):
        # AM28 D4: the module spec stands in for the GDD at standard or full;
        # minimal stops with a pointer.
        passages = {UPGRADING: upgrading_row(ENGINE_STORIES_ROW), CHANGELOG: changelog_block(STORIES_BULLET)}
        for path, passage in passages.items():
            self.assertTrue(passage, f"{path}: no engine-stories passage")
            for token in (*D4_TIERS, D4_POINTER):
                with self.subTest(path=path, token=token):
                    self.assertIn(token, flat(passage))

    def test_layout_notes_name_every_tools_row(self):
        # AM28 D6, AM30: each tools/ row of the layout, and its owner, is named
        # where the notes describe the layout.
        rows = [(p, row) for row in layout_rows() for p in row["paths"] if p.startswith(TOOLS_ROOT)]
        self.assertGreater(len(rows), 1, "the layout has no tools/ split: re-check this test")
        owners = {re.search(r"`([\w-]+)`", row["Owner agent"])[1] for _p, row in rows}
        passages = {UPGRADING: upgrading_row(ENGINE_LAYOUT_ROW), CHANGELOG: changelog_block(LAYOUT_BULLET)}
        for path, passage in passages.items():
            self.assertTrue(passage, f"{path}: no layout passage")
            for token in sorted({f"`{p}`" for p, _row in rows} | {f"`{o}`" for o in owners}):
                with self.subTest(path=path, token=token):
                    self.assertIn(token, passage)


class StatusRecords(unittest.TestCase):
    def test_audit_phase_10_bullet_names_what_the_lanes_left_open(self):
        # R64 (second review): Acceptance 7, the change's claims about itself
        # are true. The lanes left items partial or blocked, and AM27
        # superseded the guard-lane holes rather than fixing them.
        bullet = audit_bullet(PHASE_10_BULLET)
        self.assertTrue(bullet, "the Phase 10 bullet was not found")
        with self.subTest(check="no blanket claim"):
            self.assertNotRegex(bullet, BLANKET_FIX_CLAIM)
        for item in (*PHASE_10_OPEN_ITEMS, *GUARD_HOLES_SUPERSEDED):
            with self.subTest(item=item):
                self.assertRegex(bullet, rf"(?<![\w–]){re.escape(item)}(?![\w–])")
        if not plan_status_names_last_section_and_phase():
            with self.subTest(item=PLAN_STATUS_ITEM, check="derived"):
                self.assertIn(PLAN_STATUS_ITEM, bullet, "the plan's Status line is still stale")


class LedgerRecords(unittest.TestCase):
    def test_every_claim_names_a_heading_in_its_file(self):
        # LEDGER item: a claim's file exists and its heading is a markdown
        # heading there (or, outside markdown, a name the file contains).
        claims = [c for c in ledger("claims") if "file" in c]
        self.assertTrue(claims)
        for claim in claims:
            with self.subTest(claim=claim["claim_id"]):
                path = ROOT / claim["file"]
                self.assertTrue(path.is_file(), f"{claim['file']} does not exist")
                text = path.read_text(encoding="utf-8")
                if claim["file"].endswith(MARKDOWN):
                    self.assertRegex(text, rf"(?m)^#+ {re.escape(claim['heading'])}[ \t]*$")
                else:
                    self.assertIn(claim["heading"], text)


if __name__ == "__main__":
    unittest.main()
