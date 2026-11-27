# Gates

How an action that waits for a person gets its yes, what the assistant may never change, and what each check does and
does not stop. The code is `scripts/hooks.py` (the gate hook), `scripts/approval.py` (how a yes is read) and
`scripts/prepush.py` (the boundary on git).

## What is gated

- **The team's gated commands.** `gated_commands:` in `workspace.yaml` maps a plain name to a pattern over the words
  of a shell command (`send to a client: slot\.py \S+ ask notify`). A matching command waits for a yes.
- **Control files.** `workspace.yaml`, `constitution.md`, `memory/shared/grants.md`,
  `memory/shared/approval-gates.md`, `.claude/settings.json`, and everything under `slots/`, `agents/`,
  `.claude/hooks/`, `.claude/agents/` and `.claude/skills/`. They decide what the assistant may do. `modes/` is not on
  the list: working instructions are edited directly.
- **Outside the workspace, when the team turns it on.** With `outside: ask-first`, a file tool's write outside the
  workspace, the temp folder and the working areas a person declared (`areas` in the machine's config folder) waits
  for a yes. Off by default; setup turns it on when the team's changes pass no review before they take effect.

Settings, approvers, gates and grants are read from the team's shared copy (origin's branch on git). An edit in one
working copy, such as adding oneself as an approver, counts for nothing until it has been approved and shared.

## The first control files: setup, once

A new workspace has no approver yet, so nobody could approve its first control files. `scripts/setup.py` builds them,
and only while there is no workspace: the team's copy holds none (on git, the shared repository has no branch or no
`workspace.yaml` on it, and no commit in the folder ever held one; on a shared folder, no ledger) and the folder names
no approver. It prints a summary of what the control files will say, and writes only after the person running setup,
who must be one of the approvers the summary names, typed their agreement to the setup in that sitting, after the
summary as it reads now was shown. The agreement is recorded in the ledger as the founding approval (`gate: founding`),
the first commit carries it as `Approved-by:`, and the same command makes the first share. On a machine with no git user name, the name the person gave
in the interview is shown in the summary and set for that workspace only. Once the team's copy holds
a workspace the command refuses, and everything below applies. A free-form write to a control file waits for an
approver in every state, this one included.

## How a yes is given

Three things open a gate, and the assistant can write none of them.

1. **A typed yes.** A message a person typed in this session (a transcript line the runtime marks as a person's) that
   names the subject and agrees. The reader judges the sentence that names the subject and the sentences beside it:
   the message is a yes when a sentence with a yes word, and no refusal or condition word, names the subject or is
   followed on the same line by the sentence that names it. It is a no when the sentence naming the subject, or the
   next sentence on its line, holds a refusal word (no, not, don't, wait, hold, stop) or a condition (if, unless,
   until, once, after, when, before, only, first, but, yet), or when the message holds a refusal of fewer than four
   other words. A refusal about another point, in a sentence that does not name the subject, is not read. A message
   that is neither is ignored, and the latest message that is one or the other decides, so a later no wins. When in
   doubt it is a no. It counts only when the person at the keyboard, as the machine names them, is an approver.
   Otherwise the assistant hands over the exact draft, says who can approve, and parks.

   For a file change that waits outside the workspace the subject is the file's name. While that write is the only
   one waiting in the sitting, a yes typed after it was refused may also name it by the words of its file name the
   hook printed (a code such as `acct-77` whole, a word of five letters or more by its start). With two or more
   waiting, the yes names the file. When the file's path matches one of the team's `gated_commands` patterns, the
   approval is recorded under that gate's name.
2. **A bare yes through the ask-a-person slot.** The command ends with `# ask-yes <reply id>`. The reply must be the
   approver's latest on an ask for the same subject, not withdrawn, and a bare yes: any other word may carry a
   condition. A yes with a condition is not recorded; it is a new question once the condition is met.
3. **A standing grant** in `memory/shared/grants.md`: gate, scope and holder required; target, ceiling, expiry and
   review date optional. It must name an approver and where they said yes.

A gated command needs an open session and must name the session's subject: a yes is for one subject. When the hook
reads a yes it writes an `approve` line to the ledger with a hash of the message it read; `event.py approvals` lists
them. Nothing else writes that line, and `event.py emit` refuses to.

When an approve line is checked later, the typed message is looked up in the runtime's own transcript of that
sitting, found by the sitting's id in the runtime's folder for this workspace. A path written in the ledger is never
read, another workspace's folder is never read, a link is refused, and only a line carrying the same sitting id
counts. At a push the folder is the one written into git's hook when it was installed (by the session start step,
from the transcript path the runtime gave it), never one the pushing process's environment names. So the yes for a control file is typed in a session opened at the workspace root.

An unanswered ask is a no. The ask goes in "Needs you" with what a yes and a no would each change.

## The never list

No grant opens these: approving or granting, and changing the gates, approvers, agents, grants, slots, hooks,
settings or core rules. A grant that names one stands for nothing, and the health check fails it. A person does them,
through a change an approver said yes to by name.
Strong actions (production, merge, release, creating a tracker item) can be granted only with `Target:` naming the
exact target and a holder that is not `any`. A team adds a gate of its own to the strong ones by listing its name under
`strong_gates:`.

## Changing a control file

- **storage: git.** The edit waits for an approver's yes naming the file (`workspace.yaml`, `.claude/settings.json`). A folder is named with its slash (`slots/`, `agents/`,
  `.claude/hooks/`, `.claude/agents/`) or by the path of the file in it: the folder's word alone does not count. Its
  commit carries `Approved-by: <approver> <reference>`, where the reference is the id `event.py approvals` shows. The
  pre-push hook refuses a push to the team branch whose control-file changes lack that line, name someone the team's
  copy did not list before the push, or cite a yes that was not recorded.
  A record new to the team's copy is read against its transcript on the pushing machine and refused without it, so
  it is pushed from the machine where the yes was typed; one the team's copy already holds stands on any machine.
  One record covers one commit: a record another commit already cites is spent. The text of the change is not bound
  to the yes; the branch rule on the code host is what stands behind that.
- **storage: files.** The file changes only through `event.py journal --approval proposals/<file>.md`, after an
  approver said yes to that proposal by name; the proposal lists the file under `target:`. The health check fails a
  control file written any other way.

## What the assistant never writes

The gate hook refuses a session's write to: the declared name and working areas in the machine's config folder; the
git user name; the ask-a-person records under `.trampo/state/ask/`; the session ledger under `telemetry/events/`;
the runtime's own transcripts (`.jsonl` files under its `projects/` folder, in any case, by a full path or one
relative to the command's working folder); git's installed hooks, in any repository and wherever this one keeps them. It refuses a
push that skips git's own hooks or sets a variable that moves the runtime's transcript folder or git's own
configuration and programs (`CLAUDE_CONFIG_DIR`, `HOME`, `XDG_CONFIG_HOME`, `GIT_DIR`, `GIT_EXEC_PATH`, any
`GIT_CONFIG` variable), and the hooks' installer run with a home or config folder set on the command. A push that
sets any other variable on its own command line, a proxy or a connection setting for example, is not refused.

A `gated_commands` pattern is tested against every word of each part of the command, with a short list of
exceptions for text that is only recorded or printed: a commit or tag message; the quoted notes handed to the event
script, where that script is the program the part runs (after variable assignments, an optional python and a path) and the part runs no shell, `eval`, `-c`, `xargs` or `ssh`; a heredoc body kept by `cat`, `tee`, a commit or the event script on a line with no pipe; and a part that
only reads or prints (`cat`, `head`, `tail`, `less`, `ls`, `wc`, `diff`, `echo`, `printf`, a search, `git show`,
`git diff`, `git status`, `git log`) and sends its output to no file. A part that redirects its output (`>`, `>>`,
`>|`) or runs `tee` is always tested, the file it writes included, and so is everything on a line that pipes into
a shell or an interpreter. An entry with no pattern gates nothing, and the health check fails on it. The installer, run by a session, does not take the transcript folder from its environment.

## How the checks behave

Each check has a mode under `hooks:` in `workspace.yaml`: `block`, `log` or `off`. A new check starts as `log`: it
writes what it would have refused to `.trampo/state/hook-log.jsonl`, and blocks once its hit rate is known. Every
hook lets the call through when it cannot tell, because a failing hook must never stop a session. The one check that
refuses when unsure is git's pre-push hook.

## Every hook is a check against a confused assistant

A hook reads typed text and the session's own records. It stops an assistant that lost track of a rule; it does not
stop one that is trying. Known ways past, all confirmed on the system these hooks were ported from:

- A hook that reads a command is passed by rewording it: quoting, a variable, a wrapper script, a function, command
  substitution, a tool the wiring does not list.
- The stop hook sees files written with a file tool, the session's own ledger, and changed files that one of the
  session's shell commands, as the hook reads it, wrote onto. A file written in a way the reader does not
  recognise is not seen.
- A hook that times out or throws lets the call through.
- The transcript and the bridge records a yes is read from are ordinary files on the machine, and so is git's hook
  file with the transcript folder written in it. The guard on them is a hook that reads commands: a folder copied
  or moved into place, a path reached after a `cd`, and a write from another language all get past it.
- A machine where no session has run has no pre-push hook, and a person can skip it.
- The hook is installed only in the workspace repository's own hooks folder. A repository whose own `core.hooksPath`
  a person set to another folder gets no hook until they unset it, and the session start says so.

So each gated action names a **backstop outside the hook**, under `backstops:` in `workspace.yaml`. Setup asks for
one per gate, and the health check warns while one is missing.

| Gated action | What the product ships as the check | The backstop a team must hold outside it |
| --- | --- | --- |
| A team's gated command | gate hook | a credential the assistant's account does not hold, or the other system's own approval step |
| A control-file change reaching the team branch | gate hook, then the pre-push hook | a branch rule on the code host: required review, no direct push |
| A yes through the ask-a-person slot | gate hook reads the slot's records | the slot reports who answered from the tool's account data, and its records are kept where sessions cannot write, when the tool allows |
| A file change outside the workspace | gate hook, when turned on | file permissions, or review before a change takes effect |
| Sharing every turn | stop hook | a periodic check outside any session that reports unshared files |
| A push that skips the hooks | gate hook | the same branch rule |
