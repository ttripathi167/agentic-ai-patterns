# ADR-001: Orchestrated multi-agent vs. single agent

**Status:** accepted · **Date:** 2026-09-14

## Context

The workload this architecture serves — ticket triage spanning a knowledge
base, a ticketing system, and a notification path — touches several systems
with different trust levels. The core design question: one agent holding
every tool, or a planner composing specialist agents that each hold a
least-privilege tool set?

A single agent is simpler to build and debug: one prompt, one loop, no
orchestration overhead. But every capability the task might need must be
in that agent's hands at once — read tools, draft tools, write tools, and
external/page-out tools — for the entire run.

## Decision

Orchestrated multi-agent: a planner decomposes the request into steps, a
router assigns each step to a specialist (research / extraction / action),
and specialists only see the tools their role needs. The research agent
literally cannot call `notify_oncall` — the tool isn't in its registry
view — so a confused or compromised research step cannot page anyone.

## Alternatives considered

- **Single agent with all tools.** Rejected: one confused step holds every
  capability at once. The blast radius of a prompt-injection in a KB doc
  becomes "anything the agent can do" instead of "what the research role
  can do". Simplicity isn't worth that.
- **Single agent with per-step tool filtering.** A middle ground — one
  agent, tools swapped per step. Rejected: the filtering logic *is* the
  orchestrator, just unnamed and untestable. Better to name the roles and
  give each its own prompt, eval, and tool contract.
- **Fully autonomous swarm (agents calling agents).** Rejected for this
  workload: emergent delegation is powerful but the audit trail becomes
  "agents all the way down". The planner/router split keeps one place
  where the intended sequence of steps is explicit and reviewable.

## Verdict

Multi-agent orchestration wins on **blast-radius containment** at the cost
of orchestration complexity and more model calls. That tradeoff is correct
when tools have side effects; for pure read-only Q&A a single agent would
still be the right call. The router is deliberately the cheapest component
(a classifier, not a reasoning model) so the overhead stays small.
