"""Structural contracts of fix plan Phase 11 (section 13, amendment AM32).

Run: python -m unittest discover -s studio-tests -p test_engine_phase11.py -v
The plan is the OpenSpec change `add-content-and-xr-roles`: roles from engine to
tech demo, valid on every engine. These check files on disk and the output of
the repository's own scripts, not Claude's behaviour in a session.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import (  # noqa: E402
    CUSTOM_AGENT_SPEC_DIR, MIN_SPEC_CASES, MODEL_LINE, PRIMARY_DUTY_SECTION, PROTOCOL_SECTION, ROOT, SPEC_CASE_HEADING,
    TECHNICAL_SECTIONS,
    case_fixture_engines, duty_text, engine_names, frontmatter, ledger, read, section_text)
from test_engine_scope import BASH, SCRIPT_ENV, SCRIPT_TIMEOUT_S  # noqa: E402

# AM32(c): the XR signal. /setup-engine resolves the target platforms in its
# project.yaml step, which every entry path runs, and writes the whole
# `platform` block there (design D4).
SETUP_REFERENCES = ".claude/skills/setup-engine/references/"
SETUP_FILES = ".claude/skills/setup-engine/"
PROJECT_YAML_STEP = SETUP_REFERENCES + "5.5-project-yaml.md"
GUIDED_MODE = SETUP_REFERENCES + "2-guided-mode.md"
CUSTOM_SETUP = SETUP_REFERENCES + "custom.md"
WEB_SETUP = SETUP_REFERENCES + "web.md"
EFFECTS_MAP = ".claude/docs/effects-map.md"
CONFIG_RESOLUTION = ".claude/docs/config-resolution.md"
YAML_HELPER = ".claude/hooks/yaml-helper.sh"

TARGETS_KEY = "`platform.targets`"
XR_VALUE = "`XR`"
PLATFORM_BLOCK = "platform"
TARGETS = "targets"
# The block's keys. `yaml-helper.sh` takes input methods from project.yaml as
# soon as the block has any key, and then never reads technical-preferences.md
# (yaml-helper.sh, input_methods), so all four are written together.
PLATFORM_KEYS = (TARGETS, "gamepad_support", "touch_support", "primary_input")
# The resolution order the 5.5 step already uses (5.5-project-yaml.md, "Resolve
# each input in this order"): Section 2's answers, the design artifact, then
# ask. The ask names guided Question 2, so no second platform question exists.
RESOLUTION_ORDER = ("Section 2", "design artifact", "Question 2")
# The XR option each existing platform question gains, and the prompts of those
# two questions, each written once in the setup files.
GUIDED_XR_OPTION = "`VR headset (XR)`"
CUSTOM_XR_OPTION = "`XR headset`"
GUIDED_QUESTION_2 = "**Question 2"
GUIDED_QUESTION_END = "Then, in plain text:"
TYPED_ANSWER = "a typed"
# AM35(a), C168: the question tool takes two to four options per question. An
# option list is a run of backticked options joined by " / ".
MAX_TOOL_OPTIONS = 4
OPTION = re.compile(r"`[^`\n]+`")
OPTION_LIST = re.compile(r"`[^`\n]+`(?:\s*/\s*`[^`\n]+`)+")
MULTI_SELECT = "multi-select"
PLATFORM_PROMPTS = ("Where should the game be played?", "**Platforms:**")
OWN_PROMPT_MARKERS = ("Prompt:", "Options:")
DESKTOP_SYSTEMS = ("`Windows`", "`Linux`", "`macOS`")
PC_VALUE = "`PC`"
WEB_VALUE = "Web"
INPUT_METHODS_ROW = "| `input_methods` |"
TARGETS_LINE = re.compile(r"^\s+targets:\s*\[[^\]]*\]\s*#(.*)$", re.M)

LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
QUOTE = re.compile(r"^\s*>\s?")
FENCE = re.compile(r"^\s*(?:>\s?)*\s*```")


def unquoted(line):
    """A line with its blockquote markers removed."""
    while QUOTE.match(line):
        line = QUOTE.sub("", line, count=1)
    return line


def list_items(text):
    """Each Markdown list item, with its continuation lines and nested items."""
    lines = [unquoted(line) for line in text.replace("\r", "").splitlines()]
    items = []
    for start, line in enumerate(lines):
        head = LIST_ITEM.match(line)
        if not head:
            continue
        indent, body = len(head[1]), [line]
        for line in lines[start + 1:]:
            if not line.strip() or HEADING.match(line):
                break
            if len(line) - len(line.lstrip()) <= indent:
                break
            body.append(line)
        items.append(" ".join(" ".join(body).split()))
    return items


def section(text, needle):
    """The section under the first heading containing `needle`, up to the next
    heading of the same or a higher level; None when there is none."""
    lines = text.replace("\r", "").splitlines()
    for start, line in enumerate(lines):
        head = HEADING.match(line)
        if head and needle in head[2]:
            level, body = len(head[1]), []
            for line in lines[start + 1:]:
                other = HEADING.match(line)
                if other and len(other[1]) <= level:
                    break
                body.append(line)
            return "\n".join(body)
    return None


def yaml_block_keys(text, block):
    """The child keys of each fenced YAML block that opens with `<block>:`."""
    keys = set()
    for fence in re.findall(r"```yaml\n(.*?)```", text or "", re.S):
        lines = [unquoted(line) for line in fence.splitlines()]
        tops = [i for i, line in enumerate(lines) if re.match(rf"^\s*{block}:\s*(#.*)?$", line)]
        for top in tops:
            indent = len(lines[top]) - len(lines[top].lstrip())
            for line in lines[top + 1:]:
                child = re.match(r"^(\s*)([\w.]+):", line)
                if not child or len(child[1]) <= indent:
                    break
                keys.add(child[2])
    return keys


def platform_step():
    return section(read(PROJECT_YAML_STEP), f"`{PLATFORM_BLOCK}`")


# The input-method parity fixtures: one project each, as Section 5 records it
# in technical-preferences.md (5-technical-preferences.md, "Input & Platform":
# Mobile is touch Full, gamepad None; Console is gamepad Full, touch None).
PARITY_FIXTURES = {
    "Mobile with touch": {"targets": "[Mobile]", "gamepad_support": "None", "touch_support": "Full",
                          "primary_input": "Touch", "Target Platforms": "Mobile", "Input Methods": "Touch"},
    "Console with full gamepad": {"targets": "[Console]", "gamepad_support": "Full", "touch_support": "None",
                                  "primary_input": "Gamepad", "Target Platforms": "Console",
                                  "Input Methods": "Gamepad"},
    # AM33(b), critic F2: the PC row's recommended Gamepad Support `Partial`,
    # with an Input Methods line the user confirmed without Gamepad.
    "PC only, Input Methods Keyboard/Mouse, Gamepad Partial": {
        "targets": "[PC]", "gamepad_support": "Partial", "touch_support": "None", "primary_input": "Keyboard/Mouse",
        "Target Platforms": "PC", "Input Methods": "Keyboard/Mouse"},
    # AM34, critic F10: keyboard/mouse on a target with no PC or Web, and a
    # primary input that is not keyboard/mouse, so no key can give it.
    "Console, Input Methods Gamepad, Keyboard/Mouse, Gamepad Full, primary Gamepad": {
        "targets": "[Console]", "gamepad_support": "Full", "touch_support": "None", "primary_input": "Gamepad",
        "Target Platforms": "Console", "Input Methods": "Gamepad, Keyboard/Mouse"},
    # AM34, critic F10: the template's own example value, which names no
    # method. "Named" is the user's answer when the step asks which it means.
    "PC, Input Methods Mixed, Gamepad Partial": {
        "targets": "[PC]", "gamepad_support": "Partial", "touch_support": "None", "primary_input": "Keyboard/Mouse",
        "Target Platforms": "PC", "Input Methods": "Mixed", "Named": "Keyboard/Mouse, Gamepad"},
}
# AM33(b): when Section 5's support lines and its Input Methods line disagree,
# 5.5.4 asks once which is right and writes the answer to both files. One list
# item of the step holds that instruction.
RECONCILE_TOKENS = ("Input Methods", "disagree", "ask once", "both files")
SUPPORT_METHODS = (("gamepad", "gamepad_support"), ("touch", "touch_support"))
NO_SUPPORT = "None"
# AM33(a): the resolution list starts with the keys already in project.yaml,
# and a key changes only on the user's explicit answer.
NUMBERED = re.compile(r"^\d+[.)]\s")
EXISTING_KEYS_TOKENS = ("`project.yaml`", "already")
EXPLICIT_CHANGE_TOKENS = ("only", "explicit answer")
# AM33(c): 5.5.1's web/non-web input is the targets 5.5.4 resolves.
SHAPE_STEP = "5.5.1"
WEB_WORD = "web"
TARGETS_SOURCE_TOKENS = ("5.5.4", "targets", "`Web`")
# AM33(d): one approval names both files the step writes.
APPROVAL_FILES = ("`project.yaml`", "`technical-preferences.md`")
TP_LABELS = {"Target Platforms": "Target Platforms", "Input Methods": "Input Methods",
             "primary_input": "Primary Input", "gamepad_support": "Gamepad Support",
             "touch_support": "Touch Support"}
ENGINE_BLOCK = 'engine:\n  name: "Unity"\n  version: "6000.3"\n  language: "C#"\n'
INPUT_METHODS_LINE = re.compile(r"^input_methods: (.*?) \(([^;]*); primary: [^)]*\)$", re.M)
NO_METHODS = ("none", "unset")
# The spellings yaml-helper.sh reads as one method (input_methods).
METHOD_ALIASES = {"keyboard & mouse": "keyboard/mouse", "keyboard": "keyboard/mouse", "mouse": "keyboard/mouse",
                  "controller": "gamepad", "touchscreen": "touch"}
KEYBOARD_MOUSE = "keyboard/mouse"
# AM34, critic F10: a method of the Input Methods line that no value of the four
# keys can give. yaml-helper.sh gives keyboard/mouse only for a `pc` or `web`
# target, gamepad and touch from their support keys, and the primary input's
# method. The step asks once: add the target that carries the method, drop the
# method, or, for a value that names no method, name the methods. One list
# item of the step holds that instruction.
GAP_TOKENS = ("cannot give", "`Mixed`", "add the target", "drop the method", "name the methods")
SUPPORT_METHOD_NAMES = {method for method, _ in SUPPORT_METHODS}
KEYBOARD_MOUSE_TARGETS = ("pc", "web")
CARRIER_TARGET = "PC"
NAMED = "Named"


def technical_preferences(fixture):
    lines = ["# Technical Preferences", "", "## Input & Platform"]
    lines += [f"- **{label}**: {fixture[key]}" for key, label in TP_LABELS.items()]
    return "\n".join(lines) + "\n"


def platform_yaml(fixture, keys):
    lines = [f"{PLATFORM_BLOCK}:"]
    for key in PLATFORM_KEYS:
        if key in keys:
            value = fixture[key]
            lines.append(f"  {key}: {value}" if key == TARGETS else f'  {key}: "{value}"')
    return "\n".join(lines) + "\n"


def methods(text):
    found = text.strip().lower()
    if found in NO_METHODS:
        return set()
    return {METHOD_ALIASES.get(m.strip(), m.strip()) for m in found.split(",") if m.strip()}


def reconciliation_item(step):
    """The list item of the platform step that holds the AM33(b) instruction."""
    return next((item for item in list_items(step or "") if all(t in item for t in RECONCILE_TOKENS)), None)


def gap_item(step):
    """The list item of the platform step that holds the AM34 instruction."""
    return next((item for item in list_items(step or "") if all(t in item for t in GAP_TOKENS)), None)


def target_list(fixture):
    return [t.strip() for t in fixture[TARGETS].strip("[]").split(",") if t.strip()]


def unreachable(fixture, line_methods):
    """The methods of the Input Methods line that no value of the four keys can
    give for this project (AM34): keyboard/mouse with no PC or Web target and
    another primary input, and any name the keys do not know, such as Mixed."""
    reachable = set(SUPPORT_METHOD_NAMES) | methods(fixture["primary_input"])
    if any(t.lower() in KEYBOARD_MOUSE_TARGETS for t in target_list(fixture)):
        reachable.add(KEYBOARD_MOUSE)
    return line_methods - reachable


def step_answers(fixture, line_methods, asks_about_gaps):
    """(answer, project after it) for each answer 5.5.4 offers. Without the
    AM34 instruction the step asks nothing about a method the keys cannot give
    and writes the fixture as it is. With it, per such method: keyboard/mouse
    gains the target that carries it, or leaves the Input Methods line; a name
    no key knows is replaced by the methods the user names, or leaves the line
    when other methods remain on it. Each answer is written to both files."""
    gaps = unreachable(fixture, line_methods) if asks_about_gaps else set()
    if not gaps:
        return [("no question", fixture)]
    answers = []
    for gap in sorted(gaps):
        rest = sorted(line_methods - {gap})
        if gap == KEYBOARD_MOUSE:
            targets = target_list(fixture) + [CARRIER_TARGET]
            answers.append((f"add the target {CARRIER_TARGET}", dict(
                fixture, **{TARGETS: f"[{', '.join(targets)}]", "Target Platforms": ", ".join(targets)})))
        else:
            answers.append((f"name the methods {fixture[NAMED]}", dict(fixture, **{"Input Methods": fixture[NAMED]})))
        if rest:
            answers.append((f"drop the method {gap}", dict(fixture, **{"Input Methods": ", ".join(rest)})))
    return answers


def line_kept(fixture, line_methods):
    """The values 5.5.4 writes when the user answers that the Input Methods line
    is right (AM33(b)): a support value whose method the line omits is `None`."""
    values = dict(fixture)
    for method, key in SUPPORT_METHODS:
        if method not in line_methods:
            values[key] = NO_SUPPORT
    return values


class SetupWritesThePlatformBlock(unittest.TestCase):
    def input_methods(self, project_yaml, fixture):
        """(methods, source) that resolve_config gives for one fixture project."""
        self.assertIsNotNone(BASH, "Bash is required for the repository's scripts")
        with tempfile.TemporaryDirectory(prefix="ccgs-phase11-") as temp:
            project = Path(temp)
            (project / ".claude/docs").mkdir(parents=True)
            (project / ".claude/docs/technical-preferences.md").write_text(
                technical_preferences(fixture), encoding="utf-8", newline="\n")
            (project / "project.yaml").write_text(project_yaml, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [BASH, str(ROOT / YAML_HELPER), "resolve_config", "--keys", "input_methods"], cwd=project,
                env=SCRIPT_ENV, stdin=subprocess.DEVNULL, capture_output=True, timeout=SCRIPT_TIMEOUT_S)
        out = result.stdout.decode("utf-8", "replace").replace("\r", "")
        line = INPUT_METHODS_LINE.search(out)
        self.assertIsNotNone(line, f"no input_methods line in:\n{out}")
        return methods(line[1]), line[2]

    def test_setup_resolves_and_writes_the_platform_block(self):
        # AM32(c), design D4: one resolution step in 5.5, the XR option on the
        # two existing platform questions, the values Web and Custom give, and
        # no second platform question.
        missing = []
        step = platform_step()
        if step is None:
            missing.append(f"{PROJECT_YAML_STEP}: no heading naming the `{PLATFORM_BLOCK}` block")
            step = ""
        if not any(TARGETS_KEY in item and XR_VALUE in item for item in list_items(step)):
            missing.append(f"{PROJECT_YAML_STEP}: no list item holding both {TARGETS_KEY} and {XR_VALUE}")
        flat = " ".join(step.split())
        positions = [flat.find(token) for token in RESOLUTION_ORDER]
        if -1 in positions or positions != sorted(positions):
            missing.append(f"{PROJECT_YAML_STEP}: the platform step does not resolve in the order "
                           f"{' -> '.join(RESOLUTION_ORDER)} (positions {positions})")
        if any(marker in step for marker in OWN_PROMPT_MARKERS):
            missing.append(f"{PROJECT_YAML_STEP}: the platform step writes its own question; it must ask Question 2")
        keys = yaml_block_keys(step, PLATFORM_BLOCK)
        if not set(PLATFORM_KEYS) <= keys:
            missing.append(f"{PROJECT_YAML_STEP}: the `{PLATFORM_BLOCK}` block it writes lacks "
                           f"{sorted(set(PLATFORM_KEYS) - keys)}")
        guided = read(GUIDED_MODE)
        start = guided.find(GUIDED_QUESTION_2)
        question = guided[start:guided.find(GUIDED_QUESTION_END, start)] if start != -1 else ""
        question = " ".join(question.split())
        for token in (GUIDED_XR_OPTION, MULTI_SELECT, XR_VALUE):
            if token not in question:
                missing.append(f"{GUIDED_MODE}: Question 2 does not hold {token}")
        custom_items = list_items(read(CUSTOM_SETUP))
        # AM35(a): the Custom Platforms question keeps four options and takes
        # `XR headset` as a typed answer, as guided Question 2 does.
        if not any(PLATFORM_PROMPTS[1] in item and f"{TYPED_ANSWER} {CUSTOM_XR_OPTION}" in item
                   for item in custom_items):
            missing.append(f"{CUSTOM_SETUP}: the Platforms question does not take {CUSTOM_XR_OPTION} "
                           f"as a typed answer ({TYPED_ANSWER!r})")
        if not any(all(s in item for s in DESKTOP_SYSTEMS) and PC_VALUE in item for item in custom_items):
            missing.append(f"{CUSTOM_SETUP}: no list item maps {', '.join(DESKTOP_SYSTEMS)} to {PC_VALUE}")
        if not any(TARGETS_KEY in item and WEB_VALUE in item for item in list_items(read(WEB_SETUP))):
            missing.append(f"{WEB_SETUP}: no list item giving {TARGETS_KEY} the value {WEB_VALUE}")
        setup_texts = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8")
                       for p in sorted((ROOT / SETUP_FILES).rglob("*.md"))}
        for prompt in PLATFORM_PROMPTS:
            count = sum(" ".join(text.split()).count(prompt) for text in setup_texts.values())
            if count != 1:
                missing.append(f"{SETUP_FILES}: the platform prompt {prompt!r} is written {count} times, not once")
        for option, home in ((GUIDED_XR_OPTION, GUIDED_MODE), (CUSTOM_XR_OPTION, CUSTOM_SETUP)):
            others = [p for p, text in setup_texts.items() if option in text and p != home]
            if others:
                missing.append(f"{option} is offered outside {home}: {others}")
        comment = TARGETS_LINE.search(read(EFFECTS_MAP))
        if not comment or "XR" not in comment[1]:
            missing.append(f"{EFFECTS_MAP}: the platform.targets comment does not list XR "
                           f"({comment[0].strip() if comment else 'no targets line'})")
        row = next((l for l in read(CONFIG_RESOLUTION).splitlines() if l.startswith(INPUT_METHODS_ROW)), "")
        if XR_VALUE not in row:
            missing.append(f"{CONFIG_RESOLUTION}: the input_methods row does not say how {XR_VALUE} is read")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_each_platform_question_fits_the_question_tool(self):
        # AM35(a), score report 5 N1: SKILL.md asks with the question tool,
        # which takes at most four options per question (C168). Guided
        # Question 2 with its Several follow-up, and the Custom Platforms
        # question, each list at most four.
        guided = read(GUIDED_MODE)
        start = guided.find(GUIDED_QUESTION_2)
        custom = [item for item in list_items(read(CUSTOM_SETUP)) if PLATFORM_PROMPTS[1] in item]
        questions = {GUIDED_MODE: guided[start:guided.find(GUIDED_QUESTION_END, start)] if start != -1 else "",
                     CUSTOM_SETUP: custom[0] if custom else ""}
        for where, question in questions.items():
            with self.subTest(question=where):
                lists = OPTION_LIST.findall(" ".join(question.split()))
                self.assertTrue(lists, f"{where}: no option list in the platform question")
                for options in lists:
                    count = len(OPTION.findall(options))
                    self.assertLessEqual(count, MAX_TOOL_OPTIONS,
                                         f"{where}: {count} options in {options!r}; the question tool "
                                         f"takes at most {MAX_TOOL_OPTIONS} (C168)")

    def test_written_block_keeps_the_input_methods_of_technical_preferences(self):
        # R1, design D4: a `platform` block switches input_methods from
        # technical-preferences.md to project.yaml. The block 5.5 writes (its
        # targets plus the keys of the block it shows) must resolve to the same
        # methods as technical-preferences.md gives for the same project.
        # AM33(b): where Section 5's support lines and its Input Methods line
        # disagree, the step asks once which is right. The user who keeps the
        # Input Methods line gets a block without the method the line omits;
        # the user who keeps the support lines gets that line rewritten. Without
        # the instruction, the step writes the support lines as they are.
        # AM34, critic F10: where the line lists a method no key can give, the
        # step asks once and each answer is written to both files; the block
        # must then give the methods of the line as that answer leaves it.
        step = platform_step()
        written = {TARGETS} | yaml_block_keys(step, PLATFORM_BLOCK)
        reconciles = reconciliation_item(step) is not None
        asks_about_gaps = gap_item(step) is not None
        for name, fixture in PARITY_FIXTURES.items():
            legacy, legacy_src = self.input_methods(ENGINE_BLOCK, fixture)
            for answer, project in step_answers(fixture, legacy, asks_about_gaps):
                with self.subTest(fixture=name, answer=answer):
                    self.assertIn("technical-preferences.md", legacy_src)
                    self.assertTrue(legacy, f"{name}: technical-preferences.md gives no method")
                    line, _ = self.input_methods(ENGINE_BLOCK, project)
                    values = line_kept(project, line) if reconciles else project
                    block = ENGINE_BLOCK + platform_yaml(values, written)
                    resolved, source = self.input_methods(block, project)
                    self.assertIn("project.yaml", source)
                    self.assertEqual(resolved, line,
                                     f"{name} ({answer}): the project.yaml branch gives {sorted(resolved) or 'none'}, "
                                     f"technical-preferences.md gives {sorted(line)}; 5.5 writes platform keys "
                                     f"{sorted(written)}")
                    if reconciles:
                        # The other answer: the support lines stay, and the Input
                        # Methods line is rewritten to the methods the block gives.
                        as_is, _ = self.input_methods(ENGINE_BLOCK + platform_yaml(project, written), project)
                        rewritten = dict(project, **{"Input Methods": ", ".join(sorted(as_is))})
                        line, _ = self.input_methods(ENGINE_BLOCK, rewritten)
                        self.assertEqual(line, as_is, f"{name} ({answer}): the rewritten Input Methods line gives "
                                                      f"{sorted(line)}, the block gives {sorted(as_is)}")

    def test_platform_step_reconciles_the_input_methods_line(self):
        # AM33(b), critic F2: the instruction itself, in one list item.
        self.assertIsNotNone(reconciliation_item(platform_step()),
                             f"{PROJECT_YAML_STEP}: no list item of the platform step holds "
                             f"{RECONCILE_TOKENS}")

    def test_platform_step_asks_about_methods_the_keys_cannot_give(self):
        # AM34, critic F10: the instruction itself, in one list item.
        self.assertIsNotNone(gap_item(platform_step()),
                             f"{PROJECT_YAML_STEP}: no list item of the platform step holds {GAP_TOKENS}")

    def test_existing_platform_keys_win(self):
        # AM33(a), critic F1: on a re-run the `platform` keys already in
        # project.yaml are step 0, and a key changes only on an explicit answer.
        step = platform_step() or ""
        numbered = [item for item in list_items(step) if NUMBERED.match(item)]
        missing = []
        if not numbered or not all(token in numbered[0] for token in EXISTING_KEYS_TOKENS):
            missing.append(f"{PROJECT_YAML_STEP}: the platform step's resolution list does not start with the "
                           f"keys already in project.yaml (first item: {numbered[0] if numbered else None!r})")
        sentences = re.split(r"(?<=[.?!])\s+", " ".join(step.split()))
        if not any(all(token in s for token in EXPLICIT_CHANGE_TOKENS) for s in sentences):
            missing.append(f"{PROJECT_YAML_STEP}: no sentence of the platform step holds {EXPLICIT_CHANGE_TOKENS}")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_godot_shape_asks_no_second_platform_question(self):
        # AM33(c), critic F3: 5.5.1 reads the targets 5.5.4 resolves and asks
        # only 2D-vs-3D, so no route asks "does it ship to web?" beside Question 2.
        shape = section(read(PROJECT_YAML_STEP), SHAPE_STEP) or ""
        missing = []
        asks = [item for item in list_items(shape) if any(m in item for m in OWN_PROMPT_MARKERS)]
        if not asks:
            missing.append(f"{PROJECT_YAML_STEP} {SHAPE_STEP}: no shape question found")
        for item in asks:
            if WEB_WORD in item.lower():
                missing.append(f"{PROJECT_YAML_STEP} {SHAPE_STEP}: the shape question still asks about web: {item!r}")
        paragraphs = re.split(r"\n\s*\n", "\n".join(unquoted(line) for line in shape.splitlines()))
        if not any(all(token in p for token in TARGETS_SOURCE_TOKENS) for p in paragraphs):
            missing.append(f"{PROJECT_YAML_STEP} {SHAPE_STEP}: no paragraph names {TARGETS_SOURCE_TOKENS} as the "
                           f"source of the web/non-web input")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_platform_step_asks_before_each_write(self):
        # AM33(d), critic F6: the lines it mirrors into technical-preferences.md
        # are in the approval, beside the project.yaml block.
        flat = " ".join((platform_step() or "").split())
        approvals = re.findall(r'"May I write[^"]*"', flat)
        self.assertTrue(any(all(f in a for f in APPROVAL_FILES) for a in approvals),
                        f"{PROJECT_YAML_STEP}: no 'May I write' question names {APPROVAL_FILES}: {approvals}")

    def test_xr_target_keeps_keyboard_and_mouse(self):
        # Design D4: yaml-helper.sh matches `pc|web` exactly, so `[PC, XR]`
        # keeps keyboard/mouse. A guard for the existing reader, not new behaviour.
        fixture = {"targets": "[PC, XR]", "gamepad_support": "Partial", "touch_support": "None",
                   "primary_input": "Keyboard/Mouse", "Target Platforms": "PC, XR",
                   "Input Methods": "Keyboard/Mouse, Gamepad"}
        resolved, source = self.input_methods(ENGINE_BLOCK + platform_yaml(fixture, PLATFORM_KEYS), fixture)
        self.assertIn("project.yaml", source)
        self.assertIn(KEYBOARD_MOUSE, resolved)


# AM32(b), design D1, D2, D5 and D6: lighting-artist, an ordinary roster agent
# on every engine, reporting to art-director.
LIGHTING_ARTIST = "lighting-artist"
LIGHTING_SECTION = "Lighting and Look-Dev"
ART_DIRECTOR = "art-director"
ART_DIRECTOR_AGENT = f".claude/agents/{ART_DIRECTOR}.md"
# The art-director item the reporting line sits next to (design D2).
LIGHTING_DIRECTION_ITEM = "**Color and Lighting Direction**"
GRAPHICS_FEATURES = "graphics-features-engineer"
RENDERING_LEAD = "rendering-lead"
CATALOG = "studio-tests/catalog.yaml"
ROSTER = ".claude/docs/agent-roster.md"
INHERIT = "inherit"
CUSTOM_DESCRIPTION = "Custom:"
REPORTS_TO_HEADING = re.compile(r"^#+ Reports to:? (.*)$", re.M)
# The partner table: one row per engine (design D1). Godot, Unity and Unreal
# name their own specialist set; Web has none in engines.tsv and names
# lead-programmer with that reason; Custom names the layout owner and its lead.
PARTNER_SECTION = "Engine-Side Partners"
CUSTOM_ENGINE_ROW = "Custom"
ENGINE_SPECIALIST_PREFIXES = {"Godot": ("godot-",), "Unity": ("unity-",), "Unreal": ("unreal-", "ue-")}
CUSTOM_ROUTE = (GRAPHICS_FEATURES, RENDERING_LEAD)
WEB_ENGINE_ROW = "Web"
WEB_PARTNER = "lead-programmer"
WEB_REASON = "no specialist set"
# The two limits lighting-artist states itself (design D2): direction stays with
# art-director, lighting shaders with technical-artist. technical-artist is not
# edited for lighting.
MUST_NOT_SECTION = "What This Agent Must NOT Do"
LIGHTING_LIMITS = ((ART_DIRECTOR, "lighting direction"), ("technical-artist", "lighting shaders"))
# The seam (design D5): graphics-features-engineer accepts lighting requests in
# its Core Responsibilities.
LIGHTING_ACCEPT_TERM = "lighting request"
# Each sourced fact of the section: its key phrase and the claim that sources
# it (design D6, binding). The claims name the section's file and heading.
LIGHTING_KEY_PHRASES = {
    "EV100": "C169",
    # P11 critic F5: Godot's Practical sensitivity range is in ISO; EV100 is
    # the unit of CameraAttributesPhysical only.
    "Sensitivity in ISO": "C169",
    "physical light units": "C170",
    "Min Brightness": "C171",
    "before the tone mapper": "C172",
    "3D LUT": "C173",
    # AM35(c), score report 5 D2: a phrase that carries each fact's unit or
    # polarity, so reversing the fact beside its topic word fails.
    "measured at ISO 100": "C169",
    "only `CameraAttributesPhysical` sets it in EV100": "C169",
    "HDRP sets light intensities in physical light units": "C170",
    "Godot uses arbitrary units unless the project enables physical light units": "C170",
    "Max Brightness are in cd/m²": "C171",
    "an equal Min Brightness and Max Brightness turns auto exposure off": "C171",
    "Exposure scales the scene before the tone mapper": "C172",
    "other than Linear keeps bright highlights from clipping": "C172",
}
TABLE_SEPARATOR = re.compile(r"^\|[\s|:-]+\|$")
BACKTICKED_NAME = re.compile(r"`([\w-]+)`")
LIST_ITEM_START = re.compile(r"\n(?=\s*(?:[-*+]|\d+\.)\s)")


def file_text(path):
    """A repository file's text, or "" when it does not exist yet."""
    return read(path) if (ROOT / path).is_file() else ""


def table_rows(text):
    """The cells of each body row of the Markdown tables in `text`."""
    rows = []
    for line in (text or "").replace("\r", "").splitlines():
        line = line.strip()
        if not line.startswith("|") or TABLE_SEPARATOR.match(line):
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def prose_units(text):
    """Paragraphs and list items, each folded to one line."""
    return [" ".join(unit.split()) for paragraph in re.split(r"\n\s*\n", (text or "").replace("\r", ""))
            for unit in LIST_ITEM_START.split(paragraph) if unit.strip()]


def agents_on_disk():
    return {p.stem for p in (ROOT / ".claude/agents").glob("*.md")}


def custom_agents():
    return {p.stem for p in (ROOT / CUSTOM_AGENT_SPEC_DIR).glob("*.md")}


def names(text, agents):
    """The agent names in `text`, as whole words."""
    return {a for a in agents if re.search(rf"(?<![\w-]){re.escape(a)}(?![\w-])", text)}


def catalog_spec(agent):
    entry = re.search(rf"^  - name: {re.escape(agent)}\n    spec: (\S+)", file_text(CATALOG).replace("\r", ""), re.M)
    return entry[1] if entry else None


def registration_problems(agent, section, director, director_units):
    """Design D1: what keeps `agent` from being an ordinary roster agent on
    every engine: `model: inherit`, no `Custom:` description, a Reports to
    heading naming `director`, its section in TECHNICAL_SECTIONS, a spec under
    specialists/ with a case per engine route, a catalog entry, one roster row,
    and one of `director_units` (the director's line, AM32(b)) naming it."""
    path, spec_path = f".claude/agents/{agent}.md", f"studio-tests/agents/specialists/{agent}.md"
    missing = []
    text = file_text(path)
    if not text:
        missing.append(f"{path} does not exist")
    head = frontmatter(text)
    model = MODEL_LINE.search(head)
    if not model or model[1] != INHERIT:
        missing.append(f"{path}: model is {model[1] if model else 'unset'}, not {INHERIT}")
    description = re.search(r"^description:\s*\"?(.*)$", head, re.M)
    if not description or description[1].startswith(CUSTOM_DESCRIPTION):
        missing.append(f"{path}: no description, or one that starts with {CUSTOM_DESCRIPTION!r}")
    reports = REPORTS_TO_HEADING.search(text)
    if not reports or f"`{director}`" not in reports[1]:
        missing.append(f"{path}: no Reports to heading naming `{director}`")
    if (path, section) not in {(p, h) for p, h, _ in TECHNICAL_SECTIONS}:
        missing.append(f"TECHNICAL_SECTIONS does not register {path} # {section}")
    found_spec = catalog_spec(agent)
    if found_spec != spec_path:
        missing.append(f"{CATALOG}: the spec of {agent} is {found_spec}, not {spec_path}")
    spec = file_text(spec_path)
    if len(SPEC_CASE_HEADING.findall(spec)) < MIN_SPEC_CASES or not PROTOCOL_SECTION.search(spec):
        missing.append(f"{spec_path}: fewer than {MIN_SPEC_CASES} cases, or no Protocol Compliance section")
    uncovered = sorted(engine_names() - set(case_fixture_engines(spec)))
    if uncovered:
        missing.append(f"{spec_path}: no case whose fixture sets engine.name to {', '.join(uncovered)}")
    roster_rows = [row for row in table_rows(file_text(ROSTER)) if row and row[0] == f"`{agent}`"]
    if len(roster_rows) != 1:
        missing.append(f"{ROSTER}: {len(roster_rows)} roster rows for `{agent}`, not 1")
    if not any(f"`{agent}`" in unit for unit in director_units):
        missing.append(f"`{director}`: no line of its reporting-line place names `{agent}`")
    return missing


def partner_table_problems(agent, custom_route, engine_tools=None):
    """Design D1 and D5: what is wrong with `agent`'s partner table. One row
    per engine: Custom names `custom_route` (the layout owner and its lead);
    Godot, Unity and Unreal their own specialist set and, when given, the
    engine's own tool from `engine_tools`; Web lead-programmer with the reason.
    No Custom agent is named anywhere in the file outside the Custom row."""
    path = f".claude/agents/{agent}.md"
    text = file_text(path)
    rows = {row[0].strip("`* "): row for row in table_rows(section_text(text, PARTNER_SECTION))}
    on_disk, custom = agents_on_disk(), custom_agents()
    missing = []
    for engine in sorted(engine_names()):
        if engine not in rows:
            missing.append(f"{path}: the {PARTNER_SECTION} table has no {engine} row")
    custom_row = " ".join(rows.get(CUSTOM_ENGINE_ROW, []))
    for name in custom_route:
        if f"`{name}`" not in custom_row:
            missing.append(f"{path}: the {CUSTOM_ENGINE_ROW} row does not name `{name}`")
    for engine, prefixes in ENGINE_SPECIALIST_PREFIXES.items():
        row = " ".join(rows.get(engine, []))
        named = set(BACKTICKED_NAME.findall(row)) & on_disk
        if not any(n.startswith(prefixes) for n in named):
            missing.append(f"{path}: the {engine} row names no agent of {engine}'s specialist set")
        tool = (engine_tools or {}).get(engine)
        if tool and tool not in row:
            missing.append(f"{path}: the {engine} row does not name {engine}'s own tool, {tool}")
    web_row = " ".join(rows.get(WEB_ENGINE_ROW, []))
    if f"`{WEB_PARTNER}`" not in web_row or WEB_REASON not in web_row:
        missing.append(f"{path}: the {WEB_ENGINE_ROW} row does not name `{WEB_PARTNER}` "
                       f"with the reason {WEB_REASON!r}")
    outside = text.replace("\r", "")
    for line in outside.splitlines():
        if line.strip().startswith("|") and line.strip("| ").strip("`* ").startswith(CUSTOM_ENGINE_ROW):
            outside = outside.replace(line, "")
    stray = sorted(names(outside, custom))
    if stray:
        missing.append(f"{path}: Custom agents named outside the {CUSTOM_ENGINE_ROW} row: {stray}")
    return missing


def must_not_problems(agent, limits):
    """Design D2: each (owner, phrase) limit that no unit of the agent's "What
    This Agent Must NOT Do" states by naming `owner` for `phrase`."""
    path = f".claude/agents/{agent}.md"
    units = prose_units(section_text(file_text(path), MUST_NOT_SECTION))
    return [f"{path}: no {MUST_NOT_SECTION} item names `{owner}` for {phrase}"
            for owner, phrase in limits if not any(f"`{owner}`" in u and phrase in u.lower() for u in units)]


def check_key_phrases(test, agent, section, key_phrases):
    """Design D6, binding: each sourced fact's key phrase is in the section,
    and its claim names the section's file and heading (one subtest each)."""
    check_path_key_phrases(test, f".claude/agents/{agent}.md", section, key_phrases)


def check_path_key_phrases(test, path, section, key_phrases):
    """check_key_phrases for any repository file (a skill reference too)."""
    body = section_text(file_text(path), section)
    test.assertIsNotNone(body, f"{path} has no ### {section} section")
    claims = {c["claim_id"]: c for c in ledger("claims")}
    flat = " ".join(body.split())
    for phrase, claim_id in key_phrases.items():
        with test.subTest(phrase=phrase, claim=claim_id):
            test.assertIn(phrase, flat)
            claim = claims.get(claim_id, {})
            test.assertEqual((claim.get("file"), claim.get("heading")), (path, section),
                             f"claim {claim_id} does not name {path} # {section}")


class LightingArtistContracts(unittest.TestCase):
    def test_lighting_artist_is_registered_on_every_engine(self):
        # Design D1: an ordinary roster agent, `model: inherit`, no `Custom:`
        # description, a spec under specialists/ with a case per engine route,
        # a catalog entry and a roster line; it reports to art-director, whose
        # lighting-direction item names it (AM32(b)).
        items = [u for u in prose_units(file_text(ART_DIRECTOR_AGENT)) if LIGHTING_DIRECTION_ITEM in u]
        missing = registration_problems(LIGHTING_ARTIST, LIGHTING_SECTION, ART_DIRECTOR, items)
        self.assertEqual(missing, [], "\n".join(missing))

    def test_partner_table_names_each_engines_own_partner(self):
        # Design D1 and D5: one row per engine. Custom names graphics-features-
        # engineer through rendering-lead; Godot, Unity and Unreal their own
        # specialist set; Web lead-programmer with the reason. No Custom agent
        # is named anywhere in the file outside the Custom row.
        missing = partner_table_problems(LIGHTING_ARTIST, CUSTOM_ROUTE)
        self.assertEqual(missing, [], "\n".join(missing))

    def test_graphics_features_engineer_accepts_lighting_requests(self):
        # Design D5: the seam is two-way on Custom. The accepting term sits in
        # graphics-features-engineer's Core Responsibilities, in one item that
        # names lighting-artist.
        found = duty_text(file_text(f".claude/agents/{GRAPHICS_FEATURES}.md"))
        self.assertTrue(found, f"{GRAPHICS_FEATURES} has no duty section")
        items = [u for s in found for u in prose_units(s)]
        self.assertTrue(any(LIGHTING_ARTIST in u and LIGHTING_ACCEPT_TERM in u.lower() for u in items),
                        f"no Core Responsibilities item of {GRAPHICS_FEATURES} names {LIGHTING_ARTIST} "
                        f"and takes {LIGHTING_ACCEPT_TERM!r}")

    def test_graphics_features_engineer_redirects_lighting_values_to_lighting_artist(self):
        # Design D2 (P11 group 3 follow-up): graphics-features-engineer's own
        # redirects must agree with the owner split. Scene lighting, exposure and
        # grading values go to lighting-artist; nothing routes lighting authoring
        # to technical-artist any more.
        text = " ".join(file_text(f".claude/agents/{GRAPHICS_FEATURES}.md").split())
        self.assertNotRegex(text, r"lighting authoring → `technical-artist`",
                            f"{GRAPHICS_FEATURES} still routes lighting authoring to technical-artist")
        redirects = [u for u in re.split(r"(?m)\s- ", text) if "→" in u or "(art-director)" in u]
        self.assertTrue(any(f"`{LIGHTING_ARTIST}`" in u and "exposure" in u and "grading" in u for u in redirects),
                        f"no redirect of {GRAPHICS_FEATURES} sends exposure and grading values to {LIGHTING_ARTIST}")

    def test_lighting_artist_states_both_limits(self):
        # Design D2: one unit of "What This Agent Must NOT Do" names art-director
        # for lighting direction, one names technical-artist for lighting shaders.
        missing = must_not_problems(LIGHTING_ARTIST, LIGHTING_LIMITS)
        self.assertEqual(missing, [], "\n".join(missing))

    def test_lighting_section_holds_its_sourced_key_phrases(self):
        # Design D6, binding: each sourced fact's key phrase is in the section,
        # and its claim names the section's file and heading.
        check_key_phrases(self, LIGHTING_ARTIST, LIGHTING_SECTION, LIGHTING_KEY_PHRASES)


# AM32(b), design D1, D2, D5 and D6: cinematic-designer, an ordinary roster
# agent on every engine, reporting to narrative-director.
CINEMATIC_DESIGNER = "cinematic-designer"
SHOT_SECTION = "Shot Design and Editing"
NARRATIVE_DIRECTOR = "narrative-director"
NARRATIVE_DIRECTOR_AGENT = f".claude/agents/{NARRATIVE_DIRECTOR}.md"
# narrative-director's reporting line sits in its Delegation Map (AM32(b)).
DELEGATION_SECTION = "Delegation Map"
WRITER = "writer"
SEQUENCER_ENGINEER = "cinematics-sequencer-engineer"
SEQUENCER_AGENT = f".claude/agents/{SEQUENCER_ENGINEER}.md"
# The Custom route follows the layout: engine/cinematics/ and engine/camera/
# are cinematics-sequencer-engineer's, under editor-architect
# (custom-engine-layout.md).
CINEMATIC_CUSTOM_ROUTE = (SEQUENCER_ENGINEER, "editor-architect")
# Each engine's own sequencer or timeline tool, as its documentation names it
# (sources S154-S160).
ENGINE_SEQUENCER_TOOLS = {"Godot": "AnimationPlayer", "Unity": "Timeline", "Unreal": "Sequencer"}
# Design D2: story and dialogue stay with narrative-director and writer.
CINEMATIC_LIMITS = ((NARRATIVE_DIRECTOR, "story"), (WRITER, "dialogue"))
# Design D5: cinematics-sequencer-engineer accepts shot requests in its Core
# Responsibilities.
SHOT_ACCEPT_TERM = "shot request"
# Design D2: cinematics-sequencer-engineer's Must NOT line, as the plan words it.
SHOT_CONTENT_REDIRECT = (f"Write shot content (`{CINEMATIC_DESIGNER}`), story or dialogue "
                         f"(`{NARRATIVE_DIRECTOR}`, `{WRITER}`)")
SHOT_CONTENT = "shot content"
SHOT_KEY_PHRASES = {
    "Camera Cuts track": "C174",
    "Cine Camera Actor": "C175",
    "Movie Render Queue": "C176",
    "Timeline asset": "C177",
    "Cinemachine": "C178",
    "AnimationPlayer": "C179",
    # AM35(c), score report 5 D2: phrases that carry each fact.
    "takes control of the camera through its Camera Cuts track": "C174",
    "a Level Sequence of tracks and keyframes": "C174",
    "Filmback, Lens and Focus settings replicate a film camera": "C175",
    "offline with the Movie Render Pipeline": "C176",
    "Movie Render Queue queues those renders from presets": "C176",
    "Each cutscene is a Timeline asset and a Timeline instance": "C177",
    "Cinemachine composes, blends and cuts between camera shots": "C178",
    "it is a separate package": "C178",
    "can key any property of a node": "C179",
    "the `current` property of the next `Camera3D`": "C179",
}


class CinematicDesignerContracts(unittest.TestCase):
    def test_cinematic_designer_is_registered_on_every_engine(self):
        # Design D1: an ordinary roster agent with a spec, catalog entry and
        # roster line; it reports to narrative-director, whose Delegation Map
        # names it (AM32(b)).
        units = prose_units(section_text(file_text(NARRATIVE_DIRECTOR_AGENT), DELEGATION_SECTION))
        missing = registration_problems(CINEMATIC_DESIGNER, SHOT_SECTION, NARRATIVE_DIRECTOR, units)
        self.assertEqual(missing, [], "\n".join(missing))

    def test_partner_table_names_each_engines_sequencer(self):
        # Design D1 and D5: Custom names cinematics-sequencer-engineer through
        # editor-architect, per the layout; Godot, Unity and Unreal their own
        # specialist set and their own tool; Web lead-programmer with the reason.
        missing = partner_table_problems(CINEMATIC_DESIGNER, CINEMATIC_CUSTOM_ROUTE, ENGINE_SEQUENCER_TOOLS)
        self.assertEqual(missing, [], "\n".join(missing))

    def test_cinematic_designer_leaves_story_and_dialogue(self):
        # Design D2: story stays with narrative-director, dialogue with writer.
        missing = must_not_problems(CINEMATIC_DESIGNER, CINEMATIC_LIMITS)
        self.assertEqual(missing, [], "\n".join(missing))

    def test_sequencer_engineer_accepts_shot_requests(self):
        # Design D5: the seam is two-way on Custom. The accepting term sits in
        # cinematics-sequencer-engineer's Core Responsibilities, in one item
        # that names cinematic-designer.
        found = duty_text(file_text(SEQUENCER_AGENT))
        self.assertTrue(found, f"{SEQUENCER_ENGINEER} has no duty section")
        items = [u for s in found for u in prose_units(s)]
        self.assertTrue(any(CINEMATIC_DESIGNER in u and SHOT_ACCEPT_TERM in u.lower() for u in items),
                        f"no Core Responsibilities item of {SEQUENCER_ENGINEER} names {CINEMATIC_DESIGNER} "
                        f"and takes {SHOT_ACCEPT_TERM!r}")

    def test_sequencer_engineer_routes_shot_content_to_cinematic_designer(self):
        # Design D2: the Must NOT line that held "Write shot content, story or
        # dialogue (`narrative-director`, `writer`)" names cinematic-designer
        # for shot content and keeps narrative-director and writer for story
        # and dialogue. It is the only Must NOT unit about shot content.
        units = prose_units(section_text(file_text(SEQUENCER_AGENT), MUST_NOT_SECTION))
        shot_units = [u for u in units if SHOT_CONTENT in u.lower()]
        self.assertEqual(shot_units, [f"- {SHOT_CONTENT_REDIRECT}"],
                         f"{SEQUENCER_AGENT}: the {MUST_NOT_SECTION} units about {SHOT_CONTENT}")

    def test_sequencer_engineer_coordinates_with_the_content_owners(self):
        # Design D2 (P11 group 4 follow-up): the Coordinates-with line names
        # cinematic-designer for cutscene needs and lighting-artist for
        # cinematic lighting; technical-artist keeps the VFX tracks only.
        text = " ".join(file_text(SEQUENCER_AGENT).split())
        line = re.search(r"\*\*Coordinates with:\*\*(.*?)(?:\.\s|$)", text)
        self.assertIsNotNone(line, f"{SEQUENCER_AGENT} has no Coordinates with line")
        self.assertIn("`cinematic-designer`", line[1], "cutscene needs do not name cinematic-designer")
        self.assertRegex(line[1], r"`lighting-artist` on cinematic lighting",
                         "cinematic lighting is not routed to lighting-artist")
        self.assertNotRegex(line[1], r"`technical-artist` on cinematic lighting",
                            "cinematic lighting still goes to technical-artist")

    def test_shot_section_holds_its_sourced_key_phrases(self):
        # Design D6, binding: each sourced fact's key phrase is in the section,
        # and its claim names the section's file and heading.
        check_key_phrases(self, CINEMATIC_DESIGNER, SHOT_SECTION, SHOT_KEY_PHRASES)


# AM32(a) and (b), design D1, D2, D6 and D7: xr-experience-designer, an ordinary
# roster agent on every engine reporting to game-designer, and the VR sections
# of three base agents. VR guidance applies only when the project declares XR.
XR_DESIGNER = "xr-experience-designer"
COMFORT_SECTION = "Comfort and Locomotion"
XR_INTERACTION_SECTION = "XR Interaction"
GAME_DESIGNER = "game-designer"
GAME_DESIGNER_AGENT = f".claude/agents/{GAME_DESIGNER}.md"
# Design D2: the XR runtime stays with platform-engineer and XR rendering with
# graphics-features-engineer, the existing Custom owners.
XR_CUSTOM_ROUTE = ("platform-engineer", GRAPHICS_FEATURES)
# Named one-way by xr-experience-designer; their own files gain no line (design,
# Non-Goals, review cut 1).
XR_PEERS = ("ux-designer", "accessibility-specialist")
COORDINATES_WITH = "Coordinates with"
QA_LEAD_AGENT = ".claude/agents/qa-lead.md"
RELEASE_MANAGER_AGENT = ".claude/agents/release-manager.md"
PERFORMANCE_ANALYST_AGENT = ".claude/agents/performance-analyst.md"
VR_TEST_SECTION = "VR Test Evidence"
VR_STORE_SECTION = "VR Store Certification"
VR_BUDGET_SECTION = "VR Frame Budgets"
XR_SECTIONS = {
    f".claude/agents/{XR_DESIGNER}.md": (COMFORT_SECTION, XR_INTERACTION_SECTION),
    QA_LEAD_AGENT: (VR_TEST_SECTION,),
    RELEASE_MANAGER_AGENT: (VR_STORE_SECTION,),
    PERFORMANCE_ANALYST_AGENT: (VR_BUDGET_SECTION,),
}
# The XR condition each section opens with (spec xr-development, "XR guidance
# applies only to XR projects").
XR_CONDITION = (TARGETS_KEY, "contains", XR_VALUE)
# AM35(c), score report 5 N2: the gate's fixed tail, so an "also applies"
# rewording of the first unit fails.
XR_GATE_TAIL = "on any other project, ignore this section."
# Design D4 and the spec: a flat-screen run is not VR evidence; a frame that
# misses the display deadline is counted, never averaged away; the VR store
# requirements are added to the block platform.cert_tier selects.
FLAT_SCREEN = ("flat-screen", "not VR evidence")
MISSED_DEADLINE = ("missed display deadline", "averag")
REFRESH_RATE_SETTING = "`performance.target_framerate`"
CERT_TIER = ("`platform.cert_tier`", "added to")
# Values with no normative source stay out of agent text (comfort values,
# refresh rates, store thresholds): no number with a unit in these sections.
NUMBER_WITH_UNIT = re.compile(r"\d(?:[\d.,]*\d)?\s*(?:Hz|fps|ms|°|m/s|%)(?![A-Za-z])")
NO_NUMBER_SECTIONS = ((f".claude/agents/{XR_DESIGNER}.md", COMFORT_SECTION),
                      (PERFORMANCE_ANALYST_AGENT, VR_BUDGET_SECTION),
                      (RELEASE_MANAGER_AGENT, VR_STORE_SECTION))
COMFORT_KEY_PHRASES = {
    "Vection": "C180",
    "snap turns": "C181",
    "opt-in": "C182",
    "vignette": "C183",
    "diverse users": "C184",
}
XR_INTERACTION_KEY_PHRASES = {
    "STAGE reference space": "C185",
    "LOCAL reference space": "C186",
    # P11 critic F4: LOCAL is seated-scale; standing play needs the floor
    # (STAGE or LOCAL_FLOOR, core in OpenXR 1.1).
    "seated-scale": "C186",
    "LOCAL_FLOOR": "C186",
    "in meters": "C187",
    "interaction profile": "C188",
    "XR_EXT_hand_tracking": "C189",
    # AM35(c), score report 5 D2: phrases that carry each fact's polarity or
    # unit.
    "Room-scale play uses the STAGE reference space": "C185",
    "Seated play uses the LOCAL reference space": "C186",
    "the STAGE reference space without bounds, or LOCAL_FLOOR": "C186",
    "LOCAL_FLOOR, which OpenXR 1.1 makes core": "C186",
    "A stage is optional in OpenXR": "C186",
    "OpenXR gives physical distances in meters": "C187",
    "grouped into action sets": "C188",
    "binds actions to controls per interaction profile": "C188",
    "Hand tracking is an OpenXR extension": "C189",
    "a runtime may not offer": "C189",
}
VR_TEST_KEY_PHRASES = {
    "positional tracking": "C190",
    "diverse users": "C191",
}
VR_STORE_KEY_PHRASES = {
    "Virtual Reality Check": "C192",
    "VRC.Quest.Performance.1": "C193",
    "test plans": "C194",
    "Standalone Compatibility Review": "C195",
}
VR_BUDGET_KEY_PHRASES = {
    "xrWaitFrame": "C196",
    "predictedDisplayPeriod": "C197",
    "regularly late": "C198",
    "xrEnumerateDisplayRefreshRatesFB": "C199",
    # AM35(c), score report 5 D2: phrases that carry each fact.
    "`xrWaitFrame` paces the frame loop to the display": "C196",
    "`predictedDisplayPeriod`, the display period of the next frame": "C197",
    "the runtime may report one that differs from the hardware's refresh cycle": "C197",
    "regularly late to the compositor as a degraded user experience": "C198",
    "Where the runtime offers `XR_FB_display_refresh_rate`": "C199",
    "the rates a session supports come from `xrEnumerateDisplayRefreshRatesFB`": "C199",
}


def section_units(path, heading):
    return prose_units(section_text(file_text(path), heading))


class XrExperienceDesignerContracts(unittest.TestCase):
    def test_xr_experience_designer_is_registered_on_every_engine(self):
        # Design D1: an ordinary roster agent with a spec, catalog entry and
        # roster line; it reports to game-designer, whose Delegation Map names
        # it (AM32(b)).
        units = prose_units(section_text(file_text(GAME_DESIGNER_AGENT), DELEGATION_SECTION))
        missing = registration_problems(XR_DESIGNER, COMFORT_SECTION, GAME_DESIGNER, units)
        path = f".claude/agents/{XR_DESIGNER}.md"
        if (path, XR_INTERACTION_SECTION) not in {(p, h) for p, h, _ in TECHNICAL_SECTIONS}:
            missing.append(f"TECHNICAL_SECTIONS does not register {path} # {XR_INTERACTION_SECTION}")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_partner_table_names_the_existing_xr_owners(self):
        # Design D1 and D2: Custom names platform-engineer (XR runtime) and
        # graphics-features-engineer (XR rendering); Godot, Unity and Unreal
        # their own specialist set; Web lead-programmer with the reason.
        missing = partner_table_problems(XR_DESIGNER, XR_CUSTOM_ROUTE)
        self.assertEqual(missing, [], "\n".join(missing))

    def test_names_ux_designer_and_accessibility_specialist_one_way(self):
        # Spec xr-development: it names ux-designer and accessibility-specialist
        # as the agents it coordinates with; their files gain no line (design,
        # Non-Goals).
        text = file_text(f".claude/agents/{XR_DESIGNER}.md")
        start = text.find(COORDINATES_WITH)
        tail = text[start:] if start != -1 else ""
        for peer in XR_PEERS:
            with self.subTest(peer=peer):
                self.assertIn(f"`{peer}`", tail, f"{XR_DESIGNER}'s {COORDINATES_WITH} does not name `{peer}`")
                self.assertNotIn(XR_DESIGNER, file_text(f".claude/agents/{peer}.md"),
                                 f"{peer}.md names {XR_DESIGNER}; the reference is one-way")

    def test_comfort_section_holds_its_sourced_key_phrases(self):
        check_key_phrases(self, XR_DESIGNER, COMFORT_SECTION, COMFORT_KEY_PHRASES)

    def test_xr_interaction_section_holds_its_sourced_key_phrases(self):
        check_key_phrases(self, XR_DESIGNER, XR_INTERACTION_SECTION, XR_INTERACTION_KEY_PHRASES)


class VrSectionContracts(unittest.TestCase):
    def test_each_vr_section_opens_with_the_xr_condition(self):
        # Spec xr-development: guidance in the VR sections applies only when
        # `platform.targets` contains `XR`; the section's first unit says so.
        for path, headings in XR_SECTIONS.items():
            for heading in headings:
                with self.subTest(section=f"{path} # {heading}"):
                    units = section_units(path, heading)
                    self.assertTrue(units, f"{path} has no ### {heading} section")
                    self.assertTrue(all(token in units[0] for token in XR_CONDITION),
                                    f"{path} # {heading} does not open with {' '.join(XR_CONDITION)}: "
                                    f"{units[0][:120]!r}")
                    self.assertIn(XR_GATE_TAIL, units[0],
                                  f"{path} # {heading}: the first unit does not end the gate with "
                                  f"{XR_GATE_TAIL!r}")

    def test_no_number_with_a_unit_in_comfort_budget_or_store_text(self):
        # Task 5.2: comfort values, refresh rates and store thresholds come from
        # project settings, ADR options or cited pages, never agent text.
        for path, heading in NO_NUMBER_SECTIONS:
            with self.subTest(section=f"{path} # {heading}"):
                body = section_text(file_text(path), heading)
                self.assertIsNotNone(body, f"{path} has no ### {heading} section")
                self.assertEqual(NUMBER_WITH_UNIT.findall(body), [], f"{path} # {heading} states a number with a unit")

    def test_qa_lead_does_not_accept_flat_screen_runs_as_vr_evidence(self):
        units = section_units(QA_LEAD_AGENT, VR_TEST_SECTION)
        self.assertTrue(any(all(t in u for t in FLAT_SCREEN) for u in units),
                        f"no unit of {QA_LEAD_AGENT} # {VR_TEST_SECTION} holds {FLAT_SCREEN}")

    def test_performance_analyst_counts_missed_display_deadlines(self):
        units = section_units(PERFORMANCE_ANALYST_AGENT, VR_BUDGET_SECTION)
        self.assertTrue(any(all(t in u for t in MISSED_DEADLINE) for u in units),
                        f"no unit of {PERFORMANCE_ANALYST_AGENT} # {VR_BUDGET_SECTION} holds {MISSED_DEADLINE}")
        self.assertTrue(any(REFRESH_RATE_SETTING in u for u in units),
                        f"{VR_BUDGET_SECTION} does not take the refresh rate from {REFRESH_RATE_SETTING}")

    def test_release_manager_adds_vr_store_requirements_to_the_cert_tier_block(self):
        units = section_units(RELEASE_MANAGER_AGENT, VR_STORE_SECTION)
        self.assertTrue(any(all(t in u for t in CERT_TIER) for u in units),
                        f"no unit of {RELEASE_MANAGER_AGENT} # {VR_STORE_SECTION} holds {CERT_TIER}")

    def test_vr_sections_hold_their_sourced_key_phrases(self):
        for agent, heading, phrases in (("qa-lead", VR_TEST_SECTION, VR_TEST_KEY_PHRASES),
                                        ("release-manager", VR_STORE_SECTION, VR_STORE_KEY_PHRASES),
                                        ("performance-analyst", VR_BUDGET_SECTION, VR_BUDGET_KEY_PHRASES)):
            with self.subTest(agent=agent):
                check_key_phrases(self, agent, heading, phrases)


# AM32(a), design D2, D5 and D6: the DCC-to-engine seam and character tech.
# technical-artist states both contracts on every engine; on Custom,
# asset-build-tooling-engineer takes the import side and animation-systems-
# engineer the runtime data contract. Each end names the other and neither
# restates the other.
TECHNICAL_ARTIST = "technical-artist"
TECHNICAL_ARTIST_AGENT = f".claude/agents/{TECHNICAL_ARTIST}.md"
DCC_SECTION = "DCC Interchange"
CHARACTER_SECTION = "Character Technology"
ASSET_BUILD = "asset-build-tooling-engineer"
ANIMATION_SYSTEMS = "animation-systems-engineer"
DCC_IMPORT_SECTION = "DCC Import"
CHARACTER_CONTRACT_SECTION = "Character Data Contract"
# The seams (design D5): (shared end, its section, Custom end, its section, the
# term the Custom end's Core Responsibilities accept).
CONTENT_SEAMS = (
    (TECHNICAL_ARTIST, DCC_SECTION, ASSET_BUILD, DCC_IMPORT_SECTION, "dcc import"),
    (TECHNICAL_ARTIST, CHARACTER_SECTION, ANIMATION_SYSTEMS, CHARACTER_CONTRACT_SECTION, "character data contract"),
)
# The distinctive tokens of task 6.2, each absent from its file at 4b4aaea.
SEAM_TOKENS = ((TECHNICAL_ARTIST, DCC_SECTION, "up-axis"), (ANIMATION_SYSTEMS, CHARACTER_CONTRACT_SECTION, "blendshape"))
# Design D2: the DCC section extends Key Responsibilities items 4 (Art
# Pipeline) and 6 (naming) by reference, without restating them.
KEY_RESPONSIBILITIES = "Key Responsibilities"
REFERENCED_ITEMS = ("4", "6")
NUMBERED_ITEM = re.compile(r"^(\d+)\.\s+\*\*[^*]+\*\*:?\s*(.*)$")
DCC_KEY_PHRASES = {
    "linear distances in meters": "C200",
    "+Y up": "C201",
    "`upAxis`": "C202",
    "`metersPerUnit`": "C203",
    "UsdGeom stipulates a right-handed coordinate system": "C204",
    "`FbxAxisSystem`": "C205",
    "glTF-Validator": "C206",
    "`usdchecker`": "C207",
    # AM35(c), score report 5 D2: phrases that carry each fact's unit, axis or
    # polarity.
    "a right-handed coordinate system with +Y up and +Z forward": "C201",
    "`upAxis` (`Y` or `Z`)": "C202",
    "asks exporters to always author `upAxis`": "C202",
    "no authored `metersPerUnit` falls back to centimeters": "C203",
    "`FbxAxisSystem`, which includes the handedness": "C205",
    "unit from the file's settings": "C205",
    "glTF-Validator for glTF, which writes a report of the issues it finds": "C206",
    "`usdchecker` for USD": "C207",
}
CHARACTER_KEY_PHRASES = {
    "inverse bind matrices": "C208",
    "`JOINTS_0`": "C209",
    "morph targets": "C210",
    "`BlendShape`": "C211",
    # AM35(c), score report 5 D2: phrases that carry each fact.
    "optional inverse bind matrices whose order must match that joint list": "C208",
    "stores four joint influences per set": "C209",
    "a set of difference values for a primitive's vertex attributes": "C210",
    "`BlendShape` prims, which may carry inbetween shapes": "C211",
}
DCC_IMPORT_KEY_PHRASES = {
    "`UsdGeomGetStageUpAxis`": "C212",
    "`UsdGeomStageHasAuthoredMetersPerUnit`": "C213",
    # P11 critic F9: the unit's fallback is the fixed centimeters value, not a
    # site setting.
    "`UsdGeomLinearUnits::centimeters`": "C213",
    "`GetSystemUnit`": "C214",
    # AM35(c), score report 5 D2: phrases that carry each fact.
    "a site-level fallback that a `plugInfo.json` file can change": "C212",
    "the fixed fallback `UsdGeomLinearUnits::centimeters`": "C213",
    "global settings (`GetAxisSystem`, `GetSystemUnit`)": "C214",
}
CHARACTER_CONTRACT_KEY_PHRASES = {
    "weighted sum": "C215",
    "`JOINTS_1`": "C216",
    "as close as reasonably possible to 1.0": "C217",
    "`skel:blendShapeTargets`": "C218",
    # AM35(c), score report 5 D2: phrases that carry each fact.
    "adds a weighted sum of its targets' offsets to the base": "C215",
    "beyond the first four into further sets (`JOINTS_1` with `WEIGHTS_1`)": "C216",
    "bound to a mesh through `skel:blendShapeTargets`": "C218",
}
# Each section's key phrases, so the two ends of a seam can be checked for
# restating each other's sourced facts.
SECTION_KEY_PHRASES = {
    (TECHNICAL_ARTIST, DCC_SECTION): DCC_KEY_PHRASES,
    (TECHNICAL_ARTIST, CHARACTER_SECTION): CHARACTER_KEY_PHRASES,
    (ASSET_BUILD, DCC_IMPORT_SECTION): DCC_IMPORT_KEY_PHRASES,
    (ANIMATION_SYSTEMS, CHARACTER_CONTRACT_SECTION): CHARACTER_CONTRACT_KEY_PHRASES,
}


def agent_section(agent, heading):
    return section_text(file_text(f".claude/agents/{agent}.md"), heading)


def item_phrases(text):
    """The listed phrases of a numbered Key Responsibilities item: the part
    after its `--`, split at commas and the final "and"."""
    tail = text.split("--", 1)[1] if "--" in text else ""
    parts = re.split(r",\s*|\s+and\s+", tail.strip().rstrip("."))
    return [p.strip().lower() for p in parts if p.strip()]


class DccAndCharacterTechContracts(unittest.TestCase):
    def test_each_seam_is_two_way_with_the_term_in_core_responsibilities(self):
        # Design D5: the shared section names the Custom end; the Custom end's
        # section names technical-artist; the Custom end's Core
        # Responsibilities hold the accepting term in an item naming
        # technical-artist.
        for shared, section, custom, custom_section, term in CONTENT_SEAMS:
            with self.subTest(seam=f"{shared} # {section} <-> {custom} # {custom_section}"):
                missing = []
                body = agent_section(shared, section)
                if body is None:
                    missing.append(f"{shared} has no ### {section} section")
                elif f"`{custom}`" not in body:
                    missing.append(f"{shared} # {section} does not name `{custom}`")
                other = agent_section(custom, custom_section)
                if other is None:
                    missing.append(f"{custom} has no ## {custom_section} section")
                elif f"`{shared}`" not in other:
                    missing.append(f"{custom} # {custom_section} does not name `{shared}`")
                duties = section_text(file_text(f".claude/agents/{custom}.md"), PRIMARY_DUTY_SECTION)
                items = prose_units(duties)
                if not any(shared in u and term in u.lower() for u in items):
                    missing.append(f"no Core Responsibilities item of {custom} names {shared} and takes {term!r}")
                self.assertEqual(missing, [], "\n".join(missing))

    def test_distinctive_tokens_are_in_their_sections(self):
        # Task 6.2: `up-axis` in technical-artist's DCC section, `blendshape` in
        # animation-systems-engineer's character data contract.
        for agent, section, token in SEAM_TOKENS:
            with self.subTest(agent=agent, token=token):
                body = agent_section(agent, section)
                self.assertIsNotNone(body, f"{agent} has no {section} section")
                self.assertIn(token, body.lower(), f"{agent} # {section} does not hold {token!r}")

    def test_dcc_section_refers_to_items_4_and_6_without_restating_them(self):
        # Design D2: the section's first unit names Key Responsibilities items
        # 4 and 6; no phrase those items list appears in the section.
        text = file_text(TECHNICAL_ARTIST_AGENT)
        body = section_text(text, DCC_SECTION)
        self.assertIsNotNone(body, f"{TECHNICAL_ARTIST} has no ### {DCC_SECTION} section")
        first = prose_units(body)[0]
        self.assertIn(KEY_RESPONSIBILITIES, first, f"the first unit does not refer to {KEY_RESPONSIBILITIES}")
        for item in REFERENCED_ITEMS:
            self.assertRegex(first, rf"(?<![\d.]){item}(?![\d.]\d)", f"the first unit does not name item {item}")
        items = {}
        for unit in prose_units(section_text(text, KEY_RESPONSIBILITIES)):
            numbered = NUMBERED_ITEM.match(unit)
            if numbered:
                items[numbered[1]] = numbered[2]
        flat = " ".join(body.split()).lower()
        for item in REFERENCED_ITEMS:
            phrases = item_phrases(items.get(item, ""))
            self.assertTrue(phrases, f"Key Responsibilities item {item} lists no phrase")
            with self.subTest(item=item):
                self.assertEqual([p for p in phrases if p in flat], [],
                                 f"the {DCC_SECTION} section restates item {item}")

    def test_seam_ends_do_not_restate_each_other(self):
        # Spec content-production: neither end restates the other. No sourced
        # key phrase of one end appears in the other end's section.
        for shared, section, custom, custom_section, _ in CONTENT_SEAMS:
            for (owner, heading), (other, other_heading) in (((shared, section), (custom, custom_section)),
                                                              ((custom, custom_section), (shared, section))):
                with self.subTest(owner=f"{owner} # {heading}", other=f"{other} # {other_heading}"):
                    body = " ".join((agent_section(other, other_heading) or "").split())
                    restated = [p for p in SECTION_KEY_PHRASES[(owner, heading)] if p in body]
                    self.assertEqual(restated, [], f"{other} # {other_heading} restates {owner}'s facts")

    def test_sections_hold_their_sourced_key_phrases(self):
        # Design D6, binding: each sourced fact's key phrase is in its section,
        # and its claim names the section's file and heading.
        for (agent, heading), phrases in SECTION_KEY_PHRASES.items():
            with self.subTest(section=f"{agent} # {heading}"):
                check_key_phrases(self, agent, heading, phrases)


# AM35(c), score report 5 D2: every API-fact (Q9b kind a) claim Phase 11 added
# is bound to a phrase in its section, guided Question 2's included.
GUIDED_CHOICE_SECTION = "Help me choose"
GUIDED_KEY_PHRASES = {"the question tool takes four options": "C168"}
API_FACT_KIND = "API fact"
FIRST_PHASE11_CLAIM, LAST_PHASE11_CLAIM = 168, 218
ALL_KEY_PHRASES = (LIGHTING_KEY_PHRASES, SHOT_KEY_PHRASES, COMFORT_KEY_PHRASES, XR_INTERACTION_KEY_PHRASES,
                   VR_TEST_KEY_PHRASES, VR_STORE_KEY_PHRASES, VR_BUDGET_KEY_PHRASES, GUIDED_KEY_PHRASES,
                   *SECTION_KEY_PHRASES.values())


class Phase11ApiFactsAreBound(unittest.TestCase):
    def test_guided_choice_holds_its_sourced_key_phrase(self):
        check_path_key_phrases(self, GUIDED_MODE, GUIDED_CHOICE_SECTION, GUIDED_KEY_PHRASES)

    def test_every_phase11_api_fact_claim_is_bound_to_a_key_phrase(self):
        bound = {claim_id for phrases in ALL_KEY_PHRASES for claim_id in phrases.values()}
        unbound = [c["claim_id"] for c in ledger("claims")
                   if FIRST_PHASE11_CLAIM <= int(c["claim_id"][1:]) <= LAST_PHASE11_CLAIM
                   and c.get("kind", "").startswith(API_FACT_KIND) and c["claim_id"] not in bound]
        self.assertEqual(unbound, [], f"API-fact claims with no key phrase: {unbound}")


# Task 7.1 (design D8, spec roster-integrity "Every shipped agent is
# registered"): the published agent lists, each checked against the agents on
# disk. An agent's tier is the folder its catalog spec sits in under
# AGENT_SPEC_ROOT; its rubric category is its catalog `category:`.
AGENT_SPEC_ROOT = "studio-tests/agents/"
README = "README.md"
README_TREE_HEADING = "Studio Hierarchy"
# README's tree leaves out the Godot, Unity and Unreal sets: its "Engine
# Specialists" table names each set by its lead agent and its sub-specialists
# by domain ("GDScript, Shaders, GDExtension"), so the tree claims every agent
# outside those three sets.
README_TREE_OMITS_TIERS = ("engine/godot", "engine/unity", "engine/unreal")
WORKFLOW_GUIDE = "docs/WORKFLOW-GUIDE.md"
GUIDE_TREE_HEADING = "Agent Coordination (3-Tier Hierarchy)"
GUIDE_TABLE_HEADING = '"I need to do X -- which agent do I use?"'
# Not checked: the guide's "Agent Hierarchy" sketch (Appendix A), which names
# departments by abbreviation ("lead-prog", "tech-art") and is not a list of
# agents; its Custom tree is checked by test_new_item_lists_match_disk.
STUDIO_TESTS_GUIDE = "studio-tests/CLAUDE.md"
STUDIO_TESTS_README = "studio-tests/README.md"
QUALITY_RUBRIC = "studio-tests/quality-rubric.md"
AGENT_TIERS_HEADING = "Agent tiers"
TIER_LINE = re.compile(r"^([\w/]+)\s+→(.*)$")
TIER_ROW = re.compile(r"^\| `([\w/]+)` \|(.*)\|\s*$", re.M)
# studio-tests/README.md's folder tree: one line per agents/ folder, "├── <dir>/
# ← <its agents>". The engine/ folder's lines describe each engine's set
# ("Godot-specific specialists"); the tier table names those agents.
SPEC_TREE_ROOT = re.compile(r"^[├└]── agents/")
SPEC_TREE_CHILD = re.compile(r"^│   [├└]── ([\w-]+)/\s+← (.*)$")
SPEC_TREE_DESCRIBED_TIER = "engine"
RUBRIC_CATEGORY = re.compile(r"^### `(\w+)`\s*\n\s*\*\*Agents\*\*:(.*(?:\n[^\n|#*].*)*)", re.M)
CODE_BLOCK = re.compile(r"^```[^\n]*\n(.*?)^```", re.M | re.S)


def catalog_agents():
    """{agent: (tier, category)} from the `agents:` part of the catalog."""
    agents_part = file_text(CATALOG).replace("\r", "").split("\nagents:", 1)[-1]
    found = {}
    for entry in re.finditer(r"^  - name: ([\w-]+)\n((?:    .*\n?)*)", agents_part, re.M):
        spec = re.search(r"^    spec: (\S+)", entry[2], re.M)
        category = re.search(r"^    category: (\w+)", entry[2], re.M)
        tier = spec[1][len(AGENT_SPEC_ROOT):].rpartition("/")[0] if spec and spec[1].startswith(AGENT_SPEC_ROOT) else None
        found[entry[1]] = (tier, category[1] if category else None)
    return found


def grouped_names(lines, head):
    """{group: names} from lines where `head` opens a group (its match gives the
    group and the rest of the line) and lines that do not continue it."""
    groups, current = {}, None
    for line in lines:
        opened = head.match(line)
        if opened:
            current, line = opened[1], opened[2]
        if current:
            groups.setdefault(current, set()).update(re.findall(r"[a-z][\w-]*[a-z]", line))
    return groups


def agent_list_problems():
    """Each (list, agent) where an agent on disk is missing from a published
    agent list, as one line per list naming the missing agents."""
    on_disk, registry = agents_on_disk(), catalog_agents()
    tier = {a: registry.get(a, (None, None))[0] for a in on_disk}
    category = {a: registry.get(a, (None, None))[1] for a in on_disk}
    problems = []

    def require(place, expected, present):
        missing = sorted(a for a in expected if not present(a))
        if missing:
            problems.append(f"{place}: missing {', '.join(missing)}")

    readme_tree = CODE_BLOCK.search(section_text(file_text(README).replace("\r", ""), README_TREE_HEADING) or "")
    require(f"{README} ({README_TREE_HEADING} tree)", {a for a in on_disk if tier[a] not in README_TREE_OMITS_TIERS},
            lambda a: a in names(readme_tree[1] if readme_tree else "", on_disk))
    guide = file_text(WORKFLOW_GUIDE).replace("\r", "")
    guide_trees = "\n".join(CODE_BLOCK.findall(section_text(guide, GUIDE_TREE_HEADING) or ""))
    require(f"{WORKFLOW_GUIDE} ({GUIDE_TREE_HEADING} trees)", on_disk, lambda a: a in names(guide_trees, on_disk))
    table_agents = {n for row in table_rows(section_text(guide, GUIDE_TABLE_HEADING)) if len(row) > 1
                    for n in BACKTICKED_NAME.findall(row[1])}
    require(f"{WORKFLOW_GUIDE} ({GUIDE_TABLE_HEADING} table)", on_disk, lambda a: a in table_agents)
    tiers_block = CODE_BLOCK.search(section_text(file_text(STUDIO_TESTS_GUIDE).replace("\r", ""),
                                                 AGENT_TIERS_HEADING) or "")
    tier_lines = grouped_names(tiers_block[1].splitlines() if tiers_block else [], TIER_LINE)
    require(f"{STUDIO_TESTS_GUIDE} ({AGENT_TIERS_HEADING} block, on its tier's line)", on_disk,
            lambda a: a in tier_lines.get(tier[a], set()))
    studio_readme = file_text(STUDIO_TESTS_README).replace("\r", "")
    tier_rows = {t: set(re.findall(r"[a-z][\w-]*[a-z]", cell))
                 for t, cell in TIER_ROW.findall(section_text(studio_readme, AGENT_TIERS_HEADING) or "")}
    require(f"{STUDIO_TESTS_README} ({AGENT_TIERS_HEADING} table, in its tier's row)", on_disk,
            lambda a: a in tier_rows.get(tier[a], set()))
    tree_lines, inside = [], False
    for line in studio_readme.splitlines():
        if SPEC_TREE_ROOT.match(line):
            inside = True
        elif inside and not line.startswith("│   "):
            break
        elif inside:
            tree_lines.append(line)
    folders = grouped_names(tree_lines, SPEC_TREE_CHILD)
    require(f"{STUDIO_TESTS_README} (agents/ folder tree, on its folder's line)",
            {a for a in on_disk if tier[a] and tier[a].split("/")[0] != SPEC_TREE_DESCRIBED_TIER},
            lambda a: a in folders.get(tier[a], set()))
    rubric = {c: set(re.findall(r"[a-z][\w-]*[a-z]", body))
              for c, body in RUBRIC_CATEGORY.findall(file_text(QUALITY_RUBRIC).replace("\r", ""))}
    require(f"{QUALITY_RUBRIC} (its catalog category's Agents list)", on_disk,
            lambda a: a in rubric.get(category[a], set()))
    return problems


class EveryAgentIsInEveryList(unittest.TestCase):
    def test_every_agent_on_disk_is_in_every_published_agent_list(self):
        # Task 7.1 (spec roster-integrity): derived from .claude/agents/, so an
        # agent added later fails here until every list names it.
        on_disk, registry = agents_on_disk(), catalog_agents()
        with self.subTest(check="every agent has a catalog tier and category"):
            self.assertEqual(sorted(a for a in on_disk if None in registry.get(a, (None, None))), [])
        problems = agent_list_problems()
        self.assertEqual(problems, [], "\n".join(problems))


class VrGenreCardIsTrue(unittest.TestCase):
    def test_vr_card_names_the_route_and_limits_itself_to_the_one_shot(self):
        # P11 group 5 follow-up (Acceptance 7): the one-shot's VR card line said
        # the framework has no route for VR. After AM32 it has one (the XR
        # target and xr-experience-designer); the one-shot itself still builds
        # flat, so the card limits its claim to the one-shot and names the route.
        text = " ".join(file_text(".claude/genres/online-and-devices.md").split())
        card = re.search(r"`Platform: VR:[^`]*`", text)
        self.assertIsNotNone(card, "online-and-devices.md has no `Platform: VR:` card line")
        self.assertNotIn("has no route for VR", card[0], "the card still says the framework has no route for VR")
        self.assertIn("one-shot", card[0], "the card does not limit its claim to the one-shot")
        self.assertIn("/setup-engine", card[0], "the card does not name the route for a VR game")
        self.assertIn("XR", card[0], "the card does not name the XR target")


# AM32(e), spec studio-roles/roster-integrity: every addition other engines can
# observe is named in UPGRADING's "Other engines" row and in CHANGELOG's
# Unreleased section. Distinctive tokens, one per AM32 addition.
CR, NL = chr(13), chr(10)
AM32_DISCLOSURE_TOKENS = (
    "lighting-artist", "cinematic-designer", "xr-experience-designer",
    "DCC Interchange", "Character Technology", "VR Test Evidence", "VR Store Certification", "VR Frame Budgets",
    "`platform.targets`", "`gamepad_support`", "`touch_support`", "`primary_input`", "online-and-devices.md",
)
# AM35(c), score report 5 N2: the same for each AM33 and AM34 addition, and
# AM35(b)'s WORKFLOW-GUIDE row, one distinctive token each.
LATER_DISCLOSURE_TOKENS = {
    "AM33(a) existing platform keys win": "already in `project.yaml`",
    "AM33(b) Input Methods reconciliation": "asks once which is right",
    "AM33(c) Godot shape question": "2D or 3D",
    "AM33(d) approval names technical-preferences.md": "names `technical-preferences.md`",
    "AM33(e) /security-audit note": "`platform.multiplayer`",
    "AM34 methods the keys cannot give": "the four keys cannot give",
    "AM34 the template's Mixed": "`Mixed`",
    "AM35(b) WORKFLOW-GUIDE row": "`godot-csharp-specialist`",
}


def disclosure_problems(upgrading, changelog, tokens=AM32_DISCLOSURE_TOKENS):
    """Tokens missing from UPGRADING's Other engines row or CHANGELOG's Unreleased section."""
    from test_engine_support import RELEASE_NOTE_SECTIONS
    problems = []
    section = RELEASE_NOTE_SECTIONS["UPGRADING.md"].search(upgrading)
    row = next((l for l in (section[0] if section else "").splitlines() if l.startswith("| **Other engines** |")), "")
    if not row:
        problems.append("UPGRADING.md: no Other engines row in the Unreleased section")
    log = RELEASE_NOTE_SECTIONS["CHANGELOG.md"].search(changelog)
    log_text = " ".join((log[0] if log else "").split())  # markdown wraps lines
    for token in tokens:
        if row and token not in row:
            problems.append(f"UPGRADING.md Other engines row does not name {token}")
        if token not in log_text:
            problems.append(f"CHANGELOG.md Unreleased section does not name {token}")
    return problems


class Am32DisclosureIsComplete(unittest.TestCase):
    def test_every_am32_addition_is_named_in_the_release_notes(self):
        problems = disclosure_problems(file_text("UPGRADING.md").replace(CR, ""),
                                       file_text("CHANGELOG.md").replace(CR, ""))
        self.assertEqual(problems, [], NL.join(problems))

    def test_every_am33_to_am35_addition_is_named_in_the_release_notes(self):
        problems = disclosure_problems(file_text("UPGRADING.md").replace(CR, ""),
                                       file_text("CHANGELOG.md").replace(CR, ""),
                                       tuple(LATER_DISCLOSURE_TOKENS.values()))
        self.assertEqual(problems, [], NL.join(problems))


if __name__ == "__main__":
    unittest.main()
