# Principles

## Three layers, three improvement flows

Core, modules and workspace data change at different speeds and belong to different
people, so they live apart. Improvements move three ways:

1. **Upstream to the team**: a new core or module version, installed as a plugin update.
2. **Inside the team**: each close promotes facts to memory and edits the mode file; a
   later session judges the edit; control files change on an approver's yes.
3. **Team to upstream**: a change the team keeps becomes a stripped proposal through
   `propose`.

## The reference practice wins

The product is a working team's system made reusable. Where that team has a way, the product carries it. A rule of
the product's own stays only where the team never needed one (a gap filler) or the owner decided it. Each addition is
listed as new in `decisions.md`.

## A hook is a check, a backstop is the control

A hook stops an assistant that lost track of a rule. It does not stop a determined one, and it lets a call through
when it cannot tell. The control for each gated action is outside the hook, and the team names it.

## Plain files first

Markdown in a folder is the only source of truth. Hooks, transcript readers and search
indexes add to it and can be rebuilt; nothing correct depends on them.

## One backend per workspace

`storage: git` uses git for history. `storage: files` uses the journal in each session's
event file. A workspace never mixes them, and git never lives inside a synced folder.
