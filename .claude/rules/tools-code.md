---
paths:
  - "engine/tools/**"
  - "crates/tools/**"
  - "tools/ci/**"
  - "tools/build/**"
  - "tools/cook/**"
  - "tools/asset-pipeline/**"
  - "tools/validators/**"
  - "tools/reports/**"
---

# Engine Tools Code Rules

For a project that builds its own engine (`engine.name: Custom`). Asset
cookers, the derived-data cache, build tools and the profiler build switch
(each module's owner places its own zones through `core-systems-lead`'s trace
API) are owned by `asset-build-tooling-engineer`, with `tools/ci/`, `tools/build/` and
`tools/cook/`; in-game debug tools and the standalone pipeline and batch tools,
validators and report generators in `tools/asset-pipeline/`, `tools/validators/`
and `tools/reports/` by `tools-programmer` (the `tools/` rows of
`.claude/docs/custom-engine-layout.md`). The editor is `editor-code.md`'s, not
this rule's. On any other engine, ignore this file.

## Cook output is deterministic

- The same inputs, settings, target platform and cooker version produce
  byte-identical output. Nothing in the output depends on the time, the machine,
  the user, an absolute path, hash-map iteration order, thread completion order
  or uninitialised padding bytes
- Inputs are processed in a sorted, stated order; parallel cooks partition the
  work and merge results in that order, never in completion order
- A test cooks the same inputs twice (on CI, on two workers where the farm
  allows) and compares output hashes; a mismatch fails the build
- The cache key of a cooked artefact is a content hash of every input that can
  change the output: source bytes, transitive dependencies, cooker version,
  target platform and cook settings. A key that misses an input serves stale
  data
- Packaging is part of the cook: the same cooked input gives a byte-identical
  package, assets keep a stable order and, where the layout allows, unchanged
  offsets, and no timestamp or original file name is written into a pack.
  SteamPipe, for one, patches by re-sending only the roughly 1 MB chunks that
  changed, and its guidance warns that pack files that move or re-stamp
  unchanged data make updates much larger than necessary

## Formats and schemas are versioned

- Every cooked format carries a magic number and a format version; changing the
  layout bumps the version, and the runtime reader changes in the same change
  (`streaming-io-code.md`)
- Trace and telemetry event names, fields and units (Tracy zones, the engine's
  own trace format, benchmark output) are a schema with a version. Renaming or
  re-unitising an event bumps it, because `/benchmark-report`, dashboards and
  baselines read those names
- Source assets are untrusted input to a cooker: sizes, counts and offsets are
  validated before use, and a bad file is a reported error naming the file

## Dependencies

- Cookers and command-line tools link runtime and tools libraries only, never
  `engine/editor/`, unless an ADR says this tool runs inside the editor. A
  cooker runs headless on a build machine with no window, GPU or user
- A tool that needs a GPU (texture compression, shader compile) says so in its
  `--help` and fails with a clear error when none is present

## Command-line contract

- Exit code 0 means every requested item succeeded. Any error exits non-zero,
  with distinct, documented codes (for example 1 failure, 2 usage error, 3
  warnings treated as errors). A tool never logs an error and exits 0
- Results meant for machines go to stdout in a stated format (`--json`); logs
  and progress go to stderr
- Flags are stable: a renamed flag keeps the old name as a deprecated alias for
  one release, as `engine-api-code.md`'s deprecation rule says for APIs

## Examples

**Correct** — C++23:

```cpp
enum class exit_code : int { ok = 0, failed = 1, usage = 2, warnings_as_errors = 3 };

std::vector<std::filesystem::path> cook_order(std::vector<std::filesystem::path> inputs)
{
    std::ranges::sort(inputs);   // output order never depends on directory iteration
    return inputs;
}
```

Rust:

```rust
use std::collections::BTreeMap;
use std::process::ExitCode;

pub struct CookManifest {
    pub entries: BTreeMap<String, [u8; 32]>, // sorted keys: stable output order
}

pub fn exit_status(errors: usize, warnings: usize, warnings_as_errors: bool) -> ExitCode {
    if errors > 0 { ExitCode::from(1) }
    else if warnings > 0 && warnings_as_errors { ExitCode::from(3) }
    else { ExitCode::SUCCESS }
}
```

**Incorrect**:

```cpp
header.cooked_at = std::time(nullptr);                 // VIOLATION: timestamp in output
for (auto& [name, blob] : assets_by_name) write(blob); // VIOLATION: std::unordered_map order in output
catch (const std::exception& e) { log_error(e.what()); return 0; } // VIOLATION: failure exits 0
```

```rust
for (name, blob) in &self.assets { out.write_all(blob)?; } // VIOLATION: HashMap order in output
use engine_editor::selection::Selection;                    // VIOLATION: cooker depends on the editor
```
