# First load writer brief (shared by every writer)

You are one writer in a first load. Your own brief names one system, its inventory section, the sources at their
pinned commits, and the files you write. The goal: runbooks deep enough that someone who has never seen the code can
check any main feature of the system. A second agent may later replay your flows from the flow file alone, so write
every step so it can be run without you.

## Read

- `runbooks/README.md`, the rules.
- Your inventory section, `sessions/first-load/questions.md` and `sessions/first-load/unblock-list.md`.
- Any system or flow runbook your inventory section names.
- Code, only at its pinned commit: `git show <commit>:<path>` and `git grep -n <pattern> <commit>` in the copy you
  were pointed at. Never the working folder. Never fetch, check out or write there.

## Write

- `runbooks/systems/<system>.md` from the system template: `basis: code`, the stamp under the title, a `## Local`
  section even when the answer is "not known", and `_(verify)_` on each detail nobody has seen.
- One flow per main feature from the flow template: `status: not-yet-replayed`, `last-replay: none`. Each step is
  labelled `(traced from code)` and ends with `_Written <date> from code at <source>@<commit>; not yet replayed._`
- Cite every claim as `<source>@<commit>:<path>:<line>`. No path from this machine.
- A step that needs access the load does not have: add a row to `unblock-list.md`, write `waits: U<n>` and move on.
- What the code does not settle: a row in `questions.md`. Never guess an answer into a runbook.
- Every write a step makes says what it leaves behind and how the flow cleans it up.
- A step that can reach a real customer, move money or call an outside party is safe only once you have traced the
  call to where it leaves the system and cited each hop. Otherwise it goes under "Not replayable".
- Your notes, `sessions/first-load/writers/<system>.md`: commits read, each file written, what each step would
  prove, what a replay needs, drift between the code and any document, and defects you saw and left alone.

## Rails

- In this job nothing is run: no system, no test environment, no request, no query, no sign-in.
- Never read a file that holds credentials or environment settings.
- Edit only your own runbook files, your notes, and your rows in the two lists.
- Do not commit: the session that briefed you does.
- You cannot ask anyone. Decide from the evidence and say what you chose, or stop and say what is missing, who owns
  it and what would resume the work.
- Seed your own task list from the Write section before the first read.

Final message: under 200 words, each file you wrote by its path from the workspace root, and the count of questions
and unblock rows you added.
