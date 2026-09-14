"""Run the synthetic task suite and write docs/BENCHMARKS.md.

Every number in the doc is measured from executing the local simulation —
no model calls, no network. The critic is seeded (see agent/loop.py), so
re-runs reproduce the same tables.
"""
import argparse
import datetime
import os
import platform
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.loop import CRITIC_THRESHOLD, MAX_ITERS, run_all  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "docs", "BENCHMARKS.md"))
    args = ap.parse_args()

    t0 = time.perf_counter()
    runs = run_all(demo_mode=True)
    wall_s = time.perf_counter() - t0

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    py = platform.python_version()
    plat = f"{platform.system()} {platform.machine()}"

    lines: list[str] = []
    add = lines.append

    add("# Benchmarks")
    add("")
    add("> **Measured on a local illustrative run (synthetic data).** "
        "Every number below was produced by executing the simulation in this "
        "repo — mock tools, a seeded simulated critic, simulated gate "
        "approvals. No model calls, no network calls, no real tickets.")
    add("")
    add(f"- Date: {stamp} · Python {py} · {plat}")
    add(f"- Suite: {len(runs)} synthetic tasks, "
        f"critic threshold {CRITIC_THRESHOLD}, max iterations {MAX_ITERS}")
    add(f"- Suite wall time (measured): {wall_s:.3f} s")
    add(f"- Regenerate: `python scripts/benchmark.py`")
    add("")

    # ---- per-task table ----
    add("## Per-task results")
    add("")
    add("| task | iterations | critic scores | tool calls | tools used | gate | outcome |")
    add("|---|---|---|---|---|---|---|")
    for r in runs:
        scores = ", ".join(f"{s:.2f}" for s in r.critic_scores)
        tools = ", ".join(tc.tool for tc in r.tool_calls)
        if r.escalated:
            outcome, gate_s = "escalated", "—"
        elif r.gate_decision:
            outcome, gate_s = "solved", f"{r.gate_tier} → approved (simulated)"
        else:
            outcome, gate_s = "solved", "n/a (read/draft-only)"
        add(f"| `{r.task_id}` | {r.iterations} | {scores} | "
            f"{r.tool_call_count} | {tools} | {gate_s} | {outcome} |")
    add("")

    # ---- distribution ----
    add("## Iterations-to-success distribution")
    add("")
    add("| iterations used | tasks | share |")
    add("|---|---|---|")
    buckets: dict = {}
    for r in runs:
        buckets[r.iterations] = buckets.get(r.iterations, 0) + 1
    for it in sorted(buckets):
        n = buckets[it]
        add(f"| {it} | {n} | {n / len(runs):.0%} |")
    esc = sum(1 for r in runs if r.escalated)
    solved = len(runs) - esc
    add("")
    add(f"Solved within max iterations: **{solved}/{len(runs)}**. "
        f"Escalated to a human reviewer: **{esc}/{len(runs)}** "
        f"(`change-freeze` — critic never cleared the threshold).")
    add("")

    # ---- critic trajectory ----
    add("## Critic-score trajectory")
    add("")
    add("Mean simulated critic score per round, over the tasks that reached "
        "that round (later rounds only contain tasks that failed earlier "
        "ones, so the mean dips — that is the intended selection effect).")
    add("")
    add("| round | tasks scored | mean score | min | max |")
    add("|---|---|---|---|---|")
    for rnd in range(1, MAX_ITERS + 1):
        vals = [r.critic_scores[rnd - 1] for r in runs
                if len(r.critic_scores) >= rnd]
        add(f"| {rnd} | {len(vals)} | {sum(vals) / len(vals):.2f} | "
            f"{min(vals):.2f} | {max(vals):.2f} |")
    add("")

    # ---- tool calls ----
    add("## Tool-call counts")
    add("")
    add("| tool | tier | calls |")
    add("|---|---|---|")
    counts: dict = {}
    tiers: dict = {}
    for r in runs:
        for tc in r.tool_calls:
            counts[tc.tool] = counts.get(tc.tool, 0) + 1
            tiers[tc.tool] = tc.tier
    for tool in sorted(counts):
        add(f"| `{tool}` | {tiers[tool]} | {counts[tool]} |")
    total = sum(counts.values())
    add("")
    add(f"Total tool calls across the suite: **{total}** "
        f"(avg {total / len(runs):.1f} per task).")
    add("")

    # ---- escalation case ----
    add("## Escalation case")
    add("")
    esc_run = next(r for r in runs if r.escalated)
    add(f"`{esc_run.task_id}` — “{esc_run.prompt}”. Critic scores "
        f"{', '.join(f'{s:.2f}' for s in esc_run.critic_scores)} across "
        f"{esc_run.iterations} rounds never reached {CRITIC_THRESHOLD}, so "
        "the loop stopped instead of acting on a low-confidence plan. No "
        "tool side effects occurred (the gated `notify_oncall` was never "
        "reached); the transcript routes the task to a human reviewer. "
        "This is the designed failure drill: the escalation path is the "
        "feature being exercised.")
    add("")

    # ---- reproducibility ----
    add("## Reproducibility")
    add("")
    add("The critic score is `base + delta × (iteration − 1)` plus a jitter "
        "in [−0.02, +0.02] drawn from `random.Random(f\"{seed}:{task_id}:"
        "{iteration}\")` with a fixed seed (`CRITIC_SEED` in "
        "`agent/loop.py`). Task profiles in `agent/tasks.py` keep every task "
        "at least 0.03 of score away from the threshold boundary at each "
        "round, so the iteration bucket of every task is stable, not "
        "jitter-luck. Re-running `run_all()` reproduces these tables exactly.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {args.out} ({len(runs)} tasks, {wall_s:.3f}s)")


if __name__ == "__main__":
    main()
