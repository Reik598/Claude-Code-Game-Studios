# /memory-audit — Phase 3: Read the Code

> Part of `/memory-audit`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 3: Read the Code

**In this file:**

- 3a Allocator and arena inventory
- 3b C++ risk scan
- 3c Rust risk scan
- 3d Turning a match into a finding

Everything found here is **read** evidence: a risk, labelled
`risk — unconfirmed`, until a sanitizer run (Phase 2) confirms or clears it.

### 3a. Allocator and arena inventory

Find every allocator in scope — the project's own and the global hooks:

- C++: classes or functions named for an allocation strategy (arena, linear,
  bump, stack, frame, pool, slab, buddy, TLSF, ring), overrides of global or
  class `operator new`/`operator delete`, `std::pmr::memory_resource`
  subclasses, and allocator template arguments on containers.
- Rust: `#[global_allocator]`, implementations of `GlobalAlloc` or
  `Allocator`, and arena or bump types the crates define.

Per allocator, record: kind, `file:line`, the owner (which system creates and
destroys it), its reset or free point (per frame, per level, never), which
threads touch it, and its capacity and alignment where the code states them.

Then check, each with `file:line`:

- **Frame or linear arenas reset while a pointer into them survives** — a
  pointer or reference stored in a longer-lived object (a component, a cache, a
  job queued for the next frame).
- **Allocate from one allocator, free to another** — a block from an arena
  freed with `delete` or `free`, or a pool block returned to a different pool.
- **Shared allocator, no synchronisation** — an allocator reached from more
  than one thread (a job, a worker, a callback) with no lock, atomic or
  thread-local instance on that path.
- **Heap allocation in a per-frame path** where an arena exists for the purpose,
  if `docs/architecture/memory-invariants.md` or an ADR forbids it — cite the
  rule. Without such a rule, list it as an observation, not a finding.
- **Alignment** — an allocator that hands out blocks for a type with an
  `alignas` or `#[repr(align(N))]` larger than the allocator's stated
  alignment.

Read `docs/architecture/memory-invariants.md` when it exists and check each
invariant it states against the code; an invariant the code breaks is a finding
citing both. It does not exist → say so; nothing is checked against it.

### 3b. C++ risk scan

Grep the scope, then read each match in context — a match is a place to look,
not a finding.

| Risk | Where to look |
|---|---|
| Use-after-free | `delete`/`free` followed by a later use of the same pointer on some path; raw pointers or references kept to an object another owner can destroy; `std::string_view`, `std::span` or a reference returned from, or stored beyond, the object that owns the data; lambdas capturing `this` or references and queued as jobs or callbacks |
| Invalidated references | a pointer, reference or iterator into a `std::vector` (or similar) held across `push_back`, `emplace_back`, `insert`, `resize`, `erase` or a swap-remove on the same container |
| Double free | two owners of one raw pointer (copied raw owning pointer, a class with a raw owning member and the implicit copy constructor); `delete` in both a destructor and a `release`/`shutdown` method without nulling |
| Handles | entity or resource handles with no generation counter, used after their slot can be recycled |
| Out-of-bounds | `memcpy`/`memmove`/`memset` sizes not derived from the destination; indexing with a value read from a file or packet before a bounds check; `reinterpret_cast` over a buffer of unchecked length |
| Leaks | `new` or `malloc` with no owner type (`std::unique_ptr`, a container, an arena) on every exit path, including early returns and error paths when exceptions are off |

### 3c. Rust risk scan

Safe Rust rules out most of 3b; the risk concentrates in `unsafe`. Grep for
`unsafe`, then read each block and its callers; the Leaks row's calls are
safe Rust, so grep for them too:

| Risk | Where to look |
|---|---|
| Use-after-free, aliasing | raw pointers (`*const`, `*mut`) dereferenced after the owner may have moved or dropped; `&mut` created from a raw pointer while another reference is live |
| Double free | `Box::from_raw`, `Vec::from_raw_parts`, `ptr::read` on the same allocation twice; `ManuallyDrop::drop` called on a path that also drops |
| Invalid values | `mem::transmute`, `MaybeUninit::assume_init` before every field is written, `slice::from_raw_parts` with an unchecked length |
| Leaks | `mem::forget`, `Box::leak`, `ManuallyDrop` with no matching release; `Rc`/`Arc` cycles with no `Weak` |
| FFI | pointers passed to or returned from C (graphics drivers, platform APIs) whose lifetime the Rust side does not own |

Each `unsafe` block should carry a `// SAFETY:` comment stating why it is sound.
A block without one is an observation; a block whose stated reason the code
does not uphold is a risk.

### 3d. Turning a match into a finding

A finding is reported only when you can name **the sequence or input that makes
it go wrong** — "the job queued at `jobs.cpp:88` runs after
`FrameArena::reset()` at `frame.cpp:40` and reads the pointer it captured".
When every path you can enumerate is guarded, drop it. When you cannot tell,
report it as `risk — unconfirmed, needs <ASan/LSan/TSan/Miri> run` rather than
promoting or dropping it.

Number the findings `MEM-NNN`. Each has kind, `file:line`, the quoted code, the
triggering sequence, severity (SKILL.md Phase 4), and the fix.

---
