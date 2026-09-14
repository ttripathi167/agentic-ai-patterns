"""Synthetic benchmark task suite for the agent loop.

Ten tasks with deliberately varied difficulty, expressed as a critic-score
profile: ``critic_base`` (score at iteration 1) and ``critic_delta``
(improvement per iteration), plus a small seeded jitter applied by the
critic. The profiles are engineered so each task lands in a known
iteration bucket against the 0.80 threshold (jitter is bounded at +/-0.02):

  * 1 iteration : base >= 0.83  (passes immediately)
  * 2 iterations: base <= 0.77, base + delta >= 0.83
  * 3 iterations: base + delta <= 0.77, base + 2*delta >= 0.83
  * escalation  : base + 2*delta <= 0.77 (never clears in 3 tries)

Nothing here is a real workload: ticket ids, titles, and KB snippets are
fabricated for the demo. The value is in the *shape* of the runs —
success fast, success after revision, and graceful escalation — which is
exactly what docs/BENCHMARKS.md measures.
"""

TASKS = [
    {
        "id": "kb-policy",
        "title": "Look up the P1 escalation policy",
        "prompt": "What is the P1 escalation policy?",
        "steps": [
            {"agent": "research", "tool": "search_kb",
             "args": {"query": "P1 escalation policy"}},
        ],
        "final_action": None,  # read-only: no gate, no side effects
        "critic_base": 0.88,
        "critic_delta": 0.00,
    },
    {
        "id": "triage-p1",
        "title": "Triage P1 checkout-latency ticket INC-1042",
        "prompt": "triage ticket INC-1042: checkout latency spike in eu-west",
        "steps": [
            {"agent": "research", "tool": "get_ticket",
             "args": {"ticket_id": "INC-1042"}},
            {"agent": "research", "tool": "search_kb",
             "args": {"query": "checkout latency eu-west runbook"}},
            {"agent": "extraction", "tool": "draft_summary", "args": {}},
        ],
        "final_action": {
            "name": "update_ticket",
            "tier": "write",
            "description": "Attach triage summary note to INC-1042",
            "args": {"ticket_id": "INC-1042", "note": "triage summary attached"},
        },
        "critic_base": 0.85,
        "critic_delta": 0.00,
    },
    {
        "id": "policy-summary",
        "title": "Summarize the P1 runbook for the on-call handoff",
        "prompt": "summarize the P1 runbook for the on-call handoff",
        "steps": [
            {"agent": "research", "tool": "search_kb",
             "args": {"query": "P1 runbook on-call handoff"}},
            {"agent": "extraction", "tool": "draft_summary", "args": {}},
        ],
        "final_action": None,  # draft only: auto-approved by policy
        "critic_base": 0.84,
        "critic_delta": 0.02,
    },
    {
        "id": "onboard-faq",
        "title": "Answer the new-hire FAQ on on-call rotations",
        "prompt": "how do on-call rotations work for new hires?",
        "steps": [
            {"agent": "research", "tool": "search_kb",
             "args": {"query": "on-call rotations new hire"}},
        ],
        "final_action": None,
        "critic_base": 0.91,
        "critic_delta": 0.00,
    },
    {
        "id": "refund-status",
        "title": "Update INC-2077 with the customer refund status",
        "prompt": "update ticket INC-2077 with the refund status for the customer",
        "steps": [
            {"agent": "research", "tool": "get_ticket",
             "args": {"ticket_id": "INC-2077"}},
            {"agent": "extraction", "tool": "draft_summary", "args": {}},
        ],
        "final_action": {
            "name": "update_ticket",
            "tier": "write",
            "description": "Append refund-status note to INC-2077",
            "args": {"ticket_id": "INC-2077", "note": "refund status: approved, 3-5 days"},
        },
        "critic_base": 0.70,
        "critic_delta": 0.14,
    },
    {
        "id": "label-spam",
        "title": "Label noisy alert tickets as noise",
        "prompt": "label the noisy alert tickets INC-3101 as noise",
        "steps": [
            {"agent": "research", "tool": "get_ticket",
             "args": {"ticket_id": "INC-3101"}},
            {"agent": "research", "tool": "search_kb",
             "args": {"query": "alert noise labeling policy"}},
        ],
        "final_action": {
            "name": "label_ticket",
            "tier": "write",
            "description": "Apply label 'noise' to INC-3101",
            "args": {"ticket_id": "INC-3101", "label": "noise"},
        },
        "critic_base": 0.71,
        "critic_delta": 0.13,
    },
    {
        "id": "sla-report",
        "title": "Draft the weekly SLA report from ticket data",
        "prompt": "draft the weekly SLA report from open ticket data",
        "steps": [
            {"agent": "research", "tool": "get_ticket",
             "args": {"ticket_id": "INC-1042"}},
            {"agent": "research", "tool": "search_kb",
             "args": {"query": "SLA report template weekly"}},
            {"agent": "extraction", "tool": "draft_summary", "args": {}},
        ],
        "final_action": None,  # draft only
        "critic_base": 0.69,
        "critic_delta": 0.15,
    },
    {
        "id": "incident-bridge",
        "title": "Open a bridge for the eu-west payments incident",
        "prompt": "open an incident bridge for the eu-west payments outage and page on-call",
        "steps": [
            {"agent": "research", "tool": "get_ticket",
             "args": {"ticket_id": "INC-1042"}},
            {"agent": "research", "tool": "search_kb",
             "args": {"query": "incident bridge runbook payments"}},
        ],
        "final_action": {
            "name": "notify_oncall",
            "tier": "external",
            "description": "Page payments-oncall: bridge opened for INC-1042",
            "args": {"ticket_id": "INC-1042",
                     "message": "P1 bridge opened for INC-1042, commander needed"},
        },
        "critic_base": 0.68,
        "critic_delta": 0.07,
    },
    {
        "id": "vip-escalation",
        "title": "Escalate the VIP merchant outage to the incident commander",
        "prompt": "escalate the VIP merchant outage INC-5150 to the incident commander",
        "steps": [
            {"agent": "research", "tool": "get_ticket",
             "args": {"ticket_id": "INC-5150"}},
            {"agent": "research", "tool": "search_kb",
             "args": {"query": "VIP merchant escalation path"}},
            {"agent": "extraction", "tool": "draft_summary", "args": {}},
        ],
        "final_action": {
            "name": "notify_oncall",
            "tier": "external",
            "description": "Page incident commander: VIP outage INC-5150",
            "args": {"ticket_id": "INC-5150",
                     "message": "VIP merchant outage INC-5150 escalated to IC"},
        },
        "critic_base": 0.67,
        "critic_delta": 0.08,
    },
    {
        "id": "change-freeze",
        "title": "Push an emergency config change during the freeze",
        "prompt": "push an emergency config change to production during the change freeze",
        "steps": [
            {"agent": "research", "tool": "search_kb",
             "args": {"query": "change freeze emergency exception process"}},
            {"agent": "research", "tool": "get_ticket",
             "args": {"ticket_id": "INC-1042"}},
        ],
        # Deliberately adversarial: low base, slow improvement. The critic
        # never clears the threshold in MAX_ITERS, so the loop must
        # escalate instead of acting on a half-baked plan. This is the
        # designed escalation case for the benchmark suite.
        "final_action": {
            "name": "notify_oncall",
            "tier": "external",
            "description": "Page on-call: emergency config change request (freeze active)",
            "args": {"ticket_id": "INC-1042",
                     "message": "emergency config change requested during freeze"},
        },
        "critic_base": 0.66,
        "critic_delta": 0.04,
    },
]


def get_task(task_id: str) -> dict:
    """Fetch a task spec by id; KeyError if unknown."""
    for task in TASKS:
        if task["id"] == task_id:
            return task
    raise KeyError(f"unknown task id: {task_id!r}")
