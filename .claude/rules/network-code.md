---
paths:
  - "src/networking/**"
  - "Assets/**/{Networking,networking,Network,network}/**/*.cs"
  - "Source/**/{Networking,networking,Network,network}/**/*.{h,cpp}"
  - "engine/net/**"
  - "engine/online/**"
  - "game/src/net/**"
  - "crates/net/**"
  - "crates/online/**"
---

# Network Code Rules

- Server is AUTHORITATIVE for all gameplay-critical state — never trust the client
- All network messages must be versioned for forward/backward compatibility
- Client predicts locally, reconciles with server — implement rollback for mispredictions
- Handle disconnection, reconnection, and host migration gracefully
- Rate-limit all network logging to prevent log flooding
- All networked values must specify replication strategy: reliable/unreliable, frequency, interpolation
- Bandwidth budget: define and track per-message-type bandwidth usage
- Security: validate all incoming packet sizes and field ranges

## On a Custom engine (`engine/net/`, `engine/online/`, `game/src/net/`)

Netcode and replication are owned by `network-programmer`; platform and online
services in `engine/online/` (identity, matchmaking, sessions, entitlements,
cloud saves, telemetry upload) by `online-services-engineer`, which reports to
`core-systems-lead` for the engine SDK layer.

- No secrets in code, config or data: API keys, signing keys, backend
  credentials and tokens come from the platform's secure storage or the
  environment at run time, never from the repository
- Every connection to a backend uses TLS with certificate validation on;
  disabling validation is not a debug option that can ship
- Every remote call has a timeout, and retries use exponential backoff with
  jitter and a retry cap. A failed call is a handled state the game can show,
  not a hang
- Platform and backend services sit behind one engine interface in
  `engine/online/`; game code never calls a platform SDK or a vendor backend
  SDK directly. Which backend is used is an ADR option
- Incoming packets are untrusted input: parse with bounds-checked readers into
  value types, as `streaming-io-code.md` requires for files

```cpp
auto result = co_await online_.call(endpoint::matchmake, request,
                                    {.timeout = cfg.timeout, .retry = backoff{cfg.base, cfg.max_attempts}});
const std::string api_key = "sk_live_...";       // VIOLATION: secret in source
```

```rust
let session = online.call(Endpoint::Matchmake, &req, RetryPolicy::backoff(cfg.base, cfg.max_attempts)).await?;
let client = Client::builder().danger_accept_invalid_certs(true); // VIOLATION: TLS validation off
```

### Replication model and authority

The replication model is the one an Accepted ADR in `docs/architecture/` names.
The first and third bullets of this file (server authority; client prediction
with server reconciliation) apply as written when that model is client-server.
Under deterministic lockstep or rollback, these stand in for them:

- Each peer sends only its inputs and steps the whole simulation itself. A
  received input is still untrusted: it is bounds-checked and checked against
  its frame number before it enters the simulation
- The simulation must give the same result, to the bit, from the same state
  and inputs. Floating-point results can differ between compilers, operating
  systems, instruction sets, and debug and release builds, so the ADR's
  determinism contract (with `physics-simulation-engineer`) names every
  compiler, platform and build configuration that plays together, and a replay
  test proves it
- Peers detect divergence by comparing checksums of the simulation state, and
  a simulation that diverges is a handled out-of-sync state; the ADR sets the
  checksum interval and whether a desync stops or resynchronises the match
- Every peer holds the whole game state, so hidden information can be read
  locally; a game with hidden information records that exposure in the ADR,
  reviewed with `security-engineer`
- Lockstep: a peer cannot step frame *n* until it holds the input for frame
  *n*; the ADR sets the input delay and what a peer does while it waits
- Rollback: the engine predicts the inputs it lacks and runs ahead, and to roll
  back it saves, loads and steps one simulation frame without rendering it.
  Effects and sounds produced while re-simulating are deferred until the
  rollback is finished. A sync test, which re-runs every frame once and
  compares the two resulting states, runs in CI
