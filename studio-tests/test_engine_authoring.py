"""Authoring and workflow skills on Custom: the Phase 10 fixes of the
authoring-and-workflow-skills lane (fix plan section 12, AM28).

Run: python -m unittest discover -s studio-tests -p test_engine_authoring.py -v
Each test names the review item it covers (session scratchpad
aaa-engine/wf2/result.json, lane "authoring-and-workflow-skills"). They check
files on disk and, for R6, the output of adr-status.sh in two fixture projects;
not Claude's behaviour in a session.
"""
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import (  # noqa: E402
    ROOT, added_unit_violations, base_release_file, layout_rows, read, resolve_layout_row, row_lead,
    row_owner)
from test_engine_phase8 import SETUP_CUSTOM, section_text  # noqa: E402
from test_engine_scope import TwoFixtures, project_yaml  # noqa: E402

ADR_TEMPLATE = ".claude/docs/templates/architecture-decision-record.md"
ADR_SKILL = ".claude/skills/architecture-decision"
CONTRACT = f"{ADR_SKILL}/CONTRACT.md"
GATHER = f"{ADR_SKILL}/references/3-gather-context.md"
GENERATE = f"{ADR_SKILL}/references/5-generate.md"
ENGINE_MODE = f"{ADR_SKILL}/references/engine-mode.md"
ADR_SPEC = "studio-tests/skills/authoring/architecture-decision.md"
CEA_ADR = ".claude/docs/director-gates/cea-adr.md"
GATES_DIR = ".claude/docs/director-gates"
GATE_PRE_PRODUCTION = ".claude/skills/gate-check/references/gate-pre-production.md"
GATE_ASSESSMENT = ".claude/skills/gate-check/references/4-assessment.md"
CREATE_EPICS = ".claude/skills/create-epics/SKILL.md"
CREATE_STORIES = ".claude/skills/create-stories/SKILL.md"
SMOKE_RUN = ".claude/skills/smoke-check/references/2-run-tests.md"
TEST_HELPERS = ".claude/skills/test-helpers/SKILL.md"
TEAM_AUDIO = ".claude/skills/team-audio/SKILL.md"
TEAM_AUDIO_SPEC = "studio-tests/skills/team/team-audio.md"
LAYOUT_NAME = "custom-engine-layout.md"
MODULE_SPECS = "docs/architecture/modules"

# R6: the engines whose ADRs adr-status.sh must read as the base release did.
R6_ENGINES = ("Godot", "Web")
R6_ADR = "docs/architecture/adr-0001-from-base-template.md"
# R7: the two review-mode notes and the line engine sections only prints.
REVIEW_MODE_CHECK = "**Review mode check**"
CEA_NOT_RUN = "CEA-ADR not run — engine.name is <engine>, not Custom"
# R53: a closed "`agent` (Domain, Domain, ...)" routing map.
DOMAIN_MAP_BULLET = re.compile(r"`[\w-]+`\s*\((?:[A-Z][\w/&. -]*,\s*){1,}")
# R53 spec cases: the module whose ADR each case decides, and the agent the
# layout gives it (Lead, or Owner where the Lead is chief-engine-architect or none).
R53_SPEC_MODULES = {"Assets": "engine/assets/", "Cinematics": "engine/cinematics/"}
TOP_ARCHITECT = "chief-engine-architect"
# R60: each "Context to pass" field of cea-adr.md and the words that name it
# in 5-generate's CEA-ADR "Pass:" bullet. Recorded, not derived: which words
# name a field is a reading of its prose.
CEA_ADR_FIELDS = {
    "ADR file path": ("ADR file path",),
    "`engine.name` and the stack": ("stack",),
    "`performance.frame_budget_ms`": ("frame_budget_ms", "target_framerate"),
    "Path to `docs/engine-reference/custom/VERSION.md`": ("VERSION.md",),
    "Path to `docs/architecture/memory-invariants.md`": ("memory-invariants.md",),
    "Related ADRs": ("ADRs",),
}
DRAFT_CONTENT = "(or draft content)"
VERDICTS_LINE = re.compile(r"(?ms)^\*\*Verdicts\*\*:(.*?)(?=\n\s*\n|\Z)")
VERDICT_WORDS = 3
NOT_ASSESSED = "NOT ASSESSED"
# R114: the line /architecture-decision writes and the gate reads.
CEA_ADR_RECORD = "CEA-ADR: <verdict> (<date>"
# R125: the budgets the Custom gate block reads, and their two sources.
BUDGET_SOURCES = ("project.yaml", "technical-preferences.md")
PERF_BUDGETS_LINE = "perf_budgets"
# R118: the WAIVED-path build check.
BUILD_CHECK = "**Build check — the WAIVED path only**"
SMOKE_BY_EXIT = re.compile(r"Custom,?\s*`commands\.smoke`(?:`[^`]*`|[^.;`])*read by exit\s+code")
# R111: the Custom helper section and the setter of testing.framework.
HELPERS_CUSTOM_HEADING = "Custom (C++ / Rust)"
# R138: the asset cookers' owner in the layout.
COOKER_OWNER = "asset-build-tooling-engineer"
COOKERS_UNDER = re.compile(r"cookers under ((?:`[^`]+`(?:,\s*|\s+and\s+|\s+or\s+)?)+)")
# R121 / R107: the module epic's slug, and the two minimal sections.
MODULE_EPIC_SLUG = "engine-<module>"
STORY_READINESS_SPEC = "studio-tests/skills/readiness/story-readiness.md"
SPEC_CASE = re.compile(r"^### Case .*?(?=^### |^## |\Z)", re.M | re.S)
MODULE_SPEC_NAME = re.compile(r"docs/architecture/modules/([\w-]+)\.md")
EPICS_MINIMAL = "`minimal`: the brief"
STORIES_MINIMAL = "`minimal`: build the epic from the brief"
ROUTE_TIER = "standard"
SETTINGS_SKILL = "/project-settings"
# R63: the audio module's owner, its Lead, the Step 3 Custom block and what it
# leaves to technical-artist, and the shared paragraph after the team.size list.
AUDIO_OWNER = "audio-engine-engineer"
AUDIO_LEAD = "simulation-systems-lead"
TEAM_AUDIO_STEP_3 = "Step 3 spawns"
TECH_ARTIST_VISUALS_ONLY = "`technical-artist` keeps the audio-reactive visual effects only"
TEAM_SIZE_SHARED = "A non-core agent needed at `individual`"
# R108: a module's TR entries are selected by their gdd: path, never by system:
# alone (a game GDD with the same slug shares the system and the sequence).
MODULE_TR_BY_GDD = "whose `gdd:` is"
MODULE_TR_BY_SYSTEM = "whose `system:` is the module"
REGISTRY = "tr-registry.yaml"
# R53: the gate Step 5.6 runs; Step 5.5's item never merges it into its own call.
CEA_ADR_GATE = "CEA-ADR"
# R111: the C++ test-framework ADR item of /setup-engine custom points to
# /test-helpers instead of stating what CTest does.
FRAMEWORK_SETTING = "testing.framework=<name>"
HELPERS_SKILL = "/test-helpers"
# R113: /setup-engine custom's C5 and the route to /dev-story.
C5_HEADING = "C5. No scaffold (Section 7.5)"
C5_ROUTE = ("/create-epics", "/create-stories", "/dev-story")


def between(text, start, end):
    """The text from `start` up to the next `end` after it, or None."""
    begin = text.find(start)
    if begin < 0:
        return None
    stop = text.find(end, begin + len(start))
    return text[begin:stop if stop >= 0 else len(text)]


def units(text):
    """Paragraphs and list items of `text`, each joined onto one line."""
    out, current = [], []
    for line in text.replace("\r", "").splitlines():
        if not line.strip() or re.match(r"^\s*(?:[-*+]|\d+\.)\s|^#|^\|", line):
            if current:
                out.append(" ".join(current))
            current = [line.strip()] if line.strip() and not line.startswith(("#", "|")) else []
        else:
            current.append(line.strip())
    if current:
        out.append(" ".join(current))
    return out


def line_before(text, start):
    """The line directly above the first line that starts with `start`, or None."""
    lines = text.replace("\r", "").splitlines()
    index = next((i for i, line in enumerate(lines) if line.startswith(start)), None)
    return lines[index - 1] if index else None


def numbered_item(text, number):
    """The numbered list item `number.` of `text`, with its continuation lines."""
    match = re.search(rf"(?ms)^{number}\.\s.*?(?=^\d+\.\s|^#|\Z)", text.replace("\r", ""))
    return match[0] if match else None


class AdrTemplateOnOtherEngines(unittest.TestCase):
    def test_adr_status_matches_base_on_non_custom(self):
        # R6: the six engine-mode sections are not live `##` headings of the
        # shared template, so adr-status.sh reads a base-template ADR as base did.
        template = base_release_file(ADR_TEMPLATE)
        if template is None:
            self.skipTest("base release is not in this clone")
        for engine in R6_ENGINES:
            files = {"project.yaml": project_yaml(engine, workflow="standard"), R6_ADR: template}
            with self.subTest(engine=engine), TwoFixtures(self, files) as fx:
                out = fx.both(".claude/scripts/adr-status.sh", "--root", ".")
                self.assertEqual(out["work"], out["base"])


class ArchitectureDecisionEngineMode(unittest.TestCase):
    def test_review_mode_notes_say_full_engine_mode(self):
        # R7: the solo and lean notes skip CEA-ADR only in full engine mode;
        # engine sections only prints the not-run line at every review_mode.
        block = between(read(GENERATE), REVIEW_MODE_CHECK, "5.6.")
        self.assertIsNotNone(block, "no Review mode check in 5-generate.md")
        for mode in ("Solo", "Lean"):
            with self.subTest(mode=mode):
                self.assertIn(f'(full engine mode: also "CEA-ADR skipped — {mode} mode.")', block)
        self.assertNotIn("(engine mode: also", block)
        self.assertIn(CEA_NOT_RUN, block)

    def test_contract_names_step_4_for_other_engines(self):
        # R8: the contract says what --engine-internal adds on another engine.
        sentence = next((s for s in re.split(r"(?<=[.;])\s+", read(CONTRACT).replace("\r", ""))
                         if "`--engine-internal` on any other engine" in s), None)
        self.assertIsNotNone(sentence, "no CONTRACT sentence about --engine-internal on another engine")
        self.assertIn("Step 4", sentence)

    def test_engine_mode_resolves_lead_through_layout(self):
        # R53: Step 5.5's lead comes from the layout, not a copied domain map.
        text = read(ENGINE_MODE).replace("\r", "")
        step = next((u for u in units(text) if u.startswith("4. **Step 5.5**")), None)
        self.assertIsNotNone(step, "no Step 5.5 item under What changes")
        self.assertIn(LAYOUT_NAME, step)
        self.assertIn(TOP_ARCHITECT, step)
        for number, line in enumerate(text.splitlines(), 1):
            with self.subTest(line=number):
                self.assertIsNone(DOMAIN_MAP_BULLET.search(line), line)
        self.assertNotIn("Domains are the engine's modules:", text)
        # Step 5.6 spawns CEA-ADR beside TD-ADR after 5.5's revision
        # (5-generate.md); Step 5.5's item never folds the gate into its call.
        self.assertNotIn(CEA_ADR_GATE, step)

    def test_spec_cases_route_assets_and_cinematics_by_the_layout(self):
        # R53 spec cases: the agent each case expects is the layout's.
        spec = read(ADR_SPEC).replace("\r", "")
        rows = layout_rows()
        for domain, module in R53_SPEC_MODULES.items():
            row = resolve_layout_row(module, rows)
            lead = row_lead(row)
            expected = row_owner(row) if lead in (TOP_ARCHITECT, "none") else lead
            case = re.search(rf"(?ms)^### Case \d+:[^\n]*{domain} ADR.*?(?=^### |^## |\Z)", spec)
            with self.subTest(domain=domain):
                self.assertIsNotNone(case, f"no spec case for a {domain} ADR")
                spawned = set(re.findall(r"Step 5\.5 spawns `([\w-]+)`", case[0]))
                self.assertEqual(spawned, {expected})

    def test_cea_adr_caller_passes_every_context_field(self):
        # R60: 5-generate's CEA-ADR Pass bullet names each field cea-adr.md asks for.
        context = between(read(CEA_ADR).replace("\r", ""), "**Context to pass**:", "\n\n")
        fields = [line[2:] for line in context.splitlines() if line.startswith("- ")]
        self.assertTrue(fields, "cea-adr.md lists no context field")
        self.assertIn(DRAFT_CONTENT, fields[0])
        step = between(read(GENERATE).replace("\r", ""), "**Engine mode — CEA-ADR", "5.7.")
        self.assertIsNotNone(step, "no CEA-ADR step in 5-generate.md")
        passed = next((u for u in units(step) if u.startswith("- Pass:")), "")
        for field in fields:
            key = next((k for k in CEA_ADR_FIELDS if field.startswith(k)), None)
            with self.subTest(field=field):
                self.assertIsNotNone(key, "a context field with no entry in CEA_ADR_FIELDS")
                for word in CEA_ADR_FIELDS[key]:
                    self.assertIn(word, passed)

    def test_gate_verdicts_lines_list_three_words(self):
        # R59: no Verdicts line lists NOT ASSESSED (director-gates.md).
        for path in sorted((ROOT / GATES_DIR).glob("*.md")):
            for match in VERDICTS_LINE.finditer(path.read_text(encoding="utf-8").replace("\r", "")):
                with self.subTest(gate=path.name):
                    self.assertNotIn(NOT_ASSESSED, match[1])
                    self.assertEqual(len(match[1].split(" / ")), VERDICT_WORDS, match[1])

    def test_cea_adr_verdict_is_written_where_the_gate_reads_it(self):
        # R114: the CEA-ADR step writes the line both gate files look for.
        step = between(read(GENERATE).replace("\r", ""), "**Engine mode — CEA-ADR", "5.7.")
        self.assertIsNotNone(step, "no CEA-ADR step in 5-generate.md")
        for path, text in ((GENERATE, step), (GATE_PRE_PRODUCTION, read(GATE_PRE_PRODUCTION)),
                           (GATE_ASSESSMENT, read(GATE_ASSESSMENT))):
            with self.subTest(path=path):
                self.assertIn(CEA_ADR_RECORD, text)

    def test_engine_mode_links_the_module_spec(self):
        # R108: full engine mode reads the module spec and its TR ids, names
        # them under GDD Requirements Addressed, and syncs against the spec.
        text = read(ENGINE_MODE)
        self.assertIn(MODULE_SPECS + "/", text)
        self.assertIn("GDD Requirements Addressed", text)
        self.assertIn("TR-<module>-NNN", text)
        gather = read(GATHER)
        self.assertIn(MODULE_SPECS + "/", gather)
        sync = between(read(GENERATE), "5.7. **GDD Sync Check**", "5. **Write approval**")
        self.assertIn("module spec", sync)
        base = base_release_file(GATHER)
        if base is not None:
            self.assertEqual(added_unit_violations(base, read(GATHER)), [])
        # The module's registry entries are those whose gdd: is the module spec.
        for path in (GATHER, ENGINE_MODE):
            selecting = [u for u in units(read(path)) if MODULE_SPECS in u and REGISTRY in u]
            with self.subTest(path=path):
                self.assertTrue(selecting, "no unit reads the module's registry entries")
                for unit in selecting:
                    self.assertIn(MODULE_TR_BY_GDD, unit)
                    self.assertNotIn(MODULE_TR_BY_SYSTEM, unit)
        # P10 critic F2: the story route selects a module's entries the same way.
        # create-epics allows a game GDD and a module spec with the same slug
        # (`audio` and `engine-audio`), so a filter by system: would put the game
        # GDD's TR ids in the engine epic.
        for path in (CREATE_EPICS, CREATE_STORIES):
            selecting = [u for u in units(read(path)) if "registry" in u and ("**Module**" in u or "`Module:`" in u)]
            with self.subTest(path=path):
                self.assertTrue(selecting, "no unit selects a module epic's registry entries")
                for unit in selecting:
                    self.assertIn(MODULE_TR_BY_GDD, unit)
                    self.assertNotIn(MODULE_TR_BY_SYSTEM, unit)
        # Spec Case 13 holds a same-slug game GDD entry the table must not list.
        case = re.search(r"(?ms)^### Case 13:.*?(?=^### |^## |\Z)", read(ADR_SPEC).replace("\r", ""))
        self.assertIsNotNone(case, "no spec Case 13")
        self.assertRegex(case[0], r"`TR-jobs-\d{3}`[^\n]*`gdd: design/gdd/jobs\.md`")
        self.assertRegex(case[0], r"(?m)^- \[ \] The table does not list `TR-jobs-\d{3}`")


class GateCheckCustomBlock(unittest.TestCase):
    def test_custom_gate_reads_budgets_from_their_sources(self):
        # R125 (gate part): the Custom block and its CEA calls read the budget
        # keys as the any-engine check does, not from a resolved perf_budgets line.
        for path in (GATE_PRE_PRODUCTION, GATE_ASSESSMENT):
            text = read(path)
            with self.subTest(path=path):
                self.assertNotIn(PERF_BUDGETS_LINE, text)
                unit = next((u for u in units(text) if "`performance.frame_budget_ms`" in u
                             and ("is set" in u or "CEA" in u or "gate file lists" in u)), "")
                for source in BUDGET_SOURCES:
                    self.assertIn(source, unit)


class SmokeAndHelpersOnCustom(unittest.TestCase):
    def test_waived_build_check_on_custom_is_not_smoke_by_exit_code(self):
        # R118: the WAIVED build check never passes on commands.smoke's exit code.
        block = between(read(SMOKE_RUN).replace("\r", ""), BUILD_CHECK, "\n---")
        self.assertIsNotNone(block, "no build-check paragraph")
        self.assertIsNone(SMOKE_BY_EXIT.search(block))
        custom = next((s for s in re.split(r"(?<=[.;])\s+", block) if "on Custom" in s), "")
        self.assertIn("`commands.build`", custom)
        self.assertIn("test-run.sh custom", block)

    def test_helpers_send_the_framework_choice_to_an_adr_and_project_settings(self):
        # R111: /test-setup never picks a C++ test framework.
        section = section_text(read(TEST_HELPERS), HELPERS_CUSTOM_HEADING)
        self.assertIsNotNone(section)
        self.assertNotIn("/test-setup", section)
        for token in ("/architecture-decision", SETTINGS_SKILL, "testing.framework"):
            self.assertIn(token, section)
        # /setup-engine custom's framework ADR item points to /test-helpers; it
        # states no unledgered fact about CTest.
        item = next((u for u in units(read(SETUP_CUSTOM)) if FRAMEWORK_SETTING in u), None)
        self.assertIsNotNone(item, "custom.md has no testing.framework item")
        self.assertIn(HELPERS_SKILL, item)
        self.assertNotIn("asserts nothing", item)


class SetupAndPipelineOnCustom(unittest.TestCase):
    def test_setup_places_cookers_with_their_owner(self):
        # R138: every path cookers are placed under is the cookers' owner's.
        text = read(SETUP_CUSTOM)
        found = COOKERS_UNDER.findall(text)
        self.assertTrue(found, "custom.md places no cookers")
        rows = layout_rows()
        for group in found:
            for path in re.findall(r"`([^`]+)`", group):
                with self.subTest(path=path):
                    self.assertEqual(row_owner(resolve_layout_row(path, rows)), COOKER_OWNER)

    def test_module_epics_take_the_engine_slug(self):
        # R121: a module epic never shares a folder with a game epic.
        epics = between(read(CREATE_EPICS).replace("\r", ""), "**Custom** (`engine.name: Custom`)", "\n2. ")
        self.assertIsNotNone(epics)
        self.assertIn(MODULE_EPIC_SLUG, epics)
        stories = between(read(CREATE_STORIES).replace("\r", ""), "**Custom, a `Module:` epic**", "\n3. ")
        self.assertIsNotNone(stories)
        self.assertIn(MODULE_EPIC_SLUG, stories)

    def test_skill_spec_module_stories_sit_in_engine_epics(self):
        # R121 follow-up: a /story-readiness case whose story is traced to
        # docs/architecture/modules/<m>.md keeps it at production/epics/engine-<m>/.
        cases = [c for c in SPEC_CASE.findall(read(STORY_READINESS_SPEC).replace("\r", ""))
                 if "**Module**:" in c]
        self.assertTrue(cases, "story-readiness.md has no Module: case: update this test")
        for case in cases:
            title = case.splitlines()[0]
            for module in sorted(set(MODULE_SPEC_NAME.findall(case))):
                slug = MODULE_EPIC_SLUG.replace("<module>", module)
                with self.subTest(case=title, module=module):
                    self.assertNotIn(f"production/epics/{module}/", case)
                    self.assertIn(f"production/epics/{slug}/", case)

    def test_minimal_tier_stops_the_module_route(self):
        # R107 (D4): at minimal, Custom with module specs stops with a pointer.
        for path, heading in ((CREATE_EPICS, EPICS_MINIMAL), (CREATE_STORIES, STORIES_MINIMAL)):
            section = section_text(read(path), heading) or ""
            unit = next((u for u in units(section) if "Custom" in u and MODULE_SPECS in u), "")
            with self.subTest(path=path):
                self.assertIn(ROUTE_TIER, unit)
                self.assertIn(SETTINGS_SKILL, unit)
        c5 = section_text(read(SETUP_CUSTOM), C5_HEADING) or ""
        self.assertIn(f"`workflow: {ROUTE_TIER}`", c5)
        self.assertIn(SETTINGS_SKILL, c5)

    def test_c5_names_the_route_to_dev_story(self):
        # R113 (D5 a): C5 step 3 names the epic and story route before /dev-story.
        c5 = section_text(read(SETUP_CUSTOM), C5_HEADING)
        self.assertIsNotNone(c5)
        step = numbered_item(c5, 3)
        self.assertIsNotNone(step, "C5 has no step 3")
        positions = [step.find(skill) for skill in C5_ROUTE]
        self.assertNotIn(-1, positions, step)
        self.assertEqual(positions, sorted(positions), step)

    def test_team_audio_routes_engine_audio_to_its_owner(self):
        # R63: on Custom, engine-side audio goes to the engine/audio/ owner; the
        # other engines' text is the base release's.
        text = read(TEAM_AUDIO)
        custom = [u for u in units(text) if "Custom" in u and AUDIO_OWNER in u]
        self.assertTrue(custom, "no Custom unit names audio-engine-engineer")
        # Step 3's Custom block routes engine-side audio and the integration
        # check to the owner, escalates to its Lead, and leaves technical-artist
        # the audio-reactive visuals only.
        step3 = section_text(text, "Step 3: Technical Implementation (parallel)") or ""
        block = next((u for u in units(step3) if u.startswith("**Custom**")
                      and TEAM_AUDIO_STEP_3 in u), None)
        self.assertIsNotNone(block, "no Custom paragraph in Step 3 that says what Step 3 spawns")
        for token in (AUDIO_OWNER, AUDIO_LEAD, "integration check", TECH_ARTIST_VISUALS_ONLY):
            with self.subTest(token=token):
                self.assertIn(token, block)
        # The shared paragraph after the team.size list follows the line it
        # followed in the base release, so no Custom item absorbs it.
        self.assertEqual(row_owner(resolve_layout_row("engine/audio/", layout_rows())), AUDIO_OWNER)
        base = base_release_file(TEAM_AUDIO)
        if base is not None:
            self.assertEqual(added_unit_violations(base, text), [])
            self.assertEqual(line_before(text, TEAM_SIZE_SHARED), line_before(base, TEAM_SIZE_SHARED))
        self.assertIn(AUDIO_OWNER, read(TEAM_AUDIO_SPEC))


if __name__ == "__main__":
    unittest.main()
