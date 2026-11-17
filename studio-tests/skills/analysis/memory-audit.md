# Skill Test Spec: /memory-audit

## Skill Summary

`/memory-audit` audits native memory — allocators and arenas, alignment and
padding, leaks, use-after-free / double-free / out-of-bounds, and undefined
behaviour and data races — keeping **measured** evidence (ASan, LSan, UBSan,
TSan, Miri, Valgrind; `pahole`, `-Wpadded`, `size_of` output) apart from
**read** evidence (static scans of C++ and Rust `unsafe`, each a
`risk — unconfirmed`). It resolves `engine`, `engine_row`, `automation` and
`workflow` from the injected config block. Scope defaults to mapped engine roots
and native game source on `engine.name: Custom`; on another engine, the native code folders
only, saying the managed side is out of scope; none → `NOT ASSESSED — no native
code in this project`. A log with no errors counts as a clean run only when the
sanitizer was on and tests ran. A log is current only when a content-bound
receipt or the user's explicit confirmation ties it to the current source and
build inputs (revision; dirty, untracked and active ignored inputs; build
settings). A log older than the last change in scope is STALE, an unbound one
`NOT ASSESSED — tested source/build identity not established`; neither can make
the verdict CLEAN. Verdict, first
match wins: DEFECTS FOUND → RISKS FOUND → NOT ASSESSED (any CLEAN prerequisite
missing: no current leak-checking run, or no current address-error run) → CLEAN; every
verdict line names the sections that did not run. It never claims "no leaks" or
"memory safe" from reading. It asks "May I write this memory audit to
`production/qa/memory/memory-audit-[date].md`?" and keeps NOT ASSESSED lines.
Build flags it cannot source are `NOT SOURCEABLE`. No director gates.

---

## Static Assertions (Structural)

- [ ] Has required frontmatter fields: `name`, `description`, `argument-hint`, `user-invocable`, `allowed-tools`; `model: sonnet`; `disable-model-invocation: true`
- [ ] Has ≥2 phase headings; Phase 2 in `references/evidence.md`, Phase 3 in `references/scan.md`
- [ ] Contains verdict keywords: DEFECTS FOUND, RISKS FOUND, NOT ASSESSED, CLEAN — NOT ASSESSED ranks below both failures and above CLEAN
- [ ] States that a clean read is never "no leaks" and a read finding is labelled `risk — unconfirmed`
- [ ] Defines when a no-error log counts as a clean run (sanitizer on + tests ran) and the §2d freshness rule: full tested revision against `git log -1 --format=%H`, `git status --porcelain --untracked-files=all` over source roots and build inputs, content fingerprints compared with read-only `git hash-object` (never `-w`), and log dates used only to reject STALE evidence; `allowed-tools` includes `Bash(git status *)` and a `git hash-object` rule that cannot match `-w` (e.g. `Bash(git hash-object -- *)`)
- [ ] Uses the `/security-audit` severity scale (CRITICAL / HIGH / MEDIUM / LOW)
- [ ] Contains "May I write" naming `production/qa/memory/memory-audit-[date].md`
- [ ] Has a next-step handoff (Phase 5: `/dev-story`, `/bug-report`, `/architecture-decision`; memory growth goes, with a memory-track export, to `memory-allocator-specialist` on Custom or `performance-analyst` on another engine, else `Memory growth: NOT ASSESSED — no memory-over-time capture`)
- [ ] `allowed-tools` has no Edit and no build/run commands — it does not build or run sanitizers

---

## Director Gate Checks

None. The skill is an analysis report; no gates in any review mode.

---

## Fixture Defaults

Every case's `project.yaml` sets `modes.rigor: minimal` and
`modes.automation: collaborative`, with no `project.local.yaml`, unless its own
Fixture says otherwise. Rules: `studio-tests/CLAUDE.md` §
Fixture defaults. When a case explicitly calls a log current, its build receipt
binds the tested revision and source/build-input contents to the current state.
A timestamp alone does not supply that receipt. A case's stale or unknown-source
fixture takes precedence.

---

## Test Cases

### Case 1: Happy Path — ASan use-after-free in a current log

**Fixture:**
- `engine.name: Custom`, C++ under `engine/`
- `build/asan/test.log`: `ERROR: AddressSanitizer: heap-use-after-free`, access in `engine/jobs/src/worker.cpp:88`, freed by `engine/memory/src/frame_arena.cpp:40`, allocated by `engine/renderer/src/extract.cpp:121`; a CTest summary with 214 tests; log newer than the last commit touching `engine/`
- No LSan section, no layout evidence

**Input:** `/memory-audit engine --logs build/asan/test.log`

**Expected behavior:**
1. Inputs: source FOUND, ASan log FOUND (current), LSan ABSENT, layout ABSENT
2. Finding MEM-001: heap-use-after-free, measured, CRITICAL, with the three first project frames
3. Leaks: `NOT ASSESSED — no leak-checking run`; padding `NOT ASSESSED — no layout evidence`; races `NOT ASSESSED — no TSan output`
4. Verdict `DEFECTS FOUND — ...` naming each NOT ASSESSED section
5. Asks "May I write this memory audit to `production/qa/memory/memory-audit-[date].md`?"
6. Next step: fix the CRITICAL via `/dev-story` or `/bug-report`, re-run the ASan build, re-run `/memory-audit`

**Assertions:**
- [ ] The UAF is CRITICAL and measured, with access/free/alloc file:line
- [ ] Verdict DEFECTS FOUND and the line names the sections that did not run
- [ ] "May I write" before any write

---

### Case 2: No Sanitizer Run — reading alone cannot say CLEAN

**Fixture:**
- `engine.name: Custom`; `engine/memory/` has a pool allocator and frame arena
- No sanitizer, Miri or Valgrind log anywhere; static reading finds no risk

**Input:** `/memory-audit memory`

**Expected behavior:**
1. Scope read as `engine/memory/`
2. Evidence search finds no logs → every measured section `NOT ASSESSED — no sanitizer output`, naming the runs that would close each (LSan, ASan, TSan, UBSan)
3. Verdict `NOT ASSESSED` — never CLEAN, and never "no leaks"
4. Build flags for the missing runs: from `docs/engine-reference/custom/` if documented, else `NOT SOURCEABLE` and ask the user

**Assertions:**
- [ ] Verdict NOT ASSESSED despite a clean read
- [ ] The words "no leaks" / "memory safe" do not appear as a conclusion
- [ ] No sanitizer flags written from memory

---

### Case 3: No-Error Log That Proves Nothing

**Fixture:**
- `build/debug/test.log` has no sanitizer lines and a CTest summary "0 tests"; nothing shows a sanitizer was on

**Input:** `/memory-audit engine --logs build/debug/test.log`

**Expected behavior:** The log is not counted as a clean run: `NOT ASSESSED — cannot tell a clean ASan run from an unsanitised one (sanitizer not shown on; zero tests ran)`. Verdict NOT ASSESSED (or RISKS FOUND if the read found a risk).

**Assertions:**
- [ ] Not counted as clean; both missing conditions named
- [ ] Verdict is never CLEAN

---

### Case 4: Stale Log and a Read Risk in Rust

**Fixture:**
- Rust crates under `engine/`; `target/miri.log` with no errors, dated before the last commit to `engine/jobs`
- `engine/jobs/src/stack.rs` pops a node with `Box::from_raw` while another thread may still read it; no `// SAFETY:` comment

**Input:** `/memory-audit jobs --logs target/miri.log`

**Expected behavior:**
1. Miri log marked STALE (`predates <commit>`); its result cannot make the verdict CLEAN
2. Read finding MEM-001: use-after-free risk, `risk — unconfirmed, needs Miri/Loom run`, severity one step below CRITICAL, with the triggering sequence
3. Missing `// SAFETY:` comment noted as an observation
4. Verdict RISKS FOUND, naming the stale log

**Assertions:**
- [ ] STALE log named; not used for CLEAN
- [ ] Read risk is not promoted to a defect
- [ ] Verdict RISKS FOUND

---

### Case 5: Non-Custom Engine With No Native Code

**Fixture:**
- `engine.name: Godot`; project is GDScript only, no GDExtension folder

**Input:** `/memory-audit`

**Expected behavior:** Scope resolves to the native code folders that exist; none → stops with `NOT ASSESSED — no native code in this project`, saying the managed (GDScript) side is outside its scope. No report, no write prompt.

**Assertions:**
- [ ] Verdict `NOT ASSESSED — no native code in this project`
- [ ] Does not audit GDScript or claim the project is memory safe

---

### Case 6: Padding Measured on a Hot Array

**Fixture:**
- `engine.name: Custom`; `pahole` output for `struct Particle` (size 64, holes 22 bytes) on x86_64; `docs/architecture/memory-invariants.md` names `Particle[]` as a hot per-frame array
- A current LSan + ASan run with no errors and 300 tests

**Input:** `/memory-audit engine --logs build/asan/test.log --layout out/pahole.txt`

**Expected behavior:** Padding measured: 22/64 = 34 % waste on a hot array → a MEDIUM padding finding with the target (x86_64) named; leak and address runs clean; no read risk. Verdict **RISKS FOUND** (a measured MEDIUM padding finding, no measured defect), never DEFECTS FOUND (padding is waste, not a memory-safety defect); the verdict line names data races `NOT ASSESSED — no TSan output`, and the padding finding appears in the Findings table.

**Assertions:**
- [ ] Waste computed (bytes and %), target (x86_64) stated, severity MEDIUM because the array is named hot
- [ ] Verdict line names TSan as not run
- [ ] A plain `CLEAN` without qualifiers does not appear

---

### Case 7: LSan-only clean run — NOT ASSESSED, not CLEAN and not unmatched

**Fixture:**
- `engine.name: Custom`; `build/lsan/test.log`: an LSan-only build (no ASan), leak detection on, no errors, CTest summary with 180 tests; current against the last commit; clean working tree
- No ASan, Valgrind or Miri log; no read risk

**Input:** `/memory-audit engine --logs build/lsan/test.log`

**Expected behavior:** Leak section measured clean; section 4 (use-after-free, double-free, out-of-bounds) `NOT ASSESSED — no address-error run (ASan, Valgrind memcheck or Miri)`. Verdict **NOT ASSESSED**, naming the missing address-error run — a verdict always matches; CLEAN needs both runs.

**Assertions:**
- [ ] Verdict is NOT ASSESSED, never CLEAN
- [ ] The missing address-error run is named on the verdict line

---

### Case 8: Uncommitted changes after the run

**Fixture:**
- `engine.name: Custom`; a current-by-date ASan + LSan log with no errors and 214 tests, newer than the last commit to `engine/`
- `git status --porcelain --untracked-files=all` over `engine/` and its build inputs lists only ` M engine/memory/src/pool.cpp`; no build receipt beside the log
- Static reading finds no risk in scope

**Input:** `/memory-audit engine --logs build/asan/test.log`

**Expected behavior:**
1. Runs `git status --porcelain --untracked-files=all -- <source roots> <build inputs>` alongside the `git log -1 --format=%H` revision check
2. Asks whether the run used the current contents and build settings after the latest edit, naming `engine/memory/src/pool.cpp`
3. User says no (or does not know) → `NOT ASSESSED — tested source/build identity not established (engine/memory/src/pool.cpp)`; verdict NOT ASSESSED (no read risk)
4. Variant — the user explicitly confirms the run used the current contents and build settings after the latest edit, or a receipt records the matching full revision plus content fingerprints for every changed, untracked and active ignored input and the tested build configuration → the log is current and the verdict may be CLEAN. A receipt naming only the commit and the dirty filenames does not qualify.

**Assertions:**
- [ ] A log date newer than the last commit never establishes that the log is current
- [ ] The unbound file is named in the question and in the NOT ASSESSED reason
- [ ] After a no or don't-know answer the verdict is NOT ASSESSED, never CLEAN or RISKS FOUND
- [ ] Variant — an explicit confirmation is recorded as the basis in the input table and the verdict is CLEAN (naming the sections that did not run); without that confirmation, a receipt with only the commit and dirty filenames leaves it NOT ASSESSED

---

### Case 9: Rust workspace aliases — default scope and stale evidence

**Fixture:** Custom engine with engine modules at `crates/memory/` and
`crates/jobs/`, a game at `game/`, and no `engine/`. Module map and root
workspace identify each member. A Miri receipt predates an uncommitted change
to `crates/memory/src/lib.rs`; no receipt confirms the working tree.

**Input:** `/memory-audit memory --logs target/miri.log`, then `/memory-audit`

**Expected behavior:** Resolves `memory` through the module map to
`crates/memory/`. The no-argument audit includes both engine crates and game
native source. Source is FOUND, not an empty `engine/memory/` path. Applies
freshness checks to the resolved roots and reports stale working-tree evidence;
cannot return CLEAN from that receipt. Ambiguous module names request a path.

**Assertions:**
- [ ] Module and default scopes include registered crate aliases
- [ ] Dirty crate source invalidates the receipt's freshness
- [ ] Neither build nor sanitizer is run by this reporting skill

---

### Case 10: A newer log from another revision

**Fixture:** Clean current revision B; ASan/LSan log comes from revision A on
another branch. Its date is newer than B's last source commit. The receipt's
source fingerprint differs and the user does not confirm equivalent current
contents. No static risk is found.

**Input:** `/memory-audit --logs build/asan/test.log`

**Expected behavior:** Reports the identity mismatch and NOT ASSESSED; date
cannot establish freshness. Variant: log has no revision/fingerprint and no
current-source confirmation → NOT ASSESSED, never CLEAN.

**Assertions:**
- [ ] The revision/fingerprint mismatch is named; the newer log date is not used as freshness
- [ ] Verdict is NOT ASSESSED in both the mismatch and the no-identity variant, never CLEAN

---

### Case 11: Second edit to the same dirty file

**Fixture:** HEAD is revision A. The receipt names revision A and dirty
`crates/memory/src/pool.rs`, whose tested git blob hash is H1. That file is
edited again to H2; `git status` still names the same file. An untracked
`crates/memory/src/parser.rs` is added after the run. Static reading finds no
risk. Asked whether the run used the current contents, the user answers no or
does not know.

**Input:** `/memory-audit memory --logs target/miri.log`

**Expected behavior:** Compares contents, including untracked source and relevant
manifest/toolchain/sanitizer inputs. Same revision and filenames are insufficient;
the mismatched or absent content binding makes evidence NOT ASSESSED. A later
confirmation must explicitly cover the current contents after the latest edit.

**Assertions:**
- [ ] Compares current contents against the receipt's fingerprints (receipt verifier or read-only `git hash-object -- <file>`, never `-w`), not filenames
- [ ] The untracked `crates/memory/src/parser.rs` and the manifest/toolchain/sanitizer inputs are inside the binding check
- [ ] Verdict NOT ASSESSED while the current contents are unconfirmed, never CLEAN; a confirmation counts only when it covers the contents after the latest edit

---

## Protocol Compliance

- [ ] Records each input FOUND or ABSENT; ABSENT sections read `NOT ASSESSED — <reason>`
- [ ] Measured and read evidence kept in separate columns; read findings labelled `risk — unconfirmed`
- [ ] Never claims "no leaks" or "memory safe" without a current leak-checking run
- [ ] STALE or unbound logs cannot produce CLEAN
- [ ] Every verdict line names each section that did not run
- [ ] Asks "May I write" naming `production/qa/memory/memory-audit-[date].md`; keeps NOT ASSESSED lines in the file
- [ ] Does not edit code, build, or run sanitizers
- [ ] Ends with the Phase 5 next step for the verdict

---

## Coverage Notes

- TSan data-race output (CRITICAL race finding) has no dedicated case.
- `docs/architecture/memory-invariants.md` invariant violations are only touched in Case 6.
- Unsymbolised stacks (`unsymbolised — rebuild with debug info`) are not covered.
