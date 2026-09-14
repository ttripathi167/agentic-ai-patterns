"""Human-in-the-loop gate logic.

Risk tiers decide which actions need a human before execution. The gate
applies to ACTIONS, not answers: reads and drafts flow; writes above a risk
threshold wait for approval. Approvers must see the plan, the evidence, and
the diff — never a bare "approve?" button.

In demo mode approvals are simulated (clearly labeled). In production this
integrates with your ticketing/chat-ops approval flow (e.g. Slack buttons,
ServiceNow change tasks).
"""
from dataclasses import dataclass
from enum import Enum


class RiskTier(str, Enum):
    READ = "read"        # no side effects: kb search, ticket fetch
    DRAFT = "draft"      # produces text only: summaries, suggested replies
    WRITE = "write"      # reversible side effects: ticket notes, labels
    EXTERNAL = "external"  # irreversible / outward: customer messages, deploys


# Tiers that execute without human approval. Tune per deployment.
AUTO_APPROVE = {RiskTier.READ, RiskTier.DRAFT}


@dataclass
class Action:
    name: str
    tier: RiskTier
    description: str
    evidence: str = ""  # plan + supporting facts shown to the approver


@dataclass
class GateDecision:
    approved: bool
    reason: str
    decided_by: str  # "policy" or "human"


def gate(action: Action, demo_mode: bool = True) -> GateDecision:
    """Decide whether an action may execute.

    demo_mode=True simulates a human approver; set False and wire this to
    your real approval surface (chat-ops, ITSM task, etc.).
    """
    if action.tier in AUTO_APPROVE:
        return GateDecision(
            approved=True,
            reason=f"tier={action.tier.value} auto-approved by policy",
            decided_by="policy",
        )
    if demo_mode:
        # SIMULATED human approval — replace with real approval flow.
        return GateDecision(
            approved=True,
            reason="simulated human approval (demo mode)",
            decided_by="human (simulated)",
        )
    raise NotImplementedError(
        "wire gate() to your real approval surface (chat-ops / ITSM)"
    )
