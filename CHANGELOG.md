# Changelog

What changes for a team using Trampo, newest first. The format follows Keep a Changelog. The reasons behind each
change are in `docs/decisions.md`. An entry marked (gap filler) or (new) is this product's own and not the practice it
was built from. Unless an entry says more, upgrading means setting `core_version` in `workspace.yaml` to the new version.

## [0.5.0] - 2026-11-27

### Changed

- The product is renamed Trampo, and its repository is now `trampo-framework/trampo`. The marketplace, the plugin names and the commands (`/trampo-core:setup` and so on), the environment variables (`TRAMPO_USER`, `TRAMPO_SID`), the per-machine folder (`~/.config/trampo/`) and the workspace folder (`.trampo/`) all carry the new name. Names from before the rename are not read.
- Known issues: a finding outside the work's scope that is urgent (a live exposure, data at risk, or what the team's approval rules call urgent) is told to a person straight away and its entry marked `escalated (<to whom, when>)`; it is still not fixed inside the work. Constitution rule 10, write protocol rule 5, the session skill and the seeds say so. Copy the known-issues seed header and `AGENTS.md` into the workspace when you upgrade. (restores the practice it was built from)
- Documentation: How it works gains "Found on the way"; Measured results and How it was built gain two relative figures for what card work recorded outside its scope.

## [0.4.9] - 2026-11-25

### Changed

- Setup suggests a workspace name only from the folder's own name, printed by the new `setup.py WORKSPACE name`, or suggests none. It never takes a name from the signed-in account, an email, a connector or the environment. (new, gap filler, owner decision 2026-11-25)
- Card mode: a person narrowing, widening or correcting a card's scope or direction is a counted interaction, so its close-out needs a lesson. Calling it "a product decision" is not by itself a reason for `no durable lesson`: the lesson is about how the session scoped the work. Copy the card mode's seeds and templates into the workspace when you upgrade. (counting restores the practice it was built from; the product-decision rule is new, gap filler, owner decision 2026-11-25)
- Card mode and the runbooks first load: a question the session settles on the person's behalf (from a README, by inference from another answer, or by choosing a design) is written down with `assumed, not asked` in the By column: in the record's Decisions table, and in `sessions/first-load/questions.md`, which gains Answer and By columns. (new, gap filler, owner decision 2026-11-25)
- Documentation: the lite setup page says it was run end to end on 2026-11-25; the video storyboard is ready to record.

## [0.4.8] - 2026-11-24

### Added

- Setup offers a lite path for one person: the core, the card mode and the runbooks part. It asks three questions (the name, the code repository folders, the approver) and sets the rest; the summary and the typed agreement are as before. (new, gap filler, owner decision 2026-11-24)
- Lite writes the named repository folders into the person's own `areas` file, so edits in their code go ahead while a change outside them still waits. Every other setting equals the full interview's recommended answers for one person: no gated commands are added. (gap filler)
- Lite is refused when the card mode or the runbooks part is not installed, and the message names the install command.

## [0.4.7] - 2026-11-20

### Changed

- A card session closes as done only when the last verdict line in `sessions/<card>/qa-report.md` is `Verdict: PASS`. A missing report, a report with no verdict line, `Verdict: FAIL` and `Verdict: CANNOT-VERIFY` are refused, and the message says what to do. A card whose QA cannot run now is parked. Parks and other kinds of session are not asked. (gap filler)
- Each QA pass ends with one line at the start of a line: `Verdict: PASS`, `Verdict: FAIL` or `Verdict: CANNOT-VERIFY`, with nothing after the word. Tell your QA helper to write it; the card mode, the new `qa-report.md` template and the worker brief say so. Copy the card mode's seeds and templates into the workspace when you upgrade.
- In an epic run, `run.py confirm` also lists an item whose last QA verdict is not PASS.
- When there is no local path to test, QA is recorded as `Verdict: SKIPPED: <reason>`. Such a card may close as done once an approver says yes to closing it that way, naming the card; the close command asks for that yes. FAIL and CANNOT-VERIFY are never closed by a yes. The yes is read from the conversation and recorded by the gate hook, the same trust as every other approval. (new, gap filler, owner decision 2026-11-20)
- What this check is: the close command reads one line of a file the assistant itself can write. It cannot tell whether QA ran, or whether the helper was independent. It catches a forgotten QA step, not a dishonest one.

### Added

- Documentation: a visual README, and pages with diagrams under `docs/wiki/` (how it works, the parts, adopting it, controllers and agents, the security model, several teams, slots and adapters). No change to the product.

## [0.4.6] - 2026-11-19

### Changed

- Approvers name a control folder by its path with the slash, or by the path of the file being changed: "Yes, change slots/" or "Yes, change agents/card.yaml". The words "slots", "agents" and "hooks" alone no longer open anything. This applies to `slots/`, `agents/`, `.claude/hooks/` and `.claude/agents/`. (gap filler)
- The settings file is approved as `.claude/settings.json`; "settings.json" alone no longer counts. (gap filler)
- An approval given before the upgrade for a control-folder change that was not pushed yet is asked for again.
- A card session writes the system facts it learned into the system or flow runbook before it closes, marks what nobody has seen replayed as unverified, and writes a `runbook:` line in its record: the paths changed, or `none learned`.
- Closing a card as done prints a warning when its record has no `runbook:` line, and still closes. The close is refused only when the line names a runbook that does not exist. A workspace without the runbooks part writes `runbook: left in <where>`. (gap filler)

### Fixed

- The card mode pointed at `qa/runbooks/`; the runbooks live in `runbooks/`.
- `scripts/deny-scan.sh` finds ticket-key and 12-digit shapes on macOS as it does on Linux. On macOS it found none, whatever the tree held, so a contributor's local "clean" said nothing about shapes. Run it again before your next pull request.

## [0.4.5] - 2026-11-19

### Added

- A plain yes in the gated action's own words opens the gate without the item's id, while only one gated action is waiting in the sitting. With two or more waiting, the yes names the item.
- An unattended worker can wait for a person: `agent.py wait NAME ITEM KEY`. A waiting item still counts in the agent's cap, and only an approver's reply ends the wait.
- An agent's pool, waits and last beat are shared in `sessions/agents/<name>.json`, so a monitor in another copy of the workspace sees the agents it watches. At most one commit per tick, and one an hour while idle.
- Assigning an item to an agent waits for an approver. The agents mode ships the gate; run setup again, or add it under `gated_commands:`, to turn it on in an existing workspace.
- An approver can record a yes for a control-file commit made outside a session: `prepush.py adopt <workspace> <commit>`, so later pushes from that copy are not refused. (gap filler)
- `--dry-run` on `agent.py monitor` and `agent.py release`: a trial tick that prints what it would tell and posts nothing. (gap filler)
- The health check warns while a backstop is recorded as "nothing yet" or "none". (gap filler)

### Changed

- A file under `.claude/skills/` in the workspace is a control file: writing one waits for an approver's yes naming it as `skills/<name>`. A skill's name is lower-case letters, digits and hyphens, three characters or more. (gap filler)
- One command changes one control file. A command that writes two is refused: run one command for each.
- A session can no longer edit an agent's state files by hand; they change through `agent.py`. (gap filler)

### Fixed

- The review's count of repeated causes joins causes that differ only in letter case or spacing, and sessions about the same dated subject.

### Security

- A gated call through the slot runner is checked as the runner reads it, so an option placed between its words no longer gets it past the gate. Inside a session the runner refuses a gated call that has no recorded yes. (gap filler)
- Control files are guarded whatever letter case their path is typed in.

## [0.4.4] - 2026-11-19

### Changed

- A question someone may come back to now leaves an ad-hoc record; only a question about using the assistant leaves nothing. A sitting with no record is reminded at each prompt. (gap filler)
- The state of a run names a worker only once its session has opened. Before that it says the start command was printed.

### Fixed

- The agent loop releases its lock after every tick. Before, every tick after the first found the lock held.
- A yes for one gated action is no longer refused because the same message holds back another ("Yes, post the notice. Hold the ticket for now").
- A gated command is still checked after the shell moves to a folder outside the workspace.
- A worker started from inside a session keeps its transcript: the printed start command drops the mark it inherited.

### Added

- `docs/agents.md` covers the one-time steps before a worker starts, an example launch program, standing grants, how an agent's copy keeps up, and the first push to an empty shared repository.

## [0.4.3] - 2026-11-19

### Added

- Setup builds a new workspace from its interview with one command, on the person's typed agreement to one summary. Nobody types a git command or edits a file by hand. (gap filler)
- Setup asks for the team's own rules and for the shared repository's address, and sets a missing git user name for the new workspace only.

### Changed

- Git's hooks are installed only inside the workspace repository, never in a machine-wide hooks folder. A machine where an earlier version installed them machine-wide runs the health check, which prints the commands that restore it.
- The machine's other hooks still run for the workspace, through stubs kept inside the repository.

## [0.4.2] - 2026-11-19

### Security

- A background worker start must name, once, the whole settings file that dispatch wrote; an edited file or a second settings flag is refused.
- A repository listed by its address binds a worktree only inside a working area the person declared. A person whose repositories are listed by address adds the folders that hold their copies to their `areas` file.

## [0.4.1] - 2026-11-19

### Security

- A run binds only a worktree of a repository the team listed. List your code repositories under `repositories:` in `workspace.yaml`.
- A command that only mentions the event script is read whole by the gates.
- A background worker start must use the settings file dispatch wrote for that item.

## [0.4.0] - 2026-11-19

### Added

- Epic runs: a controller starts one worker per item on the dependency graph, with run records and a readiness check before a worker starts.
- Unattended agents: a card agent that works the items assigned to it, a monitor that watches the agents, a release monitor that watches finished items, and card triage that drafts items for approval. Creating a tracker item waits for an approver.
- Review mode, with its evidence rules checked in code, and a support-week handover in the triage mode.
- The runbooks part: a first load, replay, and suggestions for new skills. It installs with only the core.
- A file-backed mock for the four slots and a checker any adapter can be run against. (new)
- A standing grant's holder may be an agent's name. The health check fails an agent that is also an approver. (gap filler)

## [0.3.2] - 2026-11-19

Add `retro:` to `workspace.yaml` as in the seed.

### Added

- The periodic review is back beside learning at each close, with a totals line the health check recounts from the ledger.

### Fixed

- A yes is judged by the sentence that carries it. One refusal word elsewhere in the message no longer makes the whole message a no.
- A yes does not need the file's name when one item is waiting.
- The stop check covers the ledger and files a shell command wrote, not only file-tool edits.
- A gate pattern no longer fires on reads, commit messages and closing notes.
- A push may set a variable on its own command line.

## [0.3.1] - 2026-11-18

### Security

- The push check reads the transcript behind a control-file approval, and refuses when it cannot. A person pushing someone else's approved change pushes after the approver's own session has shared its ledger.
- One approval record covers one commit.
- A session cannot write the runtime's transcripts, and the pushing process does not choose where they are read from.

## [0.3.0] - 2026-11-18

A rebuild around one real team's working practice. Upgrading from 0.2.8 is a set of steps done by a person in one sitting: see "Upgrading from 0.2.8" in `docs/decisions.md`.

### Changed

- Approval is the approver's own typed message, read by the gate hook. The approve command the assistant ran is gone.
- On git, a control file changes on an approver's yes naming the file, with an `Approved-by:` line checked at push. On a shared folder the journal with an approved proposal stays. (gap filler)
- Identity is the git user name; a declared name is used only without git.
- Sharing on git goes through `sync.py`, a start step and a stop check.
- The ledger has one id per session, grouped by subject, and a hook counts the prompts.
- Memory is four categories routed by read triggers. Size caps are warnings.
- Modes are ad-hoc session, card session and triage. Outside systems are reached through four slots the team fills: tracker, ask, code-host and monitoring.
- When a hook is unsure it lets the call through; only the push check refuses.

### Added

- Standing grants: a written grant with a scope and a holder opens a gate later. No grant can open approving, granting, or changing gates, approvers, agents, grants, slots or core rules.

### Removed

- Declared live company systems and their guard, the identity binding of 0.2.7, hash-bound approvals, and the task and support modes.
- Asking first outside the workspace is now an option, off by default.

## [0.2.8] - 2026-11-18

The first tagged version. Most of what it held was replaced in 0.3.0; its history is the first part of `docs/decisions.md`.
