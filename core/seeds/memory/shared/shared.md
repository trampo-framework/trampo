# Shared memory: index

Facts a card session and a triage both look up.

| File | Holds | Read trigger |
| --- | --- | --- |
| `memory/shared/approval-gates.md` | what waits for a person, and how a yes is given | before any gated action; its rules are said at every start |
| `memory/shared/grants.md` | standing grants an approver agreed to once | before relying on a grant, and when the health check names one |
| `memory/shared/verification-method.md` | how a result is checked before it is called verified | before saying verified, done, clean or fixed |
| `memory/shared/known-issues.md` | defects seen outside the work's scope and left unfixed | when you find one, and before raising anything as new |
