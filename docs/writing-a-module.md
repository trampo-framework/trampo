# Writing a mode

A mode is a folder with one layout, whether it ships upstream as a plugin or lives in a team's own repository.

```
mode-<name>/
  module.md                    manifest: name, version, the ledger kind, the seeds
  skills/<name>/SKILL.md       thin: open through the core session skill, then follow modes/<name>.md
  seeds/modes/<name>.md        the working instructions, copied into the workspace by setup
  seeds/...                    any other file the mode needs in the workspace
  templates/                   the records the mode fills
  .claude-plugin/plugin.json   only for a mode that ships as a plugin
```

- **The substance goes in the seeded mode file, not the skill.** The team owns `modes/<name>.md` once setup has copied
  it, edits it directly at each close, and it wins over the skill.
- **A mode opens and closes through the core `session` skill** and files under one ledger kind
  (`core/schemas/event.schema.json`).
- **A mode reaches a tracker, a person, a code host or monitoring only through a slot** (`core/protocols/slots.md`),
  written as `slot.py . <slot> <verb>`, with a verb the contract describes. It names no product. A test fails
  otherwise.
- **Its version is the core's.** Upstream modes are listed in `.claude-plugin/marketplace.json`.
