---
paths:
  - "engine/audio/**"
  - "crates/audio/**"
---

# Audio Engine Code Rules

For a project that builds its own engine (`engine.name: Custom`). Owned by
`audio-engine-engineer` (reports to `simulation-systems-lead`); sound content
and mix direction stay with `audio-director` and `sound-designer`.
On any other engine, ignore this file.

## The audio callback is real-time

Everything reachable from the device callback (mixer, DSP graph, voice
processing) follows these rules. A miss is an audible glitch, not a slow frame.

- No locks: no mutex, no condition variable, no `std::shared_ptr` copy that
  may free, no waiting on another thread
- No allocation or deallocation: buffers, voices and DSP state are allocated
  before they reach the audio thread. Retired objects go back on a queue and
  are freed by a non-real-time thread
- No I/O: no file reads, no decoding from disk, no network. Streamed sounds are
  read and decoded on a worker thread into a ring buffer the callback consumes
- No logging, no `printf`/`println!`, no assert that formats a message. Errors
  set a counter or flag that a non-real-time thread reports
- No system calls that may block (thread creation, sleeping, memory mapping)

## Communication

- The game talks to the audio thread through lock-free single-producer
  single-consumer command queues of plain-data commands; the audio thread
  answers through another one. Queues are fixed capacity and a full queue is
  counted and reported, never waited on
- The callback applies a bounded number of commands per buffer (a count or
  cost budget from config), never "until the queue is empty". Commands left
  over wait for the next buffer; a backlog that persists is counted, reported,
  and handled by a stated overload policy (coalesce parameter updates, drop
  the lowest-priority starts), never by working past the deadline
- Parameters the callback reads continuously (volumes, positions) are atomics
  or snapshots, smoothed to avoid zipper noise. A snapshot is published with a
  release store and picked up with an acquire load once per callback; the
  writer reuses a snapshot buffer only after the reader has released it (a
  triple buffer, or an index the reader hands back). The callback never waits:
  with no new snapshot it keeps the last one
- Every atomic the callback touches is verified lock-free at compile time
  (`static_assert(std::atomic<T>::is_always_lock_free)`). In Rust,
  `std::sync::atomic` types exist only where the target supports them
  natively — gate 64-bit ones with `#[cfg(target_has_atomic = "64")]` — and a
  generic atomic cell whose fallback is a lock (check its `is_lock_free()`) is
  a lock

## Numerics, latency and voices

- Clear the entire output buffer before additive mixing, including the
  zero-voice path. Device-provided memory may contain stale samples. Offline
  tests start with nonzero output and check silence and a known waveform
- Denormals are flushed where the DSP runs. On an audio thread the engine
  creates, the flush-to-zero / denormals-are-zero mode is set at thread start
  through `engine/platform/`. When the device API owns the callback thread
  (e.g. AAudio calls the data callback "on a real-time thread owned by
  AAudio"), no engine thread-start hook runs there: set the mode at callback
  entry with an RAII guard that restores the previous mode on exit. DSP with
  feedback (filters, reverbs) is tested with silent input for a CPU spike
- The latency budget (buffer size, sample rate, the share of the buffer period
  the callback may use) comes from config and an ADR. The callback's worst-case
  time, not its average, is measured against that share
- Voice counts are capped per category from config. When a cap is reached the
  lowest-priority voice is virtualised or stolen by a stated, deterministic
  rule; nothing spawns voices without a limit
- Middleware (Wwise, FMOD) versus an in-house mixer is an ADR decision; a
  middleware callback into engine code obeys every rule above

## Examples

**Correct** — C++23:

```cpp
static_assert(std::atomic<std::uint32_t>::is_always_lock_free);

void mixer::render(std::span<float> out) noexcept     // audio thread
{
    std::ranges::fill(out, 0.0f);
    command cmd;
    std::uint32_t applied = 0;
    while (applied < max_commands_per_buffer_ && commands_.try_pop(cmd)) { // bounded, wait-free
        apply(cmd);
        ++applied;
    }
    if (applied == max_commands_per_buffer_) backlog_count_.fetch_add(1, std::memory_order_relaxed);
    for (voice& v : active_voices()) v.mix_into(out);  // preallocated voices
    if (underrun_) underrun_count_.fetch_add(1, std::memory_order_relaxed);
}
```

Rust:

```rust
fn render(&mut self, out: &mut [f32]) {
    out.fill(0.0);
    for _ in 0..self.max_commands_per_buffer { // bounded per buffer
        let Some(cmd) = self.commands.pop() else { break }; // SPSC ring
        self.apply(cmd);
    }
    for v in self.voices.iter_mut().filter(|v| v.active) { v.mix_into(out); }
}
```

**Incorrect**:

```cpp
void mixer::render(std::span<float> out)
{
    std::lock_guard lock(mutex_);                      // VIOLATION: lock on the audio thread
    while (commands_.try_pop(cmd)) apply(cmd);         // VIOLATION: unbounded drain, no per-buffer budget
    voices_.push_back(make_voice(pending_));           // VIOLATION: allocation
    log::info("mixed {} voices", voices_.size());      // VIOLATION: logging
}
```

```rust
fn render(&mut self, out: &mut [f32]) {
    let data = std::fs::read("music.ogg").unwrap(); // VIOLATION: file I/O, panics on error
    let cmds = self.shared.lock().unwrap();         // VIOLATION: Mutex on the audio thread
}
```
