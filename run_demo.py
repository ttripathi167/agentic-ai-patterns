"""Rich staged demo: watch the agent loop think.

Runs the full 10-task synthetic suite from agent/tasks.py and narrates it
like an agent trace: the task, the plan, every tool call with timing, the
critic's verdict each round, the HITL gate on consequential actions, and a
final scoreboard.

Plain ANSI colors only (no dependencies). Pass --fast (or set DEMO_FAST=1)
to skip the dramatic pauses — used by CI.

Everything is simulated locally: no model calls, no network, no real data.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.loop import CRITIC_THRESHOLD, MAX_ITERS, run_all  # noqa: E402

# ---------------------------------------------------------------- ANSI ----

C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "magenta": "\033[35m",
    "blue": "\033[34m",
    "white": "\033[37m",
}

NO_COLOR = not sys.stdout.isatty() or os.environ.get("NO_COLOR")


def paint(text: str, *styles: str) -> str:
    if NO_COLOR:
        return text
    return "".join(C[s] for s in styles) + text + C["reset"]


def pause(seconds: float, fast: bool) -> None:
    if not fast:
        time.sleep(seconds)


def hr(char: str = "─", n: int = 72) -> str:
    return paint(char * n, "dim")


def score_bar(score: float, width: int = 24) -> str:
    filled = int(score * width)
    bar = "█" * filled + "░" * (width - filled)
    color = "green" if score >= CRITIC_THRESHOLD else ("yellow" if score >= 0.7 else "red")
    return paint(f"{bar} {score:.2f}", color, "bold")


TIER_COLOR = {"read": "cyan", "draft": "blue", "write": "yellow", "external": "red"}


# -------------------------------------------------------------- narration ----

def narrate_task(run, fast: bool) -> None:
    print()
    print(paint(f"▶ TASK  {run.task_id}", "bold", "white"))
    print(paint(f"  “{run.prompt}”", "dim"))
    print(hr())
    pause(0.45, fast)

    # plan
    print(paint("  🧠 planner", "bold", "magenta") + paint("  decomposing into steps…", "dim"))
    for i, tc in enumerate(run.tool_calls, 1):
        pause(0.3, fast)
        tier_c = TIER_COLOR.get(tc.tier, "white")
        print(
            f"    {paint(f'step {i}', 'dim')} "
            f"{paint('[' + tc.agent + ']', 'cyan')} → "
            f"{paint(tc.tool, 'bold', 'white')} "
            f"{paint('tier=' + tc.tier, tier_c)} "
            f"{paint(f'{tc.duration_ms:.2f} ms', 'dim')}"
        )
        print(paint(f"      ↳ {tc.result_preview[:95]}", "dim"))
    pause(0.35, fast)

    # critic rounds
    for i, score in enumerate(run.critic_scores, 1):
        passed = score >= CRITIC_THRESHOLD
        icon = "✅" if passed else "🔁"
        print(
            f"  {icon} {paint('critic', 'bold', 'yellow')} "
            f"{paint(f'round {i}/{MAX_ITERS}', 'dim')}  {score_bar(score)}"
            + (paint("  PASS", "green", "bold") if passed
               else paint(f"  below {CRITIC_THRESHOLD:.2f} → refining plan…", "dim"))
        )
        pause(0.4, fast)

    # outcome
    if run.escalated:
        print()
        print(paint("  🚨 ESCALATED — max iterations reached. "
                    "No action taken; routed to a human reviewer.", "red", "bold"))
    elif run.gate_decision is not None:
        gd = run.gate_decision
        ok = paint("APPROVED", "green", "bold") if gd.approved else paint("DENIED", "red", "bold")
        print()
        print(f"  🛂 {paint('HITL gate', 'bold', 'yellow')} "
              f"[{paint('tier=' + run.gate_tier, TIER_COLOR.get(run.gate_tier, 'white'))}] "
              f"→ {ok} {paint(f'({gd.decided_by}: {gd.reason})', 'dim')}")
        if run.action_executed:
            print(paint("  ⚙  action executed (mock)", "green"))
    else:
        print(paint("  ✓ read/draft-only — no gate required, nothing to approve", "dim"))
    pause(0.3, fast)


def scoreboard(runs, elapsed_s: float) -> None:
    print()
    print(paint("═" * 72, "dim"))
    print(paint("  SCOREBOARD — 10 synthetic tasks, simulated critic, demo-mode gates", "bold", "white"))
    print(paint("═" * 72, "dim"))
    print(paint(f"  {'task':<16}{'iters':<7}{'critic scores':<22}{'tools':<7}{'gate':<10}outcome",
                "bold", "dim"))
    succeeded = escalated = gated = 0
    for r in runs:
        if r.escalated:
            outcome = paint("ESCALATED", "red", "bold")
            escalated += 1
            gate_s = "—"
        else:
            outcome = paint("solved", "green")
            succeeded += 1
            if r.gate_decision:
                gated += 1
                gate_s = paint("approved", "yellow")
            else:
                gate_s = paint("n/a", "dim")
        scores = " ".join(f"{s:.2f}" for s in r.critic_scores)
        print(f"  {r.task_id:<16}{r.iterations:<7}{scores:<22}"
              f"{r.tool_call_count:<7}{gate_s:<10}{outcome}")
    print(paint("─" * 72, "dim"))
    print(f"  solved {paint(str(succeeded), 'green', 'bold')}/10   "
          f"escalated {paint(str(escalated), 'red', 'bold')}   "
          f"HITL gates passed {paint(str(gated), 'yellow', 'bold')}   "
          f"suite wall time {paint(f'{elapsed_s:.2f}s', 'cyan', 'bold')}")
    print()
    print(paint("  All tools mocked locally · critic simulated · approvals simulated.",
                "dim"))
    print(paint("  See docs/BENCHMARKS.md for measured tables, "
                "docs/PRODUCTION.md for the production story.", "dim"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Agentic AI patterns — staged demo")
    ap.add_argument("--fast", action="store_true",
                    help="skip dramatic pauses (used by CI)")
    args = ap.parse_args()
    fast = args.fast or os.environ.get("DEMO_FAST") == "1"

    print(paint("═" * 72, "dim"))
    print(paint("  AGENTIC-AI-PATTERNS", "bold", "white")
          + paint("  ·  planner → router → specialists → critic → HITL gate", "dim"))
    print(paint("  illustrative simulation — no real tools, models, or data", "dim"))
    print(paint("═" * 72, "dim"))
    pause(0.5, fast)

    t0 = time.perf_counter()
    runs = run_all(demo_mode=True)
    elapsed = time.perf_counter() - t0

    for r in runs:
        narrate_task(r, fast)

    scoreboard(runs, elapsed)


if __name__ == "__main__":
    main()
