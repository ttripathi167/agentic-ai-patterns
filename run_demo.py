"""Ticket-triage demo: planner -> router -> specialists -> critic -> HITL gate.

All tools are local mocks and the human approval is simulated (demo mode).
"""
from agent.loop import run

if __name__ == "__main__":
    print("=" * 64)
    print("AGENTIC-AI-PATTERNS DEMO — illustrative simulation, no real tools run")
    print("=" * 64)
    for line in run("triage ticket INC-1042", demo_mode=True):
        print(line)
