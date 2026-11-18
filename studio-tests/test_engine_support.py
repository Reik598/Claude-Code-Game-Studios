"""Executable structural contracts for engine support (Python stdlib only).

Run: python -m unittest discover -s studio-tests -p 'test_engine_support.py' -v
These check discoverability and routing, not Claude's behavioral compliance.
"""
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
# The base release the engine-support change is measured against
# (docs/research/aaa-engine-support-2026/fix-plan.md, "Baselines").
BASE_RELEASE = "abc0de7"

# R9. Always-loaded files the reviewed change already edited: base is the wrong
# baseline for them, so they are pinned to their content in the reviewed
# worktree (recorded 2026-11-16, fix plan fix 1.3). The digest is sha256 over
# the file's bytes with every "\r" removed, so a CRLF checkout gives the same
# value. A later edit to one of these files must change its value here, in the
# same diff, where review sees it.
ALWAYS_LOADED_PINNED = {
    # Re-pinned at fix plan AM32, task 7.1: the agent count line, 74 -> 77.
    "CLAUDE.md": "bb4322d7364e8d986f6e3a5302145facdd8168456eada598952b7c18bd1d24b3",
    ".claude/docs/directory-structure.md":
        "287fb123fc227b1f1538172247f933eeee544787707a96fbbc7d8d7c241e221f",
    # Re-pinned at fix plan AM38(d), task 4.2: the pointer to escalation-ladder.md.
    ".claude/docs/coordination-rules.md":
        "c46b8be11aa86cfbfe934436a7e4d37749d9b7a5fab4ea9695ca4a78790edd35",
}
# R9. Always-loaded files the reviewed change left untouched: compared with the
# base release, where only added blocks that name Custom are allowed.
ALWAYS_LOADED_ADDITIVE = {".claude/docs/coding-standards.md"}
# The checklist line /gate-check prints on every engine but Custom
# (.claude/skills/gate-check/references/gate-pre-production.md:96-98).
GATE_CHECK_SKIP_LINE = "Custom engine additions: skipped"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def lf_sha256(data):
    return hashlib.sha256(data.replace(b"\r", b"")).hexdigest()


def base_release_file(path):
    """The file's text at BASE_RELEASE, or None when the commit is absent."""
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_RELEASE}:{path}"],
                            capture_output=True)
    return result.stdout.decode("utf-8") if result.returncode == 0 else None


def custom_scoped_catalog_steps(catalog_text):
    """Ids of the `phases:` steps in workflow-catalog.yaml that carry
    `engine: Custom`, in catalog order."""
    phases = re.search(r"^phases:\n(.*?)(?=^\S|\Z)", catalog_text.replace("\r", ""), re.M | re.S)
    found, current = [], None
    for line in (phases[1] if phases else "").splitlines():
        step = re.match(r"^      - id: *([\w-]+)", line)
        if step:
            current = step[1]
        elif current and re.match(r"^        engine: *\"?Custom\"? *$", line):
            found.append(current)
    return found


def added_block_violations(base_text, text, token="Custom"):
    """Changes from base_text to text other than added blocks naming token."""
    base_lines = base_text.replace("\r", "").splitlines()
    lines = text.replace("\r", "").splitlines()
    problems = []
    matcher = difflib.SequenceMatcher(a=base_lines, b=lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "delete"):
            problems.append(f"base lines {i1 + 1}-{i2} removed or changed")
        elif tag == "insert" and token not in "\n".join(lines[j1:j2]):
            problems.append(f"added block at lines {j1 + 1}-{j2} does not name {token}")
    return problems


ADDED_UNIT_START = re.compile(r"^\s*(?:[-*+]|\d+\.)\s|^#")


def added_unit_violations(base_text, text, token="Custom"):
    """Changes from base_text to text other than added paragraphs and list
    items that each name token (fix plan AM16(b), P5 critic F10: an
    always-loaded doc's unit is the paragraph or list item, not the diff block,
    so a line placed next to a Custom block must name Custom itself). A unit is
    a run of added lines up to a blank line; a list item or heading line starts
    a new unit, and its indented continuation lines belong to it."""
    base_lines = base_text.replace("\r", "").splitlines()
    lines = text.replace("\r", "").splitlines()
    problems = []
    matcher = difflib.SequenceMatcher(a=base_lines, b=lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "delete"):
            problems.append(f"base lines {i1 + 1}-{i2} removed or changed")
        elif tag == "insert":
            units, current = [], None
            for number in range(j1, j2):
                line = lines[number]
                if not line.strip():
                    current = None
                elif current is None or ADDED_UNIT_START.match(line):
                    current = [number]
                    units.append(current)
                else:
                    current.append(number)
            for unit in units:
                if token not in "\n".join(lines[n] for n in unit):
                    problems.append(f"added paragraph or item at lines {unit[0] + 1}-{unit[-1] + 1} "
                                    f"does not name {token}")
    return problems


def expand(pattern):
    match = re.search(r"\{([^{}]+)\}", pattern)
    if not match:
        return [pattern]
    return [p for choice in match[1].split(",")
            for p in expand(pattern[:match.start()] + choice + pattern[match.end():])]


def glob_regex(pattern):
    """Translate one brace-free `paths` glob to a regex, per the documented
    semantics: `**` crosses `/`, `*` and `?` do not, a pattern with no `/`
    matches at any depth, and a leading `/` anchors to the base directory."""
    anchored = pattern.startswith("/") or "/" in pattern
    body = pattern.lstrip("/")
    out, i = [], 0
    while i < len(body):
        if body.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif body.startswith("**", i):
            out.append(".*")
            i += 2
        elif body[i] == "*":
            out.append("[^/]*")
            i += 1
        elif body[i] == "?":
            out.append("[^/]")
            i += 1
        elif body[i] == "[" and "]" in body[i + 2:]:
            end = body.index("]", i + 2)
            chars = body[i + 1:end].replace("\\", "\\\\")
            out.append("[^" + chars[1:] + "]" if chars.startswith("!") else "[" + chars + "]")
            i = end + 1
        else:
            out.append(re.escape(body[i]))
            i += 1
    return ("" if anchored else "(?:.*/)?") + "".join(out)


def glob_match(pattern, path):
    return re.fullmatch(glob_regex(pattern), path) is not None


def matches(rule, path):
    header = read(f".claude/rules/{rule}.md").split("---", 2)[1]
    patterns = re.findall(r'^  - "([^"]+)"', header, re.M)
    return any(glob_match(p, path) for item in patterns for p in expand(item))


def rule_globs(rule):
    header = read(f".claude/rules/{rule}.md").split("---", 2)[1]
    return [p for item in re.findall(r'^  - "([^"]+)"', header, re.M) for p in expand(item)]


# R3. The one file that holds module -> rule -> owner -> lead (fix plan Q3).
LAYOUT = ".claude/docs/custom-engine-layout.md"
# A shared rule's glob is a Custom glob when it starts under a Custom root.
CUSTOM_ROOTS = ("engine/", "crates/", "game/")
NUMBER_WORDS = {w: n for n, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve".split())}
AGENT_CELL = re.compile(r"`([\w-]+)`")
NONE_WITH_REASON = re.compile(r"^none\s*[—:-]+\s*\S")


def agent_names():
    return {p.stem for p in (ROOT / ".claude/agents").glob("*.md")}


def layout_rows():
    """Rows of the layout's tables: dicts keyed by the header cells, plus the
    line number and the backticked paths of the first cell."""
    rows, header = [], None
    for number, line in enumerate(read(LAYOUT).splitlines(), 1):
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set(line) <= set("|-: "):
            continue
        row = dict(zip(header, cells), line=number, paths=re.findall(r"`([^`]+)`", cells[0]))
        rows.append(row)
    return rows


def row_owner(row):
    match = AGENT_CELL.search(row.get("Owner agent", ""))
    return match[1] if match else None


def row_sub_owners(row):
    """`sub/` -> `agent` notes in an Owner cell (the game/src/ split by path)."""
    return dict(re.findall(r"`([\w-]+/)` → `([\w-]+)`", row.get("Owner agent", "")))


def row_lead(row):
    """The Lead cell's agent, "none" for a reasoned none, or None."""
    cell = row.get("Lead")
    if cell is None:
        return None
    if NONE_WITH_REASON.match(cell):
        return "none"
    match = AGENT_CELL.search(cell)
    return match[1] if match else None


def row_rules(row):
    return re.findall(r"`([\w-]+)\.md`", row.get("Path rule", ""))


def row_globs(row):
    """(glob, literal path) per path of the row; an engine/ path also stands
    for its crates/ twin (the layout's own statement)."""
    out = []
    for path in row["paths"]:
        glob = path + "**" if path.endswith("/") else path
        out.append((glob, path))
        if glob.startswith("engine/"):
            out.append(("crates/" + glob[len("engine/"):], path))
    return out


def glob_sample(pattern):
    """One concrete path a brace-free glob matches."""
    sample = pattern.lstrip("/").replace("**/", "x/").replace("**", "x")
    return sample.replace("*", "x").replace("?", "x")


# Phase 3 critic F9: the rules of the two layout rows that cut across modules
# (the tests row and the build-files row); they decide owner and lead only for
# a path no other row covers.
CROSS_CUTTING_RULES = {"test-standards", "build-files"}


def resolve_layout_row(path, rows):
    """The most specific layout row whose paths cover `path`, or None, by the
    layout's precedence rule (AM7, Phase 3 critic F9): any other row beats the
    tests and build-files rows; between rows of the same kind a path without a
    wildcard beats one with `*`, and then the longer path wins."""
    hits = layout_row_ranks(path, rows)
    return max(hits, key=lambda hit: hit[0])[1] if hits else None


def layout_row_ranks(path, rows):
    """(rank, row) for each row path that covers `path`; resolve_layout_row
    takes the highest rank."""
    sample = glob_sample(path + "x" if path.endswith("/") else path)
    return [((not set(row_rules(row)) & CROSS_CUTTING_RULES, "*" not in literal, len(literal)), row)
            for row in rows for glob, literal in row_globs(row) if glob_match(glob, sample)]


def layout_rows_for(path, rows):
    """Every layout row whose paths cover the concrete `path`."""
    return [row for row in rows if any(glob_match(glob, path) for glob, _ in row_globs(row))]


# Fix 4.10 (owner answer 5.1): the four story skills, and where an engine
# module's spec lives (it stands in for the GDD on Custom).
STORY_SKILLS = tuple(f".claude/skills/{s}/SKILL.md"
                     for s in ("create-epics", "create-stories", "story-readiness", "story-done"))
MODULE_SPEC_DIR = "docs/architecture/modules/"
# Fix plan AM9: /create-architecture's Phase 1, which 4.10's module layering
# reaches; untouched by the reviewed change, so it may gain Custom blocks only.
LAYERS_REFERENCE = ".claude/skills/create-architecture/references/1-layers.md"
# Fix 4.8: the line an absent engine-reference file is named by.
ABSENT_REFERENCE_LINE = "NOT SOURCEABLE — <file> is not present"
# Fix plan AM7: the sentence that opens the layout's precedence rule.
LAYOUT_PRECEDENCE = "A path that more than one row covers takes the Path rule of every row that covers it"


def layout_modules(rows):
    """Module name (path under engine/) -> its row."""
    return {path[len("engine/"):-1]: row for row in rows for path in row["paths"]
            if path.startswith("engine/") and path.endswith("/") and "*" not in path}


def custom_only_glob_root(glob):
    """A glob's literal prefix: its leading segments up to the first one with a
    wildcard, as a folder (`engine/`, `tools/editor/`), or a file name when the
    glob has no wildcard (`/CMakeLists.txt` -> `CMakeLists.txt`)."""
    segments = glob.lstrip("/").split("/")
    literal = [s for s in segments[:next((i for i, s in enumerate(segments) if set(s) & set("*?[{")),
                                         len(segments))]]
    return "/".join(literal) if len(literal) == len(segments) else "/".join(literal) + "/"


def custom_only_rules():
    rows = re.findall(r"^\| `([\w-]+)\.md` \|(.*)$", read(".claude/docs/rules-reference.md"), re.M)
    return {rule for rule, rest in rows if "Custom only" in rest}


def engine_wide_rules():
    """Rules the layout names on its `Engine-wide rule:` line (fix 3.3)."""
    return set(re.findall(r"`([\w-]+)\.md`", "\n".join(
        line for line in read(LAYOUT).splitlines() if line.startswith("Engine-wide rule"))))


# R3, test_routing_agrees_with_layout. The statement forms found in the tree
# when the test was written; a new form must be added here, or a copy of the
# mapping written in it goes unchecked (.claude/rules/skill-authoring.md:76-79).
#   Units: a table row; a list item with its indented continuation lines,
#   split into clauses at ";".
#   Pairs: a table row pairs the modules of its first module cell with the
#   first agent of its last cell; a clause "MODULES → `agent`"; a clause
#   "`agent` for MODULES"; a clause "`agent` owns MODULES"; a clause
#   "for MODULES ... under `agent`".
#   Module tokens: `engine/x/` (and deeper), `engine/{x,y}/`, and bare
#   `x/ y/` spans of module names (a single bare token only in a table row or
#   left of an arrow, where it cannot be a root folder in prose).
ROUTE_SCAN_DIRS = (".claude/agents", ".claude/skills", ".claude/docs")
LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s")
ARROW = re.compile(r"→|->")


def module_tokens(text, modules, allow_single_bare):
    found = []
    for span in re.findall(r"`([^`]+)`", text):
        braces = re.fullmatch(r"engine/\{([\w,]+)\}/?.*", span)
        if braces:
            found += braces[1].split(",")
        elif span.startswith("engine/") and "<" not in span and "*" not in span:
            rest = span[len("engine/"):].rstrip("/")
            if rest:
                known = [m for m in modules if rest == m or rest.startswith(m + "/")]
                found.append(max(known, key=len) if known else rest)
        else:
            tokens = span.split()
            if (tokens and all(re.fullmatch(r"[\w-]+/", t) and t[:-1] in modules for t in tokens)
                    and (len(tokens) > 1 or allow_single_bare)):
                found += [t[:-1] for t in tokens]
    return found


def routing_pairs(text, modules, agents):
    """(line, module, agent) for each routing statement in one file."""
    agent_re = re.compile(r"(?<![\w-])(" + "|".join(sorted(agents, key=len, reverse=True)) + r")(?![\w-])")
    lines = text.splitlines()
    units, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("|"):
            units.append(("row", i + 1, line))
        elif LIST_ITEM.match(line):
            start, body = i + 1, [line]
            while (i + 1 < len(lines) and lines[i + 1].strip() and lines[i + 1][:1] in " \t"
                   and not LIST_ITEM.match(lines[i + 1]) and not lines[i + 1].lstrip().startswith("|")):
                i += 1
                body.append(lines[i])
            units.append(("item", start, " ".join(body)))
        i += 1
    pairs = []
    for kind, number, unit in units:
        if kind == "row":
            cells = [c for c in unit.strip().strip("|").split("|")]
            filled = [c for c in cells if c.strip()]
            module_cell = next((c for c in cells if module_tokens(c, modules, True)), None)
            if module_cell is None or not filled or filled[-1] is module_cell:
                continue
            agent = agent_re.search(filled[-1])
            if agent:
                pairs += [(number, m, agent[1]) for m in module_tokens(module_cell, modules, True)]
            continue
        for clause in unit.split(";"):
            arrow = ARROW.search(clause)
            if arrow:
                agent = agent_re.search(clause[arrow.end():])
                if agent:
                    pairs += [(number, m, agent[1])
                              for m in module_tokens(clause[:arrow.start()], modules, True)]
            for verb in ("for", "owns"):
                for hit in re.finditer(rf"`?({agent_re.pattern})`? {verb} (.*)", clause):
                    pairs += [(number, m, hit[1]) for m in module_tokens(hit[3], modules, False)]
            # Phase 3 critic F5: "for MODULES you work under `agent`"
            # (network-programmer.md, the two-leads bullet).
            for hit in re.finditer(rf"\bfor (.*?)\bunder `?({agent_re.pattern})`?", clause):
                pairs += [(number, m, hit[2]) for m in module_tokens(hit[1], modules, False)]
    return pairs


# Phase 10 R1/R3: the form "`agent` (concern, concern, ...)" routes the named
# concerns to the agent ("route engine findings to `core-systems-lead`
# (memory, jobs, ECS, physics)"). A concern word stands for one layout module;
# a word not listed here is not a module concern and is not checked.
CONCERN_MODULES = {"physics": "physics", "audio": "audio", "animation": "animation",
                   "scripting": "scripting", "memory": "memory", "jobs": "jobs", "ecs": "ecs"}


def prose_units(text):
    """(first line, text) per paragraph or list item, joined across its wrapped
    lines; table rows, headings and fence lines end a unit and are not one."""
    units, body, start = [], [], 0
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        breaks = not stripped or stripped.startswith(("|", "#", "```")) or LIST_ITEM.match(line)
        if breaks:
            if body:
                units.append((start, " ".join(body)))
            body = []
            if not stripped or stripped.startswith(("|", "#", "```")):
                continue
        if not body:
            start = number
        body.append(stripped)
    if body:
        units.append((start, " ".join(body)))
    return units


def concern_pairs(text, agents):
    """(line, module, agent) for each "`agent` (concern, ...)" statement."""
    agent_re = "|".join(sorted(agents, key=len, reverse=True))
    pairs = []
    for number, unit in prose_units(text):
        for hit in re.finditer(rf"`({agent_re})` \(([^()]*)\)", unit):
            for concern in hit[2].split(","):
                module = CONCERN_MODULES.get(concern.strip().lower())
                if module:
                    pairs.append((number, module, hit[1]))
    return pairs


# Phase 10 R1-R3/R54: the Custom leads an agent might enumerate when it routes
# by module, the phrases that make a sentence a routing statement, and the
# phrases that cite a module map in the agent file itself.
CUSTOM_ENGINE_LEADS = ("core-systems-lead", "rendering-lead", "simulation-systems-lead", "editor-architect")
ENUMERATED_LEADS_MIN = 3
ROUTING_PHRASE = re.compile(r"\b(?:rout\w*|go(?:es)? to|hand\w*|decides? the lead|owning (?:engine )?lead)\b", re.I)
LOCAL_MAP_PHRASE = re.compile(r"\b(?:module table|map) above\b")
# Phase 10 R4/R131 (AM28 D1): concerns the layout files under one module, so
# only that module's owner may claim them: (concern pattern, module path).
CONCERN_OWNER_MODULES = ((re.compile(r"(?i)text runtime|text stack|\bshaping\b"), "engine/ui/"),)
ENGINE_COVERAGE_DOC = ".claude/docs/engine-development-coverage.md"
# A sentence break that is not an "e.g." or "i.e."; a negated sentence.
SENTENCE_SPLIT = re.compile(r"(?<=\.)(?<!e\.g\.)(?<!i\.e\.)\s+(?=[A-Z`*])")
NEGATED = re.compile(r"\bNOT\b|\bnever\b|n't\b")
# Phase 10 R129 (AM28 D6): a pipeline-tools ownership statement, and the docs
# outside .claude/agents and .claude/rules that make one.
PIPELINE_TOOLS = re.compile(r"(?i)(?<!art )\bpipeline (?:and batch )?(?:tools|scripts)\b")
PIPELINE_TOOLS_DOCS = (".claude/docs/agent-roster.md", "docs/WORKFLOW-GUIDE.md", "README.md")
TOOLS_PROGRAMMER = "tools-programmer"
# A `tools/` path a statement assigns; "the `tools/` rows" cites the layout.
TOOLS_PATH = re.compile(r"`(tools/[^`]*)`(?!\s+rows?\b)")
# The hand-off forms that give the `tools/` paths of a clause to one agent
# ({a} is the agent-name alternation; "yours" is the agent file's own agent).
TOOLS_HANDOFF = (r"\b(?:are|is)(?: also)? `({a})`'s|\bby `({a})`|\bstays? with `({a})`|→ `({a})`"
                 r"|`({a})` (?:keeps|owns)\b|\b(?:are|is) (?:also )?(yours)\b")
# Phase 10 R4/R131 review: "`agent` owns ..." and "agent (owns ..." name the
# owner of what follows, up to the clause's end.
OWNS_CLAUSE = r"(?<![\w-])({a})(?![\w-])`?\s*\(?owns\b([^;)|]*)"
# Phase 10 R9/R49 (AM28 D2): the skill catalogs that label skills, the labels,
# and the gate a Custom-only skill stops with on any other engine.
SKILL_CATALOG_FILES = (".claude/docs/skills-reference.md", ".claude/docs/quick-start.md", "docs/WORKFLOW-GUIDE.md")
CUSTOM_ONLY_LABEL = "Custom engine:"
ANY_ENGINE_LABEL = "Any engine (Custom-oriented)"
CUSTOM_SKILL_GATE = "NOT ASSESSED — engine.name is not Custom"
# Phase 10 R5: /prototype's path question and the label it gives the browser
# sketch on a project that names an engine.
PROTOTYPE_PHASE3 = ".claude/skills/prototype/references/3-choose-path.md"
BROWSER_SKETCH_NOT_RECOMMENDED = "Browser sketch (not recommended here)"
PROTOTYPER_AGENT = ".claude/agents/prototyper.md"


# R12. The technical sections this plan adds, enumerated because "a section
# added by this plan" cannot be derived from an uncommitted tree. Phase 7
# extends it with every section it adds (.claude/rules/skill-authoring.md:76-79).
# Fix 3.4: the two network-code.md bullets the Custom section scopes.
NETWORK_MANDATE_OPENINGS = ("- Server is AUTHORITATIVE", "- Client predicts locally")
LEDGER_DIR = "docs/research/aaa-engine-support-2026"
MAX_QUOTE_WORDS = 25
TECHNICAL_SECTIONS = [
    (".claude/rules/network-code.md", "Replication model and authority", "C5, fix 3.4"),
    # Fix 7b: the dangling items' content sections (fix plan Q9a, first table).
    (".claude/agents/rendering-lead.md", "GPU and Golden-Image Test Harness", "GF1, fix 7b"),
    (".claude/agents/asset-build-tooling-engineer.md", "GPU Test Runner and CI Job", "GF1, fix 7b"),
    (".claude/agents/rhi-backend-engineer.md", "Ray-Tracing Acceleration Structures", "GF4, fix 7b"),
    (".claude/agents/rhi-backend-engineer.md", "Present Modes, Frame Pacing and VRR", "GF7, fix 7b"),
    (".claude/agents/shader-pipeline-engineer.md", "Material System", "GF5, fix 7b"),
    (".claude/agents/graphics-features-engineer.md", "XR Rendering", "GF9, fix 7b"),
    (".claude/agents/graphics-features-engineer.md", "Frame Generation and Latency SDKs", "GF7, fix 7b"),
    (".claude/agents/accessibility-specialist.md", "On a Custom Engine Project", "GF11, fix 7b"),
    # Fix 7c: the new-capability items (fix plan Q9a, second table). The
    # one-line additions that state only ownership or placement (the null
    # backends, headless lifecycle, the release-manager and security-engineer
    # handoffs, the online-services line, rhi-renderer-code.md's placement
    # bullet) carry no technical fact and are checked by HANDOFFS instead.
    (".claude/agents/asset-build-tooling-engineer.md", "Packaging, Install Chunks and Patches", "GF2, fix 7c"),
    (".claude/rules/tools-code.md", "Cook output is deterministic", "GF2 package determinism, fix 7c"),
    (".claude/agents/network-programmer.md", "Dedicated Server Target", "GF3, fix 7c"),
    (".claude/rules/build-files.md", "CMake", "GF3 server preset, fix 7c"),
    (".claude/rules/build-files.md", "Cargo", "GF3 server package, P7C critic F1"),
    (".claude/agents/rhi-backend-engineer.md", "Console Backends and NDA Placement", "GF6, fix 7c"),
    (".claude/agents/graphics-features-engineer.md", "Virtualized Geometry", "GF8, fix 7c"),
    (".claude/agents/asset-build-tooling-engineer.md", "Virtualized Geometry Build", "GF8 build side, fix 7c"),
    (".claude/agents/world-streaming-engineer.md", "Virtualized Geometry Page Streaming", "GF8 page streaming, fix 7c"),
    (".claude/agents/scripting-runtime-engineer.md", "Mods and UGC", "GF10, fix 7c"),
    (".claude/rules/streaming-io-code.md", "Mod and downloaded packages are untrusted", "GF10 packages, fix 7c"),
    # Fix 7d: the thin items (fix plan Q9a, "Thin items").
    (".claude/agents/asset-build-tooling-engineer.md", "Encoding Formats", "GF-thin encoding formats, fix 7d"),
    (".claude/agents/security-engineer.md", "Anti-Cheat Integration", "GF-thin anti-cheat, fix 7d"),
    # Fix 8.9 (score report D9, open point O11).
    (".claude/agents/devops-engineer.md", "Build and CI at Scale", "O11, fix 8.9"),
    # Phase 11 (AM32, OpenSpec add-content-and-xr-roles, design D6): the
    # sections of the roles valid on every engine, registered before their text.
    (".claude/agents/lighting-artist.md", "Lighting and Look-Dev", "AM32, task 3.3"),
    (".claude/agents/cinematic-designer.md", "Shot Design and Editing", "AM32, task 4.3"),
    (".claude/agents/xr-experience-designer.md", "Comfort and Locomotion", "AM32, task 5.3"),
    (".claude/agents/xr-experience-designer.md", "XR Interaction", "AM32, task 5.3"),
    (".claude/agents/qa-lead.md", "VR Test Evidence", "AM32(a), task 5.3"),
    (".claude/agents/release-manager.md", "VR Store Certification", "AM32(a), task 5.3"),
    (".claude/agents/performance-analyst.md", "VR Frame Budgets", "AM32(a), task 5.3"),
    (".claude/agents/technical-artist.md", "DCC Interchange", "AM32(a), task 6.3"),
    (".claude/agents/technical-artist.md", "Character Technology", "AM32(a), task 6.3"),
    (".claude/agents/asset-build-tooling-engineer.md", "DCC Import", "AM32, task 6.3"),
    (".claude/agents/animation-systems-engineer.md", "Character Data Contract", "AM32, task 6.3"),
    # Phase 12 (AM36(f), OpenSpec add-custom-engine-xr-numerics-demo): the
    # Custom XR contracts, registered before their text.
    (".claude/agents/platform-engineer.md", "XR Platform Options", "AM36(f), task 2.3"),
    (".claude/agents/audio-engine-engineer.md", "XR Audio Listener", "AM36(f), task 2.3"),
    (".claude/docs/templates/frame-budget.md", "XR — display-locked frame", "AM36(f), task 2.3"),
    # The math owner's numeric guarantees, registered before their text.
    (".claude/agents/ecs-dod-architect.md", "Numerics", "AM36(f), task 3.3"),
    # The industry-lessons document's engine sections (AM36(g), design D6),
    # registered before their text.
    (".claude/docs/engine-industry-lessons.md", "Frostbite (EA)", "AM36(f)(g), task 6.3"),
    (".claude/docs/engine-industry-lessons.md", "Naughty Dog engine", "AM36(f)(g), task 6.3"),
    (".claude/docs/engine-industry-lessons.md", "id Tech (id Software)", "AM36(f)(g), task 6.3"),
    (".claude/docs/engine-industry-lessons.md", "Decima (Guerrilla Games)", "AM36(f)(g), task 6.3"),
    (".claude/docs/engine-industry-lessons.md", "Northlight (Remedy)", "AM36(f)(g), task 6.3"),
    (".claude/docs/engine-industry-lessons.md", "Snowdrop (Ubisoft Massive)", "AM36(f)(g), task 6.3"),
    (".claude/docs/engine-industry-lessons.md", "Minecraft Bedrock (Mojang and Microsoft)", "AM36(f)(g), task 6.3"),
]


# R13, fix 7a. Each handoff sentence of the fix plan's Q9a tables: (file that
# hands over, a phrase of the handing-over statement, agent it names, term that
# agent's Core Responsibilities must take). Enumerated because a handoff is free
# prose with no machine-readable form, and which of the many redirect lines hand
# over a Phase 7 domain item cannot be derived from the text; fixes 7c and 7d
# extend the list with their own handoff lines (.claude/rules/skill-authoring.md:76-79).
HANDOFFS = [
    (".claude/agents/qa-lead.md", "golden-image", "rendering-lead", "golden-image"),
    (".claude/agents/qa-lead.md", "GPU test runner", "asset-build-tooling-engineer", "GPU test runner"),
    (".claude/docs/engine-development-coverage.md", "reference images", "rendering-lead", "reference image"),
    (".claude/docs/engine-development-coverage.md", "GPU test runner", "asset-build-tooling-engineer", "GPU test runner"),
    (".claude/agents/graphics-features-engineer.md", "acceleration-structure builds", "rhi-backend-engineer",
     "acceleration-structure"),
    (".claude/agents/technical-artist.md", "material system", "shader-pipeline-engineer", "material system"),
    (".claude/agents/platform-engineer.md", "present modes", "rhi-backend-engineer", "present mode"),
    (".claude/docs/engine-development-coverage.md", "XR rendering", "graphics-features-engineer", "XR rendering"),
    (".claude/docs/engine-development-coverage.md", "XR runtime", "platform-engineer", "OpenXR"),
    (".claude/docs/engine-development-coverage.md", "screen-reader", "accessibility-specialist", "runtime UI framework"),
    # Fix 7c (Q9a, second table).
    (".claude/agents/release-manager.md", "delta patches", "asset-build-tooling-engineer", "delta patch"),
    (".claude/agents/network-programmer.md", "null RHI backend", "rhi-backend-engineer", "null backend"),
    (".claude/agents/network-programmer.md", "null audio backend", "audio-engine-engineer", "null backend"),
    (".claude/agents/network-programmer.md", "headless lifecycle", "platform-engineer", "headless"),
    (".claude/agents/network-programmer.md", "Server hosting", "devops-engineer", "dedicated server"),
    (".claude/agents/graphics-features-engineer.md", "cluster hierarchy", "asset-build-tooling-engineer",
     "cluster hierarchy"),
    (".claude/agents/graphics-features-engineer.md", "geometry pages", "world-streaming-engineer", "geometry pages"),
    (".claude/agents/graphics-features-engineer.md", "meshlet", "shader-pipeline-engineer", "meshlet culling"),
    (".claude/agents/scripting-runtime-engineer.md", "Mod distribution", "online-services-engineer", "mod distribution"),
    (".claude/agents/scripting-runtime-engineer.md", "mod packages", "world-streaming-engineer", "mod packages"),
    (".claude/agents/security-engineer.md", "mod packages", "scripting-runtime-engineer", "mods and UGC"),
    # P7C critic F2 and F4: the upload split, the server content set and
    # console build machines.
    (".claude/agents/asset-build-tooling-engineer.md", "storefront and depot upload", "release-manager",
     "storefront and depot upload"),
    (".claude/agents/asset-build-tooling-engineer.md", "jobs that run the release upload", "devops-engineer",
     "jobs that run the release upload"),
    (".claude/agents/network-programmer.md", "content set", "asset-build-tooling-engineer",
     "dedicated server's content set"),
    (".claude/agents/rhi-backend-engineer.md", "Console builds", "devops-engineer", "console build machines"),
    # Fix 7d.
    (".claude/agents/security-engineer.md", "integration point", "platform-engineer", "anti-cheat"),
    (".claude/agents/asset-build-tooling-engineer.md", "runtime decoding", "audio-engine-engineer",
     "streaming and decoding"),
    (".claude/agents/asset-build-tooling-engineer.md", "texture format support", "rhi-backend-engineer",
     "capability queries"),
]
# Where an agent states its duties. An agent with a "Core Responsibilities"
# section is judged on that section alone (fix 7a: the accepting line goes in
# that list). The shared agents written before the Custom agents have no such
# section; they use "Key Responsibilities" and carry their Custom duties in
# "On a Custom Engine Project", and only for them do those two count (fix 7c,
# narrowed after the P7C critic's F3: a wider lookup let a term repeated in a
# Custom section stand in for a deleted Core Responsibilities line).
PRIMARY_DUTY_SECTION = "Core Responsibilities"
FALLBACK_DUTY_SECTIONS = ("Key Responsibilities", "On a Custom Engine Project")


def duty_text(agent_text):
    """The agent's duty sections by the precedence above, or [] when none."""
    primary = section_text(agent_text, PRIMARY_DUTY_SECTION)
    if primary is not None:
        return [primary]
    return [s for s in (section_text(agent_text, h) for h in FALLBACK_DUTY_SECTIONS) if s is not None]


def ledger(name):
    return [json.loads(line) for line in read(f"{LEDGER_DIR}/{name}.jsonl").splitlines() if line.strip()]


def section_text(text, heading):
    """The body under a markdown heading, up to the next heading of the same or
    a higher level, or None when the heading is absent."""
    match = re.search(rf"^(#+) {re.escape(heading)}[ \t]*$", text, re.M)
    if not match:
        return None
    level = len(match[1])
    end = re.search(rf"^#{{1,{level}}} ", text[match.end():], re.M)
    return text[match.end():match.end() + end.start()] if end else text[match.end():]


# R11, fix 6.1. A Custom statement in an agent file names `engine.name` and
# `Custom` on one line ("`engine.name` is `Custom`", "`engine.name: Custom`").
# A file-level match of the two tokens would also take in godot-specialist,
# whose "Custom resources" and `engine.name` sit on different lines.
CUSTOM_TEXT_LINE = re.compile(r"engine\.name[` ]*(is|:)[` ]*Custom")
# The same form with any engine name, read from a spec case's fixture.
FIXTURE_ENGINE_LINE = re.compile(r"engine\.name[` ]*(?:is|:)[` ]*(\w+)")
CUSTOM_ENGINE = "Custom"
CUSTOM_AGENT_SPEC_DIR = "studio-tests/agents/engine/custom"
SPEC_CASE_HEADING = re.compile(r"(?m)^### Case \d+:")
# Fix 6.2: the shape studio-tests/CLAUDE.md asks of every spec ("5 or more
# test cases + protocol compliance assertions").
SPEC_DIRS = ("studio-tests/agents", "studio-tests/skills")
MIN_SPEC_CASES = 5
PROTOCOL_SECTION = re.compile(r"(?m)^## Protocol Compliance[ \t]*$")


# R8, fix 5.1. Each published count is a site: (file, pattern with one captured
# number, kind). Each kind has one derivation from disk (published_count_values).
# Totals and subset counts are separate kinds, so a true subset count never has
# to equal a total (fix plan, "R8 design").
KIND_AGENTS = "agents total"
KIND_SKILLS = "skills total (public)"
KIND_SKILL_DIRS = "skill directories"
KIND_OLD_NAMES = "old skill names"
KIND_RULES = "rules total"
KIND_CUSTOM = "Custom agents"
KIND_CUSTOM_LEADS = "Custom leads"
KIND_CUSTOM_ARCHITECT = "Custom architect"
KIND_CUSTOM_SPECIALISTS = "Custom specialists"
KIND_NEW_SKILLS = "new skills"
KIND_NEW_RULES = "new rules"
# Fix plan AM32 (task 7.1): the agents added since the base release outside the
# Custom set, i.e. the agents valid on every engine (lighting-artist,
# cinematic-designer, xr-experience-designer at AM32).
KIND_NEW_ALL_ENGINE_AGENTS = "new agents outside the Custom set"
KIND_OPUS = "agents on opus"
KIND_SONNET = "agents on sonnet"
KIND_HAIKU = "agents on haiku"
# Fix plan AM38: the tiers of .claude/agent-models.yaml, counted from each
# agent's frontmatter `model:` and `effort:` together, so a move between two
# efforts of one model changes a count.
KIND_OPUS_HIGH = "agents on opus at high effort"
KIND_OPUS_MEDIUM = "agents on opus at medium effort"
KIND_SONNET_HIGH = "agents on sonnet at high effort"
KIND_SONNET_MEDIUM = "agents on sonnet at medium effort"
EFFORT_LINE = re.compile(r"^effort:\s*(\S+)", re.M)
# Fix plan AM15: the agents core-systems-lead starts (its `subagent_type:`
# lines), and the Custom agents other than the architect.
KIND_CORE_SYSTEMS_DELEGATES = "agents core-systems-lead starts"
KIND_CUSTOM_BELOW_ARCHITECT = "Custom agents other than the architect"
SUBAGENT_TYPE_LINE = re.compile(r"^- `subagent_type: ([\w-]+)`", re.M)
# The forms of an agent's "Reports to" line in the tree: "**Reports to:** `x`"
# and "Reports to: **x**".
REPORTS_TO_LINE = re.compile(r"^\**Reports to\b(.*)$", re.M)


def reports_to_kind(lead):
    """The kind "Custom agents whose Reports to line names <lead>" (P5 critic
    F9: a lead's own team size)."""
    return f"Custom agents reporting to {lead}"
# effects-map.md and automation-modes.md: "skills that use AskUserQuestion or
# write files", read from each public skill's allowed-tools (69 at the base
# release, where that derivation gives the published 69).
KIND_ASK_OR_WRITE = "skills that ask or write"
ASK_OR_WRITE_TOOLS = re.compile(r"\b(?:AskUserQuestion|Write)\b")
OLD_NAME_HEADING = re.compile(r"^# /[\w-]+ — old name of /[\w-]+$", re.M)
MODEL_LINE = re.compile(r"^model:\s*(\S+)", re.M)
INHERIT, OPUS, SONNET, HAIKU = "inherit", "opus", "sonnet", "haiku"
HIGH, MEDIUM = "high", "medium"
# The digits or the number word a count is written with.
COUNT_UNITS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
               "fourteen fifteen sixteen seventeen eighteen nineteen").split()
COUNT_TENS = {w: 10 * n for n, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), 2)}
COUNT_NUMBER = (r"(?:\d+|(?:" + "|".join(COUNT_TENS) + r")(?:-(?:" + "|".join(COUNT_UNITS[1:10]) + r"))?|"
                + "|".join(sorted(COUNT_UNITS, key=len, reverse=True)) + ")")
COUNT_SITES = [
    ("CLAUDE.md", r"managed through (\d+) coordinated", KIND_AGENTS),
    (".claude/docs/agent-roster.md", r"The following (\d+) agents", KIND_AGENTS),
    (".claude/docs/agent-roster.md", r"\((\d+) of them only on a Custom engine\)", KIND_CUSTOM),
    (".claude/docs/effects-map.md", r"need all (\d+) agents", KIND_AGENTS),
    (".claude/docs/effects-map.md", r"All (\d+) agents available", KIND_AGENTS),
    (".claude/docs/effects-map.md", r"\(the (\d+) Custom-engine agents only", KIND_CUSTOM),
    (".claude/docs/effects-map.md", r"All (\d+) skills that use `AskUserQuestion`", KIND_ASK_OR_WRITE),
    (".claude/docs/automation-modes.md", r"\*\*Scope\*\*: (\d+) skills", KIND_ASK_OR_WRITE),
    (".claude/docs/quick-start.md", r"organizes (\d+) specialized", KIND_AGENTS),
    (".claude/docs/quick-start.md", r"(\w+) leads — `core-systems-lead`", KIND_CUSTOM_LEADS),
    (".claude/docs/quick-start.md", r"and (\w+) engine\s+specialists", KIND_CUSTOM_SPECIALISTS),
    # AM38: the tier sentence that replaced "Thirty-three of the 77 agents run on".
    (".claude/docs/quick-start.md", r"All (\d+) agents run on the model and effort", KIND_AGENTS),
    (".claude/docs/quick-start.md", r"agents/\s+-- (\d+) agent definitions", KIND_AGENTS),
    (".claude/docs/quick-start.md", r"skills/\s+-- (\d+) slash command definitions", KIND_SKILLS),
    (".claude/docs/quick-start.md", r"rules/\s+-- (\d+) path-specific rule files", KIND_RULES),
    (".claude/docs/setup-requirements.md", r"on a (\d+)-agent project", KIND_AGENTS),
    (".claude/docs/setup-requirements.md", r"ships (\d+) skills", KIND_SKILLS),
    (".claude/docs/skills-reference.md", r"^(\d+) slash commands organized", KIND_SKILLS),
    # AM38: the per-tier list of .claude/agent-models.yaml replaced the
    # inherit / pinned / opus / sonnet sentences.
    (".claude/docs/model-tiers.md", r"\*\*opus · high \((\d+)\):\*\*", KIND_OPUS_HIGH),
    (".claude/docs/model-tiers.md", r"\*\*opus · medium \((\d+)\):\*\*", KIND_OPUS_MEDIUM),
    (".claude/docs/model-tiers.md", r"\*\*sonnet · high \((\d+)\):\*\*", KIND_SONNET_HIGH),
    (".claude/docs/model-tiers.md", r"\*\*sonnet · medium \((\d+)\):\*\*", KIND_SONNET_MEDIUM),
    (".claude/docs/model-tiers.md", r"\*\*haiku \((\d+)\):\*\*", KIND_HAIKU),
    (".claude/scripts/agent-check.sh", r"across (\d+) agent files", KIND_AGENTS),
    (".claude/scripts/skill-lint.sh", r"across (\d+) skills", KIND_SKILLS),
    (".claude/skills/setup-engine/SKILL.md", r"specialist agents are the (\d+) custom-engine agents", KIND_CUSTOM),
    (".claude/skills/setup-engine/references/custom.md", r"Custom uses the (\d+) custom-engine agents", KIND_CUSTOM),
    # /skill-test's example output states the totals it was written for.
    (".claude/skills/skill-test/SKILL.md", r"All (\d+) Skills ===", KIND_SKILLS),
    (".claude/skills/skill-test/SKILL.md", r"`All (\d+) Skills` in the header", KIND_SKILLS),
    (".claude/skills/skill-test/SKILL.md", r"Agents \(observations, not scored\): (\d+) read", KIND_AGENTS),
    (".claude/skills/skill-test/SKILL.md", r"SKILLS \((\d+) total\)", KIND_SKILLS),
    (".claude/skills/skill-test/SKILL.md", r"Specs written: (\d+) \(100%\)", KIND_SKILLS),
    (".claude/skills/skill-test/SKILL.md", r"Never static tested: (\d+)", KIND_SKILLS),
    (".claude/skills/skill-test/SKILL.md", r"Never category tested: (\d+)", KIND_SKILLS),
    (".claude/skills/skill-test/SKILL.md", r"AGENTS \((\d+) total\)", KIND_AGENTS),
    (".claude/skills/skill-test/SKILL.md", r"Agent specs written: (\d+)", KIND_AGENTS),
    (".claude/skills/skill-test/SKILL.md", r"Skill coverage:\s+(\d+)/", KIND_SKILLS),
    (".claude/skills/skill-test/SKILL.md", r"Skill coverage:\s+\d+/(\d+)", KIND_SKILLS),
    (".claude/skills/skill-test/SKILL.md", r"Agent coverage:\s+(\d+)/", KIND_AGENTS),
    (".claude/skills/skill-test/SKILL.md", r"Agent coverage:\s+\d+/(\d+)", KIND_AGENTS),
    ("README.md", r"\*\*(\d+) agents\*\*, used only when", KIND_CUSTOM),
    ("README.md", r"(\w+) leads and \w+ specialists", KIND_CUSTOM_LEADS),
    ("README.md", r"\w+ leads and (\w+) specialists", KIND_CUSTOM_SPECIALISTS),
    ("README.md", r"agents/\s+# (\d+) agent definitions", KIND_AGENTS),
    ("README.md", r"skills/\s+# (\d+) skills, plus", KIND_SKILLS),
    ("README.md", r"skills/\s+# \d+ skills, plus (\w+) old names", KIND_OLD_NAMES),
    ("README.md", r"rules/\s+# (\d+) path-scoped coding standards", KIND_RULES),
    ("README.md", r"catalog of all\s+(\d+) skills", KIND_SKILLS),
    ("README.md", r"catalog of all\s+\d+ skills and (\d+) agents", KIND_AGENTS),
    ("README.md", r"\*\*studio mode\*\*: (\d+) specialized agents", KIND_AGENTS),
    ("README.md", r"\| \*\*Agents\*\* \| (\d+) \|", KIND_AGENTS),
    ("README.md", r"plus (\d+) for a Custom engine", KIND_CUSTOM),
    ("README.md", r"\| \*\*Skills\*\* \| (\d+) \|", KIND_SKILLS),
    ("README.md", r"\| \*\*Rules\*\* \| (\d+) \|", KIND_RULES),
    # AM38: README's tier sentence now counts the table's models and efforts.
    ("README.md", r"title: ([\w-]+) roles run on Opus", KIND_OPUS),
    ("README.md", r"\(([\w-]+) of them at high effort\)", KIND_OPUS_HIGH),
    ("README.md", r"and\s+([\w-]+) on Sonnet", KIND_SONNET),
    ("README.md", r"access all (\d+) skills", KIND_SKILLS),
    ("README.md", r"access all \d+ skills \(plus (\w+) old names", KIND_OLD_NAMES),
    # CHANGELOG.md and UPGRADING.md: searched in the Unreleased section only.
    ("CHANGELOG.md", r"\*\*(\d+) agents\*\*, used only on a Custom", KIND_CUSTOM),
    ("CHANGELOG.md", r"\.\s+(\d+) agents\.", KIND_AGENTS),
    ("CHANGELOG.md", r"\*\*(\w+) skills\*\*", KIND_NEW_SKILLS),
    # P5 critic F4: the Custom split, in both notes.
    ("CHANGELOG.md", r"(\w+) architect, \w+ leads, \w+ specialists", KIND_CUSTOM_ARCHITECT),
    ("CHANGELOG.md", r"\w+ architect, (\w+) leads, \w+ specialists", KIND_CUSTOM_LEADS),
    ("CHANGELOG.md", r"\w+ architect, \w+ leads, (\w+) specialists", KIND_CUSTOM_SPECIALISTS),
    ("UPGRADING.md", r"(\w+) architect, \w+ leads, \w+ specialists", KIND_CUSTOM_ARCHITECT),
    ("UPGRADING.md", r"\w+ architect, (\w+) leads, \w+ specialists", KIND_CUSTOM_LEADS),
    ("UPGRADING.md", r"\w+ architect, \w+ leads, (\w+) specialists", KIND_CUSTOM_SPECIALISTS),
    ("CHANGELOG.md", r"\.\s+(\d+) skills\.", KIND_SKILLS),
    ("CHANGELOG.md", r"\.\s+(\d+) rules\.", KIND_RULES),
    ("CHANGELOG.md", r"\b(\w+) new rules\b", KIND_NEW_RULES),
    ("UPGRADING.md", r"\b(\w+) new rules\b", KIND_NEW_RULES),
    ("UPGRADING.md", r"\*\*New skills\*\* \| (\w+):", KIND_NEW_SKILLS),
    ("UPGRADING.md", r"\*\*New agents\*\* \| (\d+), used only", KIND_CUSTOM),
    # Fix plan AM32(e): the release notes count the agents added on every engine.
    ("UPGRADING.md", r"\b(\w+) new agents on every engine", KIND_NEW_ALL_ENGINE_AGENTS),
    ("CHANGELOG.md", r"\b(\w+) new agents on every engine", KIND_NEW_ALL_ENGINE_AGENTS),
    ("UPGRADING.md", r"\.\s+(\d+) agents \|", KIND_AGENTS),
    ("UPGRADING.md", r"\.\s+(\d+) skills\.", KIND_SKILLS),
    ("UPGRADING.md", r"\.\s+(\d+) rules \|", KIND_RULES),
    ("docs/WORKFLOW-GUIDE.md", r"(\d+)-agent system", KIND_AGENTS),
    ("docs/WORKFLOW-GUIDE.md", r"(\d+) slash commands, and", KIND_SKILLS),
    ("docs/WORKFLOW-GUIDE.md", r"### All (\d+) Commands by Category", KIND_SKILLS),
    ("docs/WORKFLOW-GUIDE.md", r"and all (\w+) leads to\s+`chief-engine-architect`", KIND_CUSTOM_LEADS),
    ("studio-tests/CLAUDE.md", r"registry for all (\d+) skills", KIND_SKILLS),
    ("studio-tests/CLAUDE.md", r"registry for all \d+ skills and (\d+) agents", KIND_AGENTS),
    ("studio-tests/README.md", r"tracks all (\d+) skills", KIND_SKILLS),
    ("studio-tests/README.md", r"tracks all \d+ skills and (\d+) agents", KIND_AGENTS),
    ("studio-tests/README.md", r"all (\d+) skills \+ \d+ agents", KIND_SKILLS),
    ("studio-tests/README.md", r"all \d+ skills \+ (\d+) agents", KIND_AGENTS),
    ("studio-tests/README.md", r"spec files for all (\d+) skills", KIND_SKILLS),
    ("studio-tests/README.md", r"Check all (\d+) skills", KIND_SKILLS),
    ("studio-tests/skills/utility/setup-engine.md", r"checks the (\d+) Custom agents", KIND_CUSTOM),
    # Fix plan AM15 (1), (2): two agent specs that count the Custom set.
    ("studio-tests/agents/engine/custom/core-systems-lead.md", r"naming all (\w+) (?:core )?specialists",
     KIND_CORE_SYSTEMS_DELEGATES),
    ("studio-tests/agents/engine/custom/core-systems-lead.md", r"Routes to its (\w+) (?:core )?specialists",
     KIND_CORE_SYSTEMS_DELEGATES),
    ("studio-tests/agents/engine/custom/chief-engine-architect.md", r"names all (\d+) other Custom engine agents",
     KIND_CUSTOM_BELOW_ARCHITECT),
    # P5 critic F9 (fix plan AM16(a)): the leads and specialists counts the
    # widened sweep sees.
    (".claude/agents/chief-engine-architect.md", r"two of the (\w+) leads", KIND_CUSTOM_LEADS),
    ("studio-tests/agents/engine/custom/chief-engine-architect.md", r"agents — the (\w+) leads", KIND_CUSTOM_LEADS),
    (".claude/agents/rendering-lead.md", r"route GPU work to (\w+) specialists", reports_to_kind("rendering-lead")),
    (".claude/agents/rendering-lead.md", r"delegate to the (\w+) specialists above", reports_to_kind("rendering-lead")),
    (".claude/agents/rendering-lead.md", r"Your (\w+) specialists:", reports_to_kind("rendering-lead")),
    (".claude/agents/simulation-systems-lead.md", r"route work to (\w+) specialists",
     reports_to_kind("simulation-systems-lead")),
    (".claude/agents/simulation-systems-lead.md", r"delegate to the (\w+) specialists above",
     reports_to_kind("simulation-systems-lead")),
    (".claude/docs/agent-roster.md", r"coordinates its (\w+) specialists", reports_to_kind("simulation-systems-lead")),
    (".claude/docs/agent-roster.md", r"coordinates the (\w+) editor specialists", reports_to_kind("editor-architect")),
    ("studio-tests/agents/engine/custom/editor-architect.md", r"sequencer work to its (\w+) specialists",
     reports_to_kind("editor-architect")),
    (".claude/docs/engine-development-coverage.md", r"rendering-lead and its (\w+) specialists",
     reports_to_kind("rendering-lead")),
    (".claude/docs/engine-development-coverage.md", r"simulation-systems-lead and its (\w+) specialists",
     reports_to_kind("simulation-systems-lead")),
    ("studio-tests/agents/engine/custom/core-systems-lead.md", r"\(the (\w+) core specialists",
     reports_to_kind("core-systems-lead")),
    ("studio-tests/agents/engine/custom/rendering-lead.md", r"starts to its (\w+) specialists",
     reports_to_kind("rendering-lead")),
    ("studio-tests/agents/engine/custom/rendering-lead.md", r"only its (\w+) specialists",
     reports_to_kind("rendering-lead")),
    ("studio-tests/agents/engine/custom/simulation-systems-lead.md", r"starts to its (\w+) specialists",
     reports_to_kind("simulation-systems-lead")),
    ("studio-tests/agents/engine/custom/simulation-systems-lead.md", r"Starts only its (\w+) specialists",
     reports_to_kind("simulation-systems-lead")),
]
# The completeness sweep: a number, then "-agent" (as in "a 74-agent project"),
# or "-" or a gap and at most one more word, then one of the counted nouns. A
# gap is spaces or one line break (the swept Markdown is hard-wrapped; a quote
# marker after the break is allowed). A number that labels a tier, phase, step
# or case ("Phase 3 agents", "Tier 2 leads") is an ordinal, not a count. Every
# match must be claimed by a site above or by an exception below, else it fails
# as unclassified (P5 critic F5, F6, F9; fix plan AM16(a)).
COUNT_GAP = r"(?:[ \t]*\r?\n[ \t>]*|[ \t]+)"
COUNT_PHRASE = re.compile(
    rf"(?<![\w.-])(?<!Phase )(?<!Step )(?<!Case )(?<!Tier )({COUNT_NUMBER})"
    rf"(?:-agent\b|(?:-|{COUNT_GAP}(?:[A-Za-z][\w-]*{COUNT_GAP})?)"
    r"(?:agents|agent files|agent definitions|skills|slash commands|slash command definitions|commands"
    r"|rules|rule files|path-scoped coding standards|path-specific rule files|leads|specialists)\b)", re.I)
# A Markdown file's YAML frontmatter is configuration, not text ("maxTurns: 20"
# above "skills:" is not a count).
FRONTMATTER = re.compile(r"\A---\r?\n.*?^---[ \t]*\r?$", re.M | re.S)
# Where the sweep reads: only the Unreleased section of these two files; the
# rest is release history (fix plan, "R8 design", exception list).
COUNT_REGIONS = {
    "CHANGELOG.md": re.compile(r"^## \[Unreleased\].*?(?=^## \[)", re.M | re.S),
    "UPGRADING.md": re.compile(r"^## Unreleased.*?(?=^## )", re.M | re.S),
}
# Not swept. docs/research/: the research record of this change. Python files:
# the test sources quote the phrases they check. CONTINUE-ENGINE-SUPPORT.md: a
# dated session checkpoint log (history, like the release sections above).
# The approved-hunk manifest pins old text verbatim (e.g. "75 Skills"); its
# numbers are quotations of reviewed hunks, not published counts (AM27).
COUNT_SWEEP_SKIPPED_PREFIXES = ("docs/research/", "CONTINUE-ENGINE-SUPPORT.md", "studio-tests/shared-file-hunks.json")
COUNT_SWEEP_SKIPPED_SUFFIXES = (".py",)
COUNT_SWEEP_SUFFIXES = (".md", ".sh", ".yaml", ".yml", ".json", ".tsv", ".awk", ".tmpl", ".txt")
# Matches that are not framework counts, per file, each phrase as many times as
# it occurs. Kept because history and examples are not mechanically separable
# from current counts (.claude/rules/skill-authoring.md:76-79); a new count
# sentence must be added to COUNT_SITES, or here with its reason.
COUNT_EXCEPTIONS = {
    # Example denominators of a /skill-test fixture (fix plan, "R8 design").
    "studio-tests/skills/utility/skill-test.md": ("73 readable skills", "74 skills", "74 skills"),
    # Not a count of the framework (found by the sweep on 2026-11-16): section,
    # step and list-item numbers ("2 The rules", "6 Rules", the "| 4 specialists |"
    # step row, "#   3  commands.build"); the top of a range ("5–15 specialist
    # agents", "5–15 specialists"); "the one commands.test"; a player's skills
    # (difficulty-curve.md). effects-map.md's "six narrative agents" and "four
    # skills" are local counts, as in the group below.
    ".claude/docs/effects-map.md": ("15 specialists", "15 specialist agents", "six narrative agents", "four skills"),
    ".claude/docs/templates/difficulty-curve.md": ("two skills",),
    ".claude/scripts/test-run.sh": ("one commands",),
    ".claude/scripts/project-coherence.sh": ("3 commands",),
    ".claude/skills/team-frame-pipeline/SKILL.md": ("4 specialists", "two rules"),
    ".claude/skills/prototype/references/one-shot-2-build.md": ("2 The rules", "Four hard rules"),
    ".claude/skills/prototype/references/one-shot-5-grow.md": ("6 Rules", "four commands"),
    # Local counts: the agents one step spawns or one passage names, the rules
    # of one passage, the skills one note names, an engine row's four commands.
    # Each counts something inside its own passage, not the framework's agents,
    # skills or rules.
    ".claude/docs/config-resolution.md": ("four default commands",),
    ".claude/docs/context-management.md": ("Two rules",),
    ".claude/docs/coordination-rules.md": ("two agents",),
    ".claude/engines/README.md": ("four commands",),
    ".claude/hooks/validate-assets.sh": ("Two rules",),
    ".claude/hooks/validate-registry.sh": ("two rules",),
    ".claude/hooks/validate-skill-change.sh": ("TWO rules",),
    ".claude/hooks/yaml-helper.sh": ("10 per-system skills", "four commands"),
    ".claude/scripts/agent-check.sh": ("two agents",),
    ".claude/skills/architecture-decision/CONTRACT.md": ("ten skills",),
    ".claude/skills/architecture-review/references/3-traceability.md": ("Four skills",),
    ".claude/skills/design-review/SKILL.md": ("5 agents",),
    ".claude/skills/design-system/references/4-section-design.md": ("two rules", "two rules"),
    ".claude/skills/design-system/references/lens-systems-designer.md": ("two rules",),
    ".claude/skills/gate-check/references/2b-workflow-tier.md": ("Two rules",),
    ".claude/skills/map-systems/SKILL.md": ("two skills",),
    ".claude/skills/setup-engine/references/5.5-project-yaml.md": ("Three further rules",),
    ".claude/skills/setup-engine/references/web.md": ("four commands",),
    ".claude/skills/team-audio/SKILL.md": ("two agents",),
    ".claude/skills/team-combat/SKILL.md": ("two agents", "two rules"),
    ".claude/skills/team-level/SKILL.md": ("two agents", "three agents"),
    ".claude/skills/team-live-ops/SKILL.md": ("two agents",),
    ".claude/skills/team-narrative/SKILL.md": ("two agents",),
    ".claude/skills/team-polish/SKILL.md": ("two agents",),
    ".claude/skills/team-qa/SKILL.md": ("two agents", "two agents", "three rules"),
    ".claude/skills/team-release/SKILL.md": ("two agents", "two agents"),
    ".claude/skills/team-ui/SKILL.md": ("two agents",),
    "docs/COLLABORATIVE-DESIGN-PRINCIPLE.md": ("4 agents",),
    "docs/WORKFLOW-GUIDE.md": ("4 specialists", "two agents", "4 agents"),
    # A lead's own two leads, or two of its specialists in a dispute or a
    # handoff (P5 critic F9: the widened sweep's local leads/specialists
    # counts; every team-size count is a site above).
    ".claude/agents/network-programmer.md": ("Two leads",),
    ".claude/agents/rendering-lead.md": ("Two specialists",),
    ".claude/agents/simulation-systems-lead.md": ("two specialists",),
    "studio-tests/README.md": ("two skills",),
    "studio-tests/agents/directors/art-director.md": ("three style rules",),
    "studio-tests/agents/leads/qa-lead.md": ("two agents",),
    "studio-tests/skills/team/team-combat.md": ("three implementing agents", "four agents"),
    "studio-tests/skills/team/team-live-ops.md": ("two parallel agents",),
    "studio-tests/skills/team/team-narrative.md": ("three agents", "six agents"),
    "studio-tests/skills/team/team-release.md": ("two parallel agents",),
    "studio-tests/skills/team/team-ui.md": ("three agents",),
    "studio-tests/skills/utility/hotfix.md": ("three sign-off agents",),
    "studio-tests/templates/agent-test-spec.md": ("two agents",),
}


def parse_count(text):
    """The value of a count written in digits or in words, or None."""
    word = text.lower()
    if word.isdigit():
        return int(word)
    if word in COUNT_UNITS:
        return COUNT_UNITS.index(word)
    tens, _, unit = word.partition("-")
    if tens in COUNT_TENS and (not unit or unit in COUNT_UNITS[1:10]):
        return COUNT_TENS[tens] + (COUNT_UNITS.index(unit) if unit else 0)
    return None


def frontmatter(text):
    parts = text.replace("\r", "").split("---", 2)
    return parts[1] if len(parts) == 3 else ""


def base_release_names(directory):
    """Entry names (file stems) under a directory at BASE_RELEASE, or None."""
    listing = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "--name-only", BASE_RELEASE, directory + "/"],
                             capture_output=True, text=True)
    return {Path(p).stem for p in listing.stdout.split()} if listing.returncode == 0 else None


def custom_hierarchy():
    """(architect set, lead set) among the Custom agents in the layout's Lead
    column: the architect has no Custom agent above it, i.e. it owns no row
    whose Lead is a Custom agent and its "Reports to" line names none."""
    custom = {p.stem for p in (ROOT / CUSTOM_AGENT_SPEC_DIR).glob("*.md")}
    rows = layout_rows()
    in_lead = {row_lead(row) for row in rows} & custom
    architects = set()
    for agent in in_lead:
        owns_under_custom = any(row_owner(row) == agent and row_lead(row) in custom for row in rows)
        # Both forms in the tree: "**Reports to:** `x`" and "Reports to: **x**".
        reports = re.search(r"^\**Reports to\b(.*)$", read(f".claude/agents/{agent}.md"), re.M)
        reports_to_custom = bool(reports) and any(
            re.search(rf"(?<![\w-]){re.escape(c)}(?![\w-])", reports[1]) for c in custom)
        if not owns_under_custom and not reports_to_custom:
            architects.add(agent)
    return architects, in_lead - architects


def published_count_values():
    """Each count kind's value, derived from disk; the new-item kinds are
    absent when the base release is not in this clone."""
    agents = {p.stem: read(p.relative_to(ROOT)) for p in (ROOT / ".claude/agents").glob("*.md")}
    models = {name: (MODEL_LINE.search(frontmatter(text)) or [None, INHERIT])[1] for name, text in agents.items()}
    efforts = {name: (EFFORT_LINE.search(frontmatter(text)) or [None, None])[1] for name, text in agents.items()}
    skill_dirs = {p.parent.name: read(p.relative_to(ROOT)) for p in (ROOT / ".claude/skills").glob("*/SKILL.md")}
    old_names = {name for name, text in skill_dirs.items() if OLD_NAME_HEADING.search(text)}
    public = {name: text for name, text in skill_dirs.items() if name not in old_names}
    rules = {p.stem for p in (ROOT / ".claude/rules").glob("*.md")}
    custom = {p.stem for p in (ROOT / CUSTOM_AGENT_SPEC_DIR).glob("*.md")}
    architects, leads = custom_hierarchy()
    values = {
        KIND_AGENTS: len(agents), KIND_SKILLS: len(public), KIND_SKILL_DIRS: len(skill_dirs),
        KIND_OLD_NAMES: len(old_names), KIND_RULES: len(rules), KIND_CUSTOM: len(custom),
        KIND_CUSTOM_LEADS: len(leads), KIND_CUSTOM_SPECIALISTS: len(custom - architects - leads),
        KIND_CUSTOM_ARCHITECT: len(architects),
        KIND_OPUS: sum(m == OPUS for m in models.values()),
        KIND_SONNET: sum(m == SONNET for m in models.values()),
        KIND_HAIKU: sum(m == HAIKU for m in models.values()),
        KIND_OPUS_HIGH: sum(models[a] == OPUS and efforts[a] == HIGH for a in models),
        KIND_OPUS_MEDIUM: sum(models[a] == OPUS and efforts[a] == MEDIUM for a in models),
        KIND_SONNET_HIGH: sum(models[a] == SONNET and efforts[a] == HIGH for a in models),
        KIND_SONNET_MEDIUM: sum(models[a] == SONNET and efforts[a] == MEDIUM for a in models),
        KIND_CORE_SYSTEMS_DELEGATES: len(set(SUBAGENT_TYPE_LINE.findall(agents["core-systems-lead"]))),
        KIND_CUSTOM_BELOW_ARCHITECT: len(custom - architects),
        KIND_ASK_OR_WRITE: sum(bool(ASK_OR_WRITE_TOOLS.search(
            "\n".join(l for l in frontmatter(text).splitlines() if l.startswith("allowed-tools"))))
            for text in public.values()),
    }
    for lead in leads:
        named = re.compile(rf"(?<![\w-]){re.escape(lead)}(?![\w-])")
        values[reports_to_kind(lead)] = sum(
            any(named.search(line) for line in REPORTS_TO_LINE.findall(agents[a])) for a in custom if a in agents)
    base_skills, base_rules = base_release_names(".claude/skills"), base_release_names(".claude/rules")
    if base_skills is not None and base_rules is not None:
        values[KIND_NEW_SKILLS] = len(set(skill_dirs) - base_skills)
        values[KIND_NEW_RULES] = len(rules - base_rules)
    base_agents = base_release_names(".claude/agents")
    if base_agents is not None:
        values[KIND_NEW_ALL_ENGINE_AGENTS] = len(set(agents) - base_agents - custom)
    return values


def count_region(path, text):
    """(start, end) of the part of a file the counts are read from: the
    Unreleased section of a release-notes file, else the text after any
    Markdown frontmatter."""
    region = COUNT_REGIONS.get(path)
    if region is None:
        frontmatter_block = FRONTMATTER.match(text) if path.endswith(".md") else None
        return (frontmatter_block.end() if frontmatter_block else 0), len(text)
    match = region.search(text)
    return (match.start(), match.end()) if match else (0, 0)


def count_sweep_files():
    """Current-release text files, relative to ROOT, for the sweep."""
    listing = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard"],
                             capture_output=True, text=True)
    if listing.returncode == 0:
        paths = listing.stdout.splitlines()
    else:
        paths = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                 if p.is_file() and ".git" not in p.relative_to(ROOT).parts]
    return sorted(p for p in paths if p.endswith(COUNT_SWEEP_SUFFIXES)
                  and not p.startswith(COUNT_SWEEP_SKIPPED_PREFIXES)
                  and not p.endswith(COUNT_SWEEP_SKIPPED_SUFFIXES) and (ROOT / p).is_file())


# R8, fix 5.2: the files whose Unreleased sections name every new item.
RELEASE_NOTE_SECTIONS = {"CHANGELOG.md": COUNT_REGIONS["CHANGELOG.md"],
                         "UPGRADING.md": COUNT_REGIONS["UPGRADING.md"]}
CUSTOM_AGENT_LIST_FILES = (".claude/docs/model-tiers.md", "studio-tests/CLAUDE.md")
# Phase 10 R56/R69: further lists of the Custom agents, each searched only in
# the text that is the list: (file, pattern whose matches' group 1, joined,
# is the list). The rubric has one "**Agents**:" paragraph per category.
CUSTOM_AGENT_LIST_REGIONS = (
    ("studio-tests/README.md", re.compile(r"^\| `engine/custom` \|(.*)$", re.M)),
    ("studio-tests/quality-rubric.md", re.compile(r"^\*\*Agents\*\*:(.*(?:\n[^\n|#*].*)*)", re.M)),
    (".claude/docs/effects-map.md", re.compile(r"^\| \*\*Custom\*\* \|(.*)$", re.M)),
)
# The workflow guide's second Custom tree (Agent Hierarchy appendix) and its
# quick-reference rows "| Custom engine: <domain> | `agent` | tier |".
WORKFLOW_GUIDE_SECOND_TREE = re.compile(
    r"^Custom engine projects only \(`engine\.name: Custom`\):\s*\n```[^\n]*\n(.*?)(?=^```)", re.M | re.S)
# Phase 10 R58: studio-tests/CLAUDE.md files a skill on no category line under
# this category ("utility → all remaining skills").
SKILL_CATEGORY_FALLBACK = "utility"
WORKFLOW_GUIDE_CUSTOM_ROW = re.compile(r"^\| Custom engine: [^|]*\| `([\w-]+)` \|", re.M)
# P5 critic F7: the workflow guide names Custom agents outside its Custom
# tree too, so only the tree's code block is searched.
WORKFLOW_GUIDE_CUSTOM_BLOCK = re.compile(r"^Tier 1 \(Director\): +chief-engine-architect.*?(?=^```)", re.M | re.S)
README_CUSTOM_HEADING = "Build your own engine"
README_HIERARCHY_HEADING = "Studio Hierarchy"
# Fix plan AM15 (3): the three full skill lists, each (file, heading or None
# for the whole file).
SKILL_LIST_PLACES = ((".claude/docs/skills-reference.md", None), ("README.md", "Slash Commands"),
                     (".claude/docs/quick-start.md", None))
# Fix plan AM15 (4): the Custom tree in the workflow guide, from its header line
# to the end of its code block; each Custom lead's line and its indented
# continuation lines name the agents under it.
WORKFLOW_GUIDE = "docs/WORKFLOW-GUIDE.md"
WORKFLOW_GUIDE_CUSTOM_TREE = re.compile(r"^Tier 2 \(Leads\) +Tier 3 \(Specialists.*?(?=^```)", re.M | re.S)
# README's Custom tree, from its heading line to the end of its code block.
README_CUSTOM_TREE = re.compile(r"^Custom engine projects only.*?(?=^```)", re.M | re.S)
# Fix plan AM15 (5): a claim's status while its section's Acceptance-8 review
# (fix plan Q9b step 4) was outstanding.
REVIEW_PENDING = "review pending"
SETUP_ENGINE_SKILL = ".claude/skills/setup-engine/SKILL.md"
# Fix 5.4 (Q8): the CI entry coding-standards.md gains for Custom.
CODING_STANDARDS = ".claude/docs/coding-standards.md"
CUSTOM_CI_COMMAND = "bash .claude/scripts/test-run.sh custom"
CUSTOM_CI_PASS_ROWS = ("custom:ctest-pass", "custom:cargo-pass")


def engine_names():
    """Engine names in the first column of .claude/engines/engines.tsv."""
    return {line.split("\t", 1)[0] for line in read(".claude/engines/engines.tsv").splitlines()[1:]
            if line.strip()}


def shared_agents_with_custom_text():
    """Agents with no Custom-agent spec that carry a Custom statement line."""
    custom_agents = {p.stem for p in (ROOT / CUSTOM_AGENT_SPEC_DIR).glob("*.md")}
    return sorted(p.stem for p in (ROOT / ".claude/agents").glob("*.md")
                  if p.stem not in custom_agents
                  and any(CUSTOM_TEXT_LINE.search(line) for line in read(p.relative_to(ROOT)).splitlines()))


def case_fixture_engines(spec_text):
    """The engine each `### Case N:` fixture sets, one entry per case that sets
    one. A fixture is the case's `**Fixture` paragraph, up to the case's next
    bold label or heading."""
    engines = []
    for case in SPEC_CASE_HEADING.split(spec_text.replace("\r", ""))[1:]:
        fixture = re.search(r"(?ms)^\*\*Fixture.*?(?=^\*\*|^#|\Z)", case)
        found = FIXTURE_ENGINE_LINE.search(fixture[0]) if fixture else None
        if found:
            engines.append(found[1])
    return engines


class EngineSupportContracts(unittest.TestCase):
    def test_glob_matcher_follows_documented_semantics(self):
        # The five rows of the pattern table in "How Claude remembers your
        # project" (https://code.claude.com/docs/en/memory, `paths` frontmatter).
        cases = [
            ("**/*.ts", "a.ts", True), ("**/*.ts", "x/y/a.ts", True),
            ("**/*.ts", "x/a.tsx", False),
            ("src/**/*", "src/a.ts", True), ("src/**/*", "src/x/y/a.ts", True),
            ("src/**/*", "lib/src/a.ts", False),
            ("*.md", "a.md", True), ("*.md", "docs/x/a.md", True),
            ("/*.md", "a.md", True), ("/*.md", "docs/a.md", False),
            ("src/components/*.tsx", "src/components/a.tsx", True),
            ("src/components/*.tsx", "src/components/a/b.tsx", False),
            ("src/components/*.tsx", "app/src/components/a.tsx", False),
        ]
        for pattern, path, expected in cases:
            with self.subTest(pattern=pattern, path=path):
                self.assertEqual(glob_match(pattern, path), expected)

    def test_always_loaded_docs_match_baseline(self):
        # R9: text every session loads changes only by added blocks naming Custom.
        imports = re.findall(r"^@(\S+)$", read("CLAUDE.md"), re.M)
        self.assertTrue(imports, "CLAUDE.md imports no file")
        loaded = ["CLAUDE.md"] + imports
        for path in loaded:
            with self.subTest(path=path):
                self.assertIn(path, set(ALWAYS_LOADED_PINNED) | ALWAYS_LOADED_ADDITIVE,
                              "always-loaded file is unclassified")
        crlf = (ROOT / "CLAUDE.md").read_bytes().replace(b"\r", b"").replace(b"\n", b"\r\n")
        self.assertEqual(lf_sha256(crlf), ALWAYS_LOADED_PINNED["CLAUDE.md"],
                         "a CRLF checkout must give the recorded value")
        for path, digest in ALWAYS_LOADED_PINNED.items():
            with self.subTest(path=path):
                self.assertEqual(lf_sha256((ROOT / path).read_bytes()), digest,
                                 "edited: update ALWAYS_LOADED_PINNED in the same diff")
        for path in sorted(ALWAYS_LOADED_ADDITIVE):
            with self.subTest(path=path):
                base = base_release_file(path)
                if base is None:
                    self.skipTest(f"base release {BASE_RELEASE} is not in this clone")
                self.assertEqual(added_unit_violations(base, read(path)), [])
        # AM16(b): the unit is the paragraph or list item, so a non-Custom line
        # placed next to a Custom block is caught (the diff block alone let it
        # through).
        base = "- a\n\n## B\n"
        with self.subTest(check="Custom paragraph alone passes"):
            self.assertEqual(added_unit_violations(base, "- a\n\nOn Custom, x.\n\n## B\n"), [])
        with self.subTest(check="adjacent non-Custom item fails"):
            self.assertTrue(added_unit_violations(base, "- a\n- not named\n\nOn Custom, x.\n\n## B\n"))

    def test_rules_reference_names_every_custom_tools_root(self):
        # Integration (routing lane request, AM28 D6): every `tools/` folder a
        # Custom-only rule loads for is named in that rule's rules-reference
        # row and in the Custom note, which says those rules load "only there".
        reference = read(".claude/docs/rules-reference.md")
        note = re.search(r"^- \*\*Custom\*\*(.*?)(?=^- \*\*|\Z)", reference, re.M | re.S)
        self.assertIsNotNone(note, "rules-reference.md has no Custom note")
        for rule in sorted(custom_only_rules()):
            row = re.search(rf"^\| `{re.escape(rule)}\.md` \|([^|]*)\|", reference, re.M)
            roots = sorted({custom_only_glob_root(g) for g in rule_globs(rule)
                            if custom_only_glob_root(g).startswith("tools/")})
            for root in roots:
                with self.subTest(rule=rule, root=root, place="row"):
                    self.assertIn(f"`{root}**`", row[1])
                with self.subTest(rule=rule, root=root, place="Custom note"):
                    self.assertIn(f"`{root}`", note[1])

    def test_custom_only_rules_do_not_match_other_engine_layouts(self):
        # R1. Paths a Godot, Unity, Unreal or Web project can hold: a native
        # plugin's build files, an engine plugin's third-party code, a web
        # game's vendored scripts.
        other_engine_paths = [
            "addons/x/CMakeLists.txt", "rust/Cargo.toml", "Assets/Plugins/x/CMakeLists.txt",
            "Source/ThirdParty/x/x.cmake", "Plugins/x/Source/ThirdParty/y/CMakeLists.txt",
            "node_modules/x/vendor/a.js", "src/vendor/a.js",
        ]
        rows = re.findall(r"^\| `([\w-]+)\.md` \|(.*)$", read(".claude/docs/rules-reference.md"), re.M)
        custom_only = {rule for rule, rest in rows if "Custom only" in rest}
        self.assertTrue(custom_only, "rules-reference.md marks no rule Custom only")
        listing = subprocess.run(
            ["git", "-C", str(ROOT), "ls-tree", "--name-only", BASE_RELEASE, ".claude/rules/"],
            capture_output=True, text=True)
        checked = set(custom_only)
        with self.subTest(check="Custom-only rows are the rules new since the base release"):
            if listing.returncode != 0:
                self.skipTest(f"base release {BASE_RELEASE} is not in this clone")
            at_base = {Path(p).stem for p in listing.stdout.split()}
            on_disk = {p.stem for p in (ROOT / ".claude/rules").glob("*.md")}
            checked |= on_disk - at_base
            self.assertEqual(custom_only, on_disk - at_base)
        for rule in sorted(checked):
            for path in other_engine_paths:
                with self.subTest(rule=rule, path=path):
                    self.assertFalse(matches(rule, path), f"{rule} loads for {path}")
            with self.subTest(rule=rule, check="guard sentence"):
                body = read(f".claude/rules/{rule}.md").split("---", 2)[2]
                paragraphs = [p for p in re.split(r"\n\s*\n", body)
                              if p.strip() and not p.lstrip().startswith("#")]
                first = " ".join(paragraphs[0].split())
                for token in ("engine.name", "Custom", "ignore"):
                    self.assertIn(token, first)

    def test_upgrade_notes_name_other_engine_output_changes(self):
        # Fix 2.5: on Godot, Unity, Unreal and Web, artifact-check.sh and
        # /gate-check gain the engine line, the skipped count and one
        # ENGINE_SKIPPED row per Custom-scoped catalog step (the allowlist in
        # test_engine_scope.py). The upgrade notes must say so.
        steps = custom_scoped_catalog_steps(read(".claude/docs/workflow-catalog.yaml"))
        self.assertTrue(steps)
        sections = {
            "UPGRADING.md": re.search(r"^## Unreleased.*?(?=^## )", read("UPGRADING.md"), re.M | re.S),
            "CHANGELOG.md": re.search(r"^## \[Unreleased\].*?(?=^## \[)", read("CHANGELOG.md"), re.M | re.S),
        }
        for path, section in sections.items():
            with self.subTest(path=path):
                self.assertIsNotNone(section, "no Unreleased section")
                text = section[0]
                self.assertNotIn("Nothing changes for", text)
                # Fix plan AM3 (IMPL F3): the step ids are searched only in the
                # paragraph that names ENGINE_SKIPPED, so an id named elsewhere
                # in the section cannot stand in for it; and (IMPL F1) that
                # paragraph names the /gate-check checklist line printed on
                # every other engine (gate-pre-production.md:96-98 and the
                # other gate references).
                paragraph = next((p for p in re.split(r"\n\s*\n", text) if "ENGINE_SKIPPED" in p), "")
                self.assertTrue(paragraph, "no paragraph names ENGINE_SKIPPED")
                for token in [*steps, GATE_CHECK_SKIP_LINE]:
                    with self.subTest(token=token):
                        self.assertIn(token, " ".join(paragraph.split()))
        # Fix plan AM2: after fix 2.3, detect-gaps.sh looks in engine/ and game/
        # only on Custom. The clause of the UPGRADING Hooks row that says so
        # (clauses are separated by ";") must state the Custom condition.
        clauses = [c for line in sections["UPGRADING.md"][0].splitlines()
                   for c in line.split(";")
                   if "detect-gaps.sh" in c and "`engine/`" in c and "`game/`" in c]
        self.assertTrue(clauses, "no UPGRADING clause names detect-gaps.sh and engine/, game/")
        for clause in clauses:
            with self.subTest(clause=clause.strip()):
                self.assertIn("Custom", clause)

    def test_public_skill_registry_and_specs_match_disk(self):
        section = read("studio-tests/catalog.yaml").split("\nagents:", 1)[0]
        entries = dict(re.findall(r"  - name: ([\w-]+)\n    spec: ([^\n]+)", section))
        skills = {p.parent.name for p in (ROOT / ".claude/skills").glob("*/SKILL.md")}
        aliases = {name for name in skills if re.search(
            r"^# /[\w-]+ — old name of /[\w-]+$",
            read(f".claude/skills/{name}/SKILL.md"), re.M)}
        self.assertEqual(skills - aliases, set(entries))
        for name, spec in entries.items():
            with self.subTest(skill=name):
                self.assertTrue((ROOT / spec).is_file())
        self.assertIn(f"{len(entries)} slash commands", read(".claude/docs/skills-reference.md"))

    def test_no_doc_row_routes_simd_math_to_physics(self):
        # Phase 10 R55 (docs part): engine/math/'s SIMD primitives are
        # ecs-dod-architect's row (physics supplies collision primitives), so
        # no table row of the docs pairs physics-simulation-engineer with SIMD
        # math. The agents' own text is checked in test_engine_accuracy.py.
        docs = sorted((ROOT / ".claude/docs").rglob("*.md")) + [ROOT / WORKFLOW_GUIDE, ROOT / "README.md"]
        for path in docs:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.lstrip().startswith("|") and "physics-simulation-engineer" in line:
                    with self.subTest(at=f"{path.relative_to(ROOT).as_posix()}:{number}"):
                        self.assertNotRegex(line, r"(?i)\bSIMD math")

    def test_async_io_backends_have_one_layer(self):
        # Phase 10 R136 (layout part): the layout's engine/io/ row holds the
        # request queue and the DirectStorage / io_uring backends and leaves
        # the OS read primitive to engine/platform/ (platform-engineer);
        # world-streaming-engineer, the row's owner, names those backends, and
        # platform-engineer names them only as engine/io/'s.
        row = layout_modules(layout_rows()).get("io")
        self.assertIsNotNone(row, "the layout has no engine/io/ row")
        for needed in ("DirectStorage", "io_uring", "`engine/platform/`", "`platform-engineer`"):
            with self.subTest(row="engine/io/", needed=needed):
                self.assertIn(needed, row["Holds"])
        self.assertEqual(row_owner(row), "world-streaming-engineer")
        self.assertIn("DirectStorage", read(".claude/agents/world-streaming-engineer.md"))
        for unit_line, unit in prose_units(read(".claude/agents/platform-engineer.md")):
            if re.search(r"DirectStorage|io_uring", unit):
                with self.subTest(at=f"platform-engineer.md:{unit_line}"):
                    self.assertRegex(unit, r"`engine/io/`|`world-streaming-engineer`")

    def test_readme_module_list_is_complete_or_points_to_layout(self):
        # Phase 10 R72: README's "Build your own engine" names engine modules
        # in a "one module per folder" list; a list that does not point to the
        # layout as the full list names every engine/ module of the layout.
        section = section_text(read("README.md").replace("\r", ""), README_CUSTOM_HEADING)
        self.assertIsNotNone(section, "README has no Custom route section")
        found = re.search(r"one module per folder([^)]*)\)", " ".join(section.split()))
        self.assertIsNotNone(found, "README names no module list")
        listed = found[1]
        if LAYOUT in listed:
            return
        modules = {m.split("/")[0] for m in layout_modules(layout_rows())}
        self.assertEqual(sorted(modules - set(re.findall(r"`([\w-]+)`", listed))), [],
                         f"the list names some modules and does not point to {LAYOUT}")

    def test_skill_category_lists_match_catalog(self):
        # Phase 10 R58/R70: studio-tests/CLAUDE.md's "Skill categories" block
        # files each skill under its catalog `category:` (a skill on no line
        # is `utility`), and a studio-tests/README.md category row that is not
        # cut short with "…" lists exactly that category's skills. Checked for
        # every skill: at the base release all of them agreed.
        catalog = read("studio-tests/catalog.yaml").replace("\r", "").split("\nagents:", 1)[0]
        categories = dict(re.findall(r"^  - name: ([\w-]+)\n(?:    .*\n)*?    category: (\w+)", catalog, re.M))
        self.assertTrue(categories, "no skill category in the catalog")
        block = re.search(r"^## Skill categories\s*\n```[^\n]*\n(.*?)^```",
                          read("studio-tests/CLAUDE.md").replace("\r", ""), re.M | re.S)
        self.assertIsNotNone(block, "studio-tests/CLAUDE.md has no Skill categories block")
        listed, current = {}, None
        for line in block[1].splitlines():
            head = re.match(r"^(\w+)\s+→(.*)$", line)
            if head:
                current, line = head[1], head[2]
            for name in re.findall(r"[\w-]+", line):
                if current and name not in ("all", "remaining", "skills"):
                    listed[name] = current
        for skill, category in sorted(categories.items()):
            with self.subTest(file="studio-tests/CLAUDE.md", skill=skill):
                self.assertEqual(listed.get(skill, SKILL_CATEGORY_FALLBACK), category)
        readme = read("studio-tests/README.md").replace("\r", "")
        for category, cell in re.findall(r"^\| `(\w+)` \| ([^|]*) \|", section_text(readme, "Skill categories")
                                         or "", re.M):
            if "…" in cell:
                continue
            with self.subTest(file="studio-tests/README.md", category=category):
                self.assertEqual(sorted(re.findall(r"[\w-]+", cell)),
                                 sorted(s for s, c in categories.items() if c == category))

    def test_every_agent_has_catalog_spec_and_roster_entry(self):
        catalog = read("studio-tests/catalog.yaml")
        entries = dict(re.findall(r"  - name: ([\w-]+)\n    spec: ([^\n]+)", catalog))
        roster = read(".claude/docs/agent-roster.md")
        for agent in sorted((ROOT / ".claude/agents").glob("*.md")):
            with self.subTest(agent=agent.stem):
                self.assertIn(agent.stem, entries)
                self.assertTrue((ROOT / entries[agent.stem]).is_file())
                self.assertIn(f"`{agent.stem}`", roster)

    def test_custom_setup_registers_every_custom_agent(self):
        setup = read(".claude/skills/setup-engine/references/custom.md")
        additional = re.search(r'^  additional: \[(.*)\]', setup, re.M)[1]
        configured = set(re.findall(r'"([\w-]+)"', additional))
        configured.update(re.findall(r'^  (?:code|shader|ui): "([\w-]+)"', setup, re.M))
        for spec in sorted((ROOT / "studio-tests/agents/engine/custom").glob("*.md")):
            with self.subTest(agent=spec.stem):
                self.assertIn(spec.stem, configured)

    def test_engine_and_rust_paths_receive_subsystem_rules(self):
        cases = {
            "engine-code": ["engine/core/src/tick.cpp", "crates/core/src/tick.rs",
                            "crates/memory/src/arena.rs", "crates/jobs/src/pool.rs",
                            "crates/platform/src/window.rs", "crates/input/src/action.rs"],
            "ecs-math-code": ["crates/ecs/src/world.rs", "crates/math/src/aabb.rs"],
            "rhi-renderer-code": ["crates/rhi/src/device.rs", "crates/renderer/src/graph.rs",
                                  "crates/vfx/src/particles.rs", "crates/xr/src/frame.rs"],
            "simulation-code": ["engine/cinematics/src/player.cpp", "engine/camera/src/blend.cpp",
                                "engine/sim/src/tick.cpp", "crates/sim/src/tick.rs",
                                "crates/physics/src/solver.rs", "crates/animation/src/pose.rs",
                                "crates/cinematics/src/player.rs", "crates/camera/src/blend.rs"],
            "audio-code": ["crates/audio/src/mixer.rs"],
            "scripting-code": ["crates/scripting/src/vm.rs"],
            "streaming-io-code": ["crates/streaming/src/cell.rs", "crates/assets/src/load.rs",
                                  "crates/io/src/read.rs", "crates/media/src/decode.rs"],
            "editor-code": ["crates/editor_cinematics/src/model.rs", "crates/editor-level/src/picking.rs",
                            "crates/editor/src/lib.rs"],
            "ai-code": ["crates/ai/src/navigation.rs"],
            "network-code": ["crates/net/src/replication.rs", "crates/online/src/session.rs"],
            "ui-code": ["crates/ui/src/text.rs"],
            "tools-code": ["crates/tools/src/cook.rs"],
            "test-standards": ["crates/physics/tests/replay.rs"],
            "shader-code": ["crates/shaders/cull.hlsl"],
        }
        for rule, paths in cases.items():
            for path in paths:
                with self.subTest(rule=rule, path=path):
                    self.assertTrue(matches(rule, path), f"{path} bypasses {rule}")

    def test_published_counts_match_disk(self):
        # R8, fix 5.1 (replaces the three-file agent-total test with a
        # superset). Each site's number equals its kind's value from disk; then
        # every count phrase in current-release text is claimed by a site or an
        # exception, so a new count sentence cannot ship unchecked.
        values = published_count_values()
        architects, leads = custom_hierarchy()
        with self.subTest(check="exactly one Custom architect"):
            self.assertEqual(len(architects), 1, architects)
        claimed = {}
        for path, pattern, kind in COUNT_SITES:
            with self.subTest(path=path, pattern=pattern):
                text = read(path)
                start, end = count_region(path, text)
                hits = list(re.compile(pattern, re.M).finditer(text, start, end))
                # P5 critic F8: the site claims its phrase before any skip, so
                # a clone without the base release skips the new-item sites by
                # name (O14) instead of failing them in the sweep below.
                for hit in hits:
                    claimed.setdefault(path, set()).add(hit.start(1))
                if kind not in values:
                    self.skipTest(f"base release {BASE_RELEASE} is not in this clone")
                self.assertTrue(hits, "count site not found")
                for hit in hits:
                    self.assertEqual(parse_count(hit[1]), values[kind],
                                     f"line {text.count(chr(10), 0, hit.start()) + 1}: {hit[0]!r} ({kind})")
        swept = count_sweep_files()
        for path in swept:
            text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
            start, end = count_region(path, text)
            spare = list(COUNT_EXCEPTIONS.get(path, ()))
            for hit in COUNT_PHRASE.finditer(text, start, end):
                phrase = " ".join(hit[0].split())
                if hit.start(1) in claimed.get(path, ()):
                    continue
                if phrase in spare:
                    spare.remove(phrase)
                    continue
                with self.subTest(path=path, unclassified=phrase):
                    self.fail(f"line {text.count(chr(10), 0, hit.start()) + 1}: unclassified count "
                              f"{phrase!r}: add a COUNT_SITES entry, or a COUNT_EXCEPTIONS entry with its reason")
            with self.subTest(path=path, check="every exception still occurs"):
                self.assertEqual(spare, [], "COUNT_EXCEPTIONS lists a phrase the file no longer has")
        for path in COUNT_EXCEPTIONS:
            with self.subTest(path=path, check="exception file is swept"):
                self.assertIn(path, swept)

    def test_upgrade_notes_name_every_custom_only_root(self):
        # P5 critic F3 (fix plan AM16(a), O1): where the notes say a Custom-only
        # rule can still load on another engine, they name every root its globs
        # reach: each glob's literal prefix (the path up to the first wildcard
        # segment, or a root file's name) is named, or a folder above it is
        # that is itself an any-file root (`<folder>/**`). P5 critic F11: a
        # folder named only for its build files (`game/`) does not cover an
        # any-file root below it (`game/scripts/**`).
        globs = [g for rule in custom_only_rules() for g in rule_globs(rule)]
        roots = sorted({custom_only_glob_root(g) for g in globs})
        any_file_roots = {custom_only_glob_root(g) for g in globs if g.endswith("/**")
                          and custom_only_glob_root(g) == g.lstrip("/")[:-2]}
        self.assertTrue(roots)
        unreleased = {path: region.search(read(path))[0] for path, region in RELEASE_NOTE_SECTIONS.items()}
        passages = {
            "CHANGELOG.md": next((p for p in re.split(r"\n\s*\n", unreleased["CHANGELOG.md"])
                                  if "Custom-only rules" in p), ""),
            "UPGRADING.md": next((l for l in unreleased["UPGRADING.md"].splitlines()
                                  if l.startswith("| **Other engines** |")), ""),
        }
        for path, passage in passages.items():
            self.assertTrue(passage, f"{path}: no passage on Custom-only rules")
            named = set(re.findall(r"`([^`]+)`", passage))
            for root in roots:
                with self.subTest(path=path, root=root):
                    self.assertTrue(any(n == root or (n in any_file_roots and root.startswith(n)) for n in named),
                                    f"{root} is not named")

    def test_count_sweep_sees_every_count_form(self):
        # P5 critic F5, F6, F9 (fix plan AM16(a)): the sweep reads the
        # hyphenated `-agent` form, a count wrapped across lines, and the
        # Custom subset nouns; a number that labels a tier or phase is not a
        # count.
        for text, expected in [("Worth raising on a 49-agent project.", ["49-agent"]),
                               ("The studio ships all 78\nskills in one place.", ["78\nskills"]),
                               ("It names 24\n  Custom agents.", ["24\n  Custom agents"]),
                               ("four leads and nineteen specialists", ["four leads", "nineteen specialists"]),
                               ("all key Tier 2 leads; Phase 3 agents", [])]:
            with self.subTest(text=text):
                self.assertEqual([m[0] for m in COUNT_PHRASE.finditer(text)], expected)

    def test_new_item_lists_match_disk(self):
        # R8, fix 5.2: every new Custom agent, skill and rule is named in the
        # Unreleased upgrade notes; the Custom agents also in the model tiers
        # and the studio-tests tier list; /setup-engine keeps no copy of C7.
        custom = sorted(p.stem for p in (ROOT / CUSTOM_AGENT_SPEC_DIR).glob("*.md"))
        self.assertTrue(custom)
        base_skills, base_rules = base_release_names(".claude/skills"), base_release_names(".claude/rules")
        if base_skills is None or base_rules is None:
            self.skipTest(f"base release {BASE_RELEASE} is not in this clone")
        new_skills = sorted({p.parent.name for p in (ROOT / ".claude/skills").glob("*/SKILL.md")} - base_skills)
        new_rules = sorted({p.stem for p in (ROOT / ".claude/rules").glob("*.md")} - base_rules)
        self.assertTrue(new_skills and new_rules)
        expected = ([f"`{a}`" for a in custom] + [f"`/{s}`" for s in new_skills]
                    + [f"`{r}.md`" for r in new_rules])
        for path, region in RELEASE_NOTE_SECTIONS.items():
            section = region.search(read(path))
            self.assertIsNotNone(section, f"{path}: no Unreleased section")
            for name in expected:
                with self.subTest(path=path, name=name):
                    self.assertIn(name, section[0])
        # README's "Build your own engine" section is a third list of the new
        # skills (fix plan D1). Its agents are described by team and domain,
        # its rules by path glob, so only the skills are a name list.
        readme = section_text(read("README.md"), README_CUSTOM_HEADING)
        self.assertIsNotNone(readme, "README has no Custom route section")
        for name in [f"`/{s}`" for s in new_skills]:
            with self.subTest(path="README.md", name=name):
                self.assertIn(name, readme)
        # Fix plan AM15 (3): the full skill lists name every new skill.
        for path, heading in SKILL_LIST_PLACES:
            text = read(path) if heading is None else section_text(read(path), heading)
            self.assertIsNotNone(text, f"{path}: no {heading} section")
            for skill in new_skills:
                with self.subTest(path=path, section=heading, skill=skill):
                    self.assertIn(f"`/{skill}`", text)
        # README's hierarchy tree names every agent, the Custom set included.
        tree = section_text(read("README.md"), README_HIERARCHY_HEADING)
        self.assertIsNotNone(tree, "README has no hierarchy section")
        for agent in custom:
            with self.subTest(path="README.md", section=README_HIERARCHY_HEADING, agent=agent):
                self.assertRegex(tree, rf"(?<![\w-]){re.escape(agent)}(?![\w-])")
        block = WORKFLOW_GUIDE_CUSTOM_BLOCK.search(read(WORKFLOW_GUIDE).replace("\r", ""))
        self.assertIsNotNone(block, "no Custom tree in the workflow guide")
        places = [(path, read(path)) for path in CUSTOM_AGENT_LIST_FILES] + [(WORKFLOW_GUIDE, block[0])]
        # Phase 10 R56/R69: the scoped lists, the guide's second tree and its
        # "Custom engine:" quick-reference rows.
        for path, pattern in CUSTOM_AGENT_LIST_REGIONS:
            found = pattern.findall(read(path).replace("\r", ""))
            self.assertTrue(found, f"{path}: the Custom agent list is not found")
            places.append((path, "\n".join(found)))
        guide = read(WORKFLOW_GUIDE).replace("\r", "")
        second = WORKFLOW_GUIDE_SECOND_TREE.search(guide)
        self.assertIsNotNone(second, "no second Custom tree in the workflow guide")
        places.append((f"{WORKFLOW_GUIDE} (second tree)", second[1]))
        places.append((f"{WORKFLOW_GUIDE} (Custom engine: rows)",
                       " ".join(f"`{a}`" for a in WORKFLOW_GUIDE_CUSTOM_ROW.findall(guide))))
        for path, text in places:
            for agent in custom:
                with self.subTest(path=path, agent=agent):
                    self.assertRegex(text, rf"(?<![\w-]){re.escape(agent)}(?![\w-])")
        setup = read(SETUP_ENGINE_SKILL)
        named = [a for a in custom if re.search(rf"(?<![\w-]){re.escape(a)}(?![\w-])", setup)]
        with self.subTest(path=SETUP_ENGINE_SKILL):
            self.assertLess(len(named), 2, f"keeps its own Custom agent list: {named}")
            self.assertIn("C7", setup)

    def test_coding_standards_has_custom_ci_entry(self):
        # Fix 5.4 (D2, Q8): the always-loaded CI list carries a Custom entry
        # that runs test-run.sh custom and passes only on a ctest or cargo pass
        # row; the What NOT to Automate list gains a Custom block. R9
        # (test_always_loaded_docs_match_baseline) guards that both are added
        # blocks naming Custom.
        text = read(CODING_STANDARDS)
        ci = section_text(text, "CI/CD Rules")
        self.assertIsNotNone(ci, "no CI/CD Rules section")
        entry = re.search(r"^\s*- \*\*Custom\*\*:(.*(?:\n\s{4,}\S.*)*)", ci, re.M)
        self.assertIsNotNone(entry, "no **Custom** entry in the CI list")
        body = " ".join(entry[1].split())
        self.assertIn(CUSTOM_CI_COMMAND, body)
        for row in CUSTOM_CI_PASS_ROWS:
            with self.subTest(row=row):
                self.assertIn(row, body)
        not_automated = section_text(text, "What NOT to Automate")
        self.assertIsNotNone(not_automated)
        self.assertRegex(" ".join(not_automated.split()), r"engine\.name[` ]*:?[` ]*Custom")

    def test_workflow_guide_tree_places_owners_under_their_lead(self):
        # Fix plan AM15 (4): in the guide's Custom tree, every layout owner
        # whose Lead is a Custom lead stands under that lead (engine/net/'s
        # network-programmer under core-systems-lead, per owner answer 5.2).
        tree = WORKFLOW_GUIDE_CUSTOM_TREE.search(read(WORKFLOW_GUIDE).replace("\r", ""))
        self.assertIsNotNone(tree, "no Custom tree in the workflow guide")
        _, leads = custom_hierarchy()
        under, current = {}, None
        for line in tree[0].splitlines()[1:]:
            first = line.split()[0] if line.strip() and not line[0].isspace() else None
            if first in leads:
                current = first
                line = line[len(first):]
            if current:
                under.setdefault(current, set()).update(re.findall(r"[a-z][\w-]*[a-z]", line))
        self.assert_owners_under_their_lead(under, leads)
        # Phase 10 R69: the guide's second tree (Agent Hierarchy appendix),
        # where a lead's line is "|-- <lead>" and its specialists follow.
        second = WORKFLOW_GUIDE_SECOND_TREE.search(read(WORKFLOW_GUIDE).replace("\r", ""))
        self.assertIsNotNone(second, "no second Custom tree in the workflow guide")
        under, current = {}, None
        for line in second[1].splitlines():
            names = re.findall(r"[a-z][\w-]*[a-z]", line)
            if names and names[0] in leads:
                current = names[0]
            elif current:
                under.setdefault(current, set()).update(names)
        self.assert_owners_under_their_lead(under, leads)

    def test_readme_tree_places_owners_under_their_lead(self):
        # Fix plan AM15 (4), README: the same rule for README's Custom tree,
        # whose groups open with "under <lead>:".
        tree = README_CUSTOM_TREE.search(read("README.md").replace("\r", ""))
        self.assertIsNotNone(tree, "no Custom tree in README")
        _, leads = custom_hierarchy()
        under, current = {}, None
        for line in tree[0].splitlines()[1:]:
            group = re.search(r"under ([\w-]+):", line)
            if group:
                current = group[1] if group[1] in leads else None
                line = line[group.end():]
            if current:
                under.setdefault(current, set()).update(re.findall(r"[a-z][\w-]*[a-z]", line))
        self.assert_owners_under_their_lead(under, leads)

    def assert_owners_under_their_lead(self, under, leads):
        """Every layout owner whose Lead is a Custom lead is among the agents
        a tree places under that lead; `under` maps lead -> names in its group."""
        self.assertEqual(set(under), leads, "the tree does not have one entry per Custom lead")
        for row in layout_rows():
            lead, owner = row_lead(row), row_owner(row)
            if lead in leads and owner and owner not in leads:
                with self.subTest(path=row["paths"], owner=owner, lead=lead):
                    self.assertIn(owner, under[lead])

    def test_ledgered_sections_record_their_review(self):
        # Fix plan AM15 (5): every section in the R12 manifest has passed its
        # Acceptance-8 review (fix plan Q9b step 4), so no claim recorded for
        # one of those sections may still say the review is pending.
        sections = {(path, heading) for path, heading, _ in TECHNICAL_SECTIONS}
        for claim in ledger("claims"):
            if (claim.get("file"), claim.get("heading")) in sections:
                with self.subTest(claim=claim["claim_id"]):
                    self.assertNotIn(REVIEW_PENDING, claim.get("status", ""))

    def test_every_documented_engine_module_gets_its_rule_in_both_layouts(self):
        rows = [line.split("|") for line in read(".claude/docs/custom-engine-layout.md").splitlines()
                if line.startswith("| `engine/")]
        self.assertTrue(rows)
        for cells in rows:
            rule = re.search(r"`([\w-]+)\.md`", cells[3])[1]
            for module in re.findall(r"`(engine/[^`]+/)`", cells[1]):
                for root in (module, module.replace("engine/", "crates/", 1)):
                    with self.subTest(module=root, rule=rule):
                        self.assertTrue(matches(rule, root + "src/example.rs"))

    def test_setup_engine_owners_match_module_map(self):
        # Fix 3.1 (Q3 item 3) extends this from the engine/ rows to every path
        # the setup routing table names, the "Outside `engine/`" rows included:
        # each resolves through the layout to the same owner (a `sub/` note in
        # the layout's Owner cell decides a sub-folder). A file extension
        # (`.hlsl`) routes by type, not by path, and is not a layout path.
        rows = layout_rows()
        table = section_text(read(".claude/skills/setup-engine/references/custom.md"),
                             "File Extension Routing")
        self.assertIsNotNone(table, "setup must publish module ownership")
        configured = []
        # Only the table right under the heading.
        for line in re.split(r"\n\s*\n", table.strip())[0].splitlines():
            cells = line.split("|")
            owner = re.match(r"`?([\w-]+)", cells[-2].strip()) if len(cells) >= 4 else None
            if owner and cells[1].strip().startswith("`"):
                configured += [(path, owner[1]) for path in re.findall(r"`([^`]+)`", cells[1])
                               if not path.startswith(".")]
        self.assertTrue(configured, "setup must publish module ownership")
        for path, owner in configured:
            with self.subTest(path=path):
                row = resolve_layout_row(path, rows)
                self.assertIsNotNone(row, "no layout row covers this path")
                expected = row_owner(row)
                for literal in row["paths"]:
                    if literal.endswith("/") and path.startswith(literal) and path != literal:
                        sub = path[len(literal):].split("/")[0] + "/"
                        expected = row_sub_owners(row).get(sub, expected)
                self.assertEqual(owner, expected)

    # ---------------------------------------------------------------- Phase 3

    def test_routing_agrees_with_layout(self):
        # R3: every other statement pairing an engine module with an agent
        # names that module's Owner or Lead in the layout, and the module has
        # a layout row. Forms scanned: see routing_pairs.
        rows = layout_rows()
        modules = layout_modules(rows)
        agents = agent_names()
        self.assertTrue(modules)
        seen = 0
        for base in ROUTE_SCAN_DIRS:
            for path in sorted((ROOT / base).rglob("*.md")):
                rel = path.relative_to(ROOT).as_posix()
                if rel == LAYOUT:
                    continue
                text = path.read_text(encoding="utf-8")
                for number, module, agent in (routing_pairs(text, modules, agents)
                                              + concern_pairs(text, agents)):
                    seen += 1
                    with self.subTest(at=f"{rel}:{number}", module=module, agent=agent):
                        self.assertIn(module, modules, "module has no layout row")
                        row = modules[module]
                        self.assertIn(agent, {row_owner(row), row_lead(row)},
                                      f"layout: owner {row_owner(row)}, lead {row_lead(row)}")
        self.assertTrue(seen, "the scan found no routing statement: the forms are out of date")

    def test_no_enumerated_lead_list_outside_layout(self):
        # Phase 10 R1-R3/R54: an agent routes engine work by the layout's
        # Owner and Lead columns, never by a closed list of Custom leads, which
        # leaves out lead-programmer's rows and the `none`-lead rows. A sentence
        # naming three or more of the Custom leads with a routing phrase fails,
        # and so does a "module table above" / "map above" in an agent file
        # that has no table to point at.
        for path in sorted((ROOT / ".claude/agents").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(ROOT).as_posix()
            for number, unit in prose_units(text):
                for sentence in re.split(r"(?<=\.)\s+(?=[A-Z`*])", unit):
                    named = [lead for lead in CUSTOM_ENGINE_LEADS
                             if re.search(rf"(?<![\w-]){re.escape(lead)}(?![\w-])", sentence)]
                    if len(named) >= ENUMERATED_LEADS_MIN and ROUTING_PHRASE.search(sentence):
                        with self.subTest(at=f"{rel}:{number}"):
                            self.fail(f"routes by a closed lead list {named}; cite {LAYOUT}'s "
                                      "Owner and Lead columns instead")
                local = LOCAL_MAP_PHRASE.search(unit)
                if local and not re.search(r"(?m)^\|", text):
                    with self.subTest(at=f"{rel}:{number}"):
                        self.fail(f"cites '{local[0]}', but the file has no table")

    def test_pipeline_tools_claims_name_their_layout_row(self):
        # Phase 10 R129 (AM28 D6): the layout splits tools/ between
        # asset-build-tooling-engineer (tools/ci/, tools/build/, cook-side
        # tools) and tools-programmer (standalone pipeline and batch tools,
        # validators, report generators). A statement that gives pipeline
        # tools to tools-programmer names a `tools/` path whose layout row is
        # tools-programmer's, so it states the split instead of keeping a copy
        # of the ownership. A statement is a table row, list item or paragraph;
        # one the base release already had is not a Custom claim and is skipped.
        # Every `tools/` path a statement assigns must be its assignee's in the
        # layout: a table row assigns its paths to the agent of its last cell
        # ("you" is the file's agent); in prose a clause (sentence or `;` part)
        # assigns each path to the nearest hand-off after it, else before it,
        # else to the last agent named before it in the clause, else to the
        # agent file's own agent (its responsibilities), else to
        # tools-programmer, whom the statement names. Every row of
        # tools-programmer's own file that names a `tools/` path is checked,
        # whatever its wording.
        rows = layout_rows()
        agent_re = "|".join(sorted(agent_names(), key=len, reverse=True))
        handoff = re.compile(TOOLS_HANDOFF.format(a=agent_re))
        files = (sorted((ROOT / ".claude/agents").glob("*.md")) + sorted((ROOT / ".claude/rules").glob("*.md"))
                 + [ROOT / p for p in PIPELINE_TOOLS_DOCS])
        seen = 0
        for path in files:
            rel = path.relative_to(ROOT).as_posix()
            own_agent = path.stem if path.parent.name == "agents" else None
            text = path.read_text(encoding="utf-8").replace("\r", "")
            base = " ".join((base_release_file(rel) or "").split())
            statements = [(n, line) for n, line in enumerate(text.splitlines(), 1) if line.lstrip().startswith("|")]
            statements += prose_units(text)
            for number, statement in statements:
                flat = " ".join(statement.split())
                if flat in base:
                    continue
                is_row = flat.startswith("|")
                own_row = own_agent == TOOLS_PROGRAMMER and is_row and TOOLS_PATH.search(flat)
                if not own_row and not (PIPELINE_TOOLS.search(flat)
                                        and re.search(r"(?<![\w-])tools-programmer(?![\w-])", flat)):
                    continue
                assigned = []
                if is_row:
                    cells = [c.strip() for c in flat.strip("|").split("|")]
                    named = re.search(rf"(?<![\w-])({agent_re})(?![\w-])", cells[-1])
                    assignee = own_agent if cells[-1] == "you" else (named[1] if named else None)
                    assigned = [(p, assignee) for p in TOOLS_PATH.findall(flat)]
                else:
                    for sentence in SENTENCE_SPLIT.split(flat):
                        for clause in sentence.split(";"):
                            hands = [(m.start(), m.end(), next(g for g in m.groups() if g))
                                     for m in handoff.finditer(clause)]
                            for found in TOOLS_PATH.finditer(clause):
                                after = [h for h in hands if h[0] >= found.end()]
                                before = [h for h in hands if h[1] <= found.start()]
                                hand = after[0] if after else (before[-1] if before else None)
                                subjects = re.findall(rf"(?<![\w-])({agent_re})(?![\w-])", clause[:found.start()])
                                who = (hand[2] if hand else subjects[-1] if subjects
                                       else own_agent or TOOLS_PROGRAMMER)
                                assigned.append((found[1], own_agent if who == "yours" else who))
                seen += 1
                with self.subTest(at=f"{rel}:{number}", text=flat[:90]):
                    for tools_path, assignee in assigned:
                        owner = row_owner(resolve_layout_row(tools_path, rows) or {})
                        self.assertEqual(owner, assignee, f"`{tools_path}` is assigned to {assignee}; "
                                         f"its layout row's owner is {owner}")
                    if not is_row or cells[-1] == "you" or assignee == TOOLS_PROGRAMMER:
                        self.assertIn(TOOLS_PROGRAMMER, {a for _, a in assigned},
                                      "names no `tools/` path it gives to tools-programmer")
        self.assertTrue(seen, "the scan found no pipeline-tools claim: the forms are out of date")

    def test_skill_catalog_labels_match_engine_gate(self):
        # Phase 10 R9/R49 (AM28 D2): a catalog row labelled "Custom engine:"
        # is for a skill that stops with the NOT ASSESSED engine gate on any
        # other engine; a skill without that gate runs on every engine and is
        # labelled "Any engine (Custom-oriented):". README's Custom route names
        # the ungated ones as any-engine skills.
        def gated(skill):
            path = ROOT / f".claude/skills/{skill}/SKILL.md"
            return path.is_file() and CUSTOM_SKILL_GATE in path.read_text(encoding="utf-8")
        seen = 0
        for path in SKILL_CATALOG_FILES:
            for number, line in enumerate(read(path).splitlines(), 1):
                row = re.match(r"^\| `/([\w-]+)` \| (Custom engine:|Any engine \(Custom-oriented\):)", line)
                if not row:
                    continue
                seen += 1
                with self.subTest(at=f"{path}:{number}", skill=row[1]):
                    self.assertEqual(gated(row[1]), row[2] == CUSTOM_ONLY_LABEL,
                                     f"labelled '{row[2]}' but the skill's engine gate says otherwise")
        self.assertTrue(seen, "no labelled skill row: the form is out of date")
        # Base skills the section names (what they gain on Custom) are not
        # new skills and carry no label there.
        base_skills = base_release_names(".claude/skills")
        if base_skills is None:
            self.skipTest(f"base release {BASE_RELEASE} is not in this clone")
        readme = " ".join((section_text(read("README.md"), README_CUSTOM_HEADING) or "").split())
        for skill in sorted(set(re.findall(r"`/([\w-]+)`", readme)) - base_skills):
            if (ROOT / f".claude/skills/{skill}").is_dir() and not gated(skill):
                with self.subTest(at="README.md", skill=skill):
                    sentence = next((s for s in SENTENCE_SPLIT.split(readme) if f"`/{skill}`" in s
                                     and ANY_ENGINE_LABEL in s), None)
                    self.assertIsNotNone(sentence, f"/{skill} runs on any engine; README's Custom route does not say so")

    def test_prototyper_custom_path_follows_prototype_phase3(self):
        # Phase 10 R5: /prototype's Phase 3 labels the browser sketch "not
        # recommended here" on a project that names an engine, Custom
        # included; the prototyper's Custom section follows that phase instead
        # of recommending the browser first.
        phase3 = read(PROTOTYPE_PHASE3)
        self.assertIn(BROWSER_SKETCH_NOT_RECOMMENDED, phase3)
        section = section_text(read(PROTOTYPER_AGENT), "On a Custom Engine Project")
        self.assertIsNotNone(section, "prototyper has no Custom section")
        section = " ".join(section.split())
        self.assertNotRegex(section, r"(?i)browser first")
        self.assertIn("Phase 3", section)

    def test_every_custom_glob_has_a_layout_row(self):
        # R3, reverse direction: every glob of a Custom rule falls in a layout
        # row that names the rule, and every row is reached by a glob of a rule
        # it names, or says `none` with a reason. The engine-wide rule named
        # above the table is checked by test_engine_wide_rule_reaches_every_module.
        rows = layout_rows()
        custom_only = custom_only_rules()
        named = {rule for row in rows for rule in row_rules(row)}
        wide = engine_wide_rules()
        for rule in sorted((custom_only | named) - wide):
            self.assertTrue((ROOT / f".claude/rules/{rule}.md").is_file(), rule)
            for glob in rule_globs(rule):
                if rule not in custom_only and not glob.startswith(CUSTOM_ROOTS):
                    continue
                with self.subTest(rule=rule, glob=glob):
                    sample = glob_sample(glob)
                    self.assertTrue(any(rule in row_rules(row) and any(
                        glob_match(g, sample) for g, _ in row_globs(row)) for row in rows),
                        "no layout row names this rule for this glob")
        for row in rows:
            with self.subTest(row=f"{LAYOUT}:{row['line']}"):
                if NONE_WITH_REASON.match(row.get("Path rule", "")):
                    continue
                self.assertTrue(row_rules(row), "row names no rule and no reason")
                self.assertTrue(any(glob_match(g, glob_sample(rule_glob)) or glob_match(rule_glob, glob_sample(g))
                                    for rule in row_rules(row) for rule_glob in rule_globs(rule)
                                    for g, _ in row_globs(row)), "no glob of the row's rules reaches it")

    def test_lead_column_agrees_with_agent_files(self):
        # R3: (a) the owner reports to the Lead (its "Reports to" line, or a
        # line naming the Lead and the row's path); (b) the Lead's file names
        # the owner; (c) a lead with the Agent tool lists every owner it leads
        # as a subagent_type, and its "Start only" count word equals the lines.
        # No agent's tools: line is changed for this test.
        rows = layout_rows()
        self.assertTrue(rows and all("Lead" in row for row in rows), "the layout has no Lead column")
        agents = {name: read(f".claude/agents/{name}.md") for name in agent_names()}
        for row in rows:
            owner, lead = row_owner(row), row_lead(row)
            with self.subTest(row=f"{LAYOUT}:{row['line']}"):
                self.assertIn(owner, agents)
                self.assertIsNotNone(lead, "Lead cell is neither an agent nor `none` with a reason")
                if lead == "none":
                    continue
                self.assertIn(lead, agents)
                for who in {owner, *row_sub_owners(row).values()}:
                    self.assertTrue(any(
                        lead in line and ("reports to" in line.lower()
                                          or any(p in line for p in row["paths"]))
                        for line in agents[who].splitlines()), f"(a) {who} does not report to {lead}")
                    self.assertRegex(agents[lead], rf"(?<![\w-]){re.escape(who)}(?![\w-])",
                                     f"(b) {lead} does not name {who}")
        for lead in sorted({row_lead(row) for row in rows} - {"none", None}):
            text = agents[lead]
            if not re.search(r"^tools:.*\bAgent\b", text, re.M):
                continue
            with self.subTest(lead=lead, check="(c) delegation list"):
                started = re.findall(r"subagent_type: ([\w-]+)", text)
                led = {row_owner(row) for row in rows if row_lead(row) == lead} - {lead}
                self.assertEqual(sorted(led - set(started)), [], "owners it leads but cannot start")
                count = re.search(r"Start only\s+(the|those)\s+(\w+)", text)
                self.assertIsNotNone(count, "a lead with the Agent tool has no Start only sentence")
                self.assertEqual(NUMBER_WORDS.get(count[2].lower()), len(started))

    def test_only_the_layout_owner_claims_change_rights(self):
        # Fix plan AM5 (C3 remainder): an agent's "Must NOT" list bounds what it
        # may change with "... outside `path`, `path` ..."; every engine path it
        # names there is one it claims, so the layout must make the agent that
        # path's owner (or a `sub/` owner in the Owner cell). The form is the one
        # found in the tree when the test was written; a new form must be added
        # here, or a claim written in it goes unchecked
        # (.claude/rules/skill-authoring.md:76-79).
        rows = layout_rows()
        seen = 0
        for path in sorted((ROOT / ".claude/agents").glob("*.md")):
            section = section_text(path.read_text(encoding="utf-8"), "What This Agent Must NOT Do") or ""
            items = re.split(r"\n(?=\s*[-*] )", section)
            for item in items:
                clause = re.search(r"\boutside\b(.*)", " ".join(item.split()))
                if not clause:
                    continue
                for claimed in re.findall(r"`((?:engine|crates)/[^`]+)`", clause[1]):
                    seen += 1
                    with self.subTest(agent=path.stem, path=claimed):
                        row = resolve_layout_row(claimed, rows)
                        self.assertIsNotNone(row, "no layout row covers this path")
                        owners = {row_owner(row), *row_sub_owners(row).values()}
                        self.assertIn(path.stem, owners, f"layout owner: {row_owner(row)}")
        self.assertTrue(seen, "the scan found no change-rights claim: the form is out of date")
        # Fix plan AM9: an agent's spec states the same bound in its summary,
        # "Does NOT own: ... outside `path`, `path` and ... (owners)"; the
        # claimed paths run from "outside" to the first "(" (the form found in
        # the tree when this was written; extend it with any new one).
        spec_seen = 0
        for path in sorted((ROOT / "studio-tests/agents").rglob("*.md")):
            for line in re.findall(r"^Does NOT own:(.*)$", path.read_text(encoding="utf-8"), re.M):
                clause = re.search(r"\boutside\b([^(]*)", line)
                if not clause:
                    continue
                for claimed in re.findall(r"`((?:engine|crates)/[^`]+)`", clause[1]):
                    spec_seen += 1
                    with self.subTest(spec=path.relative_to(ROOT).as_posix(), path=claimed):
                        row = resolve_layout_row(claimed, rows)
                        self.assertIsNotNone(row, "no layout row covers this path")
                        owners = {row_owner(row), *row_sub_owners(row).values()}
                        self.assertIn(path.stem, owners, f"layout owner: {row_owner(row)}")
        self.assertTrue(spec_seen, "the spec scan found no change-rights claim: the form is out of date")
        # Phase 10 R4/R131 (AM28 D1): a concern the layout files under one
        # module is claimed only by that module's owner. Forms: a table row
        # with the concern in any cell (the first agent of its last cell owns
        # it); "You own ..." naming the concern in an agent file; a sentence
        # that routes or hands the concern "to `agent`"; "`agent` owns ..." or
        # "agent (owns ..." up to the clause's end, in prose or a table cell.
        # Negated sentences ("does NOT hand it to ...") are not claims.
        rows = layout_rows()
        agent_re = "|".join(sorted(agent_names(), key=len, reverse=True))
        owns = re.compile(OWNS_CLAUSE.format(a=agent_re))
        files = (sorted((ROOT / ".claude/agents").glob("*.md")) + sorted((ROOT / "studio-tests/agents").rglob("*.md"))
                 + [ROOT / ENGINE_COVERAGE_DOC])
        concern_seen = 0
        for concern, module in CONCERN_OWNER_MODULES:
            owner = row_owner(resolve_layout_row(module, rows))
            for path in files:
                text = path.read_text(encoding="utf-8")
                rel = path.relative_to(ROOT).as_posix()
                claims = []
                for number, line in enumerate(text.splitlines(), 1):
                    cells = [c for c in line.strip().strip("|").split("|") if c.strip()]
                    if line.lstrip().startswith("|") and len(cells) >= 2 and concern.search(line):
                        agent = re.search(rf"(?<![\w-])({agent_re})(?![\w-])", cells[-1])
                        if agent:
                            claims.append((number, agent[1]))
                        claims += [(number, hit[1]) for hit in owns.finditer(line) if concern.search(hit[2])]
                for number, unit in prose_units(text):
                    for sentence in SENTENCE_SPLIT.split(unit):
                        if not concern.search(sentence) or NEGATED.search(sentence):
                            continue
                        if re.search(r"\bYou own\b", sentence) and path.parent.name == "agents":
                            claims.append((number, path.stem))
                        claims += [(number, hit[1]) for hit in re.finditer(
                            rf"(?i)\b(?:rout\w*|hand\w*|goes|go|sent)\b[^;]*? to `({agent_re})`", sentence)]
                        claims += [(number, hit[1]) for hit in owns.finditer(sentence) if concern.search(hit[2])]
                for number, agent in claims:
                    concern_seen += 1
                    with self.subTest(at=f"{rel}:{number}", concern=concern.pattern):
                        self.assertEqual(agent, owner, f"the layout files this under {module}, owner {owner}")
        self.assertTrue(concern_seen, "the concern scan found no claim: the forms are out of date")

    def test_skills_allow_the_helper_commands_they_name(self):
        # Fix 4.2 (B4): a `bash .claude/scripts/<x>.sh ...` command a SKILL.md
        # body tells the model to run has a matching `Bash(...)` pattern in its
        # allowed-tools (`*` matches any text). Restricted to commands that
        # contain `custom`: run over every skill first, the assertion also fired
        # on create-epics, cut and story-readiness, which this change did not
        # touch for this, where the body names the command without the
        # arguments the pattern's ` *` expects, or wraps it over a line break.
        # Whether such a mention is a gap depends on Claude Code's matching of
        # a bare command against `cmd *`, which this test cannot decide, so the
        # category is not mechanically crisp; the list is kept to the Custom
        # commands this change added (.claude/rules/skill-authoring.md:76-79),
        # and a new Custom helper command is covered by the token.
        seen = 0
        for skill in sorted((ROOT / ".claude/skills").glob("*/SKILL.md")):
            _, front, body = skill.read_text(encoding="utf-8").split("---", 2)
            allowed = re.search(r"^allowed-tools: *(.*)$", front, re.M)
            patterns = re.findall(r"Bash\(([^)]*)\)", allowed[1]) if allowed else []
            for command in sorted(set(re.findall(r"`(bash \.claude/scripts/[\w.-]+\.sh[^`]*)`", body))):
                if "custom" not in command:
                    continue
                seen += 1
                with self.subTest(skill=skill.parent.name, command=command):
                    self.assertTrue(any(re.fullmatch("".join(".*" if c == "*" else re.escape(c) for c in p),
                                                     command) for p in patterns),
                                    "no allowed-tools pattern lets the skill run this command")
        self.assertTrue(seen, "no skill names a Custom helper command: the scan is out of date")

    def test_setup_run_command_claims_agree(self):
        # Fix 4.3 (B5): when /setup-engine custom's config block leaves
        # `commands.run` unset, no text may say setup writes it, and the
        # run-and-observe procedure names the unset case. The two claim forms
        # are the ones found in the tree: "writes `commands.build`/`test`/`run`"
        # and "`commands.run`, which `/setup-engine custom` writes".
        setup = read(".claude/skills/setup-engine/references/custom.md")
        block = re.search(r"^commands:\n((?:[ \t]+.*\n)+)", setup, re.M)
        self.assertIsNotNone(block, "custom.md has no commands: block")
        if re.search(r"^\s+run:", block[1], re.M):
            self.skipTest("custom.md's config block sets commands.run")
        # Fix plan AM10 (Phase 4 critic F2): the third form is the list
        # "writes `commands.build`, `commands.test` and `commands.run`"; the
        # scanned set is every current-release markdown file, derived from git
        # (tracked and untracked, not ignored), with R8's history exceptions:
        # CHANGELOG.md and UPGRADING.md count only from their Unreleased
        # section, and docs/research/ (findings and plans quote the old claim)
        # is not release text.
        claims = (re.compile(r"\bwrites\s+`commands\.(?:\w+`?/`?)*run`"),
                  re.compile(r"\bwrites\s+(?:`commands\.\w+`,?\s+(?:and\s+)?)+`commands\.run`"),
                  re.compile(r"`commands\.run`[^.]*setup-engine[^.]*\bwrites\b"))
        listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard", "*.md"],
                                capture_output=True, text=True, check=True).stdout.splitlines()
        sections = {"CHANGELOG.md": r"^## \[Unreleased\].*?(?=^## \[)", "UPGRADING.md": r"^## Unreleased.*?(?=^## )"}
        scanned = [p for p in listed if not p.startswith("docs/research/") and (ROOT / p).is_file()]
        self.assertIn("README.md", scanned)
        for path in scanned:
            text = read(path)
            if path in sections:
                text = re.search(sections[path], text, re.M | re.S)[0]
            text = " ".join(text.split())
            for claim in claims:
                with self.subTest(path=path, claim=claim.pattern):
                    self.assertIsNone(claim.search(text))
        self.assertTrue("NOT VERIFIED — commands.run is not set"
                        in " ".join(read(".claude/docs/run-and-observe.md").split()),
                        "run-and-observe.md does not name the unset commands.run case")

    def test_code_review_lens_derives_rules_from_layout(self):
        # R5: no static path -> rule table; rules come from the layout, and an
        # unmapped path is reported, never reviewed from memory.
        text = read(".claude/skills/code-review/references/lens-engine.md")
        custom = re.search(r"^## Custom engine.*?(?=^## |\Z)", text, re.M | re.S)
        self.assertIsNotNone(custom)
        self.assertIn("custom-engine-layout.md", custom[0])
        self.assertIn("NOT ASSESSED — no layout row", custom[0])
        self.assertEqual([line for line in custom[0].splitlines()
                          if line.lstrip().startswith("|") and "`engine/" in line], [])

    def test_layout_precedence_resolves_overlapping_rows(self):
        # Fix plan AM7 (Phase 3 critic F3): the layout's rows overlap (a module
        # row, the tests row, the build-files row). The layout states the
        # precedence, resolve_layout_row follows it, and the readers that
        # resolve a path to its row cite it.
        with self.subTest(check="the layout states the precedence"):
            self.assertTrue(LAYOUT_PRECEDENCE in " ".join(read(LAYOUT).split()),
                            "the layout states no precedence for overlapping rows")
        rows = layout_rows()
        # Phase 3 critic F9: a module row written with `*` (the editor's Rust
        # crates) must still beat the tests and build-files rows, and a tie of
        # equal length between them must not be left to table order.
        cases = {  # path: (its module's path, owner, rule files the path takes)
            "engine/audio/tests/x.cpp": ("engine/audio/", "audio-engine-engineer", {"audio-code", "test-standards"}),
            "engine/audio/CMakeLists.txt": ("engine/audio/", "audio-engine-engineer", {"audio-code", "build-files"}),
            "crates/editor-ui/Cargo.toml": ("engine/editor/", "editor-architect", {"editor-code", "build-files"}),
            "crates/editor-ui/tests/x.rs": ("engine/editor/", "editor-architect", {"editor-code", "test-standards"}),
        }
        for path, (module, owner, rules) in cases.items():
            with self.subTest(path=path):
                row = resolve_layout_row(path, rows)
                self.assertIsNotNone(row)
                self.assertEqual(row_owner(row), owner)
                self.assertEqual(row_lead(row), row_lead(resolve_layout_row(module, rows)))
                ranks = layout_row_ranks(path, rows)
                top = max(rank for rank, _ in ranks)
                self.assertEqual({r["line"] for rank, r in ranks if rank == top}, {row["line"]},
                                 "two rows tie for the owner: table order decides")
                self.assertEqual({r for hit in layout_rows_for(path, rows) for r in row_rules(hit)}, rules)
        for reader in (".claude/skills/code-review/references/lens-engine.md",
                       ".claude/skills/code-review/SKILL.md",
                       ".claude/skills/perf-regression-triage/references/bisect-and-bug.md"):
            with self.subTest(reader=reader):
                self.assertIn("precedence rule", " ".join(read(reader).split()), "the reader does not cite the layout precedence rule")

    def test_roster_coordination_agrees_with_layout(self):
        # Fix plan AM8 (Phase 3 critic F8): the roster's Custom table says which
        # specialists each lead coordinates. Every owner the layout puts under
        # that lead must be in the cell. Two forms are found in the tree: a list
        # of role words ("coordinates the allocator, ... and build specialists"),
        # each word part of one agent's name, and a count ("coordinates its four
        # specialists"), which must be at least the layout's number (a lead may
        # coordinate specialists that own no row, such as the editor's). A new
        # form must be added here (.claude/rules/skill-authoring.md:76-79).
        rows = layout_rows()
        roster = section_text(read(".claude/docs/agent-roster.md"), "Custom Engine (build your own)")
        self.assertIsNotNone(roster, "the roster has no Custom Engine section")
        seen = 0
        for line in roster.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4 or cells[1] != "Lead":
                continue
            lead = AGENT_CELL.search(cells[0])[1]
            cell = re.search(r"coordinates (?:the |its )?(.*?) specialists", cells[3])
            if not cell:
                continue
            seen += 1
            led = {row_owner(row) for row in rows if row_lead(row) == lead} - {lead}
            with self.subTest(lead=lead):
                words = cell[1].split()
                if len(words) <= 2 and words[0].lower() in NUMBER_WORDS:
                    self.assertGreaterEqual(NUMBER_WORDS[words[0].lower()], len(led))
                    continue
                items = [i.strip().lower() for i in re.split(r",| and ", cell[1]) if i.strip()]
                missing = sorted(a for a in led if not any(
                    re.search(rf"(?:^|-){re.escape(i)}(?:-|$)", a) for i in items))
                self.assertEqual(missing, [], "the layout puts these under the lead; the roster omits them")
        self.assertTrue(seen, "no lead row says which specialists it coordinates: the forms are out of date")

    def test_architecture_context_names_absent_engine_reference_files(self):
        # Fix 4.8 (B3): a Custom setup writes only VERSION.md under
        # docs/engine-reference/custom/, so the other reference files these two
        # skills read are absent there; each skill's engine-reference step must
        # name an absent one, on any engine, never read past it in silence.
        steps = {
            ".claude/skills/create-architecture/references/0-load-context.md": "0a. Engine Context (Critical)",
            ".claude/skills/create-control-manifest/SKILL.md": "Engine reference",
        }
        for path, heading in steps.items():
            with self.subTest(skill=path):
                step = section_text(read(path), heading)
                self.assertIsNotNone(step, "the engine-reference step is not found")
                self.assertIn(ABSENT_REFERENCE_LINE, " ".join(step.split()))

    def assert_only_custom_blocks_added(self, path):
        """The file differs from the base release only by added blocks that
        name Custom (the plan's "Baselines": these files are untouched by the
        reviewed change, so base is their baseline)."""
        base = base_release_file(path)
        if base is None:
            self.skipTest(f"base release {BASE_RELEASE} is not in this clone")
        self.assertEqual(added_block_violations(base, read(path)), [])

    def test_start_names_custom_engine(self):
        # Fix 4.9 (B9): /start offers web unless another engine is named, and
        # never named the route for a project that builds its own engine.
        path = ".claude/skills/start/SKILL.md"
        self.assertIn("/setup-engine custom", read(path))
        self.assert_only_custom_blocks_added(path)

    def test_sprint_plan_scene_search_announces_custom(self):
        # Fix 4.9 (B8): on Custom there is no known scene file type; the scene
        # search does not run, and the plan says so (skill-authoring.md:47-52).
        path = ".claude/skills/sprint-plan/SKILL.md"
        step = next((u for u in re.split(r"\n(?=\d+\. )", read(path)) if u.startswith("3. **Check each one.**")), "")
        self.assertTrue(step, "step 3 of the goal prerequisites is not found")
        self.assertTrue(any("Custom" in s and "scene search did not run" in s
                            for s in re.split(r"(?<=\.)\s", " ".join(step.split()))),
                        "no sentence of step 3 says the scene search did not run on Custom")
        self.assert_only_custom_blocks_added(path)

    def test_story_skills_accept_module_spec_on_custom(self):
        # Fix 4.10 (R6; owner answer 5.1): on Custom the module spec stands in
        # for the GDD in the four story skills; a frame-pipeline story cannot
        # close without perf evidence or a NOT ASSESSED line. A branch is a
        # paragraph or list item that names both Custom and the spec folder.
        for path in STORY_SKILLS:
            with self.subTest(skill=path):
                units = [" ".join(u.split()) for p in re.split(r"\n\s*\n", read(path))
                         for u in re.split(r"\n(?=\s*(?:[-*]|\d+\.)\s)", p)]
                self.assertTrue(any("Custom" in u and MODULE_SPEC_DIR in u for u in units),
                                f"no branch names Custom and {MODULE_SPEC_DIR}")
                # Phase 4 critic F1: the stand-in is for a story (or epic) that
                # names a `Module:` path; a Custom game story keeps its GDD.
                if "create-epics" not in path:
                    for unit in (u for u in units if "Custom" in u and "stands in for the GDD" in u):
                        with self.subTest(branch=unit[:80]):
                            self.assertIn("Module", unit, "the stand-in is not limited to a story with a Module: path")
        stories = " ".join(read(".claude/skills/create-stories/SKILL.md").split())
        self.assertIn("Frame pipeline: yes | no", stories)
        done = " ".join(read(".claude/skills/story-done/SKILL.md").split())
        for line in ("NOT ASSESSED — no perf evidence", "NOT ASSESSED — frame-pipeline scope not stated"):
            with self.subTest(line=line):
                self.assertIn(line, done)

    def test_frame_pipeline_record_names_its_reader(self):
        # Fix plan AM11 (Phase 4 critic F3): after 4.10, /story-done reads
        # production/engine/ for a `Frame pipeline: yes` story's perf evidence,
        # so /team-frame-pipeline must name that reader, not say it has none.
        text = read(".claude/skills/team-frame-pipeline/SKILL.md")
        flat = " ".join(text.split())
        self.assertFalse("Nothing reads `production/engine/`" in flat, "the skill still says nothing reads its record")
        paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text)]
        self.assertTrue(any("production/engine/" in p and "/story-done" in p and "Frame pipeline: yes" in p
                            for p in paragraphs),
                        "no paragraph names /story-done as the reader of production/engine/")

    def test_story_skills_change_only_by_custom_blocks(self):
        # Fix 4.10, second test: the four skills are untouched by the reviewed
        # change, so they may differ from the base release only by added
        # blocks that name Custom.
        for path in STORY_SKILLS + (LAYERS_REFERENCE,):
            with self.subTest(skill=path):
                self.assert_only_custom_blocks_added(path)

    def test_layer_mapping_places_modules_on_custom(self):
        # Fix plan AM9: 4.10's block in 0-load-context.md says Phase 1 places
        # each engine module in the layer map; Phase 1's own file must say so
        # on Custom, not map only the systems of systems-index.md. A branch is
        # a paragraph or list item that names Custom and the spec folder.
        units = [" ".join(u.split()) for p in re.split(r"\n\s*\n", read(LAYERS_REFERENCE))
                 for u in re.split(r"\n(?=\s*(?:[-*]|\d+\.)\s)", p)]
        self.assertTrue(any("Custom" in u and MODULE_SPEC_DIR in u for u in units),
                        f"no branch names Custom and {MODULE_SPEC_DIR}")

    def test_code_review_unmapped_path_reaches_the_verdict(self):
        # Phase 3 critic F1: the `no layout row` line must make the result
        # not_assessed (the lens's trigger paragraph) and be one of the
        # verdict's NOT ASSESSED reasons, so a review with one unmapped path
        # cannot be APPROVED.
        token = "no layout row"
        lens = read(".claude/skills/code-review/references/lens-engine.md")
        trigger = next((p for p in re.split(r"\n\s*\n", lens)
                        if "makes the result `not_assessed`" in " ".join(p.split())), "")
        self.assertTrue(trigger, "the lens has no not_assessed trigger paragraph")
        self.assertIn(token, " ".join(trigger.split()))
        skill = read(".claude/skills/code-review/SKILL.md")
        reasons = re.search(r"^- \*\*NOT ASSESSED\*\*.*?(?=^- \*\*|^\S)", skill, re.M | re.S)
        self.assertIsNotNone(reasons, "the verdict list has no NOT ASSESSED entry")
        self.assertIn(token, " ".join(reasons[0].split()))

    def test_moved_engine_wide_text_is_not_cited_from_engine_code(self):
        # Fix plan AM6 (Phase 3 critic F2): fix 3.3 moved the public-API and
        # deprecation section, the OS/SDK-type-in-a-public-header bullet and the
        # `game/` bullet from engine-code.md to engine-api-code.md. No statement
        # (a list item, table row, heading or paragraph) may still cite
        # engine-code.md for one of them. The topic tokens are the moved text's
        # own; a new citation form must be added here
        # (.claude/rules/skill-authoring.md:76-79).
        moved_topics = ("deprecat", "Public API", "public header", "Boundary", "/api-review", "from `game/`")
        cites_engine_code = re.compile(r"(?<![\w-])engine-code\.md")
        unit_start = re.compile(r"\n(?=\s*(?:[-*]|\d+\.)\s|\||#)")
        for base in (".claude", "studio-tests"):
            for path in sorted((ROOT / base).rglob("*.md")):
                if path.name in ("engine-code.md", "engine-api-code.md"):
                    continue
                rel = path.relative_to(ROOT).as_posix()
                for paragraph in re.split(r"\n\s*\n", path.read_text(encoding="utf-8")):
                    for unit in unit_start.split(paragraph):
                        flat = " ".join(unit.split())
                        if not cites_engine_code.search(flat):
                            continue
                        # Phase 10 T6: topics match in any case ("Deprecated APIs").
                        for topic in moved_topics:
                            with self.subTest(file=rel, topic=topic, text=flat[:80]):
                                self.assertNotIn(topic.lower(), flat.lower(),
                                                 "cites engine-code.md for text now in engine-api-code.md")

    def test_engine_wide_rule_reaches_every_module(self):
        # R4: the engine-wide invariants (/api-review; engine never uses game/)
        # load for a file in every layout module, in both layouts.
        wide = []
        for rule in sorted((ROOT / ".claude/rules").glob("*.md")):
            text = rule.read_text(encoding="utf-8")
            if "/api-review" in text and re.search(r"\bnever\b[^.;]*`game/`", text):
                wide.append(rule.stem)
        self.assertTrue(wide, "no rule states the engine-wide invariants")
        for module in sorted(layout_modules(layout_rows())):
            for root in ("engine/", "crates/"):
                path = f"{root}{module}/src/example"
                with self.subTest(path=path):
                    self.assertTrue(any(matches(rule, path) for rule in wide), wide)

    def test_network_rule_scopes_authority_on_custom(self):
        # Fix 3.4 (owner answer 5.2 part 2): the Custom section scopes the
        # authority mandate by the ADR's replication model; the two mandate
        # bullets (:15 and :17 in this file) stay exactly as at the base release,
        # above the Custom section. Base numbers them differently (its
        # frontmatter is shorter), so they are found by their opening words.
        path = ".claude/rules/network-code.md"
        text = read(path)
        custom = re.search(r"^## On a Custom engine.*?(?=^## |\Z)", text, re.M | re.S)
        self.assertIsNotNone(custom)
        # Phase 3 critic F6: only the subsection fix 3.4 added counts; the rest
        # of the Custom section already said "ADR" before it.
        scoping = section_text(custom[0], "Replication model and authority")
        self.assertIsNotNone(scoping, "the Custom section has no Replication model and authority subsection")
        for token in ("ADR", "lockstep", "rollback"):
            with self.subTest(token=token):
                self.assertIn(token, scoping)
        base = base_release_file(path)
        if base is None:
            self.skipTest(f"base release {BASE_RELEASE} is not in this clone")
        above = text[:custom.start()].splitlines()
        for opening in NETWORK_MANDATE_OPENINGS:
            with self.subTest(bullet=opening):
                at_base = [line for line in base.splitlines() if line.startswith(opening)]
                self.assertEqual(len(at_base), 1)
                self.assertIn(at_base[0], above)

    def test_handoffs_name_an_owner_that_accepts(self):
        # R13, fix 7a: a handoff points to an agent whose file takes the
        # handed-over term, in its Core Responsibilities list. The handing-over
        # statement is a paragraph, list item or table row naming both the
        # phrase and the agent.
        unit_start = re.compile(r"\n(?=\s*(?:[-*]|\d+\.)\s|\|)")
        for source, phrase, agent, term in HANDOFFS:
            with self.subTest(source=source, agent=agent, term=term):
                units = [" ".join(u.split()) for p in re.split(r"\n\s*\n", read(source))
                         for u in unit_start.split(p)]
                self.assertTrue(any(phrase in u and agent in u for u in units),
                                f"no statement in {source} names both {phrase!r} and {agent}")
                found = duty_text(read(f".claude/agents/{agent}.md"))
                self.assertTrue(found, "the agent has no duty section "
                                f"({PRIMARY_DUTY_SECTION}, or {FALLBACK_DUTY_SECTIONS})")
                duties = " ".join(" ".join(s.split()) for s in found).lower()
                self.assertIn(term.lower(), duties,
                              "the agent's responsibilities do not take the handed-over term")

    def test_phase7_sections_have_spec_cases(self):
        # R13: each agent section in the R12 manifest has a case in that
        # agent's catalog `spec:` file whose title opens with the section's
        # heading ("### Case N: <heading> — ..."). Rule-file entries (fix 3.4)
        # have no agent spec and are covered by R12 alone.
        catalog = read("studio-tests/catalog.yaml").replace("\r", "")
        seen = 0
        for path, heading, item in TECHNICAL_SECTIONS:
            if not path.startswith(".claude/agents/"):
                continue
            seen += 1
            agent = Path(path).stem
            with self.subTest(agent=agent, heading=heading, item=item):
                entry = re.search(rf"^  - name: {re.escape(agent)}\n    spec: (\S+)", catalog, re.M)
                self.assertIsNotNone(entry, "the agent has no catalog spec: entry")
                self.assertTrue(re.search(rf"(?m)^### Case \d+: {re.escape(heading)} — ", read(entry[1])),
                                f"{entry[1]} has no case for this section")
        self.assertTrue(seen, "the manifest lists no agent section")

    def test_technical_sections_are_ledgered(self):
        # R12. That each quote supports its sentence is shown by review only
        # (fix plan Q9b step 4), not here.
        sources = {s["source_id"]: s for s in ledger("sources")}
        evidence = {e["evidence_id"]: e for e in ledger("evidence")}
        claims = ledger("claims")
        for path, heading, item in TECHNICAL_SECTIONS:
            with self.subTest(section=f"{path} # {heading}", item=item):
                body = section_text(read(path), heading)
                self.assertIsNotNone(body, "heading not found")
                records = [c for c in claims if c.get("file") == path and c.get("heading") == heading]
                self.assertTrue(records or "NOT SOURCEABLE" in body, "no claim record and no NOT SOURCEABLE")
        for claim in claims:
            if "file" in claim:
                with self.subTest(claim=claim["claim_id"]):
                    self.assertTrue(claim.get("evidence_ids"), "a section's claim cites no evidence")
            # A repository observation cites local files instead (local_evidence).
            for ev in claim.get("evidence_ids", []):
                with self.subTest(claim=claim["claim_id"], evidence=ev):
                    self.assertIn(ev, evidence, "evidence id does not resolve")
        for ev in evidence.values():
            with self.subTest(evidence=ev["evidence_id"]):
                self.assertIn(ev["source_id"], sources, "source id does not resolve")
                self.assertLessEqual(len(ev["quote"].split()), MAX_QUOTE_WORDS)
        for source in sources.values():
            with self.subTest(source=source["source_id"]):
                self.assertRegex(source.get("url", ""), r"^https?://")
                self.assertRegex(source.get("retrieved", ""), r"^\d{4}-\d{2}-\d{2}$")

    def test_test_rule_text_names_every_custom_test_root(self):
        # Fix 3.5: each Custom test root in the frontmatter is named in the
        # Custom naming text, by its root prefix and its folder.
        lines = read(".claude/rules/test-standards.md").splitlines()
        # AM21(b): benches/ globs sit under the Custom roots like the rest.
        roots = [g for g in rule_globs("test-standards") if g.startswith(CUSTOM_ROOTS)]
        self.assertTrue(roots)
        start = next(i for i, line in enumerate(lines) if "**Custom" in line)
        end = next((i for i in range(start, len(lines)) if lines[i].startswith("- ")), len(lines))
        spans = re.findall(r"`([^`]+)`", "\n".join(lines[start:end]))
        for glob in roots:
            prefix = glob.split("**")[0]
            folder = re.findall(r"([\w-]+)/", glob)[-1] + "/"
            with self.subTest(glob=glob):
                self.assertTrue(any(s.startswith(prefix) and s.endswith(folder) for s in spans),
                                f"no span names {prefix}...{folder}")

    def test_shared_agent_specs_cover_custom_text(self):
        # R11, fix 6.1: every shared agent with a Custom statement has a spec
        # case whose fixture sets `engine.name` to Custom and one that sets
        # another engine.
        agents = shared_agents_with_custom_text()
        self.assertTrue(agents, "no shared agent carries a Custom statement")
        godot = read(".claude/agents/godot-specialist.md")
        with self.subTest(negative_fixture="godot-specialist"):
            self.assertTrue("engine.name" in godot and CUSTOM_ENGINE in godot,
                            "the negative fixture no longer carries both tokens")
            self.assertNotIn("godot-specialist", agents)
        catalog = read("studio-tests/catalog.yaml").replace("\r", "")
        others = engine_names() - {CUSTOM_ENGINE}
        for agent in agents:
            with self.subTest(agent=agent):
                entry = re.search(rf"^  - name: {re.escape(agent)}\n    spec: (\S+)", catalog, re.M)
                self.assertIsNotNone(entry, "the agent has no catalog spec: entry")
                engines = case_fixture_engines(read(entry[1]))
                self.assertIn(CUSTOM_ENGINE, engines, f"{entry[1]} has no case whose fixture sets Custom")
                self.assertTrue(others & set(engines),
                                f"{entry[1]} has no case whose fixture sets another engine")

    def test_new_specs_have_five_cases_and_protocol_section(self):
        # Fix 6.2: the specs added since the base release keep the shape
        # studio-tests/CLAUDE.md asks of every spec.
        listing = subprocess.run(
            ["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", BASE_RELEASE, *SPEC_DIRS],
            capture_output=True, text=True)
        if listing.returncode != 0:
            self.skipTest(f"base release {BASE_RELEASE} is not in this clone")
        at_base = set(listing.stdout.split())
        added = sorted(p.relative_to(ROOT).as_posix() for d in SPEC_DIRS
                       for p in (ROOT / d).rglob("*.md")
                       if p.relative_to(ROOT).as_posix() not in at_base)
        self.assertTrue(added, "no spec was added since the base release")
        for spec in added:
            with self.subTest(spec=spec):
                text = read(spec)
                self.assertGreaterEqual(len(SPEC_CASE_HEADING.findall(text)), MIN_SPEC_CASES)
                self.assertRegex(text, PROTOCOL_SECTION)


if __name__ == "__main__":
    unittest.main()
