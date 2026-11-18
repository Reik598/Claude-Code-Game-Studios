"""Approved-hunk manifest for the shared agent and skill files (fix plan section 11, F12).

The framework's base release supports Godot, Unity, Unreal and Web. The Custom
engine change must leave those four as they were, so every agent and skill file
of the base release may differ from it only by hunks a person has approved.

Covered set (derived, never listed; skill-authoring obligation 5): every file
under .claude/agents/ and .claude/skills/ in BASE_RELEASE (`git ls-tree`), plus
every file on disk inside a skill directory that exists in base and is not in
base itself (a new references/ file a base skill can load).

Default deny. Each covered file must be exactly one of:
- equal to base, with no manifest entry;
- base plus its pinned hunks, rebuilt line for line;
- gone, under a `deleted` entry with a departure reason;
- an added file whose whole text is pinned under an `added` entry with a
  departure reason.
The work file is read with CRLF folded to LF and nothing else normalised. Pass
or fail never re-runs a diff: a hunk's base range is a fixed anchor in a fixed
commit, so the pinned hunks determine the approved file exactly. Any edit to a
covered file, inside an approved hunk or not, fails until the manifest changes,
and a manifest change is a reviewable diff of verbatim text plus its reason.

A hunk is {id, base: [i1, i2), old, new, reason}; its id is the first
ID_HEX_DIGITS of sha256(path, range, old, new). A reason has a class, a text
and a plan reference whose ids the fix plan must define:
- "custom-addition": a cheap label, held to the exact predicate of
  `addition_failures`, which `check` re-runs on every hunk that carries it.
  The predicate never approves anything by itself; it limits what a careless
  label can approve.
- "departure": any hunk. Its reason text is the review record.

Why approvals stay a list (obligation 5): "leaves Godot, Unity, Unreal and Web
behaviour unchanged" is not mechanically crisp. Five amendments (AM22-AM26)
each derived a text rule and each time a critic found the next hole. The duty
to extend the list is enforced: an unrecorded hunk fails.

Outside this guard: files outside base skill directories (new Custom agents and
skills; the catalog and Acceptance-2 tests cover those) and file modes.

Re-pinning (after a reviewed edit to a shared file):
1. python studio-tests/shared_hunks.py propose
   It rewrites the manifest for the tree on disk, keeps the reason of every
   hunk whose id is unchanged, writes `"reason": null` for each new hunk and
   prints, per new hunk, the predicate's verdict as triage.
2. Read each NEW hunk. Type its reason id into the manifest by hand:
   "custom-addition" only if the verdict allows it, else the id of a departure
   reason under "reasons" (add one: class, text, ref). There is no option that
   labels for you. A hunk that lists "supersedes" replaced a hunk pinned under
   a departure reason: its reason must cite a plan id the old reason did not
   (the amendment that decided the new text).
3. python studio-tests/shared_hunks.py check   -> "0 problem(s)"
"""
import argparse
from collections import Counter, namedtuple
from dataclasses import dataclass, field
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

BASE_RELEASE = "abc0de7"
SHARED_DIRS = (".claude/agents/", ".claude/skills/")
SKILLS_DIR = ".claude/skills/"
SKILL_DIR_DEPTH = 3     # .claude / skills / <name>
PLAN = "docs/research/aaa-engine-support-2026/fix-plan.md"
MANIFEST_NAME = "shared-file-hunks.json"
MANIFEST_VERSION = 1
ID_HEX_DIGITS = 16
CLASS_ADDITION = "custom-addition"
CLASS_DEPARTURE = "departure"
REASON_CLASSES = (CLASS_ADDITION, CLASS_DEPARTURE)
HUNK_KEYS = ("id", "base", "old", "new", "reason", "supersedes")
CUSTOM_WORD = "Custom"

# Text shapes the predicate reads. A token is a word, a whitespace run or one
# other character, so `Customize` and a Cyrillic lookalike are not `Custom`.
TOKEN = re.compile(r"\w+|\s+|[^\w\s]")
WORD = re.compile(r"\w")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
HEADING = re.compile(r"^ {0,3}(#{1,6})\s")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
TABLE_ROW = re.compile(r"^\s*\|")
THEMATIC_BREAK = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
FRONTMATTER_MARK = "---"
LEAD_IN_ENDINGS = (":", ":**", ":*", ":_")
DEEPEST_HEADING = 6
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=\S)")
DUPLICATE_MIN_WORDS = 4     # shorter sentences ("See below.") repeat by chance

# Another engine's name, in any letter case, as a whole word (so `WebFetch` and
# `community` do not count, `Unity-based` and `Godot/Unity` do).
ENGINE_WORD = re.compile(r"(?<!\w)(?:godot|unity|unreal|web|ue4|ue5)(?!\w)", re.I)
# Phrases that address another engine or every engine without naming one. A
# hunk that adds one needs a departure reason, however often it says Custom.
# Quantifiers and "engine" match in any letter case; `Custom` only as written,
# so the path `docs/engine-reference/custom/` is not the engine's name. Between
# quantifier and "engine" only the listed words may stand ("any other engine",
# "all four engines"), and a compound such as `engine-internal` does not count.
ENGINE_QUANTIFIER = r"(?i:any|every|each|all|another|other)"
ENGINE_QUALIFIER = r"(?i:other|supported|game|four|five|non-Custom)"
SCOPE_ESCAPES = (
    ("any/every/other engine", rf"\b{ENGINE_QUANTIFIER}\s+(?:{ENGINE_QUALIFIER}\s+)?(?i:engines?)\b(?![-\w])"),
    ("non-Custom", r"\b(?i:non)-?Custom\b"),
    ("not Custom", r"\b(?i:not)\s+`?Custom\b"),
    ("other than Custom", r"\b(?i:other\s+than)\s+`?Custom\b"),
    ("unless ... Custom", r"\b(?i:unless)\b[^.!?]{0,120}?\bCustom\b"),
    ("outside Custom", r"\b(?i:outside)\s+(?i:of\s+)?`?Custom\b"),
    ("regardless of", r"\b(?i:regardless\s+of)\b"),
    ("whatever engine", r"\b(?i:whatever)\s+(?i:the\s+)?(?i:engine)\b"),
    ("every/all/any project", r"\b(?i:every|all|any)\s+(?:(?i:game|other)\s+)?(?i:projects?)\b"),
)
SCOPE_ESCAPE_PATTERNS = tuple((name, re.compile(pattern)) for name, pattern in SCOPE_ESCAPES)
# The one sentence that may name the other engines under the cheap label: the
# gate that closes a Custom section to them. Exact text, so any other wording
# ("on any other engine, follow it too") is a scope escape again.
SECTION_GATE = "on any other engine, ignore this section."

# Why a hunk cannot carry the custom-addition label.
CAUSE_FRONTMATTER = "touches frontmatter"
CAUSE_BASE_LINE = "changes a base line (only whole inserted lines are additions)"
CAUSE_BASE_CHANGED = "removes or changes a base token"
CAUSE_NO_CUSTOM = "inserts a token stretch without the whole word Custom"
CAUSE_BASE_HEADING = "changes a base heading"
CAUSE_HEADING_SCOPES_BASE = "adds a heading whose section holds a base line"
CAUSE_ENGINE_WORD = "adds a Godot/Unity/Unreal/Web/UE4/UE5 word"
CAUSE_SCOPE_ESCAPE = "adds a scope-escape phrase"
CAUSE_BLOCK_NOT_CUSTOM = "inserts a block that neither names Custom nor sits under an inserted Custom heading"
CAUSE_BASE_FENCE = "inserts into a base code fence"
CAUSE_GLUED = "glues an insertion to a base unit"
CAUSE_INDENTS_BASE = "indents base text under an insertion"
CAUSE_LEAD_IN = "ends an insertion on a ':' lead-in"

# Messages of `check`. The tests and controls match on these.
MANIFEST_SCOPE = "(manifest)"
DIFFERS_FROM_APPROVED = "differs from the approved text"
NO_APPROVED_HUNKS = "changed from base; no approved hunks"
STALE_ENTRY = "stale manifest entry: the file equals base"
STALE_ADDED = "stale `added` entry: no such new file"
NOT_IN_BASE = "manifest entry for a file that is not in the base release"
DELETED_UNAPPROVED = "base file deleted or renamed; no `deleted` entry with a departure reason"
ADDED_UNAPPROVED = "new file inside a base skill directory; no `added` entry"
NEEDS_DEPARTURE = "needs a departure reason"
NOT_REVIEWED = "not reviewed"
ID_MISMATCH = "id does not match its content (edited by hand?)"
SAME_PLAN_ID = "re-pins text that was under a departure reason and cites no plan id beyond that reason's"
NOT_UTF8 = "is not valid UTF-8"
NO_PLAN_ID = "(no plan id)"

# How a plan id is written in a reason's reference, and the form in which the
# fix plan defines it. A mention elsewhere in the plan does not resolve an id.
PLAN_ID = re.compile(r"\bAM\d+|\bfix \d+\.\d+|\bO\d+\b|\bQ\d+[a-z]?\b|\bR\d+\b|\bsection \d+\b")
PLAN_DEFINITIONS = (
    (re.compile(r"AM\d+$"), r"(?m)(?:^\| {0}|amendment {0}) "),
    (re.compile(r"O\d+$"), r"(?m)^\| {0} \|"),
    (re.compile(r"R\d+$"), r"(?m)^\| {0} \|"),
    (re.compile(r"Q\d+[a-z]?$"), r"(?m)^### {0}\."),
    (re.compile(r"fix (\d+\.\d+)$"), r"(?m)^\| {0}[ |]"),
    (re.compile(r"section (\d+)$"), r"(?m)^## {0}\. "),
)
DIFF_CONTEXT = 2
PREVIEW_LINES = 40
ENCODING = "utf-8"

Problem = namedtuple("Problem", "path message")


@dataclass
class TreeState:
    """What `check` and `propose` read, held in memory so tests can build one.

    base: {path: text} of every covered base-release file.
    work: {path: text} of those that exist on disk (a missing key is a deleted file).
    added: {path: text} of files on disk inside a base skill directory, not in base.
    plan_text: the fix plan, where reason references must resolve.
    """
    base: dict
    work: dict
    added: dict = field(default_factory=dict)
    plan_text: str = ""


# ---------------------------------------------------------------- text and git

def fold_crlf(data):
    """Bytes as text with CRLF folded to LF; nothing else is normalised.

    Undecodable bytes survive as surrogates, so such a file never equals a
    text that is valid UTF-8 and `check` can name it."""
    return data.decode(ENCODING, errors="surrogateescape").replace("\r\n", "\n")


def split_lines(text):
    """Lines of a text; a final newline shows as a trailing "" so EOF changes count."""
    return text.split("\n")


def valid_utf8(text):
    try:
        text.encode(ENCODING)
    except UnicodeEncodeError:
        return False
    return True


def git(repo, *args, data=None):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, input=data, check=True).stdout


def base_present(repo, base=BASE_RELEASE):
    """True when `repo` is a git repository that holds the base commit."""
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{base}^{{commit}}"],
                          capture_output=True).returncode == 0


def base_texts(repo, base=BASE_RELEASE):
    """{path: text} of every agent and skill file in the base commit."""
    listing = git(repo, "ls-tree", "-r", "--name-only", "-z", base, "--", *SHARED_DIRS).decode(ENCODING)
    paths = sorted(p for p in listing.split("\0") if p)
    out = git(repo, "cat-file", "--batch", data="".join(f"{base}:{p}\n" for p in paths).encode(ENCODING))
    texts, pos = {}, 0
    for path in paths:
        header_end = out.index(b"\n", pos)
        size = int(out[pos:header_end].split()[2])
        texts[path] = fold_crlf(out[header_end + 1:header_end + 1 + size])
        pos = header_end + 1 + size + 1
    return texts


def disk_files(root):
    """{path: text} of every file under the shared directories, by its listed name.

    Names come from directory listings, never from opening a base path: on a
    case-insensitive file system `SKILL.md` opens a file renamed `skill.md`,
    and the rename must show as one file gone and one added."""
    found = {}
    for shared in SHARED_DIRS:
        folder, parts = Path(root), shared.strip("/").split("/")
        if any(part not in listed_names(folder / Path(*parts[:n])) for n, part in enumerate(parts)):
            continue
        for current, _, names in os.walk(folder / Path(*parts)):
            for name in names:
                file = Path(current) / name
                found[file.relative_to(root).as_posix()] = fold_crlf(file.read_bytes())
    return found


def listed_names(folder):
    return set(os.listdir(folder)) if folder.is_dir() else set()


def in_base_skill_dir(path, base_paths):
    """True for a path inside a skill directory that holds a base-release file."""
    parts = path.split("/")
    if not path.startswith(SKILLS_DIR) or len(parts) <= SKILL_DIR_DEPTH:
        return False
    prefix = "/".join(parts[:SKILL_DIR_DEPTH]) + "/"
    return any(p.startswith(prefix) for p in base_paths)


def load_state(root, base_repo=None, base=BASE_RELEASE):
    """The TreeState of the tree at `root`, with base read from `base_repo` (default: root)."""
    texts = base_texts(base_repo or root, base)
    disk = disk_files(root)
    plan = Path(root) / PLAN
    return TreeState(
        base=texts,
        work={p: disk[p] for p in texts if p in disk},
        added={p: t for p, t in disk.items() if p not in texts and in_base_skill_dir(p, texts)},
        plan_text=plan.read_text(encoding=ENCODING) if plan.is_file() else "")


# ---------------------------------------------------------------- hunks

def hunk_id(path, i1, i2, old, new):
    """The id that ties a hunk to its file, base range and exact text."""
    blob = json.dumps([path, i1, i2, old, new], ensure_ascii=False).encode(ENCODING, errors="surrogateescape")
    return hashlib.sha256(blob).hexdigest()[:ID_HEX_DIGITS]


def make_hunk(path, i1, i2, old, new):
    return {"id": hunk_id(path, i1, i2, old, new), "base": [i1, i2], "old": old, "new": new, "reason": None}


def diff_hunks(path, base_lines, work_lines):
    """The changed runs of a line diff, as unreviewed hunks. Used by `propose` only."""
    matcher = difflib.SequenceMatcher(a=base_lines, b=work_lines, autojunk=False)
    return [make_hunk(path, i1, i2, base_lines[i1:i2], work_lines[j1:j2])
            for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != "equal"]


def added_hunk(path, text):
    """An added file's whole text, as one hunk against an empty base."""
    return make_hunk(path, 0, 0, [], split_lines(text))


def rebuild(base_lines, hunks):
    """(lines, origin) of base with the hunks applied.

    origin[k] is None for a base line, else the index of the hunk that wrote
    line k. Raises ValueError when a hunk does not fit base."""
    out, origin, pos = [], [], 0
    for n, hunk in enumerate(hunks):
        i1, i2 = hunk["base"]
        if not pos <= i1 <= i2 <= len(base_lines):
            raise ValueError(f"hunk {hunk.get('id')}: base range {hunk['base']} is out of order or out of bounds")
        if base_lines[i1:i2] != hunk["old"]:
            raise ValueError(f"hunk {hunk.get('id')}: its old lines are not base lines {i1 + 1}-{i2}")
        out += base_lines[pos:i1] + hunk["new"]
        origin += [None] * (i1 - pos) + [n] * len(hunk["new"])
        pos = i2
    out += base_lines[pos:]
    origin += [None] * (len(base_lines) - pos)
    return out, origin


# ---------------------------------------------------------------- the custom-addition predicate

def frontmatter_end(lines):
    """Index of the closing '---' line, or -1 when the file has no frontmatter."""
    if not lines or lines[0] != FRONTMATTER_MARK:
        return -1
    return next((k for k in range(1, len(lines)) if lines[k] == FRONTMATTER_MARK), len(lines))


def fence_map(lines):
    """(indexes of the lines that are or sit inside a code fence,
    indexes k where a line inserted before line k would land inside one).

    A fence closes only on a line of the same character, at least as long,
    with nothing after it, so a ```` block may quote ``` lines."""
    inside, open_before, opener = set(), set(), None
    for k, line in enumerate(lines):
        match = FENCE.match(line)
        if opener is None:
            if match:
                opener = match[1]
                inside.add(k)
            continue
        inside.add(k)
        open_before.add(k)
        if match and match[1][0] == opener[0] and len(match[1]) >= len(opener) and not match[2].strip():
            opener = None
    return inside, open_before


def fenced(lines):
    """Indexes of the lines that are, or sit inside, a code fence."""
    return fence_map(lines)[0]


def heading_level(lines, k, fence_set):
    match = None if k in fence_set else HEADING.match(lines[k])
    return len(match[1]) if match else None


def indent(line):
    return len(line) - len(line.lstrip(" \t"))


def starts_unit(line):
    """True when a line opens its own heading, list item, table row or fence."""
    return bool(HEADING.match(line) or LIST_ITEM.match(line) or TABLE_ROW.match(line) or FENCE.match(line))


def names_custom(text):
    """True when the text holds the whole word Custom outside an HTML comment
    (a comment may be hidden from the model that reads the file)."""
    return CUSTOM_WORD in TOKEN.findall(HTML_COMMENT.sub("", text))


def scope_escapes(text):
    """Names of the scope-escape phrases in a text, one per occurrence.

    The exact section gate sentence is taken out first, across line wraps."""
    flat = " ".join(text.split()).replace(SECTION_GATE, "")
    return [name for name, pattern in SCOPE_ESCAPE_PATTERNS for _ in pattern.finditer(flat)]


def token_stretches(old, new):
    """(base tokens all kept in order, inserted token stretches), whitespace included."""
    a, b = TOKEN.findall(old), TOKEN.findall(new)
    kept, stretches, current = True, [], None
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag in ("delete", "replace"):
            kept = False
        if tag in ("insert", "replace"):
            current = (current or []) + b[j1:j2]
        elif current is not None and all(token.isspace() for token in a[i1:i2]):
            current += b[j1:j2]     # base whitespace between two inserted runs: one insertion
        elif current is not None:
            stretches.append(current)
            current = None
    if current is not None:
        stretches.append(current)
    return kept, stretches


def uncovered_blocks(lines, mine, fence_set):
    """Blank-line blocks among the inserted lines `mine` that hold a word, do
    not name Custom and are not inside the section of an inserted Custom heading."""
    blocks, current = [], []
    for k in mine:
        if not lines[k].strip() and k not in fence_set:
            blocks.append(current)
            current = []
        else:
            current.append(k)
    blocks.append(current)
    sections = []
    for k in mine:
        level = heading_level(lines, k, fence_set)
        if level and names_custom(lines[k]):
            end = next((m for m in range(k + 1, len(lines))
                        if (heading_level(lines, m, fence_set) or DEEPEST_HEADING + 1) <= level), len(lines))
            sections.append((k, end))
    bad = []
    for block in filter(None, blocks):
        text = "\n".join(lines[k] for k in block)
        if WORD.search(text) and not names_custom(text) and not any(a < block[0] < b for a, b in sections):
            bad.append(block)
    return bad


def insertion_structure_failures(lines, origin, mine, fence_set):
    """Structural causes for a pure insertion whose lines sit at indexes `mine`."""
    why = []
    content = [k for k in mine if lines[k].strip()]
    if not content:
        return why
    first, last = mine[0], mine[-1]
    before = lines[first - 1] if first else ""
    after = lines[last + 1] if last + 1 < len(lines) else ""
    boundary_before = not before.strip() or HEADING.match(before) or FENCE.match(before)
    if lines[first].strip() and not boundary_before and not starts_unit(lines[first]):
        why.append(CAUSE_GLUED)
    if lines[last].strip() and after.strip() and not starts_unit(after) and last not in fence_set:
        why.append(CAUSE_GLUED)
    following = next((k for k in range(last + 1, len(lines))
                      if lines[k].strip() and not THEMATIC_BREAK.match(lines[k])), None)
    if following is not None and origin[following] is None and not HEADING.match(lines[following]) \
            and indent(lines[following]) > min(indent(lines[k]) for k in content):
        why.append(CAUSE_INDENTS_BASE)
    if content[-1] not in fence_set and lines[content[-1]].rstrip().endswith(LEAD_IN_ENDINGS):
        why.append(CAUSE_LEAD_IN)
    return why


def hunk_failures(base_lines, base_fences, hunk, lines, origin, n, fence_set):
    """Why hunk n cannot carry the custom-addition label ([] when it can)."""
    why = []
    i1, i2 = hunk["base"]
    base_fence, base_open = base_fences
    mine = [k for k in range(len(lines)) if origin[k] == n]
    closing = frontmatter_end(base_lines)
    if closing >= 0 and i1 <= closing:
        why.append(CAUSE_FRONTMATTER)
    # Each line keeps its newline, so a removed or added blank line is a token change.
    old_text, new_text = ("".join(f"{line}\n" for line in side) for side in (hunk["old"], hunk["new"]))
    kept, stretches = token_stretches(old_text, new_text)
    if not kept:
        why.append(CAUSE_BASE_CHANGED)
    if any(not names_custom("".join(stretch)) for stretch in stretches):
        why.append(CAUSE_NO_CUSTOM)
    if len(ENGINE_WORD.findall(new_text)) > len(ENGINE_WORD.findall(old_text)):
        why.append(CAUSE_ENGINE_WORD)
    if Counter(scope_escapes(new_text)) - Counter(scope_escapes(old_text)):
        why.append(CAUSE_SCOPE_ESCAPE)
    if any(heading_level(base_lines, k, base_fence) for k in range(i1, i2)):
        why.append(CAUSE_BASE_HEADING)
    for k in mine:
        level = heading_level(lines, k, fence_set)
        if level is None:
            continue
        for m in range(k + 1, len(lines)):
            if (heading_level(lines, m, fence_set) or DEEPEST_HEADING + 1) <= level:
                break
            if origin[m] is None and lines[m].strip() and not THEMATIC_BREAK.match(lines[m]):
                why.append(CAUSE_HEADING_SCOPES_BASE)
                break
    if i1 != i2:
        why.append(CAUSE_BASE_LINE)
        stripped = {line.strip(): indent(line) for line in hunk["old"] if line.strip()}
        if any(indent(line) > stripped.get(line.strip(), indent(line)) for line in hunk["new"]):
            why.append(CAUSE_INDENTS_BASE)
    else:
        if uncovered_blocks(lines, mine, fence_set):
            why.append(CAUSE_BLOCK_NOT_CUSTOM)
        if i1 in base_open:
            why.append(CAUSE_BASE_FENCE)
        why += insertion_structure_failures(lines, origin, mine, fence_set)
    return sorted(set(why))


def addition_failures(base_lines, hunks):
    """Per hunk, why it cannot carry the custom-addition label ([] when it can).

    Raises ValueError when the hunks do not fit base."""
    lines, origin = rebuild(base_lines, hunks)
    base_fences, fence_set = fence_map(base_lines), fenced(lines)
    return [hunk_failures(base_lines, base_fences, hunk, lines, origin, n, fence_set) for n, hunk in enumerate(hunks)]


# ---------------------------------------------------------------- reasons and the plan

def plan_ids(reference):
    return PLAN_ID.findall(reference or "")


def plan_defines(plan_id, plan_text):
    for shape, definition in PLAN_DEFINITIONS:
        match = shape.match(plan_id)
        if match:
            key = match[1] if match.groups() else plan_id
            return bool(re.search(definition.format(re.escape(key)), plan_text))
    return False


def unresolved_plan_ids(reference, plan_text):
    """The ids of a reason reference that the plan does not define; [NO_PLAN_ID] when it cites none."""
    ids = plan_ids(reference)
    return [i for i in ids if not plan_defines(i, plan_text)] if ids else [NO_PLAN_ID]


def reason_problems(reasons, plan_text):
    problems = []
    for rid, reason in reasons.items():
        if reason.get("class") not in REASON_CLASSES:
            problems.append(Problem(MANIFEST_SCOPE, f"reason {rid}: class {reason.get('class')!r} is not one of "
                                                    f"{', '.join(REASON_CLASSES)}"))
        if not (reason.get("text") or "").strip():
            problems.append(Problem(MANIFEST_SCOPE, f"reason {rid}: empty text"))
        missing = unresolved_plan_ids(reason.get("ref"), plan_text)
        if missing:
            problems.append(Problem(MANIFEST_SCOPE, f"reason {rid}: plan reference {reason.get('ref')!r} does not "
                                                    f"resolve in {PLAN}: {', '.join(missing)}"))
    return problems


# ---------------------------------------------------------------- manifest

def empty_manifest(base=BASE_RELEASE):
    return {"version": MANIFEST_VERSION, "base": base, "reasons": {}, "files": {}, "added": {}}


def load_manifest(path):
    return json.loads(Path(path).read_text(encoding=ENCODING))


def save_manifest(path, manifest):
    """Write the manifest: one line per text line, so a re-pin is a readable diff."""
    Path(path).write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding=ENCODING,
                          newline="\n")


def where(hunk):
    i1, i2 = hunk["base"]
    return f"insert after base line {i1}" if i1 == i2 else f"base lines {i1 + 1}-{i2}"


def show_hunk(hunk):
    out = [f"    - {line}" for line in hunk["old"]] + [f"    + {line}" for line in hunk["new"]]
    more = [f"    ... {len(out) - PREVIEW_LINES} more line(s)"] if len(out) > PREVIEW_LINES else []
    return "\n".join(out[:PREVIEW_LINES] + more)


def preview(a_lines, b_lines, a_name, b_name):
    diff = difflib.unified_diff(a_lines, b_lines, a_name, b_name, n=DIFF_CONTEXT, lineterm="")
    return "\n".join("    " + line for line in list(diff)[:PREVIEW_LINES])


def hunk_record_problems(path, hunk, reasons, causes):
    """Problems of one pinned hunk's record: keys, id, reason, label, supersedes.

    causes: its predicate failures, or None for a hunk that only a departure
    reason can approve (an added file's text)."""
    tag = f"hunk {hunk.get('id')} ({where(hunk)})"
    problems = []
    unknown = sorted(set(hunk) - set(HUNK_KEYS))
    if unknown:
        problems.append(Problem(path, f"{tag}: unknown keys {unknown}"))
    if hunk.get("id") != hunk_id(path, hunk["base"][0], hunk["base"][1], hunk["old"], hunk["new"]):
        problems.append(Problem(path, f"{tag}: {ID_MISMATCH}"))
    reason = reasons.get(hunk.get("reason")) if isinstance(hunk.get("reason"), str) else None
    if reason is None:
        return problems + [Problem(path, f"{tag}: {NOT_REVIEWED} (reason {hunk.get('reason')!r})\n{show_hunk(hunk)}")]
    if reason.get("class") == CLASS_ADDITION:
        if causes is None:
            problems.append(Problem(path, f"{tag}: labelled {CLASS_ADDITION} but a whole added file "
                                          f"{NEEDS_DEPARTURE}"))
        elif causes:
            problems.append(Problem(path, f"{tag}: labelled {CLASS_ADDITION} but {', '.join(causes)}; it "
                                          f"{NEEDS_DEPARTURE}\n{show_hunk(hunk)}"))
    for old in hunk.get("supersedes", []):
        if old not in reasons:
            problems.append(Problem(path, f"{tag}: supersedes reason {old!r}, which the manifest no longer holds"))
        elif not set(plan_ids(reason.get("ref"))) - set(plan_ids(reasons[old].get("ref"))):
            problems.append(Problem(path, f"{tag}: {SAME_PLAN_ID} ({old!r}: {reasons[old].get('ref')!r}); cite "
                                          "the amendment that decided the new text"))
    return problems


def check_file(path, base_text, work_text, entry, reasons):
    """Problems of one changed base file against its pinned hunks."""
    base_lines, hunks = split_lines(base_text), entry.get("hunks", [])
    try:
        approved, _ = rebuild(base_lines, hunks)
        failures = addition_failures(base_lines, hunks)
    except (ValueError, KeyError, TypeError) as error:
        return [Problem(path, f"malformed hunks: {error}")]
    problems = [p for hunk, causes in zip(hunks, failures) for p in hunk_record_problems(path, hunk, reasons, causes)]
    if approved != split_lines(work_text):
        problems.append(Problem(path, f"{DIFFERS_FROM_APPROVED}\n"
                                      + preview(approved, split_lines(work_text), "approved", "on disk")))
    return problems


def check_added(path, text, hunk, reasons):
    """Problems of one added file against its pinned whole text."""
    if not isinstance(hunk, dict) or hunk.get("base") != [0, 0] or hunk.get("old") != [] \
            or not isinstance(hunk.get("new"), list):
        return [Problem(path, "malformed `added` entry: expected one hunk against an empty base")]
    problems = hunk_record_problems(path, hunk, reasons, None)
    if hunk["new"] != split_lines(text):
        problems.append(Problem(path, f"{DIFFERS_FROM_APPROVED}\n"
                                      + preview(hunk["new"], split_lines(text), "approved", "on disk")))
    return problems


def is_departure(reasons, rid):
    return isinstance(rid, str) and reasons.get(rid, {}).get("class") == CLASS_DEPARTURE


def check(tree, manifest):
    """Every problem of the tree against the manifest. An empty list means approved."""
    reasons = manifest.get("reasons", {})
    files, added = manifest.get("files", {}), manifest.get("added", {})
    problems = []
    if manifest.get("version") != MANIFEST_VERSION:
        problems.append(Problem(MANIFEST_SCOPE, f"version {manifest.get('version')!r} is not {MANIFEST_VERSION}"))
    if manifest.get("base") != BASE_RELEASE:
        problems.append(Problem(MANIFEST_SCOPE, f"base {manifest.get('base')!r} is not {BASE_RELEASE}"))
    problems += reason_problems(reasons, tree.plan_text)
    for path in sorted(set(files) - set(tree.base)):
        problems.append(Problem(path, NOT_IN_BASE))
    for path, base_text in sorted(tree.base.items()):
        entry, work_text = files.get(path), tree.work.get(path)
        if work_text == base_text:
            if entry is not None:
                problems.append(Problem(path, STALE_ENTRY))
        elif work_text is None:
            # A deletion keeps no base text: only a departure reason can approve it.
            if not (entry and entry.get("deleted") is True and is_departure(reasons, entry.get("reason"))):
                problems.append(Problem(path, DELETED_UNAPPROVED))
        elif not valid_utf8(work_text):
            problems.append(Problem(path, NOT_UTF8))
        elif entry is None or "hunks" not in entry:
            problems.append(Problem(path, f"{NO_APPROVED_HUNKS}\n" + preview(
                split_lines(base_text), split_lines(work_text), "base", "on disk")))
        else:
            problems += check_file(path, base_text, work_text, entry, reasons)
    for path in sorted(set(tree.added) - set(added)):
        problems.append(Problem(path, ADDED_UNAPPROVED))
    for path in sorted(set(added) - set(tree.added)):
        problems.append(Problem(path, STALE_ADDED))
    for path in sorted(set(added) & set(tree.added)):
        problems += check_added(path, tree.added[path], added[path], reasons)
    return problems


# ---------------------------------------------------------------- propose

def touches(a, b):
    """True when two hunks' base ranges overlap or meet."""
    return a["base"][0] <= b["base"][1] and b["base"][0] <= a["base"][1]


def carry_review(hunk, previous, reasons):
    """Give a re-diffed hunk its earlier review, or mark what it replaces.

    previous: the hunks pinned for the same file. Returns True for a new hunk."""
    same = next((p for p in previous if p.get("id") == hunk["id"]), None)
    if same is not None:
        hunk.update({key: same[key] for key in ("reason", "supersedes") if key in same})
        return False
    replaced = sorted({p["reason"] for p in previous if touches(p, hunk) and is_departure(reasons, p.get("reason"))})
    if replaced:
        hunk["supersedes"] = replaced
    return True


def propose(tree, manifest):
    """(manifest that pins the tree as it is, [(path, new hunk)]).

    A hunk whose id is unchanged keeps its reason. Every other hunk is new and
    gets reason None: `check` fails until a person types one."""
    reasons = manifest.get("reasons", {})
    out = {key: value for key, value in manifest.items() if key not in ("files", "added")}
    out.setdefault("version", MANIFEST_VERSION)
    out.setdefault("base", BASE_RELEASE)
    out.setdefault("reasons", {})
    out["files"], out["added"], new = {}, {}, []
    for path, base_text in sorted(tree.base.items()):
        work_text, entry = tree.work.get(path), manifest.get("files", {}).get(path, {})
        if work_text == base_text:
            continue
        if work_text is None:
            out["files"][path] = {"deleted": True, "reason": entry.get("reason") if entry.get("deleted") else None}
            continue
        hunks = diff_hunks(path, split_lines(base_text), split_lines(work_text))
        previous = [h for h in entry.get("hunks", []) if isinstance(h, dict) and len(h.get("base", [])) == 2]
        new += [(path, hunk) for hunk in hunks if carry_review(hunk, previous, reasons)]
        out["files"][path] = {"hunks": hunks}
    for path, text in sorted(tree.added.items()):
        hunk, earlier = added_hunk(path, text), manifest.get("added", {}).get(path)
        if carry_review(hunk, [earlier] if isinstance(earlier, dict) else [], reasons):
            new.append((path, hunk))
        out["added"][path] = hunk
    return out, new


def departure_sentences(manifest):
    """{sentence: path} of the sentences pinned under a departure reason."""
    reasons, found = manifest.get("reasons", {}), {}
    for path, entry in manifest.get("files", {}).items():
        for hunk in entry.get("hunks", []):
            if is_departure(reasons, hunk.get("reason")):
                for sentence in sentences(hunk["new"]):
                    found.setdefault(sentence, path)
    return found


def sentences(lines):
    text = " ".join(line.strip() for line in lines if line.strip())
    return [s for s in SENTENCE_BREAK.split(text) if len(s.split()) >= DUPLICATE_MIN_WORDS]


def triage(tree, proposed, previous, new):
    """One printable entry per new hunk: the predicate's verdict and what it repeats."""
    pinned_departures = departure_sentences(previous)
    out = []
    for path, hunk in new:
        if path in tree.added:
            verdict = f"an added file: {NEEDS_DEPARTURE}"
        else:
            hunks = proposed["files"][path]["hunks"]
            causes = addition_failures(split_lines(tree.base[path]), hunks)[hunks.index(hunk)]
            verdict = f"{CLASS_ADDITION} allowed" if not causes else f"{NEEDS_DEPARTURE}: {', '.join(causes)}"
        notes = [f"    supersedes a hunk under {old!r}: cite a plan id that reason does not"
                 for old in hunk.get("supersedes", [])]
        notes += [f"    repeats a sentence pinned under a departure reason in {pinned_departures[s]}: {s[:100]!r}"
                  for s in sentences(hunk["new"]) if s in pinned_departures and not hunk.get("supersedes")]
        out.append("\n".join([f"NEW {path} hunk {hunk['id']} ({where(hunk)}) [{verdict}]"] + notes + [show_hunk(hunk)]))
    return out


# ---------------------------------------------------------------- command line

def argument_parser():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     epilog="propose never writes a reason: a person types each one.")
    parser.add_argument("command", choices=("check", "propose"))
    parser.add_argument("--root", default=str(here.parent), help="the tree to read (default: this repository)")
    parser.add_argument("--base-repo", help=f"git repository that holds {BASE_RELEASE} (default: --root)")
    parser.add_argument("--manifest", default=str(here / MANIFEST_NAME))
    parser.add_argument("--out", help="propose: where to write (default: --manifest)")
    return parser


def main(argv=None):
    args = argument_parser().parse_args(argv)
    sys.stdout.reconfigure(encoding=ENCODING)
    base_repo = args.base_repo or args.root
    if not base_present(base_repo):
        # Obligation 1: a run that could not compare is not a pass.
        print(f"NOT ASSESSED: base release {BASE_RELEASE} is not in {base_repo}")
        return 2
    tree = load_state(args.root, base_repo)
    manifest = load_manifest(args.manifest) if Path(args.manifest).is_file() else empty_manifest()
    print(f"{len(tree.base)} base file(s) and {len(tree.added)} added file(s) covered in {args.root}")
    if args.command == "check":
        problems = check(tree, manifest)
        for problem in problems:
            print(f"{problem.path}: {problem.message}")
        print(f"{len(problems)} problem(s)")
        return 1 if problems else 0
    proposed, new = propose(tree, manifest)
    save_manifest(args.out or args.manifest, proposed)
    for entry in triage(tree, proposed, manifest, new):
        print(entry)
    unreviewed = sum(1 for p in check(tree, proposed) if NOT_REVIEWED in p.message)
    print(f"{len(new)} new hunk(s); {unreviewed} hunk(s) need a reason before `check` passes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
