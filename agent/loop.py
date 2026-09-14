"""Planner -> router -> specialist -> critic loop (simulated).

Every model-shaped piece is a deterministic local function, clearly labeled.
Production swap points are marked: replace plan() with an LLM planner,
route() with a router model, Critic.score() with an independent
judge-model call, and wire gates.gate(demo_mode=False) to a real
approval surface.

The loop runs over the synthetic task suite in agent/tasks.py. Each
TaskRun records everything a production trace would carry: iterations
used, the critic score at every iteration, per-tool-call timing, the gate
decision, and whether the run succeeded or escalated.
"""
import random
import time
from dataclasses import dataclass, field

from agent.gates import Action, RiskTier, gate
from agent.tasks import TASKS, get_task
from agent.tools import TOOL_REGISTRY

MAX_ITERS = 3
CRITIC_THRESHOLD = 0.80
CRITIC_SEED = "agentic-ai-patterns-v1"  # fixed seed => reproducible benchmarks


# ---------------------------------------------------------------------------
# Structured run records
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    tool: str
    agent: str
    tier: str
    duration_ms: float
    result_preview: str = ""


@dataclass
class TaskRun:
    task_id: str
    title: str
    prompt: str
    iterations: int                       # critic rounds actually executed
    critic_scores: list[float]            # one score per iteration
    tool_calls: list[ToolCall]
    succeeded: bool                       # critic passed within MAX_ITERS
    escalated: bool                       # hit max iterations -> human reviewer
    gate_decision: object = None          # GateDecision, if a final action ran
    gate_tier: str = ""                   # risk tier of the gated action
    action_executed: bool = False
    transcript: list[str] = field(default_factory=list)

    @property
    def tool_call_count(self) -> int:
        return len(self.tool_calls)


# ---------------------------------------------------------------------------
# Planner / router / critic (all simulated, deterministic)
# ---------------------------------------------------------------------------

def plan(task: dict) -> list[dict]:
    """Mock planner: returns the task's decomposed tool steps (simulated).

    Accepts a task spec dict from agent/tasks.py. A bare string keeps the
    old behavior: keyword match against known tasks, else a generic
    single-step lookup plan.
    """
    if isinstance(task, dict):
        return task["steps"]
    task_l = task.lower()
    for spec in TASKS:
        if spec["id"] in task_l or any(
            kw in task_l for kw in spec["prompt"].split()[:3]
        ):
            return spec["steps"]
    return [{"agent": "research", "tool": "search_kb", "args": {"query": task}}]


def route(step: dict) -> str:
    """Mock router: picks the specialist agent for a step (simulated)."""
    return step["agent"]


class Critic:
    """Simulated independent critic. Deterministic by (seed, task, iteration).

    Score model: base + delta * (iteration - 1), plus a small seeded jitter
    in [-0.02, +0.02]. Seeding on the task id and iteration (not on global
    RNG state) keeps benchmarks reproducible run after run.

    Production: an independent judge model — different config/family than
    the planner — scoring groundedness, completeness, and policy compliance
    (see docs/adr/002-independent-critic.md).
    """

    def __init__(self, threshold: float = CRITIC_THRESHOLD,
                 seed: str = CRITIC_SEED):
        self.threshold = threshold
        self.seed = seed

    def score(self, task: dict, iteration: int) -> float:
        rng = random.Random(f"{self.seed}:{task['id']}:{iteration}")
        jitter = rng.uniform(-0.02, 0.02)
        raw = task["critic_base"] + task["critic_delta"] * (iteration - 1) + jitter
        return round(min(0.99, max(0.0, raw)), 2)

    def verdict(self, task: dict, iteration: int) -> tuple[float, bool]:
        s = self.score(task, iteration)
        return s, s >= self.threshold


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------

def run_task(task: dict, demo_mode: bool = True,
             critic: Critic | None = None) -> TaskRun:
    """Execute the full loop for one task. Returns a structured TaskRun."""
    critic = critic or Critic()
    transcript: list[str] = []
    tool_calls: list[ToolCall] = []
    scores: list[float] = []

    steps = plan(task)
    transcript.append(f"plan: {len(steps)} steps")

    context: dict = {}
    for i, step in enumerate(steps, 1):
        agent = route(step)
        tool_name = step["tool"]
        entry = TOOL_REGISTRY[tool_name]
        transcript.append(
            f"step {i}: [{agent}] -> {tool_name} (tier={entry['tier']})")

        t0 = time.perf_counter()
        if tool_name == "draft_summary":
            result = entry["fn"](context.get("ticket", {}), context.get("kb_hits", []))
        else:
            result = entry["fn"](**step["args"])
            if tool_name == "get_ticket":
                context["ticket"] = result
            elif tool_name == "search_kb":
                context["kb_hits"] = result["hits"]
        dt_ms = (time.perf_counter() - t0) * 1000.0

        tool_calls.append(ToolCall(
            tool=tool_name, agent=agent, tier=entry["tier"],
            duration_ms=dt_ms, result_preview=str(result)[:100]))
        transcript.append(f"  result ({dt_ms:.2f} ms): {str(result)[:120]}")

    # critic review: iterate until the score clears the threshold
    approved = False
    iterations = 0
    for it in range(1, MAX_ITERS + 1):
        iterations = it
        score, passed = critic.verdict(task, it)
        scores.append(score)
        transcript.append(f"critic (iter {it}): score={score:.2f}")
        if passed:
            approved = True
            transcript.append(f"critic: PASS (>= {critic.threshold})")
            break
        transcript.append("critic: below threshold -> re-plan (simulated refinement)")

    if not approved:
        transcript.append("STOP: max iterations -> escalate to human reviewer")
        return TaskRun(
            task_id=task["id"], title=task["title"], prompt=task["prompt"],
            iterations=iterations, critic_scores=scores, tool_calls=tool_calls,
            succeeded=False, escalated=True, transcript=transcript)

    # consequential actions go through the HITL gate; reads/drafts need none
    gate_decision = None
    gate_tier = ""
    action_executed = False
    final = task.get("final_action")
    if final:
        action = Action(
            name=final["name"],
            tier=RiskTier(final["tier"]),
            description=final["description"],
            evidence=(f"plan={len(steps)} steps, "
                      f"critic scores={[f'{s:.2f}' for s in scores]}"),
        )
        gate_decision = gate(action, demo_mode=demo_mode)
        gate_tier = action.tier.value
        transcript.append(
            f"HITL gate: action={action.name} tier={action.tier.value} "
            f"evidence=({action.evidence})")
        transcript.append(
            f"gate: approved={gate_decision.approved} "
            f"by={gate_decision.decided_by} ({gate_decision.reason})")
        if gate_decision.approved:
            result = TOOL_REGISTRY[final["name"]]["fn"](**final["args"])
            action_executed = True
            transcript.append(f"executed: {result['tool']} (mock)")
    else:
        transcript.append("no consequential action: read/draft-only, no gate needed")

    return TaskRun(
        task_id=task["id"], title=task["title"], prompt=task["prompt"],
        iterations=iterations, critic_scores=scores, tool_calls=tool_calls,
        succeeded=True, escalated=False, gate_decision=gate_decision,
        gate_tier=gate_tier, action_executed=action_executed,
        transcript=transcript)


def run_all(demo_mode: bool = True) -> list[TaskRun]:
    """Run the full synthetic benchmark suite. Returns one TaskRun per task."""
    critic = Critic()  # shared config across the suite, like one judge model
    return [run_task(task, demo_mode=demo_mode, critic=critic) for task in TASKS]


def run(task: str, demo_mode: bool = True) -> list[str]:
    """Legacy entry point: execute a single task, return a text transcript.

    Kept for backward compatibility; new code should use run_task/run_all.
    """
    try:
        spec = get_task(task)
    except KeyError:
        spec = {
            "id": "ad-hoc", "title": task, "prompt": task,
            "steps": plan(task), "final_action": None,
            "critic_base": 0.85, "critic_delta": 0.0,
        }
    return run_task(spec, demo_mode=demo_mode).transcript


if __name__ == "__main__":
    for line in run("triage-p1"):
        print(line)
