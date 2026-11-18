"""Run the actual Rust audio-rule callback against offline buffer fixtures.

Requires rustc on PATH. Run: python studio-tests/check_audio_examples.py
The surrounding types are deterministic stubs, not a realtime/device test.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
RULE = ROOT / ".claude/rules/audio-code.md"
HARNESS = r"""
use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::Cell;
use std::collections::VecDeque;
// Counts heap allocations per thread, so a test can assert that render()
// (the device callback) allocates nothing; the test runner's own threads do
// not count against it.
struct CountingAllocator;
thread_local! { static ALLOCATIONS: Cell<usize> = const { Cell::new(0) }; }
fn count_allocation() { let _ = ALLOCATIONS.try_with(|n| n.set(n.get() + 1)); }
unsafe impl GlobalAlloc for CountingAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 { count_allocation(); unsafe { System.alloc(layout) } }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        count_allocation(); unsafe { System.alloc_zeroed(layout) }
    }
    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        count_allocation(); unsafe { System.realloc(ptr, layout, size) }
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) { unsafe { System.dealloc(ptr, layout) } }
}
#[global_allocator]
static GLOBAL: CountingAllocator = CountingAllocator;
fn allocations_during(f: impl FnOnce()) -> usize {
    let before = ALLOCATIONS.with(|n| n.get());
    f();
    ALLOCATIONS.with(|n| n.get()) - before
}
struct Queue(VecDeque<u8>);
impl Queue { fn pop(&mut self) -> Option<u8> { self.0.pop_front() } }
struct Voice { active: bool }
impl Voice {
    fn mix_into(&mut self, out: &mut [f32]) {
        for sample in out { *sample += 0.25; }
    }
}
struct Mixer {
    max_commands_per_buffer: usize,
    commands: Queue,
    voices: Vec<Voice>,
    applied: usize,
}
impl Mixer {
    fn apply(&mut self, _: u8) { self.applied += 1; }
    CALLBACK
}
fn mixer(active: bool) -> Mixer {
    Mixer { max_commands_per_buffer: 2,
            commands: Queue(VecDeque::from([1, 2, 3])),
            voices: vec![Voice { active }], applied: 0 }
}
#[test]
fn empty_voice_pool_outputs_silence() {
    let mut mixer = mixer(false);
    mixer.voices.clear();
    let mut out = [7.0; 8];
    mixer.render(&mut out);
    assert_eq!(out, [0.0; 8]);
}
#[test]
fn additive_voice_has_no_stale_samples() {
    let mut mixer = mixer(true);
    let mut out = [7.0; 8];
    mixer.render(&mut out);
    assert_eq!(out, [0.25; 8]);
    mixer.render(&mut out);
    assert_eq!(out, [0.25; 8]);
}
#[test]
fn render_does_not_allocate() {
    for active in [false, true] {
        let mut mixer = mixer(active);
        let mut out = [7.0; 8];
        assert_eq!(allocations_during(|| mixer.render(&mut out)), 0, "render() allocated");
    }
}
#[test]
fn callback_obeys_command_limit() {
    let mut mixer = mixer(false);
    mixer.render(&mut [7.0; 8]);
    assert_eq!(mixer.applied, 2);
    assert_eq!(mixer.commands.0.len(), 1);
}
"""


def main():
    compiler = shutil.which("rustc")
    if compiler is None:
        raise SystemExit("NOT ASSESSED: rustc is required for audio snippet checks")
    correct = RULE.read_text(encoding="utf-8").split("**Incorrect**", 1)[0]
    callback = re.search(r"```rust\n(.*?)\n```", correct, re.S).group(1)
    with tempfile.TemporaryDirectory(prefix=".audio-rule-", dir=ROOT / "studio-tests") as temp:
        source = Path(temp) / "callback.rs"
        binary = Path(temp) / "callback-tests.exe"
        source.write_text(HARNESS.replace("CALLBACK", callback), encoding="utf-8")
        subprocess.run([compiler, "--edition", "2021", "--test", str(source),
                        "-o", str(binary)], check=True, timeout=60)
        subprocess.run([str(binary)], check=True, timeout=30)


if __name__ == "__main__":
    main()
