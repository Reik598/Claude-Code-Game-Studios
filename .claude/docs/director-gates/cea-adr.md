> Gate definition. The spawning skill passes this file's path to the director agent; the AGENT reads it — the parent session should not.

# CEA-ADR — Engine-Internal ADR Review

Agent: `chief-engine-architect` | Model tier: `opus` · effort `high` | Domain: Engine internals — memory, threading, frame budget, ABI, determinism, platform and graphics-API support

**Applies only when** `engine.name` is `Custom`. On any other engine, do not
spawn this gate; an engine-internal ADR there does not exist, and TD-ADR covers
the project's ADRs.

**Trigger**: After an engine-internal ADR is authored (`/architecture-decision`
in engine mode — an ADR about code under `engine/`), before it is marked
Accepted. TD-ADR still runs on the same ADR; this gate does not replace it, and
only `technical-director` moves an ADR to Accepted.

**Context to pass**:
- ADR file path (or draft content)
- `engine.name` and the stack (C++ + CMake or Rust + Cargo) from `project.yaml`
- `performance.frame_budget_ms` and `performance.target_framerate`, or "unset"
- Path to `docs/engine-reference/custom/VERSION.md`, or "absent"
- Path to `docs/architecture/memory-invariants.md`, or "none"
- Related ADRs (if any)

**Prompt**:
> "Review this engine-internal Architecture Decision Record. Check that each of
> these six sections is present and specific — or explicitly marked
> `N/A — <why>`:
> **Memory** (allocator or arena used, ownership and lifetime, peak and
> steady-state size, no heap allocation in hot paths unless justified);
> **Threading** (which threads or jobs touch the data, the synchronization
> used, what is shared and what is thread-local);
> **Latency & Frame Budget** (cost per frame in ms against the project's
> `performance.frame_budget_ms` and the subsystem's slice of it, CPU and GPU
> separately where both apply);
> **ABI / API Stability** (which public engine interface changes, the
> versioning or deprecation plan, effect on the game code under `game/`);
> **Determinism** (whether results must be bit-identical across runs,
> threads or platforms, and how that is kept);
> **Platform / Graphics-API Matrix** (each target platform × graphics API the
> decision affects, whether it is supported, and the fallback or difference
> where a feature is missing on one of them — a row per pair, not a blanket
> 'all platforms').
> Check that every external fact — API or extension version, SDK, compiler,
> driver behaviour, platform capability — cites `docs/engine-reference/custom/`
> or is written `NOT SOURCEABLE — … not covered by docs/engine-reference/custom/`,
> and that every number cites a measurement or is labelled an estimate. Then
> give the verdict by the precedence below, first match wins."

**Verdicts**: APPROVE / CONCERNS / REJECT

NOT ASSESSED is the same word at every gate (`director-gates.md`, Standard
Verdict Format); this gate's conditions for it are item 3 below.

**Precedence — stated once, first match wins.** A known problem outranks an
unknown, and an unknown outranks a pass:

1. **REJECT** — one of the six sections is missing (neither filled nor
   `N/A — <why>`); the decision breaks the frame budget or a memory invariant;
   or the decision rests on an external fact the ADR **asserts** with neither a
   citation nor a NOT SOURCEABLE mark — an unsupported assertion the decision
   depends on.
2. **CONCERNS** — a section is present but not specific (a matrix with no rows
   per platform × API, a threading section that names no synchronization), an
   estimate with no plan to measure it, or an unsupported assertion the
   decision does **not** rest on. Name each.
3. **NOT ASSESSED** — nothing above was found, and something could not be
   checked. Name each:
   - neither the ADR file nor its draft content was passed, or it cannot be read;
   - `engine.name` is not `Custom` — name it; this gate does not apply;
   - the decision rests on a pinned external fact and
     `docs/engine-reference/custom/VERSION.md` is absent — name the facts;
   - the decision rests on a fact the ADR **correctly discloses** as
     `NOT SOURCEABLE` — the disclosure is right, and it is not a finding, but
     the decision cannot be judged until the fact is sourced — name the fact;
   - the Latency & Frame Budget section can only be judged against the budget
     and `performance.frame_budget_ms` is unset.
4. **APPROVE** — all six sections present and specific, every external fact the
   decision rests on cited, and every number measured or labelled an estimate. A
   correctly disclosed NOT SOURCEABLE fact the decision does **not** rest on is
   listed in the rationale and does not block APPROVE.

When a problem from 1 or 2 is found and an input from 3 is also missing, return
the problem's verdict and name the missing input in the rationale as well.
Never return APPROVE for a section you could not check.