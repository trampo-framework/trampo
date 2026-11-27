---
name: triage
description: Triage an alarm, a notice or a report in a Trampo workspace, decide whether it is anything, investigate it if it is, and leave a record either way. Use for "triage this alarm", "what happened with this alert", "is this anything", "has this happened before", "open an incident", "close out the incident".
---

Open through the core `session` skill (kind `triage`, subject the incident id, `--source` the channel), then follow
`modes/triage.md` in the workspace. The team owns that file and may have changed it; it wins over anything here. An
incident folder starts from `${CLAUDE_PLUGIN_ROOT}/templates/incident/`, copied to `incidents/<YYYY-MM-DD>-<slug>/`.

Triage records and explains; it never fixes. Read the reporter's own evidence before opening a terminal. Close
through the `session` skill, with the failure's fingerprint and whether prior art was found.
