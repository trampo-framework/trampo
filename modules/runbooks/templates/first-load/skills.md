# Skill suggestions

From `sessions/first-load/skill-usage.md` (names and counts only), the connectors and skills this session can see,
and the runbook steps that are blocked. A proposal: nothing here is added until a person approves it by name.

## Covered already

| Need | Covered by (skill or connector) | Evidence |
| --- | --- | --- |
| reading a work item | the tracker connector | 212 calls, 3 failed |

## Worth a new skill

The test: a runbook step, or a task the summary shows repeated, is blocked on something no connector can do.

| Need | Blocked step or repeated task | Why no connector covers it | Proposal |
| --- | --- | --- | --- |
| reading the ledger export | `runbooks/flows/place-order.md` step 2; `ledgerdump` run 14 times, 9 "not installed" | the export is a file on a host no connector reaches | `proposals/skill-read-ledger-export.md` |

## Could not classify

| Seen | Count | What a person could say to settle it |
| --- | --- | --- |
| 6 tool calls whose name is not a plain identifier | 6 | which tool that was |
