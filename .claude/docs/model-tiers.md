# Model Tier Assignment

> ### When a skill's `model:` is used — skills only
>
> On Claude Code 2.1.287: when it is used, a skill's `model:` overrides the
> session model for the rest of the turn the skill runs in, and your next prompt
> returns to the session model. Whether it is used depends on how the skill
> starts:
>
> | How the skill starts | Is `model:` used? |
> |---|---|
> | You type `/skill-name` in Manual (`default`) mode | Yes |
> | You type `/skill-name` in auto mode | `haiku`: no — auto mode does not support Haiku, so the session keeps its model. `sonnet` and `opus`: not tested on 2.1.287 |
> | Claude starts the skill itself, through the Skill tool | No — the session model runs it |
> | The skill has `context: fork` | Yes, typed or through the Skill tool — it moves only the fork |
>
> Two things follow:
>
> - **An `opus` skill costs more in a Sonnet session.** Typing
>   `/architecture-review`, `/gate-check` or `/review-all-gdds` in Manual mode
>   moves that turn to Opus.
> - **A `haiku` skill saves nothing in auto mode** (this project's settings start
>   terminal sessions in Manual, but a user can switch) — or when Claude starts
>   it. Never tell a user a `haiku` tier is saving them money.
>
> Because the override ends at your next prompt, a skill that stops to ask you
> something in chat finishes on the session model after you answer.
>
> **This does NOT apply to agents.** `model:` in `.claude/agents/*.md` is a
> different mechanism, spawned as a separate session rather than executed inline,
> and Claude Code documents it as applied: it is second in the subagent model
> order, after a `model` Claude passes for one invocation. See the agent section
> below.

Skills and agents are assigned tiers by task complexity. A tier is written as
the alias `model:` takes, never as a model ID: Claude Code resolves each alias
to the current model in that family, so this table does not change when a new
model ships.

| Tier | `model:` | When to use |
|------|----------|-------------|
| **Haiku** | `haiku` | Read-only status checks, formatting, simple lookups — no creative judgment needed |
| **Sonnet** | `sonnet` | Implementation, design authoring, analysis of individual systems — default for most work |
| **Opus** | `opus` | Multi-document synthesis, high-stakes phase gate verdicts, cross-system holistic review |
| **Session** | `inherit` | Agents only, through a `session` override in `.claude/agent-models.yaml` — runs on the session's model and effort; no agent uses it by default |

Skills with `model: haiku` (6): `/next-step`, `/onboard`, `/project-stage-detect`,
`/scope-check`, `/sprint-status`, and `/help`, the old name of `/next-step`

> `/help`, `/settings` and `/changelog` are the old names of `/next-step`,
> `/project-settings` and `/write-changelog`. Each carries the
> `model:` of the skill it points to: typed as `/help`, the old name runs on its
> own pin, and it then starts the new skill in the same turn.
>
> `/patch-notes` and `/write-changelog` are `sonnet`, not `haiku`: both produce
> **player-facing** copy and need judgement the cheapest tier is defined as not
> doing. Full reasoning in each skill's own header.
>
> `/project-settings` was moved off `haiku` for the same reason. It does not only read
> and format — it resolves every leaf with provenance and then compares the
> configured rigor against the project's observable working practice. That is
> synthesis, which is what the Haiku row is defined as excluding.

Skills with `model: opus` (3): `/architecture-review`, `/gate-check`, `/review-all-gdds`

All other skills are Sonnet. When creating a new skill, assign Haiku if it only
reads and formats; assign Opus if it must synthesize 5+ documents with
high-stakes output; otherwise write `model: sonnet` explicitly. Every skill
declares a tier except `/prototype`, which has no `model:` line, so it runs on
the session's model. Whether the tier takes effect depends on how the skill starts
(see the table at the top of this file).

**Agent model tiers.** Every agent's model and effort come from one table,
`.claude/agent-models.yaml` (fix plan AM38). Claude Code reads them only from
each agent's frontmatter, so `bash .claude/scripts/agent-models.sh sync` writes
them there and `check` lists any difference. A tier follows what the role's
file does and which skills and gates start it, not the role's name; the table's
comments say which way a role would move and on what. The default table assigns:

- **opus · high (21):** `creative-director`, `technical-director`, `producer`, `lead-programmer`, `chief-engine-architect`, `core-systems-lead`, `rendering-lead`, `simulation-systems-lead`, `memory-allocator-specialist`, `concurrency-job-system-engineer`, `rhi-backend-engineer`, `render-graph-specialist`, `audio-engine-engineer`, `physics-simulation-engineer`, `ecs-dod-architect`, `engine-programmer`, `network-programmer`, `security-engineer`, `godot-gdextension-specialist`, `unity-dots-specialist`, `ue-replication-specialist`. Final
  cross-domain verdicts, and work whose errors are subtle and costly:
  concurrency, lock-free code, memory, GPU submission, real-time audio,
  determinism, netcode and security. The escalation ladder reacts only to
  failures it can see, so these roles start high.
- **opus · medium (9):** `game-designer`, `economy-designer`, `narrative-director`, `art-director`, `qa-lead`, `godot-specialist`, `unity-specialist`, `unreal-specialist`, `editor-architect`. Judgement
  across several documents that a gate or lead reviews; the engine primaries
  are the only engine reviewer in `/code-review` and validate each ADR before
  it is saved.
- **sonnet · high (32):** `systems-designer`, `level-designer`, `world-builder`, `writer`, `technical-artist`, `audio-director`, `ux-designer`, `accessibility-specialist`, `localization-lead`, `live-ops-designer`, `xr-experience-designer`, `qa-tester`, `release-manager`, `gameplay-programmer`, `ai-programmer`, `ui-programmer`, `performance-analyst`, `analytics-engineer`, `unity-addressables-specialist`, `ue-gas-specialist`, `platform-engineer`, `world-streaming-engineer`, `online-services-engineer`, `asset-build-tooling-engineer`, `shader-pipeline-engineer`, `graphics-features-engineer`, `vfx-runtime-engineer`, `animation-systems-engineer`, `scripting-runtime-engineer`, `level-editor-engineer`, `cinematics-sequencer-engineer`, `engine-technical-writer`. Bounded analysis and
  implementation, checked by a lead or tests.
- **sonnet · medium (15):** `lighting-artist`, `cinematic-designer`, `sound-designer`, `community-manager`, `tools-programmer`, `devops-engineer`, `prototyper`, `godot-csharp-specialist`, `godot-gdscript-specialist`, `godot-shader-specialist`, `unity-shader-specialist`, `unity-ui-specialist`, `ue-blueprint-specialist`, `ue-umg-specialist`, `editor-ui-framework-engineer`. Execution inside one
  API, content written to a brief, and checklist work.
- **haiku (0):** no agent. The Haiku row above is for read-only lookups and
  formatting; every agent drafts, writes or judges. Building CI pipelines and
  writing player-facing text are Sonnet work, as they are for `/patch-notes`.

No agent uses `model: inherit` by default, and every agent sets `effort:`.
Claude Code applies the session's effort only to a subagent on the session's
own model, so an agent without `effort:` on another model did not get the
session's level, and nobody chose the level it got. To give one role the session's model and
effort again, add `<agent>: session` under `overrides:` in the table and run
`sync`. Another tier, `fable-high` for example, works the same way.

When a subagent cannot finish, the session that started it may start it again
one tier up: `.claude/docs/escalation-ladder.md`. The tiers, in the table's
order, are that ladder.

A pin gets that model's context window, whatever the session runs. On the
Anthropic API `sonnet` currently resolves to Sonnet 5.5 and `haiku` to Haiku
5.5, both with a 1M window (Claude Code 2.1.304, 2026-10-21), so neither pin is
smaller than a 1M session there; behind an LLM gateway a pin can resolve to an
older model with a smaller window. A subagent starts from
the brief it is given, not the parent's conversation, so this only matters when
a brief is very large. If a pinned agent does overflow, run every subagent on
the session's model with one line in your `.claude/settings.local.json`
(Claude Code v2.1.257 or later):

```json
{ "env": { "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1" } }
```

It applies to **every** pin, the `opus` agents included: under a Sonnet session
they run on Sonnet too, but each agent's `effort:` still applies; set
`CLAUDE_CODE_EFFORT_LEVEL` as well to run them all at one effort level you
choose.
`CLAUDE_CODE_SUBAGENT_MODEL` alone does not do it: it applies only to agents
that set no model of their own.
