# Mode: triage

Take an alarm, a notice or a report from arrival to a record the next person can use. Most of what arrives is
nothing, and the mode has to be as good at recording nothing as at diagnosing something: a no-action finding that
leaves no trace is investigated again at full cost. The team edits this file directly.

**Records:** `incidents/index.md` (a row for every triage), `incidents/decisions.md` (how each decision compared with
prior art), and for anything investigated `incidents/<YYYY-MM-DD>-<slug>/` with `README.md`, `analysis.md` and
`actions.md` from the mode's templates (optional `runbook.md`, `queries/`). The date is when it happened; the slug
names the failure and carries no tracker id. **Ledger kind:** `triage`.

**Triage never fixes.** It is read-only towards production: it records and explains. A fix lives where the code
lives, tracked as a card, and goes through a card session. An incident closes when the record is complete and the
actions are tracked, not when every fix has shipped.

## Open the ledger first

Through the `session` skill: kind `triage`, subject the incident id, `--source` the channel it arrived by (`tracker`,
`chat`, `email`, `monitoring`, `person`, `other`). The channel and the failure class together are the class of work,
so a triage with no start is invisible to every later count. If the report is a work item, mark it as being looked at
before anything else (`slot.py . tracker move <id> <state>`): one left in an intake list reads as unowned.

## 0. Is this already settled?

Before a terminal opens on the new thing, fetch, then search: `incidents/index.md`; `memory/`; the folders under
`incidents/` (their `queries/` are usually reusable as they are); the session records; the history; the tracker
(`slot.py . tracker search <words>`); the documentation of whatever owns the failing thing.

Everything this returns is a **lead, not a fact**. Re-key it on the new subject and run it again: the same notice for
another account reads exactly like a duplicate. **If prior art exists, reuse the decision and re-run its validation,
both halves.** Score the outcome in `incidents/decisions.md` as `NEW`, `CONFIRMED`, `DIVERGED` or `OVERTURNED`, with
whether the prior art was found before investigating and the minutes it cost. A prior record that names no check to
re-run gets one added by this triage. A prior record that turns out wrong is corrected in the same commit.

## 1. The gate: can you see what fired?

Read the reporter's own evidence first, attachments included (`slot.py . monitoring alarm <id>` for an alarm). Do not
write a disposition until each of these is answered:

| Question | The failure it prevents |
| --- | --- |
| Have I read the payload, or only a count? | A count carries no error text, and a small count can be one person failing every attempt |
| Is this number measured, derived, or merely shown? | A cumulative count read as an outage; a delivery delay read as an event time |
| Is the denominator what I am calling it? | "2 of 25 users" where the 25 counted something else |
| Is the key I grouped on stable per subject? | An optional free-text field in a key splits one subject in two |
| Is the source reproducible, or a one-off someone ran for me? | If reading the payload costs a person every time, the next alarm is judged from its count |
| Am I about to state a mechanism I inferred and did not read? | Read the rule, the definition, the code. A rendered label is not a definition |

**An unreadable payload is a finding, and it is raised.** Write `OPEN: payload unreachable`, name the access that
would settle it, draft the work item and show it; create it only on a yes. It does not close as no-action: a signal
never decoded cannot be judged. Raise it against the wall, not the incident: the wall outlives the incident.

## 2. Disposition

- **No action:** nothing consumes this, nobody is affected, it is routine. Add the index row (severity `n/a`, status
  `no-action`, a link to the report) and the decisions row, commit, stop. No folder. The row is the whole deliverable.
  If the triage finds a root cause, leaves an open item or drafts a card, it is no longer no-action: create the folder
  in the commit that records that finding and point the row at it.
- **Investigate:** there is a real failure, or the gate is not satisfied and the answer matters. A small count is not
  a reason to skip.

## 3. Open the incident

Copy the templates, fill the README's metadata at once even with `unknown` fields, add the index row, and **commit
before investigating**: an incident that exists only in a conversation is one interruption from gone. Severity `S1` to
`S4`; status `open`, `analysed`, `remediating`, `closed`; kind `incident`, `planned-maintenance` or `migration`. Data
taken from production never goes into git: keep it in the team's evidence store and commit a reference.

## 4. Investigate

- **Timeline before cause:** exact fire and clear times, then the shape of the signal at the finest grain available.
  For a report from a person, asking for the account and the time is the recommended action when nothing is
  identifiable.
- **Name the nearest competing explanation and run the one observation that separates them**, before a cause is said
  to anyone. Brief every helper to refute, not confirm; a helper briefed from your framing confirms you.
- **Chase the number that does not reconcile.** It is the thread to the mechanism or proof a claim is wrong.
- **Rule out before ruling in** (traffic, a deploy, the database, memory, throttling, a dependency), and record the
  number that eliminated each.
- **Say measured or traced.** Both are legitimate; presenting one as the other is not.
- Say which fields you did not look at before a number reaches a person, and send an adversarial reviewer before the
  stakeholder. Production is read through `slot.py . monitoring query <file>`, with the environment explicit and the
  window bounded. Writes and deploys are outside triage.

## 5. Record

`analysis.md` carries the evidence ledger: every material claim `PROVEN` (measured or read from code, citing the
query, metric or line), `REFUTED` (believed, then disproved: keep these and say what killed it) or `OPEN` (say what
would settle it). Say at the top which findings anyone can derive again and which came from a one-off snapshot.
`actions.md` has one row per change with its state, separating the cause from the structural weaknesses from the
cleanup. Never write an incident up from memory weeks later: say the evidence is gone.

## 5a. When a person raised it

Someone is waiting, so the triage covers three things in order. **Answer them:** draft a reply the person who relays
it can use as written, within what the product and policy allow, and show it before it is sent. **Make the next one
fast:** what would let the front line settle this kind alone, or reach the team sooner; record it in `actions.md`.
**Cards, optionally:** draft the items that remove the cause, scoped to stay safe and testable; creating one is draft,
show, wait (`slot.py . tracker create <file>` on a yes).

## 6. Capture the queries

Everything non-trivial goes in `queries/` as a runnable file whose first comment says what question it answers and
its traps: the column that makes the obvious query hang, the limit that silently truncated.

## 7. Promote, then close

Promote a fact to `memory/support/` when it holds beyond this incident: one fact per entry, a bolded one-sentence
claim, the date and the incident that established it, the evidence with exact numbers, then **How to apply:**. A
one-off answer stays on the report. An entry this triage disproved is fixed in the same commit. A defect seen on the
way, outside this incident, goes to `memory/shared/known-issues.md` under its fingerprint.

Close through the `session` skill: tag each prompt that changed the work (a sent-back draft or a changed conclusion
counts; a wording edit does not), then end with the outcome (`no-action`, `card-raised` or `handed-off`),
`--prior found|missed|none` and `--fp <system>:<failure-class>`. The fingerprint is how a repeat is found:
`event.py report` names every failure class seen in more than one session. When a card this triage raised is started,
list it in the README's `sessions:` and name the incident in the card's record, in the commit that starts the card.

## Support week

One person hosts the support rota for a week and hands it on. Taking over, read `incidents/HANDOVER.md` first: it is the only record of what the last person left open. If it is older than a week, check every item again. Run the health check before anything else.

- Watchers alert; a person starts each investigation. Arm every alert source in one go, and treat a quiet source with no readable credential as blind, not as covered.
- Mark the item in the tracker as in progress before investigating it, and move it on when the triage ends.
- Handing on: rewrite `incidents/HANDOVER.md` whole (dated items, undated items, tooling defects; an item open after two handovers becomes an item in the tracker), re-arm the watchers in the new session, and write the week's report under a new file name.
