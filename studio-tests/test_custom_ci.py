"""Execute generated Custom CI against deterministic test-runner fixtures.

Run: python -m unittest discover -s studio-tests -p test_custom_ci.py -v
These fixtures test the CI/result contract, not a game engine or Claude session.
"""

import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")
CTEST_PASS = "100% tests passed, 0 tests failed out of 3"
CARGO_ZERO = "test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out"
# run_ci's command for a project.yaml with no commands.test.
NO_TEST_COMMAND = ""
# A commands.build value the generated Build step must carry.
BUILD_SENTINEL = "cmake --build build-ci-sentinel"
# What the generated gate prints when the runner is read by exit code only.
RUNNER_NOT_RECOGNISED = "runner not recognised"


def write_project(project, command, scripts, build="true"):
    """A Custom project in `project`: test-run.sh and its awk helper, a
    project.yaml with commands.build and commands.test (None leaves the test
    command out), and one fake runner script per entry of `scripts`
    (name -> (output, exit code)). The output is written as given, so a
    runner's CRLF lines stay CRLF."""
    scripts_dir = project / ".claude/scripts"
    scripts_dir.mkdir(parents=True)
    for name in ("test-run.sh", "yaml-get.awk"):
        shutil.copyfile(ROOT / ".claude/scripts" / name, scripts_dir / name)
    config = f'engine:\n  name: "Custom"\ncommands:\n  build: "{build}"\n'
    if command is not None:
        config += f'  test: "{command}"\n'
    (project / "project.yaml").write_text(config, encoding="utf-8")
    for name, (output, exit_code) in scripts.items():
        # The output goes in a file of its own: Git for Windows' bash drops
        # the CR of a CRLF line in a script's here-document, so output kept
        # inline would reach test-run.sh as LF (Phase 4 critic F4).
        (project / f"{name}.out").write_bytes((output + "\n").encode("utf-8"))
        (project / name).write_bytes(
            (f'#!/usr/bin/env bash\ncat "$(dirname "$0")/{name}.out"\nexit {exit_code}\n').encode("utf-8"))


class CustomCiTests(unittest.TestCase):
    def run_ci(self, runner, output, exit_code=0, *, command=None, scripts=None):
        """Generate the Custom CI and run its "Run Tests" step. By default one
        fake runner (`ctest` or `cargo`) prints `output`; `command` and
        `scripts` (name -> (output, exit code)) replace that."""
        self.assertIsNotNone(BASH, "Bash is required for the repository's scripts")
        with tempfile.TemporaryDirectory(prefix=".custom-ci-") as temp:
            project = Path(temp)
            if command is None:
                command = "bash cargo test" if runner == "cargo" else "bash ctest"
            if scripts is None:
                scripts = {runner: (output, exit_code)}
            write_project(project, command or None, scripts)
            workflow = self.generate(project)
            test_step = workflow.split("      - name: Run Tests\n", 1)[1]
            script = textwrap.dedent(test_step.split("        run: |\n", 1)[1])
            env = dict(os.environ, RUNNER_TEMP=project.as_posix())
            result = subprocess.run(
                [BASH, "-c", script], cwd=project, env=env,
                capture_output=True, text=True, timeout=30,
            )
            return result.returncode, result.stdout + result.stderr

    def generate(self, project):
        """Run test-scaffold.sh custom on `project`; the generated workflow."""
        generated = subprocess.run(
            [BASH, str(ROOT / ".claude/scripts/test-scaffold.sh"),
             "custom", "--root", str(project)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
        return (project / ".github/workflows/tests.yml").read_text(encoding="utf-8")

    def test_ctest_nonempty_pass(self):
        code, output = self.run_ci("ctest", CTEST_PASS)
        self.assertEqual(code, 0, output)
        self.assertIn("custom:ctest-pass", output)

    def test_ctest_zero_fails_ci(self):
        code, output = self.run_ci("ctest", "No tests were found!!!")
        self.assertNotEqual(code, 0, output)
        self.assertIn("custom:ctest-zero", output)

    def test_ctest_failure_fails_ci(self):
        code, output = self.run_ci("ctest", "50% tests passed, 1 tests failed out of 2", 8)
        self.assertNotEqual(code, 0, output)
        self.assertIn("custom:ctest-failed", output)

    def test_cargo_nonempty_pass(self):
        code, output = self.run_ci("cargo", "test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out")
        self.assertEqual(code, 0, output)
        self.assertIn("custom:cargo-pass", output)

    def test_cargo_zero_fails_ci(self):
        code, output = self.run_ci("cargo", CARGO_ZERO)
        self.assertNotEqual(code, 0, output)
        self.assertIn("custom:cargo-zero", output)

    def test_unknown_count_fails_ci(self):
        code, output = self.run_ci("ctest", "runner exited without a summary")
        self.assertNotEqual(code, 0, output)
        self.assertIn("custom:0", output)

    # ---------------------------------------------------------------- Phase 4

    def test_mixed_runners_need_both_to_pass(self):
        # Fix 4.5 (B11): ctest passes and cargo runs zero tests; the rule is the
        # worse of the two, so CI fails on cargo's zero.
        code, output = self.run_ci(None, None, command="bash ctest && bash cargo test", scripts={
            "ctest": (CTEST_PASS, 0), "cargo": (CARGO_ZERO, 0)})
        self.assertNotEqual(code, 0, output)
        self.assertIn("rule\tcustom:cargo-zero\t", output)

    def test_mixed_runners_pass_when_both_pass(self):
        code, output = self.run_ci(None, None, command="bash ctest && bash cargo test", scripts={
            "ctest": (CTEST_PASS, 0),
            "cargo": ("test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out", 0)})
        self.assertEqual(code, 0, output)
        self.assertIn("reading\tctest", output)
        self.assertIn("reading\tcargo", output)

    # Fix 4.6 (E2): the rest of the rule ladder, through the generated CI.
    def assert_ci_fails_with(self, rule, *args, **kwargs):
        code, output = self.run_ci(*args, **kwargs)
        self.assertNotEqual(code, 0, output)
        self.assertIn(f"rule\t{rule}\t", output)
        return output

    def test_cargo_failure_fails_ci(self):
        self.assert_ci_fails_with(
            "custom:cargo-failed", "cargo",
            "test tick ... FAILED\ntest result: FAILED. 1 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out", 101)

    def test_cargo_compile_failure_fails_ci(self):
        self.assert_ci_fails_with(
            "custom:cargo-compile-failed", "cargo",
            "error[E0425]: cannot find value `x` in this scope\nerror: could not compile `core` due to 1 previous error", 101)

    def test_no_test_command_fails_ci(self):
        # No commands.test and no Cargo.toml: test-run.sh has no command.
        self.assert_ci_fails_with("custom:no-test-command", None, None, command=NO_TEST_COMMAND, scripts={})

    def test_runner_that_does_not_start_fails_ci(self):
        # `bash ctest` with no ctest file: bash exits 127.
        self.assert_ci_fails_with("runner-unavailable", None, None, command="bash ctest", scripts={})

    def test_one_failed_cargo_binary_among_ok_ones_fails_ci(self):
        output = "\n".join([
            "     Running unittests src/lib.rs",
            "test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out",
            "     Running tests/replay.rs",
            "test replay_matches ... FAILED",
            "test result: FAILED. 2 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out",
            "   Doc-tests core",
            "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out"])
        self.assert_ci_fails_with("custom:cargo-failed", "cargo", output, 101)

    def test_crlf_runner_output_is_read(self):
        # CTest and cargo on Windows end their lines with CR.
        self.assert_ci_fails_with(
            "custom:ctest-failed", "ctest",
            "Test project C:/x/build\r\n50% tests passed, 1 tests failed out of 2\r\n", 8)
        self.assert_ci_fails_with("custom:cargo-zero", "cargo", CARGO_ZERO + "\r\n")
        # Phase 4 critic F4: the failing tests' names are read by a pattern
        # anchored at line end (test-run.sh, list_failed '... FAILED$'). Git
        # for Windows' grep matches `$` before a CR; POSIX grep does not, so
        # on Linux and macOS only the CR strip keeps these rows.
        output = self.assert_ci_fails_with(
            "custom:cargo-failed", "cargo",
            "test tests::adds ... ok\r\ntest tests::wraps ... FAILED\r\n\r\n"
            "test result: FAILED. 1 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out\r\n", 101)
        self.assertIn("failed\ttest tests::wraps ... FAILED\n", output)

    def test_unrecognised_runner_fails_ci_and_says_why(self):
        # Fix 4.7 (B10): a runner read by exit code only cannot show that tests
        # ran; the gate still fails, and says that the runner is why.
        code, output = self.run_ci(None, None, command="bash runtests", scripts={
            "runtests": ("all good", 0)})
        self.assertNotEqual(code, 0, output)
        self.assertIn("rule\tcustom:0\t", output)
        self.assertIn(RUNNER_NOT_RECOGNISED, output)

    def test_build_failure_runs_no_test(self):
        # Outside run_ci: the generated job builds in its own step, and its test
        # step passes --no-build. So test-run.sh is run directly, with the
        # build it runs first (test-run.sh, custom build step).
        with tempfile.TemporaryDirectory(prefix="custom-build-") as temp:
            project = Path(temp)
            write_project(project, "bash ctest", {"ctest": (CTEST_PASS, 0)}, build="false")
            result = subprocess.run(
                [BASH, ".claude/scripts/test-run.sh", "custom"], cwd=project,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("rule\tcustom:build-failed\t", result.stdout)
            self.assertNotIn("custom:ctest-pass", result.stdout)

    def test_generated_workflow_builds_before_tests(self):
        with tempfile.TemporaryDirectory(prefix="custom-build-") as temp:
            project = Path(temp)
            write_project(project, "bash ctest", {}, build=BUILD_SENTINEL)
            workflow = self.generate(project)
            build = workflow.find("      - name: Build\n")
            tests = workflow.find("      - name: Run Tests\n")
            self.assertNotEqual(build, -1, "no Build step")
            self.assertLess(build, tests, "the Build step does not come before Run Tests")
            self.assertIn(BUILD_SENTINEL, workflow[build:tests])


STORY_FACTS = ROOT / ".claude/scripts/story-facts.sh"
# story-facts.sh's list of story types (`ntypes = split("Logic ...", tnames, " ")`).
STORY_TYPES_LIST = re.compile(r'ntypes = split\("([^"]+)", tnames, " "\)')
README_TYPE_TABLE = "## Story Type → Test Evidence"
TABLE_ROW = re.compile(r"^\| (?!Story Type |---)([^|]+?) \|", re.M)
NEEDS_ENGINE_VERSION = "NEEDS\tengine_version\t"
CUSTOM_NO_VERSION = "**Engine**: Custom (version NOT DETERMINED)"


def story_types():
    found = STORY_TYPES_LIST.search(STORY_FACTS.read_text(encoding="utf-8"))
    return set(found[1].split()) if found else set()


class CustomScaffoldTests(unittest.TestCase):
    def scaffold(self, project, *args):
        result = subprocess.run(
            [BASH, str(ROOT / ".claude/scripts/test-scaffold.sh"), "custom", "--root", str(project), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_no_engine_version_need_without_a_version(self):
        # R119: custom.md leaves engine.version out when none was read and
        # says never to invent one; the scaffold must not ask for it.
        with tempfile.TemporaryDirectory(prefix="custom-scaffold-") as temp:
            project = Path(temp)
            write_project(project, "bash ctest", {})
            self.assertNotIn(NEEDS_ENGINE_VERSION, self.scaffold(project, "--dry-run"))
            self.assertNotIn(NEEDS_ENGINE_VERSION, self.scaffold(project))
            readme = (project / "tests/README.md").read_text(encoding="utf-8")
            self.assertIn(CUSTOM_NO_VERSION, readme)
            self.assertNotIn("[version]", readme)

    def test_readme_story_types_are_the_canonical_ones(self):
        # R120: every Story Type cell is a type story-facts.sh knows.
        known = story_types()
        self.assertTrue(known, f"no story type list found in {STORY_FACTS}")
        with tempfile.TemporaryDirectory(prefix="custom-scaffold-") as temp:
            project = Path(temp)
            write_project(project, "bash ctest", {})
            self.scaffold(project)
            readme = (project / "tests/README.md").read_text(encoding="utf-8")
        table = readme.split(README_TYPE_TABLE, 1)[1].split("\n## ", 1)[0]
        cells = TABLE_ROW.findall(table)
        self.assertEqual(sorted(cells), sorted(known))


if __name__ == "__main__":
    unittest.main()
