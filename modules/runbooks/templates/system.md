---
basis: code
sources: orders-service@3f2a91c04b7e
---

# Orders service (`orders-service`)

_Written 2026-01-05 from code at orders-service@3f2a91c04b7e; not yet replayed._

<!-- Replace every example below. basis: is code, documents or observed; the stamp above stays until a person or a
replay has seen the system and basis: becomes observed. Mark each detail nobody has seen with _(verify)_. Cite code
as <source>@<commit>:<path>:<line>. No path from one machine. -->

## What it is

One paragraph: what the system does and for whom. What it is not, when a sibling system is easy to confuse with it.

## Where it runs

| Stage | Address | How it is deployed | Notes |
| --- | --- | --- | --- |
| test | `orders.test.example` _(verify)_ | on every merge to the test branch | |
| production | `orders.example` _(verify)_ | by a person, from a tagged build | never the target of a flow |

## Access and sign-in

Who may sign in, the sign-in steps as a person sees them, the roles, and where a credential is kept (its name only,
never its value). `orders-service@3f2a91c04b7e:app/auth.py:22` _(verify)_

## Entry points

| Entry point | What it does | Source |
| --- | --- | --- |
| `POST /orders` | places an order | `orders-service@3f2a91c04b7e:app/orders.py:14` |
| nightly export job | writes the day's orders to the ledger | `orders-service@3f2a91c04b7e:jobs/export.py:8` |

## Data it owns

Each store by its exact name, its key, and the states a record moves through. `orders` table _(verify)_

## What it calls and what calls it

Each outside party and sibling system, the direction, and whether the call can reach a real customer or move money.

## Logs and signals

Where each entry point logs, and the line that shows a request succeeded or failed.

## Local

Runs locally: not known _(verify)_. When it does: the command, what it needs first, and which flows can run against
the local copy.

## Gotchas

What has misled someone before, each with its source.
