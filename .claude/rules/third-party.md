---
paths:
  - "third_party/**"
  - "external/**"
  - "vendor/**"
---

# Third-Party Code Rules

Applies only when `engine.name` is `Custom` in `project.yaml` (the project
builds its own engine); on any other engine, ignore this file.
Code in these folders is someone else's. Every new dependency and every update
is reviewed by `security-engineer`; build integration is
`asset-build-tooling-engineer`'s; adding a dependency to the engine
(`engine.name: Custom`) is an ADR option approved by `chief-engine-architect`.
Whether a license fits the project's distribution is the user's decision, with
legal advice where needed — agents report the license, they do not rule on it.

## What every dependency carries

- Its own folder, `third_party/<name>/`, with the upstream license file
  (`LICENSE`, `COPYING`, `NOTICE`) exactly as shipped
- A metadata file (`third_party/<name>/UPSTREAM.md`, or the project's chosen
  name) with: name, version, source URL, the exact commit or the archive's
  SHA-256, SPDX license id, date imported, and who reviewed it
- An archive or a binary is checked against its published hash on import; a
  hash that cannot be found is written `NOT SOURCEABLE` and the import waits
  for the user

## Never edit in place

- Upstream files stay byte-identical to the pinned source. A local change is a
  patch file in `third_party/<name>/patches/NNNN-<what>.patch`, applied by the
  build or the import script, with its reason and its upstream status (sent,
  merged, local-only) in the metadata file
- An update re-imports the new pinned source, re-applies the patches, and
  updates the metadata, all in one change. Never a partial copy over the old
  tree
- `vendor/` written by `cargo vendor` (or another tool) is regenerated with that
  tool, never hand-edited; Rust overrides go through `[patch]` in `Cargo.toml`
- Formatters, linters and code-marker scans skip these folders; warnings in
  them are silenced at the include boundary (`SYSTEM` includes), not fixed by
  editing the files

## Containment

- Engine and game code reach a dependency through the one module that wraps it;
  its types do not appear in an engine public header unless an ADR says so
- Prebuilt binaries are a last resort, when source is not available, and
  carry the same metadata plus their hash
- Console SDKs and any material under NDA are never committed here
  (`engine-code.md`)
- Copyleft licenses (GPL, LGPL, AGPL, MPL) and licenses with field-of-use or
  attribution terms are flagged to the user before import, never after

## Examples

**Correct**:

```text
third_party/meshoptimizer/
  LICENSE.md                         # upstream, unchanged
  UPSTREAM.md                        # version, URL, commit, SHA-256, SPDX: MIT, reviewer
  patches/0001-disable-simd-on-arm32.patch
  src/ …                             # byte-identical to the pinned commit
```

```cmake
add_subdirectory(third_party/meshoptimizer SYSTEM)  # its warnings are not ours (CMake 3.25+)
target_link_libraries(engine_assets PRIVATE meshoptimizer)
```

**Incorrect**:

```cpp
// third_party/meshoptimizer/src/simplifier.cpp
-    return error * scale;
+    return error * scale * 0.5f;   // VIOLATION: edited in place, no patch file, lost on the next update
```

```text
vendor/zstd/                       # VIOLATION: no license file, no version, no source URL
```
