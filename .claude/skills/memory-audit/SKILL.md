---
name: memory-audit
description: "Memory audit — allocator arenas, alignment padding, leaks, use-after-free and double-free risks; reads ASan/LSan/UBSan/TSan/Miri/Valgrind output. Findings with file:line."
argument-hint: "[path or module] [--logs <sanitizer-output-path> ...] [--layout <pahole-or-size-output>]"
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion, Bash(git log *), Bash(git status *), Bash(git hash-object -- *), Bash(bash "*/.claude/skills/memory-audit/../../hooks/yaml-helper.sh" resolve_config *)
model: sonnet
---

!`bash "${CLAUDE_SKILL_DIR}/../../hooks/yaml-helper.sh" resolve_config --keys engine,engine_row,automation,workflow`

Resolved above — use as-is. No block → defaults in
`.claude/docs/config-resolution.md`.

# Memory Audit

> **Explicit invocation only** (`disable-model-invocation: true`): this skill
> runs when the user types `/memory-audit`. Claude does not start it from context or
> through the Skill tool; another skill that needs it prints the command for
> the user. It runs on any engine and is oriented to a Custom one.

Every `AskUserQuestion` call follows `.claude/docs/automation-modes.md`
(collaborative asks always · guided major-only · autonomous logs and proceeds;
`automation_always_ask` categories always prompt).

This skill audits native memory: the allocators and their arenas, struct layout
and padding, leaks, and use-after-free and double-free risk. It has two kinds of
evidence and never mixes them up:

- **Measured** — sanitizer and tool output: AddressSanitizer (ASan),
  LeakSanitizer (LSan), UndefinedBehaviorSanitizer (UBSan), ThreadSanitizer
  (TSan), Miri, Valgrind; layout output from `pahole`, `-Wpadded` warnings, or a
  test that prints `sizeof`/`alignof` or `std::mem::size_of`/`align_of`.
- **Read** — what a static reading of the code shows. A read finding is a
  **risk**, never a confirmed defect, and a clean read is never "no leaks".

It is written for a project that builds its own engine (`engine.name: Custom`,
C++ or Rust in the mapped engine modules). On another engine it runs on that project's native
code only (a GDExtension, a Unity native plugin, an Unreal module) and says
that the managed or garbage-collected side is outside its scope.

## Insufficient input — check this before producing any report

1. List the inputs: the source in scope, each sanitizer or tool log, any layout
   output, `docs/architecture/memory-invariants.md` and the ADRs on memory.
2. Record each `FOUND` or `ABSENT`.
3. A section whose input is ABSENT reads **`NOT ASSESSED — <reason>`**.
4. No source in scope and no log → stop: **`NOT ASSESSED — nothing to audit`**,
   naming the path that was empty.

**Never claim "no leaks", "no use-after-free" or "memory safe" from static
reading alone.** Those are claims about runs. Without a run that checks them,
the section says `NOT ASSESSED — no sanitizer output`, whatever the reading
found. A scan that found nothing because nothing ran has verified nothing.

---

## Phase 1: Scope

- On Custom, resolve source roots and module aliases using
  `.claude/docs/custom-engine-layout.md`, Resolving source roots for workflows.
  Include mapped `crates/<module>/` paths, including a crate-only engine.
- Argument an explicit path → that path. A short module name → its resolved
  module root; an ambiguous name needs an explicit path.
- No argument, `engine.name: Custom` → all resolved engine source roots and
  native game source (including the game workspace members' source roots).
- No argument, another engine → the native code folders that exist; none →
  `NOT ASSESSED — no native code in this project`.

List the files in scope by language (C/C++ headers and sources, Rust crates).
State the language mix; C++ and Rust use different scans (Phase 3). Use these
same resolved roots in Phase 2's commit and working-tree freshness checks.

---

## Phase 2: Collect the Evidence

**Read `references/evidence.md` now and follow it** — finding and reading the
sanitizer, Miri, Valgrind and layout outputs, and how old a log may be, are in
that file. Read it again if the conversation was compacted or resumed.

---

## Phase 3: Read the Code

**Read `references/scan.md` now and follow it** — the allocator inventory and the
static risk scans for C++ and Rust are in that file. Read it again if the
conversation was compacted or resumed.

---

## Phase 4: Report

```markdown
# Memory Audit — [scope]
Generated: [date]   Engine: [engine.name]   Languages: [C++ / Rust / both]

## Verdict
[DEFECTS FOUND | RISKS FOUND | NOT ASSESSED | CLEAN] — [every section NOT ASSESSED, with its reason]

## Evidence Read
| Input | Tool | Build / full revision | Source/build binding and age | Used? |
|-------|------|----------------|-----------------------------|-------|
| [path] | [ASan / LSan / UBSan / TSan / Miri / Valgrind / pahole / -Wpadded / size_of] | [value / unknown] | [matching revision/content receipt or explicit current-content confirmation / STALE — predates <commit> / NOT ASSESSED — identity not established] | [yes / no — why] |

## 1. Allocators and Arenas
| Allocator | Kind | File:line | Owner | Reset / free point | Thread use | Notes |
|-----------|------|-----------|-------|--------------------|------------|-------|

## 2. Alignment and Padding
[Measured: struct, size, padding bytes, % wasted, hot or cold, source of the number]
[Candidates (unmeasured): struct, file:line, why it is a candidate]
[or: NOT ASSESSED — no layout evidence (pahole, -Wpadded, size_of output)]

## 3. Leaks
[Measured: each leak report — bytes, allocation stack top frame file:line]
[or: NOT ASSESSED — no leak-checking run (LSan, ASan leak detection, Valgrind memcheck, Miri)]
[Read risks: file:line — the path that allocates without a free]

## 4. Use-after-free, Double-free, Out-of-bounds
[Measured: each sanitizer error — kind, access file:line, free file:line, alloc file:line]
[Read risks: MEM-NNN — file:line — pattern — why it can go wrong — the input or sequence that triggers it]

## 5. Undefined Behaviour and Data Races
[UBSan / Miri / TSan errors, each with file:line]
[or: NOT ASSESSED — no UBSan / Miri / TSan output, each named]

## Findings
| ID | Kind | Evidence | File:line | Severity | Fix |
|----|------|----------|-----------|----------|-----|
| MEM-001 | [leak / UAF / double free / OOB / UB / race / padding / arena] | [measured: tool / read: risk] | | [CRITICAL / HIGH / MEDIUM / LOW] | |

## Not Assessed
- [each section, its reason, and the run that would close it]
```

**Severity** (the same scale as `/security-audit`). A measured use-after-free,
double free, out-of-bounds access or data race is CRITICAL. A measured leak in
a per-frame path is HIGH, a one-time leak MEDIUM. A read risk takes the
severity of the defect it would be, one step lower, and is labelled
`risk — unconfirmed`. Padding waste is LOW unless it is in a hot array of
structs the ADRs, `docs/architecture/memory-invariants.md` or
`/benchmark-report` name, then MEDIUM.

**Verdict — first match wins:**

1. **DEFECTS FOUND** — any error in a current (not stale) sanitizer, Miri or
   Valgrind log.
2. **RISKS FOUND** — no measured defect, and either the static reading found at
   least one risk in sections 1–4, or a *measured* padding finding is MEDIUM
   (hot array). Padding is waste, not a memory-safety defect, so it never makes
   DEFECTS FOUND. A LOW padding finding is listed in the table and named on the
   verdict line (`… ; padding: N LOW findings`) but changes no verdict.
3. **NOT ASSESSED** — no failure above, and any prerequisite of CLEAN (rule 4)
   is missing. Name each one missing: no current leak-checking run (LSan, ASan
   with leak detection, Valgrind memcheck or Miri) over the scope; no current
   address-error run (ASan, Valgrind memcheck or Miri) over the scope — so a
   clean LSan-only run lands here, not at CLEAN; or a run whose log 2c could not
   tell from an unsanitised one, or that 2d found stale.
4. **CLEAN** — a current leak-checking run with no errors, a current
   address-error run (ASan, Valgrind or Miri) with no errors, and no read risk.
   One run may be both (ASan with leak detection on, Valgrind memcheck, Miri).

NOT ASSESSED ranks below both failures and above CLEAN: a known defect is more
actionable than an unknown, and an audit without a run has not shown the memory
is sound. **Every verdict line names each section that did not run** — for
example `CLEAN — padding NOT ASSESSED (no layout evidence); data races NOT
ASSESSED (no TSan output)`. A plain `CLEAN` is reachable only when every section
ran.

Show the summary in conversation, then ask: *"May I write this memory audit to
`production/qa/memory/memory-audit-[date].md`?"* Write only after a yes; create
the folder if absent. Keep every `NOT ASSESSED` line in the file.

---

## Phase 5: Next Steps

- `DEFECTS FOUND` → fix each CRITICAL first through `/dev-story` or `/bug-report`;
  re-run the same sanitizer build, then `/memory-audit` with the new logs.
- `RISKS FOUND` → run the sanitizer build that would confirm or clear each
  risk (ASan for use-after-free and double free, LSan for leaks, TSan for races,
  Miri for Rust `unsafe`), then re-run with `--logs`.
- `NOT ASSESSED` → produce the missing run; the build flags come from the
  project's own toolchain record (`docs/engine-reference/custom/`), and where that
  does not cover them, say they are `NOT SOURCEABLE` and ask the user rather
  than writing flags from memory.
- An allocator decision to change (a new arena, a pool size, an alignment rule)
  → `/architecture-decision` (its engine mode has a Memory section).
- Memory that grows across a capture → this skill reads sanitizer logs and
  layouts, not memory over time, and frame-time reports do not measure it
  either. Hand the profiler's memory-track export, or the allocator's per-arena
  statistics over the run, to `memory-allocator-specialist` on Custom
  (`performance-analyst` on another engine). No such export →
  `Memory growth: NOT ASSESSED — no memory-over-time capture`.

### Rules
- Every finding has a file and line, or the log line it came from.
- Measured and read evidence stay in separate columns; a read finding is never
  promoted to a defect by confident phrasing.
- This skill reads. It does not edit code, build, or run the sanitizers.
