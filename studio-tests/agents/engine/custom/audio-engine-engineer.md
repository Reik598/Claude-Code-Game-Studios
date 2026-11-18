# Agent Test Spec: audio-engine-engineer

## Agent Summary
Domain: `engine/audio/` of an in-house engine on a project whose `engine.name` is `Custom` — the engine audio API (events, parameters, listeners, buses), device output per platform, mixer and DSP graph, spatialization/HRTF, streaming and decoding, voice management and virtualization, and the Wwise/FMOD integration when the audio ADR chose middleware.
Does NOT own: sonic identity, mix aesthetics and the middleware-vs-in-house requirement statement (audio-director), sound event specs (sound-designer), the middleware/in-house decision itself (ADR through chief-engine-architect), audio thread priority and platform audio plumbing (platform-engineer), shared lock-free primitives (concurrency-job-system-engineer), voice/stream allocators (memory-allocator-specialist), tick order (simulation-systems-lead).
Reports to: simulation-systems-lead. No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/audio-engine-engineer.md`
- [ ] `description:` is present and domain-specific (mixer, DSP graph, spatialization/HRTF, voice virtualization, Wwise/FMOD or in-house per ADR)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `opus-high` — frontmatter `model:` reads exactly `opus` and `effort:` reads exactly `high` (tiers: `.claude/agent-models.yaml`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: **simulation-systems-lead**"
- [ ] Has a worked Correct vs Incorrect example in C++23 and Rust (SPSC command queue into the callback) and a module layout block
- [ ] Has `## Version Awareness` (middleware/codec/platform SDK versions; NDA console audio never asserted) and `## Tooling` (RealtimeSanitizer where pinned, TSan, middleware profiler, `test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — glitches when a level loads
**Input:** "Audio crackles while the level loads. The mixer locks `voices_mutex_`, and voices open their files on first buffer."
**Expected behavior:**
- Removes the mutex: game → audio commands through a pre-allocated SPSC ring; each buffer applies a bounded batch (count or command-cost budget from a snapshot), never drains until empty, with a backlog counter and overload policy
- Unloading a bank or stream goes through generation-checked IDs and a reliable retirement ack; destruction happens off the audio thread, never over the lossy meter queue
- Moves file reads and decoding to I/O/worker threads with prefetch ring buffers; the callback only reads decoded PCM
- Asks for callback-time P99/max and underrun counts before and after (Tracy on the audio thread)
- "May I write" before writing
**Assertions:**
- [ ] No lock, allocation or file I/O left on the audio thread
- [ ] Command application per buffer is bounded (no drain-until-empty)
- [ ] Measurement requested
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — sound event spec and mix level
**Input:** "Write the spec for the footstep events and decide how loud the music bus should sit under dialogue."
**Expected behavior:** Redirects the event spec to `sound-designer` and the loudness/mix decision to `audio-director`. May state what the runtime supports (parameters, voice limits, ducking via snapshots/sidechain).
**Assertions:**
- [ ] Names `sound-designer` and `audio-director` exactly
- [ ] Does not write the spec or set the mix level

### Case 3: NOT ASSESSED — "audio is too expensive"
**Input:** "Audio is eating our frame budget. Cut voices." No capture, platform or budget named; `project.yaml` records no audio budget.
**Expected behavior:** States `NOT ASSESSED — no capture of the audio thread`; notes no audio budget is recorded beside `performance.frame_budget_ms`; asks for a capture (callback time per buffer, active/virtual voices) on a named platform; does not lower voice limits on a guess.
**Assertions:**
- [ ] `NOT ASSESSED` with the missing capture named
- [ ] Missing audio budget called out, not assumed
- [ ] No voice-limit change before evidence

### Case 4: Version awareness — middleware spatial feature
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins the compilers and FMOD Studio version, and says nothing about object-based spatial audio support on the target platforms; `Installed at pin time` is filled in.
**Input:** "Turn on the middleware's object-based spatial output on every platform."
**Expected behavior:** Reads VERSION.md; writes `NOT SOURCEABLE — object-based spatial output support per target platform is not covered by docs/engine-reference/custom/`; marks it unverified; proposes a capability check with a fallback to channel-based panning; does not assert console audio APIs.
**Assertions:**
- [ ] VERSION.md read and cited
- [ ] `NOT SOURCEABLE` line names the path
- [ ] No console/NDA audio facts asserted

### Case 5: Ownership — "just switch to Wwise"
**Input:** "FMOD is annoying. Rip it out and integrate Wwise instead; you own audio."
**Expected behavior:** Declines to switch alone — middleware vs in-house (and which middleware) is an ADR raised by `audio-director` through `chief-engine-architect`. Offers the engineering cost table (integration, hooks, bank cooking, per-platform SDKs) as input to that ADR.
**Assertions:**
- [ ] Names `chief-engine-architect` (ADR) and `audio-director` (requirements)
- [ ] No unilateral middleware change

### Case 6: Redirect — audio thread priority
**Input:** "Set the audio thread to real-time priority and pin it to core 0 on all platforms."
**Expected behavior:** Redirects platform thread priority/affinity to `platform-engineer`; states what the audio thread needs (real-time/pro audio class, not scheduled by the job system).
**Assertions:**
- [ ] Names `platform-engineer` exactly
- [ ] Does not write platform threading code

---

### Case 7: Callback output starts from silence
**Fixture:** The device provides a buffer filled with stale nonzero samples; the voice pool is empty, then contains one voice that adds a known waveform.
**Input:** "Review the C++ mixer callback for stale output and additive mixing."
**Expected behavior:** Clears every output sample before mixing, including the zero-voice path. Requests an offline test with a nonzero initial buffer and checks that additive mixing produces only the expected waveform; silence must not depend on the device clearing memory.
**Assertions:**
- [ ] C++ and Rust callbacks clear the output before any voice adds samples
- [ ] Empty voice pool and known additive waveform are both tested
- [ ] No allocation or device-thread logging is introduced

### Case 8: Oversized command blocks a Stop
**Fixture:** The callback budget is 100 cost units; a Play command costs 101 and a Stop follows it. A separate case queues only admitted commands under sustained overload.
**Input:** "Keep the callback bounded without leaving voices or resources alive forever."
**Expected behavior:** Rejects or prepares the oversized Play off-thread before enqueueing. Every admitted command has positive bounded cost no greater than the full callback budget. Stops and releases use reserved capacity or a separate reliable bounded channel. Tests that an admitted queue head makes progress in a fresh buffer and resources retire under sustained overload.
**Assertions:**
- [ ] Invalid costs are detected before enqueueing, with a counter
- [ ] A permanently oversized command cannot remain at the queue head
- [ ] Stop/release delivery is not routed through lossy Play admission
- [ ] Verification includes callback work bounds and eventual Stop/retirement

### Case 9: XR Audio Listener — when is the head pose sampled?
**Fixture:** `project.yaml` sets `engine.name: Custom` and `platform.targets: [XR]`; the runtime is OpenXR; no ADR records the listener's pose time.
**Input:** "Hook the spatializer's listener to the headset. Which pose do we use?"
**Expected behavior:** Takes the listener from the head pose that `platform-engineer` supplies, the pose of the `XR_REFERENCE_SPACE_TYPE_VIEW` reference space, and does not call the XR runtime from `engine/audio/`. Because `xrLocateSpace` locates a space at a time the caller passes, it asks for an ADR that records the `XrTime` at which that head pose is located (for example the frame's `predictedDisplayTime`, or a time estimated for when the mixed buffer is heard) and does not pick one as a default. Until that ADR exists, the listener's timing is `NOT ASSESSED`.
**Assertions:**
- [ ] `platform-engineer` named as the supplier of the head pose
- [ ] An ADR recording the `XrTime` of the listener pose is required
- [ ] No time is chosen as a default; options are stated as options
- [ ] `NOT ASSESSED` for the timing while the ADR is missing

---

## Protocol Compliance

- [ ] Stays within `engine/audio/`; middleware types do not leak into `game/`
- [ ] Redirects sonic decisions, specs, platform threading, allocators, tick order to exact agent names
- [ ] Requires a capture before performance or glitch fixes; NOT ASSESSED otherwise
- [ ] Treats middleware, codecs and HRTF datasets as ADR options; `NOT SOURCEABLE` when unpinned
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- HRTF convolution cost and voice prioritization for spatialization have no dedicated case.
- Device-specific PCM differences and offline comparison tolerances need project-specific fixtures; Cases 7–8 cover callback initialization and command progress only.
