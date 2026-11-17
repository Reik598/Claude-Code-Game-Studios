"""Non-Custom equivalence: hooks and scripts against the base release.

Run: python -m unittest discover -s studio-tests -p test_engine_scope.py -v

Each test builds two fixture projects in the OS temp directory with identical
project files (fix plan, section 7, "Spanning test"). The base fixture holds the
base release's whole `.claude/` tree (`git archive BASE_RELEASE .claude`) and
the work fixture a copy of this worktree's, so every script runs with its own
helpers, engine table and catalog. Outputs must be equal after fixture paths are
normalised and the allowlisted lines below are removed (R2).
These test the scripts' observations, not a Claude session.
"""

import io
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import BASE_RELEASE, custom_scoped_catalog_steps, read  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")
SIDES = ("base", "work")
# The environment the scripts run in: without the session's project pointer, so
# a hook resolves its project from its working directory, the fixture.
SCRIPT_ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
SCRIPT_TIMEOUT_S = 180
# Above this many source files, with fewer than five design docs, detect-gaps.sh
# reports a "Substantial codebase" gap (detect-gaps.sh, Check 1).
DETECT_GAPS_SUBSTANTIAL = 50
# A count above detect-gaps.sh's "Large codebase" threshold (Check 5, 100), and
# the stories a stage-gap fixture holds (Check 6).
DETECT_GAPS_LARGE = 120
STORIES = 3
# Folders a Custom project's root `.` code root never scans (build output).
CUSTOM_BUILD_OUTPUT = ("build", "target", "out")

_base_archive = None


def base_claude_archive():
    """The base release's `.claude/` as a tar stream, or None without the commit."""
    global _base_archive
    if _base_archive is None:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "archive", "--format=tar", BASE_RELEASE, ".claude"],
            capture_output=True)
        _base_archive = result.stdout if result.returncode == 0 else b""
    return _base_archive or None


def project_yaml(engine=None, code_root=None, workflow=None):
    lines = []
    if engine or code_root:
        lines.append("engine:")
        if engine:
            lines.append(f'  name: "{engine}"')
        if code_root:
            lines.append(f'  code_root: "{code_root}"')
    if workflow:
        lines += ["modes:", f"  workflow: {workflow}"]
    return "\n".join(lines) + "\n"


def many(folder, count, ext):
    return {f"{folder}/gen{i}.{ext}": f"// generated {i}\n" for i in range(count)}


class TwoFixtures:
    """A base and a work fixture project with the same project files."""

    def __init__(self, test, files):
        self.test, self.files = test, files

    def __enter__(self):
        archive = base_claude_archive()
        if archive is None:
            self.test.skipTest(f"base release {BASE_RELEASE} is not in this clone")
        self._temp = tempfile.TemporaryDirectory(prefix="ccgs-scope-")
        top = Path(self._temp.name).resolve()
        self.roots = {side: top / side for side in SIDES}
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(self.roots["base"], filter="data")
        shutil.copytree(ROOT / ".claude", self.roots["work"] / ".claude",
                        ignore=shutil.ignore_patterns("__pycache__"))
        for side in SIDES:
            for rel, text in self.files.items():
                path = self.roots[side] / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8", newline="\n")
        return self

    def __exit__(self, *exc):
        self._temp.cleanup()

    def normalise(self, side, text):
        root = self.roots[side]
        forms = {str(root), root.as_posix()}
        if root.drive:
            # Git Bash on Windows prints C:\x as /c/x.
            forms.add("/" + root.drive[0].lower() + root.as_posix()[len(root.drive):])
        for form in sorted(forms, key=len, reverse=True):
            text = re.sub(re.escape(form), "<ROOT>", text, flags=re.I)
        return text.replace("\r", "")

    def run(self, side, *args, env=None):
        """Run `bash ARGS` inside one fixture; (exit code, stdout, stderr)."""
        self.test.assertIsNotNone(BASH, "Bash is required for the repository's scripts")
        result = subprocess.run(
            [BASH, *args], cwd=self.roots[side], env=env or SCRIPT_ENV, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=SCRIPT_TIMEOUT_S)
        out = result.stdout.decode("utf-8", "replace")
        err = result.stderr.decode("utf-8", "replace")
        return result.returncode, self.normalise(side, out), self.normalise(side, err)

    def both(self, *args):
        return {side: self.run(side, *args) for side in SIDES}


# R2 / fix 2.4: the only lines artifact-check.sh may print differently from the
# base release on a non-Custom project. Reason: a step skipped for "wrong
# engine" must be named in the output (.claude/rules/skill-authoring.md:47-52),
# so the engine line, the skipped count and the skipped Custom rows stay.
# Exactly: (1) the ENGINE: header; (2) the ENGINE_SKIPPED: count; (3) the STEPS:
# line, whose difference is asserted separately; (4) on the work side only, the
# rows of the catalog steps that carry `engine: Custom` (derived from the
# worktree catalog), each of which must read status=ENGINE_SKIPPED.
ARTIFACT_CHECK_ALLOWED_HEADERS = ("ENGINE: ", "ENGINE_SKIPPED: ", "STEPS: ")
STEP_ROW = re.compile(r"^  STEP: ([\w-]+) ")


def artifact_check_residue(lines, custom_steps, side):
    """Lines left after the allowlisted ones are removed."""
    kept = []
    for line in lines:
        if line.startswith(ARTIFACT_CHECK_ALLOWED_HEADERS):
            continue
        step = STEP_ROW.match(line)
        if side == "work" and step and step[1] in custom_steps:
            continue
        kept.append(line)
    return kept


def header_count(lines, name):
    values = [int(m[1]) for line in lines for m in [re.match(rf"^{name}: (\d+)$", line)] if m]
    return values[0] if len(values) == 1 else None


NON_CUSTOM_ENGINES = ("Godot", "Unity", "Unreal", "Web")
# test-run.sh's Unreal build script on Linux, under the engine root (--exe).
UNREAL_LINUX_BUILD = "Engine/Build/BatchFiles/Linux/Build.sh"
# The test-run.sh --timeout the stub build outlives, and how long it sleeps.
TEST_RUN_TIMEOUT_S = 1
UNREAL_STUB_BUILD_S = 30


class NonCustomEquivalence(unittest.TestCase):
    def web_root_dot(self):
        # A flat web game: code root `.`, sources under build/, out/, engine/
        # and game/ as well as src/ (fix plan, section 7).
        files = {"project.yaml": project_yaml("Web", ".", "standard"),
                 "src/main.ts": "export const main = 1;\n",
                 "out/app.ts": "export const app = 1;\n",
                 "engine/loop.ts": "export const loop = 1;\n",
                 "game/level.ts": "export const level = 1;\n"}
        files.update(many("build", DETECT_GAPS_SUBSTANTIAL + 1, "ts"))
        return files

    def test_project_state_matches_base_on_non_custom(self):
        with TwoFixtures(self, self.web_root_dot()) as fx:
            out = fx.both(".claude/scripts/project-state.sh", "--root", ".")
            self.assertEqual(out["work"], out["base"])

    def test_code_markers_matches_base_on_non_custom(self):
        with TwoFixtures(self, self.web_root_dot()) as fx:
            out = fx.both(".claude/scripts/code-markers.sh", "--root", ".")
            self.assertEqual(out["work"], out["base"])

    def test_detect_gaps_counts_match_base_with_root_dot(self):
        # modes.workflow standard turns DOC_CHECKS on; src/main.ts keeps the
        # fresh-project exit from being taken; build/ holds more than
        # DETECT_GAPS_SUBSTANTIAL sources; there are no design docs.
        with TwoFixtures(self, self.web_root_dot()) as fx:
            out = fx.both(".claude/hooks/detect-gaps.sh")
            self.assertIn("Substantial codebase", out["base"][1])
            self.assertEqual(out["work"], out["base"])

    def test_detect_gaps_matches_base_on_non_custom(self):
        # A Godot project whose engine is not configured yet (project.godot, no
        # engine.name): detect-gaps.sh decides "fresh project" from its source
        # roots alone, which is the only place A2's extra roots are visible.
        unconfigured = {"project.godot": "config_version=5\n",
                        "project.yaml": project_yaml(workflow="standard"),
                        "game/main.gd": "extends Node\n"}
        configured = dict(unconfigured, **{"project.yaml": project_yaml("Godot", workflow="standard")})
        for name, files in (("engine unset", unconfigured), ("engine Godot", configured)):
            with self.subTest(fixture=name), TwoFixtures(self, files) as fx:
                out = fx.both(".claude/hooks/detect-gaps.sh")
                self.assertEqual(out["work"], out["base"])

    def test_detect_gaps_adr_count_matches_base_on_non_custom(self):
        # R16: only Custom counts docs/architecture/adr-*.md; every other engine
        # counts each .md under docs/architecture/ as at the base release. One
        # ADR plus a module spec and a frame budget: three at base, so Check 3
        # is silent there, and an ADR-only count would print "only 1 ADR(s)".
        # Each engine's code root gets a core/ folder (Web: root `.`, engine/).
        sources = {"src/core/a.ts": "export const a = 1;\n", "Assets/core/a.cs": "class A {}\n",
                   "Source/core/a.cpp": "int a;\n", "engine/core/e.cpp": "int e;\n"}
        adr_only = dict(sources, **{"docs/architecture/adr-0001.md": "# ADR\n"})
        with_specs = dict(adr_only, **{"docs/architecture/modules/a.md": "# Module a\n",
                                       "docs/architecture/frame-budget.md": "# Frame budget\n"})
        for engine in NON_CUSTOM_ENGINES:
            code_root = "." if engine == "Web" else None
            yaml = {"project.yaml": project_yaml(engine, code_root, "standard")}
            with self.subTest(engine=engine):
                with TwoFixtures(self, dict(adr_only, **yaml)) as fx:
                    code, out, err = fx.run("base", ".claude/hooks/detect-gaps.sh")
                    self.assertIn("only 1 ADR(s) documented", out, "Check 3 did not run: the fixture is wrong")
                with TwoFixtures(self, dict(with_specs, **yaml)) as fx:
                    out = fx.both(".claude/hooks/detect-gaps.sh")
                    self.assertNotIn("ADR(s) documented", out["base"][1])
                    self.assertEqual(out["work"], out["base"])

    def test_write_guard_matches_base_on_non_custom(self):
        # Fix plan AM1: write-guard.sh holds a fourth copy of the code-root skip
        # list. A file under build/ that imports from prototypes/ is a
        # PROTOTYPE_IMPORT only if build/ is one of write-guard's code roots.
        files = dict(self.web_root_dot(), **{
            "build/reach.ts": 'import { p } from "../prototypes/demo/p";\n',
            "prototypes/demo/p.ts": "export const p = 1;\n"})
        with TwoFixtures(self, files) as fx:
            out = fx.both(".claude/scripts/write-guard.sh", "prototype", "build/reach.ts")
            self.assertEqual(out["work"], out["base"])

    def test_test_run_unreal_build_timeout_matches_base(self):
        # R13: an Unreal pre-test build that outlives --timeout prints the same
        # rows as at the base release ("the editor build timed out").
        files = {"project.yaml": project_yaml("Unreal"), "Game.uproject": "{}\n"}
        with TwoFixtures(self, files) as fx, tempfile.TemporaryDirectory(prefix="ccgs-ue-") as ue:
            build = Path(ue) / UNREAL_LINUX_BUILD
            build.parent.mkdir(parents=True)
            build.write_text(f"#!/bin/sh\nsleep {UNREAL_STUB_BUILD_S}\n", encoding="utf-8", newline="\n")
            build.chmod(0o755)
            out = fx.both(".claude/scripts/test-run.sh", "unreal", "--exe", Path(ue).as_posix(),
                          "--os", "linux", "--timeout", str(TEST_RUN_TIMEOUT_S), "--tool", "perl",
                          "--log", "run.log")
            self.assertIn("build_timed_out\tyes", out["base"][1], "the stub build did not time out")
            self.assertEqual(out["work"], out["base"])

    def assert_artifact_check_allowlisted(self, fx):
        custom_steps = custom_scoped_catalog_steps(read(".claude/docs/workflow-catalog.yaml"))
        self.assertTrue(custom_steps, "the worktree catalog has no engine: Custom step")
        out = fx.both(".claude/scripts/artifact-check.sh", ".")
        for side in SIDES:
            self.assertEqual(out[side][0], 0, out[side][2])
        lines = {side: out[side][1].splitlines() for side in SIDES}
        steps = {side: header_count(lines[side], "STEPS") for side in SIDES}
        self.assertNotIn(None, steps.values(), "a STEPS: line is missing or repeated")
        self.assertEqual(steps["work"] - steps["base"], len(custom_steps))
        rows = {STEP_ROW.match(line)[1]: line for line in lines["work"] if STEP_ROW.match(line)}
        for step in custom_steps:
            self.assertIn("status=ENGINE_SKIPPED", rows.get(step, ""), step)
        self.assertEqual(artifact_check_residue(lines["work"], custom_steps, "work"),
                         artifact_check_residue(lines["base"], custom_steps, "base"))

    def test_artifact_check_differs_from_base_only_by_allowlisted_lines(self):
        for engine in NON_CUSTOM_ENGINES:
            files = {"project.yaml": project_yaml(engine, workflow="standard")}
            with self.subTest(engine=engine), TwoFixtures(self, files) as fx:
                self.assert_artifact_check_allowlisted(fx)

    def test_scripts_match_base_on_every_non_custom_engine(self):
        # The spanning test of fix plan section 7: one fixture per non-Custom
        # engine, sources in every engine's code root and in the Custom and
        # build-output folders; the Web fixture has code root `.`.
        # T4: content-count.sh and asset-scan.sh read the content and asset
        # roots (assets/, Assets/, Content/, game/), and validate-commit.sh's
        # hardcoded-value scan reads a staged gameplay file in each code root.
        sources = {"src/a.ts": "export const a = 1;\n", "Assets/a.cs": "class A {}\n",
                   "Source/Game/a.cpp": "int a;\n", "engine/core/e.cpp": "int e;\n",
                   "game/src/g.cpp": "int g;\n", "out/o.ts": "export const o = 1;\n",
                   "assets/data/items/i.json": "{}\n", "assets/art/a.png": "png\n",
                   "Assets/Data/Items/i.json": "{}\n", "Assets/Art/a.png": "png\n",
                   "Content/Maps/m.umap": "map\n", "Content/Art/a.uasset": "asset\n",
                   "game/data/items/i.json": "{}\n", "game/levels/l.json": "{}\n",
                   **HARDCODED_GAMEPLAY}
        sources.update(many("build", DETECT_GAPS_SUBSTANTIAL + 1, "ts"))
        for engine in NON_CUSTOM_ENGINES:
            code_root = "." if engine == "Web" else None
            files = dict(sources, **{"project.yaml": project_yaml(engine, code_root, "standard")})
            with self.subTest(engine=engine), TwoFixtures(self, files) as fx:
                for script in ([".claude/scripts/project-state.sh", "--root", "."],
                               [".claude/scripts/code-markers.sh", "--root", "."],
                               [".claude/hooks/detect-gaps.sh"],
                               [".claude/scripts/content-count.sh", "found", "--files"],
                               [".claude/scripts/asset-scan.sh", "--root", ".", "--files"]):
                    with self.subTest(script=script[0]):
                        out = fx.both(*script)
                        self.assertEqual(out["work"], out["base"])
                with self.subTest(script="validate-commit.sh"):
                    out = {side: commit_hook(fx, side, sorted(HARDCODED_GAMEPLAY)) for side in SIDES}
                    self.assertIn(HARDCODED_WARNING, out["base"][1], "the fixture raised no hardcoded-value warning")
                    self.assertEqual(out["work"], out["base"])
                with self.subTest(script="artifact-check.sh"):
                    self.assert_artifact_check_allowlisted(fx)


class FixtureHelper(unittest.TestCase):
    def test_normalise_accepts_a_root_without_a_drive(self):
        # IMPL F2: on macOS and Linux a path has no drive letter.
        fx = TwoFixtures(self, {})
        fx.roots = {"work": PurePosixPath("/tmp/ccgs-scope-x/work")}
        self.assertEqual(fx.normalise("work", "/tmp/ccgs-scope-x/work/a.ts\r\n"), "<ROOT>/a.ts\n")


class CustomStillSkipsBuildOutput(unittest.TestCase):
    """Fix 2.2's guard keeps Custom's skip of build output in all three places."""

    FILES = {"project.yaml": project_yaml("Custom", workflow="standard"),
             "engine/core/a.cpp": "int a;\n", "game/src/b.cpp": "int b;\n",
             **{f"{d}/gen.cpp": "int g;\n" for d in CUSTOM_BUILD_OUTPUT}}
    SOURCES = 2

    def test_yaml_helper_code_root_find_skips_build_output(self):
        with TwoFixtures(self, self.FILES) as fx:
            code, out, err = fx.run(
                "work", "-c", ". .claude/hooks/yaml-helper.sh; code_root_find . -type f -name '*.cpp'")
            self.assertEqual(code, 0, err)
            found = sorted(p.removeprefix("./") for p in out.split())
            self.assertEqual(found, ["engine/core/a.cpp", "game/src/b.cpp"])

    def test_project_state_skips_build_output(self):
        with TwoFixtures(self, self.FILES) as fx:
            code, out, err = fx.run("work", ".claude/scripts/project-state.sh", "--root", ".")
            self.assertEqual(code, 0, err)
            self.assertRegex(out, rf"(?m)^source_files\t{self.SOURCES}\t")

    def test_code_markers_skips_build_output(self):
        with TwoFixtures(self, self.FILES) as fx:
            code, out, err = fx.run("work", ".claude/scripts/code-markers.sh", "--root", ".")
            self.assertEqual(code, 0, err)
            self.assertRegex(out, rf"(?m)^scanned_files\t{self.SOURCES}\b")


# R14 / fix plan AM28 D8: on Custom the root `.` code root also skips vendored
# code (third-party.md) and scans tools/ (tools/editor/ is the editor's code,
# custom-engine-layout.md). Other engines keep the base list.
CUSTOM_VENDORED = ("third_party", "external", "vendor")
MARKED = "// TODO: marked\nint m;\n"


class CustomScopesVendoredAndTools(unittest.TestCase):
    FILES = {"project.yaml": project_yaml("Custom", workflow="standard"),
             "engine/core/src/a.cpp": MARKED, "tools/editor/src/inspector.cpp": MARKED,
             **{f"{d}/lib/x.cpp": MARKED for d in CUSTOM_VENDORED}}
    OWN = ["engine/core/src/a.cpp", "tools/editor/src/inspector.cpp"]

    def test_yaml_helper_code_root_find(self):
        with TwoFixtures(self, self.FILES) as fx:
            code, out, err = fx.run(
                "work", "-c", ". .claude/hooks/yaml-helper.sh; code_root_find . -type f -name '*.cpp'")
            self.assertEqual(code, 0, err)
            self.assertEqual(sorted(p.removeprefix("./") for p in out.split()), self.OWN)

    def test_yaml_helper_code_root_filter(self):
        with TwoFixtures(self, self.FILES) as fx:
            paths = " ".join(sorted(p for p in self.FILES if p.endswith(".cpp")))
            code, out, err = fx.run(
                "work", "-c", f". .claude/hooks/yaml-helper.sh; printf '%s\\n' {paths} | code_root_filter .")
            self.assertEqual(code, 0, err)
            self.assertEqual(sorted(out.split()), self.OWN)

    def test_project_state_counts_own_code_only(self):
        with TwoFixtures(self, self.FILES) as fx:
            code, out, err = fx.run("work", ".claude/scripts/project-state.sh", "--root", ".")
            self.assertEqual(code, 0, err)
            self.assertRegex(out, rf"(?m)^source_files\t{len(self.OWN)}\t")

    def test_code_markers_reports_own_code_only(self):
        with TwoFixtures(self, self.FILES) as fx:
            code, out, err = fx.run("work", ".claude/scripts/code-markers.sh", "--root", ".")
            self.assertEqual(code, 0, err)
            self.assertRegex(out, rf"(?m)^todo\t{len(self.OWN)}$")
            self.assertEqual(sorted(re.findall(r"(?m)^MARK\tTODO\t(\S+)\t", out)), self.OWN)

    def test_non_custom_still_matches_base(self):
        # Control: the same tree on Web with code root `.` prints as at base.
        files = dict(self.FILES, **{"project.yaml": project_yaml("Web", ".", "standard")})
        with TwoFixtures(self, files) as fx:
            for script in ([".claude/scripts/project-state.sh", "--root", "."],
                           [".claude/scripts/code-markers.sh", "--root", "."]):
                with self.subTest(script=script[0]):
                    out = fx.both(*script)
                    self.assertEqual(out["work"], out["base"])

    def test_docs_describe_the_custom_code_root_scope(self):
        # Integration (scripts-hooks-permissions lane request): the prose that
        # describes the Custom code root `.` names the vendored folders it
        # skips and the tools/ folder it scans, as the scripts above do.
        for path, start, needed in (
                (ENGINES_README, CUSTOM_README_PARAGRAPH, CUSTOM_SCANNED_TOOLS),
                (STAGE_DETECT_SKILL, CUSTOM_STAGE_BULLET, CUSTOM_SCANNED_EDITOR)):
            text = read(path)
            self.assertIn(start, text, f"{path}: the Custom passage moved; update this test")
            passage = re.split(r"\n\s*\n|\n- ", text[text.index(start):], maxsplit=1)[0]
            for folder in (*(f"`{d}/`" for d in CUSTOM_VENDORED), needed):
                with self.subTest(file=path, folder=folder):
                    self.assertIn(folder, passage)


ENGINES_README = ".claude/engines/README.md"
CUSTOM_README_PARAGRAPH = "**Custom** is a project that builds its own engine"
CUSTOM_SCANNED_TOOLS = "`tools/`"
STAGE_DETECT_SKILL = ".claude/skills/project-stage-detect/SKILL.md"
CUSTOM_STAGE_BULLET = "- **Custom** (a project that builds its own engine, code root `.`)"
CUSTOM_SCANNED_EDITOR = "`tools/editor/`"


class CustomDetectGapsCounts(unittest.TestCase):
    def test_module_specs_and_budgets_are_not_adrs(self):
        # R16: the docs the Custom workflow keeps beside the ADRs in
        # docs/architecture/ are not ADRs; with none, Check 3 says 0.
        files = {"project.yaml": project_yaml("Custom", workflow="standard"),
                 "engine/core/src/a.cpp": "int a;\n",
                 **{f"docs/architecture/modules/{m}.md": f"# {m}\n" for m in ("core", "memory", "jobs")},
                 "docs/architecture/frame-budget.md": "# Frame budget\n",
                 "docs/architecture/memory-invariants.md": "# Memory invariants\n"}
        with TwoFixtures(self, files) as fx:
            code, out, err = fx.run("work", ".claude/hooks/detect-gaps.sh")
            self.assertEqual(code, 0, err)
            self.assertIn("Core systems exist but only 0 ADR(s) documented", out)

    def test_engine_code_counts_for_planning_and_stage_checks(self):
        # R17: only the design-doc check (Check 1) narrows to game/ on
        # Custom; the planning (5) and stage (6) checks count all the code.
        files = {"project.yaml": project_yaml("Custom", workflow="standard") + "project:\n  stage: Concept\n",
                 **many("engine/core/src", DETECT_GAPS_LARGE, "cpp"),
                 **{f"production/epics/core/story-{i}.md": "# Story\n" for i in range(STORIES)}}
        with TwoFixtures(self, files) as fx:
            code, out, err = fx.run("work", ".claude/hooks/detect-gaps.sh")
            self.assertEqual(code, 0, err)
            self.assertIn(f"Large codebase ({DETECT_GAPS_LARGE} files)", out)
            self.assertIn(f"project.stage says 'Concept', but {STORIES} stories and {DETECT_GAPS_LARGE} source files", out)
            # Check 1 still counts game/ only: none here, so no design-doc gap.
            self.assertNotIn("Substantial codebase", out)


PROTOTYPE_HEADER = "// PROTOTYPE - NOT FOR PRODUCTION\n"


class CustomWriteGuardRoots(unittest.TestCase):
    """R15 / AM28 D8: on Custom, write-guard's code roots are the layout's code
    folders (engine/, game/, crates/, tools/editor/), not every folder on disk."""

    def check_prototype(self, line):
        files = {"project.yaml": project_yaml("Custom", workflow="standard"),
                 "engine/core/x.h": "int x;\n", "assets/textures/rock.png": "png\n",
                 "third_party/x/x.h": "int t;\n", "tools/editor/e.h": "int e;\n",
                 "prototypes/demo/main.cpp": PROTOTYPE_HEADER + line + "\n"}
        with TwoFixtures(self, files) as fx:
            code, out, err = fx.run("work", ".claude/scripts/write-guard.sh", "check", "prototypes/demo/main.cpp")
            self.assertEqual(code, 0, err)
            return [row for row in out.splitlines() if row.startswith("PROTOTYPE_IMPORT\t")]

    def test_shared_assets_and_vendored_code_are_not_code_roots(self):
        for line in ('auto t = load("../../assets/textures/rock.png");', '#include "../../third_party/x/x.h"'):
            with self.subTest(line=line):
                self.assertEqual(self.check_prototype(line), [])

    def test_layout_code_folders_are_code_roots(self):
        # Control: an include that climbs into the engine or the editor tools.
        for line in ('#include "../../engine/core/x.h"', '#include "../../tools/editor/e.h"'):
            with self.subTest(line=line):
                rows = self.check_prototype(line)
                self.assertEqual(len(rows), 1, rows)
                self.assertIn("\tinto-production\t", rows[0])


# The interpreters yaml-helper.sh tries (_yaml_helper_resolve_python).
PYTHON_NAMES = ("python", "python3", "py")


def env_without_python(stub_dir):
    """SCRIPT_ENV with python, python3 and py resolving to stubs that exit 1."""
    for name in PYTHON_NAMES:
        stub = Path(stub_dir) / name
        stub.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8", newline="\n")
        stub.chmod(0o755)
    return dict(SCRIPT_ENV, PATH=str(stub_dir) + os.pathsep + SCRIPT_ENV.get("PATH", ""))


class CustomStillReportsSource(unittest.TestCase):
    def test_detect_gaps_reports_engine_source_on_custom(self):
        # Fix plan AM4 (IMPL F4): with Python resolvable, get_yaml_key already
        # marks a Custom project as not fresh (detect-gaps.sh:46-50). With no
        # Python, only the Custom roots branch (engine/, game/) can.
        files = {"project.yaml": project_yaml("Custom", workflow="standard"),
                 "engine/core/a.cpp": "int a;\n"}
        with TwoFixtures(self, files) as fx, tempfile.TemporaryDirectory(prefix="ccgs-nopy-") as stubs:
            env = env_without_python(stubs)
            code, out, err = fx.run(
                "work", "-c", ". .claude/hooks/yaml-helper.sh; get_yaml_key project.yaml engine.name", env=env)
            self.assertEqual(out.strip(), "", "get_yaml_key still read the engine: Python resolved")
            self.assertIn("no python interpreter", err)
            code, out, err = fx.run("work", ".claude/hooks/detect-gaps.sh", env=env)
            self.assertEqual(code, 0, err)
            self.assertNotIn("NEW PROJECT", out)

    def test_detect_gaps_suggests_engine_path_on_custom(self):
        # Fix 4.4 (B7): Check 3 ("Core systems exist but only N ADR(s)") built
        # its suggestion from the code root, which is `.` on Custom: `./core/`.
        files = {"project.yaml": project_yaml("Custom", workflow="standard"),
                 "engine/core/a.cpp": "int a;\n", "docs/architecture/adr-0001.md": "# ADR\n"}
        with TwoFixtures(self, files) as fx:
            code, out, err = fx.run("work", ".claude/hooks/detect-gaps.sh")
            self.assertEqual(code, 0, err)
            self.assertIn("ADR(s) documented", out, "Check 3 did not fire: the fixture is wrong")
            self.assertNotIn("./core/", out)
            self.assertIn("/reverse-document architecture engine/[module]", out)
        # The same tree on Web with code root `.`: the line is as at base.
        web = dict(files, **{"project.yaml": project_yaml("Web", ".", "standard")})
        with TwoFixtures(self, web) as fx:
            out = fx.both(".claude/hooks/detect-gaps.sh")
            self.assertIn("ADR(s) documented", out["base"][1], "Check 3 did not fire: the fixture is wrong")
            self.assertEqual(out["work"], out["base"])


# Exit codes of the validate-commit.sh PreToolUse hook (its header): 0 allows
# the call, 2 blocks it.
HOOK_ALLOW, HOOK_BLOCK = 0, 2
COMMIT_PAYLOAD = '{"tool_name": "Bash", "tool_input": {"command": "git commit -m data"}}'
# T4: a gameplay value in a file of each non-Custom code root (and game/), and
# the warning validate-commit.sh's hardcoded-value scan gives for it.
HARDCODED_GAMEPLAY = {"src/combat.ts": "export const damage = 10;\n",
                      "Assets/Combat.cs": "class Combat { int damage = 10; }\n",
                      "Source/Game/Combat.cpp": "int damage = 10;\n",
                      "game/src/combat.cpp": "int damage = 10;\n"}
HARDCODED_WARNING = "may contain hardcoded gameplay values"


def commit_hook(fx, side, staged):
    """Stage `staged` in a git repo inside the fixture, run validate-commit.sh;
    (exit code, normalised stdout and stderr). Warnings go out on stdout as
    hook JSON, a block on stderr."""
    root = fx.roots[side]
    for args in (["init", "-q"], ["add", "--", *staged]):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    result = subprocess.run(
        [BASH, ".claude/hooks/validate-commit.sh"], cwd=root, env=SCRIPT_ENV,
        input=COMMIT_PAYLOAD.encode("utf-8"), capture_output=True, timeout=SCRIPT_TIMEOUT_S)
    out = (result.stdout + result.stderr).decode("utf-8", "replace")
    return result.returncode, fx.normalise(side, out)


class CommitDataValidation(unittest.TestCase):
    """Fix 4.1 (B2): on Custom, game data lives in game/data/ (data-files.md)."""

    def commit_hook(self, fx, side):
        """Stage game/data/x.json in a git repo inside the fixture, run the hook."""
        return commit_hook(fx, side, ["game/data/x.json"])

    def test_broken_game_data_json_blocks_on_custom(self):
        broken = "{ not json\n"
        custom = {"project.yaml": project_yaml("Custom"), "game/data/x.json": broken}
        with TwoFixtures(self, custom) as fx:
            code, err = self.commit_hook(fx, "work")
            self.assertEqual(code, HOOK_BLOCK, err)
            self.assertIn("game/data/x.json is not valid JSON", err)
        # Control: on Godot game/data/ is not a data root; as at the base release,
        # the commit is not blocked.
        godot = dict(custom, **{"project.yaml": project_yaml("Godot")})
        with TwoFixtures(self, godot) as fx:
            for side in SIDES:
                with self.subTest(side=side):
                    code, err = self.commit_hook(fx, side)
                    self.assertEqual(code, HOOK_ALLOW, err)


if __name__ == "__main__":
    unittest.main()
