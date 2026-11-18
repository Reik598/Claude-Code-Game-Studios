# Engine table

`engines.tsv` holds one row per engine `engine.name` can name: Godot, Unity,
Unreal, Web and Custom. The hooks, helpers and skills read it instead of keeping their
own copy of each engine's folders.

**Custom** is a project that builds its own engine (`engine/`) and the game on
it (`game/`) in one repository, so its code root is `.` (the project root, with
the framework's folders, the build output — `build/`, `target/`, `out/` — and
vendored code — `third_party/`, `external/`, `vendor/` — skipped; unlike every
other engine, it scans `tools/`, which holds the editor in `tools/editor/`). Its four commands are `-`: they depend on whether the engine is C++
(CMake and CTest) or Rust (Cargo), so `/setup-engine custom` writes them to
`commands.*` in `project.yaml`. The framework ships no engine code for it.

| Column | What it is | Read by |
|---|---|---|
| `engine` | The `engine.name` value. Matched in any case; any name starting with "unreal" is the Unreal row | every reader |
| `code_root` | Where the game's code lives, unless `engine.code_root` says otherwise | `resolve_code_root` (`yaml-helper.sh`), `project-state.sh`, `write-guard.sh`, `content-count.sh` |
| `test_root` | Where the tests live, unless `engine.test_root` says otherwise | `resolve_test_root` (`yaml-helper.sh`) |
| `asset_root` | Where the assets live | `asset-scan.sh`, `content-count.sh` |
| `run`, `build`, `test`, `smoke` | The default commands. `-` where the command needs something only `/setup-engine` can ask for (the editor's path, a build target) | `test-run.sh` (`test`, when `commands.test` is unset) |

Skills read a row with `resolve_config --keys engine_row`. The files listed above
read the table through one reader, `.claude/scripts/engine-row.awk`.
`test-scaffold.sh` does not read it: it writes its own copy of each engine's test
paths, so a change to `test_root` here must also be made there.

**Format.** Tab-separated, LF line ends, a header row first. A `-` is an empty
cell; no cell is left blank. Read it with `awk -F'\t'`: a bash `IFS` read merges
empty fields.

## `web/`

The files a new web project starts from. `scaffold/` holds every file
`/setup-engine web` copies into the project root, through
`.claude/scripts/web-scaffold.sh` (which never overwrites a file); its
`playwright.config.ts` is also the one `/test-setup` writes
(`test-scaffold.sh web`). `web/README.md` says what each file is for.
