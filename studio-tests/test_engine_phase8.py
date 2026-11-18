"""Structural contracts added by fix plan Phase 8, lane A (score remediation).

Run: python -m unittest discover -s studio-tests -p test_engine_phase8.py -v
The fixes and their deductions are in
docs/research/aaa-engine-support-2026/fix-plan.md, section 10. These check
files on disk, not Claude's behaviour in a session.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import (  # noqa: E402
    BASE_RELEASE, CROSS_CUTTING_RULES, CUSTOM_AGENT_SPEC_DIR, FRONTMATTER, RELEASE_NOTE_SECTIONS,
    ROOT, added_unit_violations, base_release_file, base_release_names, frontmatter, layout_rows,
    read, resolve_layout_row, row_lead, row_owner, row_rules)

ARCHITECT = "chief-engine-architect"


def custom_agents():
    """The Custom agents: one spec each under studio-tests/agents/engine/custom/."""
    return sorted(p.stem for p in (ROOT / CUSTOM_AGENT_SPEC_DIR).glob("*.md"))


def section_text(text, heading):
    """The body under a markdown heading, up to the next heading of the same or
    a higher level outside a code fence (a `# Rust` comment in a fenced layout
    is not a heading), or None when the heading is absent."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines)
                  if line.startswith("#") and line.rstrip().lstrip("#").strip() == heading), None)
    if start is None:
        return None
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    body, fenced = [], False
    for line in lines[start + 1:]:
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(rf"#{{1,{level}}} ", line):
            break
        body.append(line)
    return "".join(body)


def names(text, agent):
    return re.search(rf"(?<![\w-]){re.escape(agent)}(?![\w-])", text) is not None


def bullets(text):
    """Each list item with its indented continuation lines, joined."""
    items, current = [], None
    for line in text.splitlines():
        if line.startswith("- "):
            current = [line]
            items.append(current)
        elif current is not None and line.startswith("  ") and line.strip():
            current.append(line)
        else:
            current = None
    return [" ".join(item) for item in items]


# Fix 8.1 (D2). A placement is a path under a Custom root with at least one
# folder below the root (`engine/vfx/`, `crates/math/src/aabb4.rs`). Not
# placements: a template (`engine/<module>/...`), a wildcard root (`engine/*`)
# and a workspace member string (`"engine/core"`), which names a manifest
# entry, not where code goes. These are the forms found in the tree when the
# test was written; a new form must be added here, or a placement written in it
# goes unchecked (.claude/rules/skill-authoring.md:76-79).
PLACEMENT = re.compile(r"(?<![\w/<.-])((?:engine|crates|game)/[\w.{},*-]+/[\w./{},*-]*)")
# An example's path comment: the first line of a code block names its file.
EXAMPLE_PATH_LINE = re.compile(r"^[ \t]*(?://|#)[ \t]*((?:engine|crates|game)/\S+)", re.M)


def agent_placements(text):
    """(line, path) for each placement in the agent's Module Layout section and
    each example path comment anywhere in the file."""
    found = []
    for line in (section_text(text, "Module Layout") or "").splitlines():
        found += [(line, path.rstrip(",.;:")) for path in PLACEMENT.findall(line)]
    for match in EXAMPLE_PATH_LINE.finditer(text):
        line = text[match.start():text.find("\n", match.start())]
        found.append((line, match[1].rstrip(",.;:")))
    return found


# Fix 8.3 (D4). The Custom shader file-name order the rule sets (it loads on
# the path, so it wins): `[stage-or-kind]_[name]`. The rule lists `vs`, `ps`,
# `cs`, `ms`, `as`, `rgen`, "…", `common`; the "…" stands for the other
# pipeline stages, listed here.
SHADER_RULE = ".claude/rules/shader-code.md"
SHADER_AGENT = ".claude/agents/shader-pipeline-engineer.md"
SHADER_NAME_ORDER = "[stage-or-kind]_[name]"
OTHER_SHADER_STAGES = {"gs", "hs", "ds", "rint", "rahit", "rchit", "rmiss", "rcall"}
SHADER_FILE = re.compile(r"\b([A-Za-z0-9_]+)\.(?:hlsl|slang)\b")
# The rule's section for a project's own engine: scoped by its heading, so its
# bullets need not repeat "Custom" (Q8, section-level scoping).
SHADER_CUSTOM_SECTION = "## A project's own engine"


def shader_stage_prefixes():
    """The stage and kind prefixes the rule lists on its Custom naming bullet."""
    naming = next((item for item in bullets(read(SHADER_RULE)) if item.startswith("- Custom engine")
                   and SHADER_NAME_ORDER in item), "")
    return set(re.findall(r"`([a-z]{2,6})`", naming)) | OTHER_SHADER_STAGES


# Fix 8.4 (D5). gameplay-code.md's Custom text sits in its own guarded section;
# the guided /setup-engine question for a repo that may hold its own engine.
GAMEPLAY_RULE = ".claude/rules/gameplay-code.md"
GAMEPLAY_CUSTOM_HEADING = "Custom engine (`engine.name: Custom`)"
GUIDED_MODE = ".claude/skills/setup-engine/references/2-guided-mode.md"
OWN_ENGINE_QUESTION = "Is this your own engine?"

# Fix 8.5 (D6). C7 of setup-engine's Custom reference names the Custom agents;
# its first paragraph, up to "They are used only", is the list.
SETUP_CUSTOM = ".claude/skills/setup-engine/references/custom.md"
C7_HEADING = "C7. The engine agents (Section 9)"
C7_LIST_END = "They are used only"
# Git permissions a skill added by this change may hold: subcommands that read
# history, refs or the working tree. Kept as a list because "read-only" is a
# property of each git subcommand and its flags, not something the tree records
# (.claude/rules/skill-authoring.md:76-79); a new read-only form is added here
# with its reason.
# These forms are read-only only together with the settings deny rule below:
# `git diff`, `git log`, `git show` and `git rev-list` take `--output=<file>`
# ("Output to a specific file instead of stdout", git-diff docs; git 2.52
# rejects an abbreviated `--outp=`), which writes any file: `git rev-list
# --output=<file> HEAD` creates or truncates it (R33). Fix plan AM19 denies it in
# .claude/settings.json, one Bash and one PowerShell rule per subcommand; the
# test checks both spellings against them, and that a command merely naming
# the flag (a commit message) is not refused. `git log --output-indicator-*`
# (display only) is also refused by the log rule: an accepted cost.
# Residual, not shown here: what the list grants beyond the subcommand's own
# options (for example a shell redirection after an allowed form) is decided
# by Claude Code's command matching, which this file-level test cannot run.
READ_ONLY_GIT_PERMISSIONS = {
    "git log *", "git show *", "git diff *", "git status *", "git rev-parse *", "git rev-list *",
    "git merge-base *", "git tag --list*", "git branch --list *",
    "git hash-object -- *",  # no -w: prints the id, writes no object
}
GIT_PERMISSION = re.compile(r"Bash\((git\b[^)]*)\)")
SETTINGS = ".claude/settings.json"
# The allowed subcommands that take --output, and the deny rules AM19 adds:
# one per subcommand, so a command that merely mentions the flag (a commit
# message naming it, P8 F13) is not refused on every engine.
GIT_OUTPUT_SUBCOMMANDS = ("git diff", "git log", "git show", "git rev-list")
GIT_OUTPUT_DENY = tuple(f"{tool}({subcommand} *--output*)" for tool in ("Bash", "PowerShell")
                        for subcommand in GIT_OUTPUT_SUBCOMMANDS)
# R33: the probe that keeps GIT_OUTPUT_SUBCOMMANDS complete. Each allowed form,
# without its wildcard, runs in a temporary repository with
# `--output=<file> HEAD`; a form that creates the file writes through --output.
GIT_PROBE_OUTPUT = "probe-output.txt"
GIT_PROBE_TIMEOUT_S = 30
# Commands that mention --output without writing through it; none may be denied.
GIT_OUTPUT_NOT_DENIED = ('git commit -m "Add --output option to the cooker"',)


def denied(command, rules):
    """True when a Bash deny rule's pattern matches the command, reading `*`
    as any run of characters (the permission-rule wildcard)."""
    for rule in rules:
        pattern = re.fullmatch(r"Bash\((.*)\)", rule)
        if pattern and re.fullmatch(".*".join(map(re.escape, pattern[1].split("*"))), command):
            return True
    return False


def c7_agent_names():
    section = section_text(read(SETUP_CUSTOM), C7_HEADING) or ""
    return set(re.findall(r"`([\w-]+)`", section.split(C7_LIST_END)[0]))

# Fix 8.6 (D7, closes O9). On Custom, /architecture-review registers each
# module spec's section-10 criteria as TR-[module]-NNN and traces them; each
# reference file below gains an added paragraph naming Custom that holds the
# tokens listed (the base files stay unchanged apart from added units that
# name Custom).
ARCH_REVIEW_CUSTOM_BLOCKS = {
    ".claude/skills/architecture-review/references/1-load.md":
        ("docs/architecture/modules/", "10. Test Plan and Acceptance Criteria", "review-receipts.sh"),
    ".claude/skills/architecture-review/references/2-extract-requirements.md":
        ("docs/architecture/modules/", "TR-[module]-NNN", "system:"),
    ".claude/skills/architecture-review/references/3-traceability.md":
        ("TR-[module]-NNN", "GDD Requirements Addressed"),
    ".claude/skills/architecture-review/references/8-write.md":
        ("TR-[module]-NNN", "gdd: docs/architecture/modules/", "docs/architecture/modules/*.md"),
}
CREATE_STORIES = ".claude/skills/create-stories/SKILL.md"
CREATE_STORIES_MODULE_ITEM = "- **Custom, a `Module:` epic:** the same rule"
# T7: the line the module item writes for an unregistered criterion. A bare
# "NOT ASSESSED" would also match the item's other mentions.
CREATE_STORIES_NOT_REGISTERED_LINE = "NOT ASSESSED — criterion not registered"
ARCH_REVIEW_SPEC = "studio-tests/skills/review/architecture-review.md"
STALE_MODULE_ID_CLAIMS = ("not registered yet", "stay provisional")
# P8 critic F1: section 10 of a module spec is loaded whole. The template's
# section 10 opens with a comment and lists Unit, Integration and Benchmarks
# before the Done when criteria, so a fixed Grep window cuts the criteria
# first. The long fixture is the critic's case: 6 unit, 4 integration,
# 4 benchmark and 5 Done when lines.
ARCH_REVIEW_LOAD = ".claude/skills/architecture-review/references/1-load.md"
MODULE_SPEC_TEMPLATE = ".claude/docs/templates/engine-module-spec.md"
SECTION_10_HEADING = "## 10. Test Plan and Acceptance Criteria"
LONG_SECTION_10 = {"Unit": 6, "Integration": 4, "Benchmarks": 4, "Done when": 5}
GREP_AFTER_WINDOW = re.compile(r"-A (\d+)")
READ_TO_NEXT_HEADING = "to the line before the next `## ` heading"
# P8 critic F2: a module story with an unregistered criterion reaches both
# verdicts. The create-stories verdict line's count for those stories, and the
# id form the readiness TR-ID item and its NOT ASSESSED verdict name.
CREATE_STORIES_NOT_REGISTERED = "[N] with criteria not registered: NOT ASSESSED — run /architecture-review"
CREATE_STORIES_SPEC = "studio-tests/skills/pipeline/create-stories.md"
STORY_READINESS = ".claude/skills/story-readiness/SKILL.md"
STORY_READINESS_SPEC = "studio-tests/skills/readiness/story-readiness.md"
STORY_READINESS_TR_ITEM = "- [ ] **TR-ID valid**"
UNREGISTERED_MODULE_ID = "TR-[module]-???"


def long_section_10_spec():
    """The module-spec template with LONG_SECTION_10's lines in section 10."""
    lines = read(MODULE_SPEC_TEMPLATE).replace("\r", "").splitlines()
    start = lines.index(SECTION_10_HEADING)
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
    body = [line for line in lines[start + 1:end] if not line.startswith("- ")]
    body = body[:-1] if body and not body[-1].strip() else body
    for kind, count in LONG_SECTION_10.items():
        body += [f"- {kind}: criterion {n}" for n in range(1, count + 1)]
    return lines[:start + 1] + body + [""] + lines[end:]


def paragraphs(text):
    return [p for p in re.split(r"\n[ \t]*\n", text.replace("\r", "")) if p.strip()]


class Phase8LaneA(unittest.TestCase):
    def test_agent_module_layout_paths_belong_to_the_agent_or_name_the_owner(self):
        # Fix 8.1 (D2; amendment: the main session's option (a), 2026-11-16).
        # A Custom agent places code where the layout makes it the owner, or the
        # line holding the path names the layout's owner of that path. The tests
        # and build-files rows cut across modules and are skipped (an agent
        # writes its module's tests and build files without owning those rows).
        rows = layout_rows()
        seen = 0
        for agent in custom_agents():
            for line, path in agent_placements(read(f".claude/agents/{agent}.md")):
                row = resolve_layout_row(path, rows)
                seen += 1
                with self.subTest(agent=agent, path=path):
                    self.assertIsNotNone(row, "no layout row covers this path")
                    if set(row_rules(row)) & CROSS_CUTTING_RULES:
                        continue
                    owner = row_owner(row)
                    self.assertTrue(owner == agent or names(line, owner),
                                    f"layout owner {owner}, not named on: {line.strip()}")
        self.assertTrue(seen, "the scan found no placement: the forms are out of date")

    def test_architect_refers_to_the_layout_for_the_module_map(self):
        # Fix 8.2 (D3): the architect's responsibilities point to the layout,
        # the one statement of the module map, and keep no copy of its names.
        text = read(f".claude/agents/{ARCHITECT}.md")
        duties = section_text(text, "Core Responsibilities") or ""
        self.assertIn("custom-engine-layout.md", duties)
        modules = {path[len("engine/"):].rstrip("/") for row in layout_rows() for path in row["paths"]
                   if path.startswith("engine/") and "*" not in path}
        copied = sorted(set(re.findall(r"`([\w/]+)`", duties)) & modules)
        self.assertEqual(copied, [], "module names copied from the layout")

    def test_architect_layering_places_every_layout_module(self):
        # Fix 8.2 (D3): "an arrow may only point down" needs a layer for every
        # module the layout names (its first path; an alias is not a module).
        layering = section_text(read(f".claude/agents/{ARCHITECT}.md"), "Engine Layering") or ""
        diagram = re.search(r"```\n(.*?)```", layering, re.S)
        self.assertIsNotNone(diagram, "Engine Layering has no diagram")
        for row in layout_rows():
            primary = row["paths"][0] if row["paths"] else ""
            if not primary.startswith("engine/"):
                continue
            with self.subTest(module=primary):
                self.assertRegex(diagram[1], rf"(?<![\w/]){re.escape(primary)}(?![\w/])")

    def test_architect_delegation_reaches_every_engine_owner(self):
        # Fix 8.2 (D3): every owner of an `engine/` row, and its lead, is named
        # in the architect's Delegation Map, so a question about any module has
        # a route.
        delegation = section_text(read(f".claude/agents/{ARCHITECT}.md"), "Delegation Map") or ""
        self.assertTrue(delegation, "no Delegation Map section")
        for row in layout_rows():
            # A module row; the tests row also names `engine/**/tests/`.
            if not (row["paths"] and row["paths"][0].startswith("engine/")):
                continue
            for agent in {row_owner(row), row_lead(row)} - {"none", None, ARCHITECT}:
                with self.subTest(row=row["paths"][0], agent=agent):
                    self.assertTrue(names(delegation, agent))

    def test_no_agent_forbids_creating_the_module_it_owns(self):
        # Fix 8.2 (D3, world-streaming-engineer.md:291): a "Must NOT" item that
        # forbids creating a module the layout gives the agent contradicts the
        # layout.
        rows = layout_rows()
        for agent in custom_agents():
            section = section_text(read(f".claude/agents/{agent}.md"), "What This Agent Must NOT Do") or ""
            for path in re.findall(r"\b[Cc]reate\s+`((?:engine|crates)/[^`]+)`", section):
                row = resolve_layout_row(path, rows)
                with self.subTest(agent=agent, path=path):
                    self.assertNotEqual(row_owner(row) if row else None, agent)

    def test_custom_shader_file_names_follow_the_rule_order(self):
        # Fix 8.3 (D4): one Custom naming order. Both files state the rule's
        # order, and every shader file name in .claude/ starts with a stage or
        # kind prefix the rule lists.
        for path in (SHADER_RULE, SHADER_AGENT):
            with self.subTest(file=path):
                self.assertIn(SHADER_NAME_ORDER, read(path))
        prefixes = shader_stage_prefixes()
        self.assertTrue({"cs", "ps", "common"} <= prefixes, "the rule's prefix list was not found")
        seen = 0
        for path in sorted((ROOT / ".claude").rglob("*.md")):
            for stem in SHADER_FILE.findall(path.read_text(encoding="utf-8")):
                seen += 1
                with self.subTest(file=path.relative_to(ROOT).as_posix(), name=stem):
                    self.assertIn(stem.split("_")[0], prefixes)
        self.assertTrue(seen, "no shader file name found: the pattern is out of date")

    def test_shader_rule_keeps_the_other_engines_bullets(self):
        # Fix 8.3 (D4), R9-style: below the frontmatter, every base line of
        # shader-code.md is unchanged; an added paragraph or bullet outside the
        # Custom section names Custom; and Custom has its own line on branching,
        # so the other engines' "avoid dynamic branching" bullet does not bind it.
        base = base_release_file(SHADER_RULE)
        if base is None:
            self.skipTest(f"base release {BASE_RELEASE} absent from this clone (O14)")
        body = FRONTMATTER.sub("", read(SHADER_RULE), count=1).split(SHADER_CUSTOM_SECTION)[0]
        self.assertEqual(added_unit_violations(FRONTMATTER.sub("", base, count=1), body), [])
        self.assertTrue(any(item.startswith("- Custom engine") and "branch" in item
                            for item in bullets(body)),
                        "no Custom line on branching outside the Custom section")

    def test_gameplay_rule_keeps_the_other_engines_bullets(self):
        # Fix 8.4 (D5): gameplay-code.md loads on Godot `src/gameplay/**` too.
        # Below the frontmatter it equals the base release once its guarded
        # Custom section is taken out, and that section opens with the guard.
        base = base_release_file(GAMEPLAY_RULE)
        if base is None:
            self.skipTest(f"base release {BASE_RELEASE} absent from this clone (O14)")
        text = read(GAMEPLAY_RULE)
        section = section_text(text, GAMEPLAY_CUSTOM_HEADING)
        rest = FRONTMATTER.sub("", text, count=1)
        if section is not None:
            rest = rest.replace(f"## {GAMEPLAY_CUSTOM_HEADING}\n{section}", "")
        self.assertEqual(added_unit_violations(FRONTMATTER.sub("", base, count=1), rest), [])
        self.assertIsNotNone(section, f"no '## {GAMEPLAY_CUSTOM_HEADING}' section")
        guard = next((p for p in re.split(r"\n\s*\n", section) if p.strip()), "")
        for token in ("engine.name", "Custom", "ignore"):
            with self.subTest(guard_token=token):
                self.assertIn(token, guard)

    def test_release_notes_name_the_guided_mode_own_engine_question(self):
        # Fix 8.4 (D5): guided /setup-engine on a repo with a CMakeLists.txt or
        # Cargo.toml and no other engine's project file now asks the question
        # in 2-guided-mode.md; the notes for other engines must name it.
        self.assertIn(OWN_ENGINE_QUESTION, " ".join(read(GUIDED_MODE).split()))
        unreleased = {path: region.search(read(path))[0] for path, region in RELEASE_NOTE_SECTIONS.items()}
        passages = {
            "CHANGELOG.md": next((p for p in re.split(r"\n\s*\n", unreleased["CHANGELOG.md"])
                                  if p.startswith("Also on every engine")), ""),
            "UPGRADING.md": next((line for line in unreleased["UPGRADING.md"].splitlines()
                                  if line.startswith("| **Other engines** |")), ""),
        }
        for path, passage in passages.items():
            with self.subTest(path=path):
                self.assertTrue(passage, "the other-engines passage was not found")
                self.assertIn(OWN_ENGINE_QUESTION, " ".join(passage.split()))

    def test_setup_c7_names_every_custom_agent(self):
        # Fix 8.5 (D6, the form of original F3): C7's list of Custom agents
        # equals the Custom agent specs on disk.
        self.assertEqual(sorted(c7_agent_names()), custom_agents())

    def test_new_skills_hold_only_read_only_git_permissions(self):
        # Fix 8.5 (D6): every git permission in the allowed-tools of a skill
        # this change added (absent from the base release) is read-only.
        # AM19: the --output write path of the allowed forms is denied.
        deny = json.loads(read(SETTINGS))["permissions"]["deny"]
        for rule in GIT_OUTPUT_DENY:
            self.assertIn(rule, deny)
        for command in GIT_OUTPUT_NOT_DENIED:
            with self.subTest(not_denied=command):
                self.assertFalse(denied(command, deny), f"a deny rule in {SETTINGS} refuses {command!r}")
        for subcommand in GIT_OUTPUT_SUBCOMMANDS:
            for command in (f"{subcommand} --output=out.txt HEAD", f"{subcommand} HEAD --output out.txt"):
                with self.subTest(command=command):
                    self.assertTrue(denied(command, deny), f"no deny rule in {SETTINGS} matches {command!r}")
        base = base_release_names(".claude/skills")
        if base is None:
            self.skipTest(f"base release {BASE_RELEASE} absent from this clone (O14)")
        added = sorted(p.name for p in (ROOT / ".claude/skills").iterdir()
                       if (p / "SKILL.md").exists() and p.name not in base)
        self.assertTrue(added, "no skill added since the base release")
        for skill in added:
            for permission in GIT_PERMISSION.findall(frontmatter(read(f".claude/skills/{skill}/SKILL.md"))):
                with self.subTest(skill=skill, permission=permission):
                    self.assertIn(permission, READ_ONLY_GIT_PERMISSIONS)

    def test_every_allowed_git_form_that_writes_through_output_is_denied(self):
        # R33: GIT_OUTPUT_SUBCOMMANDS is not trusted as written. Every
        # READ_ONLY_GIT_PERMISSIONS form that writes a file through --output
        # on the installed git must be listed there, so the test above
        # requires its deny rules.
        if shutil.which("git") is None:
            self.skipTest("git is not on PATH")
        with tempfile.TemporaryDirectory(prefix="ccgs-git-output-") as repo:
            git = ["git", "-C", repo, "-c", "user.name=probe", "-c", "user.email=probe@example.invalid"]
            for args in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "probe"]):
                subprocess.run(git + args, check=True, capture_output=True, timeout=GIT_PROBE_TIMEOUT_S)
            target = Path(repo) / GIT_PROBE_OUTPUT
            for permission in sorted(READ_ONLY_GIT_PERMISSIONS):
                form = permission.rstrip("* ").split()[1:]
                with self.subTest(permission=permission):
                    target.unlink(missing_ok=True)
                    subprocess.run(git + form + [f"--output={target.as_posix()}", "HEAD"],
                                   capture_output=True, timeout=GIT_PROBE_TIMEOUT_S)
                    if target.exists():
                        self.assertIn(" ".join(["git", form[0]]), GIT_OUTPUT_SUBCOMMANDS,
                                      f"{permission!r} writes through --output and has no deny rule")

    def test_architecture_review_registers_module_criteria_on_custom(self):
        # Fix 8.6 (D7): load, extract, trace and write each gain a Custom
        # paragraph; nothing else in these base files changes.
        for path, tokens in ARCH_REVIEW_CUSTOM_BLOCKS.items():
            text = read(path)
            with self.subTest(file=path):
                block = next((p for p in paragraphs(text)
                              if "`engine.name: Custom`" in p and all(t in p for t in tokens)), None)
                self.assertIsNotNone(block, f"no Custom paragraph naming all of {tokens}")
                base = base_release_file(path)
                if base is None:
                    self.skipTest(f"base release {BASE_RELEASE} absent from this clone (O14)")
                self.assertEqual(added_unit_violations(base, text), [])

    def test_create_stories_uses_registered_module_ids(self):
        # Fix 8.6 (D7): a module epic's story takes the registered
        # TR-[module]-NNN; with none registered it writes TR-[module]-??? and a
        # NOT ASSESSED line, and no text says module ids are never registered.
        item = next((i for i in bullets(read(CREATE_STORIES)) if i.startswith(CREATE_STORIES_MODULE_ITEM)), "")
        self.assertTrue(item, "the Custom Module: item was not found")
        for token in ("/architecture-review", "TR-[module]-???", CREATE_STORIES_NOT_REGISTERED_LINE):
            with self.subTest(token=token):
                self.assertIn(token, item)
        unreleased = [region.search(read(path))[0] for path, region in RELEASE_NOTE_SECTIONS.items()]
        for text in [item, *unreleased]:
            for claim in STALE_MODULE_ID_CLAIMS:
                with self.subTest(claim=claim, text=text[:40]):
                    self.assertNotIn(claim, " ".join(text.split()))

    def test_architecture_review_spec_has_a_module_criteria_case(self):
        # Fix 8.6 (D7): the behaviour is a hypothesis until a live run; the
        # spec carries the case that run would check.
        cases = re.split(r"(?m)^### Case ", read(ARCH_REVIEW_SPEC).replace("\r", ""))[1:]
        found = [c for c in cases if "engine.name: Custom" in c and "docs/architecture/modules/" in c
                 and "tr-registry.yaml" in c and "TR-" in c]
        self.assertTrue(found, "no Custom case registers module criteria")

    def test_architecture_review_loads_all_of_each_module_section_10(self):
        # P8 critic F1: every fixed Grep window the Custom load paragraph names
        # must reach the next heading of the long fixture, and the paragraph
        # reads section 10 up to the next heading.
        block = next((p for p in paragraphs(read(ARCH_REVIEW_LOAD))
                      if "`engine.name: Custom`" in p and "docs/architecture/modules/" in p), "")
        self.assertTrue(block, "the Custom module-spec load paragraph was not found")
        spec = long_section_10_spec()
        start = spec.index(SECTION_10_HEADING)
        for window in map(int, GREP_AFTER_WINDOW.findall(block)):
            with self.subTest(window=window):
                shown = spec[start + 1:start + 1 + window]
                self.assertTrue(any(line.startswith("## ") for line in shown),
                                f"-A {window} ends before the next heading; lost: "
                                f"{[l for l in spec[start + 1 + window:] if l.startswith('- Done when')]}")
        self.assertIn(READ_TO_NEXT_HEADING, " ".join(block.split()))

    def test_unregistered_module_criteria_reach_both_verdicts(self):
        # P8 critic F2: /create-stories counts such a story apart from Ready in
        # its verdict, and /story-readiness's TR-ID item and NOT ASSESSED
        # verdict take TR-[module]-??? whether or not a registry exists.
        block = next((p for p in paragraphs(read(CREATE_STORIES))
                      if "`engine.name: Custom`" in p and CREATE_STORIES_NOT_REGISTERED in " ".join(p.split())), "")
        self.assertTrue(block, "no Custom paragraph puts the unregistered count in the verdict line")
        self.assertIn("never as Ready", " ".join(block.split()))
        readiness = read(STORY_READINESS)
        item = next((i for i in bullets(readiness) if i.startswith(STORY_READINESS_TR_ITEM)), "")
        verdict = re.search(r"(?ms)^3\. \*\*NOT ASSESSED\*\*.*?(?=^4\. )", readiness)
        for text, where in ((item, "TR-ID item"), (verdict[0] if verdict else "", "NOT ASSESSED verdict")):
            with self.subTest(where=where):
                flat = " ".join(text.split())
                self.assertIn("`engine.name: Custom`", flat)
                self.assertIn(UNREGISTERED_MODULE_ID, flat)
        self.assertIn("whether or not a registry exists", " ".join(item.split()))
        cases = re.split(r"(?m)^### Case ", read(CREATE_STORIES_SPEC).replace("\r", ""))[1:]
        self.assertTrue([c for c in cases if "engine.name: Custom" in c and "Verdict: COMPLETE" in c
                         and "with criteria not registered" in c], "create-stories has no Custom verdict case")
        cases = re.split(r"(?m)^### Case ", read(STORY_READINESS_SPEC).replace("\r", ""))[1:]
        self.assertTrue([c for c in cases if "engine.name: Custom" in c and "TR-audio-???" in c
                         and "not READY" in c], "story-readiness has no Custom unregistered-criterion case")


if __name__ == "__main__":
    unittest.main()
