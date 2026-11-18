"""Structural contracts of fix plan Phase 12 (section 14, amendment AM36).

Run: python -m unittest discover -s studio-tests -p test_engine_phase12.py -v
The plan is the OpenSpec change `add-custom-engine-xr-numerics-demo`: what only
a project that builds its own engine (`engine.name: Custom`) needs. These check
files on disk, not Claude's behaviour in a session.
"""
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shared_hunks as sh  # noqa: E402
from test_engine_support import (  # noqa: E402
    COUNT_PHRASE, RELEASE_NOTE_SECTIONS, ROOT, TECHNICAL_SECTIONS, ledger, section_text)
from test_engine_phase11 import (  # noqa: E402
    NUMBER_WITH_UNIT, XR_CONDITION, XR_GATE_TAIL, agents_on_disk, check_path_key_phrases, disclosure_problems,
    file_text, names, prose_units)

# Design D7 and spec xr-runtime-contracts: the Custom XR contracts. Each
# section opens with part 1's XR gate sentence; the agents are Custom-only, so
# the agent file is the Custom gate.
PLATFORM_AGENT = ".claude/agents/platform-engineer.md"
AUDIO_AGENT = ".claude/agents/audio-engine-engineer.md"
FRAME_BUDGET_TEMPLATE = ".claude/docs/templates/frame-budget.md"
FRAME_BUDGET_GATE = ".claude/docs/director-gates/cea-frame-budget.md"
PLATFORM_XR_SECTION = "XR Platform Options"
AUDIO_XR_SECTION = "XR Audio Listener"
TEMPLATE_XR_SECTION = "XR — display-locked frame"
XR_RUNTIME_SECTIONS = ((PLATFORM_AGENT, PLATFORM_XR_SECTION), (AUDIO_AGENT, AUDIO_XR_SECTION),
                       (FRAME_BUDGET_TEMPLATE, TEMPLATE_XR_SECTION))
# Score report 6, N2(c): the whole fixed gate sentence, so a widened
# condition ("contains `XR` or `PC`") fails, not only a missing token.
XR_GATE_SENTENCE = ("Applies only when `platform.targets` in `project.yaml` contains `XR` (matched without "
                    "regard to case); on any other project, ignore this section.")
# Design D4: the distinctive token of each file, absent before task 2.3.
PASSTHROUGH = "passthrough"
HEAD_POSE = "head pose"
MISSED_DEADLINE = "missed display deadline"
XR_TOKENS = ((PLATFORM_AGENT, PASSTHROUGH), (AUDIO_AGENT, HEAD_POSE),
             (FRAME_BUDGET_TEMPLATE, MISSED_DEADLINE), (FRAME_BUDGET_GATE, MISSED_DEADLINE))
# platform-engineer: standalone headsets and passthrough are ADR options; the
# ADR, not the agent, records the device's GPU class, thermal limits and
# refresh rates. Its existing XR bullet in Core Responsibilities points to the
# section (design D1(f)), and rendering facts stay with graphics-features.
CORE_RESPONSIBILITIES = "Core Responsibilities"
PLATFORM_XR_BULLET = "XR through OpenXR"
ADR_OPTION = "ADR option"
STANDALONE_HEADSET = "standalone headset"
DEVICE_FACTS_IN_THE_ADR = ("ADR", "GPU class", "thermal limits", "refresh rates")
RENDERING_OWNER = "`graphics-features-engineer`"
# audio-engine-engineer: an ADR records the XrTime at which the head pose is
# located for the listener; platform-engineer supplies the pose.
LISTENER_TIME_ADR = ("ADR", "`XrTime`", HEAD_POSE)
POSE_SUPPLIER = ("`platform-engineer`", "supplies the head pose")
# The template: the refresh rate comes from project.yaml, the budget is
# performance-analyst's, and what the display shows after a miss is
# runtime-defined (design D5, NOT SOURCEABLE in the core specification).
REFRESH_RATE_SETTING = "`performance.target_framerate`"
VR_BUDGET_POINTER = ("`performance-analyst`", "VR Frame Budgets")
AFTER_A_MISS = (MISSED_DEADLINE, "runtime-defined", "NOT SOURCEABLE")
# The gate: one NOT ASSESSED bullet for an XR project with the refresh rate
# unset; chief-engine-architect reads platform.targets itself, so the
# Verdicts line and the spawners stay as they are.
NOT_ASSESSED_HEAD = "**NOT ASSESSED when**"
GATE_XR_TOKENS = ("`platform.targets`", "`XR`", REFRESH_RATE_SETTING, "`project.yaml`")
# Score report 6, N2(a): the bullet's fixed condition, so a flipped polarity
# ("is set") fails while the four tokens stay.
GATE_XR_CONDITION = ("`platform.targets` in `project.yaml` contains `XR` and `performance.target_framerate` "
                     "is unset, so no frame can be judged against its missed display deadline")
VERDICTS_LINE = "**Verdicts**: APPROVE / CONCERNS / REJECT"

# Design D5, binding (AM35(c)): each sourced fact's key phrase, carrying its
# unit or polarity, bound to the claim of its section.
PLATFORM_XR_KEY_PHRASES = {
    "`XR_ENVIRONMENT_BLEND_MODE_ALPHA_BLEND`": "C219",
    "the typical environment blend mode for video passthrough": "C219",
    "alpha-blended with the real world behind the display": "C219",
    "`XR_ENVIRONMENT_BLEND_MODE_OPAQUE`": "C220",
    "shows no view of the physical world": "C220",
}
AUDIO_XR_KEY_PHRASES = {
    "`XR_REFERENCE_SPACE_TYPE_VIEW`": "C221",
    "tracks the view origin of the primary viewer": "C221",
    "every OpenXR runtime supports it": "C221",
    "`xrLocateSpace` locates a space at a time the caller passes": "C222",
    "`predictedDisplayTime` (the anticipated display time of the next frame)": "C223",
}
TEMPLATE_XR_KEY_PHRASES = {
    "only frames whose `xrBeginFrame` and `xrEndFrame` both succeed are composed": "C224",
    "`XR_FRAME_DISCARDED`": "C225",
    "the frame begun before it is forfeited": "C225",
    "`xrWaitFrame` may return immediately": "C226",
    "may change the throttling of `xrWaitFrame` in response to frame submission": "C227",
}
SECTION_KEY_PHRASES = {
    (PLATFORM_AGENT, PLATFORM_XR_SECTION): PLATFORM_XR_KEY_PHRASES,
    (AUDIO_AGENT, AUDIO_XR_SECTION): AUDIO_XR_KEY_PHRASES,
    (FRAME_BUDGET_TEMPLATE, TEMPLATE_XR_SECTION): TEMPLATE_XR_KEY_PHRASES,
}
# Design D5 and spec numerics-and-research: the math owner names each numeric
# guarantee as an ADR decision, and an undecided guarantee is an open option.
MATH_AGENT = ".claude/agents/ecs-dod-architect.md"
MATH_RULE = ".claude/rules/ecs-math-code.md"
LEVEL_EDITOR_AGENT = ".claude/agents/level-editor-engineer.md"
STREAMING_AGENT = ".claude/agents/world-streaming-engineer.md"
NUMERICS_SECTION = "Numerics"
ADR = "ADR"
NUMERICS_DECISIONS = ("precision per type", "large-world strategy", "transcendental accuracy",
                      "quaternion renormalization", "near-singular inversion", "robust geometric predicates")
OPEN_OPTION = ("open option", "never a default")
# No primary text states a renormalization interval or an inversion
# threshold, so these two decisions carry no number at all.
NO_NUMBER_DECISIONS = ("quaternion renormalization", "near-singular inversion")
DIGIT = re.compile(r"\d")
# A compiler default is named with its compiler and the version or manual its
# source states (design D5).
COMPILER_DEFAULT = re.compile(r"\bby default\b|\bdefaults? to\b|\bthe default\b|'s default\b", re.I)
COMPILER_NAME = re.compile(r"\b(?:MSVC|GCC|Clang)\b|clang-cl")
COMPILER_SOURCE = re.compile(r"\bVisual Studio \d{4}\b|\bmanual\b")
SENTENCE_BREAK = re.compile(r"(?<=\.)(?<!e\.g\.)(?<!i\.e\.)\s+(?=[A-Z`*])")
# The rule: each math function states a ULP bound or a tolerance, beside the
# existing rule for tests.
RULE_SECTION = "Math"
ULP = "ULP"
RULE_ACCURACY = ("ULP bound", "tolerance", "math function")
RULE_TEST_TOLERANCE = "Floating-point comparisons in tests use a stated tolerance, never `==`"
# Design D1(b): one owner for the large-world decision. The editor keeps its
# rule, which now reads as applying the ADR; streaming gains one line.
LARGE_WORLD_ADR = "the large-world ADR owned by `ecs-dod-architect`"
# Score report 6, N2(b): each applier says it does not choose a strategy, so
# a second owner of the decision fails.
EDITOR_NO_STRATEGY = "the editor does not choose a strategy of its own"
STREAMING_NO_STRATEGY = "streaming applies it and does not choose a strategy"
# Design D5: each large-world option the vendors document comes with its cost,
# sourced or NOT SOURCEABLE (double precision, origin shifting, camera-relative).
LARGE_WORLD_BULLET = "Large-world strategy"
LARGE_WORLD_COSTS = ("performance and memory usage penalty", "adds complexity to game logic",
                     "cost of camera-relative rendering: NOT SOURCEABLE")
EDITOR_VIEWPORT_SECTION = "Viewport"
EDITOR_LARGE_WORLD_BULLET = "Large worlds:"
EDITOR_RULE_TEXT = ("camera-relative rendering and gizmo math in double precision or camera-relative float; "
                    "never feed absolute far-from-origin floats to the GPU.")
NUMERICS_KEY_PHRASES = {
    "the accuracy of floating-point operations is implementation-defined": "C228",
    "`std::numeric_limits<T>::is_iec559`": "C229",
    "true only for a type that adheres to ISO/IEC 60559": "C229",
    "does not round the intermediate product": "C230",
    "Rust's `f32::mul_add` rounds once": "C230",
    "MSVC's `/fp:precise` defaults to `fp_contract(off)`": "C231",
    "clang-cl's `/fp:precise` keeps contraction on": "C231",
    "MSVC's `/fp:fast` enables `/fp:contract` by default": "C232",
    "`-ffp-contract=fast`": "C233",
    "except for C in a standards-compliant mode": "C233",
    "by default (`-ffp-contract=on`)": "C234",
    "units of the last place": "C235",
    "does not aim for correctly rounded results": "C235",
    "except for certain functions such as `sqrt`, `fma` and `rint`": "C235",
    "the accuracy of some math functions in ULP": "C236",
    "is non-deterministic": "C237",
    "varies by platform and Rust version": "C237",
    "bounds the precision of many shader operations in ULP, not as an exact result": "C238",
    "picks FMA3 or non-FMA3 implementations by CPU": "C239",
    "increase the precision of all the engine's floating-point computations": "C240",
    "performance and memory usage penalty": "C240",
    "origin shifting": "C241",
    "works with single-precision floats but adds complexity to game logic, especially in multiplayer": "C241",
    "lets you set most material nodes": "C242",
    "Camera Relative World Position": "C242",
    "for precision and performance": "C242",
    "can give a wrong result when the true determinant is near zero": "C243",
    "only as much work as a correct result needs": "C243",
}

# Design D1(c), D3 and spec numerics-and-research: the research route. Engine
# research reaches the engine only as an ADR option; its spike stays in
# prototypes/ (prototyper.md, "On a Custom Engine Project").
CHIEF_AGENT = ".claude/agents/chief-engine-architect.md"
RESEARCH_ROUTE_SECTION = "Research Route"
RESEARCH_ROUTE = "research route"
RESEARCH_STEPS = ("Question", "Spike", "Measurement", "ADR option")
NUMBERED_STEP = re.compile(r"^(\d+)\. \*\*([^*]+?)\.\*\*")
SPIKE_STEP_TOKENS = ("`prototypes/`", "spike mode's", "cap", "owner of the affected module", "engine-side code")
NO_MERGE_WITHOUT_ADR = ("No spike", "`engine/`", "accepted ADR")
# The engine spike: one Custom-gated block in /prototype's spike mode, after
# the performance spike and before the closing rule (design D3).
PROTOTYPE_SKILL_DIR = ".claude/skills/prototype/"
SPIKE_MODE = PROTOTYPE_SKILL_DIR + "references/spike-mode.md"
PROTOTYPE_UNCHANGED = (PROTOTYPE_SKILL_DIR + "SKILL.md", PROTOTYPE_SKILL_DIR + "references/3-choose-path.md")
ENGINE_SPIKE = "engine spike"
PERFORMANCE_SPIKE_LEAD = "**Performance spike (special case):**"
CLOSING_RULE = "---"
CUSTOM_GATE = ("`engine.name`", "`Custom`")
ENGINE_SPIKE_TOKENS = ("owner of the affected module", "engine-side code", "ADR option", "spike mode's", "cap",
                       "`prototypes/`", "never touches `engine/`")
PROTOTYPER_AGENT = ".claude/agents/prototyper.md"
PROTOTYPER_CUSTOM_SECTION = "On a Custom Engine Project"
PROTOTYPER_SPIKE_RULE = ("`/prototype --spike`", "stay in `prototypes/`", "never touch `engine/`")
MANIFEST = Path(__file__).resolve().parent / sh.MANIFEST_NAME
# Design D2 and spec tech-demo-delivery: the engine tech-demo path in
# /vertical-slice, one Custom-gated block as the last block of Phase 2 and of
# Phase 6. The Phase 2 block reads engine.name itself, so the bootstrap line
# stays the base line every engine sees.
VERTICAL_SLICE_SKILL_DIR = ".claude/skills/vertical-slice/"
VERTICAL_SLICE = VERTICAL_SLICE_SKILL_DIR + "SKILL.md"
SCOPE_PHASE = "Phase 2: Define the Slice Scope and Validation Question"
REPORT_PHASE = "Phase 6: Generate Vertical Slice Report"
TECH_DEMO_PATH = "tech-demo path"
BOOTSTRAP_PREFIX = "!`bash"
BOOTSTRAP_LINE = ('!`bash "${CLAUDE_SKILL_DIR}/../../hooks/yaml-helper.sh" resolve_config '
                  '--keys review_mode,automation,workflow`')
READS_THE_ENGINE = ("Read `engine.name` from `project.yaml`", "`Custom`")
DEMO_QUESTIONS = ("engine capabilities", "frame budget", "target hardware")
CAPABILITY_PLAN = ("each capability", "module owner", "budget", "evidence", "`/benchmark-report`", "test")
ENGINE_WORK_ROUTE = ("Engine work", "module owner", "lead", "`.claude/docs/custom-engine-layout.md`")
CONTENT_OWNERS = ("`lighting-artist`", "`cinematic-designer`", "`technical-artist`", "`world-builder`",
                  "`level-designer`", "`sound-designer`")
SHOWCASE_LIGHTING = ("`lighting-artist`", "showcase scene")
ONE_WAY = "one-way references"
DEMO_BUILD_OWNER = ("demo build", "`asset-build-tooling-engineer`", "exact tested build", "configuration",
                    "frozen content")
FOOTAGE_OWNER = ("footage", "`cinematic-designer`", "build", "hardware", "settings", "offline", "render-to-movie",
                 "real time")
REPORT_SECTIONS = ("Demo Capabilities", "Demo Build", "Footage")
# AM37: the Phase 6 block sits after the phase's "May I write" ask, so it says
# that the sections and the evidence rules go into the report before that ask.
WRITE_ASK = 'Ask: "May I write this report'
BEFORE_THE_WRITE_ASK = 'before you ask "May I write this report'
RENDER_TO_MOVIE = "render-to-movie"
PERFORMANCE_EVIDENCE = "performance evidence"
NO_REAL_TIME_CAPTURE = ("real-time capture", "target hardware", "`NOT ASSESSED`")
LIST_ITEM_UNIT = "- "

# Design D6 and spec industry-lessons: one Custom-only document of published
# lessons from in-house engines, one H2 per engine and one H3 per lesson (the
# closed list of task 6.1, each with the year its label must name), and one
# pointer line per pointed Custom agent.
LESSONS_DOC = ".claude/docs/engine-industry-lessons.md"
LESSONS_DOC_NAME = "engine-industry-lessons.md"
LESSONS_GUARD = "Applies only when `engine.name` is `Custom`; on any other engine, ignore this file."
LESSONS_PURPOSE = ("records published lessons for design decisions, not architectures to copy",
                   "an input to an ADR option, never a default")
FROSTBITE = "Frostbite (EA)"
NAUGHTY_DOG = "Naughty Dog engine"
ID_TECH = "id Tech (id Software)"
DECIMA = "Decima (Guerrilla Games)"
NORTHLIGHT = "Northlight (Remedy)"
SNOWDROP = "Snowdrop (Ubisoft Massive)"
MINECRAFT = "Minecraft Bedrock (Mojang and Microsoft)"
F1 = "Frame graph: passes and transient resources declared per frame"
N1 = "Fiber-based jobs and frame-centric data lifetime"
I1 = "Few shaders: coherent branching over permutations"
I2 = "GPU triangle culling and merged indirect draws"
D1 = "Streaming over a content graph"
D2 = "Visual programming compiled to native code"
R1 = "Data described in script, with versioning and a permutation budget"
M1 = "One editor and node graphs shared across disciplines"
MC1 = "A versioned, data-driven creator format"
MC2 = "One engine unified across platforms"
MC3 = "Chunked worlds from seed and coordinates"
LESSONS = {
    FROSTBITE: ((F1, 2017),),
    NAUGHTY_DOG: ((N1, 2015),),
    ID_TECH: ((I1, 2016), (I2, 2020)),
    DECIMA: ((D1, 2023), (D2, 2025)),
    NORTHLIGHT: ((R1, 2024),),
    SNOWDROP: ((M1, 2024),),
    MINECRAFT: ((MC1, 2025), (MC2, 2017), (MC3, 2025)),
}
PRINCIPLE_LABEL = re.compile(r"^\*\*Principle \((\d{4})\):\*\*", re.M)
LESSON_LABELS = ("**Principle (", "**Problem it solved:**", "**Cost:**", "**Source:**")
COST_LINE = re.compile(r"^\*\*Cost:\*\* (.*)$", re.M)
COST_NOT_SOURCEABLE = re.compile(r"^NOT SOURCEABLE — \S")
# No Mojang or Microsoft source states the problem MC3 solved, so its label
# says NOT SOURCEABLE with the reason; every other lesson names its problem.
PROBLEM_LINE = re.compile(r"^\*\*Problem it solved:\*\* (.*)$", re.M)
PROBLEM_NOT_SOURCEABLE = (MC3,)
# Score report 6, N1(b): neither Snowdrop source ties a cost to the shared
# editor or NodeGraphs, so M1's Cost line reads NOT SOURCEABLE with its reason.
COST_NOT_SOURCEABLE_LESSONS = (M1,)
NOT_SOURCEABLE = "NOT SOURCEABLE"
POINTER_LEAD = "- Industry lessons: "
POINTER_LINE = re.compile(r"^- Industry lessons: `([^`]+)` (.+)$")
POINTER_SEPARATOR = "; "
COORDINATION_SECTION = "Coordination"
LESSON_POINTERS = {
    ".claude/agents/render-graph-specialist.md": (COORDINATION_SECTION, (F1,)),
    ".claude/agents/concurrency-job-system-engineer.md": (COORDINATION_SECTION, (N1,)),
    ".claude/agents/world-streaming-engineer.md": (COORDINATION_SECTION, (D1, MC3)),
    ".claude/agents/editor-architect.md": (COORDINATION_SECTION, (M1, D2)),
    ".claude/agents/graphics-features-engineer.md": (COORDINATION_SECTION, (I2,)),
    ".claude/agents/chief-engine-architect.md": ("Delegation Map", (MC2, M1)),
    ".claude/agents/shader-pipeline-engineer.md": (COORDINATION_SECTION, (I1, R1)),
    ".claude/agents/asset-build-tooling-engineer.md": (COORDINATION_SECTION, (MC1, R1)),
}
MODULE_PATH = re.compile(r"\bengine/[\w-]+/")
SHADER_FILE = re.compile(r"\w\.(?:hlsl|slang|glsl|metal)\b", re.I)
H2_HEADING = re.compile(r"^## (.+?)[ \t]*$", re.M)
H3_HEADING = re.compile(r"^### (.+?)[ \t]*$", re.M)
FROSTBITE_KEY_PHRASES = {
    "render passes and resources as nodes": "C244",
    "from scratch every frame": "C244",
    "in a decoupled and modular way while keeping efficiency": "C244",
    "memory allocation and aliasing": "C244",
    "re-architecture in 2016": "C244",
    "one goal of the re-architecture": "C244",
    "the setup phase is relatively cheap": "C245",
    "template-heavy setup API": "C245",
}
NAUGHTY_DOG_KEY_PHRASES = {
    "can yield to other jobs in the middle of execution": "C246",
    "ran jobs to completion without ever yielding": "C246",
    "every programmer was solving the same problem": "C246",
    "greatly simplifies data lifetime and memory management": "C246",
    "a frame-centric design simplifies the engine": "C246",
    "system synchronization primitives can no longer be used": "C247",
    "atomic spin locks are used almost everywhere": "C247",
    "the wrong thread-local storage (TLS) pointer": "C247",
}
ID_TECH_KEY_PHRASES = {
    "about 100 shaders and about 350 pipeline states": "C248",
    "the same shader for all static geometry": "C248",
    "recommends static or coherent branching": "C248",
    "keep it simple": "C248",
    "relatively short development time": "C248",
    "a substantial catch-up to do": "C248",
    "pick its fights carefully": "C248",
    "keep an eye on VGPR pressure": "C249",
    "minimize nested loops and the worst-case path": "C249",
    "early on the GPU in a compute prepass": "C250",
    "which removes about 70% of submitted triangles": "C250",
    "a single indirect index buffer": "C250",
    "lowers CPU setup cost": "C250",
    "3 times the on-screen triangle count": "C250",
    "has to use the same pipeline state": "C251",
    "a completely bindless GPU pipeline": "C251",
}
DECIMA_KEY_PHRASES = {
    "separated by streaming links": "C252",
    "customizable logic for different domains": "C252",
    "no object is ever loaded more than once": "C252",
    "could not load content around the player dynamically": "C252",
    "must always be loaded fully": "C253",
    "opening and closing so many files is costly": "C253",
    "a language-specific backend": "C254",
    "a dynamic library that can be hot-reloaded": "C254",
    "more independent from programmers": "C254",
    "recompile the game just because of changes to some content": "C254",
    "tools for debugging by users": "C255",
    "get up to speed with the content's structure": "C255",
    "was difficult to maintain": "C255",
}
NORTHLIGHT_KEY_PHRASES = {
    "in Lua instead of C++": "C256",
    "versioning and patching in the same file": "C256",
    "a flat list, avoiding programmatic generation": "C256",
    "technical vision for materials": "C256",
    "the script file is pure Lua": "C256",
    "patching is based on version number": "C256",
    "dynamic branching is preferred over a highly specific compile-time feature set": "C256",
    "error prone and time consuming": "C256",
    "to keep compile times and pipeline state changes low": "C257",
    "about 2500 shaders": "C257",
}
SNOWDROP_KEY_PHRASES = {
    "unify the look and feel of the different editors": "C258",
    "a crucial tool for quick iterations": "C258",
    "a tool shared by programmers and designers": "C258",
    "presenting that complexity to designers": "C258",
    "made their way into Snowdrop and stayed there": "C259",
    "10 years later": "C259",
    "neither the Massive article nor the GDC 2016 session page states a cost": "C259",
}
MINECRAFT_KEY_PHRASES = {
    "but only if the format version is set correctly": "C260",
    "`min_engine_version`": "C260",
    "can grow or change over time": "C260",
    "Incorrect format versions are a frequent source of errors": "C261",
    "In 2017, with version 1.2.0": "C262",
    "unifying the various non-Java releases across platforms": "C262",
    "can be played on most devices": "C262",
    "cross-platform play": "C262",
    "can play together with the others": "C262",
    "all other isolated versions": "C262",
    "would give more players the chance": "C262",
    "less playable for certain audiences": "C263",
    "a six or eight-chunk radius": "C263",
    "three-dimensional XYZ coordinates": "C264",
    "smoothly changing noise values": "C264",
    "chunk-by-chunk": "C264",
    "As of version 1.18": "C265",
    "the same seed generates the same landscape": "C265",
    "9 or fewer characters": "C265",
    "order is not guaranteed within each pass": "C265",
    "no more world generation takes place": "C265",
}
LESSONS_KEY_PHRASES = {
    FROSTBITE: FROSTBITE_KEY_PHRASES,
    NAUGHTY_DOG: NAUGHTY_DOG_KEY_PHRASES,
    ID_TECH: ID_TECH_KEY_PHRASES,
    DECIMA: DECIMA_KEY_PHRASES,
    NORTHLIGHT: NORTHLIGHT_KEY_PHRASES,
    SNOWDROP: SNOWDROP_KEY_PHRASES,
    MINECRAFT: MINECRAFT_KEY_PHRASES,
}

# Every claim Phase 12 adds from here on that names a file is bound to a key
# phrase in one of these maps; each later group adds its maps to the tuple.
FIRST_PHASE12_CLAIM = 219
# Each later phase's map joins the completeness test below (Phase 12 task 2.2):
# fix plan AM38's claims are bound in test_agent_models.py.
from test_agent_models import KEY_PHRASES as AGENT_MODEL_KEY_PHRASES  # noqa: E402
ALL_KEY_PHRASES = (*SECTION_KEY_PHRASES.values(), NUMERICS_KEY_PHRASES, *LESSONS_KEY_PHRASES.values(),
                   {phrase: claim_id for claim_id, (_, phrase) in AGENT_MODEL_KEY_PHRASES.items()})


def units_of(path, heading):
    """The section's paragraphs and list items, each folded to one line."""
    return prose_units(section_text(file_text(path), heading))


def bold_list(text, head):
    """The list items under a bold lead-in line such as **NOT ASSESSED when**,
    each folded to one line, up to the first blank line after the list."""
    start = text.find(head)
    if start == -1:
        return []
    block = re.split(r"\n\s*\n", text[start:].replace("\r", ""), maxsplit=1)[0]
    return [" ".join(item.split()) for item in re.split(r"\n(?=- )", block)[1:]]


class XrRuntimeContracts(unittest.TestCase):
    def test_each_file_holds_its_xr_token(self):
        for path, token in XR_TOKENS:
            with self.subTest(path=path, token=token):
                self.assertTrue(token in file_text(path), f"{path} does not hold {token!r}")

    def test_xr_sections_are_registered(self):
        registered = {(path, heading) for path, heading, _item in TECHNICAL_SECTIONS}
        for path, heading in XR_RUNTIME_SECTIONS:
            with self.subTest(section=f"{path} # {heading}"):
                self.assertIn((path, heading), registered, "not in TECHNICAL_SECTIONS")

    def test_each_xr_section_opens_with_the_xr_condition(self):
        for path, heading in XR_RUNTIME_SECTIONS:
            with self.subTest(section=f"{path} # {heading}"):
                units = units_of(path, heading)
                self.assertTrue(units, f"{path} has no {heading} section")
                self.assertTrue(all(token in units[0] for token in XR_CONDITION),
                                f"the first unit does not hold {' '.join(XR_CONDITION)}: {units[0][:120]!r}")
                self.assertIn(XR_GATE_TAIL, units[0], f"the first unit does not end the gate with {XR_GATE_TAIL!r}")
                self.assertEqual(units[0], XR_GATE_SENTENCE, "the first unit is not the fixed XR gate sentence")

    def test_platform_options_are_adr_options_with_no_device_numbers(self):
        body = section_text(file_text(PLATFORM_AGENT), PLATFORM_XR_SECTION)
        self.assertIsNotNone(body, f"{PLATFORM_AGENT} has no {PLATFORM_XR_SECTION} section")
        units = prose_units(body)
        with self.subTest(check="no number with a unit"):
            self.assertEqual(NUMBER_WITH_UNIT.findall(body), [], "the section states a device number")
        for option in (STANDALONE_HEADSET, PASSTHROUGH):
            with self.subTest(option=option):
                self.assertTrue(any(option in u.lower() and ADR_OPTION in u for u in units),
                                f"no unit states {option!r} as an {ADR_OPTION}")
        with self.subTest(check="the ADR records the device facts"):
            self.assertTrue(any(all(t in u for t in DEVICE_FACTS_IN_THE_ADR) for u in units),
                            f"no unit holds {DEVICE_FACTS_IN_THE_ADR}")
        with self.subTest(check="rendering facts stay with graphics-features-engineer"):
            self.assertTrue(any(RENDERING_OWNER in u for u in units), f"the section does not name {RENDERING_OWNER}")
        with self.subTest(check="the XR bullet points to the section"):
            duties = prose_units(section_text(file_text(PLATFORM_AGENT), CORE_RESPONSIBILITIES))
            bullet = [u for u in duties if PLATFORM_XR_BULLET in u]
            self.assertEqual(len(bullet), 1, f"{len(bullet)} Core Responsibilities units hold {PLATFORM_XR_BULLET!r}")
            self.assertIn(PLATFORM_XR_SECTION, bullet[0])

    def test_audio_listener_takes_the_head_pose_at_a_recorded_time(self):
        units = units_of(AUDIO_AGENT, AUDIO_XR_SECTION)
        self.assertTrue(units, f"{AUDIO_AGENT} has no {AUDIO_XR_SECTION} section")
        for tokens in (LISTENER_TIME_ADR, POSE_SUPPLIER):
            with self.subTest(tokens=tokens):
                self.assertTrue(any(all(t in u for t in tokens) for u in units), f"no unit holds {tokens}")

    def test_template_points_to_the_vr_budget_and_leaves_the_miss_to_the_runtime(self):
        units = units_of(FRAME_BUDGET_TEMPLATE, TEMPLATE_XR_SECTION)
        self.assertTrue(units, f"{FRAME_BUDGET_TEMPLATE} has no {TEMPLATE_XR_SECTION} section")
        for tokens in ((REFRESH_RATE_SETTING,), VR_BUDGET_POINTER, AFTER_A_MISS):
            with self.subTest(tokens=tokens):
                self.assertTrue(any(all(t in u for t in tokens) for u in units), f"no unit holds {tokens}")

    def test_gate_reports_an_unset_refresh_rate_on_xr_as_not_assessed(self):
        text = file_text(FRAME_BUDGET_GATE)
        items = bold_list(text, NOT_ASSESSED_HEAD)
        self.assertTrue(items, f"{FRAME_BUDGET_GATE} has no {NOT_ASSESSED_HEAD} list")
        xr_items = [i for i in items if all(t in i for t in GATE_XR_TOKENS)]
        with self.subTest(check="one XR bullet"):
            self.assertEqual(len(xr_items), 1, f"{len(xr_items)} {NOT_ASSESSED_HEAD} bullets hold {GATE_XR_TOKENS}")
        with self.subTest(check="the XR bullet's fixed condition"):
            self.assertIn(GATE_XR_CONDITION, xr_items[0] if xr_items else "")
        with self.subTest(check="Verdicts line unchanged"):
            lines = [line.strip() for line in text.replace("\r", "").splitlines() if line.startswith("**Verdicts**")]
            self.assertEqual(lines, [VERDICTS_LINE])

    def test_xr_sections_hold_their_sourced_key_phrases(self):
        for (path, heading), phrases in SECTION_KEY_PHRASES.items():
            with self.subTest(section=f"{path} # {heading}"):
                check_path_key_phrases(self, path, heading, phrases)


class NumericsContracts(unittest.TestCase):
    def numerics_units(self):
        units = units_of(MATH_AGENT, NUMERICS_SECTION)
        self.assertTrue(units, f"{MATH_AGENT} has no {NUMERICS_SECTION} section")
        return units

    def test_numerics_section_is_registered(self):
        registered = {(path, heading) for path, heading, _item in TECHNICAL_SECTIONS}
        self.assertIn((MATH_AGENT, NUMERICS_SECTION), registered, "not in TECHNICAL_SECTIONS")

    def test_each_numeric_guarantee_is_an_adr_decision(self):
        units = self.numerics_units()
        for decision in NUMERICS_DECISIONS:
            with self.subTest(decision=decision):
                self.assertTrue(any(decision in u.lower() and ADR in u for u in units),
                                f"no unit names {decision!r} beside {ADR!r}")
        with self.subTest(check="an undecided guarantee is an open option"):
            self.assertTrue(any(all(t in u for t in OPEN_OPTION) for u in units), f"no unit holds {OPEN_OPTION}")

    def test_renormalization_and_inversion_state_no_number(self):
        units = self.numerics_units()
        for decision in NO_NUMBER_DECISIONS:
            with self.subTest(decision=decision):
                bullets = [u for u in units if u.lower().startswith(f"- **{decision}")]
                self.assertEqual(len(bullets), 1, f"{len(bullets)} bullets open with {decision!r}")
                self.assertEqual(DIGIT.findall(bullets[0]), [], f"the bullet states a number: {bullets[0][:120]!r}")

    def test_each_large_world_option_states_its_cost(self):
        bullets = [u for u in self.numerics_units() if u.startswith(f"- **{LARGE_WORLD_BULLET}")]
        self.assertEqual(len(bullets), 1, f"{len(bullets)} bullets open with {LARGE_WORLD_BULLET!r}")
        for cost in LARGE_WORLD_COSTS:
            with self.subTest(cost=cost):
                self.assertIn(cost, bullets[0])

    def test_every_compiler_default_names_its_compiler(self):
        sentences = [s for u in self.numerics_units() for s in SENTENCE_BREAK.split(u) if COMPILER_DEFAULT.search(s)]
        self.assertTrue(sentences, "the section states no compiler default")
        for sentence in sentences:
            with self.subTest(sentence=sentence[:100]):
                self.assertRegex(sentence, COMPILER_NAME)
                self.assertRegex(sentence, COMPILER_SOURCE, "names no version or manual")

    def test_math_rule_requires_a_ulp_bound_or_tolerance(self):
        units = prose_units(section_text(file_text(MATH_RULE), RULE_SECTION))
        with self.subTest(check="ULP in the rule"):
            self.assertIn(ULP, file_text(MATH_RULE))
        with self.subTest(check="each math function states its accuracy"):
            self.assertTrue(any(all(t in u for t in RULE_ACCURACY) for u in units), f"no unit holds {RULE_ACCURACY}")
        with self.subTest(check="the test-tolerance rule stays"):
            self.assertTrue(any(RULE_TEST_TOLERANCE in u for u in units))

    def test_editor_and_streaming_apply_the_large_world_adr(self):
        bullets = [u for u in prose_units(section_text(file_text(LEVEL_EDITOR_AGENT), EDITOR_VIEWPORT_SECTION))
                   if u.startswith(f"- {EDITOR_LARGE_WORLD_BULLET}")]
        with self.subTest(agent="level-editor-engineer"):
            self.assertEqual(len(bullets), 1, f"{len(bullets)} Viewport bullets open with {EDITOR_LARGE_WORLD_BULLET!r}")
            self.assertIn(LARGE_WORLD_ADR, bullets[0])
            self.assertIn(EDITOR_RULE_TEXT, bullets[0], "the editor rule's text did not stay")
            self.assertIn(EDITOR_NO_STRATEGY, bullets[0], "the editor no longer leaves the choice to the ADR")
        with self.subTest(agent="world-streaming-engineer"):
            units = [u for u in prose_units(file_text(STREAMING_AGENT)) if LARGE_WORLD_ADR in u]
            self.assertEqual(len(units), 1, f"{len(units)} units of {STREAMING_AGENT} name {LARGE_WORLD_ADR!r}")
            self.assertIn(STREAMING_NO_STRATEGY, units[0], "streaming no longer leaves the choice to the ADR")

    def test_numerics_section_holds_its_sourced_key_phrases(self):
        check_path_key_phrases(self, MATH_AGENT, NUMERICS_SECTION, NUMERICS_KEY_PHRASES)


def blocks_of(text):
    """The file's blank-line-separated blocks, CRLF folded to LF."""
    return [b.strip() for b in re.split(r"\n\s*\n", text.replace("\r", "")) if b.strip()]


def skill_hunks(manifest, skill_dir):
    """(path, hunk) for every manifest hunk of a file in the skill directory."""
    found = [(p, h) for p, entry in manifest["files"].items() if p.startswith(skill_dir)
             for h in entry["hunks"]]
    return found + [(p, h) for p, h in manifest.get("added", {}).items() if p.startswith(skill_dir)]


class ResearchRouteAndEngineSpike(unittest.TestCase):
    def test_chief_engine_architect_owns_a_research_route(self):
        body = section_text(file_text(CHIEF_AGENT), RESEARCH_ROUTE_SECTION)
        self.assertIsNotNone(body, f"{CHIEF_AGENT} has no {RESEARCH_ROUTE_SECTION} section")
        units = prose_units(body)
        with self.subTest(check="names the research route"):
            self.assertTrue(any(RESEARCH_ROUTE in u for u in units), f"no unit names the {RESEARCH_ROUTE!r}")
        steps = [(m.group(1), m.group(2)) for m in (NUMBERED_STEP.match(u) for u in units) if m]
        with self.subTest(check="the four steps in order"):
            self.assertEqual(steps, [(str(n), s) for n, s in enumerate(RESEARCH_STEPS, 1)])
        with self.subTest(check="the spike step"):
            spike = [u for u in units if u.startswith(f"2. **{RESEARCH_STEPS[1]}.**")]
            self.assertEqual(len(spike), 1)
            for token in SPIKE_STEP_TOKENS:
                self.assertIn(token, spike[0])
        with self.subTest(check="nothing merges into engine/ without an accepted ADR"):
            self.assertTrue(any(all(t in u for t in NO_MERGE_WITHOUT_ADR) for u in units),
                            f"no unit holds {NO_MERGE_WITHOUT_ADR}")

    def test_spike_mode_offers_the_engine_spike_in_one_custom_block(self):
        blocks = blocks_of(file_text(SPIKE_MODE))
        mine = [k for k, b in enumerate(blocks) if ENGINE_SPIKE in b.lower()]
        self.assertEqual(len(mine), 1, f"{len(mine)} blocks of {SPIKE_MODE} name the {ENGINE_SPIKE!r}")
        block = " ".join(blocks[mine[0]].split())
        with self.subTest(check="gated on engine.name Custom"):
            self.assertTrue(all(t in block for t in CUSTOM_GATE), f"the block does not hold {CUSTOM_GATE}")
        for token in ENGINE_SPIKE_TOKENS:
            with self.subTest(token=token):
                self.assertIn(token, block)
        with self.subTest(check="after the performance spike, before the closing rule"):
            self.assertTrue(blocks[mine[0] - 1].startswith(PERFORMANCE_SPIKE_LEAD) if mine[0] else False,
                            "the block does not follow the performance spike")
            self.assertEqual(blocks[mine[0] + 1:], [CLOSING_RULE], "the block is not the last before the rule")

    def test_engine_spike_agrees_with_the_prototyper(self):
        section = section_text(file_text(PROTOTYPER_AGENT), PROTOTYPER_CUSTOM_SECTION)
        self.assertIsNotNone(section, f"{PROTOTYPER_AGENT} has no {PROTOTYPER_CUSTOM_SECTION} section")
        section = " ".join(section.split())
        for token in PROTOTYPER_SPIKE_RULE:
            with self.subTest(token=token):
                self.assertIn(token, section)

    def test_prototype_skill_and_path_files_have_no_manifest_entry(self):
        manifest = sh.load_manifest(MANIFEST)
        for path in PROTOTYPE_UNCHANGED:
            with self.subTest(path=path):
                self.assertNotIn(path, manifest["files"])
                self.assertNotIn(path, manifest.get("added", {}))

    def test_every_prototype_hunk_is_a_custom_addition(self):
        hunks = skill_hunks(sh.load_manifest(MANIFEST), PROTOTYPE_SKILL_DIR)
        with self.subTest(check="the spike-mode block is pinned"):
            self.assertTrue(any(path == SPIKE_MODE for path, _hunk in hunks), f"no manifest hunk for {SPIKE_MODE}")
        for path, hunk in hunks:
            with self.subTest(path=path, hunk=hunk["id"]):
                self.assertEqual(hunk["reason"], sh.CLASS_ADDITION)


def phase_block(test, phase):
    """The one blank-line block of a /vertical-slice phase that names the
    tech-demo path, checked to be the last block before the phase's closing rule."""
    section = section_text(file_text(VERTICAL_SLICE), phase)
    test.assertIsNotNone(section, f"{VERTICAL_SLICE} has no {phase} section")
    blocks = blocks_of(section)
    mine = [k for k, b in enumerate(blocks) if TECH_DEMO_PATH in " ".join(b.split())]
    test.assertEqual(len(mine), 1, f"{len(mine)} blocks of {phase} name the {TECH_DEMO_PATH!r}")
    test.assertEqual(blocks[mine[0] + 1:], [CLOSING_RULE], f"the block is not the last block of {phase}")
    return prose_units(blocks[mine[0]])


class TechDemoPath(unittest.TestCase):
    def test_scope_phase_reads_the_engine_and_asks_for_the_demo(self):
        units = phase_block(self, SCOPE_PHASE)
        lead = units[0]
        with self.subTest(check="reads engine.name itself, gated on Custom"):
            self.assertTrue(all(t in lead for t in READS_THE_ENGINE), f"the lead does not hold {READS_THE_ENGINE}")
        with self.subTest(check="asks for capabilities, budget and target hardware"):
            self.assertTrue(all(t in lead for t in DEMO_QUESTIONS), f"the lead does not hold {DEMO_QUESTIONS}")
        with self.subTest(check="each capability with its owner, budget and evidence"):
            self.assertTrue(all(t in lead for t in CAPABILITY_PLAN), f"the lead does not hold {CAPABILITY_PLAN}")

    def test_scope_phase_routes_the_work_to_its_owners(self):
        units = phase_block(self, SCOPE_PHASE)
        items = [u for u in units if u.startswith(LIST_ITEM_UNIT)]
        for name, tokens in (("engine work", ENGINE_WORK_ROUTE), ("content owners", CONTENT_OWNERS),
                             ("showcase lighting", SHOWCASE_LIGHTING), ("demo build", DEMO_BUILD_OWNER),
                             ("footage", FOOTAGE_OWNER)):
            with self.subTest(route=name):
                self.assertEqual(len([i for i in items if all(t in i for t in tokens)]), 1,
                                 f"not exactly one list item holds {tokens}")
        with self.subTest(check="the content handoffs are one-way references"):
            self.assertTrue(any(ONE_WAY in u for u in units), f"no unit holds {ONE_WAY!r}")

    def test_report_phase_rejects_render_to_movie_as_performance_evidence(self):
        units = phase_block(self, REPORT_PHASE)
        with self.subTest(check="gated on Custom"):
            self.assertIn(CUSTOM_GATE[1], units[0])
        with self.subTest(check="names the report sections to add"):
            self.assertTrue(all(t in units[0] for t in REPORT_SECTIONS), f"the lead does not hold {REPORT_SECTIONS}")
        items = [u for u in units if u.startswith(LIST_ITEM_UNIT)]
        with self.subTest(check="render-to-movie is not performance evidence, in one list item"):
            self.assertTrue(any(RENDER_TO_MOVIE in i and PERFORMANCE_EVIDENCE in i for i in items),
                            f"no list item holds {RENDER_TO_MOVIE!r} and {PERFORMANCE_EVIDENCE!r}")
        with self.subTest(check="no real-time capture on the target hardware is NOT ASSESSED"):
            self.assertTrue(any(all(t in i for t in NO_REAL_TIME_CAPTURE) for i in items),
                            f"no list item holds {NO_REAL_TIME_CAPTURE}")

    def test_report_sections_go_into_the_draft_before_the_write_ask(self):
        # AM37: the user approves the report with its demo sections, so the
        # file written after the ask holds them.
        units = phase_block(self, REPORT_PHASE)
        section = " ".join(section_text(file_text(VERTICAL_SLICE), REPORT_PHASE).split())
        with self.subTest(check="the phase asks before it writes REPORT.md"):
            self.assertIn(WRITE_ASK, section)
        with self.subTest(check="the lead adds the sections before that ask"):
            self.assertIn(BEFORE_THE_WRITE_ASK, units[0])

    def test_bootstrap_line_is_unchanged(self):
        lines = [line.strip() for line in file_text(VERTICAL_SLICE).replace("\r", "").splitlines()
                 if line.startswith(BOOTSTRAP_PREFIX)]
        self.assertEqual(lines, [BOOTSTRAP_LINE])

    def test_every_vertical_slice_hunk_is_a_custom_addition(self):
        # The AM37 re-pin cites its amendment through a reason of its own whose
        # class is custom-addition, so check re-runs the same predicate on it.
        manifest = sh.load_manifest(MANIFEST)
        hunks = skill_hunks(manifest, VERTICAL_SLICE_SKILL_DIR)
        with self.subTest(check="the SKILL.md blocks are pinned"):
            self.assertTrue(any(path == VERTICAL_SLICE for path, _hunk in hunks), f"no manifest hunk for {VERTICAL_SLICE}")
        for path, hunk in hunks:
            with self.subTest(path=path, hunk=hunk["id"]):
                self.assertEqual(manifest["reasons"].get(hunk["reason"], {}).get("class"), sh.CLASS_ADDITION)


def h3_sections(text):
    """(H2 title, H3 title, H3 body) for each H3, CRLF folded to LF."""
    text = text.replace("\r", "")
    found, h2 = [], None
    for match in re.finditer(r"^(##|###) (.+?)[ \t]*$", text, re.M):
        if match[1] == "##":
            h2 = match[2]
        else:
            found.append((h2, match[2], section_text(text, match[2])))
    return found


class IndustryLessons(unittest.TestCase):
    def lessons_text(self):
        text = file_text(LESSONS_DOC).replace("\r", "")
        self.assertTrue(text, f"{LESSONS_DOC} does not exist")
        return text

    def test_engine_sections_are_registered(self):
        registered = {(path, heading) for path, heading, _item in TECHNICAL_SECTIONS}
        for engine in LESSONS:
            with self.subTest(section=f"{LESSONS_DOC} # {engine}"):
                self.assertIn((LESSONS_DOC, engine), registered, "not in TECHNICAL_SECTIONS")

    def test_document_opens_with_the_custom_guard_and_its_purpose(self):
        text = self.lessons_text()
        units = prose_units(re.split(r"^# .*$", text, maxsplit=1, flags=re.M)[-1])
        self.assertTrue(units, "no text after the H1 title")
        self.assertEqual(units[0], LESSONS_GUARD, "the first paragraph after the H1 title is not the Custom guard")
        flat = " ".join(text.split())
        for phrase in LESSONS_PURPOSE:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, flat)

    def test_lessons_are_the_closed_list_under_their_engines(self):
        text = self.lessons_text()
        self.assertEqual(H2_HEADING.findall(text), list(LESSONS), "the H2s are not the seven engines")
        expected = [(engine, title) for engine, lessons in LESSONS.items() for title, _year in lessons]
        self.assertEqual([(h2, h3) for h2, h3, _body in h3_sections(text)], expected)

    def test_each_lesson_holds_its_four_labels_and_its_year(self):
        years = {title: year for lessons in LESSONS.values() for title, year in lessons}
        for _h2, title, body in h3_sections(self.lessons_text()):
            with self.subTest(lesson=title):
                starts = [line for line in body.splitlines() if line.startswith("**")]
                self.assertEqual([next((l for l in LESSON_LABELS if s.startswith(l)), s) for s in starts],
                                 list(LESSON_LABELS), "not the four labels, once each, in order")
                self.assertEqual(PRINCIPLE_LABEL.findall(body), [str(years.get(title))],
                                 "the Principle label does not name the lesson's year")
                cost = COST_LINE.search(body)
                self.assertTrue(cost and cost[1].strip(), "the Cost line holds no text")
                if cost[1].startswith(NOT_SOURCEABLE):
                    self.assertRegex(cost[1], COST_NOT_SOURCEABLE, "NOT SOURCEABLE without a reason")

    def test_a_problem_no_studio_source_states_reads_not_sourceable(self):
        # A how-to step or a property is not the problem a principle solved:
        # MC3's label says NOT SOURCEABLE with its reason.
        not_sourceable = []
        for _h2, title, body in h3_sections(self.lessons_text()):
            problem = PROBLEM_LINE.search(body)
            with self.subTest(lesson=title):
                self.assertTrue(problem and problem[1].strip(), "the Problem line holds no text")
                if problem[1].startswith(NOT_SOURCEABLE):
                    not_sourceable.append(title)
                    self.assertRegex(problem[1], COST_NOT_SOURCEABLE, "NOT SOURCEABLE without a reason")
        self.assertEqual(not_sourceable, list(PROBLEM_NOT_SOURCEABLE))

    def test_a_cost_no_studio_source_states_reads_not_sourceable(self):
        # A note the source does not tie to the lesson's principle is not its
        # cost: M1's Cost line says NOT SOURCEABLE with its reason.
        not_sourceable = [title for _h2, title, body in h3_sections(self.lessons_text())
                          if (cost := COST_LINE.search(body)) and cost[1].startswith(NOT_SOURCEABLE)]
        self.assertEqual(not_sourceable, list(COST_NOT_SOURCEABLE_LESSONS))

    def test_each_pointed_agent_ends_its_section_with_one_pointer(self):
        h3s = {title for _h2, title, _body in h3_sections(file_text(LESSONS_DOC))}
        for path, (section, titles) in LESSON_POINTERS.items():
            with self.subTest(agent=path):
                body = section_text(file_text(path).replace("\r", ""), section)
                self.assertIsNotNone(body, f"{path} has no {section} section")
                lines = [line for line in body.splitlines() if line.strip()]
                self.assertEqual(sum(line.startswith(POINTER_LEAD) for line in lines), 1,
                                 "not exactly one pointer line in the section")
                pointer = POINTER_LINE.match(lines[-1])
                self.assertIsNotNone(pointer, f"the section's last line is not the pointer: {lines[-1][:80]!r}")
                self.assertEqual(pointer[1], LESSONS_DOC)
                self.assertEqual(pointer[2], POINTER_SEPARATOR.join(f'"{t}"' for t in titles))
                for title in titles:
                    self.assertIn(title, h3s, f"{title!r} is not an H3 of {LESSONS_DOC}")

    def test_only_the_document_and_the_pointed_agents_name_it(self):
        allowed = {LESSONS_DOC, *LESSON_POINTERS}
        naming = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / ".claude").rglob("*") if p.is_file()
                        and LESSONS_DOC_NAME in p.read_bytes().decode("utf-8", errors="ignore"))
        self.assertEqual([p for p in naming if p not in allowed], [])

    def test_document_names_no_agent_module_path_shader_file_or_count(self):
        text = self.lessons_text()
        self.assertEqual(sorted(names(text, agents_on_disk())), [], "names an agent")
        self.assertEqual(MODULE_PATH.findall(text), [], "names an engine/<module>/ path")
        self.assertEqual(SHADER_FILE.findall(text), [], "names a shader file")
        self.assertIsNone(COUNT_PHRASE.search(text), "states an agent, skill or rule count")

    def test_engine_sections_hold_their_sourced_key_phrases(self):
        for engine, phrases in LESSONS_KEY_PHRASES.items():
            with self.subTest(section=engine):
                check_path_key_phrases(self, LESSONS_DOC, engine, phrases)


# Task 7.1, design D1(a) and D6: the release notes say the Phase 12 additions
# are Custom only, in one sentence that names each of them, in UPGRADING's
# Other engines row and in CHANGELOG's Unreleased section. The sentence is held
# true by the guard tests above (every /prototype and /vertical-slice hunk is a
# custom-addition) and by test_only_the_document_and_the_pointed_agents_name_it.
NO_CHANGE_ON_OTHER_ENGINES = "other engines see no change from them"
NO_CHANGE_SUBJECTS = ("`/prototype`", "`/vertical-slice`", f"`{LESSONS_DOC_NAME}`")
OTHER_ENGINES_ROW = "| **Other engines** |"


class Phase12DisclosureIsTrue(unittest.TestCase):
    def test_release_notes_say_other_engines_see_no_change(self):
        upgrading = file_text("UPGRADING.md").replace("\r", "")
        changelog = file_text("CHANGELOG.md").replace("\r", "")
        problems = disclosure_problems(upgrading, changelog, (NO_CHANGE_ON_OTHER_ENGINES,))
        self.assertEqual(problems, [], "; ".join(problems))
        section = RELEASE_NOTE_SECTIONS["UPGRADING.md"].search(upgrading)
        row = next((line for line in (section[0] if section else "").splitlines()
                    if line.startswith(OTHER_ENGINES_ROW)), "")
        log = RELEASE_NOTE_SECTIONS["CHANGELOG.md"].search(changelog)
        for path, text in (("UPGRADING.md", row), ("CHANGELOG.md", " ".join((log[0] if log else "").split()))):
            sentences = [s for s in re.split(r"(?<=\.)\s+", text) if NO_CHANGE_ON_OTHER_ENGINES in s]
            with self.subTest(path=path):
                self.assertEqual(len(sentences), 1, f"{len(sentences)} sentences hold {NO_CHANGE_ON_OTHER_ENGINES!r}")
                for subject in NO_CHANGE_SUBJECTS:
                    self.assertIn(subject, sentences[0])


class Phase12ClaimsAreBound(unittest.TestCase):
    def test_every_phase12_claim_with_a_file_is_bound_to_a_key_phrase(self):
        bound = {claim_id for phrases in ALL_KEY_PHRASES for claim_id in phrases.values()}
        unbound = [c["claim_id"] for c in ledger("claims")
                   if int(c["claim_id"][1:]) >= FIRST_PHASE12_CLAIM and "file" in c and c["claim_id"] not in bound]
        self.assertEqual(unbound, [], f"Phase 12 claims with no key phrase: {unbound}")


if __name__ == "__main__":
    unittest.main()
