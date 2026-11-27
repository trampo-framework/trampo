# Contributing

Most improvements start inside a team's workspace: a close notices something about the method, the team edits its
mode file, a later session judges the edit, and the `propose` skill turns what the team keeps into a draft for this
repository.

1. **Strip the workspace out.** A contribution carries the general problem and the proposed change, never a team's
   memory, records, names, ids or numbers that identify a customer or system. The `propose` skill does this; check it
   anyway.
2. **Scan before you open a pull request.** Run `scripts/deny-scan.sh` with your own terms file (company names,
   internal hostnames, tracker prefixes). Keep that file out of git. CI also runs a secret scan.
3. **Keep the core small, and say what is new.** The product carries one team's proven practice. A change that adds
   to it is listed as new in `docs/decisions.md`, with the reason the proven way could not be carried over.
   Update `CHANGELOG.md` in the same change: one plain line on what changes for a team.
4. **Test first, and run every suite** from `core/scripts`: `python3 -B -m unittest discover -p 'test_*.py'`.
5. Contributions are under the Apache License 2.0.
