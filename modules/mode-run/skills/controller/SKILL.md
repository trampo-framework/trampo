---
name: controller
description: Run an epic, a set of work items, in parallel with one background worker per item, sequenced on their dependency graph, with one blocker register and a confirmed evidence checklist before an item closes. Use for "run the epic", "start the run", "run these items in parallel", "run status".
---

Open through the core `session` skill (kind `run`, subject the run's name), then follow `modes/run.md` in the workspace. The team owns that file; it wins over anything here. Every record goes through `python3 ${CLAUDE_PLUGIN_ROOT}/../../core/scripts/run.py --ws . --run <run> ...` (subcommands plan, state, write, dispatch, confirm, follow, rails); never edit the ledger, phase log or register by hand.

You never implement. Briefs come from `${CLAUDE_PLUGIN_ROOT}/templates/brief.md`; the plan from `templates/plan.md`; run-only overrides from `templates/run-rules.md`.
