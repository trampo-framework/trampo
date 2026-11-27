# Roadmap

What is planned and not built yet. An item here is not a promise of a date. Each one names what it adds and what it
waits on.

## Review agent (agents module)

An unattended PR reviewer, added to `mode-agents` beside the card agent, the monitor, the release monitor and card
triage.

- It reviews each change it is asked to, with the `mode-review` rules and the team's standards in `memory/review/`.
- It learns with the people: when a person overrules or corrects a finding, that becomes a candidate lesson in the
  same shared memory the card sessions and people read, through the same write rules and approval gates as any other
  memory change.
- Its findings and outcomes go into the telemetry ledger, so the periodic review can see which findings people
  accept and which they reject.

Today the review mode can be run by an agent, but it is read-only and writes no memory. The intro video describes
only that.

Builds on: the code-host slot, which already lists changes and posts and resolves comments. Waits on: an owner
decision on when it starts.

## Unattended delivery for low-risk work

Letting the card agent take low-risk work through to ready for release with nobody at the keyboard, as the next
experiment.

- It starts with work the approval gates already classify as low risk, and a person still signs the release.
- It is kept or dropped on the measured results, as any part was.

Builds on: `mode-agents` and its card agent. Waits on: an owner decision on when it starts.
