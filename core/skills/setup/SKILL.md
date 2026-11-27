---
name: setup
description: Create a new Trampo workspace for a team. Interviews the team, then builds the folder from the seeds, with its settings, memory layout, modes and slots. Use when someone says "set up a workspace", "set up trampo", or opens an empty folder they want to turn into a team workspace.
---

# Setup: interview, then build from the seeds

Run in the folder that will become the workspace. Refuse if `workspace.yaml` already exists; offer `doctor` instead.
`EV` means `python3 -B "${CLAUDE_PLUGIN_ROOT}/scripts/event.py"`.

## 0. Lite or full

Ask first: **lite** (one person working alone, the card mode with runbooks) or **full** (a team, or any other choice
of modes: the interview in section 1). Recommend lite for one person who wants to start today, full for a team.

Lite needs the card mode and the runbooks part installed; the build refuses without them and names the install
command. Lite asks three questions, one at a time:

1. **Team or workspace name**, and one line on what the work is. You may suggest only what `SETUP . name`
   prints, the folder's own name, or no name at all: never from the account, email, connector, environment or anything
   else outside this folder. Suggest no line about the work; ask for it.
2. **The code repository** (or repositories) the person works in: the full path of each folder on this machine.
3. **The approver**: the person at the keyboard. Read their git user name yourself (`git config user.name`); when the
   machine has none, ask for their name and write it as `your_name:` too, as in the full interview.

Write the answers file with only `setup: lite`, `team`, `approvers` and `repositories` (and `your_name` when asked),
then go to section 2. Everything else is set by the build, and the summary shows it: storage git, branch main, the
card mode, a change outside the workspace waits for the approver, the repositories' folders go into the person's own
`areas` file so edits there go ahead, no gated commands (as in the full interview's recommended answers), the slots
stay stubs, no team rules, and the seed's review and size numbers. A control-file change still asks. Copying the card mode's and the runbooks part's seeds is done by the build. To change any default, run the
full interview instead. Once built, the runbooks part's first load (`/trampo-runbooks:first-load`) is the next step.

## 1. Interview

One question at a time, with a recommended answer for each. Write down the person's words.

1. **Team:** its name and one line on what it does. Run `SETUP . name` for the only name you may suggest.
   Then one question: does the team have code repositories it wants the assistant to know, and which? It has two
   halves, and say both plainly. The team lists each repository once under `repositories:` in `workspace.yaml`, by the
   address it is cloned from (or by a folder, when every machine keeps it in the same place); that list changes only
   on an approver's yes. Each person says where their own copies are kept. They write the folders, by hand, one full path
   per line, in the `areas` file beside their `user` file in the machine's config folder. A run binds a worker only to
   a worktree of a listed repository that sits inside one of that person's folders; the assistant never writes
   either half. If yes and the runbooks
   part is installed, say that its first load (`/trampo-runbooks:first-load`) is the first thing to run once this
   setup has built the workspace; if it is not installed, say that part exists. The skill lives in that part.
2. **Storage:** `git` (recommended: every person works in their own clone of one shared repository) or `files`, only
   for a team with no git, in a shared folder. Never both, and never git inside a synced folder.
3. **Who is at the keyboard.** On git it is each person's git user name. Read it yourself (`git config user.name`);
   do not ask the person to check it in a terminal. When the machine has none, ask the person for their name and
   write it in the answers as `your_name:`: the summary shows it as "You are <name>", and the build sets it for this
   workspace only. That happens at this first setup and nowhere else; you never set or change a name any other way.
   On files each person writes their name, by hand, on the first line of the `user` file in the machine's Trampo
   config folder. Never write it for them.
4. **Approvers:** the names of the people who may say yes to a gated action, spelled as in step 3. One owner lists one
   name.
5. **Modes:** which of the installed mode plugins to start with (ad-hoc session, card session, triage, review, epic run,
   unattended agents). The runbooks part is not a mode: its first load adds its own files.
6. **Gated actions:** which actions must wait for an approver. Offer examples: a message that leaves the team, a
   production change, a merge or a release, deleting data, creating a tracker item. For each, ask for the command that
   performs it today and write a pattern over that command's own words under `gated_commands:`, narrow enough that
   reading a file or writing a note does not match it: the name of the program, never an everyday word. When the
   action is saving a file outside the workspace, write the pattern over the folder's path and turn on
   `outside: ask-first`; the approval is then recorded under the gate's name. Never write a pattern that can never
   match: one over a slot that is not filled in, or over a command the team does not have yet. Record such a gate in
   `memory/shared/approval-gates.md` as waiting for its command, tell the person it is not enforced yet, and leave it
   out of `gated_commands:`. An entry with no pattern fails the health check.
   A chosen mode may ship gates of its own under `gates:` in its `module.md` (the agents mode ships
   `create a tracker item` and `assign an item to an agent`: an item is created, and handed to an agent, only on an
   approver's recorded approval). Write each one under
   `gated_commands:` without asking whether, as soon as the slot it names is filled, the mock included, and ask only
   for its backstop.
7. **A backstop for each gated action.** Say plainly: the hook is a check against a confused assistant and an
   ordinary rewording gets past it. For each gate ask what stops the action outside the hook (a credential the
   assistant's account does not hold, a rule on the other system's side, a required review). Write the answer under
   `backstops:`. "Nothing yet" is recorded as that; the health check keeps warning until one is named.
8. **Do the team's changes pass a review before they take effect?** (A second person reads every change before it is
   merged or deployed.) If yes, leave `outside:` off. **If no, turn on `outside: ask-first`**: a file change outside
   the workspace then waits for an approver. Ask which folders outside the workspace the team works in every day, and
   tell each person to list them, by hand, one full path per line, in the `areas` file beside their `user` file.
9. **The team branch on the code host** (git): ask whether direct pushes to it are refused and a review is required.
   That rule is the backstop for every control-file change; record the answer under `backstops:` as
   `control files`.
10. **Slots:** for each of `tracker`, `ask`, `code-host` and `monitoring`, whether the team will fill it now. Setup
    copies a stub for each; the team writes its own program later, on an approver's yes naming `slots/` (the folder with its slash, or the file's path). If the `ask`
    slot will carry approvals, say what its contract requires: it reports who answered from the tool's own account
    data, and it alone writes its records.
    For a trial or a simulated team, offer the mock: copy `${CLAUDE_PLUGIN_ROOT}/mocks/slot` to each of the four
    slot files and write the shared folder's path in `slots/mock-home`, so every clone reads one world
    (`protocols/slots.md`, "The mock adapter"). After filling any slot, run
    `python3 -B ${CLAUDE_PLUGIN_ROOT}/scripts/slot_contract.py .` and read out what it says.
11. **Standing grants:** none are written at setup. Say that an approver can add one later, with a scope and a
    holder, and that the health check asks for a review of any grant with no ceiling and no expiry after
    `grants.review_days` (90 unless they choose another number).
12. **The periodic review:** how often the team reviews its own work (`retro.every_days`, 7 unless they choose
    another number) and how many days of sessions a review reads (`retro.window_days`, 14). Say what it is: a person
    asks for it, it counts every session in the window and quotes the count, and the health check counts it again.
13. **Size prompts:** the word counts past which the health check suggests a split (600 for an index, 1,500 for a
    file unless they choose others). Warnings only.
14. **The team's own rules** (optional, one question): anything the team always or never does that the assistant
    should hold to, in their words. They go into `constitution.md` and into the summary the person agrees to. "None
    yet" is a fine answer.
15. **The shared repository** (git): its address, when the team has one. With none yet, the workspace is built on this
    machine and shared later.

## 2. Build

You do not write `workspace.yaml`, `constitution.md`, the slots or `memory/shared/approval-gates.md` yourself, and you
never ask a person to type a command: not to add an approver, not to start a repository, not to share. One command
builds the control files, on the person's typed agreement to a summary. `SETUP` is
`python3 -B ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py`.

1. Write the interview's answers to a file in the folder (`setup-answers.yaml`), in the form the head of `setup.py`
   lists: `team`, `storage`, `branch`, `remote`, `approvers`, `modes`, `repositories`, `gated_commands`, `backstops`,
   `outside`, `slots` (`mock` or `stub`), `mock_home`, `rules`.
2. For each chosen mode, copy its plugin's `seeds/` into the folder (`modes/<mode>.md`, and for triage the
   `incidents/` files). These are working instructions, not control files.
3. Run `SETUP . show setup-answers.yaml`. Read the whole summary to the person, word for word, and wait. Do not
   shorten it and do not answer for them. If they want a change, change the answers file and show it again.
4. When the person has typed that they agree to the setup, run `SETUP . build setup-answers.yaml`. It checks that
   they are one of the approvers the answers name, writes the control files, records their agreement in the ledger
   as the founding approval, and on git makes the first commit and the first share to the shared repository.
5. Read out what it says. If the first share did not go through it says, in plain words, what a person has to
   arrange (an address, an empty repository, access). When that is arranged, run `SETUP . share <address>`.
   On git, the next session start installs git's hooks inside the workspace repository's own `.git/hooks` folder and
   nowhere else: a hooks folder the machine shares between repositories is left as it is.
6. **storage: files:** write every seeded memory file that is not a control file through
   `EV journal --ws . --sid <sid> --path <file> --from <file>`, so the journal holds each seed.

This works once. When the team's copy holds a workspace the command refuses, and a control file changes only on an
approver's approval (`protocols/gates.md`). Each other person gets their own copy from the shared address.

## 3. Record it and check

The build opened the setup session (subject `setup`). It is a session like any other: a record at
`sessions/setup/session.md` holding the interview answers under Decisions, in the person's words, and
`EV close --ws . --outcome done --goal-met "<how the tree was checked against the answers>"`.

Then run `doctor`. It must report no failures. Read its warnings to the person: each gate with no backstop is one.
