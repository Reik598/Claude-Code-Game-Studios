---
paths:
  - "engine/**"
  - "crates/**"
---

# Engine-Wide Rules (every engine module)

For a project that builds its own engine (`engine.name: Custom`): these rules
hold in every module under `engine/` or `crates/`, beside the module's own rule
in `.claude/docs/custom-engine-layout.md`. On any other engine, ignore this file.

- Module dependencies follow the ADRs in `docs/architecture/`; `engine/` never
  includes or uses anything from `game/`
- Facts about the toolchain or a graphics API come from
  `docs/engine-reference/custom/`; a fact not there is written
  `NOT SOURCEABLE — <what> is not covered by docs/engine-reference/custom/`
- No public header (`engine/<module>/include/`) or public crate API outside
  `engine/platform/` exposes an OS or SDK type (`HWND`, `ID3D12Device*`,
  `MTLDevice`, a console SDK handle)

## Public API and deprecation (`engine/<module>/include/`, public crate items)

- A public API is removed or changed incompatibly only after a deprecation
  window: it is first marked `[[deprecated("use X; removed in N+2")]]` (or the
  engine's `ENGINE_DEPRECATED(version, msg)` macro) in C++, or
  `#[deprecated(since = "…", note = "use X")]` in Rust, and stays for the
  number of engine releases an ADR sets
- The deprecation message names the replacement and the release that removes
  it; a deprecation with no replacement says so
- Every breaking or deprecating change has a migration note written with
  `engine-technical-writer`, and goes through `/api-review` with sign-off from
  `chief-engine-architect`
- Deprecation warnings stay warnings inside `engine/` and `game/`; they are
  not silenced, they are fixed before the removal release

## Examples

**Incorrect** (an SDK type in a public header):

```cpp
// engine/rhi/include/rhi/device.hpp
#include <d3d12.h>                                // VIOLATION: SDK type leaks through a public header
ID3D12Device* native_device();                    // (fine in engine/rhi/src/d3d12/, backend-private)
```
