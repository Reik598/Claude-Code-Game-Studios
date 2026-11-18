---
paths:
  - "/CMakeLists.txt"
  - "/CMakePresets.json"
  - "/Cargo.toml"
  - "/Cargo.lock"
  - "/rust-toolchain.toml"
  - "cmake/**/*.cmake"
  - "engine/**/CMakeLists.txt"
  - "engine/**/*.cmake"
  - "engine/**/Cargo.toml"
  - "crates/**/Cargo.toml"
  - "crates/**/*.cmake"
  - "game/**/CMakeLists.txt"
  - "game/**/*.cmake"
  - "game/**/Cargo.toml"
---

# Build File Rules

Applies only when `engine.name` is `Custom` in `project.yaml` (the project
builds its own engine); on any other engine, ignore this file. Owned by
`asset-build-tooling-engineer`; CI, the build matrix and
the build farm by `devops-engineer`. A change to a module's dependencies follows
the ADRs in `docs/architecture/` and goes to `chief-engine-architect` when it
adds an edge between modules.

## CMake

- Targets, not directories: `target_include_directories`,
  `target_compile_definitions`, `target_compile_options`,
  `target_link_libraries` with `PUBLIC`/`PRIVATE`/`INTERFACE`. Never
  `include_directories`, `add_definitions`, `link_libraries` or an edit to
  `CMAKE_CXX_FLAGS` in a `CMakeLists.txt`
- Shared warning, sanitizer and hardening flags live on an `INTERFACE` target
  (`engine_warnings`) or in a preset or toolchain file, and modules link it
- The language level is `target_compile_features(<t> PUBLIC cxx_std_23)` with
  `CMAKE_CXX_EXTENSIONS OFF`; exceptions and RTTI settings follow the ADR
- Every configuration `commands.build` and `commands.test` use (debug,
  release, shipping, each sanitizer) is a preset in `CMakePresets.json`.
  `CMakeUserPresets.json` is per-developer and gitignored
- A dedicated server, where the project has one (`network-programmer`'s
  Dedicated Server Target), is a `server` configure preset that inherits the
  shared base preset and changes only what the server needs, such as the null
  RHI and audio backends through its cache variables. A CMake preset inherits
  every field of the presets it names, except a few such as its name, and may
  override them
- Sources are listed explicitly; `file(GLOB …)` for sources is not used, since
  a new file is missed until someone reconfigures
- A module's public headers are only in `engine/<module>/include/`; anything
  else is `PRIVATE`. A target links only what it uses

## Cargo

- One workspace; `members` names the actual crate roots (directories with a
  `Cargo.toml`), never a glob that also matches non-crate folders
- `edition`, `rust-version` and shared dependency versions are set once in
  `[workspace.package]` and `[workspace.dependencies]`; crates use
  `dep.workspace = true`. A virtual workspace sets `resolver` explicitly
- Features are additive: enabling one never removes behaviour. Library crates
  keep `default` minimal; `editor`, profiling and dev features are never in a
  runtime crate's `default` (`editor-code.md`)
- A dedicated server in Cargo: features belong to a package, not to a binary,
  so the server is either its own package in the workspace with its own
  features, or a `[[bin]]` that lists `required-features`, which Cargo skips
  unless those features are enabled. Cargo builds a dependency with the union
  of the features that every package using it enables, so when the server's
  null backends are features, the server is built in a `cargo build` of its
  own, never in the same invocation as the client
- Profiles change codegen only (optimisation, LTO, debug info, `panic`); a
  shipping profile is defined and its settings come from an ADR
- `build.rs` is deterministic, makes no network calls, and declares every input
  with a `rerun-if-changed` instruction

## Pinned, reproducible inputs

- `Cargo.lock` is committed and CI builds with `--locked`; the toolchain is
  pinned in `rust-toolchain.toml`. For C++, the compiler and CMake versions are
  in `docs/engine-reference/custom/VERSION.md`
- External sources are pinned to an exact commit or a hashed archive:
  `FetchContent` with a full `GIT_TAG` commit hash or `URL` plus `URL_HASH`, a
  vcpkg manifest with a `builtin-baseline`, a git dependency with `rev`. Never
  a branch name. Vendored code follows `third-party.md`
- A new dependency is an ADR option reviewed by `security-engineer`
  (`third-party.md`), never added in passing

## Build time is budgeted

- Clean and incremental build times on the reference machine have budgets in
  an ADR, are measured in CI, and a change that exceeds them is fixed or
  justified in an ADR
- Precompiled headers (`target_precompile_headers`, `PRIVATE`) and unity builds
  (`UNITY_BUILD`) are per-target choices. CI also builds once without them, so
  a missing include or a symbol clash between files is caught
- Include hygiene is checked by a tool (include-what-you-use or
  clang-include-cleaner, chosen in an ADR); a header compiles on its own

## Examples

**Correct** — CMake:

```cmake
add_library(engine_memory STATIC src/arena.cpp src/pool.cpp)
target_include_directories(engine_memory PUBLIC include)
target_compile_features(engine_memory PUBLIC cxx_std_23)
target_link_libraries(engine_memory PUBLIC engine_core PRIVATE engine_warnings)
```

Cargo (`Cargo.toml` at the root):

```toml
[workspace]
resolver = "2"
members = ["engine/core", "engine/memory", "engine/jobs", "game"]

[workspace.package]
edition = "2021"
rust-version = "1.85"

[workspace.dependencies]
engine-core = { path = "engine/core" }
```

**Incorrect**:

```cmake
include_directories(${CMAKE_SOURCE_DIR}/engine)   # VIOLATION: directory-wide, every target sees everything
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3")      # VIOLATION: global flag edit
file(GLOB SRC src/*.cpp)                           # VIOLATION: new files missed until reconfigure
FetchContent_Declare(fmt GIT_REPOSITORY https://github.com/fmtlib/fmt GIT_TAG master) # VIOLATION: branch, not a pin
```

```toml
[workspace]
members = ["engine/*"]                             # VIOLATION: also matches non-crate folders

[dependencies]
gpu-alloc = { git = "https://example.com/gpu-alloc", branch = "main" } # VIOLATION: unpinned
```
