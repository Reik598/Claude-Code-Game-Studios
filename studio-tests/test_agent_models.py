"""Agent models and effort (fix plan AM38, OpenSpec change set-agent-model-and-effort).

`.claude/agent-models.yaml` is the one source of each agent's model and effort.
`.claude/scripts/agent-models.sh` writes them into the agents' frontmatter
(`sync`) and reports any difference (`check`). This module is a second, Python
reader of the same grammar: every rejected form must be rejected by both.

Grammar (design D1): top-level keys `tiers`, `agents` and `overrides` only;
tiers at two spaces with `model`, `effort` and an optional `optional: true` at
four; agents and overrides as `name: tier` at two spaces. The tiers, in file
order, are the escalation ladder and must rise strictly; only the last may be
optional. `session` is allowed only under `overrides:` and means
`model: inherit` with no `effort:` line. Tabs, duplicate keys and flow maps
are rejected; a trailing `# comment` is allowed.
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_engine_scope import BASH, SCRIPT_ENV, SCRIPT_TIMEOUT_S

ROOT = Path(__file__).resolve().parents[1]
TABLE = ".claude/agent-models.yaml"
SCRIPT = ".claude/scripts/agent-models.sh"
AGENTS_DIR = ".claude/agents"
SPECS_DIR = "studio-tests/agents"
GATES_DIR = ".claude/docs/director-gates"
TOP_KEYS = ("tiers", "agents", "overrides")
TIER_FIELDS = ("model", "effort", "optional")
MODEL_RANK = {"haiku": 0, "sonnet": 1, "opus": 2, "fable": 3}
EFFORT_RANK = {"low": 0, "medium": 1, "high": 2, "xhigh": 3, "max": 4}
SESSION = "session"
INHERIT = "inherit"
NAME = r"[a-z0-9][a-z0-9-]*"
SPEC_TIER_LINE = re.compile(
    r"Model tier is `(" + NAME + r")` — frontmatter `model:` reads exactly `(\w+)`"
    r"(?: and `effort:` reads exactly `(\w+)`| and `effort:` is absent)")
GATE_AGENT = re.compile(r"Agent: `(" + NAME + r")`")
GATE_TIER = re.compile(r"Model tier: `(\w+)`(?: · effort `(\w+)`)?")


def strip_comment(line):
    cut = line.find(" #")
    return line[:cut].rstrip() if cut >= 0 else line.rstrip()


def read_table(text):
    """(tiers, agents, overrides, errors). tiers: list of (name, model, effort, optional)."""
    tiers, agents, overrides, errors = [], {}, {}, []
    fields = {}
    section = current = None
    seen_top = set()
    for number, raw in enumerate(text.replace("\r", "").split("\n"), 1):
        if "\t" in raw:
            errors.append(f"line {number}: tab")
            continue
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = strip_comment(raw)
        if re.match(r"^\S", line):
            match = re.fullmatch(r"([a-z_]+):", line)
            if not match:
                errors.append(f"line {number}: top-level key with a value or flow form")
                continue
            key = match[1]
            if key not in TOP_KEYS:
                errors.append(f"line {number}: unknown top-level key {key}")
            if key in seen_top:
                errors.append(f"line {number}: duplicate key {key}")
            seen_top.add(key)
            section, current = key, None
            continue
        match = re.fullmatch(r"  (" + NAME + r"):(?: (\S+))?", line)
        if match and section == "tiers" and match[2] is None:
            current = match[1]
            if current in fields:
                errors.append(f"line {number}: duplicate key {current}")
            fields[current] = {}
            tiers.append(current)
            continue
        if match and section in ("agents", "overrides") and match[2] is not None:
            target = agents if section == "agents" else overrides
            value = match[2]
            if value[0] in "{[":
                errors.append(f"line {number}: flow form")
            if match[1] in target:
                errors.append(f"line {number}: duplicate key {match[1]}")
            target[match[1]] = value
            continue
        match = re.fullmatch(r"    ([a-z]+): (\S+)", line)
        if match and section == "tiers" and current is not None:
            if match[1] not in TIER_FIELDS:
                errors.append(f"line {number}: unknown tier field {match[1]}")
            elif match[1] in fields[current]:
                errors.append(f"line {number}: duplicate key {match[1]}")
            if match[2][0] in "{[":
                errors.append(f"line {number}: flow form")
            fields[current][match[1]] = match[2]
            continue
        errors.append(f"line {number}: not in the grammar: {line.strip()}")
    ordered = []
    previous = None
    for index, name in enumerate(tiers):
        f = fields[name]
        model, effort, optional = f.get("model"), f.get("effort"), f.get("optional", "false")
        if model not in MODEL_RANK:
            errors.append(f"tier {name}: unknown model {model}")
        if effort not in EFFORT_RANK:
            errors.append(f"tier {name}: unknown effort {effort}")
        if optional not in ("true", "false"):
            errors.append(f"tier {name}: optional must be true or false")
        if optional == "true" and index != len(tiers) - 1:
            errors.append(f"tier {name}: only the last tier may be optional")
        if model in MODEL_RANK and effort in EFFORT_RANK:
            rank = (MODEL_RANK[model], EFFORT_RANK[effort])
            if previous is not None and rank <= previous:
                errors.append(f"tier {name}: not above the tier before it")
            previous = rank
        ordered.append((name, model, effort, optional == "true"))
    names = set(tiers)
    for agent, tier in agents.items():
        if tier == SESSION:
            errors.append(f"agent {agent}: session is allowed only under overrides")
        elif tier not in names:
            errors.append(f"agent {agent}: unknown tier {tier}")
    for agent, tier in overrides.items():
        if tier != SESSION and tier not in names:
            errors.append(f"override {agent}: unknown tier {tier}")
        if agent not in agents:
            errors.append(f"override {agent}: no such agent in agents")
    return ordered, agents, overrides, errors


def expected_frontmatter(tiers, agents, overrides):
    """agent -> (model, effort or None)."""
    by_name = {name: (model, effort) for name, model, effort, _ in tiers}
    result = {}
    for agent, tier in agents.items():
        tier = overrides.get(agent, tier)
        result[agent] = (INHERIT, None) if tier == SESSION else by_name.get(tier, (None, None))
    return result


def frontmatter_fields(text):
    parts = text.replace("\r", "").split("---", 2)
    head = parts[1] if len(parts) == 3 else ""
    model = re.search(r"^model:\s*(\S+)", head, re.M)
    effort = re.search(r"^effort:\s*(\S+)", head, re.M)
    return (model[1] if model else None), (effort[1] if effort else None)


def run_script(root, *args):
    return subprocess.run([BASH, str(root / SCRIPT), *args, "--root", str(root)], capture_output=True,
                          text=True, env=SCRIPT_ENV, timeout=SCRIPT_TIMEOUT_S)


VALID_TABLE = """# fixture
tiers:
  low-tier:
    model: sonnet
    effort: medium
  high-tier:
    model: opus
    effort: high   # a comment
  top-tier:
    model: fable
    effort: high
    optional: true
agents:
  alpha: low-tier
  beta: high-tier
overrides:
"""

AGENT_FILE = "---\nname: {name}\ndescription: \"x\"\ntools: Read\nmodel: inherit\nmaxTurns: 10\n---\n\nmodel: body line\n"

REJECTED = {
    "tab": VALID_TABLE.replace("  alpha: low-tier", "\talpha: low-tier"),
    "duplicate agent": VALID_TABLE.replace("  beta: high-tier", "  beta: high-tier\n  beta: low-tier"),
    "duplicate tier field": VALID_TABLE.replace("    effort: medium", "    effort: medium\n    effort: high"),
    "flow map": VALID_TABLE.replace("overrides:\n", "overrides: {}\n"),
    "unknown top-level key": VALID_TABLE + "ladder:\n",
    "unknown model": VALID_TABLE.replace("model: sonnet", "model: gpt"),
    "unknown effort": VALID_TABLE.replace("effort: medium", "effort: huge"),
    "tiers out of order": VALID_TABLE.replace("model: sonnet\n    effort: medium", "model: opus\n    effort: max"),
    "optional not last": VALID_TABLE.replace("    effort: medium", "    effort: medium\n    optional: true"),
    "session under agents": VALID_TABLE.replace("  alpha: low-tier", "  alpha: session"),
    "unknown tier": VALID_TABLE.replace("  beta: high-tier", "  beta: mid-tier"),
    "agent without a file": VALID_TABLE.replace("  beta: high-tier", "  beta: high-tier\n  gamma: low-tier"),
    "file without an agent": VALID_TABLE.replace("  beta: high-tier\n", ""),
    "unknown tier field": VALID_TABLE.replace("    effort: medium", "    effort: medium\n    weight: heavy"),
    "flow list": VALID_TABLE.replace("  alpha: low-tier", "  alpha: [low-tier]"),
    "flow map in a tier field": VALID_TABLE.replace("    model: sonnet", "    model: {a: b}"),
}


class FixtureTree:
    """A temp project with the script, a table and agent files alpha and beta."""

    def __init__(self, table, crlf=()):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        (self.root / ".claude/scripts").mkdir(parents=True)
        (self.root / AGENTS_DIR).mkdir(parents=True)
        shutil.copy(ROOT / SCRIPT, self.root / SCRIPT)
        (self.root / TABLE).write_bytes(table.encode("utf-8"))
        for name in ("alpha", "beta"):
            text = AGENT_FILE.format(name=name)
            if name in crlf:
                text = text.replace("\n", "\r\n")
            (self.root / AGENTS_DIR / f"{name}.md").write_bytes(text.encode("utf-8"))

    def agent(self, name):
        return (self.root / AGENTS_DIR / f"{name}.md").read_bytes().decode("utf-8")

    def close(self):
        self.dir.cleanup()


class TableGrammar(unittest.TestCase):
    """Both readers accept the valid table and reject each form the grammar forbids."""

    def test_valid_fixture_is_accepted_by_both_readers(self):
        _, _, _, errors = read_table(VALID_TABLE)
        self.assertEqual(errors, [])
        tree = FixtureTree(VALID_TABLE)
        try:
            result = run_script(tree.root, "sync")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = run_script(tree.root, "check")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        finally:
            tree.close()

    def test_each_rejected_form_fails_in_both_readers(self):
        for label, table in REJECTED.items():
            with self.subTest(form=label):
                files_only = label in ("agent without a file", "file without an agent")
                _, agents, _, errors = read_table(table)
                if files_only:
                    self.assertNotEqual(set(agents), {"alpha", "beta"}, label)
                else:
                    self.assertTrue(errors, f"the Python reader accepted: {label}")
                tree = FixtureTree(table)
                try:
                    result = run_script(tree.root, "check")
                    self.assertEqual(result.returncode, 1, f"{label}: {result.stdout}{result.stderr}")
                    self.assertTrue(result.stdout.strip() or result.stderr.strip(), label)
                finally:
                    tree.close()


class Sync(unittest.TestCase):
    """sync writes only the frontmatter's model and effort lines, keeping line endings."""

    def setUp(self):
        self.tree = FixtureTree(VALID_TABLE, crlf=("beta",))
        self.before = {name: self.tree.agent(name) for name in ("alpha", "beta")}
        result = run_script(self.tree.root, "sync")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def tearDown(self):
        self.tree.close()

    def test_frontmatter_gets_the_tier(self):
        self.assertEqual(frontmatter_fields(self.tree.agent("alpha")), ("sonnet", "medium"))
        self.assertEqual(frontmatter_fields(self.tree.agent("beta")), ("opus", "high"))

    def test_only_model_and_effort_lines_change(self):
        for name in ("alpha", "beta"):
            before = self.before[name].replace("\r", "").split("\n")
            after = self.tree.agent(name).replace("\r", "").split("\n")
            removed = [line for line in before if line not in after]
            added = [line for line in after if line not in before]
            self.assertTrue(all(line.startswith("model:") for line in removed), (name, removed))
            self.assertTrue(all(line.startswith(("model:", "effort:")) for line in added), (name, added))

    def test_body_line_starting_with_model_is_untouched(self):
        for name in ("alpha", "beta"):
            self.assertIn("model: body line", self.tree.agent(name))

    def test_crlf_file_stays_crlf(self):
        text = self.tree.agent("beta")
        self.assertEqual(text.count("\r\n"), text.count("\n"), "beta lost its CRLF endings")
        self.assertNotIn("\r", self.tree.agent("alpha"))

    def test_a_hand_edit_is_named_by_check(self):
        path = self.tree.root / AGENTS_DIR / "alpha.md"
        path.write_bytes(path.read_bytes().replace(b"model: sonnet", b"model: opus"))
        result = run_script(self.tree.root, "check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("alpha", result.stdout)

    def test_an_override_moves_exactly_one_agent(self):
        table = self.tree.root / TABLE
        table.write_text(VALID_TABLE + "  alpha: session\n", encoding="utf-8")
        before_beta = self.tree.agent("beta")
        result = run_script(self.tree.root, "sync")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(frontmatter_fields(self.tree.agent("alpha")), (INHERIT, None))
        self.assertEqual(self.tree.agent("beta"), before_beta)
        self.assertEqual(run_script(self.tree.root, "check").returncode, 0)


class ScriptArguments(unittest.TestCase):
    def test_root_without_a_value_is_a_usage_error(self):
        # `timeout` runs inside bash so that a hang ends as exit 124 and fails
        # here, instead of leaving a looping bash process behind (critic P13 F8).
        script = (ROOT / SCRIPT).as_posix()
        result = subprocess.run([BASH, "-c", f'timeout 10 bash "{script}" check --root'], capture_output=True,
                                text=True, env=SCRIPT_ENV, timeout=60)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


class RepositoryTable(unittest.TestCase):
    """The repository's table is valid, complete and matches every agent file."""

    def setUp(self):
        self.text = (ROOT / TABLE).read_text(encoding="utf-8") if (ROOT / TABLE).exists() else ""
        self.tiers, self.agents, self.overrides, self.errors = read_table(self.text)

    def test_table_exists_and_is_valid(self):
        self.assertTrue(self.text, f"{TABLE} does not exist")
        self.assertEqual(self.errors, [])

    def test_table_names_every_agent_file_once(self):
        files = {p.stem for p in (ROOT / AGENTS_DIR).glob("*.md")}
        self.assertEqual(set(self.agents), files)

    def test_no_default_is_inherit_or_unset(self):
        expected = expected_frontmatter(self.tiers, self.agents, {})
        for agent, (model, effort) in expected.items():
            with self.subTest(agent=agent):
                self.assertNotEqual(model, INHERIT)
                self.assertIsNotNone(effort)

    def test_script_check_passes_on_the_tree(self):
        result = run_script(ROOT, "check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_frontmatter_matches_the_table(self):
        expected = expected_frontmatter(self.tiers, self.agents, self.overrides)
        for agent, want in expected.items():
            with self.subTest(agent=agent):
                text = (ROOT / AGENTS_DIR / f"{agent}.md").read_text(encoding="utf-8")
                self.assertEqual(frontmatter_fields(text), want)


class SpecsAndGates(unittest.TestCase):
    """Each agent spec's Model-tier line and each gate header state the agent's frontmatter."""

    def setUp(self):
        _, agents, overrides, _ = read_table((ROOT / TABLE).read_text(encoding="utf-8"))
        self.tiers = {agent: overrides.get(agent, tier) for agent, tier in agents.items()}

    def frontmatter_of(self, agent):
        return frontmatter_fields((ROOT / AGENTS_DIR / f"{agent}.md").read_text(encoding="utf-8"))

    def test_every_spec_states_model_and_effort(self):
        specs = {p.stem: p for p in (ROOT / SPECS_DIR).rglob("*.md")}
        for agent_file in sorted((ROOT / AGENTS_DIR).glob("*.md")):
            agent = agent_file.stem
            with self.subTest(agent=agent):
                self.assertIn(agent, specs, f"no spec for {agent}")
                match = SPEC_TIER_LINE.search(specs[agent].read_text(encoding="utf-8"))
                self.assertIsNotNone(match, f"{specs[agent]}: no Model-tier line with model and effort")
                self.assertEqual((match[2], match[3]), self.frontmatter_of(agent), specs[agent])
                self.assertEqual(match[1], self.tiers.get(agent), f"{specs[agent]}: tier name")

    def test_every_gate_header_states_model_and_effort(self):
        for gate in sorted((ROOT / GATES_DIR).glob("*.md")):
            with self.subTest(gate=gate.name):
                lines = gate.read_text(encoding="utf-8").splitlines()
                header = next((line for line in lines[:8] if line.startswith("Agent:")), "")
                agent, tier = GATE_AGENT.search(header), GATE_TIER.search(header)
                self.assertIsNotNone(agent, f"{gate.name}: no Agent line")
                self.assertIsNotNone(tier, f"{gate.name}: no Model tier with a backticked model")
                self.assertEqual((tier[1], tier[2]), self.frontmatter_of(agent[1]))


LADDER_DOC = ".claude/docs/escalation-ladder.md"
COORDINATION = ".claude/docs/coordination-rules.md"
# Spec studio-roles/escalation-ladder: what the document must say, as phrases.
LADDER_PHRASES = {
    "signal: a check fails again": "fails again after a fix attempt",
    "signal: a second rejection": "second rejection on the same finding",
    "signal: a block or maxTurns": "`maxTurns`",
    "signal: a format failed twice": "required format twice",
    "non-signal: missing information": "missing information",
    "non-signal: the user's decision": "a decision that is the user's",
    "non-signal: a refusal": "a refusal",
    "non-signal: taste": "a matter of taste",
    "a non-signal wins": "the non-signal wins",
    "one rung": "one rung above the rung it last ran at",
    "per-invocation parameters": "per-invocation `model` and `effort`",
    "the brief goes with it": "what was tried",
    "the report line": "role, old rung, new rung and signal",
    "reset per task": "starts at its own tier again",
    "the optional top rung": "`fable-high`",
    "the stop": "stop and ask the user",
    "effort set by the environment": "`CLAUDE_CODE_EFFORT_LEVEL`",
    "models forced by the environment": "`CLAUDE_CODE_SUBAGENT_MODEL_FORCE`",
    "the main session is the user's": "`/effort`",
    "a subagent that starts agents": "a subagent that starts agents",
    "live behaviour": "live behaviour",
}


class EscalationLadder(unittest.TestCase):
    """The ladder's rule lives in one document that every session loads through coordination-rules.md."""

    def test_document_states_the_rule_and_its_limits(self):
        path = ROOT / LADDER_DOC
        self.assertTrue(path.exists(), f"{LADDER_DOC} does not exist")
        text = " ".join(path.read_text(encoding="utf-8").split())
        for label, phrase in LADDER_PHRASES.items():
            with self.subTest(rule=label):
                self.assertIn(phrase, text)

    def test_coordination_rules_point_to_it_in_one_line(self):
        lines = (ROOT / COORDINATION).read_text(encoding="utf-8").splitlines()
        self.assertEqual(sum(LADDER_DOC in line for line in lines), 1)

    def test_no_agent_file_states_the_ladder(self):
        for path in sorted((ROOT / AGENTS_DIR).glob("*.md")):
            with self.subTest(agent=path.stem):
                self.assertNotIn("escalation-ladder", path.read_text(encoding="utf-8"))


LEDGER = "docs/research/aaa-engine-support-2026"
# Fix plan AM38, task 4.3: each Claude Code fact the new text states is a
# ledger claim, bound to a phrase that must stay in its file (as in Phase 11).
KEY_PHRASES = {
    "C266": (".claude/docs/model-tiers.md", "applies the session's effort only to a subagent on the session's own model"),
    "C267": (".claude/docs/model-tiers.md", "set `CLAUDE_CODE_EFFORT_LEVEL` as well"),
    "C268": (LADDER_DOC, "per-invocation `model` and `effort` parameters"),
    "C269": (LADDER_DOC, "stops a per-invocation model"),
}


class LedgerBindings(unittest.TestCase):
    """The model and effort facts are ledger claims whose key phrases stay in their files."""

    def setUp(self):
        import json
        read = lambda name: [json.loads(line) for line in (ROOT / LEDGER / name).read_text(encoding="utf-8").splitlines()
                             if line.strip()]
        self.claims = {c["claim_id"]: c for c in read("claims.jsonl")}
        self.evidence = {e["evidence_id"] for e in read("evidence.jsonl")}

    def test_each_fact_is_a_claim_bound_to_its_file(self):
        for claim_id, (path, phrase) in KEY_PHRASES.items():
            with self.subTest(claim=claim_id):
                self.assertIn(claim_id, self.claims)
                claim = self.claims[claim_id]
                self.assertEqual(claim.get("file"), path)
                self.assertTrue(set(claim["evidence_ids"]) <= self.evidence)
                text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
                self.assertIn(phrase, text)


# Design D6: what both release notes must say about AM38, as phrases.
DISCLOSURE_TOKENS = {
    "the table": "`.claude/agent-models.yaml`",
    "the script": "agent-models.sh",
    "the per-role way back": "`session`",
    "the way back for every subagent": "`CLAUDE_CODE_SUBAGENT_MODEL_FORCE`",
    "the effort way back": "`CLAUDE_CODE_EFFORT_LEVEL`",
    "a session above the pin": "no longer lifts it",
    "the cost": "far more roles run on Opus",
    "the ladder": "escalation-ladder.md",
    "not provable": "live behaviour",
    "the ladder's limits with both variables set": "the ladder does nothing",
    "the main session is the user's": "`/effort`",
    "the session override and the studio tests": "`session` override",
    "the gate headers after a session override": "director-gates",
}
# The AM38 passage of the notes states no tier count, so it cannot drift from
# the table; the counts live in model-tiers.md and README, which the count
# sweep checks (critic P13 F5).
AM38_PASSAGE = ("Every agent now runs on the model and effort", "name the new models.")
NUMBER_WORDS = re.compile(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
                          r"fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|"
                          r"seventy|eighty|ninety)(?:-\w+)?\b", re.I)


class ReleaseNotes(unittest.TestCase):
    """UPGRADING and CHANGELOG disclose AM38's change on every engine, its cost and the way back."""

    def unreleased(self, path, start, stop):
        text = (ROOT / path).read_text(encoding="utf-8")
        section = text[text.index(start):text.index(stop, text.index(start) + 1)]
        return " ".join(section.split())

    def test_both_notes_disclose_the_change(self):
        notes = {
            "UPGRADING.md": self.unreleased("UPGRADING.md", "## Unreleased", "\n## v1.2.0"),
            "CHANGELOG.md": self.unreleased("CHANGELOG.md", "## [Unreleased]", "\n## [1.3.0]"),
        }
        for note, text in notes.items():
            for label, token in DISCLOSURE_TOKENS.items():
                with self.subTest(note=note, says=label):
                    self.assertIn(token, text)
            with self.subTest(note=note, says="no tier counts"):
                start, end = AM38_PASSAGE
                self.assertIn(start, text)
                passage = text[text.index(start):text.index(end, text.index(start))]
                self.assertEqual(NUMBER_WORDS.findall(passage.replace("AM38", "")), [])


if __name__ == "__main__":
    unittest.main()
