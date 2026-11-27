# Mode: epic run

One controller session drives a set of work items to done. It never implements: it plans, briefs, dispatches, reads reports, keeps the records and shares. One worker per item, each in its own worktree and branch, running sandboxed in the background and unable to ask a person. The golden rule: no blocker in a run lands on a person unless it was settled in readiness first. Safety, then quality, then speed.

**Records:** `sessions/<run>/run-ledger.md`, `phase-log.md`, `blockers.md`, `readiness.md`, `workers/`. **Ledger kind:** `run`. Open through the `session` skill with kind `run`.

## Readiness

Before the first dispatch, once. Look up what can be looked up; prove each capability with a read-only check; then ask the owner every remaining question in one numbered list, each with a default. Record the answers and write the verdict in the first line of `readiness.md`. A question that comes up later and was not asked here is a readiness defect: record it as one.

## Plan gate

`run.py plan <items>` reads each item from the tracker and groups them into steps by what each waits on. Check two things the graph cannot show: surfaces two items both change, and items that wait on a person. Show the plan and wait for the owner's word before the first dispatch.

## Dispatch

Per item: make a worktree on a new branch, write the brief from the template, then `run.py dispatch <item> --brief <file> --worktree <dir>`. It refuses without readiness, with an unready need, with an open blocker, or with a brief that has an open point. Type the printed command in the shell yourself. Then `run.py write` the move and the worker's name. Workers load only what the dispatch settings give them: the gates apply in their worktree through the binding `dispatch` writes, and `run.py state` says per worker whether the gate hook was seen.

## The phase ladder

Intake, Coding, Local checks, Review request, Waiting build, Reading build, Waiting review, Triaging findings, Deploy to test, Waiting test deploy, Test checks, Evidence on item, Ready, Peer review, Owner review, Ready for release, Merged, Released, Done. Off the ladder: parked, Open, Abandoned. A move back names its cause in the reason: `ci:`, `review:`, `qa:`, `po:`, `reopen:`, `ext:` or `scope:`. The tracker follows the phase log one hop at a time with `run.py follow`, never past ready for release: merge, release and done belong to people.

## Blockers

One register row per missing thing, not per item: what is missing, the items waiting, the owner, the observable resume condition and the ask class. Park an item only for something irreversible or only a person can give. A blocker owned by a person goes to them through the ask slot once, with the exact thing needed.

## A tick

List the sessions. Read the phase log. Read each worker's report. Read the items from the tracker. Sweep the open review requests in a helper that returns a digest. Update the register and dispatch what is now free. When nothing is free and nothing changed, the tick is over: do not poll by hand.

## Close-out of an item

`run.py confirm <item>` reads the item's own records: a session ended done with how its goal was checked, a last QA verdict of PASS in `sessions/<item>/qa-report.md` (or a recorded skip with an approver's yes to closing the item that way), a report with a commit id and no NOT PROVEN, checks passed and no open findings on its review request. It is not re-run by hand. Workers commit and report; you share with the sync script.

## Rails said again

`run.py rails` prints the rails; the index hook repeats them at every start and after compaction while a run is open.
