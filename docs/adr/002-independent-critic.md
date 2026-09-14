# ADR-002: Independent critic design

**Status:** accepted · **Date:** 2026-09-14

## Context

A planner that grades its own homework will pass its own homework. If the
loop's quality gate is just the planner re-reading its draft, systematic
blind spots — misread policy, skipped evidence, hallucinated ticket fields —
survive every iteration because the same model makes the same mistake the
same way. The critic exists to break that correlation, but only if it
actually fails differently.

## Decision

The critic is an **independent judge**: a different model configuration
from the planner (different family preferred; at minimum a different
system prompt, temperature, and scoring rubric), scoring each draft on
groundedness, completeness, and policy compliance against a numeric
threshold (0.80 in this repo). The loop iterates until the score clears
the threshold or `MAX_ITERS` (3) triggers escalation — never silent
acceptance of a below-threshold draft.

Score thresholds and iteration caps are deployment-tunable, but the
*structure* is fixed: independent judge → numeric bar → bounded retries →
escalate. In this repo the critic is simulated with a seeded deterministic
scorer so the benchmark suite (`docs/BENCHMARKS.md`) is reproducible; the
swap point is `Critic.score()` in `agent/loop.py`.

## Alternatives considered

- **Self-critique (planner reviews its own draft).** Rejected: correlated
  failures. Cheap and fast, but it converts the quality gate into a
  rubber stamp for the planner's blind spots.
- **Same model, different prompt.** Weak acceptability: better than
  self-critique, still shares the base model's failure modes. Acceptable
  as a cost compromise, but monitor the critic/planner agreement rate —
  near-100% agreement is a collusion smell, not a success metric.
- **Human review of every draft.** Rejected at scale: converts the critic
  into the gate-queue problem (see ADR-003). Humans review escalations
  and sample audits, not every iteration.
- **No critic; single-pass with a strong planner.** Rejected: removes the
  only mechanism that catches planner errors before action. The benchmark
  suite shows why — 60% of tasks need 2–3 rounds to clear the bar.

## Verdict

An independent critic with a numeric threshold and a bounded retry budget
is the cheapest reliable quality gate for agentic loops. Its cost —
roughly doubling model calls — is real (see `docs/PRODUCTION.md` cost
model) and is managed by tiering critic depth, not by removing the critic.
