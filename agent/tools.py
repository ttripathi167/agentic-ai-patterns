"""Mock tool implementations for the agent demo.

In production these are MCP tool-server entries: typed contracts, OAuth2/OIDC
identity per call, least-privilege scopes, and every invocation written to an
audit log. Here they are local functions returning synthetic data.
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
    return {
        "tool": "draft_summary",
        "draft": (
            f"Summary for {ticket['ticket_id']}: {ticket['title']} "
            f"(severity {ticket['severity']}). "
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


# Registry mirrors what an MCP tool registry advertises: name, tier, schema.
TOOL_REGISTRY = {
    "search_kb": {"tier": "read", "fn": search_kb},
    "get_ticket": {"tier": "read", "fn": get_ticket},
    "draft_summary": {"tier": "draft", "fn": draft_summary},
    "update_ticket": {"tier": "write", "fn": update_ticket},
}
