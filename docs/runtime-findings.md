# Runtime findings

Step 1 of the plan: one day in the Claude desktop app on a shared folder, before relying
on any of these. Fill each row with what was observed, not what the docs say.

| Check | Sync client A | Sync client B | Result | Date |
| --- | --- | --- | --- | --- |
| Workspace `CLAUDE.md` (`@AGENTS.md`) loads in the desktop app | | | | |
| Workspace `.claude/skills/` loads | | | | |
| Plugin hooks run (UserPromptSubmit touch event appears) | | | | |
| Session transcript is reachable | | | | |
| `python3` is available to the agent | | | | |
| Two machines edit the same memory file: what the sync client keeps | | | | |
| `journal --diff` shows that conflict and `--restore` or `--adopt` settles it | | | | |
| Grep finds text in files-on-demand placeholders | | | | |
| Who installs core when nobody can enable org plugins | | | | |

## Verified from docs

- Marketplace file shape (`name`, `owner`, `plugins[]` with `name` and relative `source`),
  relative paths from the marketplace root, entry name equal to manifest name, and local
  directory marketplaces loading plugins in place:
  https://code.claude.com/docs/en/plugin-marketplaces (read 2026-10-25).
- `plugin.json` needs only `name`; `version` pins users; default `skills/` and
  `hooks/hooks.json` locations; hooks files wrap the event map in `"hooks"`;
  `${CLAUDE_PLUGIN_ROOT}` resolves in hook commands and skill bodies; a plugin with a
  top-level `bin/` is not installed by claude.ai or Cowork:
  https://code.claude.com/docs/en/plugins/manifest-reference (read 2026-10-25).

## From the plan review, not yet re-checked here

- A `CLAUDE.md` above the working directory stops `AGENTS.md` loading on its own, which is
  why setup writes `CLAUDE.md` containing `@AGENTS.md`.
- Cowork adds marketplaces only from git hosts or a zip, not a local folder, which is why
  team modules are plain markdown rather than plugins.
