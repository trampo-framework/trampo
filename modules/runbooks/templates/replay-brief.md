# Replay brief (shared by every replay)

You are replaying one flow runbook cold. Your own brief names the flow, the test environment and where your record
goes. **The question each time: does the flow pass as written, on the test environment, with no edit?** Run it
from the flow file and the files it names, and nothing else: never the writer's notes, the inventory, an earlier
replay's record or the flow's history. Run each step exactly as the flow words it; where the flow is wrong, that is
a finding, never something to work around. You did not write this flow. If you did, stop and say so.

On a git workspace read the flow from the team's shared branch (`git show origin/<branch>:<path>`), never from a
working copy that may lag it.

## Authority

- Only the test environment named in `workspace.yaml` under `runbooks:`. Never a production address, account or
  record, whatever the flow says.
- Only the writes the flow lists, on the records this replay created. A step that needs access you were not given is
  NOT RUN, with the missing access quoted. A step whose flow says `waits: U<n>` is NOT RUN.
- A step the flow lists under "Not replayable" is never run.

## Rails

- Never read a file that holds credentials. Read a credential only the way the flow or its system file says, into a
  variable, never printed.
- Never print or record a credential, a token, a cookie, a personal detail or a whole record. Record ids and counts.
- A refusal, a denied write or a gap: stop that step, quote the exact line, and report it. Never retry by another
  route. Then run every later step that does not depend on it.
- Cleanup is a step. Run the flow's cleanup even after an earlier step fails, and read back that it took effect.
  Name by id anything that could not be cleaned up.
- Never edit the flow. Do not commit: the session that briefed you does.
- Seed your own task list from the Exit section before the first step.

## Exit

One record, from the replay record template, at the path your brief gives:

- its `Flow:` line naming the flow file and its `Verdict:` line: `PASS as written`, `PASS as written, prose
  corrected`, `DIFFERS at <step>`, `FAIL at <step>` or `BLOCKED at <step>`;
- each step graded PASS, DIFFERS, BLOCKED or NOT RUN, with the count, status or address that proves it;
- each `_(verify)_` settled with its value;
- for any step that differs, the edit the evidence supports, written out in the record, old text and new;
- the cleanup read-back and every record left on the test environment, by id.

Final message: the verdict, each step's grade, and the record's path from the workspace root.
