# Benchmarks

> **Measured on a local illustrative run (synthetic data).** Every number below was produced by executing the simulation in this repo — mock tools, a seeded simulated critic, simulated gate approvals. No model calls, no network calls, no real tickets.

- Date: 2026-09-14 · Python 3.12.3 · Linux x86_64
- Suite: 10 synthetic tasks, critic threshold 0.8, max iterations 3
- Suite wall time (measured): 0.001 s
- Regenerate: `python scripts/benchmark.py`

## Per-task results

| task | iterations | critic scores | tool calls | tools used | gate | outcome |
|---|---|---|---|---|---|---|
| `kb-policy` | 1 | 0.89 | 1 | search_kb | n/a (read/draft-only) | solved |
| `triage-p1` | 1 | 0.84 | 3 | get_ticket, search_kb, draft_summary | write → approved (simulated) | solved |
| `policy-summary` | 1 | 0.83 | 2 | search_kb, draft_summary | n/a (read/draft-only) | solved |
| `onboard-faq` | 1 | 0.91 | 1 | search_kb | n/a (read/draft-only) | solved |
| `refund-status` | 2 | 0.72, 0.84 | 2 | get_ticket, draft_summary | write → approved (simulated) | solved |
| `label-spam` | 2 | 0.72, 0.85 | 2 | get_ticket, search_kb | write → approved (simulated) | solved |
| `sla-report` | 2 | 0.69, 0.86 | 3 | get_ticket, search_kb, draft_summary | n/a (read/draft-only) | solved |
| `incident-bridge` | 3 | 0.66, 0.75, 0.83 | 2 | get_ticket, search_kb | external → approved (simulated) | solved |
| `vip-escalation` | 3 | 0.66, 0.74, 0.85 | 3 | get_ticket, search_kb, draft_summary | external → approved (simulated) | solved |
| `change-freeze` | 3 | 0.68, 0.71, 0.75 | 2 | search_kb, get_ticket | — | escalated |

## Iterations-to-success distribution

| iterations used | tasks | share |
|---|---|---|
| 1 | 4 | 40% |
| 2 | 3 | 30% |
| 3 | 3 | 30% |

Solved within max iterations: **9/10**. Escalated to a human reviewer: **1/10** (`change-freeze` — critic never cleared the threshold).

## Critic-score trajectory

Mean simulated critic score per round, over the tasks that reached that round (later rounds only contain tasks that failed earlier ones, so the mean dips — that is the intended selection effect).

| round | tasks scored | mean score | min | max |
|---|---|---|---|---|
| 1 | 10 | 0.76 | 0.66 | 0.91 |
| 2 | 6 | 0.79 | 0.71 | 0.86 |
| 3 | 3 | 0.81 | 0.75 | 0.85 |

## Tool-call counts

| tool | tier | calls |
|---|---|---|
| `draft_summary` | draft | 5 |
| `get_ticket` | read | 7 |
| `search_kb` | read | 9 |

Total tool calls across the suite: **21** (avg 2.1 per task).

## Escalation case

`change-freeze` — “push an emergency config change to production during the change freeze”. Critic scores 0.68, 0.71, 0.75 across 3 rounds never reached 0.8, so the loop stopped instead of acting on a low-confidence plan. No tool side effects occurred (the gated `notify_oncall` was never reached); the transcript routes the task to a human reviewer. This is the designed failure drill: the escalation path is the feature being exercised.

## Reproducibility

The critic score is `base + delta × (iteration − 1)` plus a jitter in [−0.02, +0.02] drawn from `random.Random(f"{seed}:{task_id}:{iteration}")` with a fixed seed (`CRITIC_SEED` in `agent/loop.py`). Task profiles in `agent/tasks.py` keep every task at least 0.03 of score away from the threshold boundary at each round, so the iteration bucket of every task is stable, not jitter-luck. Re-running `run_all()` reproduces these tables exactly.
