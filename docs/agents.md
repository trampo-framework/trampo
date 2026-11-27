# Setting up a controller and unattended agents

Every step runs against the mock adapters first, so a team can see the whole loop before it connects a real tracker or chat.

## 1. The workspace and the mocks

Run the core `setup` skill. It asks its questions one at a time, shows one summary, and builds the workspace on the person's typed agreement to it: the control files, the founding approval, the first commit and the first share. Nobody types a command. At the slots step choose the mock: it copies `core/mocks/slot` over the four slots and points them at one shared folder (`slots/mock-home`, first line). Check any adapter, mock or real, with `python3 core/scripts/slot_contract.py <workspace>`; it names each verb an adapter fails.

## 2. A person who can say yes

List the approvers in `workspace.yaml` under `approvers:`. An agent is never listed: the health check fails a name that is both. Run `python3 core/scripts/doctor.py <workspace>`.

## 3. An epic run (controller)

1. Install `mode-run`. Open a session of kind `run` named for the epic.
2. Create the items in the tracker with their `needs:` links.
3. Run the readiness skill: it looks facts up, proves capabilities with read-only checks, asks every remaining question once with a default, and writes `sessions/<run>/readiness.md` with `Verdict: READY` on its first line.
4. `python3 core/scripts/run.py --ws . --run <run> plan <items>` prints the steps. Show them to the owner and wait for the word to go.
5. The code repository must be listed under `repositories:` in `workspace.yaml`, and when it is listed by address, the person's copy must sit inside a folder they wrote in their `areas` file; dispatch refuses any other folder, the workspace itself and any folder that holds the workspace or the home folder.
6. For each free item: make a worktree and branch, write the brief from `templates/brief.md`, then `run.py dispatch <item> --brief <file> --worktree <dir>`. Type the command it prints. Record the move with `run.py write`.
7. Each tick: `run.py state`, read reports, `run.py confirm <item>` when a worker reports, `run.py follow` to move the tracker, share with `sync.py`.

### Four one-time steps before a worker can start

Each is done once per machine by the person whose machine it is, at their own terminal. No session and no agent does any of them for the person, and a background start stops at each one that is missing, with nobody there to see the prompt.

1. **Trust the code folder.** Start the runtime in the code repository once and accept its trust prompt. Missing, the start says "Added folder not trusted".
2. **Accept the bypass notice.** The printed command starts the worker with `--permission-mode bypassPermissions`, and the runtime shows a one-time warning for that mode. Start the runtime once with that mode, read the warning and accept it. The worker's sandbox file, which dispatch writes, is what limits it after that.
3. **Trust the workspace folder.** Start the runtime in the workspace folder once and accept its trust prompt. Missing, the start says "Workspace not trusted".
4. **Write your areas line.** The file `areas` in the product's folder under your own config folder (`$XDG_CONFIG_HOME/trampo/areas`, or `~/.config/trampo/areas` when that variable is not set) lists, one full path per line, the folders where your copies of the team's code live. You write it by hand. A session's write to it is refused, because it says where a session may work.

After typing a printed start command, run `run.py state`: an item reads "start command printed, no worker session has opened for it" until the worker has opened its session. If it stays that way, look at the runtime's own list of background sessions for the prompt that stopped it.

What a worker loads: the core plugin, named in the printed command by its folder, so its hooks load whether or not the plugin is installed for that session. The worker may write its own ledger and sitting state in the workspace, never the records an answer is read from.

Also: the sandbox and flags in the printed command, the hooks only if the plugin is enabled for its session, and the gate hook applies in its worktree through the binding dispatch writes. `run.py state` says per worker whether the gate hook was seen. Sub-agents a worker starts are not known to load hooks.

## 4. The card agent

1. In its own clone, set the git user name to the agent's name. That is the identity the tracker and the grants see.
2. Write `agents/<name>.yaml` (kind, assignee, cap, interval, launch) and a `launch` program that starts one worker for an item. These are control files: an approver says yes to them, naming `agents/` with its slash or the file's path ("Yes, change agents/card.yaml"). The word "agents" alone does not count.
3. Assign an item to the agent (`tracker assign <id> <agent>`). With the agents mode's gates in place this waits for an approver's yes, as creating an item does. Run `python3 core/scripts/agent.py --ws . tick <name>`: it claims the item, starts the worker, and writes one word when idle.
4. When a worker has asked a person something and cannot go on, it says so with `python3 core/scripts/agent.py --ws . wait <name> <item> <key>`, where the key is the one its question was asked under. The item stays the agent's and still counts in its cap: an agent with a cap of 1 holds that one item and claims no other. Only a reply from someone on the approver list ends the wait and starts the worker again. Anyone else's reply is noted in the tick's output and the wait stays. A session cannot edit the agent's state files by hand: the pool and the waits change only through `agent.py`.
5. Install the timer (below). Pause with `agent.py pause <name>`, resume with `resume`.

### An example launch program and worker prompt

The tick runs the `launch` program from the workspace folder with one argument, the item's id, no input, and a limit of two minutes. Exit 0 means a worker started. It only starts the worker and returns; it does not wait for it.

```sh
#!/bin/sh
# agents/launch-<name>.sh ITEM: start one background worker for the item and return
set -eu
item=$1
ws=$(cd "$(dirname "$0")/.." && pwd)
prompt="$ws/agents/worker-prompt.md"
cd "$ws"
env -u CLAUDE_CODE_CHILD_SESSION claude --bg "Item $item. $(cat "$prompt")" \
  --permission-mode bypassPermissions --disallowed-tools AskUserQuestion \
  --plugin-dir <the core plugin's folder> --settings <a settings file with the sandbox on>
```

The worker prompt (`agents/worker-prompt.md`), a starting point to make your own:

```text
You are the card agent <name>, working one tracker item with nobody at the keyboard.
Run the card skill for the item named above and follow modes/card.md.
Never merge, approve, release, or move an item to done: stop at "ready for release".
When you need a person, ask through the ask-a-person slot, park the session, and stop.
Done when the item's "Done when" is stated with its evidence, or a clean park is stated:
what is missing, who owns it, and what resumes it.
```

Both files sit under `agents/`, so they are control files: an approver says yes to each change. For a worker that works in a code repository, use the command `run.py dispatch` prints in place of the `claude` line: it writes the sandbox and binds the worktree.

### How an agent's own copy keeps up with the team

An agent works in its own clone of the workspace, like a person. A tick runs `sync.py` only when the agent's state changed, and once an hour for its beat; an idle tick in between does not sync. The agent's definition, its launch program and every later change to them reach that clone only when it is synced, so run `python3 core/scripts/sync.py <workspace>` there after the definitions are approved and shared, and on a timer of its own after that (the same kinds of timer as below, a few minutes apart from the tick). A worker's session start also syncs in the background.

### What the team sees of an agent

Each tick writes the agent's pool, waits, pause and last beat to `sessions/agents/<name>.json`, a tracked file, and shares it: one commit named `agent <name>: state` when something changed, none when nothing did. An idle agent shares its beat once an hour, so a quiet agent adds at most one commit an hour. A monitor in another clone syncs and reads that file, and allows the extra hour before it calls a loop stopped. The working copy under `.trampo/state/` stays in the agent's clone.

### Tracker state words

The scripts read five words from the tracker slot, exactly as written: `open`, `in progress`, `in review`, `ready for release`, `done`. The card agent picks up `open` and `in progress` items assigned to it, leaves `ready for release` for a person, and never writes `done`. A tracker with other words maps them in the slot program.

## 5. The monitors

Write `agents/<name>.yaml` with `kind: monitor` and `watches:`, or `kind: release` with `systems:`. Install a timer for `agent.py monitor <name>` or `agent.py release <name>`.

To try a monitor without telling anyone, add `--dry-run`: `agent.py --ws . monitor <name> --dry-run` prints each notice as `would tell: ...`, posts nothing through the ask slot, writes no record and shares nothing. The card agent's tick has no trial form, since a tick claims items and starts workers.

## Installing the timer

The timer is outside any session and runs `modules/mode-agents/loop/agent-loop.sh <workspace> <verb> <name>`; the script holds a lock so a slow tick never overlaps the next.

- macOS: a launchd agent with `StartInterval` set to the interval in seconds and `ProgramArguments` the script and its three arguments.
- Linux: a systemd user timer (`OnUnitActiveSec`) with a service that runs the script, or a crontab line.
- Windows: a Task Scheduler task that repeats at the interval and runs the script under a POSIX shell, or `agent.py` directly.

## The backstop

An unattended agent has no person to ask, so each gated action names a backstop outside the hook: a credential its account does not hold, or the other system's own approval step. Setup asks for one per gate and the health check warns while one is missing, and keeps warning while one is recorded as "nothing yet", "none" or the like.

## A control-file commit made outside a session

A person who changes a control file at their own terminal has no recorded approval for it, so the boundary check refuses every later push from a session in that clone. An approver settles it in a session: they are shown the commit (`git show <commit>`), type their agreement naming it by at least seven characters of its id ("Yes, I approve commit 1a2b3c4"), and the assistant runs `python3 core/scripts/prepush.py adopt <workspace> <commit>`. The record covers that one commit. It is refused for anyone who is not an approver, for a reply that came through the ask slot, and for an agent: approving stays on the list of things no agent does.

## Skills in the workspace

A file under `.claude/skills/` is a control file. A write there waits for an approver's agreement naming it as `skills/<name>` (or by its path); the name alone does not count, because a skill may be called by an everyday word. A skill's name is lower-case letters, digits and hyphens, three characters or more. One command changes one control file.

## Standing grants: who writes one

An approver decides a grant; the assistant drafts it and writes it only on that approver's typed yes naming `memory/shared/grants.md`, as for any control file. The entry is a second-level heading with a date, then `Gate:`, `Scope:`, `Holder:` and `Approved-by:`, and where they apply `Target:`, `Ceiling:`, `Expires:` and `Reviewed:`. `Holder:` is a way of working (a kind of session such as `triage`), one session id, or `any`. It cannot name a person: who may act under the grant is whoever runs a session of that kind inside the scope. It stands once it is on the team's branch.

## Other files people ask about

- **The earlier-sessions folder** (first load of the runbooks part): any folder the person names that holds the runtime's own session transcripts, read as every `*.jsonl` file under it, one JSON object per line with the message under `message.content`. Only names and counts of tools, connectors, skills and programs leave it; no prompt, reply, path or result does.
- **The handover file** (`incidents/HANDOVER.md`, triage part): three headings, `## Dated items`, `## Undated items` and `## Tooling defects`, one line per item. The person handing the rota on rewrites the whole file each time; nothing is appended.
- **The first push to an empty shared repository**: setup makes it. Give setup the address of a repository that exists and has no branch yet; its build makes the first commit, which carries the founding approval, and the first share. If the share did not go through, arrange what it names (the address, an empty repository, write access) and ask the assistant to share again (`setup.py <workspace> share <address>`). The boundary check lets the first push of the team branch through, because there is no team copy yet for a change to get past.
