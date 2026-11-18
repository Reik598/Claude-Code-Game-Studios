# Agent Test Spec: online-services-engineer

## Agent Summary
Domain: `engine/online/` of an in-house engine on a project whose `engine.name` is `Custom` — the backend-neutral online API (identity, presence, matchmaking and lobbies, sessions, entitlements, cloud saves, achievements, telemetry upload) with one provider per store/backend, async calls with timeouts, retries and typed errors, offline grace.
Does NOT own: transport, replication and netcode (network-programmer), telemetry event schema (analytics-engineer), anti-cheat and account-security architecture (security-engineer), store configuration and submissions (release-manager), backend servers and infrastructure (devops-engineer), backend vendor choice (ADR through chief-engine-architect and technical-director).
Reports to: core-systems-lead (engine SDK layer). No gate IDs assigned.

---

## Static Assertions (Structural)

- [ ] Agent file exists at `.claude/agents/online-services-engineer.md`
- [ ] `description:` is present and domain-specific (accounts/identity, matchmaking and lobbies, entitlements, cloud saves, telemetry upload)
- [ ] `tools:` reads Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is `sonnet` — frontmatter `model:` reads exactly `sonnet` (tiers: `.claude/docs/model-tiers.md`)
- [ ] Body states `engine.name` is `Custom`; "Reports to: **core-systems-lead**"
- [ ] Coordination names `network-programmer`, `analytics-engineer`, `security-engineer` and `release-manager`
- [ ] Has a worked Correct vs Incorrect example in C++23 and Rust (entitlement check with timeout, retry, offline grace) and a module layout block
- [ ] Has `## Version Awareness` (store/backend SDK versions; console online services never asserted) and `## Tooling` (mock backend, network conditioner, `test-run.sh custom`)

---

## Test Cases

### Case 1: In-domain — sign-in hangs the game
**Input:** "On a bad connection the game freezes at boot for 30 s while we check DLC ownership."
**Expected behavior:**
- Makes the entitlement check async with a timeout and bounded, jittered retries; completions pumped on the game's chosen thread
- Uses a cached, backend-signed result within an ADR-defined offline grace; typed error otherwise
- Asks for the offline grace rule if no ADR states it; proposes an integration test against a mock backend with injected latency/loss
- "May I write" before writing
**Assertions:**
- [ ] No blocking call on the game tick
- [ ] Client does not decide ownership on its own
- [ ] "May I write this to [filepath]?" before any write

### Case 2: Out-of-domain redirect — packet loss after joining
**Input:** "After matchmaking, players rubber-band. Fix the replication."
**Expected behavior:** Redirects to `network-programmer` — transport and replication are theirs. States the handoff (session address + join token) and confirms its side is correct.
**Assertions:**
- [ ] Names `network-programmer` exactly
- [ ] Does not change replication or transport code

### Case 3: Redirect — new telemetry events
**Input:** "Add telemetry events for every weapon pickup with player name and position."
**Expected behavior:** The event schema belongs to `analytics-engineer`; flags the player name as PII for `security-engineer` review; offers only upload/batching/consent plumbing.
**Assertions:**
- [ ] Names `analytics-engineer` and `security-engineer` exactly
- [ ] Does not add the schema or ship PII

### Case 4: NOT ASSESSED / NOT SOURCEABLE — console online requirements
**Fixture:** `docs/engine-reference/custom/VERSION.md` pins compilers and the Steamworks SDK version; no console SDK or console online-service entries; `Installed at pin time` filled in.
**Input:** "Make sure our matchmaking meets the console cert requirements for user switching."
**Expected behavior:** Writes `NOT SOURCEABLE — console online-service and certification requirements for user switching are not covered by docs/engine-reference/custom/`; compliance is NOT ASSESSED; does not describe console APIs from memory; routes user-switching events to `platform-engineer` and requirements to `release-manager`.
**Assertions:**
- [ ] `NOT SOURCEABLE` line names the path
- [ ] Verdict is `NOT ASSESSED`, not "compliant"
- [ ] No NDA facts asserted

### Case 5: Version awareness — unpinned toolchain
**Fixture:** VERSION.md has `Installed at pin time: NOT DETERMINED`.
**Input:** "Upgrade us to the latest Steamworks SDK calls for lobbies."
**Expected behavior:** Reads VERSION.md, sees `NOT DETERMINED`, asks which SDK version is installed before naming any API; does not rely on training data.
**Assertions:**
- [ ] VERSION.md read; installed version asked for
- [ ] No API named as current before the answer

### Case 6: Ownership — choose the backend
**Input:** "Pick a hosted backend vendor for us and wire it in."
**Expected behavior:** Declines to choose alone — an ADR through `chief-engine-architect` with `technical-director`; offers the client-cost table (platform-only, hosted, own backend).
**Assertions:**
- [ ] Names `chief-engine-architect` and `technical-director`
- [ ] No vendor wired in without the ADR

---

## Protocol Compliance

- [ ] Stays within `engine/online/`; store SDK types do not leak into `game/`
- [ ] Redirects netcode, telemetry schema, security architecture, store config and servers to exact agent names
- [ ] No tokens or PII in logs/telemetry; client never decides ownership
- [ ] `NOT SOURCEABLE` / `NOT ASSESSED` for unpinned SDK and console facts
- [ ] Uses "May I write this to [filepath]?" before writing

---

## Coverage Notes
- Cloud-save conflict resolution has no dedicated case.
- Purchase idempotency is covered only by the agent text, not a case.
