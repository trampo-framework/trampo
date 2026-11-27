# Memory

Durable team memory lives in this workspace, one file per category under `memory/`, never in an assistant's
per-machine store. This file is an index of indexes: it routes to one index per category, and each index lists its
files with the trigger that says when to read them. A new file's row goes in its category's index, not here.

## Categories

| Category | Index | Holds | Read trigger |
| --- | --- | --- | --- |
| shared | `memory/shared/shared.md` | facts every mode looks up: gates, grants, the verification method, defects seen out of scope, tooling | at every start, then each matching row |
| dev | `memory/dev/dev.md` | the card loop: tests, review, release mechanics, how the team likes to work | before card work or a code change |
| support | `memory/support/support.md` | triage method, alarm playbooks, facts about the systems the team supports | before a triage |
| review | `memory/review/review.md` | standards and lessons a review checks | before reviewing a change, and before a push |

Four files are read whole only when their trigger fires: `memory/shared/approval-gates.md` before a gated action,
`memory/shared/verification-method.md` before saying a result is verified or done, `memory/shared/grants.md` before
relying on a standing grant, and `people/<your name>.md` before choosing how to work with the person here.

## Entry shape

One fact per `## heading` entry, dated, naming the session or incident that established it, ending with a
**How to apply:** line. A correction edits the entry and says `(corrects earlier claim that X)`. A claim about live
state carries its own line: `As of <date> (<source>); re-check: <command>`. Archived entries move to
`memory/archive/<file>.md`; nothing is silently deleted.
