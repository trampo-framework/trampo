# Taking only some parts

A team installs the core and then any parts it wants. Each part lists what it needs.

| Part | Needs | Notes |
| --- | --- | --- |
| core | nothing | rules, hooks, protocols, setup, session, doctor, the slot runner and the mock adapters |
| mode-adhoc | core | a session with a record |
| mode-card | core, tracker slot; code-host slot to open and read the review | one item from intake to done |
| mode-triage | core, monitoring slot optional | alarms and notices, and the support week |
| mode-review | core, code-host slot | evidence rules checked in code |
| mode-run | core, tracker, ask and code-host slots, mode-card | the controller and readiness |
| mode-agents | core, tracker and ask slots; monitoring for the release monitor; mode-card for the worker, which uses the code-host slot | card agent, agents monitor, release monitor, card triage |
| runbooks | core | system and flow runbooks, the first load from code, replay; no slot, no other mode |

A part that needs a slot works against the mock until the team fills the slot. A part never reaches an outside system except through a slot.

The runbooks part is the first example of taking one part alone: [modules/runbooks/README.md](../modules/runbooks/README.md) shows the install, what it adds to a workspace and what it leaves out.
