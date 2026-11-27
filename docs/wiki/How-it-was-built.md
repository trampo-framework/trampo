# How the reference system was built

Trampo comes from a working practice: the reference system, one team's way of working with Claude Code. Each part
of that practice began as an experiment on real work. The team measured it, then kept it or dropped it on the
numbers, and only then made it routine. This page tells that story and says, for each part, whether Trampo ships
it or whether it stayed in the reference system.

Numbers on this page are relative only, and come from the same period and the same caveats as
[Measured results](Measured-results.md): one team, 2 October to 20 November 2026, not measured on Trampo itself,
except where a line names an earlier period.
Some figures from the team's own account of this story could not be reproduced from its records, so they are left
out.

## 1. A delivery agent, with a person approving each step

The team built an agent that takes a work item through planning, implementation, review, QA and release, with a
person approving each step. It was put into production on real work.

- Trampo ships it: `modules/mode-card` (the card loop with its premise check, slices, independent QA and close),
  and `modules/mode-agents` (the card agent that runs it unattended, with a person still signing the release).
- What the records show: unattended cards passed review the first time 66.4% of the time after the first run, with
  8.4% rework after ready. Time to ready for release was slower than in the first run, not faster. See
  [Measured results](Measured-results.md).
- What the earlier task ledger shows, March to August 2026, before the measured period: 98.5% of the cards
  delegated to the agent that entered its loop were completed (cards marked done, over done plus failed, in the
  agent's own task ledger). Over the same months its average time from start to done went to about 2.4 times its
  best sprint, so completion held while speed fell.
- What the team's tracker shows, before the measured period and not rerunnable from this repository (unlike the
  telemetry figures, these come from the team's tracker, not from files here):
  - Share of delivered cards: from 25 March to 29 June 2026, about a quarter of delivered cards and about a sixth
    of story points. A card counts when it was resolved while the agent was its assignee. Counting every card the
    agent touched gives about 30%.
  - Speed: over the same period, the median time from in progress to ready for release was about 3 times faster
    than for cards done by people, and about 2 times faster against the whole team. The routing sent simpler cards
    to the agent, so part of this is card mix. It also sits before the stricter review measured later, which made
    unattended cards slower.
  - Bug share: the bug share of delivered cards roughly halved, from the last four months of 2025 to the first
    half of 2026. The months are noisy.
- Left out: the team's account also claimed that output rose 56%. It only holds against a holiday-season dip.

## 2. Adopting parts on evidence

The team measured each part separately (coding with AI, automated review of changes, browser QA) and kept what
worked. The hybrid it settled on: engineers drive the work locally with AI, and an independent agent does the
verification.

- Trampo ships the independent pass: the card mode will not close a card as done without a QA verdict of PASS,
  checked by a script. It also ships the telemetry ledger and the periodic review (`core/`) that make this kind of
  measurement possible in a new workspace.
- The measuring itself stayed in the reference system: the comparison between the parts was one team's analysis, not
  a shipped feature.

## 3. Knowledge as shared, reusable assets

One shared workflow repository holds the team's skills, its QA runbooks, its durable project memory and a record of
every work session. Every problem is logged with its cause and turned into a lesson, a runbook update or a fix, so
that a problem happens once.

- Trampo ships the mechanism: the workspace layout, memory with its read and write protocols, `modules/runbooks`,
  the session record, and the close step that turns each correction into memory or a runbook. The assets
  themselves (the team's skills, runbooks and sessions) stayed in the reference system.
- Counts of those assets are left out on purpose, because they would show the team's size.
- What the records show: the team kept extending agent coverage, the systems and flows the agents can work on and
  check through runbooks. Runbooks grew 3.9 times from 2 October to 20 November, the share of card records citing
  one rose from about 29% to about 45%. See section 7 for what was found on the way.
  See [Measured results](Measured-results.md).

## 4. Operational work done by background agents

Background agents handled release monitoring (with a suggested revert), incident triage, review of changes and the
weekly dependency upkeep.

- Trampo ships: `mode-triage` (alarms and incidents), `mode-review` (a read-only review of one change, run by a
  person or an agent), and in `mode-agents` the card agent, the agents monitor, the release monitor and card triage.
- Stayed in the reference system: the weekly dependency upkeep agent. An unattended review
  agent that learns from corrections is on the [roadmap](../../ROADMAP.md).
- What the records show: the open dependency upgrade backlog was 86% smaller at the last count than at the first,
  on the same scope.

## 5. Governance that makes speed safe

A rulebook sorted work into what an agent may ship alone, what needs approval and what stays human-only (money,
personal data, high-risk code). Personal data was filtered before the AI saw it. A global kill switch and automatic
pause triggers covered the whole system.

- Trampo ships a different, smaller set: approval gates with named approvers, a prepush boundary on git, the
  independent QA rule, and a pause that a person sets on one agent (`agent.py pause`).
- Stayed in the reference system: the three-colour rulebook, the filtering of personal data, the global kill switch
  and the automatic pause triggers. Trampo does not ship them.

## 6. Finding premise errors before work starts

Agents help find wrong assumptions in a work item before anyone builds it. Trampo ships this as the premise check
at intake in `mode-card`.

## 7. Found on the way: recorded, not fixed inside the card

A card stayed on its acceptance criteria. When the work met something else on the way, it did not stop and did not
widen the card. For example, a security concern found while building an unrelated feature was recorded and triaged,
not fixed inside the card. The finding was searched for in the shared register by its fingerprint and added as a
sighting, or as a new entry. Other sessions and agents read that register, and people triaged it later in their own
process: accept into planned work, decline, or fix, with later checks confirming it was covered. Something urgent,
such as a live exposure or data at risk, went to a person straight away instead of waiting in the register, and was
still not fixed inside the card.

- Trampo ships the practice: the register seed `memory/shared/known-issues.md` with fingerprints, sightings and an
  `escalated` marker, rule 10 of the constitution, rule 5 of the write protocol, and card triage in `mode-agents`
  sweeping the register. See [How it works](How-it-works.md#found-on-the-way).
- What the records show: about 57% of card records wrote down at least one finding outside their scope, and about
  45% of all findings were a sighting on an entry already in the register. See
  [Measured results](Measured-results.md#found-on-the-way).
- Why it was kept: cards did not inflate, and nothing found was lost.

## The reference system around the framework

The reference system also connected the assistant to the team's own data and tools, with per-person access. That is
specific to the team and is not part of Trampo, which reaches outside systems only through
[slots](Slots-and-adapters.md).

## What is next

Unattended delivery for low-risk work is the next experiment. It is on the [roadmap](../../ROADMAP.md).

Back to [Home](Home.md).
