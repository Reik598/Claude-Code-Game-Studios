# Escalation Ladder

When a subagent you started cannot finish its task, you may start it again one
step stronger. This file is that rule. It binds the session that starts an
agent, not the agent: no agent file states it, and escalating never edits a
file under `.claude/agents/`.

## The ladder

The ladder is the `tiers:` list of `.claude/agent-models.yaml`, from lowest to
highest:

| Rung | Model | Effort |
|---|---|---|
| `sonnet-medium` | `sonnet` | `medium` |
| `sonnet-high` | `sonnet` | `high` |
| `opus-medium` | `opus` | `medium` |
| `opus-high` | `opus` | `high` |
| `opus-xhigh` | `opus` | `xhigh` |
| `fable-high` | `fable` | `high` |

`fable-high` is optional: the table marks it `optional: true`, and while it
does, the ladder ends at `opus-xhigh`. A project that wants it removes that
line. Each agent starts at the tier the table gives it (`agents:`, or its line
under `overrides:`).

## When to escalate

Escalate only on one of these signals:

1. **A check fails again after a fix attempt**: the same test, gate or verifier
   fails again after the agent tried to fix it.
2. **A second rejection on the same finding**: a critic or verifier rejects the
   output a second time for the same finding.
3. **A block or the turn limit**: the agent reports that it is blocked, or ends
   at `maxTurns` without a result.
4. **A format failed twice**: the output misses its required format twice.

These are not signals: missing information, a decision that is the user's, a
refusal, and a matter of taste. A stronger model does not supply a missing
design document or make the user's choice. Ask the user instead. When a signal
and a non-signal overlap, the non-signal wins. For example, an agent that is
blocked because a document it needs does not exist gets a question to the user,
not a stronger model.

## How to escalate

- Start the same agent type again, one rung above the rung it last ran at,
  through the Agent tool's per-invocation `model` and `effort` parameters. They
  win over the agent's `model:` and `effort:` lines; the `effort` parameter
  needs Claude Code v2.1.292 or later. This document is the instruction that
  asks for those parameters.
- Give it the same brief, plus what was tried and the evidence of the failure:
  the failing output, the test message or the finding. Never send just "try
  again".
- Record each escalation as one line in the task's report: role, old rung, new
  rung and signal.
- One rung per step, never skipping one.
- The next task starts at its own tier again: an escalation does not carry
  over.
- At the top rung, stop and ask the user, with the rungs tried and the
  evidence.

## Limits

- **`CLAUDE_CODE_EFFORT_LEVEL`** overrides every effort, the ladder's
  included. With it set, only the model steps of the ladder have an effect.
- **`CLAUDE_CODE_SUBAGENT_MODEL_FORCE`** ignores each agent's `model:` and
  stops a per-invocation model, so only effort can rise. Raise the effort while
  the ladder has a higher effort for that model, then stop and ask the user.
- **The main session is the user's.** You cannot change your own model or
  effort; the user does that with `/model` and `/effort`. When the work you do
  yourself is stuck, stop and ask, and you may suggest either command.
- **Nested callers.** Only a subagent that starts agents (for example
  `core-systems-lead`, which has the Agent tool) and whose brief or file passes
  this rule on applies it. Pass it on in the brief when that matters.
- **Live behaviour.** The tests check this document, the ladder's order and
  each tier. Whether a session follows the ladder is live behaviour that no
  test shows.
