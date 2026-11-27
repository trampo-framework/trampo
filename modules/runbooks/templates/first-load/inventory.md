# Inventory: <team or product group>

Read at: orders-service@3f2a91c04b7e, handbook@2026-01-05

<!-- One "## <System>" section per system. Every feature row carries its entry point as <source>:<path>:<line>, or
(inferred) when it was not read. Name a source by its folder name and commit, never by where it sits on a machine.
About 40 to 70 lines per system; tables over prose. -->

## Orders service

Sources: orders-service (code), handbook (documents)

| Feature | Entry point | Covered by | Gap: what a runbook needs |
| --- | --- | --- | --- |
| Place an order | `orders-service:app/orders.py:14` | none | a flow; a test customer the run creates |
| Nightly export to the ledger | `orders-service:jobs/export.py:8` | none | a flow; a way to start the job on one record |
| Refund an order | (inferred) | none | the handler was not found: question Q1 |

Drift: what a document or an existing runbook claims and the code contradicts, or "none found".
Prerequisites: test data, accounts, sandboxes of outside parties, settings. What an assistant can build itself and
what needs a person.
Proposed work:
- S `runbooks/systems/orders-service.md`: the system file
- M `runbooks/flows/place-order.md`: sign in, place, read back
Risks: any step that would write to a shared test record, move money, or reach a real customer or an outside party.
