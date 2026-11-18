---
paths:
  - "tests/**"
  - "Assets/Tests/**/*.cs"
  - "Source/**/Tests/**/*.{h,cpp}"
  - "engine/**/tests/**"
  - "game/**/tests/**"
  - "crates/**/tests/**"
  - "engine/**/benches/**"
  - "crates/**/benches/**"
  - "game/**/benches/**"
---

# Test Standards

- Test naming follows the engine's language — every name says the scenario and
  the expected result:
  - **Godot (gdUnit4):** file `[system]_[feature]_test.gd`, function
    `test_[scenario]_[expected]`
  - **Unity (NUnit):** class `[System]Tests` in a file of the same name, method
    `[Scenario]_[Expected]` in PascalCase
  - **Unreal (Automation):** class `F[System][Scenario]Test` — one per test:
    each `IMPLEMENT_SIMPLE_AUTOMATION_TEST` defines its class, so a second test
    reusing a name fails to link — test name
    `<Project>.[System].[Scenario]` — the project's test command,
    `Automation RunTests <Project>.`, runs every test whose name contains
    `<Project>.` (a substring match, not a prefix). `<Project>.` is the root
    that filter in `commands.test` uses: the project name, or the distinct root
    `/setup-engine` chose when the project's name is also an engine area
    (`Audio`, `Core`, `Input`, …) — name tests under whichever it is
  - **Web (Vitest, Playwright):** file `[module].test.ts` under `tests/unit/`
    (Vitest) or `[system].spec.ts` under `tests/integration/` (Playwright),
    test `'[scenario] [expected]'` in plain words —
    `it('keeps the square inside the field')`
  - **Custom, C++ (CTest):** file `[system]_[feature]_test.cpp` under
    `tests/unit/` or `tests/integration/`, case `[scenario]_[expected]`
    (`allocate_past_capacity_returns_null`), each registered with CTest so
    `commands.test` runs it
  - **Custom, Rust (cargo test):** `#[test] fn [scenario]_[expected]()` in the
    crate's `tests/` or a `#[cfg(test)] mod tests`. An inline
    `#[cfg(test)] mod tests` sits in a `src/` file, so this rule is not loaded
    for it by path; the same standards apply
  - **Custom, benchmarks:** `[system]_[feature]_bench` under
    `tests/benchmarks/` or a module's or crate's `benches/`; each states its threshold (time per iteration or per
    frame, against `performance.frame_budget_ms`) and fails when it is exceeded.
    A benchmark with no threshold is a measurement, not a test
  - **Custom, test locations:** module-local `engine/<module>/tests/` and
    `engine/<module>/benches/`, `game/**/tests/` and `game/**/benches/`, a
    crate's `crates/<crate>/tests/` and `crates/<crate>/benches/` are valid
    alongside `tests/unit/` and `tests/integration/`
- Every test must have a clear arrange/act/assert structure
- Unit tests must not depend on external state (filesystem, network, database)
- Integration tests must clean up after themselves
- Performance tests must specify acceptable thresholds and fail if exceeded
- Test data must be defined in the test or in dedicated fixtures, never shared mutable state
- Mock external dependencies — tests should be fast and deterministic
- Every bug fix must have a regression test that would have caught the original bug —
  and **you must watch it fail before you trust it.** Run the new test against the
  unfixed code, confirm it fails, then apply the fix and confirm it passes. A
  regression test that has only ever been seen passing is not known to test anything.

  > This is `.claude/rules/skill-authoring.md`'s "a gate you have not watched fail
  > is not a gate", applied to tests. It is written out here because stating the
  > *goal* is not enough. A regression test for an iteration-order defect can use
  > a fixture where no cell takes part in two transfers per tick — it then passes
  > against the very bug it was written for, and looks authoritative doing it. The
  > fixture, not the assertion, is what makes it useless, and only running it
  > against the unfixed code exposes that.

## Examples

**Correct** (proper naming + Arrange/Act/Assert) — Godot, gdUnit4:

```gdscript
extends GdUnitTestSuite

func test_take_damage_reduces_health() -> void:
    # Arrange — auto_free: a Node left alive is an orphan (gdUnit4 exit 101)
    var health: HealthComponent = auto_free(HealthComponent.new())
    health.max_health = 100
    health.current_health = 100

    # Act
    health.take_damage(25)

    # Assert
    assert_int(health.current_health).is_equal(75)
```

Unity, NUnit (`Assets/Tests/EditMode/HealthTests.cs`):

```csharp
using NUnit.Framework;

public class HealthTests
{
    [Test]
    public void TakeDamage_ReducesHealth()
    {
        // Arrange
        var health = new Health(maxHealth: 100);

        // Act
        health.TakeDamage(25);

        // Assert
        Assert.AreEqual(75, health.Current);
    }
}
```

Unreal, Automation (`Source/<Module>/Private/Tests/HealthTest.cpp`):

```cpp
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHealthTakeDamageTest, "<Project>.Health.TakeDamageReducesHealth",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FHealthTakeDamageTest::RunTest(const FString& Parameters)
{
    // Arrange
    FHealthPool Health(100);

    // Act
    Health.TakeDamage(25);

    // Assert
    TestEqual(TEXT("health after 25 damage"), Health.GetCurrent(), 75);
    return true;
}

#endif
```

Custom engine, Rust (`engine/memory`'s crate, `tests/arena.rs`):

```rust
#[test]
fn allocate_past_capacity_returns_none() {
    // Arrange
    let mut arena = FrameArena::with_capacity(64);
    arena.allocate::<[u8; 64]>().unwrap();

    // Act
    let result = arena.allocate::<u8>();

    // Assert
    assert!(result.is_none());
}
```

**Incorrect**:

```gdscript
func test1() -> void:  # VIOLATION: no descriptive name
    var h := HealthComponent.new()
    h.take_damage(25)  # VIOLATION: no arrange step, no clear assert
    assert_bool(h.current_health < 100).is_true()  # VIOLATION: imprecise assertion
```
