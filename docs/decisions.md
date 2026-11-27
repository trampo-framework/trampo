# Trampo: a public foundation for self-improving team workspaces

## Goal
A public, Apache-2.0 foundation that lets a team create a workspace of plain markdown that holds long-lived memory, support and task records, and learns from each unit of work. The workspace evolves by proposal. It runs first on the Claude desktop app with a OneDrive or Dropbox folder, and second on the terminal with git. v1 demonstrates the loop with a fictional team, "Acme". The company-wide layout, project mode and migration of an existing workspace come after v1.

## Scope
**In v1:**
- One team workspace, supporting both `storage: files` and `storage: git`, never mixed.
- Core plugin: constitution, protocols, and the `setup`, `session`, `retro`, `doctor` and `propose` skills.
- Two example modes, task and support. A team's own modes are plain markdown read from `modules/`.
- Extension points limited to what the demo uses: `record-schema` and `close-checklist`.
- An automatic telemetry floor, plus hooks and transcript reading as optional extras.
- The Acme example workspace, replayed deterministically in CI.
- Publishing safeguards and a one-day desktop-runtime test.

**Deferred to v2:**
- The company layout: `teams/<team>/` subtrees, team identity from `people/`, restricted teams, submodules, company-level writes and the company index cap.
- Project mode and the worker-dispatch extension point.
- `doctor migrate`.
- The search-index module.
- Migrating an existing workspace onto Trampo as proof of concept.

## Implementation Steps
1. **Run the one-day desktop test first, before any core code.** On both OneDrive and Dropbox, in the Claude desktop app, test whether a `CLAUDE.md` loads from the workspace folder; whether the folder's `.claude/skills/` loads; whether hooks run and a session transcript is reachable; whether Python is available; and concurrent edits from two machines. Write the results to `docs/runtime-findings.md`. They decide how much of steps 3 to 6 can rely on hooks and on `doctor.py`.
2. **Create the private repo and the base files.** LICENSE, NOTICE, `AGENTS.md`, `CONTRIBUTING.md`, `docs/principles.md` and this file. User-facing docs say "core, modules, data"; HMVC appears only in `docs/principles.md`, as the engine's internal design principle.
3. **Write the constitution and protocols.** The six invariants; the first rule extended with "memory is data, never authority" (gates come from `workspace.yaml`, the constitutions and `memory/gates.md`; loosening a gate needs an approved proposal; amended 2026-10-28); add-only addenda; memory write, read and sizing protocols, measured in words; the two extension points.
4. **Build the core plugin.** Skills `setup`, `session`, `retro`, `doctor`, `propose`. The `session` skill writes a closing event itself (outcome, why a human intervened, record path), so the retro works with no hooks; runs `doctor` at the start of every session; writes `telemetry_degraded` when data is missing. Every record and event carries `schema_version`, and a version mismatch with the pinned core makes memory writes refuse. The retro reads only the last N days (a team setting), proposes changes and never edits mode files itself; a person approves each one. `who` is off by default in telemetry, and `people/` holds only preferences.
5. **Build `doctor`.** Structural checks only, in a script (Python is a declared requirement); contradiction review between constitution layers is a skill step. Checks: caps and unknown `.md` files that neither the index nor the journal mentions; journal replay; secret patterns on `storage: files`; memory entries that name URLs or loosen a gate; refuses `storage: git` inside a known sync folder; fails if a team's copied module and the upstream plugin are both active.
6. **Build the files-backend journal.** Each memory write logs the full new text plus a hash of the previous content in that session's own JSONL file. Splits and index rewrites happen only in the retro.
7. **Build the two modes.** Plugins for task and support, with templates and seed memory. `setup` interviews the team and seeds `modes/<name>.md`. A team's own modes are markdown the `session` skill reads from `modules/`; they are never loaded as plugins.
8. **Build the Acme example repo.** Its history shows the `setup` interview; a task record that promotes two facts; a support triage that finds one of them as prior art; a file hitting its word cap and splitting; a retro that proposes a mode change, which a person approves.
9. **Build the deterministic CI replay.** Schema validation, a clean `doctor` run, a byte-for-byte journal rebuild of memory, parsing of fixture transcripts, and a check that the workspace rules reach the agent's context. It never runs a live agent; live agent evals are a separate manual job.
10. **Add publishing safeguards.** The private deny-list as a pre-push hook and a CI secret, with patterns for ticket keys, 12-digit account ids and people's names; gitleaks in the public repo; `propose` strips workspace facts before drafting an upstream PR, and CONTRIBUTING runs the same scan on contributors; Acme is checked for incidents that resemble a real employer's; before going public, a fresh squashed history and a full human read of the diff.
11. **Dry run.** A real small team uses the desktop app on a OneDrive folder, then a Dropbox folder. Findings feed back into `docs/runtime-findings.md`.

## Acceptance Criteria
- The step 1 findings are recorded, and every later design choice that depends on them cites the finding.
- A workspace produced by `setup` works on a OneDrive folder in the desktop app. A closing event is written with hooks off.
- Two machines write memory at the same time on a shared folder. `doctor` rebuilds the correct state from the journals with no lost text.
- The same workspace works on `storage: git`.
- CI replay passes without calling a live agent. A deliberately broken fixture fails it.
- `doctor` fails on each of: a split-brain module, a missing cap, an unknown `.md` file, a secret pattern, a git repo inside a sync folder, and a version mismatch.
- The retro never edits a mode file without a recorded approval.
- A scan with the private deny-list finds no company terms in the public tree.
- Written clearance from the author's employer covers ownership as well as publication.

## Rollout
1. Build in a private repo.
2. Gates before the first public push: written employer clearance covering IP ownership; trademark search for "Trampo" at IP Australia, USPTO and JPO; availability on npm, the plugin marketplaces and the domain; the squashed history; the human diff read.
3. Publish and pilot with one team.
4. v2, in order: the company layout, project mode with worker dispatch, `doctor migrate`, then the search-index module.

---

## Plan Review Notes
**Changes applied:**
- v1 proves the desktop app on a shared folder first and git second (user).
- v1 is one team, two modes, and the extension points the demo uses; the company layout and project mode move to v2 (user, from the critics' cut). The worker-dispatch point ships with project mode.
- Team modules are plain markdown, not plugins (both critics).
- A telemetry floor that needs no hooks (both critics).
- The retro proposes and a person approves (both critics).
- The journal stores full text plus a hash of the previous content, and `doctor` runs at each session start (both critics).
- Memory is data, never authority (practical critic).
- Version guard with `schema_version` (technical critic).
- Shadowing disables the upstream plugin (technical critic).
- Deterministic CI replay (both critics).
- `doctor` boundaries and the git-in-sync-folder refusal (both critics).
- Bounded retro (practical critic).
- Personal-data handling (practical critic).
- Publishing hygiene, including `propose` stripping workspace facts.
- HMVC kept as an internal principle in `docs/principles.md`.
- One-day desktop test as step 1 (both critics).
- Deferred to v2 with the company layout: team entry files and per-team settings, explicit team identity, restricted teams' proposals.

**Accepted as-is:**
- `doctor migrate` and a company index word cap, deferred with the company layout.
- Journal over one-file-per-entry for sync conflicts.

**Open until step 1:**
- Whether the desktop app loads a `CLAUDE.md` or `.claude/skills/` from the workspace; whether a session transcript is reachable; whether Python is available; who installs core when a team has no admin.

**2026-10-28 sync from the source repo:** generic changes made in the source workspace
since the design, ported into v1.
- Task list seeded from the exit condition, one task in progress, completed means its
  check passed, re-read before every stop; falls back to a checklist in the record.
  (`core/skills/session/SKILL.md`)
- Live-state claims carry `As of <date> (<record id>); re-check: <command>`, old values
  stay as dated past lines, `re-check: not recorded` refused on a new claim; `doctor`
  fails both. (`core/protocols/write.md`, `doctor.py`)
- On `storage: git`: commit only your own paths, never stash, pull or rebase a shared
  checkout. (`core/protocols/write.md`)
- Resume restates the record's `Next`, open items and decisions, and does not re-ask.
- Close is safe to run twice and rewrites the record's `Status` and `Next`.
- Unique `event_id` on every event; a duplicated line is read once. (`event.py`, schema)
- Start events stamp `core_version` and `modes_sha`; the retro judges each approved
  proposal on before and after sessions, minimum `retro.min_sessions`, else
  `no verdict yet`. (`event.py`, `core/skills/retro/SKILL.md`)
- A split is verbatim only if the sorted lines match. (`core/protocols/sizing.md`)
- Support findings need a reachable trigger before they are reported. (support seed)

**2026-11-13 sync from the source repo:** second pass, same rule: only generic changes.
- The claim line carries the verdict, any "do not" and the scope; an index row is a
  headline plus a link; a changed fact is dated in every file that still states the old
  version. Measured in the source workspace as the writing patterns that most often made
  an agent answer wrongly after reading the right file. (`core/protocols/write.md`,
  `core/protocols/sizing.md`)
- Memory review: four mechanical checks (`stale-correction`, `conflicting-count`,
  `scope-undone`, `buried-do-not`). Ruling: it runs as a retro step, not as `doctor`
  warnings, so session starts stay quiet; the retro lists rewordings and a person
  approves them. Two source checks were not ported: entry size (the word caps cover it)
  and undated shipped claims (the live-state stamp covers it).
  (`core/scripts/memory_review.py`, `core/skills/retro/SKILL.md`)
- `event.py emit` refuses an end with no outcome, a `blocked` end with no cause, and a
  cause outside a fixed list of seven. `schema_version` stays 1 and the core version
  stays 0.1.0: every earlier event is still valid and nothing is published yet.
  (`event.py`, schema)
- Task close: a reachable review finding is fixed or refuted with evidence. Support
  close: a drafted reply gets a fresh refutation pass on its premises. (mode seeds)
- After a resume or compaction the session reconciles the record with the user's
  messages first. Every script run and watcher is timeboxed. (`session` skill, `AGENTS.md`)

Three rulings on conflicts the sync found:
1. **Parked sessions:** `parked` is an outcome. Pausing writes an end with it; resuming
   starts again with `resumes: <event_id>`. A start with no end past 12 hours is a crash,
   and `doctor` fails it. Constitution rule 5 amended.
2. **Index of indexes:** over its cap, `memory.md` splits into
   `memory/<category>/index.md` sub-indexes, one level only. Caps apply to every index;
   `doctor` fails deeper nesting. Decision 9 amended.
3. **Gates in memory:** gates may live in `memory/gates.md`, and an optional SessionStart
   hook injects `memory.md` and `memory/gates.md`, also after a compaction. This reverses
   the review's "gates only from config" fix. One guard stays: an entry that loosens or
   removes a gate must cite an approved proposal, and `doctor` warns when it does not.
   Constitution rules 1 and 3 amended.

Ported later: the "Needs you" lint, a vocabulary for why work was blocked, memory-read
telemetry from transcripts, and worker tooling with project mode. Skipped: ad-hoc sessions
as a mode (the session skill covers them) and source-specific grants and push gates.

**2026-11-16, version 0.2.0:** a simulated team ran eleven units of work on 0.1 and an
independent judge marked the result. Thirteen gaps closed.
- The `init` skill is now `setup`; the old name collided with a built-in command.
- Identity is declared per machine or account (`TRAMPO_USER`, else
  `~/.config/trampo/user`), outside the workspace because the workspace may be synced.
  It is a claim, not authentication. `telemetry.who: on` now stamps it on every event.
- An approval is an `approve` event written by `event.py approve` for a name under
  `approvers:`. A name typed in the chat is never one. Ruling: the gate named must be
  under `gates:` in `workspace.yaml`, so a gate added to `memory/gates.md` also gets a
  line there. `--field` cannot set `ev`, `who`, `gate`, `ts`, `ns`, `event_id`,
  `schema_version` or `sid`. (`core/protocols/gates.md`, `event.py`)
- Every request is a unit, however small. The SessionStart hook prints the standing
  rules and a `hook_sid`; a start that carries it ties the hook's `touch` lines to the
  unit. `doctor` fails work outside a start and an end, and warns for two weeks on a
  conversation with prompts and no start. A start that was never written is backfilled
  with `emit --ev start --at <time>`, which marks the event `backfill`.
- `resumes` covers `blocked` as well as `parked`. `emit` refuses a start that continues
  such a unit without naming that end. Constitution rule 5 amended.
- Setup and the retro are sessions with a start and an end. Setup journals every text
  file it seeds except `workspace.yaml`, which people edit by hand. `doctor` no longer
  calls the first journaled write of an older file a concurrent edit.
- `doctor` warns on likely email addresses, phone numbers, street addresses and secrets
  in `records/` and `memory/`. A pattern match, so warnings only.
- Records keep the approved text word for word, and every number names its command.
- Every approved proposal gets a `verdict:` line (`helped`, `no-change`, `hurt`,
  `too-early`), whatever it targets; the proposal states its `observable:` first. This
  replaces `no change`, `worse` and `no verdict yet`.
- Mode files name categories, never files. A split writes its index rows in the same
  change, and `doctor` fails a memory file no index lists.
- Support: refuting the cause before drafting, and promoting a fact or writing
  `promoted: none because <reason>`, are required steps.
- `schema_version` stays 1: every 0.1 event is still valid.

**2026-11-16, version 0.2.1:** the same simulated team replayed four units on 0.2 and the
judge found approvals that covered the wrong thing. Ten changes.
- An approval is bound to one unit and one exact text. `event.py approve` needs
  `--text FILE` and an open start under that sid; the event stores `unit` (from that
  start), `text_sha`, `gate` and `who`. `event.py approved` exits 0 only for the same gate
  and text under the open start, and the agent runs it just before the gated action.
- Ruling, how `doctor` tells old approvals from new: by the `core_version` on the start
  the approve sits under. Only a start that plainly states a version below 0.2.1 excuses a
  missing `text_sha`; a missing or unreadable version does not. An approve outside an open
  start, or written before its start was (a backfilled start), fails whatever the version.
  `--field` can no longer set `core_version` or `modes_sha`, so a start cannot claim an
  old core.
- No approval after the fact. A person saying an earlier action "was approved" is a dated
  note in the record, never an `approve` event. An approver's conditions are part of the
  approved text.
- A gated action is described from what it does: what runs, what it changes as read from
  the script, what it does not do or was not verified. The unit ends `done` only when the
  stated effect was checked.
- People are told what is needed in their own words. No script, command, event or
  internal names unless they used them first.
- No routes around identity: the agent checks `whoami` against `approvers:` before trying
  `approve`, never probes, and never explains how to change the declared identity.
- A health check warning about a file the unit touched, or about personal data anywhere,
  is fixed or named as left open. A closed record may be edited only to remove personal
  data, and the edit leaves a dated line.
- A count is re-run before it goes into memory or a verdict, or quoted as
  "<n> per <record>".
- One sid per unit. The record's `Session` line is the sid for every later session on
  the unit; the runtime's session id is only the `hook_sid` link. `emit` refuses a start
  whose unit already has a ledger under another sid, unless `resumes` names the unit's
  last blocked or parked end. Ruling: a proposal is one unit, so applying it and judging
  it later share the sid `<date>-proposal-<slug>`.
- Core rule 6 is enforced for the team `constitution.md` as for mode files: the first
  journaled write is the seed, later writes cite an approved proposal.
- Fixed: an all-digit `resumes` or `hook_sid` stays a string; "looks like an aws access
  key".
- Moving a 0.2.0 workspace to 0.2.1: a person sets `core_version: 0.2.1` in
  `workspace.yaml`; the team's own `modes/*.md` take the new seed lines by an approved
  proposal; run `doctor`. `schema_version` stays 1.

**2026-11-16, version 0.2.2:** owner decision after a simulated unit closed `done` on a
deploy that only copied a config file, while the customer's problem stayed. Three changes.
- A unit ends `done` only when the requester's goal is met. The goal in the record is the
  requester's, in their words. Narrower work ends `blocked` or `parked` with what would
  unblock it. Only the requester changes the goal, and the record keeps the original and
  who changed it. A `done` end carries `goal_met`, set with `--goal-met "<how it was
  checked>"` and never with `--field`; `emit` refuses a `done` end without it, and refuses
  the flag on any other event. Records gain a `Goal met` line.
- Ruling, how `doctor` tells old ends from new: as for approvals, by the `core_version`
  on the start the end closes. Only a start that plainly states a version below 0.2.2
  excuses a `done` end with no `goal_met`. The script stamps that version itself, so a
  new start cannot claim an old core.
- A `helped`, `no-change` or `hurt` verdict needs `retro.min_sessions` ended units behind
  it (5 when the line is missing or below 1). That key was already in the `workspace.yaml`
  seed, so no new key was added. `doctor` counts from the ledger: distinct units with an
  end after the first event that names the proposal (the start of its own unit, or a
  write that cites it), retros left out. It fails a verdict that comes too soon and says
  how many it counted. `too-early` always passes.
- Ruling: a proposal's approval is a line a person edits, so the ledger has no event for
  it. The count starts where the ledger first names the proposal. A proposal the ledger
  never names counts as zero.
- An approver's conditions sit inside the hashed text. The approved file is exactly what
  the approver was shown, in full, and ends with a `Conditions:` section (`Conditions:
  none` when there are none). `approve` refuses a file with no such line. A condition
  added after approval is a new text and a new approval.
- Moving a 0.2.1 workspace to 0.2.2: a person sets `core_version: 0.2.2` in
  `workspace.yaml`; the team's own `modes/*.md` take the new seed lines by an approved
  proposal; run `doctor`. A proposal that already holds a final verdict with too few
  units behind it fails until the line is changed to `too-early`. `schema_version` stays 1.

**2026-11-16, version 0.2.3:** the same simulated team ran six units and an independent
judge found that the rules about approvals and safety held and the learning step did not.
Seven changes, and two security fixes found in review of this pass.
- Every end names a root cause. `emit` refuses an end without `--root-cause "<a few plain
  words>"` (`none` for routine work), refuses it on any other event and through
  `--field`, and refuses "unknown", "other" and the like. `event.py causes --ws .` prints
  every unit that ever ended, once, with its date, outcome, root cause and record, in
  four lists: `repeats` (root causes that share words), `single`, `routine` and
  `no_root_cause`. The retro runs it over the whole ledger, not the review window, and
  reads the grouped records.
- Ruling: the key is `root_cause`, not `cause`. `cause` has been the fixed list of why a
  person stepped in since 0.1, and the retro counts it by exact value. The root cause is
  free text and is compared by its words.
- A retro file holds two required sections. `## Repeated causes` names each repeat with
  its record paths, its count and what would stop it, or says none was found and how many
  units were compared. `## Standing warnings` lists every health check warning, and for
  one that the previous retro also listed, the fix made or the person asked to decide.
  `doctor` fails a retro file without either, and fails the newest retro when a record
  that `causes` groups as a likely repeat is not named in the first section.
- Ruling, how `doctor` tells old ends and old retros from new: as before, by the
  `core_version` on the start the end closes. Only a start that plainly states a version
  below 0.2.3 excuses an end with no root cause or a retro file with no sections. The
  retro file is found from the unit name: `retro/<date>` leaves `retros/<date>.md`.
- When prior art shows the same cause as an earlier record, the record says
  `repeat of <record>, sighting <N>` when it is seen, and the end uses that record's
  words for the root cause.
- A hand edit is reconciled. `journal --diff` shows what differs between the journal and
  the file; the person is shown it in plain words and asked; `journal --adopt
  --accepted-by <name> [--edited-by <name>]` records the file as it is, with both names;
  `journal --restore` puts the journal's text back. `doctor` points there, and
  `doctor --rebuild` now only puts back files that are missing: it never overwrites a
  file that is there and differs. An adopted `constitution.md` or mode file still needs
  `--approval <an approved proposal>`.
- An approval can be superseded. `event.py supersede --ws . --sid SID --text FILE
  --reason "<plain words>"` writes a `supersede` event with the `text_sha`. From then on
  `approved` fails for that text in every unit and gives the reason, until the text is
  shown and approved again. Any unit may supersede, because the unit that finds the
  facts is often not the one that holds the approval. `emit` refuses to write one by
  hand.
- Ruling: `doctor` cannot fail a gated action taken after its approval was superseded.
  The ledger records approvals and never the sending or running, so there is nothing to
  compare. The stop is in `approved`, which the agent runs just before acting.
- A warning about personal data or a secret in any workspace file is fixed in the unit
  that sees it, not carried.
- Talking to people: the answer or the ask comes first; an approval request is the full
  text plus at most three lines; other replies stay under about 120 words; the approver
  is asked for a yes or no in their own words and never to run or name a command; the
  person is "you", never the third person.
- Owner decision, 2026-11-16: a requester may narrow the goal at close, the record keeps
  the original goal and who changed it, and the part cut off becomes its own blocked or
  parked unit. This amends the 0.2.2 rule that narrower work always ends `blocked` or
  `parked`: it still does unless the requester narrows the goal.
- A number copied from an older record or memory entry is re-derived from its source
  file before it is written again, or written as "<n> per <record>, not re-checked".
- Security: every workspace-relative path goes through one guard. `journal` (write,
  remove, diff, adopt, restore), the ledger file itself, `doctor --rebuild` and every
  path a ledger line names are refused when they leave the workspace or are, or pass
  through, a symbolic link. `doctor` walks the workspace without following links and
  fails every link it finds, file or folder; the SessionStart hook prints no file that
  is reached through one.
- New event fields: `root_cause`; `adopt`, `accepted_by`, `edited_by` on a write or
  remove; the event `supersede` with `reason` and `supersedes`. `schema_version` stays 1.
- Upgrading a 0.2.2 workspace. No key is added to `workspace.yaml`; one value changes.
  Two workspace files change: `modes/task.md` and `modes/support.md` take the new seed
  lines (root cause and repeats, sensitive data fixed at once, superseded approvals,
  talking to people, the narrowed goal, copied numbers). Old ends, old approvals and old
  retro files are excused by their version, so nothing in the ledger is rewritten.
  `CORE` is the installed core plugin folder and `MODS` the folder holding the mode
  plugins. An admin does this, in order:
  1. By hand, in `workspace.yaml`: `core_version: 0.2.3`.
  2. `python3 CORE/scripts/doctor.py .` It passes at this point unless the workspace
     holds a symbolic link (replace it with the real file or folder) or a file that
     differs from its journal (step 3).
  3. For each file reported as differing, inside a unit:
     `python3 CORE/scripts/event.py journal --ws . --sid SID --path <file> --diff`, show
     the person the difference, then the same command with
     `--adopt --accepted-by "<name>"` to keep it or `--restore` to drop it.
  4. A person writes `proposals/<date>-seed-0-2-3.md` with `status: approved` and
     `target: modes/task.md, modes/support.md`. Then, with
     `SID=<date>-proposal-seed-0-2-3`:
     `python3 CORE/scripts/event.py emit --ws . --sid $SID --ev start --mode retro --unit proposals/<date>-seed-0-2-3.md`
     `python3 CORE/scripts/event.py journal --ws . --sid $SID --path modes/task.md --from MODS/mode-task/seeds/modes/task.md --approval proposals/<date>-seed-0-2-3.md`
     `python3 CORE/scripts/event.py journal --ws . --sid $SID --path modes/support.md --from MODS/mode-support/seeds/modes/support.md --approval proposals/<date>-seed-0-2-3.md`
     `python3 CORE/scripts/event.py emit --ws . --sid $SID --ev end --mode retro --unit proposals/<date>-seed-0-2-3.md --outcome done --goal-met "both mode files match the 0.2.3 seeds" --root-cause none`
     A team that changed its mode files merges the new lines by hand into a copy and
     journals that copy in place of the seed. On `storage: git`, copy and commit instead.
  5. `python3 CORE/scripts/doctor.py .` must print `doctor: ok`.
  6. `python3 CORE/scripts/event.py causes --ws .` Every unit ended before the upgrade
     is under `no_root_cause`; the first retro on 0.2.3 reads those records by hand.
  From then on every end needs `--root-cause`, also the end of a unit that was started,
  blocked or parked under 0.2.2. This was rehearsed on a workspace built with the 0.2.2
  scripts: the health check passed after step 1 and after step 4.

**2026-11-16, version 0.2.4:** across four simulated rounds, whatever the scripts enforce
improved and stayed improved, and whatever was only asked for in words did not. This pass
moves five rules from words into the scripts. Three security fixes came from review of
this pass. After it the engine is frozen for a held-out test.
- Owner decision, 2026-11-16: a proposal is approved only through the approve command, on
  its full text. `event.py approve --ws . --sid SID --proposal proposals/<file>` runs in
  the approver's session, checks the declared identity against `approvers:`, needs an
  open start, and refuses a file with no `status:`, `target:`, `observable:` or
  `Conditions:` line. It writes an `approve` event with `gate: proposal`, the `proposal`
  path and the `text_sha`, and marks the file `status: approved` itself.
  `event.py approved --proposal` and `event.py supersede --proposal` work on the same
  hash. This replaces the 0.2.2 ruling that a proposal's approval is a line a person
  edits.
- Ruling, what the hash covers. The file is split on new lines only, with Windows line
  endings read as new lines. Two lines are outside the hash: the first line that is only
  `status: <one word>`, and the first line that is only `verdict: helped`, `no-change`,
  `hurt` or `too-early (look again <YYYY-MM-DD>)`. Empty lines at the very end do not
  count. Everything else is inside it, including a second status or verdict line and any
  words added to either. So the verdict line holds only the verdict, and its numbers go
  in the retro file or the record of the unit that judged it.
- `doctor` fails a proposal marked `status: approved` with no `approve` event, a proposal
  that was ever approved through the command and no longer holds an approved text,
  whatever its status line says, and one still marked approved after its approval was
  superseded. A changed proposal is a new text and needs a new approval.
- Ruling, how `doctor` tells old proposals from new: by the `core_version` on the start
  the ledger first names the proposal under (the start of its own unit, or a write that
  cites it). Only a start that plainly states a version below 0.2.4 excuses a proposal
  marked approved by hand. One the ledger never names is not excused.
- A journaled write that cites `--approval <proposal>` is refused unless that approval
  stands for the text the proposal holds now, and unless the path is listed under the
  proposal's `target:` line (paths inside the workspace, separated by commas). Inside
  the unit named for a proposal every journaled write answers to that proposal, cited or
  not. Ruling, the allowance: that unit may still journal under `records/`, `retros/`,
  `people/` and `proposals/` without an approval, because those hold its own record,
  the retro file, a person's stated preferences and proposals that need their own
  approval. Any other file needs another approved proposal that names it.
- Each such write carries `approval` and `approval_sha`, the hash of the proposal when
  the write was made. `doctor` fails a write whose proposal had no approval of that text
  standing at that moment. A mode file or constitution write from 0.2.4 on is checked
  this way and no longer by the proposal's status line, so withdrawing a proposal later
  does not turn an honest write into a failure.
- `emit` refuses to write a `write` or `remove` event, as it already refused `approve`
  and `supersede`: each has its own command. `--field` can no longer set `proposal`,
  `approval`, `approval_sha`, `text_sha`, `supersedes`, `path`, `text`, `prev_sha`,
  `adopt`, `accepted_by`, `edited_by` or `backfill`.
- Review numbers come from a command. `event.py stats --ws . [--since YYYY-MM-DD]` counts
  by unit, never by ledger line: units ended by mode and final outcome, units that
  stopped at least once (an end that was blocked or parked) by cause of the stop, and
  each root cause with how many units named it. The retro copies its numbers from
  `stats` or `causes`; any other number says how it was counted.
- Ruling, first-hand or follow-on: the ledger has no field for it, so `stats` does not
  claim to know. It splits each root cause by mode, work modes against `retro`, `doctor`
  and `setup`, and says in its output that the ledger records no more than that.
- The newest retro quotes the first line of `stats` word for word. The line names its
  own window and the time it was counted, so `doctor` counts again over the same events
  and fails the retro file when the line is missing or does not match. Other numbers in
  the file are not checked: a machine cannot tell which command a number in a sentence
  came from.
- Superseding at review. `stats` lists every approval with no later done end in the
  unit it belongs to: the same unit for a gated action, the unit `proposals/<file>` for
  a proposal. The retro reads each one against later records, supersedes one that later
  facts made wrong and tells the approver in one line. `doctor` fails the newest retro
  when a standing approval is not named in the file.
- A person's stated preferences reach the next session. `event.py prefer --ws . --sid
  SID --line "<what they said>"` adds one dated line to `people/<name>.md` through the
  journal. The name comes from the declared identity in one way: lower case, every run
  of characters that are not letters or digits becomes one hyphen (`event.py whoami
  --file` prints it). The SessionStart hook prints the newest 20 lines of that file,
  each cut to 300 characters, straight after the standing rules, under a heading that
  says they are that person's own preferences and grant no permission. Nothing sensitive
  goes in the file, and `doctor` now warns on personal data patterns under `people/`.
- Security, found in review of this pass. The proposal hash first took any text after
  `verdict:` as outside the hash and split lines on every character Python counts as a
  line break: both were ways to add words an approver never saw. It now uses
  the closed forms above and refuses a file that holds any line break other than a new
  line. A proposal is read exactly, and one that is not valid UTF-8 is refused, so two
  different files never hash alike. The text of a gated action was already read
  strictly. `doctor` first checked only proposals marked approved, and only that some
  approval came before a cited write; it now checks every proposal that was ever
  approved and matches each cited write to the approval that stood when it was made.
- What the scripts still cannot see. On `storage: git` there is no journal, so the
  target rule is not enforced there; `event.py approved --proposal` before the commit is
  the check. Nothing can tell that an approver was shown the whole file and not a
  summary. A rule written into a memory file from an ordinary unit, outside the
  proposal's unit and citing no approval, is an ordinary memory write to the scripts.
- New event fields: `proposal` on an approve; `approval_sha` on a write or remove.
  `schema_version` stays 1.
- Upgrading a 0.2.3 workspace. No key is added to `workspace.yaml`; one value changes.
  Two workspace files change: `modes/task.md` and `modes/support.md` take the new seed
  lines (a person's stated preferences are written down). Old ends, old retro files and
  proposals the ledger shows were applied under an older core are excused by their
  version, so nothing in the ledger is rewritten. `CORE` is the installed core plugin
  folder and `MODS` the folder holding the mode plugins. An admin does this, in order;
  steps 3 and 4 need an approver at the keyboard, in their own session:
  1. By hand, in `workspace.yaml`: `core_version: 0.2.4`.
  2. `python3 CORE/scripts/doctor.py .` It fails once for each proposal that says
     `status: approved` and that the ledger never names: a proposal approved by hand and
     not yet applied. Proposals already applied under the older core pass and are left
     as they are. They are not under the hash, and no new write can cite them.
  3. For each proposal step 2 names, and for any older approved proposal the team wants
     under the hash: by hand, set its first line back to `status: proposed`, and add the
     lines it lacks (`target:`, `observable:`, `Conditions: none`). Move any numbers on
     a verdict line into the retro file, so the line reads only `verdict: <word>`. Show
     the approver the whole file. On their yes, with `SID=<date>-proposal-<slug>` (the
     sid that proposal's unit already has, when it has one):
     `python3 CORE/scripts/event.py emit --ws . --sid $SID --ev start --mode retro --unit proposals/<file>`
     `python3 CORE/scripts/event.py approve --ws . --sid $SID --proposal proposals/<file>`
     `python3 CORE/scripts/event.py emit --ws . --sid $SID --ev end --mode retro --unit proposals/<file> --outcome parked --root-cause none`
     A proposal the team no longer wants is set to `status: proposed` or removed instead.
  4. Write `proposals/<date>-seed-0-2-4.md`:
     ```
     status: proposed
     target: modes/task.md, modes/support.md
     evidence: core 0.2.4 changed the seed mode files
     change: replace both mode files with the 0.2.4 seeds, keeping the team's own lines
     observable: doctor prints "doctor: ok" after the change; today it does
     Conditions: none
     ```
     Show the approver the whole file. On their yes, with
     `SID=<date>-proposal-seed-0-2-4` and `P=proposals/<date>-seed-0-2-4.md`:
     `python3 CORE/scripts/event.py emit --ws . --sid $SID --ev start --mode retro --unit $P`
     `python3 CORE/scripts/event.py approve --ws . --sid $SID --proposal $P`
     `python3 CORE/scripts/event.py journal --ws . --sid $SID --path modes/task.md --from MODS/mode-task/seeds/modes/task.md --approval $P`
     `python3 CORE/scripts/event.py journal --ws . --sid $SID --path modes/support.md --from MODS/mode-support/seeds/modes/support.md --approval $P`
     `python3 CORE/scripts/event.py emit --ws . --sid $SID --ev end --mode retro --unit $P --outcome done --goal-met "both mode files match the 0.2.4 seeds" --root-cause none`
     A team that changed its mode files merges the new lines by hand into a copy and
     journals that copy in place of the seed. On `storage: git`, run
     `python3 CORE/scripts/event.py approved --ws . --sid $SID --proposal $P`, then copy
     and commit.
  5. `python3 CORE/scripts/doctor.py .` must print `doctor: ok`.
  6. `python3 CORE/scripts/event.py stats --ws .` prints the totals line the next retro
     quotes, and under its last heading every approval that still waits to be acted on.
  From then on every retro started under 0.2.4 quotes the totals line and names every
  standing approval; a retro started under 0.2.3 is excused. This was rehearsed on a workspace
  built with the 0.2.3 scripts, holding one proposal applied under 0.2.3 and one marked
  approved by hand and never applied: the health check failed once after step 1, for
  the second proposal, and passed after step 4.

**2026-11-16, version 0.2.5:** five simulated people worked in five clones of one
`storage: git` workspace, and the workspace gave them nothing to share it with. The old
rule said only what not to do in "a checkout another session may be using". So work
stayed in the clone that made it: an approver was told nothing was waiting while the
draft sat unpushed on a colleague's machine, a review counted one clone and reported it
as the team, and the same cause was fixed three times by three people who could not see
each other's records. The same run showed approval conditions reaching a customer inside
the approved file, and a repeat that no word matching would catch.

- **Sync is a command, and the scripts run it.** `event.py sync` commits, fetches,
  merges and pushes. It runs by itself at session start, at every start and end event,
  around `approve` and `supersede`, and before `approved`, `stats` and `causes`. The
  model is one clone per person and one origin. The old rule (never stash, pull or
  rebase) stays true and is now complete: sync merges, because a merge rewrites no local
  commit and git refuses it, before changing anything, when it would touch a file with
  uncommitted changes. A rebase would rewrite commits a ledger already describes.
- **Nothing blocks local work.** No remote, no network, a refused push and a conflict
  are reports. What changes is what the assistant may say: every syncing command prints
  either `in step with origin` or what is missing, and after `ORIGIN WAS NOT SEEN` the
  rule is "I could not look at the shared copy", never "there is none". A fetch or push
  that takes over 15 seconds counts as origin out of reach.
- **Conflicts.** Ledgers are append-only, so both sides' lines are kept. Two additions
  at the same place in another file are both kept, this copy's first: two people adding
  memory entries is the common case and neither is wrong. Two different changes to the
  same existing lines are never merged by a script: the merge is undone, both versions
  are printed, and a person chooses with `--resolve mine` or `--resolve theirs`. Known
  cost: two people adding the same heading get it twice, which the memory review finds.
- **A sync commits only what this copy declared.** The ledgers, the unit's record, files
  named with `--wrote` on the end or `--path` on a sync, journaled paths, and a proposal
  this session approved. Never a folder and never "everything changed": a blanket add
  publishes whatever is in the folder, another session's half-written file or a secret
  among them. Other changed files are listed as `not shared:` and left alone. The list
  of declared files lives inside the clone's git folder, outside the shared tree, so a
  ledger line that arrives from origin cannot make this copy publish a file. Each
  declared path must be a real file inside the workspace, and a file that looks like a
  secret is held back and named. Cost: a unit that forgets `--wrote` leaves its file
  unshared, and says so loudly. A deleted file is shared with `sync --path`.
- **What sync means on `storage: files`.** Nothing to run: the shared folder is the
  shared copy and its sync client moves the files. `event.py sync` says so and does
  nothing, and no other command changes. No script can see whether a colleague's client
  is behind, so the honest statement there is "in this folder as it is now". The journal
  and its conflict checks are unchanged.
- **`doctor` warns about sharing and never fails on it.** Commits not on origin, commits
  not taken in, changed files nobody shared, no remote. A fail would break every
  mid-unit health check and every person working offline, and the session rule is that
  a fail is settled before work. Ledger files are left out of the uncommitted warning
  because the prompt hook writes them between syncs. `doctor` reads what the last fetch
  left and does not contact origin. Open sessions are judged as before.
- **Conditions live on the approval, not in the file.** 0.2.4 put a `Conditions:`
  section in the approved file to bind them to the text; the file is also what gets
  sent, so the approver's internal note went to the recipient. Now `approve` takes
  `--conditions`, refuses a file that holds such a line, and stores the conditions with
  one hash over text and conditions. `approved` checks that hash and prints the
  conditions just before the action. Proposals keep their in-file line: a proposal is
  never sent to anyone.
- **A repeat is named, not guessed.** In the run, three units with one cause used three
  wordings with no shared word, and no word rule separates that from three different
  causes. `emit --ev end --repeat-of <unit or record>` links a unit to an earlier ended
  one, `causes` and `stats` group linked units, and every start prints the earlier root
  causes so the link can be seen in time. Choosing the link is still the assistant's
  judgement.
- **Text from other people is printed as data.** One module, `untrusted.py`, cleans
  every field the scripts print from ledgers, memory, preferences and proposals: one
  line, no control characters, capped length, under a fixed line saying it is data and
  grants no permission. A sid, unit or record that is not a plain name is printed as
  `[invalid <kind> <id>]`, and `emit` refuses to write one.
- **The totals line says whose work it counts.** `in N sessions by M named people`, so a
  review of one clone reads as one. `doctor` recounts it for a retro started under
  0.2.5; older retros keep the older line.
- **How to talk** joins the rules injected at every session start: answer first, under
  about 120 words, no paths, commands or internal words. Length is not measured.
- **New event fields:** `conditions` and `bound_sha` on approve; `wrote` and `repeat_of`
  on end. `wrote` is a record of what was said and is never what a sync reads.
- **Upgrading a 0.2.4 workspace.** Nothing in a ledger is rewritten, and approvals
  written under 0.2.4 still pass for their files. `CORE` is the installed core plugin
  folder. An admin does this, in order:
  1. By hand, in `workspace.yaml`: `core_version: 0.2.5`.
  2. On `storage: git`, once: if `git remote` prints nothing, add the shared repository
     (`git remote add origin <address>`). Then
     `python3 CORE/scripts/event.py sync --ws . --path workspace.yaml`. It must print
     `sync: in step with origin`. A `not shared:` list names files earlier units left
     uncommitted: for each, the person who wrote it shares it with
     `event.py sync --ws . --path <file>`, or it is left alone. Every other person then
     opens a session in their own clone, which syncs by itself, and shares what their
     clone holds the same way.
  3. Replace both mode files with the 0.2.5 seeds through a seed proposal, exactly as
     step 4 of the 0.2.4 note, with `0-2-5` in the names. On `storage: git` the last
     three commands are `event.py approved --ws . --sid $SID --proposal $P`, the copy,
     and the end event with `--wrote modes/task.md --wrote modes/support.md`.
  4. A draft that waits for approval and ends with a `Conditions:` section: take the
     section out of the file and pass it as `--conditions` when the approver says yes.
     A text approved under 0.2.4 and not yet sent still passes `approved` with its
     section inside; take the section out before sending, show the approver the clean
     file and approve it again.
  5. `python3 CORE/scripts/doctor.py .` must print `doctor: ok`. A unit or record whose
     name holds a space or another character outside letters, digits, `.`, `_`, `#`, `/`
     and `-` now shows as `[invalid ...]` with a warning, and cannot be started again
     under that name: continue it as a new unit under a plain name, with a line in the
     new record naming the old one.
  Steps 1, 2 and 5 were rehearsed on a clone of a git workspace written under 0.2.4: the
  health check failed on the version before step 1, warned about `workspace.yaml` after
  it, and printed `doctor: ok` with no warning after step 2. Steps 3 and 4 were not
  rehearsed.

**2026-11-16, version 0.2.6:** the same simulated team replayed its fourteen units on
0.2.5. Sharing worked whenever two clones did not touch one file. The one time they
did, a record left uncommitted by a session that never ended made git refuse the merge,
the report said only that a merge had failed, and that person's work stayed local for
four units, during which a second approver signed something the first had refused. A
start was lost to a closed pipe, an end was written with no start, a gate line was typed
in on a spoken yes, and an approver was shown a rewording called "the exact text".

- **A sync is not stopped by this copy's own files without saying how to go on.**
  Before merging, the sync lists the files origin changed that are also changed here.
  One this copy declared in any of its sessions is committed and merged; a unit's
  record is now declared when the unit starts, at `records/<unit>.md` and
  `records/<mode>/<unit>.md`, so a session that never ends no longer leaves it
  unnamed. Any other file stops the merge before it begins, and the report names it
  with the one command that settles it. That keeps the 0.2.5 rule that only declared
  files are committed: taking in an unnamed file would publish it. Nothing is discarded
  and the copy is never left half merged. Rejected: setting the file aside and merging
  under it, which is a stash by another name and can silently undo a colleague's lines.
- **A stopped sync is remembered** in a file inside the copy's git folder until a sync
  goes through. `doctor` fails on it, in that copy only, and the session start syncs
  again and says it again. This is the one sharing state that fails: it has a named
  way out, and four units of silent divergence cost more than a failed check.
- **Why a sync stopped is one of a fixed list of sentences.** What git printed is shown
  under it as marked data, with every `remote:` line removed, because a server or a
  hook on it writes those words; none of it is kept in the remembered state. That file
  is read back as data: an unknown reason, a name that fails the path guard and any
  other field are dropped.
- **A name in a suggested command is one quoted shell word, or there is no command.**
  File names can arrive in a colleague's commit. A name with a quote, a shell
  character, a line break, a leading `-` or `..` is printed as `[unsafe name <id>]`
  and the line says a person must look. This holds for every command the scripts
  print with a path, unit, sid or id in it.
- **The ledger.** A start writes its event before it prints anything, and every
  command survives a reader that closed the pipe (`| head -1`). An end is refused when
  its sid has no open start, with the command that writes a lost start first; a second
  end of the same start is refused as already ended. A backfilled start is checked
  against the ends before its own time, so it is no longer asked to resume an end that
  comes after it. A start is refused when the same unit is in the ledger with or
  without one leading folder (`task/x` and `x`), with the spelling to use.
- **The gates, the approvers, the constitution and the mode files on `storage: git`.**
  Nothing journals a write there, so the sync and `doctor` compare these files with
  the state the copy last shared with origin. A change is shared only when an approval
  that still stands, given after that state and not declined since, carries exactly
  it: for `gates:` and `approvers:` one line per change in the proposal (`gate-add:`
  and the like), for any other file a `result:` line with the hash of the new text,
  which `event.py result` prints. Naming the file under `target:` is not enough, or
  one approval would cover every later edit. Creating, deleting or renaming such a
  file is a change; a link or an unreadable file is refused, not skipped. A commit of
  such a change made by hand keeps the copy from pushing. The other lines of
  `workspace.yaml` stay free. Chosen over recording a hash at first share and marking
  the approval spent: that would let anything through before the first share.
  `event.py propose-gate` writes the proposal for one new gate and prints it for the
  approver, so the honest path costs one command and one yes. Gates rule 8 now says
  what is checked: these change as an approved proposal says, whoever types them.
- **What stays unenforced there.** Before a workspace is first shared nothing is
  compared (setup). A copy with no origin is checked for uncommitted changes only, and
  `doctor` says so. A change pushed with plain git from outside any session is seen by
  no script in the pushing copy; the other copies take it in as origin's state. Two
  proposals pending on one file at once are not combined: apply and share one, then
  the other. An approval is refused if a colleague's commit touched the same file
  after it was given: show and approve again. On `storage: files`, `workspace.yaml` is
  not journaled, so a change to its gates or approvers is not checked; each start now
  stamps a hash of them and `doctor` warns when the file no longer matches the last
  stamp. `memory/gates.md` is not under this check.
- **An approval follows `event.py show`.** It prints the bytes and the conditions the
  approval binds, fenced and with the hash, and writes a `show` event; `approve`
  refuses a text, conditions or proposal that was not shown under the open start. What
  no script can check is the paste: the assistant can still retype. The output says
  so, and the protocol says only what `show` printed may be called the exact text.
- **Small additions.** `event.py decline` records a no, and `show` prints it to the
  next approver of that unit, text or proposal. The session start prints the running
  core next to the workspace's `core_version` and says in capitals when they differ.
  `doctor` warns when origin was last looked at two or more days ago. Not built: a
  `--repeat-of` suggestion at start, because the cause is not known until the end.
- **New events and fields:** `show` and `decline` events; `gates_sha` on a start.
- **Upgrading a 0.2.5 workspace.** Nothing in a ledger is rewritten. First refresh the
  installed plugin (README, "Upgrading"). Then an admin, in order:
  1. By hand, in `workspace.yaml`: `core_version: 0.2.6`. On `storage: git`, share it:
     `python3 CORE/scripts/event.py sync --ws . --path workspace.yaml`.
  2. `python3 CORE/scripts/doctor.py .` An end with no start left by 0.2.5 fails as
     before; write the start with the command the line prints, adding `--unit <the
     unit>` and, when it then asks, the `--field resumes=<id>` it names.
  3. On `storage: git`, a file `doctor` now names as changed with no approved proposal
     is settled by a proposal that carries the change, or by a person putting the file
     back. Units already in the ledger under two spellings stay as they are; new
     starts must use the spelling the refusal prints.
  4. The seed mode files changed by one sentence (the approval request is what
     `event.py show` prints). Taking it in is the seed proposal of the 0.2.4 note; on
     `storage: git` make the change in the copy first, add to the proposal the two
     lines `event.py result --ws . --path modes/<mode>.md` prints, then show, approve
     and end with `--wrote` for both files.
  5. Drafts waiting for approval need nothing: they are shown with `event.py show`
     when the approver sits down. Approvals given under 0.2.5 still pass `approved`.
  Steps 1 and 2 were rehearsed on a clone of a git workspace written under 0.2.5 that
  held one end with no start: the health check failed twice before step 1, once after
  it, and printed `doctor: ok` after the backfill. Steps 3 and 4 were not rehearsed.

**2026-11-17, version 0.2.7:** a simulated team replayed two units that changed a company
reference table. In one, the assistant edited the table on a requester's word while the owner
was away, and the record said the requester had made the change. In the other, an approver
opened a session and was never told what had waited for days. A plain push to the shared
repository also changed the approvers without an approval, and nothing said so.

- **Ask first before changing a company system.** A seventh core rule: before the assistant
  changes any file outside the workspace that a person or a system relies on, an approver
  or the system's named owner says yes to the exact change, in their own sitting. A
  requester who is neither does not count. A workspace names such files under `live:` as
  `<name> | <owner>`; paths never go in `workspace.yaml`, only in each machine's
  `~/.config/trampo/live`, written by a person. Setup offers the gate "changing a live
  setting or reference data in a company system"; a decline is written with `decline-gate`
  (who, when, their words), is shown by `stats` and again at every retro, and `doctor`
  warns until the gate is listed or declined. When the gate is listed, the owner alone no
  longer counts: like every gate it is for approvers.
- **Enforcement is detection by hash.** The scripts hash each declared live file at every
  start, emit, sync and end. A difference is a `change` line the script writes, naming the
  assistant as actor (`actor: assistant`, or `unknown` when no unit was open), the requester
  apart, and who agreed. It matches a standing approval only when the file now holds exactly
  the result the approved text bound with its `live-result:` line (`event.py result --live
  --from <draft>` prints it); one approval covers one change. Any other change is marked
  `unapproved`: the unit cannot end `done`, every session start prints it first, and `doctor`
  fails until an approver or the owner, from another session and after the change, records
  `event.py decide --event <id> --accept` or `--reverted` (believed only when the hash
  matches). One helper, `valid_authority`, decides whether a decision or an approval read
  from the shared ledger counts; anything else is ignored and `doctor` names who wrote it.
- **What is prevented and what is not.** The Edit and Write tools are stopped by a
  pre-tool hook, with the path resolved through links and `..`, on a live path without a
  standing approval, and on the two files a person declares by hand and this machine's state
  tree. The Bash pre-check is a courtesy, not a boundary: it stops a command whose raw text
  holds a live path, one of those files, the identity variable name, or `approve` or
  `decide` joined to anything else. An assistant that runs a shell can change a live file;
  what the product guarantees is that such a change cannot go unrecorded, unattributed or
  unreviewed in a workspace whose live entries are declared. A team needing real prevention
  uses file permissions or a sandbox outside the product. An earlier design parsed shell
  commands; it was removed because every parse had a bypass and each one made the guard
  look stronger than it was.
- **Identity, restated once.** A person and their assistant share one machine account, so
  the product cannot prove a human typed an approval. What it enforces: the name a sitting
  starts with is recorded on its start line and fixed for the sitting. Every command
  resolves to that name whatever the variable or the file say afterwards; a command run
  under another name, and a name appearing where nobody was bound, approves, decides,
  declines, withdraws and prefers nothing and is written as `identity-changed`, which fails
  the health check until an approver decides on it. A second start on an open sitting cannot
  take another name. This machine's own record of the start is a second check and a
  disagreement refuses. A start written before 0.2.7 carries no mark. Which lines are
  old is decided by one upgrade marker, never by a version a line claims for itself and
  never by an event id: `event.py upgrade`, run once by a person, writes the baseline with,
  for each ledger file as it stands then, how many lines it held and a hash of them. A line
  is old only by where it sits: inside that count, in a file whose first lines still hash
  to the recorded value. An end never writes the marker, and the upgrade step is refused
  once a baseline exists. An event id used by two different lines fails the health check,
  and sync and the receive hook refuse the new line.
  For an old start the identity binding is skipped and nothing else: the author must still be
  an approver or the owner under the config in force, the session must differ, and the time
  and verdict rules apply. A workspace where the upgrade step was never run has
  no old lines at all. A second marker, or one outside the baseline ledger, is refused by
  sync and the receive hook. A session started with nobody declared,
  in a workspace with live systems, is told that approvals and decisions are unavailable.
- **The assistant is named as the actor.** `stats`, `causes`, the retro and the record
  template print "the assistant changed <name> at the request of <who>, agreed by <who>";
  `doctor` fails when a change line names no actor or when the record of that unit does not
  say it. One prose rule in the session skill says to say "I changed it".
- **An approver's first reply lists what waits.** The session start prints, for an approver,
  every item awaiting approval oldest first with its age, through the sanitiser; `doctor`
  warns past `approvals.warn_days` (7). Prose-only: opening the reply with the list.
- **Plain pushes and hand edits to what only a proposal may change.** The first end of a
  workspace writes one `baseline` line to `telemetry/events/baseline.jsonl`, read only from
  that file (a baseline line anywhere else is ignored, reported and never shared). One
  reader, `read_baseline`, serves the health check, the commands, the sync and the server
  hook: it parses every line as JSON, wants exactly one baseline, on the first line, chosen
  by position and never by a time it states, and reports an unreadable or extra line; the
  first stands meanwhile so the guard stays on. A gate, approver or live line, or a
  constitution or mode file, that differs from it counts for nothing in force unless an
  approved proposal carries exactly that change (`gate-add:`, `approver-add:`, `live-add:`
  and their `-remove:` forms, or a `result:` line). Approvals are read in order against the
  approvers in force before each, so a change cannot appoint the approver who approves it.
  Every sync, start and session start says it in capitals with the commit and author, `sync`
  exits 1, and `doctor` fails on both storage kinds. `receive.py` is an optional
  pre-receive hook with the same rule: it also refuses a tree with no `workspace.yaml`,
  deleting a branch, rewriting history and a rewritten baseline. A tag or another kind of
  ref is let through.
- **A ledger only gains lines.** A sync refuses to commit a ledger whose earlier lines
  changed or vanished (`ledger-cut`), and names the one way out.
- **New events and fields:** `seen`, `change`, `decision`, `identity-changed`,
  `gate-declined` and `baseline` events; `identity_sha` on a start; `live`, `actor`,
  `requester`, `agreed_by`, `before`, `after`, `unapproved`, `reverts`, `decides`, `verdict`,
  `was` on the lines that carry them. New commands: `result --live`, `decide`,
  `decline-gate`, `guard`; `approve --live --requested-by`.
- **Reversible.** The owner may say yes alone unless the live gate is listed. The baseline
  is written at the first end, so a gate typed in before it counts as approved. A decision
  needs another session than the change's.
- **Not covered.** A ledger edited after the marker was written drops the changed file out of
  the old set, so its approvals need a bound sitting. Approvals of proposals that change nothing guarded still verify as in
  0.2.6, and a proposal's declines and withdrawals are not authority-checked. A ledger line
  forged directly into a file a person can write is not caught until its sync. The hash
  covers one regular file per live entry for approval, and a folder only for detection.
- **Upgrading a 0.2.6 workspace.** Nothing in a ledger is rewritten. Refresh the installed
  plugin (README, "Upgrading"). Then an admin, in order:
  1. By hand, in `workspace.yaml`: `core_version: 0.2.7`. On `storage: git`, share it:
     `python3 CORE/scripts/event.py sync --ws . --path workspace.yaml`.
  2. `python3 CORE/scripts/doctor.py .` It warns once that the live settings gate was never
     settled: offer it to an approver (setup, question 4) or record the decline.
  3. To use live systems: add `live:` lines by a proposal (`live-add:`), and IT writes
     `~/.config/trampo/live` on each machine. A workspace with none behaves as before.
  4. A person, in their own terminal, before anyone starts a sitting on 0.2.7:
     `python3 CORE/scripts/event.py upgrade --ws .` It writes the baseline from the files
     as they stand and the marker over every ledger as it stands; settle any pending
     change first. The assistant is stopped from running it. If it is skipped, the first
     end writes a baseline with no marker and it can no longer be run: approvals from
     before the upgrade then no longer count, and `doctor` warns for each.
  5. The seed mode record templates gained a "Changes to company systems" section; take it in
     by the 0.2.4 seed proposal. Old records without it still pass.
  Steps 1 and 2 were rehearsed on a copy of the end-state clone of a simulated team: `doctor` failed once on
  the version before step 1 and printed `doctor: ok` after it, with two warnings (the
  uncommitted `workspace.yaml` and the unsettled live gate). On a fresh copy the upgrade step recorded 35 ledgers and
  136 old lines; `doctor` printed `doctor: ok` (no failures), and all 4 old gate approvals
  still verified. A start forged afterwards claiming 0.2.4, with an approval by a person who
  is not an approver, was refused by `approved` and made `doctor` fail, naming the approval;
  so was one by an approver's name that reused the id of an old approval, which `doctor`
  also named as an id used twice. A second upgrade step was refused. Steps 3 and 5 were not
  rehearsed.

**2026-11-17, version 0.2.8:** a simulated team replayed two units on 0.2.7. Nobody had
listed a live system, the assistant never asked, and it changed a company reference table
outside the workspace with the Edit tool on a requester's word. No script refused and no
ledger line recorded it; later replies said "someone fixed the table". Owner decision:
protection is the default, not something a person opts into.

- **Ask-first by default outside the workspace.** The pre-tool hook refuses Edit, Write,
  MultiEdit and NotebookEdit on every path that resolves outside the workspace root. Paths
  are resolved through links and `..` and compared part by part, never as text, so a
  sibling such as `code-old` is not inside `code`. Three things let a write through: a
  working area, the system temp folders, and an approval that stands for exactly that
  result. A declared live system is judged first and keeps its 0.2.7 treatment, also
  inside a working area.
- **Working areas are declared per machine, by hand.** `~/.config/trampo/areas`, one
  absolute path per line, `#` for a comment, at most 200 lines. It sits beside `user` and
  `live` for the same reason: a path belongs to one machine, and `workspace.yaml` is
  shared, so what it says must never choose what happens on a disk. The root, the home
  folder and a folder above it are refused and `doctor` warns for each. The assistant
  cannot add one: the whole config folder and the state folder are closed to the edit
  tools, and a shell command that names them is stopped. That shell stop is a courtesy,
  as for the other two files.
- **The temp rule.** A write is let through under the resolved system temp folder of the
  session (`TMPDIR`, as Python's `tempfile.gettempdir()` reads it) and under `/tmp`.
  Nothing else counts as temp. Scratch files live there and nothing a company relies on
  should.
- **Approval of one outside file reuses the live machinery.** `result`, `show` and `approve`
  take `--outside <absolute path>` in place of `--live <name>`: the text carries
  `outside-result: <path> = <hash of the whole file as it will be>`, the approval is
  bound to text and conditions by hash, was shown in the same sitting, is checked by
  `valid_authority`, and is spent by one change. Only an approver decides, because the
  file has no named owner. The hook lets through the Write tool alone, and only when the
  content it is about to write hashes to the approved result; it then writes the `change`
  line with `actor: assistant`, the requester, `agreed_by` and `approve_id`. The Edit
  tool is refused even with an approval, because only a whole-file write can be compared
  with the approved bytes before it happens. A request with no approver at hand ends the
  unit `blocked` on `approval-gate`, which the approver's session start already lists.
- **The refusal names the way forward.** One line of why, then who can approve, the three
  commands in their exact shape, and that a person may declare the folder instead. The
  path and the approvers' names are printed through the sanitiser and marked as data.
- **The session start says the rule.** One line: everything outside this workspace is
  ask-first, and either that no working area is declared on this machine or which ones
  are. The word budget of the session start rules moved from 150 to 180 for it.
- **The hook follows the session, not the folder it stands in.** When the session's
  current folder is no longer inside the workspace, the hook finds the workspace from the
  folder the session was opened in (`CLAUDE_PROJECT_DIR`). Before, stepping out of the
  workspace switched the live check off.
- **The shell check stays a courtesy and no parser comes back.** For a declared live
  system the hash comparison still finds a shell change. For any other file outside the
  workspace nothing does: there is no declared path to hash. This is said in the README
  and in `protocols/gates.md`. Not built: hashing each outside path the hook refused and
  comparing it again at the end of the unit would catch the common case of an assistant
  that is refused and then reaches for the shell. It is a proposal, not a decision.
- **A start that cannot keep its state writes nothing.** `emit --ev start` checks that the
  state folder takes a file before it writes the start line, and refuses in one plain
  line otherwise. Before, the line was written and the command then died, which left two
  starts and no end in one ledger. An end no longer fails on a state file it cannot remove.
- **Where the machine's files are, and why it is safe to move them.** The hand-written
  files are in `$XDG_CONFIG_HOME/trampo` and the state in `$XDG_STATE_HOME/trampo` when
  those variables are absolute paths, else in `~/.config/trampo` and
  `~/.local/state/trampo`. A relative value is ignored, as the standard says. A start
  records a hash of both resolved places (`home_sha`, never the paths), and every later
  command under that sitting that sees another place is refused before it does anything.
  This also closes what 0.2.7 left open: `HOME=<elsewhere>` in front of one command swapped
  the declared name and emptied the live list for that command. The hook reads its place
  from the session's own environment, which a command cannot change, and the shell check
  stops a command that holds `HOME=`, `XDG_CONFIG_HOME` or `XDG_STATE_HOME`. What remains
  is what identity already was: a sitting begun under another place is bound to whatever
  that place declares, exactly as one begun with another `TRAMPO_USER`. Declared, not
  proven.
- **Tests never touch the real home.** Four of the eight suites (`test_guarded`, `test_queue`,
  `test_sync`, `test_untrusted`) declared a name without moving the home folder, so every start in them wrote a file under the real
  `~/.local/state/trampo/bound/` and read the real `~/.config/trampo/`. `testenv.py`,
  imported first by every suite, points both folders at a temp folder for the whole test
  process and its children. One test fails when a suite does not import it.
- **New fields and flags:** `outside` on a show, an approve and a change; `home_sha` on a
  start; `--outside` on `result`, `show` and `approve`. The internal `standing_live(ws,
  name)` is `standing(ws, key, name)`.
- **Not covered.** A shell command that changes an undeclared file outside the workspace.
  A `change` line for an approved outside write is written as the write is let through, a
  moment before it happens: a write the tool then fails leaves the line. An outside
  notebook cannot be approved. An approval binds one regular file; a new folder of files
  is a working area or one approval per file. A person who puts a company folder inside a
  working area has switched ask-first off for it unless it is also under `live:`.
- **Upgrading a 0.2.7 workspace.** Nothing in a ledger is rewritten and the upgrade step of
  0.2.7 is not run again. Refresh the installed plugin (README, "Upgrading"). Then:
  1. By hand, in `workspace.yaml`: `core_version: 0.2.8`. On `storage: git`, share it:
     `python3 CORE/scripts/event.py sync --ws . --path workspace.yaml`.
  2. On each machine, a person writes the folders the team works in every day into
     `~/.config/trampo/areas`, one absolute path per line. A development team lists its
     code repositories. Until then every Edit or Write outside the workspace is refused
     and asks for an approver. The assistant is stopped from writing this file.
  3. Company files stay under `live:` as before. Listing one is still what makes a shell
     change to it visible.
  4. A sitting that was open across the upgrade carries no `home_sha` and is not held to
     its place; end it and start the unit again.
  5. A sandbox or a test harness that closes the home folder sets `XDG_CONFIG_HOME` and
     `XDG_STATE_HOME` to absolute folders it may write, for the whole session and before
     the first start, and puts `trampo/user` (and `live`, `areas`) under the first.
  None of these steps was rehearsed on a copy of a team's workspace.

## The grill decisions, as amended

| # | Area | Decision |
| --- | --- | --- |
| 1 | Name, licence, owner | Trampo, Apache-2.0, the author's personal account, private until written employer clearance |
| 2 | Delivery | Claude Code plugins; an `setup` skill interviews the team and creates its workspace |
| 3 | Runtime | Plain-markdown protocols any agent can follow; Claude Code is the reference runtime; hooks are extras |
| 4 | Layers | Core, then modules, then workspace data; HMVC as the engine's internal principle |
| 5 | Harness | One generic loop in core; worker dispatch arrives with project mode in v2 |
| 6 | Modes | Modes are team-owned data; v1 ships task and support; project in v2 |
| 7 | Overrides | Named extension points; core changes by proposal; local shadowing flagged by `doctor` |
| 8 | Modules | One layout; upstream modules are plugins; team modules are plain markdown in `modules/` |
| 9 | Memory | One pool behind an index, with one level of per-category sub-indexes once it outgrows its cap; the agent decides what to read; word caps force splits |
| 10 | Storage | Markdown files; `storage: git` or `storage: files`, never both; the journal replaces git history on files |
| 11 | Company layout | One company workspace with `teams/<team>/` subtrees; v2 |
| 12 | Writes | Teams write company facts directly; company rules change by proposal; v2 |
| 13 | Constitution | Seven fixed rules (the seventh added in 0.2.7); teams set the numbers and add rules; core, then company, then team; gates may live in `memory/gates.md`, loosened only by proposal |
| 14 | Learning | Facts at close of each unit; process changes from a periodic retro, by proposal |
| 15 | Telemetry | Rich schema captured automatically, over a floor the agent writes itself; unused fields are removed |
| 16 | v1 scope | Engine, `setup`, two modes, the Acme example replayed in CI |
| 17 | Leak protection | Private deny-list in a pre-push hook and a CI secret; gitleaks in the public repo |
| 18 | Migration | An existing workspace moves onto Trampo one mode at a time, after v1 |

## Release 0.3 (2026-11-18)

Everything above this heading is the history of versions 0.1 to 0.2.8 and describes features this release removed.
It is kept as a record and is not a description of the product.

### What changed and why

The owner reframed the product: it is one real team's working system (below, "the reference") made reusable, not a
new framework. The reference's practice wins by default. A rule of Trampo's own stays only as a named gap filler or
by the owner's direct decision. Where both had a rule and differed, the reference's way was ported and goes to trial.

| Area | 0.2.8 | 0.3.0 | Why |
| --- | --- | --- | --- |
| Approval | a command the assistant ran, bound to a hash of the text | the approver's own typed message, read by the gate hook from the transcript; or their bare yes through the ask-a-person slot | the reference's way; a yes the assistant records is a yes it can give itself |
| Conditions on a yes | stored and hashed | not recorded: a yes with a condition is a new question | the reference's way; removes a field and a class of mistakes |
| Standing grants | none | a written grant with a scope and a holder opens a gate later | owner decision 1 |
| Never list | prose | approving, granting and changing gates, approvers, agents, grants, slots or core rules can be opened by no grant | owner decision 3 |
| Control files | proposals and a journal | on git: an approver's yes naming the file, an `Approved-by:` line, checked by git's pre-push hook. On a shared folder: the journal with an approved proposal | the reference's way on git; the journal stays as the gap filler for teams with no git |
| Identity | a binding added in 0.2.7 | the git user name; a declared name only without git | owner decision 7 |
| Live company systems | declared and guarded | removed | owner decision 9 |
| Outside the workspace | ask-first by default | an option, off by default; setup turns it on when changes pass no review | owner decision 9 |
| Sharing on git | a sync command that wrote the commits | the reference's sync through a throwaway worktree, a start step and a stop check | owner decision 7, on trial |
| Ledger | one id per unit; counts typed by the assistant; a free-text root cause | one id per session, grouped by subject; touches counted by a hook with where each prompt came from; a typed fingerprint | hand-typed counts were wrong in every simulation; word matching never found a repeat |
| Pausing | an end, and a `resumes` chain | parking writes no end; the session stays open | the reference's way |
| Memory | one pool, word caps that failed the health check | four categories routed by read triggers; caps are warnings | the reference's way |
| Answers | under 120 words | the owner's answer shape, with the "Needs you" check on stop | the 120-word rule failed in every round |
| Modes | task, support | ad-hoc session, card session, triage | ported from the reference's skills |
| Outside systems | named in mode text | four slots the team fills: tracker, ask, code-host, monitoring | the frame: the product names no product |
| Retro | a periodic pass writing proposals, verdict floor of 5 | learning at each close; an edit judged later with a floor of 20 and a `confounded` verdict; `too-early` kept. From 0.3.2 the periodic review is back beside it, with a totals line a fresh clone recounts | the reference's way; the periodic retro missed the repeated cause three times, and without it nothing counted every unit |
| Hooks when unsure | the gate refused | every hook lets the call through; only pre-push refuses | failing closed stopped whole sittings in simulation |

Kept from Trampo by the owner's decision or as gap fillers: the approver list; shared-folder storage with its
journal; the declared name for teams with no git; the `done` rule (a `done` end states how the goal was checked);
the health check as a tool.

### Upgrading from 0.2.8

None of these steps was rehearsed on a copy of a real team's workspace. Do them in one sitting, by a person, on a
branch or a copy.

1. Update the plugins (`claude plugin marketplace update`, then `claude plugin update`). Uninstall the task and
   support mode plugins; install the ad-hoc, card and triage modes. Start a new session.
2. `workspace.yaml`: set `core_version: 0.3.2`. Remove `live:`, `telemetry:` and `modules:`; keep `retro:` with its
   `every_days` and `window_days` (the periodic review is back in 0.3.2). Replace the
   `gates:` list with `gated_commands:` (a name and a pattern over the command's words for each) and add
   `backstops:`, `hooks:`, `grants:` and `modes:` as in `core/seeds/workspace.yaml`. Keep `approvers:` and `caps:`.
   Add `outside: ask-first` only if the team's changes pass no review.
3. Who is at the keyboard: on git, check each person's git user name matches the approver list. The identity binding
   of 0.2.7 and the `live` file on each machine are no longer read; delete them. On a shared folder the `user` file
   stays.
4. Memory: create `memory/shared`, `memory/dev`, `memory/support` and `memory/review`, each with its index from the
   seeds, and move each existing memory file under the category where it will be looked for, unchanged. Replace
   `memory.md` with the seed's index of indexes. Move `memory/gates.md` to `memory/shared/approval-gates.md` and give
   each entry a **How to apply:** paragraph. Copy `verification-method.md`, `known-issues.md` and `grants.md` from
   the seeds.
5. Records: `records/` stays as history. New work is recorded in `sessions/<subject>/session.md` and `incidents/`.
   Copy each mode's `seeds/` into the workspace; the old `modes/task.md` and `modes/support.md` can be kept as
   history.
6. Replace `AGENTS.md` with the seed's, and copy `people/README.md`, the `slots/` stubs and the seed `.gitignore`
   lines (`.trampo/state/` must be ignored).
7. The ledger: old files in `telemetry/events/` stay and are read where their fields match. Old approvals open
   nothing. The commands `approve`, `approved`, `show`, `prefer` and `sync` of `event.py` are gone: a yes is typed by
   an approver, sharing is `sync.py`, preferences are a file a session reads.
8. On git, the first push after the upgrade changes control files, so its commits need an `Approved-by:` line from
   an approver's typed yes for each file, or a person pushes it once outside a session.
9. Run `doctor`. It must report no failures; read the warnings, each gate with no backstop among them.

### Why the hooks are Python

The reference's hooks are written in JavaScript. The product's are Python: one script, `core/scripts/hooks.py`, one
command per hook. The engine was already Python, the hooks share its readers (the transcript, the ledger, the
settings as the team agreed them), and a team installs one runtime instead of two. The behaviour was ported, not the
code, and each ported check has its tests.

### Every hook is a check against a confused assistant

A review of the reference's hooks found that every hook that reads shell commands lets an ordinary rewording through.
The owner's decision: keep the hooks as the reference has them, and say what they are. A hook is a check against a
confused assistant. It is not a wall, it lets a call through when it cannot tell, and a refused command is never
reworded. Each gated action names a backstop outside the hook, and setup asks each team for it.

| Gated action | The check the product ships | Known ways past it | The backstop outside the hook |
| --- | --- | --- | --- |
| A team's gated command | gate hook, a pattern over every word of each part of the command, less what is only recorded or printed | a variable, a wrapper script, a function, a name built at run time, a tool the wiring does not list | a credential the assistant does not hold; the other system's own approval |
| A typed yes | gate hook reads the session transcript | the transcript is an ordinary file on the machine | the same credential or approval; the yes is a record, not the control |
| A yes through the ask slot | gate hook reads the slot's records | the records are ordinary files; a write form the guard does not list | the slot reads who answered from the tool, and keeps its records where sessions cannot write |
| A control-file change | gate hook, then git's pre-push hook, which reads commits and not commands | a machine where no session installed the hook; a person skipping it | a branch rule on the code host: required review, no direct push |
| A change outside the workspace (when on) | gate hook, file tools only; recorded under a team gate whose pattern matches the path | a shell command writing the file | file permissions; review before a change takes effect |
| Sharing every turn | stop hook: files written with a file tool, the session's own ledger, changed files a shell command of the sitting wrote onto | a file written by a script the command ran, or from a folder other than the workspace root | a periodic report of unshared files, outside any session |
| A "Needs you" item with no consequence | stop hook, a shape check | any wording outside its patterns | a person reading the answer |
| Hook, settings and slot files | control paths, as above | an edit to the installed plugin's own files | the plugin installed read-only, or by an administrator |

### What is new relative to the reference

These are not the reference's practice. Each is here by an owner decision, as a gap filler, or is marked for the
owner to rule on.

- **Control settings are read from the team's shared copy.** Approvers, gated commands, grants and hook modes come
  from origin's branch, so a local edit adding oneself counts for nothing. Added by the previous developer.
- **A session end needs an outcome, and `done` needs how the goal was checked.** Stricter than the reference's prose.
  Kept by owner decision 10.
- **The approver list, and the rule that a typed yes counts only from an approver.** Gap filler, owner decision 7.
  The reference has one owner at the keyboard.
- **Standing grants as a parsed file with a never list.** Owner decisions 1 and 3; the mechanism is new.
- **Slots and `slot.py`.** The reference calls its tools directly. The indirection is the frame's requirement that
  the product names no product; the runner and its exit statuses are new.
- **The bridge reports who answered, and only an approver's reply counts.** Gap filler, owner decision 8.
- **Shared-folder storage with its journal, and the declared name.** Gap fillers for teams with no git.
- **The health check.** A tool, kept as optional. Three of its checks are new and for the owner to rule on: the
  warning for a gated action with no backstop (it makes the owner's backstop decision checkable); the pattern
  warnings for text that looks like personal data or a secret (Trampo's own, kept as a warning where the reference
  has a sentence and file-type refusals); and the failure for an incident folder with no index row (the reference
  checks its index when a change is pushed, the product in the health check).
- **`Approved text` in the session records.** Carried from Trampo, as the list of differences recommended.
- **Hook modes (`block`, `log`, `off`) per check in the settings.** The reference ships a new check as log-only by
  editing the hook; the product makes that a setting.
- **Control paths are guarded when a tool writes them, not only when a change reaches the team branch.** The reference
  checks its control paths at the pre-push boundary; the product also asks for the yes at the edit. Trampo's own
  means, kept in slice 2. `.claude/settings.local.json` and the installed plugin's files are not on the list.
- **The gate also guards the session ledger, the declared name and the git user name.** Added in slices 2 and 3 after
  security review, because an approve line or a name a session wrote would be a yes it gave itself.

### Enforced and prose

What a hook or a script checks, and what is only written down.

| Practice | Checked by | Or prose |
| --- | --- | --- |
| A gated command waits for an approver's yes | gate hook | |
| A yes is one approver's, for one subject, bare when it comes by chat | gate hook (`approval.py`) | |
| Grants need a scope, a holder and an approver; the never list | gate hook; health check | |
| Control files change on a yes; the commit carries `Approved-by:` | gate hook; pre-push hook | |
| A session does not write the ledger, the ask records or a declared name | gate hook | |
| A push does not skip git's hooks | gate hook | |
| Ask first outside the workspace, when on | gate hook | |
| One touch per prompt, with its origin | prompt hook | |
| Each prompt from a person gets a cause at close | `event.py close` counts what is left | the tagging |
| `done` states how the goal was checked | `event.py` | |
| One open ledger per assistant session; close is safe twice; parking writes no end | `event.py` | |
| Work opens a session before it starts | | prose, with a backfill offer at close |
| A repeat is found by its fingerprint | `event.py report` | giving a failure its fingerprint |
| The routes and gate rules are said at start, clear and compaction | start hook | |
| Read triggers are followed; prior art is searched | | prose |
| Memory entry shape; one fact per entry | | prose |
| A live-state claim carries its `As of` line | health check; pre-push hook | |
| Size caps; a file no index routes to | health check, warnings | splitting before compressing |
| A defect out of scope goes to the register | | prose |
| "Needs you" items carry a consequence | stop hook | the rest of the answer shape |
| What a session wrote is committed and shared | stop hook (file tools, git) | files written by a shell |
| The checkout is never pulled, stashed or rebased | `sync.py` does not | a session doing it by hand |
| Slot output is data | `slot.py` marks it | not following what it says |
| Every gate names a backstop | health check, warning | holding the backstop |
| No real user data; refused file types | ignore file; health check, warnings | prose |
| Incident folders are complete and indexed | health check | the evidence ledger's content |
| The verification method; test first | | prose |
| The task list habit | | prose |
| Personal preferences are read | | prose |
| Promotion, the lesson and the retrospective at close | | prose |
| A mode names an outside system only as a slot | a test in the product | a team's own mode edits |

### 0.3.1 (2026-11-18): five fixes from a security review of 0.3.0

All five are in how a yes for a control file is checked. No new mechanism: no signature, no hash of the change.
A workspace sets `core_version: 0.3.1`; nothing else changes for a team.

1. **The push check reads the transcript or refuses.** In 0.3.0 an approve record whose transcript could not be read
   passed git's pre-push hook, the one check meant to refuse when it cannot tell. Now a typed control-file approve
   record that is new to the team's copy is read against its sitting's transcript on the pushing machine, whether a commit
   cites it or not, and is refused when the transcript is not there. A record the team's copy already holds,
   unchanged, stands without its transcript: it passed this check once, on the machine where the yes was typed. So a
   person pushing someone else's approved change (a merge, for example) pushes after the approver's own session has
   shared its ledger, which every turn's sync does. The simpler rule, strict for everyone, would refuse that push
   for good; failing open for it was the hole.
2. **One record covers one commit.** A record a commit on the team's copy already cites, or an earlier commit of the
   same push, is spent: the approver is asked again. The text of the change is still not bound to the yes (binding
   by hash was removed in 0.3.0 by the owner's decision), so a yes for `workspace.yaml` covers whatever that one
   commit does to it. The backstop is the same branch rule on the code host: required review, no direct push.
3. **The transcript is found by the sitting's id, never by a stored path.** In 0.3.0 the approve line stored the
   path of its transcript and the check read whatever file that named. The line no longer stores a path. The check
   looks for `<sitting id>.jsonl` in the runtime's own folder for this workspace (under `projects/` in its config
   folder, named after the workspace's path), refuses a link, and counts only a typed line that carries the same
   sitting id. A transcript in another workspace's folder is not read.
4. **The pushing process does not choose where transcripts are read.** The runtime's transcript folder is written
   into git's hook when it is installed, the way the interpreter path is. The session start step takes it from the
   transcript path the runtime hands the hook, not from a variable; a person installing by hand has it read from
   their own environment. The check reads only there and ignores `CLAUDE_CONFIG_DIR` at push time. A hook installed
   before 0.3.1 names no folder and refuses a typed record it must read until a session start installs it again.
   The installer itself refuses to read the folder from the environment when the runtime's session variables are
   set, so a command a session runs cannot name it. The gate hook refuses a command that sets a variable for its
   own push (from 0.3.2 only `CLAUDE_CONFIG_DIR`), a session's write onto an installed hook (any repository's, named by its hooks folder, and this repository's wherever a setting put it, case ignored),
   and a session running the installer with `HOME` or `CLAUDE_CONFIG_DIR` set on the command, read after quotes are
   removed.
5. **A session does not write the runtime's transcripts.** The gate hook refuses a file tool or a shell write onto a
   `.jsonl` file under the runtime's `projects/` folder, whatever the case of the name, and a relative path that
   resolves there from the command's working folder. The lookup takes only a file whose name on disk is exactly
   `<sitting id>.jsonl`. Other files there are not refused: the runtime keeps files of its own beside the
   transcripts, and sessions write those.

What these do not change, and the owner's frame for it: each is a weak check against a confused assistant. The
transcript folder and git's hook file are ordinary files on the machine. The guard on them reads commands, so an
ordinary rewording gets past it, and an assistant that is trying can write a transcript or reinstall the hook:
a folder copied or moved into place, a path built after a `cd` or by a variable, a write from another language, a
variable set by a call the guard does not read, a command that clears the runtime's session variables before it
runs the installer. Further findings of this class are known limits, not defects to fix one by one. A
workspace on a path long enough for the runtime to shorten its folder name is not found, and a yes typed in a session
opened below the workspace root is filed under another folder: both are refused at the boundary, not passed. What
stands behind all of it is the branch rule on the code host: required review, no direct push. Records pushed under
0.3.0 are already on the team's copy and stand as they are; a team that doubts one reads `event.py approvals`
against its history.

An option, not built: a genuine-file check. When the gate hook writes an approve record it would also store the name
of the project folder the runtime's transcript path named at that moment, and the lookup would read only that folder
under the installed transcript folder. About 25 lines and three tests, no new mechanism. It would lift the two
refusals above (a long workspace path, a session opened below the root). The stored name would sit in the session
ledger, guarded by the same command-reading hook, so it is no stronger than the rest.

### 0.3.2 (2026-11-19): six fixes from the first trial run

The trial ran two teams through 16 units on 0.3.0. Fifteen lines of the marking sheet went from pass to partial;
these are the defects behind them, fixed before 0.4. A workspace sets `core_version: 0.3.2` and adds `retro:` as in
the seed.

1. **The periodic review is back.** Learning at each close stays. `event.py stats --since <day>` prints one totals
   line (sessions ended by outcome, how many stopped at least once, how many are still open, by how many people)
   that names its own window and the time it counted to. The review (`retros/<date>.md`, the retro skill, section
   4) quotes that line and has two sections, repeated causes and standing warnings. The health check recounts the
   newest review's line from the ledger and fails when it differs, so a fresh clone gets the same totals or says
   so. `retro.every_days` and `retro.window_days` are settings again, and setup asks for them.
2. **The typed-answer reader judges the sentence, not the message.** In 0.3.0 one refusal word anywhere made the
   whole message a no; nine clear approvals in the trial were refused that way. The rule now: a message is a yes
   for an item when a sentence that agrees, with no refusal or condition word in it, names the item or is followed
   on the same line by the sentence that names it. It is a no when the sentence naming the item, or the next
   sentence on its line, refuses or sets a condition, or when the message holds a refusal of fewer than four other
   words; a later message with a verdict decides over an earlier one. Kept refused, each a test: a conditional
   agreement, "not yet", agreement to another item, a non-approver, a later refusal. Known cost: "Yes, send it. I do
   not need a copy." is refused, because the sentence after the agreement holds a refusal word and the reader does
   not know what it is about. A wrong refusal costs one more ask; a wrong pass runs the action.
3. **An approval does not need the file's name when one item waits.** The gate hook keeps, per sitting, the file
   changes it refused outside the workspace. While exactly one waits, an approver's agreement typed after the
   refusal may name it by its file name or by a word of that name the refusal printed (a code whole, a word of five
   letters or more by its start); the same reader then applies. With two or more waiting, only the file name
   counts, and the refusal lists them. A file change whose path matches a `gated_commands` pattern is recorded
   under that gate's name, so a team's own gate holds its sends. The list of waiting items is an ordinary state
   file; it widens only which names count for an approver's own typed agreement. This applies to the outside
   gate only: a control file is still approved by its name, and the push check reads it the same way.
4. **The stop check covers the ledger and files a shell command wrote.** It held only file-tool edits, and four
   ledgers never reached the team's copy, one holding the only approval for a client reply. It now also holds the
   ledger of each session the sitting filed under, once that ledger has a line the team's copy lacks other than a
   prompt count, and any changed file that a shell command of the sitting wrote onto (a redirect, a copy, an
   in-place edit, an interpreter that names it and writes). Each is named with how it was written. A fault found on
   the way: a tracked file changed but not staged was missed when it came first in git's status.
5. **A gate pattern is tested against the command.** Patterns fired on reads, commit messages and closing notes.
   The pattern is now tested against what each part of the command runs: not a part that only reads or prints, a
   commit or tag message, a heredoc body no shell or interpreter reads, or a quoted argument of several words given
   to a program that does not run it. Text handed to a shell is still read. This is a looser check than 0.3.1's,
   by the owner's decision: a program outside the short list that runs its quoted text passes. An entry with no
   pattern gated every command in every clone during the trial; it now gates nothing and the health check fails on
   it. Setup writes a pattern only over a command the team has today, never over a slot that is not filled in, and
   the health check warns about a gate written over an unfilled slot.
6. **A push may set a variable on its own command line.** The general refusal is dropped by the owner's decision.
   The one variable that moves the runtime's transcript folder, `CLAUDE_CONFIG_DIR`, is still refused by name.

Three corrections from a security review of 0.3.2, shipped with 0.4. A part of a command that redirects its output
or runs `tee` is never read as read-only, and the file it writes is tested against the gate patterns. Quoted text
is left out only for the short list of programs that record or print it (a commit or tag message, the event
script's notes, `echo` and `printf` with no redirect), where 0.3.2 left it out for every program but a list of
runners. A push that sets `HOME`, `XDG_CONFIG_HOME`, `GIT_DIR` or `GIT_EXEC_PATH` is refused, since each moves
git's own configuration or hooks; proxy and connection variables still pass. Not added: a check of shell
redirects against the outside-the-workspace option, which reads file tools only; a redirect is tested against the
team's gate patterns.

Two small things: the session start names a memory file that is in no index, and `sync.py --help`, or a folder
that is no workspace, prints the usage or says so in place of "not on storage: git".

Not built, by the owner's decision: a session id per unit, a root cause on end records, a shorter setup, the first
push of a new workspace, further hardening of the hooks against reworded commands, the genuine-file check above.

### 0.4.0 (2026-11-19): the agents half

A workspace sets `core_version: 0.4.0`. Each item says whether it is a port of the reference system's practice, a gap filler
(the reference system has no equivalent or leaves the point open) or new.

| Item | Label | Reason |
| --- | --- | --- |
| The four mock adapters in one file, the contract checker, slot output as JSON rows with named fields | new | the reference system uses real services; a product needs a world a team can run on day one, and an adapter needs one written contract to be checked against |
| Run records (ledger, phase log, blocker register) as three files written as one all-or-nothing batch and committed by path | port | same record shape, line caps, cause tokens, blocker keyed by the missing thing; the reference script also shares, here the controller shares with `sync.py` |
| The ladder of nineteen phases | port | names are generic rewrites of the reference ladder |
| Readiness verdict as a first line the dispatch reads | port with a gap filler | the reference asks for readiness before a run; here a worker cannot start without the verdict, enforced in code |
| Sandboxed background dispatch and the spawn check in the gate hook | port | same flags and sandbox shape, the command typed in the shell itself so the check can read it |
| A worktree bound to the workspace in the machine's config folder, and `run.py state` reporting whether a worker's gate hook was seen | gap filler | what a worker loads is unverified in the reference system; the product verifies what it can and says the rest: hooks load in a worker only when the plugin is enabled for its session, and sub-agents are not known to load them |
| A worker's report as `sessions/<item>/report.md` and the close-out checklist read by `run.py confirm` | gap filler | the reference reads the runtime's own job state, which a product cannot assume |
| The rails said again after compaction | port | same list, read by the index hook while a run session is open |
| Card agent tick as deterministic code with a launch program for the judgement | port with a gap filler | pause, pickup, pool cap, waiting on a chat answer, stop at ready for release and the quiet one-word tick are ported; the launch program is how a product stays independent of one runtime |
| Agents monitor: alive, stuck, uncommitted or unshared files, paused; one finding a day | port | the reference has more checks (heuristics on agent commits, disk, trend); not ported, the product has no counterpart for them yet |
| Release monitor: reads checks, records a verdict, posts only a fail, no checks counts as a fail | port | |
| Card triage drafts only, creation gated as a strong action | port | |
| Review evidence rules in `review_check.py` | port | the reference runtime drops findings in code; same rules, same twelve-finding cap |
| Support week as a handover file and a short routine in the triage mode | port | |
| A grant's holder may be an agent's own name; the health check fails an agent that is also an approver | gap filler | agents hold no approver role; a grant to one needs a name to hold |
| Security corrections from a review of 0.3.2 | gap fix | see the paragraph above |

Not ported: the reference agents monitor's trend and heuristic checks, its weekly and daily jobs, and the reference
card agent's choice of entry point by item status beyond open and in progress. Known limits: the tick has no
real runtime in its tests (a fake launch program stands in); sub-agent hook loading is unverified; the mock's branch
rule is a model of a code host's, not a copy of one.

Joined with the runbooks part (built beside this half, merged before release). The agents mode ships one gate of its
own, `create a tracker item`, under `gates:` in its `module.md`; setup writes it once the tracker slot is filled, so
creation only on an approver's recorded approval is not left for a team to discover (port). Setup asks one question
about code repositories and points to the runbooks part's first load. Not built, by the owner's decision: a check of
shell redirects against the outside-the-workspace option.

A live start of one worker was tried once on the build machine and refused by the runtime before any session began:
the worktree's repository had not been trusted by a person. Nothing past that point is observed: whether a worker's
session loads the gate hook, commits and reports is still unverified by a live run. Two changes came out of preparing
it (gap fillers): the printed command names the core plugin's folder, so a worker's hooks do not depend on what is
installed for its session, and the worker's sandbox may write the workspace's ledger folder and sitting state, since
without them a worker could not open the session its close-out is read from; the folder an ask's answers are read
from is denied.

### 0.4.1 (2026-11-19): three fixes from the security review of 0.4.0

A workspace sets `core_version: 0.4.1` and lists its code repositories under `repositories:`.

1. **A run binds only a worktree of a declared repository.** Dispatch bound any folder it was given, and a bound folder
   counts as the workspace's for the gate. It now binds only the top folder of a git worktree whose repository a
   person listed under `repositories:` in `workspace.yaml` (by folder or by the address it is cloned from; read from
   the team's copy), never the workspace, a folder that holds the workspace or the home folder, or the file system
   root. Setup asks for the list in its question about code repositories.
2. **The event script is known by where it stands.** Its quoted notes are left out of what a gate pattern reads only
   when the script is the program the part runs, after variable assignments, an optional python and a path; a part
   that merely mentions its name, or that runs a shell, `eval`, a `-c` flag, `xargs` or `ssh`, is read whole.
3. **A background start names the settings dispatch wrote.** The file must be `sessions/<run>/workers/<item>.settings.json`
   for an item dispatch bound, and its sandbox must equal what dispatch writes for that item now; inline settings, a
   copy elsewhere and an edited file are refused. The start is found behind `env`, `nohup`, `timeout`, `command`,
   `exec`, `nice`, `time`, `setsid` and `caffeinate`. Known limit, unchanged: any other wrapper, a script or a
   variable holding the program's name gets past, as with every check that reads a command.

### 0.4.2 (2026-11-19): three fixes from the review of 0.4.1

A workspace sets `core_version: 0.4.2`. A person whose repositories are listed by address adds the folders that hold
their copies to their `areas` file.

1. **The settings of a background start are the whole file dispatch wrote.** Only the sandbox was compared, so other
   keys could be added to the file. The parsed file must now equal what dispatch writes, key for key.
2. **A start names its settings once and leaves the file alone.** More than one settings flag is refused; the
   `--settings=value` form is read like the spaced one; a command that also writes, removes or touches the settings
   file in any part is refused. Known limit: the file is read when the command is checked and again by the runtime
   when it starts, and a write between the two from another process is not seen.
3. **An address is not enough to bind a worktree.** A repository's address is its own word for itself and any folder
   can be given one. A repository listed by address is bound only when its folder sits inside a working area the
   person declared on that machine (the `areas` file in the machine's config folder, which a session's file tools and
   shell writes are already refused on); one listed by folder stands as before.

From here, findings in new code that come down to rewording a command are written into the known limits, not fixed.

### 0.4.3 (2026-11-19): setup builds a workspace without a terminal

A workspace sets `core_version: 0.4.3`. Gap filler: the reference system has no setup step, its workspace was made
by hand by the people who run it, so nothing here is a port.

The defect, seen in two trial runs with a lead who does not use a terminal: after the interview the gate refused the
assistant's writes to the control files, since a control file needs an approver and the approver list was still
empty; the lead was asked to type commands to add herself, an agreement she had typed earlier was refused, and the
first share failed with a request for one more command.

1. **A setup command, valid only where there is no workspace.** `setup.py <workspace> show <answers>` prints a
   summary of what the control files will say; `build` writes them from the interview's answers file (approvers,
   gates and backstops, storage, modes, repositories, the team's own rules, the slots), records the founding approval,
   makes the first commit with its `Approved-by:` line and the first share. Whether there is a workspace is read from
   the team's copy and from what git remembers: the shared repository's branch, any commit in the folder that held a
   `workspace.yaml`, the folder's own tie to another address; on a shared folder, a ledger. Emptying the local
   approver list, deleting local files or pointing at another address does not reopen it.
2. **One typed agreement.** The person running setup must be an approver the answers name. Their agreement is read
   by the same reader as any other, for the subject "setup", from the runtime's transcript of that sitting, and only
   from messages typed after the summary as it reads now was shown. Changed answers are shown and agreed to again.
3. **No command typed by a person.** When the first share cannot go through (no address yet, no access) the command
   says what a person arranges in plain words, and `share` finishes it later. The refusals that used to tell a
   person to edit a file or run git now point to setup.
4. **The gate is unchanged.** A free-form write to a control file waits for an approver in a new folder too. The
   setup command writes from its own process, as the journal command does on a shared folder.
5. **Setup asks for the team's own rules**, one optional question, and for the shared repository's address.

6. **A missing git user name is set at first setup** (gap filler, owner decision). Only while there is no workspace
   yet, and only when the machine has no git user name: the person gives their name as an answer, the summary shows
   it ("You are <name>"), and the build sets it in that workspace's own git config, never the machine-wide one. It
   must be an approver the answers name. A name the machine already has is never replaced, and a session setting a
   name any other way is refused as before. Shared-folder teams are unchanged. The limit, plainly: at first setup the
   name is what the person told the assistant, covered by their typed agreement to the summary that shows it;
   nothing else proves it.

7. **Git's hooks are installed only inside the workspace repository** (defect found in trial run 2; owner's rule:
   never install into a machine-wide hooks folder). The installer followed git's `core.hooksPath`, so on a machine
   whose git config names one hooks folder for every repository it renamed that folder's own hooks and wrote stubs
   bound to one workspace there. Every repository on the machine then ran them, and a machine hook using the same
   rename convention ended up calling itself. Now the stubs go in the repository's own hooks folder (the common
   directory's, so linked worktrees share them) and no file outside it is created, renamed or edited. When a hooks
   folder is in force from outside the repository, the install sets the repository's own `core.hooksPath` to its
   own folder, writes the outside folder's path beside the stubs (`trampo-outside`, rewritten on every install),
   and each stub runs the machine's hook of the same name from that folder after its own check, with the same
   arguments and input, and returns its answer. A `core.hooksPath` a person set in the repository to another folder
   is not replaced: the install refuses and says what to do. The health check warns about a stub of ours left in an
   outside folder and prints the commands that put the old hook back; it changes nothing itself. The guard on the
   stub files covers the repository's folder, the folder git resolves and the recorded outside folder. Gap filler:
   the reference system has no such case. Limits: only the system and user scopes of git's config count as outside
   (a path given on a command line or through the environment is not read); the health check looks in the outside
   folder in force now and the one recorded, so a stub left in a folder no longer configured is not found; the
   recorded path is an ordinary file, like the hook kept as `.next`.
   **The machine's other hooks run for the workspace too** (owner decision: "but keep it to the repository"). For
   every executable file in the outside folder that carries a client-side git hook name (pre-commit, commit-msg,
   post-merge, post-checkout and the rest; not the two above), the install writes a pass-through stub in the
   repository's own folder that runs the machine's hook at its original path with the same arguments and input and
   returns its exit code. Backups, helpers and any other file name get none, and neither does a file carrying one
   of our marks. Each install follows the folder: a hook added there gains a stub, one removed loses its stub. A
   hook a person put in the repository's own folder is never replaced; the install names it, and the session start
   tells the person the machine's hook of that name does not run here. The stub guard covers the pass-through
   stubs. Limits: a hook added to the machine's folder runs for the workspace from the next session start, not
   before; the hooks a receiving repository runs (update, pre-receive and the like) get no stub; the guard does not
   cover the machine's own hook files, as it never did.

Known limits. The setup command is a program a session runs, and its checks are the same kind as the hooks': a
session that removes the folder's git history and names a different, empty address builds a new workspace there, and
still needs a person's typed agreement naming the approvers. The record of when the summary was shown is an ordinary
state file. On a shared folder the seeded memory files are journaled by the skill after the
build, as before.

### 0.4.4 (2026-11-19): defects from the second trial run

An independent judge read trial run 2 and listed what the product got wrong. Each item below was reproduced in a
failing test before it was changed. None is a port of the reference system: all are gap fillers.

1. **The agent loop's lock is released after every tick.** The loop script set a cleanup and then replaced itself
   with the tick program, so the cleanup never ran and every tick after the first found the lock held. The script
   now waits for the tick and removes the lock on any exit, a failed tick included, and passes the tick's exit
   code on.
2. **The approval reader is told which gated action it is reading for.** One subject can have several gated
   actions (a notice and a tracker item for one incident). The reader took only the subject, so any refusal near an
   agreement had to count against it, and "Yes, post the notice for X. Hold the ticket for now" read as a no. The
   gate now hands the reader the words of the gated action's name (those over three letters). Beside an agreeing
   sentence that uses one of those words, two things are read as being about another action: a sentence right
   after it that refuses in its own words (four words or more, none of them the action's, not pointing back with
   "it", "that" or "this", not opening as a condition), and a short refusal earlier in the message. What follows a
   colon in the sentence that agrees and names the subject is the terms being agreed to ("yes to the grant in
   <file>: template wording only, until Monday") and is a condition only when it opens as one or refuses. Without
   the action's words (a control file, a file outside the workspace) the reader is as strict as before, apart from
   the colon rule. Limits: the action's words are the team's wording for the gate, so an agreement in other words
   ("the ticket" for a gate named "create a tracker item") is still read strictly and the person is asked again;
   an agreement that does not name the subject still opens nothing; a refusal in a long sentence that avoids both
   the action's words and a pronoun, right after an agreement, is read as about something else. That last one is
   weaker than 0.3.2 and is the price of reading "Don't put the customer's name in either of them" as an
   instruction and not a refusal.
3. **A gated action is checked after the shell leaves the workspace.** The gate found its workspace from the
   shell's folder, so a release run from a code folder that is no bound worktree was not checked at all and left
   no approval record. The gate now remembers, in the product's folder under the person's config folder, the
   workspace each sitting was last seen in, and in a folder that belongs to no workspace it applies that
   workspace's gated actions and nothing else: the other folder's files, hooks and pushes are not its business.
   Limits: a sitting that never ran a tool inside the workspace is not known; the stop checks still find their
   workspace from the folder; one small file per sitting is kept and never removed.
4. **The run's state names a worker only once its session has opened.** An item whose start command was printed
   read "worker dispatched" even when the runtime had stopped the start at a prompt. It now reads "start command
   printed, no worker session has opened for it" until a session has opened for the item.
5. **The printed start command drops the child-session mark.** A start typed inside a session inherited that mark
   and the worker saved no transcript. The command now begins `env -u CLAUDE_CODE_CHILD_SESSION`, and the check on
   background starts reads through `env -u NAME`, which it did not, so a start behind it was not checked. The
   effect of the mark on the runtime is taken from the trial's run log and was not observed here.
6. **A sitting with no record is told so at each prompt.** This one changes a written rule and is flagged to the
   owner: the core rules said "a quick question leaves nothing", and the trial's person came back the next day to a
   question that had left nothing. The rule now reads: a question someone may come back to leaves an ad-hoc
   record, and only a question about using the assistant leaves nothing. The prompt hook says one line to the
   assistant while a sitting has had no record. It blocks nothing and repeats no reply.
7. **The constitution's date: not reproduced.** Nothing in the product writes a date into `constitution.md` since
   setup builds it from the seed, and the product has no date source of its own to read: it uses the machine's
   clock everywhere. A date in that file in the trial was typed by the assistant.
8. **Documentation** (`docs/agents.md`): the four one-time steps before a worker starts, an example launch program
   and worker prompt, who writes a standing grant, how an agent's copy keeps up with the team, the earlier-sessions
   folder, the tracker's state words, the handover file and the first push to an empty shared repository.

### 0.4.5 (2026-11-19): waits, shared agent state and the owner's answers to the second trial

A workspace sets `core_version: 0.4.5`. Each item was reproduced in a failing test before it was built. The label
says where it comes from: **as the reference does**, **the reference's intent with this product's mechanism**, or
**new (gap filler)**.

| Item | Label | What it does |
| --- | --- | --- |
| A. An agreement in the gated action's words opens the gate without the item's id | the reference's intent with this product's mechanism | Only while exactly one gated action is waiting in the sitting, and only from a message typed after the gate first refused. With two or more waiting the id is needed and the refusal says so, listing them |
| B. A real wait for an unattended worker | the reference's intent with this product's mechanism | `agent.py wait NAME ITEM KEY` moves an item from the pool to the waits. Waiting items count in the cap. Only an approver's reply ends a wait; another person's reply is noted and the wait stays. The approver list is this product's |
| B. Agent state guarded from hand edits | new (gap filler) | A session's write to `.trampo/state/agent-*` or `sessions/agents/` is refused |
| C. Agent state shared through the team's repository | the reference's intent with this product's mechanism | `sessions/agents/<name>.json`, one commit per changed tick, an idle beat once an hour; a monitor in another clone syncs and reads it |
| D. Assigning an item to an agent is a seeded gated action | the reference's intent with this product's mechanism | Shipped with the agents mode as a pattern over the tracker slot's `assign`, with the agents' names read from `agents/*.yaml` |
| D. The slot runner checks the same gates | new (gap filler) | Inside a session, `slot.py` refuses a gated call that holds no recorded approval naming what the call names. From a security review of D |
| E. Recording an approval for a control-file commit made outside a session | new (gap filler) | `prepush.py adopt <workspace> <commit>`: the approver's own typed agreement naming the commit, never a reply through the ask slot, never an agent |
| G. A skill file is a control file | new (gap filler) | A write under `.claude/skills/` waits for an approver. The reference deliberately leaves its skills folder ungated: its agents edit their own skills daily. The gate here rests on the owner's decision that a person approves each proposed skill. The trial's lock on that folder was the runtime's own |
| Repeated causes in the review | new (gap filler) | The count joins classes that differ only in case, spaces or underscores, and sessions whose dated subjects share a name |
| A trial tick for the monitors | new (gap filler) | `--dry-run` on `monitor` and `release` |
| A backstop recorded as "nothing yet" | new (gap filler) | The health check warns, as the setup text already promised |

Not built, by the owner's decision: a person as a grant's holder.

**Security review of D.** The gate read the raw command, and the slot runner takes `--timeout N` between words and a
workspace path with a space, so `tracker assign` could be spelled past the pattern; the same was true of
`create a tracker item`. The gate now also tests each pattern against the call as the runner reads it. An assignee
that reaches the line through a variable cannot be read from the text, so a word with shell expansion in the
assignee's place asks for approval, and the runner itself checks the words it was really given.

**Security review of G.** Three findings had one cause: the approval was matched by a word derived from the path and
the write was matched by text. They were fixed as one change of shape and not three patches.

1. A skill is approved as `skills/<name>`, not by its bare name. A skill called "notes" was opened by "Yes, send the
   notes to the committee". An agreement that gives the path satisfies it too. A name outside lower-case letters,
   digits and hyphens, or under three characters, is refused whatever was said.
2. Every control path a command writes is found, not the first one. A command that writes more than one is refused
   (one command for each), and a skill path holding `..` is refused. Before, an approval for one skill carried a
   second write in the same command, and reading one skill while writing another asked about the one that was read.
3. Paths are compared the way the disk compares them. Shell patterns for every control file ignore letter case, and
   a file written with the Write or Edit tool belongs to the workspace when its folder is the workspace on disk,
   however the folder's name was spelled. Before, `.claude/Skills/...` in a shell command, and any control file
   reached through the workspace folder's name in another letter case, were not guarded at all. That second gap was
   older than G and covered every control file.

The same review asked whether other control files share the first finding. They do, and this is **not fixed here**
because it changes what approvers type for gates already released: the folders `slots/`, `agents/`, `.claude/hooks/`
and `.claude/agents/` are approved by the words "slots", "agents" and "hooks", so "go ahead and tell the agents"
opens a write to `agents/`, and `.claude/agents/` shares its word with `agents/`. The files (`workspace.yaml`,
`constitution.md`, `grants.md`, `approval-gates.md`, `settings.json`) carry a dot or a hyphen and do not have the
problem. The fix would be the one used for skills: the folder's path with its slash as the key.

Known limits.

- A: the agreement may be about something similar that uses the same words; a wait for a file outside the workspace
  counts as a waiting action too.
- B: a non-approver's reply is used up by the poll and appears only in that tick's output.
- C: a stopped loop is noticed from another clone after two intervals and one hour; each monitor tick runs a sync;
  a pause is shared at the next tick.
- D: the pattern covers the slot runner and `slots/tracker`. An agent's name anywhere after `assign`, and any
  unexpanded shell word, asks for approval, so some assignments to people ask needlessly. The runner's own check
  applies only inside a session and only to calls made through `slot.py`.
- E: one record covers every control path of the commit.
- G: only `.claude/skills/` in the workspace. Whether the runtime also asks before a write there was not observed.
  Which paths a shell command writes is still read from its text, as for every gate that reads a command: a path
  built at run time is not seen.
- Path comparison by the disk works only for folders that exist; a control folder being created under another
  spelling of a parent that does not exist yet is not matched.
- Repeated causes still depend on the class a person typed, or on subjects that share a name.

Left alone, for the owner: reply length, and card work writing system facts back to runbooks.

### 0.4.6 (2026-11-19): folder approvals by path, and card work feeding the runbooks

A workspace sets `core_version: 0.4.6`. Each item was reproduced in a failing test before it was built.

| Item | Label | What it does |
| --- | --- | --- |
| A control folder is approved by its path with the slash | new (gap filler) | The keys for `slots/`, `agents/`, `.claude/hooks/` and `.claude/agents/` are those paths, met by the folder with its slash or by the path of a file in it. The reference has people read an approval; a reader in code needs a key an everyday sentence cannot contain |
| The settings file is approved as `.claude/settings.json` | new (gap filler) | `settings.json` alone is the name of many files a team may talk about |
| A card writes the system facts it learned into the runbooks at close | as the reference does | System facts go in the system or flow runbook in the same session; what was checked for the card stays in the record. A fact not seen replayed is marked the way a first-load draft is |
| A done card's record carries a `runbook:` line | new (gap filler) | `event.py close` warns, and closes, when a done card's record has no such line or still holds the template's placeholder. It refuses only a line that names a runbook that is not a file: that is a false statement in the record, not a forgotten line. The owner chose the warning over a refusal. The reference states the rule and does not check it in code |

**The approval keys, in full.** Before 0.4.6 a control folder was approved by its last word, so "Sure, go ahead and
tell the agents" opened a write to `agents/card.yaml`, and `.claude/agents/` shared the word "agents" with `agents/`.
Now `agents/` is not met by `.claude/agents/...`, and the reverse. This changes what approvers type for gates already
released: "Yes, change slots" no longer opens anything; "Yes, change slots/" or "Yes, change slots/tracker" does. An
approval recorded before the upgrade for a folder change that was not pushed yet no longer covers it, and the
approver is asked again.

Left as they are, with the reason: `workspace.yaml` and `constitution.md` sit at the workspace root, so their name is
their path. `grants.md` and `approval-gates.md` are still approved by file name without `memory/shared/`: the names
are not everyday words, the full path is a lot for an approver to type, and a yes giving the full path already
satisfies them. This is the owner's decision: they stay approved by file name. The weakness that remains is a team
that keeps another file with one of those two names.

**Item G of 0.4.5, relabelled.** The skills approval is new (gap filler). The reference deliberately leaves its
skills folder ungated, because its agents edit their own skills daily. The gate rests on the owner's decision that a
person approves each proposed skill, not on the reference's practice.

Not built, by the owner's decision ("not now"): a word budget for replies.

Known limits.

- A bare yes typed after the gate has asked, while it is the one thing waiting, still opens a control folder
  without naming it (0.3.2, kept).
- The folder rule tells `agents/` from `.claude/agents/` only by the text right before the word; a path such as
  `old/agents/card.yaml` in an approval meets the key `agents/`.
- The close check warns for a missing line and so does not stop a close. It reads the record's line and that the named files exist. It cannot tell whether the facts are in
  them, whether a fact was missed, or whether "none learned" is true.
- The check runs only for a card session closed as done whose record is `sessions/<subject>/session.md`. A card
  with no record file is not asked.
- The card mode named `qa/runbooks/` where the runbooks part writes `runbooks/`; the mode now says `runbooks/`.

**The publishing scan was blind on macOS.** `scripts/deny-scan.sh` looked for ticket-key and 12-digit shapes with
`\b`, which `git grep -E` honours on Linux and ignores on macOS. On a Mac the shape scan matched nothing and printed
"clean", while the same script failed in CI from 0.3.2 on. Every local "clean" before 0.4.6 covered the terms file
only. The pattern now spells its edges out, and a test builds a small repository holding each shape and expects the
script to fail on the machine the suite runs on. The fixed scan found seven lines, all one fictional account code in
the approval tests and `core/protocols/gates.md`; the code was renamed to a lower-case form the scan does not flag.
The approval reader treats any letters, a hyphen and digits as a code, in either case, so the tests read the same
behaviour, and a direct test now holds "a code is matched whole". No file was excluded from the scan.

### 0.4.7 (2026-11-20): a card closes as done only on a QA verdict of PASS

A workspace sets `core_version: 0.4.7` and copies the card mode's seeds and templates again.

| Item | Label | What it does |
| --- | --- | --- |
| A done close of a card needs a last QA verdict of PASS | new (gap filler), owner decision 2026-11-20 | `event.py close --outcome done` on a card session reads the last line starting `Verdict:` in `sessions/<card>/qa-report.md` and refuses unless it is exactly `Verdict: PASS` |
| One verdict line per QA pass | new (gap filler) | `Verdict: PASS`, `Verdict: FAIL` or `Verdict: CANNOT-VERIFY`, at the start of a line, nothing after the word. The last one in the file counts. Written into the card mode, a `qa-report.md` template and the worker brief |
| `run.py confirm` reads the same line | new (gap filler) | A few lines, so it was built: a QA pass that failed after the worker closed shows up when the controller confirms the item |

**Why it is a gap filler.** The reference requires an independent QA pass before a card is delivered and says so in
its instructions. No script of its own reads a QA verdict when a card closes. The nearest scripted check there is
at the first push of a branch, which wants a recorded passing self-check for the commit being pushed. That is a
different check at a different moment, so the rule here is the owner's decision, not a port.

**What is refused.** A missing report; a report with no verdict line; a last verdict of FAIL or CANNOT-VERIFY; a
last `Verdict:` line that is not one of the three words written exactly (the template's placeholder, lower case,
words after the verdict). A park is not asked, and neither is any session that is not a card. The mode already
let a push go ahead on `skipped: no local path`; such a card can be pushed and parked, and cannot be closed as done.

**What this check is not.** The close command reads one line of a file that the same session can write. It does
not know whether a QA helper ran, whether it was a different helper from the implementer, or whether the evidence
above the line is true. An assistant that writes `Verdict: PASS` itself passes the check. It turns a forgotten QA
step into a refusal with instructions; independence stays a rule of the mode that a person can audit by reading
the report. The control outside the assistant is the team's own review and release step.

**The worker path.** A worker in an epic run closes its card with the same command, so the check applies to it
unchanged. The brief now tells the worker where its falsifying helper writes and what the last line must be.
`run.py confirm` lists the verdict beside the other things an item lacks.

**A recorded skip, closed on an approver's yes.** new (gap filler), owner decision 2026-11-20 ("yes, an approver
can move it"). When nothing can run locally, the QA pass is the line `Verdict: SKIPPED: <reason>`. A done close of a
card whose last line is a skip waits at the gate hook for an approver's yes naming the card, which is recorded as an
approve line under the gate `close a card with QA skipped` with the card as its key: the same record every other
approval uses, not a second store. The close command and `run.py confirm` accept the skip only when such a line, by
someone on the approver list, names that card. FAIL and CANNOT-VERIFY stay refused whatever was said, and a skip
with no reason is not a skip. The yes is read from the conversation and written by the gate hook, so it carries the
same trust as other approvals: the hook reads who typed it from the declared git name, and the reason in the report
is the assistant's own text. A worker in an epic run cannot ask a person, so it parks a skipped card.

**Deferred: a forward move that skips a phase of the run.** The run's ladder refuses only a move back without a
cause token; any forward move is accepted, including one past "Test checks". The owner decided not to refuse it for
now ("No for now"): `run.py confirm` already reads the item's own report, its review request's checks and findings,
and its QA verdict before the controller treats it as finished, so a skipped phase still shows up where it matters.

Known limits.

- The verdict belongs to the file, not to a commit: a PASS written before later changes still reads as PASS.
- A card session whose subject is not the folder name under `sessions/` is told its report is missing.
- A team that keeps QA reports elsewhere has to write the verdict line in this file as well.
- An approver's yes to closing a skipped card stays valid if the report later gets a new skip with another reason.
- The skip's yes is accepted from any ledger in the workspace, so a yes recorded in one session counts in another
  session on the same card.

Also in this release: the README and the adoption page say Python 3, tested on 3.12. The changelog line about the
visual README and the `docs/wiki/` pages moved from "Unreleased" into 0.4.7, because those pages were committed
after the 0.4.6 tag.

### 0.4.8 (2026-11-24): a lite setup for one person

A workspace sets `core_version: 0.4.8`.

| Item | Label | What it does |
| --- | --- | --- |
| Setup offers lite or full | new (gap filler), owner decision 2026-11-24 | Lite is the core, the card mode and the runbooks part, for one person. It asks three questions (the team or workspace name, the code repositories as folders on this machine, the approver) and sets everything else |
| Lite is refused when the card mode or the runbooks part is missing | new (gap filler) | The refusal names `claude plugin install <part>@trampo` |
| Lite writes the named repositories into the person's `areas` file | new (gap filler), owner decision 2026-11-24 | Only after the person agreed to a summary that names those folders. Until now the product never wrote that file; a person did, by hand |

**Lite's defaults, against the full interview's recommended answers for one person with no second reviewer.**

| Setting | Lite | Full, recommended |
| --- | --- | --- |
| storage, branch | git, main | git, main |
| approvers | the person at the keyboard | the same |
| modes | card | the person's choice; card for this comparison |
| outside | ask-first | ask-first when changes pass no review |
| areas | the named repository folders, written by setup | written by the person, by hand |
| gated_commands | none | none unless the team names one |
| backstops | none, since there is no gate | asked for each gate |
| slots | stubs | stubs, or the mock for a trial |
| rules | none | optional |
| remote | not asked; shared later with `setup.py share` | asked when the team has one |
| grants, retro, caps | the seed's values (90 days; every 7 days over 14; 600 and 1,500 words) | the same |
| seeds of the card mode and runbooks | copied by the build | copied by the assistant |
| summary | one more line naming the folders that go into `areas` | no such line |

Lite matches full (owner, 2026-11-24): `workspace.yaml`, `constitution.md`, `AGENTS.md` and
`memory/shared/approval-gates.md` are byte for byte what the full interview writes for the same person answering
the recommended way, and a test holds that. The differences are only the rows above that are not control files: the
`areas` lines, the remote not asked, the seeds copied by the build, and one summary line. A first build had added a
gate on code pushes; the owner removed it, since lite gates only what full gates. No release or push command is
gated: the skill's rule is never to write a pattern over a command the team has not named.

Known limits.

- The `areas` file is written outside the workspace, on this machine only, and nothing records that setup wrote it.
  A second machine needs its own lines.
- A repository is named by its folder, which suits one person on one machine; a team moving to the full path lists
  it by address.
- Lite takes only its own answers: an answers file that sets anything else is refused, not merged.

### 0.4.9 (2026-11-25): lessons from the first lite run

A workspace sets `core_version: 0.4.9` and copies the card mode's seeds and templates, and the runbooks template
`first-load/questions.md`, again. The first real run of the lite path, on a demo booking app, found three gaps.

| Item | Label | What it does |
| --- | --- | --- |
| Setup suggests a name only from the folder | new (gap filler), owner decision 2026-11-25 | `setup.py WORKSPACE name` prints the folder's own name; the setup skill suggests that or nothing, never a name from the account, an email, a connector or the environment. In the run, a fresh folder was offered a name taken from the signed-in account |
| A person changing a card's scope or direction is a counted interaction | restores the practice it was built from | That practice counts a correction to the acceptance criteria or the direction, and a correction outranks a clarification. The card mode now names scope changes in any phase, so a cut made at close-out is counted too |
| "A product decision" is not by itself a reason for `no durable lesson` | new (gap filler), owner decision 2026-11-25 | The lesson is about how the session scoped the work, for example: keep a card to what was asked and offer extras as separate cards. In the run, a scope cut was closed as "no durable lesson" because it was called a product decision |
| Assumed, not asked | new (gap filler), owner decision 2026-11-25 | A question the session settles alone (from a README, by inference from another answer, or by choosing a design) goes in the record's Decisions table with `assumed, not asked` in the By column. First load's `questions.md` gains Answer and By columns and keeps such rows the same way |
| The lite setup page and the storyboard | documentation | The page says it was run end to end on 2026-11-25; the storyboard is ready to record |

Known limits.

- The rules on scope changes, lessons and assumed answers are text in the card mode and its templates. No script
  reads the Decisions table, the memory promotion table or `questions.md`; the close check still counts only that
  every memory promotion row is filled.
- A worker brief must not carry "assumed": the epic run's brief check refuses unsettled words, so assumed answers
  stay in the record, where the person sees them, and a brief names them only once they are settled.
- The name helper gives the skill one deterministic source. It cannot stop a model from reading other context; the
  skill text says not to.
