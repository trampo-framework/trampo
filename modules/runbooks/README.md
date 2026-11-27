# Runbooks

A part of Trampo a team can take on its own. It gives a workspace a place for what the team knows about its
systems, a way to load that knowledge from code on day one, and a way to find out which of it is true.

## What it is

- **System runbooks** (`runbooks/systems/`): durable knowledge about one system.
- **Flow runbooks** (`runbooks/flows/`): one end-to-end scenario as numbered steps an agent can follow literally.
- **An index and the rules** (`runbooks/README.md`): runbooks describe systems, never a single piece of work; what a
  session learns about a system goes into its runbook in the same session; every step says whether it was observed
  or traced from code; no path from one machine; each system says whether it runs locally.
- **The first load:** a person points it at repositories and document folders; it writes an inventory, draft
  runbooks, the questions it could not settle, the access a replay would need, and skill suggestions. It reads at a
  pinned commit and runs nothing.
- **Replay:** a second agent runs a flow from the file alone on the team's test environment. Only that sets a flow
  to verified. Off by default.

A runbook written from reading is a draft. Reading code alone gets sign-in screens, column names and even the
database engine wrong, so nothing here presents a draft as fact: every traced step carries a stamp until a replay
has run it.

## Install it alone

It needs the core and nothing else: no card mode, no triage, no slots filled.

```bash
claude plugin marketplace add trampo-framework/trampo
claude plugin install trampo-core@trampo
claude plugin install trampo-runbooks@trampo
```

In an empty folder run `/trampo-core:setup` and choose no modes. Then `/trampo-runbooks:first-load` copies
`runbooks/README.md` and `modes/runbooks.md` into the workspace on its first run. In a workspace that already
exists, the same command adds them and changes nothing else.

## Day one

`/trampo-runbooks:first-load`, with the person at the keyboard:

1. It asks whether the team has a test environment. Without one, replay stays off.
2. The person names the repositories and document folders. Each is pinned to its commit.
3. It writes `sessions/first-load/inventory.md`: systems, features with file and line, and gaps.
4. It drafts one system runbook per system and a flow per main feature. With more than three systems it gives each
   system to its own writer, all on one shared brief.
5. It leaves two lists for a person: `questions.md` (what reading did not settle) and `unblock-list.md` (access a
   replay would need).
6. It asks for the folder of the person's earlier assistant sessions and summarises it as names and counts only.
   From that, and from the connectors already in use, it proposes which needs are covered, which are worth a small
   new skill, and what it could not classify. Each new skill is a file under `proposals/` until a person approves
   it by name.

Nothing is run against any system during the first load. The session summary holds tool, connector, skill and
program names with counts, and a fixed label for what failed; no prompt, reply, argument, path or result text.

## Turning replay on

A person adds the test environment to `workspace.yaml`, on an approver's say-so, since it is a control file:

```
runbooks:
  replay: on
  test_environment: <the name the team uses for it>
```

Then `/trampo-runbooks:replay`. `runbooks.py verify` is the only thing that writes `verified`, and only from a
record that says the flow passed as written. Editing a step afterwards sets the flow back; correcting a note does
not.

## The health check

`/trampo-core:doctor` picks this part up when it is installed beside the core, and reports: a runbook missing
from the index; a flow marked verified with no replay record, or edited since; a step with no label, or traced from
code with no stamp; a machine-local path; a system file with no `## Local` section; a drafted skill that depends on
the workspace, or was added with no approver. `scripts/health.py <workspace>` runs the same checks alone.

## With the other parts

Nothing here needs them. When a team adds them:

- **Ad-hoc sessions:** the first load and each replay already run as sessions of that kind.
- **Card mode (`modes/card.md`):** before work on a system, a card session reads the system file, and its `## Local`
  section decides whether the check before a push runs locally. What the card learns goes back into the runbook in
  the same session; the card's own validation stays in its session record.
- **Triage:** an investigation starts from the system file and corrects it when the evidence disagrees.
- **Unattended agents and a controller (0.4):** writers and replayers are the workers a controller fans out, with
  the two shared briefs in `templates/`.
- **Slots:** a drafted skill is how a team reaches what its connectors cannot. A slot is still how a mode reaches
  the tracker or a person.

## Where each piece comes from

| Piece | Origin |
| --- | --- |
| Layout, index, the rules, statuses, labels, stamps, the writer and replay briefs, the replay record, the inventory, the unblock list, one writer per system | ported from the reference system |
| Templates for a system and a flow runbook, `basis:` on a system file | gap filler: the reference system copied an existing file |
| `verify` and the steps fingerprint that resets a flow | the reference system's rule, with a mechanism in place of convention |
| The first load as one skill, the questions list, the replay switch | new |
| Skill suggestions and the session summariser | new, the owner's addition |
