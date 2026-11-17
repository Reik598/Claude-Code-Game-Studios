"""Phase 8, lane B: the change's status records agree with the tree.

Run: python -m unittest discover -s studio-tests -p test_engine_phase8b.py -v

Fix 8.7 (score report D1): the files that record the engine-support change's
review state must not claim a test count other than the suite's, must not say
review is closed or converged while the fix plan's open points are open, must
list those open points, and the review snapshot must either match the files it
hashes or say it is superseded and why.
Fix 9.1 (score report 2, N1) extends this: the ledger size a current status
record states must equal the ledger files, and no current record may call a
phase unreviewed once its critic findings file is listed.
These test the records' text, not a Claude session.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import BASE_RELEASE, COUNT_NUMBER, RELEASE_NOTE_SECTIONS, ROOT, parse_count, read  # noqa: E402

STUDIO_TESTS = Path(__file__).resolve().parent
RESEARCH_DIR = "docs/research/aaa-engine-support-2026"
FIX_PLAN = f"{RESEARCH_DIR}/fix-plan.md"
CONTINUATION = "CONTINUE-ENGINE-SUPPORT.md"
SNAPSHOT = f"{RESEARCH_DIR}/review-snapshot.json"
# The files that record the change's review state (fix plan fix 8.7). Enumerated:
# a status record is prose with no machine-readable marker, so which files are
# records cannot be derived (.claude/rules/skill-authoring.md, obligation 5); a
# new status file must be added here.
STATUS_FILES = (CONTINUATION, f"{RESEARCH_DIR}/implementation-audit.md", SNAPSHOT)
# A claim about the size of the Python suite: unittest's own "Ran N tests" line,
# or "N tests" / "N Python tests". Counts of other runners name the runner
# between the number and "tests" ("3 Rust callback tests") and are not matched.
SUITE_COUNT = re.compile(rf"\bRan ({COUNT_NUMBER}) tests?\b|\b({COUNT_NUMBER})"
                         r"(?:[ \t]+(?:Python|unittest|structural))?[ \t]+tests?\b")
# Statements that the review is finished.
CLOSED_REVIEW = (re.compile(r"Nothing in review remains open", re.I),
                 re.compile(r"^\s*result:\s*converged\b", re.I | re.M))
OPEN_POINTS_HEADING = re.compile(r"^## 8\. Open points[ \t]*$", re.M)
OPEN_POINT_ROW = re.compile(r"^\|\s*(O\d+)\s*\|.*\|\s*([^|]*?)\s*\|\s*$", re.M)
# P8 critic F7: an amendment can raise an open point in prose ("New open point
# **O15**"); each such id must also be a section 8 row, or the records checked
# against section 8 can miss it. AM25(c): the plan also writes it as
# "**O16 (new open point):**".
OPEN_POINT_MENTION = re.compile(r"open point \*\*(O\d+)\*\*|\*\*(O\d+) \(new open point\)", re.I)
# The records that list the open points: the continuation file by id, the audit
# by id or by a range ("O8–O14").
OPEN_POINT_LISTS = (CONTINUATION, f"{RESEARCH_DIR}/implementation-audit.md")
OPEN_POINT_RANGE = re.compile(r"\bO(\d+)[–-]O(\d+)\b")
CLOSED_STATUS = "Closed"
SUPERSEDED = "superseded"
# Fix 9.1 (score report 2, N1). The evidence ledger, and a status record's
# statement of its size ("98 sources, 290 evidence records (E01-E290) and 123
# claims").
LEDGER_FILES = {"sources": "sources.jsonl", "evidence": "evidence.jsonl", "claims": "claims.jsonl"}
LEDGER_COUNT = re.compile(r"\b(\d+) sources,[ \t\n]+(\d+)[ \t\n]+evidence[ \t\n]+records(?:[ \t\n]+\([^)]*\))?,?"
                          r"[ \t\n]+(?:and[ \t\n]+)?(\d+)[ \t\n]+claims\b")
# run_manifest.json keeps one dated "ledger_*" entry per step; the earlier ones
# record the ledger as it was then, and only the last describes the tree.
MANIFEST = f"{RESEARCH_DIR}/run_manifest.json"
MANIFEST_LEDGER_KEY = "ledger_"
# The continuation's review table is the in-repo record of which phases'
# critic findings files exist (the files sit in the session scratchpad, outside
# the repository): a row "| AAA-ENGINE-2026-P8 |" says Phase 8 was reviewed.
REVIEW_ROW = re.compile(r"^\|\s*AAA-ENGINE-2026-P(\d+)\w*\s*\|", re.M)
# Phase 10 R64: the plan also records a phase's critic rounds ("P9 critic
# round 2", "P9 findings F5, F8", "P7D findings F4"). A phase the plan records
# a critic round or findings for was reviewed, whether or not the
# continuation's table has caught up with it.
PLAN_REVIEW_MENTION = re.compile(r"\bP(\d+)[A-Z]*\s+(?:critic\s+round|findings)\b")
# Phase 10 R65: the plan's own Status line (its first "Status:" paragraph)
# names the plan's last section and its last phase, so the plan does not
# describe itself as it was a phase earlier.
PLAN_STATUS = re.compile(r"^Status:[^\n]*", re.M)
PLAN_SECTION_MENTION = re.compile(r"\bsections?\s+(?:\d+[–-])?(\d+)\b|\(section (\d+)\)")
PHASE_RANGE = re.compile(r"\bPhases? (?:\d+[–-])?(\d+)\b")
# Phase 10 R68: the Unreleased "Files: Safe to Overwrite" section names every
# path the release changes, by itself or by a folder above it, and keeps the
# exception for the user's technical-preferences.md. The change's own working
# records are not shipped to users and are left out.
FILES_HEADING = re.compile(r"^### Files: Safe to Overwrite[ \t]*$", re.M)
NOT_SHIPPED = ("CONTINUE-ENGINE-SUPPORT.md", "docs/research/")
USER_FILE = ".claude/docs/technical-preferences.md"
# Statements that a phase is still unreviewed or under way. The forms are the
# ones the status records have used ("Phase 8 in progress", "has not yet been
# reviewed by a critic", "its critic has not run yet", "the Phase 9 critic has
# not checked these", "await the Phase 9 critic", "Phase 8 critic re-run
# pending"; P9 critic F6). Wording is free prose, so the list is kept here and
# a new form must be added (.claude/rules/skill-authoring.md:76-79). Each match
# is charged to the last "Phase N" of its sentence at or before the match's
# end, so "Phase 9 (...) addresses ...; its critic has not run yet" is Phase 9's.
UNREVIEWED_WORDING = re.compile(
    r"\b(?:in progress|unreviewed|review pending"
    r"|has not (?:yet )?(?:been )?(?:run|reviewed|checked)|not yet (?:been )?(?:run|reviewed|checked)"
    r"|awaits?\b[^.|]{0,40}?\bcritic|critic\b[^.|]{0,40}?\b(?:pending|not yet run))", re.I)
PHASE_MENTION = re.compile(r"\bPhase (\d+)\b")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*(|#-])")
# P9 critic F3: how a status record states how far the plan is implemented.
# Every such statement names the plan's last phase (its highest "## N. Phase M"
# section heading).
IMPLEMENTED_THROUGH = (re.compile(r"implemented through Phase (\d+)"),
                       re.compile(r"Phases 1[–-](\d+) (?:are|is) implemented"),
                       re.compile(r"^#+ Current state\b[^\n]*\bPhase (\d+)", re.M))
PLAN_PHASE_SECTION = re.compile(r"^## \d+\. Phase (\d+)\b", re.M)
# P9 critic F11, AM24(c): an amendment range ("AM1–AM24", "AM20–AM24 in its
# section 11") ends at the plan's last amendment, or at the last one of the
# section it names. An amendment is defined by a section 9 table row
# ("| AM16 |") or a bold "amendment AM<n>" heading in a later section.
AM_RANGE = re.compile(r"\bAM(\d+)[–-]AM(\d+)\b(?:\s+in\s+its\s+section\s+(\d+))?")
PLAN_SECTION = re.compile(r"^## (\d+)\. ", re.M)
AM_DEFINITION = re.compile(r"^\|\s*AM(\d+)\s*\||\bamendment AM(\d+)\b", re.M)
AM_RANGE_FILES = (CONTINUATION, f"{RESEARCH_DIR}/implementation-audit.md", f"{RESEARCH_DIR}/run_manifest.json")


def suite_count():
    """The number of tests unittest discovers in studio-tests, without running them."""
    loader = unittest.TestLoader()
    return loader.discover(str(STUDIO_TESTS), pattern="test_*.py", top_level_dir=str(STUDIO_TESTS)).countTestCases()


def open_points():
    """Ids of the fix plan's section 8 rows whose status is not Closed."""
    text = read(FIX_PLAN).replace("\r", "")
    start = OPEN_POINTS_HEADING.search(text)
    if start is None:
        return None
    end = re.search(r"^## ", text[start.end():], re.M)
    body = text[start.end():start.end() + end.start()] if end else text[start.end():]
    return [pid for pid, status in OPEN_POINT_ROW.findall(body) if not status.startswith(CLOSED_STATUS)]


def named_open_points(text):
    """Open point ids a record names, singly or inside a range."""
    named = set(re.findall(r"\bO\d+\b", text))
    for first, last in OPEN_POINT_RANGE.findall(text):
        named.update(f"O{n}" for n in range(int(first), int(last) + 1))
    return named


def file_sha256(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def ledger_counts():
    """(sources, evidence records, claims): the line counts of the ledger files."""
    return tuple(len((ROOT / RESEARCH_DIR / name).read_text(encoding="utf-8").splitlines())
                 for name in LEDGER_FILES.values())


def last_manifest_ledger_entry():
    """(key, text) of the last "ledger_*" entry of run_manifest.json's verification."""
    verification = json.loads(read(MANIFEST))["verification"]
    entries = [(key, text) for key, text in verification.items() if key.startswith(MANIFEST_LEDGER_KEY)]
    return entries[-1] if entries else (None, "")


def reviewed_phases():
    """Phase numbers the continuation's review table lists a findings file for,
    or the plan records a critic round or findings for (R64)."""
    return sorted({int(n) for n in REVIEW_ROW.findall(read(CONTINUATION))}
                  | {int(n) for n in PLAN_REVIEW_MENTION.findall(read(FIX_PLAN))})


def changed_paths():
    """Paths the worktree changes or adds against the base release, or None
    when the base release is not in this clone (O14)."""
    diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", BASE_RELEASE],
                          capture_output=True, text=True, encoding="utf-8")
    if diff.returncode != 0:
        return None
    new = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard"],
                         capture_output=True, text=True, encoding="utf-8")
    return sorted(set(diff.stdout.split()) | set(new.stdout.split()))


def unreviewed_statements(text):
    """(phase number, phrase) for each unreviewed-wording match, charged to the
    last "Phase N" of its sentence at or before the match's end."""
    found = []
    for sentence in SENTENCE_END.split(" ".join(text.split())):
        for match in UNREVIEWED_WORDING.finditer(sentence):
            phases = PHASE_MENTION.findall(sentence[:match.end()])
            if phases:
                found.append((int(phases[-1]), match[0]))
    return found


def plan_amendments():
    """{section number: highest amendment number it defines}."""
    text = read(FIX_PLAN).replace("\r", "")
    heads = list(PLAN_SECTION.finditer(text))
    found = {}
    for n, head in enumerate(heads):
        body = text[head.end():heads[n + 1].start() if n + 1 < len(heads) else len(text)]
        ids = [int(row or bold) for row, bold in AM_DEFINITION.findall(body)]
        if ids:
            found[int(head[1])] = max(ids)
    return found


def current_status_texts():
    """The status records' text that describes the tree now: the status files
    and the last ledger entry of run_manifest.json."""
    texts = {path: read(path) for path in STATUS_FILES}
    key, text = last_manifest_ledger_entry()
    texts[f"{MANIFEST} verification.{key}"] = text
    return texts


class StatusRecordsMatchTree(unittest.TestCase):
    def test_status_files_claim_the_suites_test_count(self):
        actual = suite_count()
        self.assertGreater(actual, 0, "the suite discovered no test")
        for path in STATUS_FILES:
            text = read(path)
            for match in SUITE_COUNT.finditer(text):
                claimed = parse_count(match[1] or match[2])
                line = text.count("\n", 0, match.start()) + 1
                with self.subTest(path=path, line=line, text=match[0]):
                    self.assertEqual(claimed, actual, f"{path}:{line} claims {match[0]!r}; the suite has {actual}")

    def test_no_closed_review_claim_while_open_points_are_open(self):
        still_open = open_points()
        self.assertIsNotNone(still_open, f"{FIX_PLAN} has no '## 8. Open points' section")
        if not still_open:
            return
        for path in STATUS_FILES:
            text = read(path)
            for pattern in CLOSED_REVIEW:
                with self.subTest(path=path, pattern=pattern.pattern):
                    self.assertIsNone(pattern.search(text),
                                      f"{path} says the review is closed while {', '.join(still_open)} are open")

    def test_continuation_lists_every_open_point(self):
        still_open = open_points()
        self.assertTrue(still_open, f"{FIX_PLAN} section 8 lists no open point; re-check this test")
        for path in OPEN_POINT_LISTS:
            named = named_open_points(read(path))
            for pid in still_open:
                with self.subTest(path=path, open_point=pid):
                    self.assertIn(pid, named, f"{path} does not name open point {pid}")

    def test_every_open_point_the_plan_raises_is_a_section_8_row(self):
        text = read(FIX_PLAN).replace("\r", "")
        rows = set(re.findall(r"^\|\s*(O\d+)\s*\|", text, re.M))
        mentioned = {a or b for a, b in OPEN_POINT_MENTION.findall(text)}
        self.assertTrue(mentioned, f"{FIX_PLAN} raises no open point in prose; re-check this test")
        for pid in sorted(mentioned):
            with self.subTest(open_point=pid):
                self.assertIn(pid, rows, f"{FIX_PLAN} raises {pid} but section 8 has no row for it")

    def test_status_records_state_the_ledger_counts_on_disk(self):
        # Fix 9.1 (score report 2, N1): a ledger size any current status record
        # states equals the .jsonl line counts, and the last run_manifest.json
        # ledger entry states one.
        actual = ledger_counts()
        key, entry = last_manifest_ledger_entry()
        self.assertTrue(LEDGER_COUNT.search(entry or ""), f"{MANIFEST}: last ledger entry {key} states no ledger size")
        for where, text in current_status_texts().items():
            for match in LEDGER_COUNT.finditer(text):
                with self.subTest(where=where, text=" ".join(match[0].split())):
                    self.assertEqual(tuple(map(int, match.groups())), actual,
                                     f"{where} states {match[0]!r}; the ledger holds {actual}")

    def test_no_status_record_calls_a_reviewed_phase_unreviewed(self):
        # Fix 9.1 (score report 2, N1): once the review table lists a phase's
        # findings file, no current status record says that phase is in
        # progress, unreviewed, or waiting for its critic.
        phases = reviewed_phases()
        self.assertTrue(phases, f"{CONTINUATION} lists no reviewed phase; re-check this test")
        for where, text in current_status_texts().items():
            for phase, said in unreviewed_statements(text):
                with self.subTest(where=where, phase=phase, said=said):
                    self.assertNotIn(phase, phases, f"{where} calls reviewed Phase {phase} unreviewed: {said!r}")

    def test_status_records_name_the_plans_last_phase_as_implemented(self):
        # P9 critic F3: every "implemented through Phase N" (or "Phases 1-N
        # are implemented", or a "Current state ... Phase N" heading) in a
        # current status record names the plan's last phase, so no record
        # stops a phase short of another.
        last = max(map(int, PLAN_PHASE_SECTION.findall(read(FIX_PLAN).replace("\r", ""))), default=None)
        self.assertIsNotNone(last, f"{FIX_PLAN} has no '## N. Phase M' section")
        found = 0
        for where, text in current_status_texts().items():
            flat = " ".join(text.split())
            for pattern in IMPLEMENTED_THROUGH:
                for match in pattern.finditer(text if pattern.flags & re.M else flat):
                    found += 1
                    with self.subTest(where=where, text=match[0][:80]):
                        self.assertEqual(int(match[1]), last, f"{where} says {match[0][:80]!r}; the plan ends at Phase {last}")
        self.assertTrue(found, "no status record states how far the plan is implemented: re-check this test")

    def test_amendment_ranges_end_at_the_plans_last_amendment(self):
        # P9 critic F11, AM24(c): no status record stops the plan's amendments
        # short ("AM1–AM22" while the plan holds AM24).
        sections = plan_amendments()
        self.assertTrue(sections, f"{FIX_PLAN} defines no amendment: re-check this test")
        last = max(sections.values())
        found = 0
        for path in AM_RANGE_FILES:
            for match in AM_RANGE.finditer(" ".join(read(path).split())):
                found += 1
                expected = sections.get(int(match[3])) if match[3] else last
                with self.subTest(path=path, text=match[0]):
                    self.assertEqual(int(match[2]), expected, f"{path} says {match[0]!r}")
        self.assertTrue(found, "no status record states an amendment range: re-check this test")

    def test_plan_status_line_names_its_last_section_and_phase(self):
        # R65: the plan's Status line names its highest "## N." section and
        # its highest "Phase N" (P9 F3's class, in the plan itself).
        text = read(FIX_PLAN).replace("\r", "")
        status = PLAN_STATUS.search(text)
        self.assertIsNotNone(status, f"{FIX_PLAN} has no Status line")
        last_section = max(map(int, PLAN_SECTION.findall(text)))
        last_phase = max(map(int, PLAN_PHASE_SECTION.findall(text)))
        named_sections = {int(a or b) for a, b in PLAN_SECTION_MENTION.findall(status[0])}
        named_phases = {int(n) for n in PHASE_RANGE.findall(status[0])}
        with self.subTest(check="section"):
            self.assertIn(last_section, named_sections, f"the Status line names sections {sorted(named_sections)}")
        with self.subTest(check="phase"):
            self.assertIn(last_phase, named_phases, f"the Status line names phases {sorted(named_phases)}")

    def test_unreleased_files_section_names_every_changed_path(self):
        # R68: a user who follows the Unreleased file list gets every file the
        # release changes, and keeps technical-preferences.md.
        paths = changed_paths()
        if paths is None:
            self.skipTest(f"base release {BASE_RELEASE} is not in this clone (O14)")
        section = RELEASE_NOTE_SECTIONS["UPGRADING.md"].search(read("UPGRADING.md"))
        self.assertIsNotNone(section, "UPGRADING.md has no Unreleased section")
        start = FILES_HEADING.search(section[0])
        self.assertIsNotNone(start, "the Unreleased section has no Files: Safe to Overwrite heading")
        body = re.split(r"^### ", section[0][start.end():], maxsplit=1, flags=re.M)[0]
        named = set(re.findall(r"`([^`\s]+)`", body))
        self.assertIn(USER_FILE, named, "the .claude/docs/ entry no longer names the user's file")
        shipped = [p for p in paths if not p.startswith(NOT_SHIPPED)]
        self.assertTrue(shipped, "nothing changed against the base release: re-check this test")
        for path in shipped:
            ancestors = {path} | {"/".join(path.split("/")[:n]) + "/" for n in range(1, path.count("/") + 1)}
            with self.subTest(path=path):
                self.assertTrue(ancestors & named, f"{path} is not named, nor a folder above it")

    def test_review_snapshot_matches_or_is_superseded(self):
        snapshot = json.loads(read(SNAPSHOT))
        if snapshot.get("status") == SUPERSEDED:
            self.assertTrue(snapshot.get("superseded_reason", "").strip(), "superseded without a reason")
            return
        for path, digest in snapshot["files"].items():
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), "hashed file is missing")
                self.assertEqual(file_sha256(path), digest, "hash differs from the file on disk")


if __name__ == "__main__":
    unittest.main()
