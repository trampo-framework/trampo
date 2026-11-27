---
name: mode-run
version: 0.5.0
kind: run
seeds:
  - seeds/modes/run.md
---

# mode-run

A set of work items driven to done in parallel: one background worker per item, sequenced on what each item waits for, with one run ledger, one phase log and one blocker register. Includes the readiness step that settles every question before the first worker starts.

Depends on: core, the tracker, ask and code-host slots, and the card mode (a worker runs the card loop). Takes nothing else.
