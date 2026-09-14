"""Planner -> router -> specialist -> critic loop (simulated).

Every model-shaped piece is a deterministic local function, clearly labeled.
Production swap points are marked: replace plan() with an LLM planner,
route() with a router model, critic_score() with an independent
judge-model call, and wire gates.gate(demo_mode=False) to a real
approval surface.
"""
import hashlib

from agent.gates import Action, RiskTier, gate
from agent.tools import TOOL_REGISTRY

MAX_ITERS = 3
CRITIC_THRESHOLD = 0.8


def plan(task: str) -> list[dict]:
    """Mock planner: decomposes a task into tool steps (simulated)."""
    task_l = task.lower()
    if "ticket" in task_l or "triage" in task_l:
        return [
            {"agent": "research", "tool": "get_ticket", "args": {"ticket_id": "INC-1042"}},
            {"agent": "research", "tool": "search_kb", "args": {"query": task}},
            {"agent": "extraction", "tool": "draft_summary", "args": {}},
            {"agent": "action", "tool": "update_ticket", "args": {"note": "triage summary attached"}},
        ]
    return [{"agent": "research", "tool": "search_kb", "args": {"query": task}}]


def route(step: dict) -> str:
    """Mock router: picks the specialist agent for a step (simulated)."""
    return step["agent"]


def critic_score(draft: dict, iteration: int) -> float:
    """Simulated critic score. Deterministic so the demo is reproducible.

    Production: an independent judge model (different config than the
    planner) scoring groundedness, completeness, and policy compliance.
    """
    digest = hashlib.sha256(repr(sorted(draft.items())).encode()).hexdigest()
    base = (int(digest[:4], 16) % 25) / 100.0  # 0.00–0.24
    return round(min(0.70 + base + 0.08 * iteration, 0.99), 2)


def run(task: str, demo_mode: bool = True) -> list[str]:
    """Execute the agent loop. Returns a human-readable transcript."""
    transcript: list[str] = []
    steps = plan(task)
    transcript.append(f"plan: {len(steps)} steps")

    context: dict = {}
    for i, step in enumerate(steps, 1):
        agent = route(step)
        tool_name = step["tool"]
        entry = TOOL_REGISTRY[tool_name]
        transcript.append(f"step {i}: [{agent}] -> {tool_name} (tier={entry['tier']})")

        if tool_name == "draft_summary":
            result = entry["fn"](context.get("ticket", {}), context.get("kb_hits", []))
        elif tool_name == "update_ticket":
            result = {"tool": tool_name, "pending": True}  # gated below
        elif tool_name == "get_ticket":
            result = entry["fn"](**step["args"])
            context["ticket"] = result
        else:
            result = entry["fn"](**step["args"])
            if tool_name == "search_kb":
                context["kb_hits"] = result["hits"]
        transcript.append(f"  result: {str(result)[:120]}")

    # critic review over the draft artifacts
    draft = {"task": task, "steps": len(steps), "context_keys": sorted(context)}
    approved = False
    for it in range(1, MAX_ITERS + 1):
        score = critic_score(draft, it)
        transcript.append(f"critic (iter {it}): score={score:.2f}")
        if score >= CRITIC_THRESHOLD:
            approved = True
            transcript.append(f"critic: PASS (>= {CRITIC_THRESHOLD})")
            break
        transcript.append("critic: below threshold -> re-plan (simulated refinement)")

    if not approved:
        transcript.append("STOP: max iterations -> escalate to human reviewer")
        return transcript

    # consequential action goes through the HITL gate
    action = Action(
        name="update_ticket",
        tier=RiskTier.WRITE,
        description="Attach triage summary note to INC-1042",
        evidence=f"plan={len(steps)} steps, critic score above threshold",
    )
    decision = gate(action, demo_mode=demo_mode)
    transcript.append(
        f"HITL gate: action={action.name} tier={action.tier.value} "
        f"evidence=({action.evidence})"
    )
    transcript.append(
        f"gate: approved={decision.approved} by={decision.decided_by} "
        f"({decision.reason})"
    )
    if decision.approved:
        result = TOOL_REGISTRY["update_ticket"]["fn"]("INC-1042", "triage summary attached")
        transcript.append(f"executed: {result['tool']} (mock)")
    return transcript


if __name__ == "__main__":
    for line in run("triage ticket INC-1042"):
        print(line)
