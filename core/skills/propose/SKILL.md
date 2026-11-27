---
name: propose
description: Turn a change a team made to its own workspace into a draft proposal for the Trampo core or an upstream mode, stripped of everything that belongs to the team. Use for "send this upstream", "propose to trampo".
---

# Propose upstream

1. Start from a change the team already keeps: an edit to a mode file with its verdict (`retro` skill), or a rule in
   the team's `constitution.md`.
2. Rewrite it for strangers. Strip everything from the workspace: team, company, people and product names, record
   ids, memory text, numbers that identify a customer or a system. Keep the general problem, the pattern of evidence
   (counts, not contents) and the proposed text.
3. Show the stripped draft to the person and wait for a yes. Nothing leaves the workspace without it.
4. On yes, write the draft to `proposals/<date>-<slug>.upstream.md` for them to open against the Trampo repository.
   Do not open it yourself unless asked.
