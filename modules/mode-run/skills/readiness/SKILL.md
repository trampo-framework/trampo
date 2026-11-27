---
name: readiness
description: Before a run or a card starts, collect from the owner every decision, access, value and approval the workers will need, in one numbered list with a default on each, so nobody is asked again mid-run. Use for "is this run ready", "what do you need from me", "ask me everything now".
---

Follow the Readiness section of `modes/run.md`. Look facts up and prove capabilities with read-only checks first, ask only what remains, and write `sessions/<run>/readiness.md` from `${CLAUDE_PLUGIN_ROOT}/templates/readiness.md`. Its first line carries the verdict; `run.py dispatch` refuses a worker without `Verdict: READY` for that item.
