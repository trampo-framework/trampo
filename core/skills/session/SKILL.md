---
name: session
description: Open, resume, park or close a session in a Trampo workspace, so the work keeps its information across turns, compactions and machines. Every mode opens through this skill and closes through it. Use for "start a session on X", "pick up where we left off on X", "close the session", "wrap up", "are we clean to stop".
---

# session: open and close

Two halves. **Open** gives the work a record, a ledger the prompt hook writes to, the read set and a seeded task
list. **Close** confirms the ledger is tagged and ended (or parked), the session's own files are committed and shared,
and the open tasks are named. Close never redoes a step that is already done, so it is safe to run twice.

**Running the scripts.** `EV` below means `python3 -B "${CLAUDE_PLUGIN_ROOT}/scripts/event.py"`, and a mode file's
`slot.py . <slot> <verb>` means `python3 -B "${CLAUDE_PLUGIN_ROOT}/scripts/slot.py" . <slot> <verb>`, both run from
the workspace folder. You run the commands; the person does not.

## Open

**Argument:** a subject and, optionally, one line of goal. The subject is a short plain name (letters, digits, `_`,
`.`, `-`): for ad-hoc work a lowercase slug naming the topic, for a card the card's id, for a triage the incident id
`<YYYY-MM-DD>-<slug>` naming the failure. No subject given: propose one and use it.

### 0. Route

- A work item to build or investigate: kind `card`, then hand to the `card` skill.
- An alarm, a notice or a report to judge: kind `triage`, with `--source <channel>`, then hand to the `triage` skill.
- Anything else (research, a write-up, a change to the workspace itself): kind `adhoc`, and this skill's steps are the
  whole mode, with the team's `modes/adhoc.md`.
- This assistant session already files under an open ledger (`EV open` says so and refuses): say which, and ask
  whether to close it or keep filing under it. Never work around the refusal.

### 1. Sync and read

On git, fetch first; a clean status says nothing about the team's branch. Then the read protocol in `AGENTS.md`: the
routes and gate rules the start hook said, every matching read trigger for the subject, and `people/<name>.md` for the
person here (`EV whoami --ws .`).

### 2. New or resumed

Look for the record on the team's branch (`sessions/<subject>/session.md`, or `incidents/<id>/README.md`).

- **Absent: new.** Copy the mode's template and fill the header and the goal.
- **Present: resume.** Read it from the team's branch, not a possibly stale copy. Its **Next**, **Open** and
  **Decisions** are the starting state: restate them to the person in three lines at most before doing anything else.
  A decision recorded there is not asked again.

### 3. Open the ledger

`EV open --ws . --kind <kind> --subject <subject> [--source <channel>] [--parent <sid>] [--note "<text>"]`

It prints `opened <sid>`, or `resumed <sid>` when the last session on the subject parked: a parked ledger has no end,
so the same sid carries on and nothing is written. After an end, a new sid is opened whose note names the last one.
From here the prompt hook records every prompt as a touch. Put the sid in the record's header.

### 4. Seed the task list

From the goal (and on a resume, Next and Open), write the tasks that, all completed, mean the goal is met, each an
outcome with its check. The last task is always "session closed, shared with the team".

### 5. Share the opening

Commit the record by name and share it, so another machine picking up the subject sees it is live.

### While it runs

The record is the memory; the conversation is not. Write as things happen, not at the end:

- **Decisions:** a row the moment the person decides something, with their words where they matter.
- **Log:** one dated line per finding, with its evidence (command, path and line, query).
- **Open:** a question or loose end when it appears; strike it when it closes.
- A fact that outlives the subject goes to its memory category file, and the log line points to it. A defect outside
  the scope goes to `memory/shared/known-issues.md` and the work stays on its goal. A live exposure, data at risk, or
  what the approval rules call urgent is told to a person now and the entry marked escalated, still not fixed here.
- After a compaction, bring the record up to date first: every message since its last row gets its row before any
  other work.

## Close

**Argument:** `parked`, or an outcome: `done`, `abandoned`, `no-action`, `card-raised`, `handed-off`. Absent: `done`
when nothing is left open, else `parked`.

### 1. Find the ledger

`EV close` finds it. If it says the session files under no open ledger, the work never opened one: ask once whether to
backfill. On yes, `EV open ... --note backfilled` and carry on. On no, go to step 4.

### 2. Tag, then end or park

- **Touches.** The hook counted each prompt as `untagged`. For each prompt from a person that changed the work, emit
  one tagged touch: `EV emit --ws . --sid <sid> --kind <kind> --ev touch --cause <cause> --by agent`. Causes:
  `criteria` (the request or its acceptance criteria were wrong or incomplete), `direction` (you had to ask which way
  to go, or were told again), `verification` (a person caught what the work missed), `tooling` (a tool or access limit
  forced it), `collision` (another session's work was in the way), `approval-gate` (the yes for a gate kept on
  purpose), `intake` (first clarification, nothing corrected), `other`. A wrong or stale memory entry behind a touch
  adds `--subtag stale-memory`. Prompts from a loop, another agent or a notification are counted and need no cause.
- **Park** when the work waits on a person: `EV close --ws . --park --cause <cause> [--ask <class>] --note "<what it
  waits on>"`. No end is written: the ledger stays open and reopens on the reply. The block it writes is what
  `EV waiting --ws .` lists for the team.
- **End** otherwise: `EV close --ws . --outcome <outcome>`. A `done` end needs `--goal-met "<how the requester's goal
  was checked>"`: if the work delivered less, park it and say what remains, or the requester narrows the goal on the
  record first. A triage adds `--prior found|missed|none --fp <system>:<failure-class>`.
- Before either, rewrite the record's **Next** (the first action for the next session, concrete enough to take cold)
  and **Status**, and move any unanswered question to **Open**.

### 3. Share only this session's paths

Everything this session wrote goes to the team's branch now, its ledger (`telemetry/events/<sid>.jsonl`) and any file a
shell command wrote included; the stop hook names what is left. Commit by name (`git commit -m '<message>' -- <paths>`,
after `git add <path>` for a new file), then the sync script the stop hook names. Never `add -A`, and never pull,
stash or rebase in a shared checkout. Another session's files are not yours: touch none. On a shared folder
(storage: files) memory files are written through `EV journal` and there is nothing to push.

### 4. Report

One block, in the answer shape:

- **Headline:** `closed <sid> (<outcome>)`, `parked <sid> (waits on <who or what>)`, or `no ledger (backfill declined)`.
- **Needs you:** each pending or in-progress task by its subject, a blocker by what unblocks it; "nothing" when clear.
- What was shared, the record's full path, the touch counts (tagged and untagged).
