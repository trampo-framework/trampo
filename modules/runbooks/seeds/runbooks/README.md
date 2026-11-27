# Runbooks

What the team knows about its systems, written so an assistant that has never seen the code can act on it. The
working instructions are in `modes/runbooks.md`.

## Layout

- `systems/<system>.md`: durable knowledge about one system: what it is, where it runs, how to sign in, its entry
  points, the data it owns, what it calls and what calls it, where its logs are, and whether it runs locally.
- `flows/<flow>.md`: one end-to-end scenario, as numbered steps an agent can follow literally. It names its system
  file by path.
- This file: the rules and the index.

## Rules

- **Runbooks describe systems, never a single piece of work.** What was checked for one work item stays in that
  item's session record.
- **What a session learns about a system is committed to that system's runbook in the same session.** A moved
  screen, a renamed table, a new step: the runbook changes before the session closes.
- **A runbook written from code or documents is a draft, never fact.** Code reading alone has produced wrong sign-in
  screens, columns that did not exist and the wrong database engine. A system file says `basis: code`, `documents` or
  `observed` in its front matter; a detail nobody has seen is marked `_(verify)_`.
- **Every step is labelled** in its heading: `(observed)`, seen on the test environment, or `(traced from code)`,
  read from source and not driven. A traced step ends with its stamp:
  `_Written <date> from code at <source>@<commit>; not yet replayed._`
- **A flow's front matter** carries `status:` (`not-yet-replayed` or `verified`), `system:`, `waits:` (`none`, or the
  row of the unblock list it waits for) and `last-replay:` (`none`, or the date and the record of the last replay).
- **Only a passing replay by a second agent sets `verified`.** An edit to a step (a command, an input, an expected
  value, the order) sets it back to `not-yet-replayed`, because the replay did not run that text. A correction to
  prose outside the steps does not.
- **No machine-local paths.** A runbook is read on every machine. Cite code as `<source>@<commit>:<path>:<line>` and
  a workspace file by its path from the workspace root. A session's own evidence may keep the path it ran from.
- **Each system file has a `## Local` section:** whether the system runs on a developer's machine, how, and which
  flows can run against that copy.
- **A step that would reach a real customer, move money or call an outside party stays out of the flow** and is
  listed under "Not replayable" with the reason.

## Index

Systems:

Flows:
