# Known issues

Defects seen outside the scope of the work that found them and left unfixed. The assistant records here and never
raises a tracker item on its own call: a person decides from the For review list, and the assistant applies the
decision. An in-scope defect is a task on the session's own list, not an entry here.

**How to write one.** A new entry gets the next id (`issue-1`, `issue-2`, in order, never reused), a heading that names the
failure, the date and the session that saw it, its typed fingerprint `<system>:<failure-class>` (the same value the
session's ledger carries as `--fp`), the evidence, and a status: `for review`, `accepted (<tracker reference>)`,
`declined (<who, why>)` or `fixed (<reference>)`. Seeing it again is a dated sighting line on the existing entry, never
a second entry: search this file for the fingerprint first.

**Escalation.** Most entries wait for a person here. One that is urgent does not wait: a live exposure, data at risk,
or what the team's approval rules call urgent. Tell a person straight away, add `escalated (<to whom, when>)` to its
status line, and keep it at the top of For review. It is still not fixed inside the work that found it.

    ## issue-1: <the failure, in one line> (<date>, <session>)
    Fingerprint: <system>:<failure-class>
    Status: for review
    Evidence: <command, path:line or query, with numbers>
    Sightings:
    - <date> <session>: <what was seen this time>
    **How to apply:** <what a session that meets this should do until it is fixed>

## For review

Entries a person has not decided on yet, newest first. A person answers each with accept, decline or fix.

- none yet
