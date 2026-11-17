"""Structural contracts for the technical accuracy and ownership statements of
the Custom engine agents and rules (fix plan section 12, Phase 10, lane
engine-agents-sim-editor).

Run: python -m unittest discover -s studio-tests -p test_engine_accuracy.py -v
Each test names the review item it guards (R-numbers in the session's
Phase 10 triage). These check files on disk, not Claude's behaviour in a
session.
"""
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import (  # noqa: E402
    CUSTOM_AGENT_SPEC_DIR, CUSTOM_TEXT_LINE, FRONTMATTER, NUMBER_WORDS, ROOT, expand, glob_match,
    layout_rows, read, resolve_layout_row, row_lead, row_owner, section_text)

AGENTS_DIR = ".claude/agents"
# Paths an agent can claim: the Custom roots and the tools/ rows of the layout.
CLAIMED_PATH = r"`((?:engine|crates|game|tools)/[^`]*)`"
OPENER_CLAIM = re.compile(r"You own (.*?)(?::|\.(?:\s|$))")
RESPONSIBILITY_CLAIM = re.compile(r"\bin " + CLAIMED_PATH)
PARENTHESISED = re.compile(r"\([^()]*\)")
ROUTES_TO_LINE = re.compile(r"Routes to:(.*?)(?:\.\s|\.$|\n\n)", re.S)
DUTY_SECTION = "Core Responsibilities"
REPORTS_TO = re.compile(r"^\*\*Reports to:\*\* `([\w-]+)`", re.M)
SPEC_ROUTES_LINE = re.compile(r"Routes work to (.*)")
SPECIALIST_COUNT = re.compile(r"\bits (\w+) specialists\b", re.I)
EDITOR_UI_AGENT = f"{AGENTS_DIR}/editor-ui-framework-engineer.md"
TEXT_STACK_SECTION = "Engine text stack"
CHIEF_AGENT = f"{AGENTS_DIR}/chief-engine-architect.md"
WRITER_AGENT = f"{AGENTS_DIR}/engine-technical-writer.md"
SIM_LEAD_AGENT = f"{AGENTS_DIR}/simulation-systems-lead.md"
LEVEL_EDITOR_AGENT = f"{AGENTS_DIR}/level-editor-engineer.md"
SCRIPTING_AGENT = f"{AGENTS_DIR}/scripting-runtime-engineer.md"
AUDIO_AGENT = f"{AGENTS_DIR}/audio-engine-engineer.md"
CONCURRENCY_AGENT = f"{AGENTS_DIR}/concurrency-job-system-engineer.md"
ONLINE_AGENT = f"{AGENTS_DIR}/online-services-engineer.md"
PHYSICS_AGENT = f"{AGENTS_DIR}/physics-simulation-engineer.md"
ANIMATION_AGENT = f"{AGENTS_DIR}/animation-systems-engineer.md"
RULES_DIR = ".claude/rules"
SCRIPTING_RULE = f"{RULES_DIR}/scripting-code.md"
SIMULATION_RULE = f"{RULES_DIR}/simulation-code.md"
AUDIO_RULE = f"{RULES_DIR}/audio-code.md"
ENGINE_RULE = f"{RULES_DIR}/engine-code.md"
NAMED_INCLUDE_PATH = re.compile(r"(engine/[\w/{},.<>-]*?\binclude/[\w/{},.<>-]*)")
SAMPLE_HEADER = "x.h"
HEADER_SUFFIXES = (".h", ".hpp")
SIMD_MATH_WRONG_ROUTE = re.compile(r"physics-simulation-engineer|simulation-systems-lead")
EVIDENCE_LEDGER = "docs/research/aaa-engine-support-2026/evidence.jsonl"
CROSSBEAM_AARCH64_EVIDENCE = "E316"
QUOTE_WORD = re.compile(r"[\w.-]*\w")
# R74: reject when the host's struct_size is smaller than this version's struct.
SHORT_TABLE_REJECTED = re.compile(r"<\s*(?:(?:core|std)::mem::)?size_of::<")
WRONG_SIZE_DIRECTION = re.compile(r"(?:>|>=|!=|==)\s*(?:(?:core|std)::mem::)?size_of::<")


def custom_agents():
    """{name: text} of every agent with a Custom statement line."""
    out = {}
    for path in sorted((ROOT / AGENTS_DIR).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if CUSTOM_TEXT_LINE.search(text):
            out[path.stem] = text
    return out


def body(text):
    return FRONTMATTER.sub("", text, count=1)


def opener(text):
    """The agent's prose before its first second-level heading."""
    return body(text).split("\n## ", 1)[0]


def flat(text):
    return " ".join(text.split())


class OwnershipClaims(unittest.TestCase):
    """R55, R62: an agent's opener and Core Responsibilities claim only the
    layout rows it owns (custom-engine-layout.md is the one statement of
    path -> owner; plan Q3)."""

    def test_agent_opening_claims_match_layout(self):
        rows = layout_rows()
        problems = []
        for name, text in custom_agents().items():
            claims = []
            for clause in OPENER_CLAIM.finditer(PARENTHESISED.sub("", flat(opener(text)))):
                claims += [("opener", p) for p in re.findall(CLAIMED_PATH, clause[1])]
            duties = section_text(body(text), DUTY_SECTION) or ""
            for line in duties.splitlines():
                claims += [(DUTY_SECTION, p) for p in RESPONSIBILITY_CLAIM.findall(line)]
            for where, path in claims:
                row = resolve_layout_row(path, rows)
                owner = row_owner(row) if row else None
                if owner != name:
                    problems.append(f"{name} ({where}) claims `{path}`, whose layout owner is {owner}")
        self.assertEqual(problems, [])

    def test_simd_math_is_not_routed_to_physics(self):
        # engine/math/ (SIMD primitives) is ecs-dod-architect's row; physics
        # supplies collision primitives to it, so no agent routes SIMD math to
        # physics or to physics' lead.
        problems = [f"{path.name}:{number}"
                    for path in sorted((ROOT / AGENTS_DIR).glob("*.md"))
                    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                    if "SIMD math" in line and SIMD_MATH_WRONG_ROUTE.search(line)]
        self.assertEqual(problems, [])


def layout_reports():
    """{lead: {agent, ...}}: the owners whose layout Lead it is, plus the
    agents with no layout row whose `Reports to:` names it (Q9a's agents
    without a row, e.g. level-editor-engineer)."""
    out = {}
    for row in layout_rows():
        lead, owner = row_lead(row), row_owner(row)
        if lead and lead != "none" and owner and owner != lead:
            out.setdefault(lead, set()).add(owner)
    for name, text in custom_agents().items():
        match = REPORTS_TO.search(text)
        if match and match[1] in out:
            out[match[1]].add(name)
    return out


class LeadRouting(unittest.TestCase):
    """R57: a lead's stated routes, and its spec, name every owner whose
    layout Lead it is, and a stated count of its specialists is that number."""

    def test_routes_to_line_names_every_layout_report(self):
        problems = []
        for lead, owners in layout_reports().items():
            text = read(f"{AGENTS_DIR}/{lead}.md")
            for match in ROUTES_TO_LINE.finditer(text):
                missing = owners - set(re.findall(r"`([\w-]+)`", match[1]))
                if missing:
                    problems.append(f"{lead} 'Routes to:' leaves out {sorted(missing)}")
        self.assertEqual(problems, [])

    def test_lead_spec_names_every_layout_report(self):
        problems = []
        for lead, owners in layout_reports().items():
            spec = ROOT / CUSTOM_AGENT_SPEC_DIR / f"{lead}.md"
            if not spec.exists():
                continue
            text = spec.read_text(encoding="utf-8")
            # The spec's summary names every layout report, whether the
            # agent states its routes on a "Routes to:" line or in a table.
            for match in SPEC_ROUTES_LINE.finditer(text):
                missing = {o for o in owners if o not in match[1]}
                if missing:
                    problems.append(f"{spec.name} 'Routes work to' leaves out {sorted(missing)}")
            for match in SPECIALIST_COUNT.finditer(text):
                if NUMBER_WORDS.get(match[1].lower()) != len(owners):
                    problems.append(f"{spec.name} says '{match[0]}'; layout rows and "
                                    f"Reports-to lines give {len(owners)}")
        self.assertEqual(problems, [])


class TextRuntimeOwner(unittest.TestCase):
    """R4, R131 under AM28 D1: ui-programmer owns the runtime text stack in
    engine/ui/; editor-ui-framework-engineer consumes it under an ADR."""

    def test_editor_ui_consumes_the_text_runtime(self):
        section = section_text(read(EDITOR_UI_AGENT), TEXT_STACK_SECTION)
        self.assertIsNotNone(section, f"{EDITOR_UI_AGENT} has no '{TEXT_STACK_SECTION}' section")
        section = flat(section)
        self.assertNotRegex(section, r"\bYou own\b")
        for needed in ("`ui-programmer`", "`engine/ui/`", "ADR"):
            self.assertIn(needed, section)


class ToolsSplit(unittest.TestCase):
    """R129 (chief part) under AM28 D6: tools/ci/, tools/build/ and cook-side
    tools are asset-build-tooling-engineer's; standalone pipeline and batch
    tools, validators and report generators are tools-programmer's. A chief
    line that hands pipeline tools to tools-programmer states the split."""

    def test_chief_states_the_tools_split(self):
        lines = [line for line in read(CHIEF_AGENT).splitlines()
                 if "`tools-programmer`" in line and "pipeline" in line]
        self.assertTrue(lines, "the chief no longer routes pipeline tools: update this test")
        for line in lines:
            for needed in ("standalone", "`asset-build-tooling-engineer`", "`tools/ci/`", "`tools/build/`"):
                self.assertIn(needed, line)


def fenced_blocks(text, language):
    """Bodies of the ```language fences in text, in order."""
    return re.findall(rf"^```{language}[ \t]*\n(.*?)^```", text, re.M | re.S)


def outside_cplusplus_guards(code):
    """code with every `#ifdef __cplusplus` ... `#endif` region removed."""
    return re.sub(r"^#ifdef __cplusplus\b.*?^#endif.*?$", "", code, flags=re.M | re.S)


class ChiefAbiExamples(unittest.TestCase):
    """chief-engine-architect's API and plugin-ABI statements."""

    def test_deprecation_window_names_its_unit(self):
        # R47: patch tags on a release branch must not count toward a window
        # stated in "releases"; the ADR names the unit, minor versions by default.
        bullet = re.search(r"^- \*\*Deprecation window\*\*.*?(?=^- |\Z)", read(CHIEF_AGENT), re.M | re.S)
        self.assertIsNotNone(bullet)
        sentence = flat(bullet[0])
        self.assertRegex(sentence, r"\bminor versions?\b")
        self.assertRegex(sentence, r"\bpatch\b[^.]*\b(?:do not|don't|never) count")

    def test_rust_plugin_entry_documents_safety_and_checks_the_table(self):
        # R74: an `extern "C" fn` taking a raw pointer must not form `&*ptr`
        # unchecked (a safe fn trips clippy::not_unsafe_ptr_arg_deref, deny by
        # default), and an unsafe one documents its contract.
        entries = [block for block in fenced_blocks(read(CHIEF_AGENT), "rust")
                   if re.search(r'extern "C" fn \w+\([^)]*\*const', block)]
        self.assertTrue(entries, "no Rust plugin entry block: update this test")
        for block in entries:
            sigs = list(re.finditer(r'^pub (unsafe )?extern "C" fn \w+\((\w+): \*const', block, re.M))
            self.assertTrue(sigs, "no `pub extern \"C\" fn name(ptr: *const ...)`: update this test")
            for sig in sigs:
                if sig[1]:
                    # An unsafe pub fn states its contract (clippy::missing_safety_doc).
                    preamble = re.search(r"(?:^(?:///|#\[).*\n)*\Z", block[:sig.start()], re.M)[0]
                    self.assertRegex(preamble, r"(?m)^/// # Safety$", "unsafe entry without a `/// # Safety` doc")
                deref = block.find(f"&*{sig[2]}", sig.end())
                self.assertGreaterEqual(deref, 0, "entry never forms the table reference: update this test")
                # Whatever the fn's safety, the table is checked before `&*`:
                # null, then an older host's shorter table is rejected.
                checks = block[sig.end():deref]
                self.assertIn(f"{sig[2]}.is_null()", checks)
                self.assertIn("struct_size", checks)
                self.assertRegex(checks, SHORT_TABLE_REJECTED, "a table shorter than this version's struct is not rejected")
                self.assertNotRegex(checks, WRONG_SIZE_DIRECTION)

    def test_plugin_abi_header_is_c(self):
        # R75: a C ABI header a C translation unit (and bindgen without
        # `-x c++`) can parse: extern "C" only under `#ifdef __cplusplus`, and
        # no C++-only syntax outside such a guard.
        headers = [block for block in fenced_blocks(read(CHIEF_AGENT), r"(?:c|cpp)")
                   if "plugin_abi.h" in block]
        self.assertTrue(headers, "no plugin_abi.h block: update this test")
        for block in headers:
            self.assertIn("#ifdef __cplusplus", block)
            plain = outside_cplusplus_guards(block)
            for cpp_only in ('extern "C"', "noexcept", r"\busing\b"):
                self.assertNotRegex(plain, cpp_only)


def named_public_headers():
    """{(agent file, concrete header path)} for every `engine/.../include/...`
    path the agents name, braces expanded; a directory or a cut-off brace
    list stands for one header inside it."""
    out = set()
    for path in sorted((ROOT / AGENTS_DIR).glob("*.md")):
        for named in NAMED_INCLUDE_PATH.findall(path.read_text(encoding="utf-8")):
            if "<" in named:
                continue
            if named.count("{") > named.count("}"):
                named = named[:named.rfind("{")]
            for concrete in expand(named):
                if concrete.endswith("/"):
                    concrete += SAMPLE_HEADER
                if "/include/" in concrete and concrete.endswith(HEADER_SUFFIXES):
                    out.add((path.name, concrete))
    return out


class WriterHeaderGlob(unittest.TestCase):
    """R37, R95 (writer part): the writer's public-header Grep glob covers
    every public header the agents name, nested modules included, under the
    Grep/Glob semantics where `*` does not cross `/`."""

    def test_writer_glob_covers_every_named_public_header(self):
        tooling = section_text(read(WRITER_AGENT), "Tooling")
        globs = [g for g in re.findall(r'glob: "([^"]+)"', tooling or "") if "include" in g]
        self.assertTrue(globs, "the writer's Tooling names no public-header glob: update this test")
        patterns = [p for g in globs for p in expand(g)]
        headers = named_public_headers()
        self.assertTrue(headers)
        missed = sorted(f"{agent}: {header}" for agent, header in headers
                        if not any(glob_match(p, header) for p in patterns))
        self.assertEqual(missed, [])

    def test_job_contract_is_on_the_referenced_data(self):
        # R100: `job` is a by-value parameter, gone when submit returns; the
        # lifetime contract binds the data it refers to.
        text = read(WRITER_AGENT)
        self.assertEqual(re.findall(r"`job` must outlive[^\n]*", text), [])
        self.assertRegex(flat(text), r"data `job` refers to must stay valid until `counter` reaches zero")


class SimulationOrder(unittest.TestCase):
    """R79: motor targets drive the step, so motor-driven ragdolls also sample
    animation before it (Jolt's PoweredRigTest sets them in PrePhysicsUpdate);
    the tag changes which output is authoritative, not the order."""

    def test_motor_driven_entities_keep_the_order(self):
        answer = re.search(r"\*\*Animation before or after physics\?\*\*(.*?)(?:\n\n|\Z)",
                           read(SIM_LEAD_AGENT), re.S)
        self.assertIsNotNone(answer)
        answer = flat(answer[1])
        self.assertNotRegex(answer, r"order flips")
        self.assertRegex(answer, r"motor targets?[^.]*before the step")


def prose_items(text):
    """Paragraphs and list items of text, each joined onto one line."""
    items, current = [], []
    for line in text.splitlines():
        if not line.strip() or re.match(r"\s*(?:[-*]|\d+\.)\s", line) or line.startswith(("#", "|", "```")):
            if current:
                items.append(" ".join(current))
            current = [line.strip()] if line.strip() and not line.startswith(("#", "|", "```")) else []
        else:
            current.append(line.strip())
    if current:
        items.append(" ".join(current))
    return items


class ConcurrencyTooling(unittest.TestCase):
    """concurrency-job-system-engineer and the Rust tooling statements."""

    def test_loom_model_swaps_the_slot_cell(self):
        # R80: loom tracks non-atomic accesses only through
        # loom::cell::UnsafeCell (with/with_mut); swapping only the atomics
        # leaves the slot write the Release store publishes unmodelled.
        sentence = next((s for s in prose_items(read(CONCURRENCY_AGENT)) if s.startswith("Verify with `loom`")), None)
        self.assertIsNotNone(sentence)
        self.assertIn("loom::cell::UnsafeCell", sentence)
        self.assertRegex(sentence, r"`with`.*`with_mut`|`with_mut`.*`with`")

    def test_aarch64_padding_reason_is_attributed(self):
        # R82: the 128-byte aarch64 line is crossbeam's stated reason, not a
        # hardware fact (generic arm64 L1_CACHE_BYTES is 64).
        section = section_text(read(CONCURRENCY_AGENT), "False sharing")
        self.assertRegex(flat(section), r"aarch64 \([^)]*crossbeam")
        # What is attributed to crossbeam says only what its comment says
        # (ledger E316): a hedge such as "some" belongs outside the quote.
        reason = re.search(r"crossbeam's stated reason: ([^)]*)\)", flat(section))
        self.assertIsNotNone(reason, "no 'crossbeam's stated reason: ...' parenthetical")
        quote = next(json.loads(line)["quote"] for line in read(EVIDENCE_LEDGER).splitlines()
                     if line.strip() and json.loads(line)["evidence_id"] == CROSSBEAM_AARCH64_EVIDENCE)
        quoted = set(QUOTE_WORD.findall(quote.lower()))
        extra = [w for w in QUOTE_WORD.findall(reason.group(1).lower())
                 if w not in quoted and w.rstrip("s") not in quoted]
        self.assertEqual(extra, [], f"words crossbeam does not say ({CROSSBEAM_AARCH64_EVIDENCE}): {quote}")

    def test_cargo_metadata_is_not_the_cfg_source(self):
        # R96: cargo metadata reports packages, dependencies and Cargo
        # features, not rustc target features or --cfg flags from RUSTFLAGS or
        # .cargo/config.toml.
        problems = [f"{name}: {item[:100]}" for name, text in custom_agents().items()
                    for item in prose_items(text)
                    if re.search(r"cargo metadata`? for [^;.]*(?:target features|\bcfg\b)", item)]
        self.assertEqual(problems, [])

    def test_miri_ffi_sentence_matches_its_claim(self):
        # R91: ledger C111 says Miri has no access to *most* FFI and that its
        # native-library flag is Unix-only; the agent says no more than that.
        item = next((i for i in prose_items(read(ONLINE_AGENT)) if "Miri" in i and "FFI" in i), None)
        self.assertIsNotNone(item)
        self.assertIn("most FFI", item)
        self.assertNotRegex(item, r"Miri cannot call")


def custom_agents_and_rules():
    """{path: text} of the Custom agents and of every rule file."""
    out = {f"{AGENTS_DIR}/{name}.md": text for name, text in custom_agents().items()}
    for path in sorted((ROOT / RULES_DIR).glob("*.md")):
        out[path.relative_to(ROOT).as_posix()] = path.read_text(encoding="utf-8")
    return out


class FloatingPointDeterminism(unittest.TestCase):
    """R93, R94: what pins FP results, per compiler and per machine."""

    def test_fp_precise_is_not_contraction_off_under_clang_cl(self):
        # R93: clang-cl's /fp:precise is -ffp-model=precise, which keeps
        # -ffp-contract=on (clang Options.td, Clang Users Manual); MSVC before
        # VS 2022 also contracted under /fp:precise.
        problems = [f"{path}: {item[:90]}" for path, text in custom_agents_and_rules().items()
                    for item in prose_items(text)
                    if "/fp:precise" in item and re.search(r"contract", item, re.I)
                    and not re.search(r"clang-cl|/clang:-ffp-contract=off", item)]
        self.assertEqual(problems, [])

    def test_engine_transcendentals_cover_cross_machine(self):
        # R94: the x64 CRT and glibc pick transcendental implementations per
        # CPU, so the same binary differs across machines.
        for path in (PHYSICS_AGENT, ANIMATION_AGENT):
            with self.subTest(path=path):
                items = [i for i in prose_items(read(path))
                         if re.search(r"(?i)transcendental|`std::sin`", i)]
                self.assertTrue(items)
                for item in items:
                    self.assertRegex(item, r"(?i)cross-machine")
                    self.assertNotRegex(item, r"when cross-platform|where cross-platform")
        answer = re.search(r"\*\*Float or fixed point\?\*\*(.*?)(?:\n\n|\Z)", read(PHYSICS_AGENT), re.S)
        self.assertIsNotNone(answer)
        self.assertNotRegex(flat(answer[1]), r"usually for cross-machine")


class EditorAndScripting(unittest.TestCase):
    """Level editor, scripting runtime and audio statements."""

    def test_level_editor_does_not_offer_what_it_bans(self):
        # R97: Anti-Patterns ban one file per cell for placed entities; Core
        # Responsibilities must not offer it.
        text = read(LEVEL_EDITOR_AGENT)
        duties = flat(section_text(text, DUTY_SECTION) or "")
        banned = flat(section_text(text, "Anti-Patterns") or "")
        self.assertRegex(banned, r"per cell for placed entities")
        self.assertNotRegex(duties, r"one file per cell")

    def test_lua_baseline_is_current(self):
        # R98: lua.org/versions.html: Lua 5.5 is current and "There will be
        # no further releases of Lua 5.4."
        text = read(SCRIPTING_AGENT)
        options = next((i for i in prose_items(text) if "**The language is an ADR.**" in i), None)
        self.assertIsNotNone(options)
        self.assertIn("Lua 5.5", options)
        table_rows = [line for line in text.splitlines() if line.startswith("| Lua")]
        self.assertTrue(table_rows)
        for row in table_rows:
            self.assertIn("Lua 5.5", row)
        self.assertIn('collectgarbage("param"', flat(text))

    def test_lua_sandbox_names_every_escape(self):
        # R101: loadfile reads any file, package.loadlib links a native
        # library without require, and the debug library "can compromise
        # otherwise secure code" (Lua manual 6.10).
        sandbox = section_text(read(SCRIPTING_RULE), "Sandbox — no ambient authority")
        self.assertIsNotNone(sandbox)
        lua = next((i for i in prose_items(sandbox) if "In Lua" in i), None)
        self.assertIsNotNone(lua)
        for name in ("`loadfile`", "`debug`", "`package.loadlib`", "`string.dump`", "`dofile`", "`load`"):
            self.assertIn(name, lua)
        self.assertIn("not a security boundary", flat(sandbox))

    def test_audio_grep_finds_its_own_incorrect_allocations(self):
        # R99: the Tooling grep must match the allocations and I/O that the
        # Incorrect examples of the agent and of audio-code.md show (C++
        # push_back as well as Rust push); Vec::new does not allocate (Rust
        # std docs).
        text = read(AUDIO_AGENT)
        tooling = flat(section_text(text, "Tooling") or "")
        pattern = re.search(r"patterns like `([^`]+)`", tooling)
        self.assertIsNotNone(pattern, "no grep pattern in the audio Tooling section")
        regex = re.compile(pattern[1])
        blocks = re.findall(r"^\*\*Incorrect[^\n]*\n```\w*\n(.*?)^```", text, re.M | re.S)
        rule_incorrect = re.search(r"^\*\*Incorrect\*\*:?\n(.*?)(?=^#|^\*\*|\Z)", read(AUDIO_RULE), re.M | re.S)
        self.assertIsNotNone(rule_incorrect, "no **Incorrect** examples in audio-code.md: update this test")
        rule_blocks = re.findall(r"^```\w*\n(.*?)^```", rule_incorrect[1], re.M | re.S)
        self.assertTrue(rule_blocks, "no fenced Incorrect example in audio-code.md: update this test")
        lines = [line for block in blocks + rule_blocks for line in block.splitlines()
                 if re.search(r"(?://|#).*(?:allocat|I/O)", line)]
        self.assertTrue(lines, "no allocating Incorrect line: update this test")
        problems = [f"missed: {line.strip()}" for line in lines if not regex.search(line)]
        if "Vec::new" in pattern[1]:
            problems.append("pattern lists Vec::new, which does not allocate")
        self.assertEqual(problems, [])


class SimulationAndAudioRules(unittest.TestCase):
    """simulation-code.md, audio-code.md and engine-code.md statements."""

    def test_fixed_step_accumulator_is_clamped(self):
        # R104: an unclamped accumulator spirals (Fiedler, "Fix Your
        # Timestep!", the source of ledger C78); core-systems-lead clamps the
        # same loop.
        accumulators = [block for block in fenced_blocks(read(SIMULATION_RULE), r"(?:cpp|rust)")
                        if "accumulator" in block]
        self.assertTrue(accumulators, "no accumulator example: update this test")
        for block in accumulators:
            self.assertRegex(block, r"accumulator\w*\s*\+=\s*(?:std::)?min\(|\.min\(|max_steps")

    def test_denormal_mode_reaches_device_owned_callback_threads(self):
        # R105: a device API can run the callback on a thread it owns (AAudio:
        # "a real-time thread owned by AAudio"), where no engine thread-start
        # hook runs; the mode is set at callback entry and restored.
        audio = next((i for i in prose_items(read(AUDIO_RULE)) if re.search(r"(?i)denormal", i)), None)
        self.assertIsNotNone(audio)
        self.assertRegex(audio, r"callback entry")
        self.assertRegex(audio, r"restores")
        engine = next((i for i in prose_items(read(ENGINE_RULE)) if re.search(r"denormal modes", i)), None)
        self.assertIsNotNone(engine)
        self.assertRegex(engine, r"threads the engine creates")
        self.assertRegex(engine, r"callback entry")


if __name__ == "__main__":
    unittest.main()
