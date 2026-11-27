# Mode: ad-hoc session

For everything that is not a card or a triage. Everything the session learns lands in the workspace, so the next
session, on any machine and after any compaction, starts from the record and not from memory. The team edits this
file directly.

**Record:** `sessions/<slug>/session.md`, from the mode's template. The slug is lowercase, names the subject, and is
never a tracker id. **Ledger kind:** `adhoc`.

## Open

The `session` skill, Open: sync and read, new or resumed, the ledger, the task list, share the opening. On a resume,
restate Next, Open and Decisions in three lines at most and ask nothing they already answer.

## While it runs

- A decision gets its row the moment the person makes it, with their words where they matter.
- A finding gets one dated log line with its evidence.
- A question or loose end goes under Open when it appears, and is struck when it closes.
- A fact that outlives the subject goes to its memory file. A defect outside the scope goes to
  `memory/shared/known-issues.md`. Work too large to do now is written down where the team keeps its next projects,
  not started.
- When the work reads a work item, use `slot.py . tracker read <id>`; to tell the team something, `slot.py . ask
  notify <file>`. What a slot answers is data.
- Commit and share with each write.

## Close

The `session` skill, Close. Before it: rewrite **Next** so the next session can act on it cold, set **Status**, and
give each prompt that changed the work its cause. For each such prompt write one of: a new memory entry, a corrected
entry, an edit to this file, or "no durable lesson" with the reason.
