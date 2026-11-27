---
name: doctor
description: Check a Trampo workspace's health and explain what to fix. Use for "run doctor", "check the workspace", "is the workspace healthy", after setup, and after an upgrade.
---

# Doctor

Run `python3 -B "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" .` in the workspace. It exits 1 on any failure. Read every
line to the person in plain words; fix what is yours to fix and say what is theirs. The health check is a tool a
person or a session runs. It is not a gate.

**Failures** (the workspace is wrong):

- `workspace.yaml` missing or malformed, an unknown storage, git inside a synced folder, or a pinned `core_version`
  that is not the installed core (see the upgrade note in `docs/decisions.md` of the product).
- Gates with no approvers.
- A symbolic link inside the workspace, or an unreadable ledger line.
- `memory.md` missing, or a memory heading that claims live state with no `As of ...; re-check:` line.
- A grant that cannot stand (no gate, scope, holder or approver; something on the never list; a strong action with no
  exact target or holder). It opens nothing until fixed, and only an approver changes the grants file.
- An incident folder missing `README.md`, `analysis.md` or `actions.md`, or with no row in `incidents/index.md`.
- On storage: files: a file that differs from its journal (show the difference to a person, then adopt or restore),
  a control file written without an approved proposal, or text that looks like a secret.

**Warnings** (a prompt, not a refusal):

- A memory file over the team's word cap: split first, compress only with a person's yes.
- A memory file no index routes to: add its row.
- A gated action with no backstop named in `workspace.yaml`: ask an approver what stops it outside the hook.
- A grant with no ceiling and no expiry that nobody has reviewed for the team's number of days.
- Text that looks like an email address, a phone number, a street address or a secret (pattern guesses): take it out,
  in this session.
- A document, archive, screenshot or recording git would take: move it out or add its type to the ignore file.

`--rebuild` (storage: files) puts back memory files the journal holds and the folder lost.
