# Mode: card session

One session drives one work item (a card) from intake to done. The main thread reads, decides, records and gates; it
does not implement. Implementation, QA and review run in helpers picked per task, each briefed to do the work itself
and to seed its own task list. The goal is not "did the card ship" but "why did a person have to speak after intake":
a card that ships and teaches nothing is a failed run. The team edits this file directly.

**Record:** `sessions/<card>/session.md` from the mode's template; every other file for the card (goal, plan, QA
reports, evidence) sits beside it. **Ledger kind:** `card`.

## Before you start

1. Open through the `session` skill (kind `card`, subject the card's id) before anything else.
2. Read the most recent `sessions/*/session.md` for the same repository: its interaction log holds the last card's
   conventions nobody has promoted yet. Read the last few sessions' touches by cause (`event.py report`): the dominant
   cause is what this run must improve.
3. Read the card: `slot.py . tracker read <card>`.
4. **Claim the card when this run will build it**: `slot.py . tracker claim <card>`, unless someone else already holds
   it; then say whose it is and change nothing. A run that only investigates (confirms behaviour, finishes criteria,
   reviews a proposal) writes no tracker state. In a card session a claim and a state change need no ask; every other
   tracker write (a comment, a field) waits for its own yes, and creating an item is always draft, show, wait.

## Gate log

Every gate (slice QA, full QA, review, staging, release) gets a row in the record when it happens:
`time UTC | gate | repository | base | head | verdict | evidence`. Base and head are full commit ids: head is the
exact commit tested or reviewed, base the commit it is compared against. Before relying on a gate, resolve both again:
**a changed base or head invalidates it**. Keep the old row and run the gate again. Uncommitted changes inherit
nothing. A pending, failed or skipped gate is recorded as that; neither "not yet reviewed" nor a skip is a pass.

## 1. Intake gate: nothing is built on an unconfirmed premise

Verify every claim the card makes against the code and the data, then write into the record:

- **Premise check:** confirmed, or the list of discrepancies. Discrepancies go to the card as one comment (drafted,
  shown, posted on a yes with `slot.py . tracker comment <card> <file>`), and the run stops there. A fixture is part of
  the premise: any account, environment or sample the card names is a claim to verify before anything runs against it.
- **Goal list:** the card cut into vertical slices, each buildable and checkable on its own, each with an estimate.
  Map every requirement of the card to a slice, and label anything you added as *not in the card*.
- **Requirement-to-test map**, before the first failing test: every scenario and stated rule, the test that proves it,
  and the line where that test failed first. A requirement with no row does not reach QA.
- **Path table for the card's central rule:** state the rule in one sentence, then list every path that can break it
  (each caller, job, retry and error path; search for them), each with its test or the line that shows it cannot be
  reached.
- **Open questions**, each with your recommended answer. Ask them once, together.
- **Assumed, not asked.** When you settle a question on the person's behalf (from a README, by inference from another
  answer, or by choosing a design), write it to the record's Decisions table at that moment with `assumed, not asked`
  in the By column, so the person sees it and can overturn it. Never let such a choice live only in the code.
- **Deploy topology**, read from the repository's pipeline definition: which branch deploys where, and whether a
  manual step gates it. If merging is the production deploy, every later decision depends on knowing it now.
- **Rollback plan:** the class (R0 redeploy the previous build, R1 plus a flag or config change, R2 a data fix or a
  down-migration, R3 an irreversible outside effect) and the procedure. A card with no code says so.
- **One re-run of an inherited claim:** pick the claim the whole fix rests on and re-run its cheapest check, however
  confidently it was handed over.
- **A report that a shipped fix came back** is a premise too: first read which build the reporter is on, and search
  the card's own history for the evidence being offered.

These are intake deliverables, produced without being asked, together with the agreed goal written to
`sessions/<card>/goal.txt` with concrete defaults (who implements, the order of gates, what each check must prove)
rather than blanks. Wait for the person to confirm the goal list and the answers before slice one.

## 2. Slice loop

For each slice, in order: brief a helper to implement it test first (failing test, then code, then tidy); have a
different helper check it (section 5); record the verdict and actual against estimate on the goal row. A fail goes
back to the implementer with the evidence. A slice is done when its check passes.

## 3. Full check, then share for review

1. **A full pass over every acceptance criterion** by an independent helper, briefed with the criteria and the whole
   base-to-head diff, never the implementer's summary. A green suite and a clean lint are the condition for starting
   it, not the pass. Where nothing can run locally, use the path that can run, or record the skip in `qa-report.md` as `Verdict: SKIPPED: no local path, <reason>` with
   the reason; a skip permits the push, not a claim that QA passed.
2. **A finding that names a reachable trigger is fixed, or refuted with evidence** (a trace, a test, a reproduction),
   before the push. "Theoretical" is not a refutation. Write each finding's verdict beside it: `fixed <commit>`,
   `refuted (<evidence>)` or `asked`. A fix that would change behaviour outside the card goes to the owner as an ask.
3. **Check the diff against `memory/review/`** (the team's standards, lessons and classes of defect fixed before) and
   record one line per item that applies: pass, not applicable with why, or fixed.
4. **One review round is one push.** Fix or refute every finding, ask "what does this fix break?" of the fix alone,
   then commit once and push. A finding that breaks the central rule re-runs its path table first.
5. **Open the review**: `slot.py . code-host open-review <branch> <file>`. Its description is true of the commit it
   opens on and stays true: after a push that changes what it says, rewrite it (`slot.py . code-host describe <review>
   <file>`), never append a correction.
6. **Read the review** with `slot.py . code-host status <ref>` and `slot.py . code-host findings <review>`. Triage every
   finding: fix, or refute with evidence on the review. A blocking finding gates the merge here even if the code host
   does not enforce it. A finding that says something does not exist is checked against the history before any code
   is added. **Silence never approves:** no findings, a green build, a timeout or a verdict on an earlier commit is not
   a pass for this one; record "not yet reviewed" with the time of the last check.
7. Before a pipeline run whose result you will interpret, write one sentence predicting it. Verify with the commands
   the pipeline itself runs, not only the tests the diff touched. A red pipeline is not automatically a bad commit:
   reproduce the failure before changing code.

## 4. Staging and release

1. Deploy to staging the way the repository actually deploys, and run the staging pass. An accepted trigger is not a
   finished deploy: say which one you saw.
2. **Production release is a person's act.** The assistant never merges, approves or releases. Before raising a gate,
   read the instruction that opened the session (a named class of action is already authorised), and prove the route
   exists before asking for the permission.
3. **A merge that starts the production deploy is not the deploy.** Watch the deploying step itself, record it as its
   own gate row, and watch passively afterwards: read health and logs (`slot.py . monitoring query <file>`), send
   production nothing whose cost nobody measured.
4. When a change spans two things that release on different clocks, name the safe order before either ships.
5. A card whose rollback class is R2 or R3 rehearses the rollback on staging (deploy, revert, verify) and files the
   evidence before it is offered for release.
6. **Moving the card to review means putting the evidence on the card**: one comment from the mode's proof template,
   its four headings in order, posted on a yes. A QA verdict is not a handover: the person who checks needs the
   accounts, the numbered steps and the exact expected results.
7. A staging pass is parked for review, not done. The card is done when the record shows four things, each written
   only when it happened: the developer review and the owner review (on a person's statement, never your judgement),
   the merge and the release (read back and checked).

## 5. How QA runs

- Prove the input path before planning around it: one throwaway action and the observation that shows it worked.
  Before recording a tool or a permission as a blocker, check whether another tool supplies the same capability.
- QA is an independent helper, not the implementer, given only the criteria, the full diff with its base and head,
  the runbooks for the systems involved (`runbooks/`) and its tools. It derives its own evidence and tries to break
  the change, beyond the happy path. Each pass is appended to `sessions/<card>/qa-report.md` (template:
  `qa-report.md`), and each pass ends with exactly one verdict line, at the start of a line and with nothing after
  the word: `Verdict: PASS`, `Verdict: FAIL` or `Verdict: CANNOT-VERIFY`. Tell the helper to write that line as its
  last line. The last verdict line in the file is the card's QA verdict.
- Three verdicts: **PASS** with evidence; **FAIL**, which goes back to the implementer; **CANNOT-VERIFY**, which means
  the runbook was not enough: update the runbook, then run again. Never proceed past it.
- **A card closes as done only on a last verdict of PASS.** The close command reads that one line and refuses a done
  close on FAIL, on CANNOT-VERIFY, on a missing report and on a report with no verdict line. The one exception is a
  recorded skip, `Verdict: SKIPPED: <reason>` (no local path to test): the card may close as done once an approver
  says yes to closing it that way, naming the card ("Yes, close <card> as done without QA"). The close command asks
  for that yes when it runs; show the approver the reason first. FAIL and CANNOT-VERIFY are never closed by a yes.
  Any other card whose QA cannot run now is parked with what it waits on, never closed as done. The command reads a line of a file this session can
  write: it does not know whether the helper was independent or ran at all. That part is this rule, kept by you.
- Review rounds do not replace one adversarial pass, and more of them do not help: after two clean rounds on one
  question, send QA at it instead of a third.
- What QA learns about a system goes into that system's runbook; what it learns about the card stays in the record.

## 6. Interaction log: written as it happens

Every message from the person gets one row at the moment it arrives: `time | phase | cause | what was needed | why |
the answer that already existed`. Phase is intake, slice, pre-push, staging-release or close-out. One cause per row,
from the ledger's list: `criteria`, `direction`, `verification`, `tooling`, `collision`, `approval-gate`, `intake`,
`other`; a correction outranks a clarification. Cite where the answer already was (the goal, a rule, an earlier
message), or `none`. When a direction was already answered, apply it and repair the brief now. After a compaction,
first write a row for every message since the last one. The count that matters is every cause except `intake` and
`approval-gate`. A person narrowing, widening or correcting the card's scope or direction is a counted interaction
(`criteria` or `direction`), in whatever phase it comes.

## 7. Close-out: blocked until the memory table is complete

1. **Memory promotion, for every counted interaction:** exactly one of a new memory entry, a correction to an entry, a
   runbook update, or `no durable lesson` with the reason. A cause that repeats on the next card means the prevention
   failed: fix the defaults in this file as well. Calling it "a product decision" is not by itself a reason for `no durable
   lesson`: when a person changed the scope, the lesson is about how the session scoped the work (for example: keep a
   card to what was asked and offer extras as separate cards).
2. **One lesson at most:** `cue` (the shape of the situation, not the card's facts), `lesson` (an edit to a named
   file), `scope`, `evidence` (causes and card ids) and `contrast` (an earlier card where the same cue went the other
   way). No contrast means `no durable lesson`. A lesson is not assumed to help: an edit made from it is judged later
   (core `retro` skill).
3. **Retrospective**, scoped to the card: a gate that did not earn its cost, a template field nobody filled, a cause
   that never discriminates. What it finds edits this file or the template now.
4. Write the one line: what would have made this card need no improvable interaction.
5. **System facts go to the runbooks.** List what this card learned about a system, as opposed to about the card: a
   moved screen, a renamed table, a sign-in step, a new step in a flow. Write each into `runbooks/systems/<system>.md`
   or `runbooks/flows/<flow>.md` now, in this session. A fact seen on the test environment is written as `(observed)`;
   one read from code or told by someone and not seen is marked `_(verify)_`, and a changed step of a flow sets the
   flow's `status:` back to `not-yet-replayed`, as a first-load draft would be. What was checked for this card alone
   stays in the record. Then write one line in the record's close-out: `runbook: <the paths changed>`, or
   `runbook: none learned`. In a workspace with no `runbooks/` folder (the runbooks part is not installed), keep the
   facts under the close-out and write `runbook: left in <where>`; nothing fails. A done close warns when the line
   is missing, and is refused only when the line names a runbook that is not a file.
6. Tag the touches and close through the `session` skill, at true close and not at parked-for-review. Waiting on
   someone else's move is a park, with what it waits on.
7. Commit and share before starting the next card.
