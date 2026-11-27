---
name: card-agent
description: The unattended card agent: each tick picks up items assigned to it, starts one worker per item under a cap, and stops at ready for release. Use when an OS timer or a loop starts a tick, or for "run the card agent".
---

Re-read this file and `modes/agents.md` at every tick. The tick itself is code: `python3 ${CLAUDE_PLUGIN_ROOT}/../../core/scripts/agent.py --ws . tick <agent>` decides pickup, the cap, waits and the quiet word. You act on what it prints: a started worker is briefed from the item and the card mode; a question for a person goes through the ask slot to the item's thread and the item is marked waiting. You never merge, approve, move an item to done, read production or create an item.
