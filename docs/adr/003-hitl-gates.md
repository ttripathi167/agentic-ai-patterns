# ADR-003: Human-in-the-loop gates on consequential actions

**Status:** accepted · **Date:** 2026-09-14

## Context

Some agent outputs are answers; some are actions. Answers can be
regenerated. Actions — a ticket note, a label, a 3am page — happen in the
world and can't be un-happened cheaply. The question isn't *whether* humans
stay in the loop on actions, but *which* actions and *how* the gate is
designed so it stays meaningful at volume instead of degrading into
rubber-stamp theater.

## Decision

**Risk-tiered gates on actions, not answers**, enforced at the tool
registry boundary (`agent/gates.py`):

| Tier | Meaning | Gate behavior |
|---|---|---|
| `read` | no side effects (KB search, ticket fetch) | auto-approve by policy |
| `draft` | produces text only, changes nothing | auto-approve by policy |
| `write` | reversible side effects (ticket notes, labels) | human approval required |
| `external` | irreversible / outward-facing (pages, customer messages) | human approval required, no auto-approve path ever |

Approvers see the **plan, the evidence, and the diff** — never a bare
"approve?" button. A gate decision is a traceable event: action, tier,
evidence shown, approver identity, decision, timestamp. In this repo's
demo, approvals are simulated (`demo_mode=True`); production wires
`gate()` to the real approval surface (chat-ops, ITSM change task).

## Alternatives considered

- **Gate everything, including reads.** Rejected: gate volume explodes,
  approvers fatigue, and the control degrades precisely where it matters.
  Reads can't harm anything; gating them buys nothing.
- **Gate nothing; rely on the critic.** Rejected: the critic judges draft
  *quality*, not action *consequence*. A perfect draft can still describe
  an action nobody should take at 3am without a human saying so.
- **One flat approval for all writes.** Rejected: treats "add a label" and
  "page the on-call" identically, which trains approvers to click through
  the frequent low-risk ones — and then through the rare high-risk one.
  Tiers exist to protect approver attention as a scarce resource.
- **Async notify instead of blocking gate.** Partially adopted: the gate
  *is* async (runs suspend/resume; see `docs/PRODUCTION.md`), but for
  `external` tier there is no fire-and-notify path — execution waits for
  the decision.

## Verdict

Tier by reversibility and outward impact; gate the tiers that change the
world; show approvers evidence, not buttons. The gate is the scarcest
resource in the system — human attention — so the tier model is really a
budget for spending it where it matters. Any write/external execution
without a matching approved gate event is a security incident (see
`docs/PRODUCTION.md` observability).
