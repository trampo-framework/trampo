---
name: replay
description: Replay one flow runbook from the file alone on the team's test environment, by a second agent, and set it to verified only when it passes as written. Off until a person turns it on. Use for "replay this flow", "verify the runbook", "which flows are not yet replayed", "turn replay on".
---

`RB` is `python3 -B "${CLAUDE_PLUGIN_ROOT}/scripts/runbooks.py"`. Run `RB flows .` first: it says whether replay is
on, on which test environment, and each flow's status.

**Replay off:** do not run anything. Say that a person turns it on in `workspace.yaml` once the team has a test
environment ("Setting up" in `modes/runbooks.md`), and stop.

**Replay on:** open through the core `session` skill (kind `adhoc`, subject `replay-<flow>`), then follow "Replay,
when it is on" in `modes/runbooks.md`. Give the flow to a second agent that did not write it, with
`${CLAUDE_PLUGIN_ROOT}/templates/replay-brief.md` and nothing else about the flow. Its record starts from
`${CLAUDE_PLUGIN_ROOT}/templates/replay-record.md`. `RB verify . <flow> <record>` is the only thing that writes
`verified`, and it refuses any record that does not say the flow passed as written.

Only the test environment `workspace.yaml` names. Never production, whatever the flow says.
