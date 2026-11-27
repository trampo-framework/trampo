# Mode: unattended agents

Agents here run with nobody at the keyboard. Each is defined in `agents/<name>.yaml` (a control file: changing it waits for an approver), acts under its own tracker identity, holds no approver role (the health check fails otherwise) and has no credential for anything it must not do: that, not a hook, is the backstop.

## The tick

A timer outside any session starts a tick on an interval (`loop/agent-loop.sh`, installed per platform in the docs). The tick is deterministic code: pause file, pickup of items assigned to the agent, claim, a worker started through the agent's `launch` program up to its `cap`, items waiting on a chat answer left alone, items at ready for release left for a person, and one word written to `.trampo/state/agent-<name>.last` when nothing happened. Every judgement goes into the worker the tick starts.

## The card agent

Works items assigned to it, from the entry point their state gives, with the card mode's rules. It asks a person only through the ask slot, into the item's own thread, and the item waits. It never merges, approves, moves an item to done, reads production data or creates an item. Its last act on an item is ready for release.

## The agents monitor

Each tick: is each watched agent alive (a tick within twice its interval), moving (a worker with no report past `stuck_hours`), tidy (nothing uncommitted or unshared past `dirty_hours`), and unpaused. It acts on the one highest finding and posts it once a day. It never edits an agent's definition on its own.

## The release monitor

After an item is done it reads the checks of the systems the definition lists for `window_hours`, writes `sessions/release-monitor/<item>.md`, and posts only a failing verdict. No checks reported counts as failing.

## Card triage

Sweeps new alerts, known issues and unassigned items, grades each against the team's approval rules, drops anything that touches production data or money, drafts small items from the template, and shows the drafts. On a recorded approval naming the draft it creates the item, assigned to the agent, in the active sprint or one of the next two. It never creates an item on its own call.

## What a worker loads

A worker started in a worktree outside the workspace loads the plugin's hooks only when the plugin is enabled for that session. The gate hook finds its workspace through the binding the run's dispatch writes in the machine's config folder, and `run.py state` says per worker whether the gate hook was seen. Sub-agents a worker starts are not known to load the hooks; the sandbox and the missing credentials are the backstop.
