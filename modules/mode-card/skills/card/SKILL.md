---
name: card
description: Drive one work item (a card) end to end in a Trampo workspace, from an intake gate through slices, an independent check, review and release, then turn what a person had to say into memory. Use for "run this card", "start the card", "work on <card id>", "close the card".
---

Open through the core `session` skill (kind `card`, subject the card's id), then follow `modes/card.md` in the
workspace. The team owns that file and may have changed it; it wins over anything here. The record starts from
`${CLAUDE_PLUGIN_ROOT}/templates/session.md`, copied to `sessions/<card>/session.md`; the comment that puts the evidence
on the card is filled from `${CLAUDE_PLUGIN_ROOT}/templates/proof.md`.

The main thread reads, decides, records and gates. Helpers implement, check and review; each brief tells the helper to
do the work itself, to seed its own task list, and what its check must prove. Close through the `session` skill.
