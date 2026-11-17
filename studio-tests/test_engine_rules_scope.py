"""Structural contracts for the base release's path-scoped rules (fix plan
section 12, Phase 10, items T1-T3 of the tests-other review).

Run: python -m unittest discover -s studio-tests -p test_engine_rules_scope.py -v
A rule that existed at the base release loads on Godot, Unity, Unreal and Web
projects too, so the change may only add to it: Custom-labelled sections and
units in its body, Custom-root globs in its `paths`. These tests derive the
covered rules from the base commit instead of listing them, and skip (saying
why) when the base commit is not in the clone. They check files on disk, not
Claude's behaviour in a session.
"""
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import (  # noqa: E402
    BASE_RELEASE, ROOT, added_unit_violations, base_release_file)

RULES_DIR = ".claude/rules"
CUSTOM_TOKEN = "Custom"
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---[ \t]*\n", re.S)
HEADING = re.compile(r"^(#{1,6}) (.*)$", re.M)
# A section is Custom when its heading names Custom, or carries the rules'
# own title for their Custom part, "A project's own engine"
# (test_engine_phase8.SHADER_CUSTOM_SECTION; shader-code.md's heading names
# no engine).
CUSTOM_HEADING = re.compile(r"\bCustom\b|^A project's own engine\b")
FENCE_JOIN = " ⏎ "
PATHS_KEY = re.compile(r"^paths:[ \t]*(.*)$", re.M)
LIST_ITEM = re.compile(r"^[ \t]+-[ \t]+(.*?)[ \t]*$")
DOUBLE_QUOTED = re.compile(r'^"((?:[^"\\]|\\.)*)"$')
SINGLE_QUOTED = re.compile(r"^'((?:[^']|'')*)'$")
# Reviewed in-place edits of a base rule line, as (base line, current line):
# each one names Custom and is decided in the fix plan. Anything else that
# changes or removes a base line fails.
BASE_LINE_EDITS = {
    ".claude/rules/data-files.md": {
        # Fix plan fix 4.1 (B2): Custom's game/data/ JSON takes the Godot and
        # Web naming convention, stated on the line that gives it.
        ("- File naming (Godot and Web data): lowercase with underscores only, "
         "following `[system]_[name].json` pattern.",
         "- File naming (Godot, Web and Custom `game/data/`): lowercase with underscores only, "
         "following `[system]_[name].json` pattern."),
    },
}
# A base glob the change removed, with the plan decision that removed it.
# Empty: no base glob has been removed.
REMOVED_BASE_GLOBS = {}


def base_rule_paths():
    """Rule files present at BASE_RELEASE, or None when the commit is absent."""
    result = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "--name-only", f"{BASE_RELEASE}:{RULES_DIR}"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return [f"{RULES_DIR}/{name}" for name in result.stdout.split() if name.endswith(".md")]


def normalise(text):
    return text.replace("\r", "")


def split_rule(text):
    """(frontmatter, body) of a rule; frontmatter is '' when it has none."""
    match = FRONTMATTER.match(normalise(text))
    return (match[1], normalise(text)[match.end():]) if match else ("", normalise(text))


def joins_label(line):
    """A label line, or a folded block: a block after it (blank lines between)
    belongs to the same unit."""
    return line.rstrip().endswith(":") or line.startswith("```")


def fold_fences(body):
    """body with each fenced code block folded onto one line, so a `#` inside
    code is not a heading. A block whose label paragraph (the text just above
    it, or a block that joined it) ends with ':' joins that paragraph's unit:
    an example is judged by its label ("Custom engine, Rust (...):")."""
    out, fence, label_gap = [], None, []
    for line in body.splitlines():
        if fence is not None:
            fence.append(line)
            if line.startswith("```"):
                folded = FENCE_JOIN.join(fence)
                if label_gap and out and joins_label(out[-1]):
                    out.append(folded)          # drop the blank lines: same unit as the label
                else:
                    out.extend(label_gap + [folded])
                fence, label_gap = None, []
            continue
        if line.startswith("```"):
            fence = [line]
            continue
        if not line.strip() and out and joins_label(out[-1]):
            label_gap.append(line)
            continue
        out.extend(label_gap + [line])
        label_gap = []
    out.extend(label_gap + (fence or []))
    return "\n".join(out) + ("\n" if body.endswith("\n") else "")


def without_custom_sections(body):
    """body with every Custom section (CUSTOM_HEADING) removed, from the
    heading to the next heading of the same or a higher level; text after
    that heading stays and is compared."""
    while True:
        heading = next((h for h in HEADING.finditer(body) if CUSTOM_HEADING.search(h[2])), None)
        if heading is None:
            return body
        level = len(heading[1])
        end = re.compile(rf"^#{{1,{level}}} ", re.M).search(body, heading.end())
        body = body[:heading.start()] + (body[end.start():] if end else "")


def path_items(frontmatter):
    """[(raw item, value or None)] of the `paths:` block list; value is None
    for a form this parser does not read."""
    match = PATHS_KEY.search(frontmatter)
    if not match:
        return []
    if match[1].strip():
        return [(match[1].strip(), None)]   # flow style or a scalar: not a block list
    items = []
    for line in frontmatter[match.end():].lstrip("\n").splitlines():
        item = LIST_ITEM.match(line)
        if not item:
            break
        raw = item[1]
        double, single = DOUBLE_QUOTED.match(raw), SINGLE_QUOTED.match(raw)
        if double:
            items.append((raw, double[1].encode().decode("unicode_escape")))
        elif single:
            items.append((raw, single[1].replace("''", "'")))
        else:
            items.append((raw, raw.split(" #")[0].strip()))
    return items


def reviewed_edit_lines(rel):
    edits = BASE_LINE_EDITS.get(rel, set())
    return {old for old, _ in edits}, {new for _, new in edits}


class BaseRuleScope(unittest.TestCase):

    def setUp(self):
        self.base_rules = base_rule_paths()
        if self.base_rules is None:
            self.skipTest(f"{BASE_RELEASE} is not in this clone: the base rules cannot be derived")

    def test_base_rule_bodies_change_only_by_custom_additions(self):
        # T1, T2: the body below the frontmatter, outside sections whose
        # heading names Custom, equals base except for added units that each
        # name Custom; text after a Custom section is compared too.
        checked = 0
        for rel in self.base_rules:
            current_path = ROOT / rel
            with self.subTest(rule=rel):
                self.assertTrue(current_path.exists(), "a base rule was deleted")
                base_text = base_release_file(rel)
                text = current_path.read_text(encoding="utf-8")
                if normalise(base_text) == normalise(text):
                    continue
                checked += 1
                base_old, current_new = reviewed_edit_lines(rel)
                base_body = "\n".join(line for line in fold_fences(split_rule(base_text)[1]).splitlines()
                                      if line not in base_old)
                body = without_custom_sections(fold_fences(split_rule(text)[1]))
                body = "\n".join(line for line in body.splitlines() if line not in current_new)
                self.assertEqual(added_unit_violations(base_body, body, CUSTOM_TOKEN), [])
        self.assertTrue(checked, "no base rule differs from base: this test checked nothing")

    def test_reviewed_line_edits_still_apply(self):
        # A reviewed in-place edit that no longer matches the tree is stale.
        for rel, edits in BASE_LINE_EDITS.items():
            base_lines = split_rule(base_release_file(rel) or "")[1].splitlines()
            lines = split_rule((ROOT / rel).read_text(encoding="utf-8"))[1].splitlines()
            for old, new in edits:
                with self.subTest(rule=rel, line=new[:60]):
                    self.assertIn(old, base_lines)
                    self.assertIn(new, lines)
                    self.assertIn(CUSTOM_TOKEN, new)

    def test_base_rule_globs_are_kept(self):
        # T3: every glob a base rule had is still in its `paths`, unless a
        # plan decision removed it (REMOVED_BASE_GLOBS).
        for rel in self.base_rules:
            with self.subTest(rule=rel):
                base = {value for _, value in path_items(split_rule(base_release_file(rel))[0])}
                current = {value for _, value in path_items(split_rule((ROOT / rel).read_text(encoding="utf-8"))[0])}
                removed = base - current - set(REMOVED_BASE_GLOBS.get(rel, ()))
                self.assertEqual(sorted(removed), [])


class RulePathItems(unittest.TestCase):
    """Current rules only: runs in every clone, with or without BASE_RELEASE."""

    def test_rule_path_items_are_double_quoted(self):
        # T3: the framework's own readers (test_engine_support.matches and
        # rule_globs) see only `  - "glob"`; any other form would load in
        # Claude Code but escape every scope check, so it fails here.
        rules = sorted((ROOT / RULES_DIR).glob("*.md"))
        self.assertTrue(rules)
        for path in rules:
            frontmatter = split_rule(path.read_text(encoding="utf-8"))[0]
            for raw, _ in path_items(frontmatter):
                with self.subTest(rule=path.name, item=raw):
                    self.assertRegex(raw, DOUBLE_QUOTED)


class ScopeHelpers(unittest.TestCase):
    """The helpers above, on inputs whose answer is known."""

    def test_custom_section_removal_keeps_what_follows(self):
        body = "# R\n\n- a\n\n## Custom engine\n\n- c\n\n### Sub\n\n- d\n\n## Mobile\n\n- m\n"
        self.assertEqual(without_custom_sections(body), "# R\n\n- a\n\n## Mobile\n\n- m\n")

    def test_path_items_read_every_scalar_form(self):
        front = 'paths:\n  - "a/**"\n  - \'b/**\'\n  - c/**\nother: 1'
        self.assertEqual(path_items(front), [('"a/**"', "a/**"), ("'b/**'", "b/**"), ("c/**", "c/**")])
        self.assertEqual(path_items('paths: ["a/**"]'), [('["a/**"]', None)])


if __name__ == "__main__":
    unittest.main()
