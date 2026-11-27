---
name: mode-agents
version: 0.5.0
kind: agents
seeds:
  - seeds/modes/agents.md
gates:
  create a tracker item: (?:slot\.py \S+ |slots/)tracker create
  assign an item to an agent: (?:slot\.py \S+ |slots/)tracker assign\b.*<agents>
---

# mode-agents

Agents that run with no person at the keyboard: the card agent that works items assigned to it, the monitor that keeps those agents running, the release monitor that watches finished items, and card triage that drafts items for approval.

Depends on: core, the tracker, ask and code-host slots (monitoring for the release monitor), and mode-card for the worker a tick starts. The deterministic tick is `core/scripts/agent.py`; this module adds the prompts, the loop wrapper and the working instructions. Takes nothing else.
