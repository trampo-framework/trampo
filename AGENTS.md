# Working on Trampo

This repository is the product: the core, the parts under `modules/` (six modes and the runbooks part) and the docs. The instructions an assistant follows inside
a team's workspace are `core/seeds/AGENTS.md`; this file is for work on the product itself.

## The frame

The product is one real team's working system made reusable. That team's practice wins by default. A rule of
Trampo's own survives only as a named gap filler or by the owner's decision. Anything else that is added is
labelled as new in `docs/decisions.md`, with the reason the proven way could not be carried over. Avoid adding.

## Rules

- **Nothing about any real team.** No company, product or people's names, no tracker ids, no chat, tracker, code-host
  or cloud product names, no hostnames, no paths from a machine. A mode reaches the outside only through a slot.
  `scripts/deny-scan.sh` runs in CI; its term list stays out of git.
- **Test first.** A failing test, then the code, then tidy. Run every suite from `core/scripts`:
  `GIT_CONFIG_GLOBAL=/dev/null python3 -B -m unittest discover -p 'test_*.py'`.
- **Tests isolate git and never write to the real home.** Every test module imports `testenv` first.
- **A hook is registered or it is prose.** Every hook is wired in `core/hooks/hooks.json`, for every shell-capable
  tool the wiring lists, and `core/scripts/test_wiring.py` has a test that fails when it is not.
- **Do not harden beyond the reference practice without saying so, and do not weaken it.** No signing, no new
  cryptography. Every hook lets a call through when it cannot tell; the pre-push hook is the one that refuses.
- **The docs say what the code does.** A change to a script changes the protocol, the skill and the constitution line
  that describe it, in the same commit. Delete what describes a removed feature.
- **One version everywhere:** `core/.claude-plugin/plugin.json`, each mode's `plugin.json` and `module.md`, and
  `core/seeds/workspace.yaml`. The tests compare them.
- Comments say why, never what. No change narration in code.

## Layout

`core/scripts/` (the engine and its tests), `core/hooks/hooks.json`, `core/seeds/` (the workspace a team starts
from), `core/protocols/`, `core/skills/`, `modules/mode-*/`, `modules/runbooks/`, `docs/`.
