---
name: read-ledger-export
status: proposed
approved-by:
---

# Skill proposal: read-ledger-export

<!-- Replace the example. status: is proposed until an approver approves this by name; the skill is then added under
.claude/skills/<name>/ in the workspace, with their name under approved-by: and status: added. -->

## Why

The trigger, with its evidence as counts and names only:

- the runbook step it unblocks: `runbooks/flows/place-order.md` step 2 reads the ledger export, and no connector
  this team uses can read it;
- or the repeated task: the session summary shows the program `ledgerdump` run 14 times and failing 9 times as "not
  installed".

Why a connector the team already has does not cover it.

## Draft

The whole skill, as it would be added. It does one thing. It names no file of this workspace and no path on one
machine, so it loads where there is no copy of either.

````markdown
---
name: read-ledger-export
description: Read one day's ledger export and print its totals. Use for "what did the ledger export say for <date>".
---

1. Ask for the date.
2. Run `ledgerdump --date <date> --totals`. It reads the export with the reader's own access.
3. Print the totals. Never print a row.
````

## Before it is added

- What access it needs, and who holds it.
- What it must never do (write, print a record, reach production).
- How a person can check it does what it says.
