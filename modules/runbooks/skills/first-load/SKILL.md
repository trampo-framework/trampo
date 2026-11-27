---
name: first-load
description: Load a team's systems into runbooks on day one, from the code repositories and document folders a person points at, read-only. Writes an inventory, one draft system runbook per system, draft flows for the main features, the questions it could not settle, the access a replay would need, and skill suggestions. Use for "load our systems", "first load", "write runbooks from this repository", "what skills would help us".
---

Run in the workspace. If `runbooks/README.md` is missing, copy `${CLAUDE_PLUGIN_ROOT}/seeds/` over the workspace
first. Open through the core `session` skill (kind `adhoc`, subject `first-load`), start the record from
`${CLAUDE_PLUGIN_ROOT}/templates/first-load/session.md`, then follow "Setting up" and "The first load" in
`modes/runbooks.md`. The team owns that file; it wins over anything here.

- `RB` is `python3 -B "${CLAUDE_PLUGIN_ROOT}/scripts/runbooks.py"`: `pin`, `inventory-check`, `flows`.
- The session summariser is `python3 -B "${CLAUDE_PLUGIN_ROOT}/scripts/session_summary.py" <folder> --out
  sessions/first-load/skill-usage.md`. The person names the folder. Never read a transcript yourself.
- Templates: `${CLAUDE_PLUGIN_ROOT}/templates/system.md`, `flow.md`, `skill-proposal.md`, and under `first-load/`:
  `inventory.md`, `writer-brief.md`, `questions.md`, `unblock-list.md`, `skills.md`.

Three things never bend. Nothing is run against any system, a test environment included. Every draft says it is a
draft: a stamp on each traced step, `not-yet-replayed` on each flow. A drafted skill is a proposal until
a person approves it by name.

Finish with the health check and tell the person what is a draft, what is asked of them (`questions.md`,
with each row marked `assumed, not asked` to confirm or correct, `unblock-list.md`, the skill proposals), and that replay is the next step once they have a test environment.
