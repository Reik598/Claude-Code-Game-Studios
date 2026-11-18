# /memory-audit — Phase 2: Collect the Evidence

> Part of `/memory-audit`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 2: Collect the Evidence

**In this file:**

- 2a Find the logs
- 2b Read each tool's output
- 2c A log with no errors: clean run, or no run?
- 2d Stale logs
- 2e Layout evidence

### 2a. Find the logs

`--logs` paths first. Without them, search for the tools' own header lines
(2b) with the Grep tool in `build*/`, `out/`, `target/`, `tests/` and
`production/qa/memory/` — derive the set from what is there, not from file
names. List what was found and ask which logs belong to this audit. None found
→ every measured section is `NOT ASSESSED — no sanitizer output`, and the
report says which runs would close each.

### 2b. Read each tool's output

Classify each log by the lines it holds. These are the tools' report headers;
read the lines the log actually has, and quote them in the finding.

| Tool | Error lines | What to extract |
|---|---|---|
| **ASan** | `ERROR: AddressSanitizer: <kind>` (heap-use-after-free, heap-buffer-overflow, stack-use-after-return, `attempting double-free`, …), `SUMMARY: AddressSanitizer:` | kind; the access stack's first frame in the project's code (file:line); the `freed by` and `previously allocated by` stacks' first project frames |
| **LSan** | `ERROR: LeakSanitizer: detected memory leaks`, `Direct leak of`, `Indirect leak of` | bytes and object count; the allocation stack's first project frame |
| **UBSan** | `runtime error:`, `SUMMARY: UndefinedBehaviorSanitizer` | the file:line on the `runtime error` line and the message |
| **TSan** | `WARNING: ThreadSanitizer: <kind>` (`data race`, `lock-order-inversion (potential deadlock)`, …), `SUMMARY: ThreadSanitizer` | the two accesses' first project frames and their threads |
| **Miri** | `error: Undefined Behavior:`, `error: memory leaked` | the message and the `-->` file:line |
| **Valgrind** | `Invalid read of size`, `Invalid write of size`, `Invalid free()`, `definitely lost`, `indirectly lost`, `ERROR SUMMARY:` | kind, bytes, first project frame |

"First project frame" means the first stack frame whose file is under the audit
scope, not in the standard library, the sanitizer runtime or a third-party
folder. When a stack has no symbol or file (a build without debug info), record
`unsymbolised — rebuild with debug info` and keep the finding.

Collapse duplicates: the same kind at the same first project frame is one
finding with a count.

### 2c. A log with no errors: clean run, or no run?

Most sanitizers print nothing when nothing went wrong, so a log with no error
lines is either a clean sanitized run or a run without the sanitizer. Count it
as a **clean run** only when both hold:

1. The log or its build shows the sanitizer was on — the flags in the log, in
   the build cache, or in the preset the user names as the one that produced it;
   or the user confirms it.
2. The log shows tests ran: a non-zero test count (a CTest or `cargo test`
   summary, or the count and `rule` rows a `test-run.sh custom` run printed —
   output the user supplies; this skill runs nothing). Valgrind's
   `ERROR SUMMARY: 0 errors` shows the tool ran but not what it covered.

Otherwise: `NOT ASSESSED — cannot tell a clean <tool> run from an unsanitised
one (<which of 1 or 2 is missing>)`.

**Leak checking is its own run.** An ASan log counts as a leak-checking run only
when it holds a LeakSanitizer section, or its options show leak detection on;
whether it is on by default depends on the platform and is not assumed here.

### 2d. Stale logs

A log is **current** only when it is bound to the source and build inputs as
they are now. Include the resolved source roots and the manifests, toolchain,
sanitizer settings and other build inputs used for those targets.

1. **Source identity.** Read the receipt beside the log, or identity lines in
   it. Compare the full tested revision to `git log -1 --format=%H`. A matching
   revision covers tracked files only while their current contents match it.
   A different revision needs matching content fingerprints for all relevant
   source/build inputs before it can describe the same tested contents.
2. **Working-tree contents.** Run
   `git status --porcelain --untracked-files=all -- <source roots> <build inputs>`.
   A receipt must bind the contents of changed and untracked inputs, including
   active inputs ignored by git, and the tested build configuration. Compare
   its fingerprints to current contents using the project's receipt verifier
   or read-only `git hash-object -- <file>` (without `-w`, with the same hash
   scheme as the receipt). The same commit and dirty filenames are insufficient:
   a second edit to an already dirty file changes the tested contents.
3. **Missing binding.** A clean tree or a recent date does not identify the
   tested revision. With a missing, mismatched or incomplete receipt, ask whether
   the run used the **current contents and build settings after the latest
   edit**, naming the unresolved inputs. Record explicit confirmation as the
   basis; absent/unknown confirmation → `NOT ASSESSED — tested source/build
   identity not established (<inputs>)`. Recheck after any later edit.
4. **Dates reject stale evidence only.** Compare the log date with
   `git log -1 --format=%H%x09%cI -- <source roots> <build inputs>`; an older
   run is STALE. A newer date never supplies the identity checks above.

Stale or unbound logs retain their findings with their tested-source context,
but cannot make the verdict `CLEAN`. State the mismatch, missing identity or
older revision in the NOT ASSESSED reason. Without git, use a matching content
receipt or explicit current-source/build confirmation under the same rule.

### 2e. Layout evidence

| Source | Read |
|---|---|
| `pahole` output | per struct: `size`, `cachelines`, `sum holes`, `padding`; the holes' positions |
| `-Wpadded` warnings | struct, member, and the file:line on the warning; bytes of padding only where the warning prints them — Clang's do, GCC's member warning (`padding struct to align …`) does not, so those bytes are `unknown` without `pahole` or `size_of` output |
| a test or tool printing `sizeof`/`alignof`, `std::mem::size_of`/`align_of` | struct, size, alignment, and the sum of member sizes when printed |
| `static_assert(sizeof(T) == N)` or a Rust `const _: () = assert!(size_of::<T>() == N)` in the code | the size the compiler checked — measured, for that target only |

Waste per struct = size − sum of member sizes, and as a percent of size. Flag a
hot array of structs (one an ADR, `docs/architecture/memory-invariants.md` or a
`/benchmark-report` hotspot names) whose waste is over 25 %, and any struct over
one cache line that is touched per frame. With no layout source:
`Padding: NOT ASSESSED — no layout evidence (pahole, -Wpadded, size_of output)`.
Layout differs per compiler, target and ABI: a size measured on one target is
reported with that target.

---
