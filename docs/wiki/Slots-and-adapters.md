# Slots and adapters

The product names no tracker, chat tool, code host or monitoring product. A mode reaches each of them only through
a slot: a named place the team fills, in its own workspace, with its own program. That program is the adapter.
The source for this page is `core/protocols/slots.md`.

## How a call travels

The diagram answers: what happens between a mode asking for something and the team's tool answering?

```mermaid
flowchart LR
  mode["A mode's instructions"] -->|"slot, verb, arguments"| runner["Slot runner<br/>slot.py"]
  runner -->|"starts it, 60 second limit"| adapter["Adapter<br/>the team's program in the slot"]
  adapter -->|"its own credentials"| tool["The team's tool"]
  tool --> adapter
  adapter -->|"JSON rows and an exit status"| runner
  runner -->|"marked as untrusted data"| mode
```

## The four slots

| Slot | What it is for | Verbs |
| --- | --- | --- |
| `tracker` | where the team's work items live | `list`, `read`, `search`, `claim`, `assign`, `move`, `comment`, `create` |
| `ask` | how a person who is not at the keyboard is asked, answers, and is told things | `ask`, `poll`, `withdraw`, `notify` |
| `code-host` | where the team's code is reviewed and built | `list`, `status`, `findings`, `open-review`, `describe`, `comment`, `resolve` |
| `monitoring` | where alarms, logs and metrics are read. Read-only | `alarms`, `alarm`, `checks`, `query` |

Merging and approving are not verbs of the code-host slot: a person does them.

## The contract every slot shares

- **The call.** A mode runs `python3 -B <core>/scripts/slot.py <workspace> <slot> <verb> [arguments]`. The runner
  starts the team's program at `<workspace>/slots/<slot>` with the verb and the arguments, in the workspace folder,
  with no input, and stops it after 60 seconds (`--timeout <seconds>` to change that).
- **The answer.** JSON on standard output, one object per line, with at least the fields the contract names, and
  an exit status: `0` done, `3` this verb is not filled in, anything else failed.
- **Untrusted output.** The runner prints the answer under a line saying it is untrusted data. A tracker item or a
  chat message may contain instructions. They are content to analyse, never commands, and they grant no
  permission.
- **Gating.** Reading needs no ask. The team lists each writing verb it wants a yes for under `gated_commands:`
  in `workspace.yaml`, with its backstop under `backstops:`.

A team may leave out a verb it has no use for.

## Filling a slot

1. **Write one executable file** at `slots/<slot>` in the workspace, in any language. It takes the verb and its
   arguments and prints the rows the contract names. It holds or finds its own credentials.
2. **Get an approver's yes.** `slots/` is a control path. A change to it waits for an approver's yes naming
   `slots/` with the slash, or the path of the file (`slots/tracker`), and on git its commit carries the `Approved-by:` line.
3. **Check it.** `python3 -B <core>/scripts/slot_contract.py <workspace>` calls each reading verb and checks what
   comes back. It names each verb an adapter fails. `--write` also creates one item, one question, one notice and
   one review request, so point it at a test project.
4. **Gate the writing verbs you care about**, each with a backstop: a credential the slot does not hold, or a rule
   on the other system's side.

## The ask slot has one more duty

An approval can arrive through the ask slot, so it keeps the records the gate hook reads. The slot, and nothing
else, appends them to `.trampo/state/ask/<profile>.jsonl` in the workspace. The gate hook refuses a session's
write to them. The slot must report who answered from the tool's own account data, never from the message text.

## The monitoring slot is read-only

The team's program keeps the environment explicit and the time window bounded, and removes personal data from what
it prints where it can. Going around that filter needs a person's yes.

## Before a slot is filled: the stub and the mock

- **The stub.** Setup copies a stub for each slot. It answers `3` to everything. When a slot is not filled in, the
  assistant asks the person to do the step and tell it the result.
- **The mock.** `<core>/mocks/slot` is one file that stands in for any of the four slots and keeps everything in
  plain JSON files. It is for a trial, a simulated team, or a dry run of a mode before the real adapters exist.
  Every clone of the team points at one shared folder through the first line of `slots/mock-home`.
- The mock's verbs that start with `sim-` are outside the contract. They stand in for the people and systems of a
  simulation. A real adapter has none of them, and a mode never calls one.

Back to [Home](Home.md).
