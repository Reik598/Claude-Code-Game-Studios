"""Structural contracts for the six skills this change added and the grants the
change gave shared skills (fix plan section 12, Phase 10, lane
new-skills-and-permissions; decisions AM28 D2, D3, D7).

Run: python -m unittest discover -s studio-tests -p test_engine_new_skills.py -v
Each test names the review item it guards (R- and T-numbers in the session's
Phase 10 triage). These check files on disk and run one read-only helper
(frame-stats.sh); they do not check Claude's behaviour in a session.
"""
import math
from pathlib import Path, PurePosixPath
import random
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import ROOT, frontmatter, layout_rows, read  # noqa: E402
from test_engine_phase9 import NEW_SKILL_ALLOWED_TOOLS, allowed_tools  # noqa: E402
from test_engine_scope import BASH, SCRIPT_ENV, SCRIPT_TIMEOUT_S  # noqa: E402
from test_engine_accuracy_gpu import BUILD_AGENT_NAME, ZONE_ROUTE, statements  # noqa: E402

SKILLS_DIR = ROOT / ".claude/skills"
SCRIPTS_DIR = ".claude/scripts"
NEW_SKILLS = sorted(NEW_SKILL_ALLOWED_TOOLS)

# R19, R34 (D7): a grant must not let a skill run test-run.sh with a command
# of its own choosing; --cmd, --root and --log take arbitrary text.
ARBITRARY_TEST_RUN = "bash .claude/scripts/test-run.sh custom --cmd 'git push --force'"
FREE_TEXT_OPTION = re.compile(r"^#\s+--(?:cmd|root|log)\b", re.M)
HELPER_GRANT = re.compile(r"^bash \.claude/scripts/([\w.-]+\.sh)\b")
GIT_GRANT = re.compile(r"^Bash\(git ([\w-]+)")
FENCE = "```"
HELPER_COMMAND_START = "bash .claude/scripts/"

# R35, R50 (D3): the statistics helper and the sample it is checked on.
FRAME_STATS = f"{SCRIPTS_DIR}/frame-stats.sh"
FRAME_STATS_ROWS = 1200
# Score report 5 D1, AM35(c): a count that is not a multiple of 100, so k*n/100
# has a fraction below one half for P95 and P99 (1139.05, 1187.01). Rounding
# the rank half up instead of up then reads ranks 1139 and 1187, not 1140 and
# 1188.
FRAME_STATS_UNEVEN_ROWS = 1199
FRAME_STATS_SEED = 20261117
FRAME_STATS_BUDGET_MS = 16.6
PERCENTILES = (50, 95, 99)
FLOAT_TOLERANCE = 1e-9
BAD_USAGE_EXIT = 2

API_SURFACE = ".claude/skills/api-review/references/surface.md"
API_REPORT = ".claude/skills/api-review/references/report.md"
API_SKILL = ".claude/skills/api-review/SKILL.md"
RELEASE_SKILL = ".claude/skills/engine-release/SKILL.md"
RELEASE_INVENTORY = ".claude/skills/engine-release/references/inventory.md"
# R37: other files that name the public-header folder; it is any module's
# include/, nested modules included (engine/**/include/).
PUBLIC_HEADER_MENTIONS = (
    ".claude/agents/core-systems-lead.md",
    ".claude/agents/engine-technical-writer.md",
    ".claude/docs/context-management.md",
    ".claude/skills/architecture-decision/references/engine-mode.md",
)
PIPELINE_SKILL = ".claude/skills/team-frame-pipeline/SKILL.md"
PIPELINE_PHASES = ".claude/skills/team-frame-pipeline/references/pipeline.md"
BENCH_SKILL = ".claude/skills/benchmark-report/SKILL.md"
BENCH_STATS = ".claude/skills/benchmark-report/references/statistics.md"
BENCH_REPORT = ".claude/skills/benchmark-report/references/report.md"
MEMORY_SKILL = ".claude/skills/memory-audit/SKILL.md"
MEMORY_EVIDENCE = ".claude/skills/memory-audit/references/evidence.md"
TRIAGE_SKILL = ".claude/skills/perf-regression-triage/SKILL.md"
TRIAGE_BISECT = ".claude/skills/perf-regression-triage/references/bisect-and-bug.md"
DEV_STORY = ".claude/skills/dev-story/SKILL.md"
STORY_DONE = ".claude/skills/story-done/SKILL.md"
TEAM_POLISH = ".claude/skills/team-polish/SKILL.md"
GATE_CHECK = ".claude/skills/gate-check/SKILL.md"
GATE_RUN = ".claude/skills/gate-check/references/3-run-gate-check.md"
SETUP_SKILL = ".claude/skills/setup-engine/SKILL.md"
SETUP_UPGRADE = ".claude/skills/setup-engine/references/11-upgrade.md"

# The two stops of /api-review that end the run before any verdict rule.
API_STOPS = ("engine.name is not Custom", "no change to review")
NOT_ASSESSED_REASON = re.compile(r"NOT ASSESSED —\s+([^`*\n]+?)(?:`|\*|$)", re.M)
CEA_LEAD_CASE = re.compile(r"Lead is\s+`chief-engine-architect`")
# R61: a layout row whose Lead cell says none sits outside the engine
# hierarchy; its Owner is not a lead, and security-engineer never implements.
LEAD_NONE = re.compile(r"^none\b")
REVIEWER_ONLY = re.compile(r"`security-engineer`[^.;]*never implements")
STORY_FIELDS = ("Story:", "Module:")
ENGINE_GATE = "NOT ASSESSED — engine.name is not Custom"
NO_MODEL_INVOCATION = re.compile(r"^disable-model-invocation:\s*true\s*$", re.M)
NO_MODEL_INVOCATION_TOKEN = "`disable-model-invocation: true`"
SKILL_SPEC_DIR = "studio-tests/skills"
SPEC_FRONTMATTER_LINE = "required frontmatter fields"
SPEC_HANDOFF_LINE = "next-step handoff"
NEXT_STEPS_SECTION = re.compile(r"^## [^\n]*Next Steps[^\n]*\n(.*?)(?=^## |\Z)", re.M | re.S)
SKILL_TOOL_RUN = re.compile(r"`/([\w-]+)`[^.`]*?with the Skill tool|with the Skill tool[^.`]*?`/?([\w-]+)")
USAGE_LINE = "If no argument is provided"
READ_INSTRUCTION = re.compile(r"(?i)\b(?:resolve|read)\b|project\.yaml")


def text_of(path):
    return read(path).replace("\r", "")


def body_of(path):
    return text_of(path).split("---", 2)[2]


def skill_folder_text(skill):
    """SKILL.md outside its frontmatter, plus every reference file."""
    folder = SKILLS_DIR / skill
    parts = [body_of(f".claude/skills/{skill}/SKILL.md")]
    parts += [p.read_text(encoding="utf-8").replace("\r", "") for p in sorted(folder.glob("references/*.md"))]
    return "\n".join(parts)


def between(text, start, end=None):
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start)) if end else -1
    return text[i:j if j >= 0 else len(text)]


def fenced_helper_commands(text):
    """Helper commands on their own line inside ``` fenced blocks, without a
    trailing # comment."""
    commands, fenced = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(FENCE):
            fenced = not fenced
        elif fenced and stripped.startswith(HELPER_COMMAND_START):
            commands.append(re.sub(r"\s+#.*$", "", stripped))
    return commands


def grant_matches(pattern, command):
    """A Bash(...) pattern read the way Claude Code reads it: `*` is any text."""
    regex = "".join(".*" if c == "*" else re.escape(c) for c in pattern)
    return re.fullmatch(regex, command, re.S) is not None


def bash_patterns(skill):
    return [e[len("Bash("):-1] for e in allowed_tools(skill) if e.startswith("Bash(")]


def all_skills():
    return sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))


def script_header(name):
    lines = []
    for line in text_of(f"{SCRIPTS_DIR}/{name}").splitlines():
        if not line.startswith("#"):
            break
        lines.append(line)
    return "\n".join(lines)


def table_row(text, first_cell):
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and cells and cells[0] == first_cell:
            return cells
    return []


def nearest_rank(values, k):
    ordered = sorted(values)
    return ordered[-(-k * len(ordered) // 100) - 1]


def run_frame_stats(*args):
    return subprocess.run([BASH, FRAME_STATS, *args], cwd=ROOT, env=SCRIPT_ENV, capture_output=True,
                          text=True, encoding="utf-8", timeout=SCRIPT_TIMEOUT_S)


class NewSkillsTests(unittest.TestCase):

    # R19, R34 (D7) --------------------------------------------------------
    def test_no_grant_lets_test_run_custom_run_any_command(self):
        for skill in all_skills():
            for pattern in bash_patterns(skill):
                with self.subTest(skill=skill, grant=pattern):
                    self.assertFalse(grant_matches(pattern, ARBITRARY_TEST_RUN),
                                     "the grant approves test-run.sh custom --cmd <anything>")

    def test_new_skill_helper_grants_end_before_free_text_options(self):
        seen = 0
        for skill in NEW_SKILLS:
            for pattern in bash_patterns(skill):
                helper = HELPER_GRANT.match(pattern)
                if not helper:
                    continue
                seen += 1
                if pattern.endswith("*") and FREE_TEXT_OPTION.search(script_header(helper[1])):
                    with self.subTest(skill=skill, grant=pattern):
                        self.fail("a trailing * reaches the helper's --cmd/--root/--log")
        self.assertTrue(seen, "no new skill grants a .claude/scripts helper: the scan is out of date")

    # R40 ------------------------------------------------------------------
    def test_new_skill_git_grants_name_a_step(self):
        for skill in NEW_SKILLS:
            text = skill_folder_text(skill)
            for entry in allowed_tools(skill):
                sub = GIT_GRANT.match(entry)
                if sub:
                    with self.subTest(skill=skill, grant=entry):
                        self.assertRegex(text, rf"git {re.escape(sub[1])}\b", "no step runs this git command")

    def test_api_review_reads_a_non_head_range_at_its_head(self):
        surface = text_of(API_SURFACE)
        self.assertIn("git show <head>:<path>", surface)
        self.assertIn("git show <head>:<dir>/", surface)

    # R35, R50 (D3) --------------------------------------------------------
    def test_frame_stats_matches_nearest_rank_computed_here(self):
        rng = random.Random(FRAME_STATS_SEED)
        frames = [round(rng.lognormvariate(math.log(12.0), 0.25), 3) for _ in range(FRAME_STATS_ROWS)]
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "capture.csv"
            rows = ["frame,frame_ms,gpu_ms"] + [f"{i},{v},{v / 2:.3f}" for i, v in enumerate(frames)]
            csv.write_bytes(("\r\n".join(rows) + "\r\n").encode())
            before = sorted(p.name for p in Path(tmp).iterdir())
            result = run_frame_stats(str(csv), "frame_ms", str(FRAME_STATS_BUDGET_MS))
            after = sorted(p.name for p in Path(tmp).iterdir())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, after, "frame-stats.sh wrote a file")
        seen = dict(line.split("\t", 1) for line in result.stdout.splitlines() if "\t" in line)
        self.assertEqual(int(seen.get("n", -1)), FRAME_STATS_ROWS)
        expected = {f"p{k}": nearest_rank(frames, k) for k in PERCENTILES}
        expected.update(max=max(frames), mean=sum(frames) / len(frames))
        for key, value in expected.items():
            with self.subTest(stat=key):
                self.assertAlmostEqual(float(seen[key]), value, delta=FLOAT_TOLERANCE * max(1.0, value))
        self.assertEqual(int(seen.get("over_budget", -1)), sum(v > FRAME_STATS_BUDGET_MS for v in frames))
        self.assertEqual(seen.get("method"), "nearest-rank")

    def test_frame_stats_rounds_ranks_up_on_a_small_sample(self):
        # Seven samples: P50 is rank ceil(3.5) = 4, P95 rank 7; a floor would
        # give ranks 3 and 6.
        frames = [5.0, 1.0, 7.0, 3.0, 2.0, 6.0, 4.0]
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "small.csv"
            csv.write_text("frame_ms\n" + "".join(f"{v}\n" for v in frames), encoding="utf-8")
            result = run_frame_stats(str(csv), "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        seen = dict(line.split("\t", 1) for line in result.stdout.splitlines() if "\t" in line)
        for k in PERCENTILES:
            with self.subTest(stat=f"p{k}"):
                self.assertEqual(float(seen[f"p{k}"]), nearest_rank(frames, k))

    def test_frame_stats_rounds_ranks_up_when_n_is_not_a_multiple_of_100(self):
        rng = random.Random(FRAME_STATS_SEED)
        frames = [(i + 1) / 100 for i in range(FRAME_STATS_UNEVEN_ROWS)]  # distinct, so each rank has its own value
        rng.shuffle(frames)
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "uneven.csv"
            csv.write_text("frame_ms\n" + "".join(f"{v}\n" for v in frames), encoding="utf-8")
            result = run_frame_stats(str(csv), "frame_ms")
        self.assertEqual(result.returncode, 0, result.stderr)
        seen = dict(line.split("\t", 1) for line in result.stdout.splitlines() if "\t" in line)
        self.assertEqual(int(seen.get("n", -1)), FRAME_STATS_UNEVEN_ROWS)
        for k in PERCENTILES:
            with self.subTest(stat=f"p{k}"):
                self.assertEqual(float(seen[f"p{k}"]), nearest_rank(frames, k))

    def test_frame_stats_refuses_bad_input_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "capture.csv"
            csv.write_text("frame,frame_ms\n0,1.5\n1,abc\n", encoding="utf-8")
            good = Path(tmp) / "good.csv"
            good.write_text("frame_ms\n10\n20\n30\n", encoding="utf-8")
            cases = (((str(csv), "frame_ms"), "not a number"), ((str(csv), "nope"), "no column"),
                     ((str(good), "frame_ms", "-5"), "budget"), ((str(good), "frame_ms", "0"), "budget"))
            for args, cause in cases:
                with self.subTest(args=args[1:]):
                    result = run_frame_stats(*args)
                    self.assertEqual(result.returncode, BAD_USAGE_EXIT, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(cause, result.stderr)

    def test_benchmark_report_computes_statistics_with_the_helper(self):
        self.assertIn("bash .claude/scripts/frame-stats.sh", text_of(BENCH_STATS))
        self.assertNotIn("sort -g", skill_folder_text("benchmark-report"))

    # R37 ------------------------------------------------------------------
    def test_api_review_public_glob_covers_every_engine_module_row(self):
        cpp = between(text_of(API_SURFACE), "**C++.**", "**Rust.**")
        glob = re.search(r"\(Glob `([^`]+)`", cpp)
        self.assertTrue(glob, "surface.md 2a quotes no C++ Glob")
        modules = sorted({p for row in layout_rows() for p in row["paths"]
                          if p.startswith("engine/") and p.endswith("/") and "*" not in p})
        self.assertIn("engine/renderer/features/", modules)
        for module in modules:
            with self.subTest(module=module):
                self.assertTrue(PurePosixPath(f"{module}include/x/a.h").full_match(glob[1]))
        for path in (API_REPORT, RELEASE_INVENTORY):
            with self.subTest(file=path):
                self.assertNotIn("engine/*/include/", text_of(path))
        for path in PUBLIC_HEADER_MENTIONS:
            with self.subTest(file=path):
                self.assertNotIn("engine/*/include", text_of(path))

    # R102 -----------------------------------------------------------------
    def test_rust_breaking_source_names_dyn_compatibility_and_type_parameters(self):
        surface = text_of(API_SURFACE)
        rust_breaking = table_row(surface, "`breaking-source`")[2]
        self.assertIn("dyn", rust_breaking)
        self.assertIn("type parameter without a default", rust_breaking)
        # Rust Reference, items/traits.md, Dyn compatibility.
        for item in ("Dyn compatibility", "no `self` receiver", "associated type with generic parameters",
                     "a receiver other than"):
            with self.subTest(item=item):
                self.assertIn(item, rust_breaking)
        rust_additive = table_row(surface, "`additive`")[2]
        self.assertRegex(rust_additive, r"defaulted trait method[^;|]*dyn")

    # R39, R112 ------------------------------------------------------------
    def test_api_review_pins_its_range_and_release_matches_by_hash(self):
        header = between(text_of(API_REPORT), "# API Review — [short name]", "## Verdict")
        for field in ("Base:", "Head:", "Reviewed commits:"):
            with self.subTest(field=field):
                self.assertIn(field, header)
        self.assertIn("full hash", header)
        phase1 = between(text_of(API_SKILL), "## Phase 1", "## Phase 2")
        self.assertIn("git rev-parse", phase1)
        self.assertIn("git log --format=%H", phase1)
        inventory = between(text_of(RELEASE_INVENTORY), "### 2b.", "### 2c.")
        self.assertNotIn("git log --format=%H <report range>", inventory)
        self.assertIn("NOT ASSESSED — report range not pinned", inventory)

    # R45 ------------------------------------------------------------------
    def test_every_api_review_not_assessed_state_reaches_rule_three(self):
        rule3 = " ".join(between(text_of(API_REPORT), "3. **NOT ASSESSED**", "4. **APPROVED**").split())
        self.assertTrue(rule3)
        reasons = {m.strip() for m in NOT_ASSESSED_REASON.findall(body_of(API_SKILL))}
        reasons = [r for r in reasons if not r.startswith("<") and not r.startswith(API_STOPS)]
        self.assertTrue(reasons)
        for reason in sorted(reasons):
            with self.subTest(reason=reason):
                self.assertIn(" ".join(reason.split()[:2]), rule3)
        self.assertIn("a reviewer returned NOT ASSESSED", rule3)

    # R47 ------------------------------------------------------------------
    def test_removal_window_counts_the_release_kind_the_adr_names(self):
        step = between(text_of(API_SURFACE), "3. **Removal window**", "4. **ADR**")
        self.assertTrue(step)
        self.assertIn("distinct minor versions", step)
        self.assertIn("patch", step)
        self.assertIn("NOT ASSESSED — window unit not stated", step)

    # R38 ------------------------------------------------------------------
    def test_engine_release_reads_custom_nonzero_as_fail(self):
        rows = [line for line in text_of(RELEASE_SKILL).splitlines()
                if line.startswith("|") and "custom:nonzero" in line]
        self.assertEqual(len(rows), 1)
        self.assertIn("| FAIL", rows[0])

    # R48 ------------------------------------------------------------------
    def test_frame_pipeline_ranks_needs_work_before_blocked(self):
        output = between(text_of(PIPELINE_SKILL), "## Output", "## Next Steps")
        words = re.findall(r"^- \*\*([A-Z ]+)\*\*", output, re.M)
        self.assertIn("NEEDS WORK", words)
        self.assertIn("BLOCKED", words)
        self.assertLess(words.index("NEEDS WORK"), words.index("BLOCKED"))

    # R42, R115 ------------------------------------------------------------
    def test_frame_pipeline_passes_a_threshold_with_its_baseline(self):
        calls = re.findall(r"`/?benchmark-report [^`]*`", text_of(PIPELINE_PHASES))
        self.assertTrue(calls)
        for call in calls:
            with self.subTest(call=call):
                self.assertIn("--threshold", call)
        hint = re.search(r'^argument-hint: "(.*)"$', frontmatter(text_of(PIPELINE_SKILL)), re.M)
        self.assertIn("--threshold", hint[1])

    # R41, R116 ------------------------------------------------------------
    def test_benchmark_report_never_overwrites_a_same_day_report(self):
        phase5 = between(text_of(BENCH_SKILL), "## Phase 5", "## Phase 6")
        self.assertIn("benchmark-[date]-[HHMM]-[scene-slug].md", phase5)
        self.assertRegex(phase5, r"(?i)never overwrites?")
        self.assertNotIn("benchmark-[date].md", skill_folder_text("benchmark-report"))

    # R44, R110 ------------------------------------------------------------
    def test_perf_evidence_names_story_and_module(self):
        for path in (BENCH_REPORT, PIPELINE_PHASES):
            for field in STORY_FIELDS:
                with self.subTest(file=path, field=field):
                    self.assertIn(field, text_of(path))
        for path in (BENCH_SKILL, PIPELINE_SKILL):
            hint = re.search(r'^argument-hint: "(.*)"$', frontmatter(text_of(path)), re.M)
            with self.subTest(file=path):
                self.assertIn("--story", hint[1])
        perf = between(text_of(STORY_DONE), "**Custom, perf evidence", "A missing item")
        for field in STORY_FIELDS:
            with self.subTest(file=STORY_DONE, field=field):
                self.assertIn(f"`{field}", perf)
        writers = {clause.split("`")[0]: clause
                   for clause in re.findall(r"`/([\w-]+` writes[^.;)]*)", " ".join(perf.split()))}
        for path in (BENCH_SKILL, PIPELINE_SKILL):
            skill = PurePosixPath(path).parent.name
            hint = re.search(r'^argument-hint: "(.*)"$', frontmatter(text_of(path)), re.M)[1]
            with self.subTest(file=STORY_DONE, writer=skill):
                self.assertIn(skill, writers, "story-done does not say how this skill writes the lines")
                for flag in re.findall(r"`(--[\w-]+)`", writers.get(skill, "")):
                    self.assertIn(flag, hint, "the skill takes no such argument")
        self.assertIn("Frame pipeline: yes", text_of(DEV_STORY))

    # R52 ------------------------------------------------------------------
    def test_default_capture_search_covers_every_bench_root(self):
        no_path = between(text_of(BENCH_SKILL), "**No path given:**", "For each path")
        roots = [p for row in layout_rows() for p in row["paths"] if "benches/" in p]
        self.assertTrue(roots, "the layout names no benches root: the test is out of date")
        for root in roots:
            with self.subTest(root=root):
                self.assertIn(f"`{root}**`", no_path)
        self.assertIn("target/criterion/**/new/estimates.json", no_path)

    # R43 ------------------------------------------------------------------
    def test_memory_growth_is_not_sent_back_to_benchmark_report(self):
        bullet = [line for line in text_of(MEMORY_SKILL).splitlines() if "grows across" in line]
        self.assertTrue(bullet)
        for line in bullet:
            self.assertNotIn("/benchmark-report", line)

    # R106 -----------------------------------------------------------------
    def test_tsan_row_quotes_the_runtime_kind(self):
        row = table_row(text_of(MEMORY_EVIDENCE), "**TSan**")
        self.assertTrue(row)
        self.assertIn("lock-order-inversion (potential deadlock)", row[1])

    # R51 ------------------------------------------------------------------
    def test_suspects_resolve_crate_roots(self):
        suspects = between(text_of(TRIAGE_BISECT), "**Suspects.**", "### 4.")
        self.assertIn("crates/", suspects)
        self.assertIn("Resolving source roots", suspects)

    # R49 (D2) -------------------------------------------------------------
    def test_perf_triage_states_its_own_rules(self):
        text = " ".join(skill_folder_text("perf-regression-triage").split())
        self.assertRegex(text, r"NOT REPRODUCED[^.]*kept open as unconfirmed")
        self.assertRegex(text, r"regression SLA NOT SET[^.]*never assume")
        self.assertIn("same machine, preset and GPU/driver", text)
        for unit in statements(skill_folder_text("perf-regression-triage")):
            if re.search(r"performance-analyst`?(?:'s rule|'s triage flow|\.md`, Perf-regression triage)", unit):
                with self.subTest(statement=unit[:90]):
                    self.assertIn("Custom", unit, "cites the Custom-only agent section as the rule's source")

    # R9 (D2) --------------------------------------------------------------
    def test_every_new_skill_is_gated_or_user_invoked_only(self):
        for skill in NEW_SKILLS:
            text = text_of(f".claude/skills/{skill}/SKILL.md")
            with self.subTest(skill=skill):
                self.assertTrue(NO_MODEL_INVOCATION.search(frontmatter(text)) or ENGINE_GATE in text)

    def test_new_skill_specs_match_their_skill(self):
        # Integration (D2/R43 follow-up): a new skill's spec asserts the
        # frontmatter flag its skill carries, and its handoff names only skills
        # that the skill's Next Steps section hands to.
        for skill in NEW_SKILLS:
            specs = sorted((ROOT / SKILL_SPEC_DIR).glob(f"*/{skill}.md"))
            with self.subTest(skill=skill):
                self.assertEqual(len(specs), 1, f"{skill} has no single spec under {SKILL_SPEC_DIR}")
                spec = specs[0].read_text(encoding="utf-8").replace("\r", "")
                folder = skill_folder_text(skill)
                if NO_MODEL_INVOCATION.search(frontmatter(text_of(f".claude/skills/{skill}/SKILL.md"))):
                    fields = [line for line in spec.splitlines() if SPEC_FRONTMATTER_LINE in line]
                    self.assertTrue(fields and NO_MODEL_INVOCATION_TOKEN in fields[0])
                handoff = [line for line in spec.splitlines() if SPEC_HANDOFF_LINE in line.lower()]
                next_steps = "".join(NEXT_STEPS_SECTION.findall(folder))
                self.assertTrue(next_steps, f"{skill} has no Next Steps section")
                for named in re.findall(r"`/([\w-]+)`", "".join(handoff)):
                    self.assertIn(f"/{named}", next_steps, f"spec hands off to /{named}")

    def test_no_skill_runs_a_user_invoked_only_skill_with_the_skill_tool(self):
        user_only = {s for s in all_skills()
                     if NO_MODEL_INVOCATION.search(frontmatter(text_of(f".claude/skills/{s}/SKILL.md")))}
        for skill in all_skills():
            for unit in statements(skill_folder_text(skill)):
                for hit in SKILL_TOOL_RUN.finditer(unit):
                    target = hit[1] or hit[2]
                    clause = unit[unit.rfind(".", 0, hit.start()) + 1:hit.end()]
                    if target in user_only and not re.search(r"\b(?:not|cannot|never)\b", clause):
                        with self.subTest(skill=skill, target=target):
                            self.fail("disable-model-invocation: true keeps the Skill tool from running it")

    # R61 ------------------------------------------------------------------
    def test_custom_routing_names_the_cea_lead_case(self):
        dev = between(text_of(DEV_STORY), "**Custom engine routing takes precedence", "**Config/Data stories")
        polish = between(text_of(TEAM_POLISH), "**Custom engine override.**", USAGE_LINE)
        for path, paragraph in ((DEV_STORY, dev), (TEAM_POLISH, polish)):
            with self.subTest(file=path):
                self.assertTrue(paragraph)
                self.assertRegex(paragraph, CEA_LEAD_CASE)

    def test_custom_routing_gives_lead_none_rows_their_own_route(self):
        none_rows = [row for row in layout_rows() if LEAD_NONE.match(row.get("Lead", ""))]
        self.assertTrue(none_rows, "the layout has no Lead-none row: the test is out of date")
        dev = between(text_of(DEV_STORY), "**Custom engine routing takes precedence", "**Config/Data stories")
        polish = between(text_of(TEAM_POLISH), "**Custom engine override.**", USAGE_LINE)
        for path, paragraph in ((DEV_STORY, dev), (TEAM_POLISH, polish)):
            flat = " ".join(paragraph.split())
            for sentence in re.split(r"(?<=\.)\s", flat):
                if "directly" in sentence:
                    with self.subTest(file=path, sentence=sentence[:60]):
                        self.assertNotIn("`none`", sentence, "a Lead-none Owner is not a lead")
            for row in none_rows:
                with self.subTest(file=path, row=row["paths"][0]):
                    self.assertIn(f"`{row['paths'][0]}`", flat)
            with self.subTest(file=path, check="security-engineer"):
                self.assertRegex(flat, REVIEWER_ONLY)

    # R12 ------------------------------------------------------------------
    def test_team_polish_reads_nothing_before_its_usage_exit(self):
        text = body_of(TEAM_POLISH)
        self.assertIn(USAGE_LINE, text)
        for line in text[:text.find(USAGE_LINE)].splitlines():
            with self.subTest(line=line[:60]):
                self.assertNotRegex(line, READ_INSTRUCTION)
        keys = re.search(r"resolve_config --keys ([\w.,]+)", text)
        self.assertIn("engine", keys[1].split(","))

    # R125 -----------------------------------------------------------------
    def test_gate_check_reads_budgets_with_their_fallback(self):
        keys = re.search(r"resolve_config --keys ([\w.,]+)", text_of(GATE_CHECK))
        self.assertNotIn("perf_budgets", keys[1].split(","))
        self.assertIn("engine", keys[1].split(","))
        self.assertIn("(else technical-preferences.md)", text_of(GATE_RUN))

    # R117 -----------------------------------------------------------------
    def test_setup_upgrade_stops_on_custom(self):
        upgrade = text_of(SETUP_UPGRADE)
        self.assertIn("Custom", upgrade)
        self.assertIn("/engine-release", upgrade)
        line = next(x for x in text_of(SETUP_SKILL).splitlines() if x.startswith("- **Upgrade**"))
        self.assertIn("Custom", line)

    # R135 (cross-lane, engine-agents-render-platform) ---------------------
    def test_frame_pipeline_gives_the_build_agent_no_zones(self):
        for unit in statements(skill_folder_text("team-frame-pipeline")):
            if BUILD_AGENT_NAME in unit:
                with self.subTest(statement=unit[:90]):
                    self.assertNotRegex(unit, ZONE_ROUTE)
                    self.assertNotIn("instrumentation and benchmark", unit)

    # T5 -------------------------------------------------------------------
    def test_skill_folders_allow_the_helper_commands_they_name(self):
        # Like test_engine_support's scan (SKILL.md only, commands naming
        # custom), over SKILL.md and every references/*.md against the parent
        # SKILL.md's grants; a new skill's commands are scanned whatever they
        # name. A command wrapped over a line break is read as one line, and a
        # command on its own line in a fenced block is read too.
        seen = 0
        for skill in all_skills():
            patterns = bash_patterns(skill)
            text = skill_folder_text(skill)
            commands = re.findall(r"`(bash \.claude/scripts/[\w.-]+\.sh[^`]*)`", text) + fenced_helper_commands(text)
            for command in sorted({" ".join(c.split()) for c in commands}):
                if "custom" not in command and skill not in NEW_SKILLS:
                    continue
                seen += 1
                with self.subTest(skill=skill, command=command):
                    self.assertTrue(any(grant_matches(p, command) for p in patterns),
                                    "no allowed-tools pattern lets the skill run this command")
        self.assertTrue(seen, "no skill names a helper command: the scan is out of date")


if __name__ == "__main__":
    unittest.main()
