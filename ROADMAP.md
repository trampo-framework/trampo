# Roadmap

What is planned and not built yet. An item here is not a promise of a date. Each one names what it adds and what it
waits on.

When two goals pull against each other, the order is **security, then quality, then velocity**. The releases below
follow it: the review and security agents come before the colours, and the colours before unattended delivery, so
that delivery runs only once both checks it relies on are in place.

| Release | Adds | Why it is here |
| --- | --- | --- |
| 0.6 | Review agent | Quality check on every change, unattended |
| 0.7 | Security agent | Security check on every change, unattended |
| 0.8 | Approval colours | Grades work Green, Amber or Red from the gates and the two agents' findings |
| 0.9 | Unattended delivery for low-risk work | Uses the colours; starts with Green work only |

## 0.6: Review agent (agents module)

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

Builds on: the code-host slot, which already lists changes and posts and resolves comments. Next up.

## 0.7: Security agent (agents module)

An unattended security reviewer for each change, beside the review agent.

- It reads the base-to-head diff for the classes of defect the security model names (secrets, injection, auth and
  access checks, unsafe input handling, dependency changes) and posts findings the same way the review agent does.
- A security finding blocks the change until a person resolves it. It is never downgraded by a quality or speed
  argument.
- Findings go into the same shared memory and telemetry ledger as the review agent's.

Builds on: the review agent. Waits on: 0.6.

## 0.8: Approval colours

Every card gets a colour before work starts, and again before release.

- Green: low risk, the gates pass, and neither agent has an open finding.
- Amber: needs a person's sign-off at the named step.
- Red: out of bounds for an agent; a person drives it.

Builds on: the approval gates and the two agents' findings. Waits on: 0.7.

## 0.9: Unattended delivery for low-risk work

Letting the card agent take low-risk work through to ready for release with nobody at the keyboard, as the next
experiment.

- It takes Green work only, and a person still signs the release.
- It is kept or dropped on the measured results, as any part was.

Builds on: `mode-agents`, its card agent and the colours. Waits on: 0.8.
