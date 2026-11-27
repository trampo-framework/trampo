---
name: mode-review
version: 0.5.0
kind: review
seeds:
  - seeds/modes/review.md
---

# mode-review

One change request reviewed at its head commit, read-only, with findings that must pass evidence rules in code before a person sees them.

Depends on: core and the code-host slot. Takes nothing else; an agent or a person can run it alone.
