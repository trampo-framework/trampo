# Standing grants

A grant is a yes an approver gives once, in writing, that opens one gate later without a yes to each change. A control
file: an entry stands only on the team's branch, with an approver's recorded yes. A grant can never open approving,
granting, or a change to the gates, approvers, agents, grants, slots or core rules.

Each grant is one second-level heading with a date, followed by its lines. Required: `Gate:` (the gate's name in
`workspace.yaml`), `Scope:` (folders or repositories, comma separated), `Holder:` (a kind of session, a session id, or
`any`) and `Approved-by:` (an approver's name and the session or reply where they said yes). Optional: `Target:`,
`Ceiling:`, `Expires:` and `Reviewed:`. A strong action (production, merge, release, creating a tracker item) needs
`Target:` naming the exact target and a holder that is not `any`. The health check warns about a grant with no ceiling
and no expiry that nobody has reviewed for the number of days the team set.

No grants yet.
