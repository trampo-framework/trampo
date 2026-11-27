---
status: not-yet-replayed
system: runbooks/systems/orders-service.md
waits: none
last-replay: none
---

# Flow: place an order as a signed-in customer

<!-- Replace every example below. status: is not-yet-replayed until a second agent replays the flow and
`runbooks.py verify` sets verified. waits: is none, or the unblock-list row a step needs (U<n>: what). Every step is
a "### <n>. <name>" heading that ends with (observed) or (traced from code); a traced step ends with its stamp. -->

## What this proves

One paragraph: the behaviour a passing run proves, and what it does not cover.

## Source references

- `orders-service@3f2a91c04b7e:app/orders.py:14`: the handler that places the order.

## Inputs and test data

What the run creates for itself (a fresh customer, a fresh order) and how. A flow runs on its own records, never on
shared ones.

## Steps

### 1. Sign in as the test customer (traced from code)

- Do: open the sign-in page of the test environment and sign in with the customer this run created.
- Expect: the account page opens and shows the customer's name.

_Written 2026-01-05 from code at orders-service@3f2a91c04b7e; not yet replayed._

### 2. Place an order for one item (traced from code)

- Do: add the first listed item to the basket and confirm the order.
- Expect: a confirmation page with an order number, and one new row for this customer in the orders store.
- Leaves behind: one order on the run's own customer.

_Written 2026-01-05 from code at orders-service@3f2a91c04b7e; not yet replayed._

## Checks

What to read back after the last step, and the value that proves the end state.

## Cleanup

Each record the steps left behind and how the flow removes it, or that it stays and why.

## Not replayable

Each step left out because it would reach a real customer, move money or call an outside party, with the reason and
its source.

## Gotchas

What has misled a reader before. Correcting this section does not reset a verified flow.
