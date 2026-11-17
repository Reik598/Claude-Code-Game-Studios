"""Structural contracts for the technical accuracy and ownership statements of
the Custom render, platform, memory, streaming and build agents and rules (fix
plan section 12, Phase 10, lane engine-agents-render-platform).

Run: python -m unittest discover -s studio-tests -p test_engine_accuracy_gpu.py -v
Each test names the review item it guards (R- and T-numbers in the session's
Phase 10 triage). These check files on disk, not Claude's behaviour in a
session; a compiler run of an example is a manual check recorded in the lane
note, not here.
"""
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import (  # noqa: E402
    CUSTOM_TEXT_LINE, FRONTMATTER, ROOT, custom_only_rules, duty_text, read)
from test_engine_phase8 import bullets, custom_agents, section_text  # noqa: E402

AGENTS_DIR = ".claude/agents"
RULES_DIR = ".claude/rules"
TEMPLATES_DIR = ".claude/docs/templates"
CORE_LEAD = f"{AGENTS_DIR}/core-systems-lead.md"
RENDERING_LEAD = f"{AGENTS_DIR}/rendering-lead.md"
RHI_AGENT = f"{AGENTS_DIR}/rhi-backend-engineer.md"
SHADER_AGENT = f"{AGENTS_DIR}/shader-pipeline-engineer.md"
VFX_AGENT = f"{AGENTS_DIR}/vfx-runtime-engineer.md"
ALLOCATOR_AGENT = f"{AGENTS_DIR}/memory-allocator-specialist.md"
STREAMING_AGENT = f"{AGENTS_DIR}/world-streaming-engineer.md"
BUILD_AGENT = f"{AGENTS_DIR}/asset-build-tooling-engineer.md"
PLATFORM_AGENT = f"{AGENTS_DIR}/platform-engineer.md"
RHI_RULE = f"{RULES_DIR}/rhi-renderer-code.md"
MEMORY_TEMPLATE = f"{TEMPLATES_DIR}/memory-invariants.md"
SHADER_SPEC = "studio-tests/agents/engine/custom/shader-pipeline-engineer.md"
RHI_SPEC = "studio-tests/agents/engine/custom/rhi-backend-engineer.md"

# A statement: a paragraph, list item or table row (the unit
# test_engine_support's handoff check reads).
UNIT_START = re.compile(r"\n(?=\s*(?:[-*]|\d+\.)\s|\|)")
CORRECT_LABEL = re.compile(r"^\*\*Correct\b")

# R55: engine/math/ (vectors, matrices, SIMD primitives) is ecs-dod-architect's
# row under core-systems-lead; the lead keeps it, it does not hand it over.
MATH_OWNER = "ecs-dod-architect"
SIMULATION_LEAD = "simulation-systems-lead"
SIMD_MATH = re.compile(r"SIMD math", re.I)

# R132, R135: hand-overs to rhi-backend-engineer, in the form of
# test_engine_support.HANDOFFS: (file that hands over, phrase of the handing-
# over statement, agent it names, term that agent's duties must take).
RHI_HANDOFFS = [
    (ALLOCATOR_AGENT, "upload rings", "rhi-backend-engineer", "upload rings"),
    (STREAMING_AGENT, "Staging rings", "rhi-backend-engineer", "staging rings"),
    (RENDERING_LEAD, "upload rings", "rhi-backend-engineer", "upload rings"),
    (RENDERING_LEAD, "GPU memory sub-allocation", "rhi-backend-engineer", "GPU memory sub-allocation"),
    (RENDERING_LEAD, "GPU zones", "rhi-backend-engineer", "GPU zones"),
]
# R132: memory-allocator-specialist is consulted on the algorithm only.
GPU_MEMORY_TERMS = re.compile(r"upload ring|staging|sub-allocation", re.I)
ALGORITHM = "algorithm"
# R135: zones are placed by each module's owner through core-systems-lead's
# trace API; asset-build-tooling-engineer owns the build switch, presets and
# CI captures, so no routing statement hands it zones or instrumentation.
# "Tracy/PIX instrumentation build switch" names the switch it does own.
ZONE_ROUTE = re.compile(
    r"(?:GPU|profiler) zones|profil(?:er|ing) (?:memory )?instrumentation|memory instrumentation"
    r"|(?:Tracy|PIX)[^|]*?instrumentation(?!\s+(?:build\s+)?switch)", re.I)
BUILD_AGENT_NAME = "asset-build-tooling-engineer"
# Routing statements live in every Custom agent, every Custom-only rule and
# the roster.
ROSTER = ".claude/docs/agent-roster.md"

# R136: one layer for the async I/O backends.
IO_BACKEND = "DirectStorage"
IO_MODULE = "`engine/io/`"
STREAMING_PLATFORM_REDIRECT = re.compile(r"^- .*→ `platform-engineer`", re.M)
OWNED_IO_WORDS = re.compile(r"platform I/O APIs|Raw async file read")

# R129 (D6): tools/ is split; asset-build-tooling-engineer names both halves.
TOOLS_PROGRAMMER_ROW = re.compile(r"^- \*\*tools-programmer\*\*.*$", re.M)
D6_OWN_TOOLS = ("`tools/ci/`", "`tools/build/`", "`tools/cook/`")

# R73: VK_EXT_descriptor_buffer is deprecated by VK_EXT_descriptor_heap (vk.xml).
DESCRIPTOR_BUFFER = re.compile(r"descriptor[ _]buffer", re.I)
DESCRIPTOR_BUFFER_STATUS = re.compile(r"deprecated|descriptor_heap", re.I)

# R76: a qualified member redeclared outside its class must be a definition.
QUALIFIED_DECLARATION = re.compile(r"^[^\s/].*\bInput::sample\([^)]*\)[^{]*;\s*$", re.M)
INPUT_CLASS = re.compile(r"class Input\b[^;]*?\{[^}]*\bsample\(\)", re.S)

# R81: MiniDumpWriteDump remarks: from a separate process if at all possible.
CRASH_SECTION = "Crash handling"
OUT_OF_PROCESS = re.compile(r"out-of-process|separate process", re.I)
# The in-process handler signals a separate process; every clause that says
# who writes the dump names the out-of-process handler as its subject.
CLAUSE_END = re.compile(r"[.:;](?:\s|$)")
WRITES_DUMP = re.compile(r"\bwrites? the (?:mini)?dump", re.I)
OUT_OF_PROCESS_WRITER = re.compile(
    r"(?:out-of-process|separate[^.:;]*process)[^.:;]*\bwrites? the (?:mini)?dump", re.I)
IN_PROCESS_HANDLER = "in-process handler"
SIGNALS_SEPARATE = re.compile(r"signals a separate[^.:;]*process", re.I)

# R77: clippy::mut_from_ref is deny by default and fires on alloc(&self) -> &mut.
MUT_FROM_REF_ALLOW = re.compile(r"#\[allow\(clippy::mut_from_ref\)\][^\n]*\n\s*pub fn alloc\b")

# R78: a pmr do_allocate returns storage or throws; never null.
NORETURN_OVERFLOW = re.compile(r"\[\[noreturn\]\][^;]*\bon_overflow\(")
RETURNS_OVERFLOW = re.compile(r"return\s+on_overflow\(")
THROWS_BAD_ALLOC = re.compile(r"\bthrow\s+std::bad_alloc\b")
# do_allocate returns only a pointer it checked non-null in the same
# statement; the fall-through reports overflow or throws.
DO_ALLOCATE = re.compile(r"\bdo_allocate\([^)]*\)[^{;]*\{")
CHECKED_RETURN = re.compile(
    r"if\s*\(\s*void\s*\*\s*(\w+)\s*=\s*try_allocate\([^)]*\)\s*\)[^;]*?\breturn\s+\1\s*;")
RETURN_STATEMENT = re.compile(r"\breturn\b[^;]*;")
OVERFLOW_PATH = re.compile(r"\bon_overflow\(|\bthrow\s+std::bad_alloc\b")

# R84: a wanted cell already resident or in flight is skipped before it is
# reserved and submitted again.
SKIP_PENDING = "resident_or_pending"
RESERVE_OR_SUBMIT = re.compile(r"try_reserve\(|submit\(")

# R85, R86: a visibility-buffer resolve samples with analytic gradients.
RESOLVE_PATH = "cs_resolve.hlsl"
MIP0_SAMPLE = re.compile(r"SampleLevel\(\s*\w+\s*,\s*[\w.]+\s*,\s*0(?:\.0)?f?\s*\)")
IMPLICIT_DERIVATIVE = re.compile(r"[Ii]mplicit[- ](?:\(quad\) )?derivative")
UNCONDITIONAL_COMPUTE_BAN = re.compile(r"[Ii]mplicit[- ]derivative[^.]*\bin compute\b(?! derivatives)")
BOUNDARY = "boundar"

# R87: a deterministic dead list does not come from atomic appends.
DETERMINISTIC_BULLET = "Deterministic simulation option"
ORDERED_LIST = re.compile(r"prefix|compaction", re.I)

# R88, R90: rhi-backend-engineer's statements.
CPU_WAIT_EVERY_FRAME = "CPU wait every frame"
AS_SECTION = "Ray-Tracing Acceleration Structures"
AS_MEMORY_BULLET = "**Memory.**"
UPDATE_SCRATCH = "UpdateScratchDataSizeInBytes"

# R92: CMake's --profiling-output profiles CMake scripts, not compilation.
COMPILE_HYGIENE = "**Compile-time hygiene (C++)**"
CMAKE_PROFILING = "--profiling-output"

# R103: an execute closure runs at graph execution, after the function that
# added the pass returned, so it captures values, never `self`.
EXECUTE_CLOSURE = re.compile(r"\|\s*(?:cmd|ctx)\b[^|]*\|")

# R137, T9: cache-line padding goes through the per-target constant.
CACHE_LINE_CONSTANT = "engine::cache_line"
LITERAL_CACHE_LINE = re.compile(
    r"\b(?:alignas|align|aligned)\(\s*(?:64|128|256)\s*\)"
    r"|\b(?:padded|aligned) to \[?(?:64|128|256)\]?(?:\s*-?\s*bytes?)?"
    r"|\ban? (?:64|128|256)-byte cache[- ]line", re.I)

# T8: recreate first; exit only when recreating fails.
DEVICE_LOSS = re.compile(r"[Dd]evice[- ]l(?:oss|ost)")
RULE_DEVICE_LOSS_ORDER = re.compile(r"recreate[^.]*;[^.]*exit[^.]*only if[^.]*fails")
AGENT_DEVICE_LOSS_ORDER = re.compile(r"recreate.*?\bexit\b[^.]*\bonly if\b[^.]*\bfails\b")
RHI_AGENT_SECTION = "All backends"


def statements(text):
    """Each paragraph, list item and table row, whitespace-flattened."""
    return [" ".join(u.split()) for p in re.split(r"\n\s*\n", text.replace("\r", ""))
            for u in UNIT_START.split(p) if u.strip()]


def fenced(text):
    """(label line, language, code) for each fenced block; the label is the
    nearest non-blank line above the fence."""
    lines, out, i = text.replace("\r", "").splitlines(), [], 0
    while i < len(lines):
        if lines[i].startswith("```"):
            label = next((lines[k] for k in range(i - 1, -1, -1) if lines[k].strip()), "")
            end = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("```")), len(lines))
            out.append((label, lines[i][3:].strip(), "\n".join(lines[i + 1:end])))
            i = end + 1
        else:
            i += 1
    return out


def prose(text):
    """The text outside fenced blocks."""
    return re.sub(r"^```.*?^```[^\n]*$", "", text.replace("\r", ""), flags=re.M | re.S)


def correct_blocks(path, language):
    return [code for label, lang, code in fenced(read(path))
            if CORRECT_LABEL.match(label) and lang == language]


def braced_body(code, open_brace):
    """From an opening brace to its matching closing brace, exclusive."""
    depth = 0
    for i in range(open_brace, len(code)):
        depth += {"{": 1, "}": -1}.get(code[i], 0)
        if depth == 0:
            return code[open_brace + 1:i]
    return code[open_brace + 1:]


def clauses(text):
    """The text split at sentence ends, colons and semicolons, flattened."""
    return [c for c in CLAUSE_END.split(" ".join(text.split())) if c.strip()]


def closure_body(code, start):
    """From a closure's parameter list to the end of its expression: the
    bracket depth returns below its start, or a `;` at that depth."""
    depth = 0
    for i in range(start, len(code)):
        ch = code[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                return code[start:i]
        elif ch == ";" and depth == 0:
            return code[start:i]
    return code[start:]


class Routing(unittest.TestCase):
    def assert_handoff(self, source, phrase, agent, term):
        units = statements(read(source))
        self.assertTrue(any(phrase in u and agent in u for u in units),
                        f"no statement in {source} names both {phrase!r} and {agent}")
        found = duty_text(read(f"{AGENTS_DIR}/{agent}.md"))
        self.assertTrue(found, "the agent has no duty section")
        duties = " ".join(" ".join(s.split()) for s in found).lower()
        self.assertIn(term.lower(), duties, "the agent's responsibilities do not take the handed-over term")

    def test_core_lead_keeps_simd_math(self):
        # R55: core-systems-lead hands simulation work to simulation-systems-lead
        # but not its own engine/math/ row; that row goes to ecs-dod-architect.
        units = statements(read(CORE_LEAD))
        handed = [u for u in units if SIMULATION_LEAD in u and SIMD_MATH.search(u)]
        self.assertEqual(handed, [], "core-systems-lead hands SIMD math to simulation")
        routing = section_text(read(CORE_LEAD), "Routing Table") or ""
        self.assertTrue(any("SIMD" in u and MATH_OWNER in u for u in statements(routing)),
                        f"the routing table does not send engine/math/ to {MATH_OWNER}")

    def test_gpu_memory_and_zones_have_an_accepting_owner(self):
        # R132, R135: each hand-over lands in rhi-backend-engineer's Core
        # Responsibilities.
        for source, phrase, agent, term in RHI_HANDOFFS:
            with self.subTest(source=source, term=term):
                self.assert_handoff(source, phrase, agent, term)

    def test_allocator_specialist_is_consulted_on_the_algorithm_only(self):
        # R132: rendering-lead and rhi-backend-engineer no longer send GPU
        # rings or sub-allocation to memory-allocator-specialist.
        for path in (RENDERING_LEAD, RHI_AGENT):
            for unit in statements(read(path)):
                if "memory-allocator-specialist" in unit and GPU_MEMORY_TERMS.search(unit):
                    with self.subTest(file=path, statement=unit[:90]):
                        self.assertIn(ALGORITHM, unit)

    def test_zones_are_not_routed_to_the_build_agent(self):
        # R135: asset-build-tooling-engineer may not edit module code, so no
        # routing statement gives it zones or instrumentation: not in any
        # Custom agent (its own description included), Custom-only rule or
        # the roster.
        files = [f"{AGENTS_DIR}/{a}.md" for a in custom_agents()]
        files += [f"{RULES_DIR}/{r}.md" for r in sorted(custom_only_rules())]
        files.append(ROSTER)
        self.assertIn(RENDERING_LEAD, files)
        for path in files:
            for unit in statements(read(path)):
                if BUILD_AGENT_NAME in unit and ZONE_ROUTE.search(unit):
                    with self.subTest(file=path, statement=unit[:90]):
                        self.fail("zones or instrumentation routed to the build agent")

    def test_build_agent_states_the_profiler_split(self):
        # R135: the build agent's duty names the split, so it does not claim zones.
        duties = " ".join(" ".join(s.split()) for s in duty_text(read(BUILD_AGENT)))
        self.assertNotRegex(duties, r"Profiler instrumentation \(Tracy CPU/GPU zones")
        self.assertIn("core-systems-lead", duties)
        self.assertIn("build switch", duties)

    def test_io_backends_sit_in_one_layer(self):
        # R136: both agents put DirectStorage in engine/io/, and the streaming
        # agent hands only the OS file primitive to platform-engineer.
        for path in (STREAMING_AGENT, PLATFORM_AGENT):
            with self.subTest(file=path):
                units = [u for u in statements(read(path)) if IO_BACKEND in u]
                self.assertTrue(any(IO_MODULE in u for u in units), f"no statement puts {IO_BACKEND} in engine/io/")
        redirects = STREAMING_PLATFORM_REDIRECT.findall(read(STREAMING_AGENT))
        self.assertTrue(redirects, "no redirect to platform-engineer")
        for line in redirects:
            self.assertNotRegex(line, OWNED_IO_WORDS)

    def test_build_agent_follows_the_tools_split(self):
        # R129 (D6): standalone pipeline and batch tools go to tools-programmer;
        # tools/ci/, tools/build/ and the cook-side tools stay here.
        rows = TOOLS_PROGRAMMER_ROW.findall(read(BUILD_AGENT))
        self.assertEqual(len(rows), 1)
        self.assertIn("standalone", rows[0])
        for path in D6_OWN_TOOLS:
            with self.subTest(path=path):
                self.assertIn(path, " ".join(duty_text(read(BUILD_AGENT))))


class GraphicsFacts(unittest.TestCase):
    def test_descriptor_buffer_is_named_as_deprecated(self):
        # R73: vk.xml marks VK_EXT_descriptor_buffer deprecatedby
        # VK_EXT_descriptor_heap, so no statement offers it without saying so.
        paths = sorted((ROOT / AGENTS_DIR).glob("*.md")) + sorted((ROOT / RULES_DIR).glob("*.md"))
        for path in paths:
            for unit in statements(prose(path.read_text(encoding="utf-8"))):
                if DESCRIPTOR_BUFFER.search(unit):
                    with self.subTest(file=path.name, statement=unit[:90]):
                        self.assertRegex(unit, DESCRIPTOR_BUFFER_STATUS)

    def test_descriptor_spec_case_uses_descriptor_heap(self):
        # R73: the version-awareness case asks about the forward path.
        case = re.search(r"### Case 4:.*?(?=\n### Case )", read(RHI_SPEC).replace("\r", ""), re.S)
        self.assertIsNotNone(case)
        self.assertIn("VK_EXT_descriptor_heap", case[0])

    def test_resolve_samples_with_analytic_gradients(self):
        # R85: the visibility-buffer resolve samples with SampleGrad, not mip 0.
        blocks = [c for c in correct_blocks(SHADER_AGENT, "hlsl") if RESOLVE_PATH in c]
        self.assertEqual(len(blocks), 1, "the cs_resolve Correct block was not found")
        self.assertIn("SampleGrad", blocks[0])
        self.assertNotRegex(blocks[0], MIP0_SAMPLE)

    def test_implicit_derivative_hazard_is_stated_precisely(self):
        # R86: SM 6.6 has quad derivatives in compute; the hazard is the quad
        # spanning other triangles or materials, not compute as such.
        anti = section_text(read(SHADER_AGENT), "Anti-Patterns") or ""
        found = [b for b in bullets(anti) if IMPLICIT_DERIVATIVE.search(b)]
        self.assertEqual(len(found), 1, "expected one implicit-derivative anti-pattern")
        self.assertNotRegex(found[0], UNCONDITIONAL_COMPUTE_BAN)
        self.assertIn(BOUNDARY, found[0])
        case = re.search(r"### Case 1:.*?(?=\n### Case )", read(SHADER_SPEC).replace("\r", ""), re.S)
        self.assertIsNotNone(case)
        self.assertIn("SampleGrad", case[0])

    def test_deterministic_particles_order_the_dead_list(self):
        # R87: the dead list's order comes from the previous frame's atomic
        # appends unless it is rebuilt in slot order.
        standards = section_text(read(VFX_AGENT), "VFX Runtime Standards (2026 practice)") or ""
        found = [b for b in bullets(standards) if DETERMINISTIC_BULLET in b]
        self.assertEqual(len(found), 1)
        self.assertRegex(found[0], ORDERED_LIST)

    def test_no_cpu_wait_every_frame_anti_pattern(self):
        # R88: the file prescribes a waitable-swapchain wait before every frame.
        anti = section_text(read(RHI_AGENT), "Anti-Patterns") or ""
        self.assertTrue(anti)
        self.assertNotIn(CPU_WAIT_EVERY_FRAME, anti)

    def test_both_apis_report_update_scratch(self):
        # R90: D3D12's prebuild info has UpdateScratchDataSizeInBytes too.
        section = section_text(read(RHI_AGENT), AS_SECTION) or ""
        found = [b for b in bullets(section) if AS_MEMORY_BULLET in b]
        self.assertEqual(len(found), 1)
        self.assertIn(UPDATE_SCRATCH, found[0])

    def test_rust_execute_closures_do_not_borrow_self(self):
        # R103: a deferred execute closure that reads `self.` borrows the
        # adding function's receiver (rustc E0521 when the graph stores it);
        # `move` does not help, it moves the `&self` reference.
        seen = 0
        for path in sorted((ROOT / ".claude").rglob("*.md")):
            for label, lang, code in fenced(path.read_text(encoding="utf-8")):
                if lang != "rust" or not CORRECT_LABEL.match(label):
                    continue
                for hit in EXECUTE_CLOSURE.finditer(code):
                    seen += 1
                    if "self." in closure_body(code, hit.start()):
                        with self.subTest(file=path.relative_to(ROOT).as_posix(), closure=hit[0]):
                            self.fail("execute closure reads self.")
        self.assertTrue(seen, "no Rust execute closure found: the form is out of date")


class PlatformMemoryBuildFacts(unittest.TestCase):
    def test_input_sample_is_declared_in_its_class(self):
        # R76: `Input::sample() noexcept;` at namespace scope is ill-formed.
        blocks = [c for c in correct_blocks(PLATFORM_AGENT, "cpp") if "InputSnapshot" in c]
        self.assertEqual(len(blocks), 1)
        self.assertNotRegex(blocks[0], QUALIFIED_DECLARATION)
        self.assertRegex(blocks[0], INPUT_CLASS)

    def test_crash_dump_is_written_out_of_process(self):
        # R81: MiniDumpWriteDump in the crashed process can deadlock on the
        # loader lock; Microsoft says to call it from a separate process.
        section = section_text(read(PLATFORM_AGENT), CRASH_SECTION) or ""
        self.assertTrue(section)
        self.assertRegex(section, OUT_OF_PROCESS)
        handler = [b for b in bullets(section) if IN_PROCESS_HANDLER in " ".join(b.split())]
        self.assertEqual(len(handler), 1, "no single in-process handler bullet")
        self.assertRegex(" ".join(handler[0].split()), SIGNALS_SEPARATE)
        writers = [c for c in clauses(section) if WRITES_DUMP.search(c)]
        self.assertTrue(writers, "no clause says who writes the dump")
        for clause in writers:
            with self.subTest(clause=clause[:90]):
                self.assertRegex(clause, OUT_OF_PROCESS_WRITER)

    def test_arena_alloc_allows_mut_from_ref(self):
        # R77: the lint is deny by default; the example states why it is sound.
        blocks = [c for c in correct_blocks(ALLOCATOR_AGENT, "rust") if "FrameArena" in c]
        self.assertEqual(len(blocks), 1)
        self.assertRegex(blocks[0], MUT_FROM_REF_ALLOW)

    def test_pmr_arena_never_returns_null(self):
        # R78: on_overflow reports and does not return (or throws bad_alloc).
        blocks = [c for c in correct_blocks(ALLOCATOR_AGENT, "cpp") if "class FrameArena" in c]
        self.assertEqual(len(blocks), 1)
        self.assertTrue(NORETURN_OVERFLOW.search(blocks[0]) or THROWS_BAD_ALLOC.search(blocks[0]),
                        "on_overflow is neither [[noreturn]] nor throws bad_alloc")
        self.assertNotRegex(blocks[0], RETURNS_OVERFLOW)
        # do_allocate itself never returns an unchecked, nullable pointer.
        head = DO_ALLOCATE.search(blocks[0])
        self.assertIsNotNone(head, "do_allocate was not found")
        body = braced_body(blocks[0], head.end() - 1)
        self.assertRegex(body, CHECKED_RETURN, "no checked non-null return")
        rest = CHECKED_RETURN.sub("", body)
        self.assertEqual(RETURN_STATEMENT.findall(rest), [], "do_allocate returns an unchecked pointer")
        self.assertRegex(rest, OVERFLOW_PATH, "the fall-through neither reports overflow nor throws")

    def test_streaming_update_skips_resident_and_pending_cells(self):
        # R84: a cell wanted for several frames is submitted once.
        for language in ("cpp", "rust"):
            blocks = [c for c in correct_blocks(STREAMING_AGENT, language) if "update(" in c]
            with self.subTest(language=language):
                self.assertEqual(len(blocks), 1)
                skip = blocks[0].find(SKIP_PENDING)
                first = RESERVE_OR_SUBMIT.search(blocks[0])
                self.assertNotEqual(skip, -1, "no resident-or-pending skip")
                self.assertIsNotNone(first)
                self.assertLess(skip, first.start(), "the skip comes after the reserve or submit")
                if language == "cpp":
                    self.assertIn("std::erase_if", blocks[0], "cancelled requests stay in in_flight_")

    def test_compile_time_hygiene_names_compiler_tools(self):
        # R92: --profiling-output profiles CMake scripts, not compilation.
        found = [b for b in bullets(read(BUILD_AGENT)) if COMPILE_HYGIENE in b]
        self.assertEqual(len(found), 1)
        self.assertNotIn(CMAKE_PROFILING, found[0])
        self.assertIn("-ftime-trace", found[0])

    def test_no_literal_cache_line_padding(self):
        # R137, T9: Custom agents, Custom-only rules and Custom templates pad
        # to the per-target constant. A code line, or a prose statement, with
        # a literal line size must name engine::cache_line.
        files = [f"{AGENTS_DIR}/{a}.md" for a in custom_agents()]
        files += [f"{RULES_DIR}/{r}.md" for r in sorted(custom_only_rules())]
        files += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / TEMPLATES_DIR).glob("*.md"))
                  if CUSTOM_TEXT_LINE.search(p.read_text(encoding="utf-8"))]
        self.assertIn(MEMORY_TEMPLATE, files)
        for path in files:
            text = read(path)
            checked = [line for _, _, code in fenced(text) for line in code.splitlines()]
            checked += statements(prose(text))
            for item in checked:
                if LITERAL_CACHE_LINE.search(item) and CACHE_LINE_CONSTANT not in item:
                    with self.subTest(file=path, text=item.strip()[:90]):
                        self.fail("literal cache-line size")

    def test_device_loss_recreates_before_it_exits(self):
        # T8: the policy order, not just its words: recreate, and exit only
        # if recreating fails.
        rule = [b for b in bullets(FRONTMATTER.sub("", read(RHI_RULE), count=1)) if DEVICE_LOSS.search(b)]
        self.assertEqual(len(rule), 1)
        self.assertRegex(" ".join(rule[0].split()), RULE_DEVICE_LOSS_ORDER)
        agent = [b for b in bullets(section_text(read(RHI_AGENT), RHI_AGENT_SECTION) or "")
                 if DEVICE_LOSS.search(b)]
        self.assertEqual(len(agent), 1)
        self.assertRegex(" ".join(agent[0].split()), AGENT_DEVICE_LOSS_ORDER)


if __name__ == "__main__":
    unittest.main()
