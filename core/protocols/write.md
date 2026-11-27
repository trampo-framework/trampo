# Write protocol

Where things are written, in what shape, and what is checked.

## Memory

1. **One fact, one entry, one file.** A new durable fact is a `## heading` entry in the one category file where it
   will be looked for (not the one it is about): dated, naming the session or incident that established it, ending
   with a **How to apply:** line. No session narrative. A new file gets its row in its category's index.
2. **A correction edits the entry** and adds `(corrects earlier claim that X)`. The wrong version never stays above it.
3. **A claim about live state** (on or off, a version, a grant, a schedule) carries `As of <date> (<source>);
   re-check: <command>` on its own line. When the state changes, the old value stays as a dated past line. The health
   check fails a claim without the line, and on git the pre-push hook refuses a new one.
4. **System facts learned during QA go in the system's runbook** (`runbooks/systems/` or `runbooks/flows/`), where
   QA will look for them.
5. **A defect outside the scope goes in `memory/shared/known-issues.md`**: a new entry with the next id and its
   fingerprint, or a dated sighting on the existing entry. A person decides from its For review list. Never a tracker
   item on the assistant's own call. A live exposure, data at risk, or what the approval rules call urgent is told to
   a person straight away and the entry marked `escalated (<to whom, when>)`; it is still not fixed inside the work.
6. **Size is a prompt, not a limit.** `caps:` in `workspace.yaml` sets word counts for an index and a file; over a
   cap the health check warns and nothing is refused. Split before compressing: when three or more entries share a
   subject the file is not named for, move them out unchanged (a split is verbatim when the sorted lines match).
   Compress prose only with a person's yes, and measure in words, never lines. Obsolete entries move to
   `memory/archive/<file>.md`. `scripts/memory_review.py` reviews a category for contradictions and buried rules.
7. **Promotion at close is per tagged prompt:** each one yields a new entry, a corrected entry, an instruction or
   runbook update, or "no durable lesson" with the reason.

## Records

- An ad-hoc or card session: `sessions/<subject>/session.md`, with its evidence, briefs and reports beside it.
- A triage: a row in `incidents/index.md` and in `incidents/decisions.md` every time; a folder
  `incidents/<YYYY-MM-DD>-<slug>/` with `README.md`, `analysis.md` and `actions.md` once anything is investigated. The
  health check fails a folder missing a file or its index row.
- A record is written as things happen. Anything sent or run on a yes is kept word for word under Approved text.

## The ledger

One file per session, `telemetry/events/<sid>.jsonl`, appended and never rewritten, written only by `event.py` and the
hooks. The fields and their lists are in `schemas/event.schema.json`.

- `event.py open` starts a ledger or picks up the one left open; `close --park` writes a block and no end;
  `close --outcome` ends it. A `done` end needs `--goal-met`.
- The prompt hook writes one `touch` per prompt, `cause: untagged`, with `prompt_origin` (`human`, `loop`, `peer`,
  `notification`). At close the session emits one tagged touch per prompt from a person that changed the work.
- `--fp <system>:<failure-class>` and `--prior found|missed|none` type a failure so a repeat is found by its class.
  `event.py report` prints sessions, touches by cause, prompts by origin, blocks, outcomes and repeated classes;
  `event.py waiting` lists every block nobody has cleared.

## Sensitive data

No real user data in the workspace. On git the seeded ignore file refuses documents, archives, screenshots and
recordings; one meant for the workspace is added by name. The health check warns on text that looks like a secret, an
email address, a phone number or a street address (guesses from patterns), and on a refused file type git would take.
The session that sees a warning fixes it.

## Sharing

- **storage: git.** Commit only your own paths, by name; then `scripts/sync.py <workspace>` sends them through a
  throwaway worktree and moves the branch to origin's. Never pull, stash or rebase in a shared checkout. The stop
  hook holds a turn that leaves a file it wrote with a file tool, its session ledger or a file one of its shell
  commands wrote uncommitted or unshared; the start hook syncs in the
  background, installs the pre-push hook, and says what the last sync set aside.
- **storage: files** (a team with no git, on a shared folder). Memory and control files are written through
  `event.py journal`, which keeps every write with its whole text; the health check compares each file with its
  journal, `--rebuild` puts back a missing one, and a hand edit is shown to a person, then adopted or restored. The
  person at the keyboard is the name they declared by hand in the machine's config folder.
