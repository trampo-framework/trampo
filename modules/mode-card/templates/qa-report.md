# QA report: <card>

<Written by the QA helper, never by the implementer. One section per pass, appended; earlier passes stay. Each pass ends
with its verdict line, exactly as below: at the start of a line, one of the three words, nothing after it. The last
verdict line in this file is the card's QA verdict, and the card closes as done only when it is PASS.>

## Pass <n>, <time UTC>, base <commit> head <commit>

| Criterion | What was done | What was seen | Result |
| --- | --- | --- | --- |

Limits: <what could not be checked, and why>

Verdict: <PASS | FAIL | CANNOT-VERIFY>

<When QA cannot run at all because there is no local path to test, the pass is one line instead, with its reason:
"Verdict: SKIPPED: no local path, <reason>". A card whose last line is a skip closes as done only on an approver's yes
naming the card, which the close command asks for.>
