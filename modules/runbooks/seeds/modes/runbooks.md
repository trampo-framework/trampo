# Runbooks: the first load, keeping them true, and replay

The rules and the index are in `runbooks/README.md`. This file says how the work runs. The team edits it directly.
`RB` means `python3 -B "<the runbooks part>/scripts/runbooks.py"`; the skills give the full path.

**Record:** `sessions/<subject>/session.md`, opened and closed through the core `session` skill. **Ledger kind:**
`adhoc`.

## Setting up

Ask the person one question: **does the team have a test environment an assistant may run against?**

- No, or not sure: write nothing. Replay stays off, and every runbook stays a draft until a person confirms it.
- Yes: ask its name and who may reset it. Replay is turned on by adding this to `workspace.yaml`, a control file
  that changes only on an approver's say-so naming it:

  ```
  runbooks:
    replay: on
    test_environment: <the name the team uses for it>
  ```

## The first load

Run once, by a person, on day one. It reads; it runs nothing. **Nothing is run against a live system**, a test
environment included: no request, no query, no sign-in, no job.

1. **Sources.** The person names each code repository and document folder. `RB pin <source>...` names each at its
   commit (a document folder at today's date). Every stamp cites that name and commit. Read code only as
   `git show <commit>:<path>` in the person's copy: never the working folder, never a fetch, a checkout or a write.
   Never open a file that holds credentials or environment settings.
2. **Inventory.** `sessions/first-load/inventory.md`, from the template: per source, the systems it holds and each
   system's features, each with its entry point as file and line, what covers it today, and the gap. Mark anything
   not read as `(inferred)`. `RB inventory-check` must pass.
3. **Drafts.** One system runbook per system and one flow per main feature, from the templates. Every traced step
   carries its stamp, every flow starts `not-yet-replayed`, every system file starts `basis: code` or `documents`.
   Add each file's line to the index.
4. **A large codebase is fanned out: one writer per system.** With more than three systems, or a system of more than
   about 25 features, give each system to its own writer with the shared brief
   (`templates/first-load/writer-brief.md`) and that system's inventory section. A writer edits only its own runbook
   files and its own notes; the session that fanned out reads each result, checks cited lines, and commits.
5. **Questions.** What the code did not settle goes to `sessions/first-load/questions.md`, one row each, with what
   was read and what an answer would change. Never guess an answer into a runbook. A question you settle yourself, from
   a README or by inference, keeps its row with the answer taken and `assumed, not asked` under By.
6. **Unblock list.** Access a replay would need and the load does not have (an account, a test record, a sandbox of
   an outside party) goes to `sessions/first-load/unblock-list.md`. A step that waits on a row says `waits: U<n>`
   and the flow moves on.
7. **Skill suggestions** (below).
8. **Close.** Run the health check. Tell the person plainly: these are drafts from reading, none has been run, and
   here are the questions.

## Skill suggestions

Part of the first load, and repeatable later.

1. Ask the person for the folder that holds their own earlier assistant sessions. Run
   `session_summary.py <folder> --out sessions/first-load/skill-usage.md`. **Only that summary enters the workspace:**
   tool, connector, skill and program names with counts, and a fixed label for what failed. It carries
   no session content and no personal data. Never open a transcript yourself, and never copy from one.
2. List the connectors and skills this session can see.
3. Write `sessions/first-load/skills.md` from the template, in three lists: needs **covered already** by an existing
   skill or connector; gaps **worth a new skill**; and what could **not be classified**.
4. The test for a new skill: a runbook step, or a task the summary shows repeated, is blocked on something no
   connector can do. A need a connector already covers is never a new skill.
5. Draft each new skill as `proposals/skill-<name>.md` from the template. A drafted skill is small, does one thing,
   and must not depend on the workspace: it names no workspace file, so it loads on machines with no copy of it.
6. **An approver approves each one by name before it is added.** On their yes naming it as `skills/<name>` ("Yes, add
   skills/<name>"; the name alone is not enough, since it may be an everyday word), write it to `.claude/skills/<name>/SKILL.md` in the workspace, then set `status: added` and their
   name under `approved-by:` in the proposal. A skill file is a control file: the write waits for that yes, and its
   commit carries the `Approved-by:` line. A team that keeps its skills somewhere else adds it there by hand.

## Keeping runbooks true

- Before work on a system, read its system file, `## Local` first.
- What the session learns about the system goes into the runbook before the session closes, in the same commit as
  the work that found it.
- Editing a step of a verified flow sets it back: `RB flows . --reset` does it, and the health check fails until
  then.

## Replay, when it is on

A second agent, never the writer, runs one flow from the flow file alone, on the test environment `workspace.yaml`
names. Brief it with `templates/replay-brief.md`. It writes a record from `templates/replay-record.md` and never
edits the flow.

- **PASS as written:** `RB verify . <flow> <record>` sets `verified`, the date and the record.
- **Anything else:** apply the edits the record supports, relabel the steps it saw as `(observed)`, keep
  `not-yet-replayed`, and replay again.
- A replay that corrected only prose still passes as written; name the corrections in the record.
- A step that depends on a clock is written so the replay causes the event on its own record; a real wait is the
  exception and says why.
