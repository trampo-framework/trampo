---
name: agents-monitor
description: Keep the unattended agents running: check each is alive, moving, within its rules and not leaving work unshared, act on the single highest finding, tell a person once a day. Use for a monitor tick.
---

Run `python3 ${CLAUDE_PLUGIN_ROOT}/../../core/scripts/agent.py --ws . monitor <monitor>`. It reads the agents it watches (agents/<name>.yaml `watches:`), ranks what it finds (alive, then moving, then plumbing, then paused) and posts the top one through the ask slot, each finding at most once a day. A fix to an agent's own automation is a change to a control file and waits for an approver. A quiet tick says one word and does nothing else.
