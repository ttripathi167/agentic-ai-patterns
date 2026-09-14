"""Mock tool implementations for the agent demo.

In production these are MCP tool-server entries: typed contracts, OAuth2/OIDC
identity per call, least-privilege scopes, and every invocation written to an
audit log. Here they are local functions returning synthetic data.

Tiers (see agent/gates.py):
  read     - no side effects (search_kb, get_ticket)
  draft    - produces text only, changes nothing (draft_summary)
  write    - reversible side effects, gated (update_ticket, label_ticket)
  external - irreversible / outward-facing, always gated (notify_oncall)
"""


def search_kb(query: str) -> dict:
    """Read-only knowledge-base lookup (mock)."""
    return {
        "tool": "search_kb",
        "query": query,
        "hits": [
            {"doc_id": "doc_0142", "title": "policy-manual.pdf",
             "snippet": "P1 escalation: page on-call lead, open bridge in 15 min."},
            {"doc_id": "doc_0216", "title": "runbook-p1.pdf",
             "snippet": "Assign commander, comms, scribe; start the timeline."},
        ],
    }


def get_ticket(ticket_id: str) -> dict:
    """Read-only ticket fetch (mock)."""
    return {
        "tool": "get_ticket",
        "ticket_id": ticket_id,
        "title": "Checkout latency spike in eu-west",
        "severity": "P1",
        "status": "open",
        "owner": "payments-oncall",
    }


def draft_summary(ticket: dict, kb_hits: list) -> dict:
    """Draft-only: produces text, changes nothing (mock)."""
    ticket = ticket or {}
    ref = ticket.get("ticket_id", "general query")
    title = ticket.get("title", "no linked ticket")
    severity = ticket.get("severity", "n/a")
    return {
        "tool": "draft_summary",
        "draft": (
            f"Summary for {ref}: {title} (severity {severity}). "
            f"Relevant guidance: {kb_hits[0]['snippet'] if kb_hits else 'none'}."
        ),
    }


def update_ticket(ticket_id: str, note: str) -> dict:
    """WRITE action (mock): would mutate the ticket system in production.

    Always routed through the HITL gate in agent/loop.py before execution.
    """
    return {
        "tool": "update_ticket",
        "ticket_id": ticket_id,
        "note_added": note,
        "mock": True,
    }


def label_ticket(ticket_id: str, label: str) -> dict:
    """WRITE action (mock): applies a label to a ticket (reversible)."""
    return {
        "tool": "label_ticket",
        "ticket_id": ticket_id,
        "label_applied": label,
        "mock": True,
    }


def notify_oncall(ticket_id: str, message: str) -> dict:
    """EXTERNAL action (mock): pages the on-call engineer.

    Irreversible and outward-facing: wakes a human up at 3am. Always gated.
    """
    return {
        "tool": "notify_oncall",
        "ticket_id": ticket_id,
        "message_sent": message,
        "mock": True,
    }


# Registry mirrors what an MCP tool registry advertises: name, risk tier,
# a short contract description, and the callable. The tier is what the
# HITL gate (agent/gates.py) keys off — not the tool name.
TOOL_REGISTRY = {
    "search_kb": {
        "tier": "read",
        "description": "Full-text lookup over the ops knowledge base.",
        "fn": search_kb,
    },
    "get_ticket": {
        "tier": "read",
        "description": "Fetch a ticket by id (title, severity, status, owner).",
        "fn": get_ticket,
    },
    "draft_summary": {
        "tier": "draft",
        "description": "Compose a summary draft from ticket + KB context.",
        "fn": draft_summary,
    },
    "update_ticket": {
        "tier": "write",
        "description": "Append a note to a ticket. Reversible, gated.",
        "fn": update_ticket,
    },
    "label_ticket": {
        "tier": "write",
        "description": "Apply a label to a ticket. Reversible, gated.",
        "fn": label_ticket,
    },
    "notify_oncall": {
        "tier": "external",
        "description": "Page the on-call engineer. Irreversible, always gated.",
        "fn": notify_oncall,
    },
}
