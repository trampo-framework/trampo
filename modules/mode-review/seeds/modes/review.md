# Mode: change-request review

One review is one change request at one head commit. It is read-only: no edits, no git writes, no network, no credentials. Ledger kind: `review`.

## Inputs

The brief (review id, head and base commits, worktree), the change's description and diff (the whole base-to-head diff every round), earlier comments and replies, the item's acceptance criteria, the team's standards and suppressions in memory, and the checked-out code at head.

## How

Read the brief and the item, then the whole diff, then what was already said before forming any finding. Read each changed file whole at head, and callers where a contract changed. Check the change against the item's acceptance criteria: a missing one is a finding only when the change claims to deliver it. Draft findings, then run the evidence rules on each.

## Evidence rules (enforced by `review_check.py`)

1. Anchored at head: the path exists, the lines are in the file at head.
2. Quoted: the quote is the cited lines' text.
3. Near the change: within 10 lines of a hunk, or naming the other end of a cross-file defect.
4. Absence is proven by a search: any claim that something is not there carries the command and its result.
5. A defect, not a preference. A suggested fix is optional and traced before it is given.
6. A finding refuted on code that has not changed since is never raised again.

## Severity and volume

BLOCKER: merging breaks production, loses data or opens a hole, and you can name the input. MAJOR: a real defect with limited reach or a missed claimed criterion. MINOR: correct today but fragile. NIT: style only, recorded, never posted. Downgrade when unsure. Fewer, true findings: at most 12 are posted, worst first. Questions are not findings: say them in the summary as unchecked.

## Posting

Only what the checker keeps, through the code-host slot's `comment`. The agent reviewing never approves, merges or resolves a finding.
