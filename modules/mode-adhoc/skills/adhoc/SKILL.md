---
name: adhoc
description: Open or resume an ad-hoc session in a Trampo workspace, for work that is not a card or a triage (research, a write-up, a spike, a change to the workspace itself). Use for "start a session on X", "open an ad-hoc session", "pick up where we left off on X", "resume the X session".
---

Run the core `session` skill, kind `adhoc`, and follow `modes/adhoc.md` in the workspace. The team owns that file and
may have changed it; it wins over anything here. A new record starts from `${CLAUDE_PLUGIN_ROOT}/templates/session.md`,
copied to `sessions/<slug>/session.md`.

A work item to build is a card (`card` skill). An alarm or a report to judge is a triage (`triage` skill).
