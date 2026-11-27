---
name: retro
description: Question the process after a piece of work, and judge whether an earlier change to the working instructions helped. Use at the close of a card or a triage, for "run a retro", "did that change help", "judge last month's edits", "what should we change".
---

# Retro: learn at each close, judge each edit later

Learning happens in four places. The first two run at every close and are part of the mode. The third is a person-run
pass over several sessions. The fourth is the periodic review, on the cadence the team set. (An unattended weekly run is
not part of this release.)

`EV` means `python3 -B "${CLAUDE_PLUGIN_ROOT}/scripts/event.py"`.

## 1. At each close: promote, one lesson, then question the process

1. **Promotion, for every prompt that changed the work** (every touch whose cause is not `intake` or
   `approval-gate`): a new memory entry, a corrected entry, a runbook or instruction update, or `no durable lesson`
   with the reason. The close is blocked until the table in the record is complete.
2. **At most one lesson**, written in the record: `cue` (the shape of the situation, not this work's facts), `lesson`
   (an operation on a named file), `scope` (how the team works, or what it knows), `evidence` (causes and session
   ids) and `contrast` (one earlier session where the same cue went the other way). No contrast means
   `no durable lesson`.
3. **The retrospective** questions the process, not the facts: a gate that did not earn its cost, a template field
   nobody filled, a cause that never discriminates, a question asked twice. What it finds edits the mode file
   (`modes/<mode>.md`) or the template now, in this session, not as a described intention. Mode files are edited
   directly. A change to a gate, a grant, a slot or a core rule is out of bounds here: it becomes a proposal for an
   approver.

## 2. Judging an earlier edit

An edit is not assumed to help. Every start line in the ledger carries `modes_sha`, a hash of the team's mode files,
so sessions before and after an edit can be told apart.

1. Read the numbers: `EV report --ws . --since <day> --until <day>` for the window before the edit and the window
   after: sessions, touches per session by cause, blocks, outcomes, repeated failure classes.
2. Give the edit one verdict, with the cohort sizes beside it:
   - `too-early`: fewer than 20 sessions of that mode on either side. This is a valid answer, and the usual one.
   - `confounded`: another edit landed in the window, or the mix of work shifted. It wins over `hurt`.
   - `helped`, `no observed effect` or `hurt`: the measure the edit named moved the right way, did not move, or moved
     the wrong way.
3. `hurt`, or `no observed effect` in two windows, proposes reverting the edit.
4. Write the verdict beside the edit, in `memory/dev/` where the team keeps its list of process edits (edit, date,
   the measure it should move and by how much, verdict, cohort sizes), in a later session than the one that made it.

## 3. One bounded edit

From the numbers, find the largest gap and the one mechanism behind most of it, on two or more named sessions. Make
one small edit to a mode file, a template or a runbook, naming the measure it should move and by how much, or write
`no edit this time`. Check it against past work it was not written from before it lands, and ask the person: keep or
reject. An edit the list shows as rejected is not proposed again without new evidence.

A repeat is found by its fingerprint, not by reading: `EV report` prints every `<system>:<failure-class>` seen in more
than one session, and `memory/shared/known-issues.md` holds the sightings.

## 4. The periodic review

Every `retro.every_days` days (in `workspace.yaml`), or when a person asks, review the last `retro.window_days` days. It
is a session like any other: open one with `--kind review --subject review-<date>` and close it when the file is written.

1. On git, share first (`sync.py`), so the count covers what colleagues have shared. On a shared folder the count covers
   the folder as it has been delivered.
2. **The numbers come from a command.** Run `EV stats --ws . --since <first day of the window>`. Its first line is the
   totals line: how many sessions ended and how, how many of those stopped at least once, how many are still open, and
   how many named people wrote them. It counts sessions, never ledger lines. A team of five whose line says one person
   is a review of one copy: say so in the file.
3. Every number in the review is copied from that output. Write "6 of 13 sessions stopped", never a count of lines.
4. Write `retros/<date>.md` with the totals line quoted word for word, and two sections under exactly these headings:
   - `## Repeated causes`: each failure class `EV stats` lists under repeats, with its sessions and what would stop it
     (the edit made under part 3, the entry in `memory/shared/known-issues.md`, or why nothing changes). When there is
     none, write "None found" and how many sessions were compared.
   - `## Standing warnings`: run the health check and list every warning. One the previous review also lists has stood
     for more than a window: beside it write the fix made now, or the person asked to decide and the date.
5. The health check fails a review file without either section, and counts the newest file's totals line again over
   the same window: a line that no longer matches means work arrived since, so run `EV stats` again and correct every
   number taken from the old line.

