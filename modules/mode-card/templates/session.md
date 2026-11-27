# <card>: <one-line headline>

| Field | Value |
| --- | --- |
| Card | <card id> |
| Author | <the name the machine gives, never an email> |
| Repository | <target repository> |
| Started | <YYYY-MM-DD HH:MM> |
| Ledger | <sid>, one per session, newest last |
| Status | open \| parked on <who or what> \| closed <YYYY-MM-DD> (<outcome>) |
| Incident | <incidents/<id>/ or none> |
| Risk | <low\|medium\|high> |
| Deploys | <which branch deploys where, and whether a manual step gates it> |
| Rollback | <R0\|R1\|R2\|R3>, the procedure or the runbook that holds it. Or `no code, no rollback` |

## Goal

<The card's goal in the requester's words, and how it will be checked.>

## Premise check

<`confirmed`, or the list of discrepancies and the reference of the comment that reported them.>

## Open questions (intake)

| # | Question | Recommended answer | Decision |
| --- | --- | --- | --- |

## Goal list

<One row per vertical slice. Every requirement of the card maps to a slice; anything added is marked not in the card.>

| # | Slice | Requirement | Estimate | Actual | Done by | QA verdict |
| --- | --- | --- | --- | --- | --- | --- |

## Requirement-to-test map

| Requirement | Test | First failure |
| --- | --- | --- |

## Path table

<The card's central rule in one sentence, then every path that can break it.>

| Path | Test, or the line that shows it cannot be reached |
| --- | --- |

## Gate log

<One row per gate per attempt, written when it happens. Full commit ids. A changed base or head invalidates a row:
keep it and add a new one. Verdicts: PASS, FAIL, CANNOT-VERIFY for QA (the QA helper also ends each pass in
`qa-report.md` with the line `Verdict: <word>`, which the close reads; done needs a last verdict of PASS, or a recorded `SKIPPED: <reason>` and an approver's yes); IN-PROGRESS, NOT-YET-REVIEWED (with the time of
the last check), REVIEWED (with each finding's verdict) and FINDING for the rest.>

| Time UTC | Gate | Repository | Base | Head | Verdict | Evidence |
| --- | --- | --- | --- | --- | --- | --- |

## Interaction log

<One row per message from the person, written when it arrives. One cause: criteria, direction, verification, tooling,
collision, approval-gate, intake, other.>

| Time | Phase | Cause | What was needed | Why | The answer that already existed |
| --- | --- | --- | --- | --- | --- |

## Next

<Where the next session starts, concrete enough to take cold.>

## Open

- <question or loose end, and who settles it>

## Decisions

<By is the person who decided, or `assumed, not asked` when the session settled it alone (from a README, by inference,
or by choosing a design). The person confirms or overturns each assumed row.>

| # | Decision | By | Date |
| --- | --- | --- | --- |

## Approved text

<The exact text of anything sent or run on an approver's yes, word for word, with who said yes and where. "none" when
nothing was gated.>

## Close-out

### Memory promotion

<One row per interaction whose cause is not intake or approval-gate, a scope or direction change by a person among
them. Close is blocked until every row is filled. Calling it "a product decision" is not by itself a reason for no durable
lesson: say what the session should have done differently.>

| Interaction | Action taken | Where |
| --- | --- | --- |
| <row> | <new entry \| corrected entry \| runbook update \| no durable lesson: reason> | <file> |

### Runbook

<System facts this card learned, each written into its system or flow runbook in this session. One line, read at close.>

runbook: <paths of the runbooks changed | none learned | left in <where>, when the workspace has no runbooks folder>

### Lesson

<At most one: cue, lesson, scope, evidence, contrast. Or `no durable lesson`.>

### What would have made this card need no improvable interaction

<One sentence.>
