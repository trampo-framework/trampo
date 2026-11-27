# Brief: <item id>

## Goal
One sentence: the end state, in the item's own words.

## Done when
The observable end state, each point checkable. Nothing here says "to confirm".

## Reads
The files to read before anything else: the item's session record, `modes/card.md`, `sessions/<run>/readiness.md`, the run rules.

## Rails
- You cannot ask a person. Every answer you need is in the files above or it is a park.
- You work in your own worktree and your own branch; you never push, merge or release.
- Fetch before reading. Delegate wide reads to a helper and keep only its digest.
- Write state down in `sessions/<item>/` as you go: a compaction drops what is only in your head.
- Before you call anything done, send a helper to try to falsify it. Its pass is appended to `sessions/<item>/qa-report.md` and ends with one line: `Verdict: PASS`, `Verdict: FAIL` or `Verdict: CANNOT-VERIFY`. The close refuses done unless the last verdict is PASS; anything else is fixed and checked again, or parked. If there is no local path to test at all, write `Verdict: SKIPPED: no local path, <reason>` and park: you cannot ask a person, and only an approver's yes lets a skipped card close as done.

## Park
Park only for something irreversible or something only a person can give. To park, state what is missing, who owns it, and the observable condition that resumes the work.

## Report
Your final message is the report, and the same text goes to `sessions/<item>/report.md`: the commit id, each acceptance point marked PROVEN or NOT PROVEN with its evidence, and what a person must do.
