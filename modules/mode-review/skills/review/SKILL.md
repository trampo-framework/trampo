---
name: review
description: Review one change request at its head commit and write one findings file that the evidence checker accepts. Read-only. Use for "review this change", "review request R-3".
---

Open through the core `session` skill (kind `review`, subject the review's id), then follow `modes/review.md`. Write findings from `${CLAUDE_PLUGIN_ROOT}/templates/findings.json`, run `python3 ${CLAUDE_PLUGIN_ROOT}/../../core/scripts/review_check.py` over them, and post only what it keeps, through the code-host slot's `comment` verb. You never approve or merge.
