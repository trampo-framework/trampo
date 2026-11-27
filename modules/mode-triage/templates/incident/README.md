---
id: YYYY-MM-DD-short-slug
date: YYYY-MM-DD
closed:
severity: S?
status: open
systems: []
items: []
owner:
kind: incident
risk: <low|medium|high>
ledger: <sid>
sessions:            # card sessions this triage opened, none or more
  - card: <card id>
    opened_at: <intake|diagnosis|remediation|follow-up>
---

# <One line naming the failure, not the system>

## At a glance

<Three to six sentences a stranger can read cold: what broke, what people experienced, what caused it, whether it is
fixed. Numbers, not adjectives.>

| | |
| --- | --- |
| Detected | <how: the alarm, the report, the dashboard> |
| Duration | <first impact to recovery> |
| Impact | <what people experienced, with counts> |
| Cause | <one line> |

## Documents

- [analysis.md](analysis.md): the diagnosis and the evidence ledger
- [actions.md](actions.md): what is being changed
- [runbook.md](runbook.md): a reusable procedure <delete if none>
- [queries/](queries/): the commands used
