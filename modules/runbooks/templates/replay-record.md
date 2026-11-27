# Replay: <flow title>, <first|second|...> replay

Flow: `runbooks/flows/<flow>.md`
Verdict: <PASS as written | PASS as written, prose corrected | DIFFERS at <step> | FAIL at <step> | BLOCKED at <step>>

<One paragraph: which steps passed as written and the one fact that proves the end state.> Run <start> to <end>, on
<the test environment>, from the flow file and the files it names. No earlier record and no flow history was read.
<Any refusal, quoted; else "Nothing was refused.">

## Records this replay created

Ids only.

## Steps

| Step | Result | Seen |
| --- | --- | --- |
| <n> <name> | PASS / DIFFERS / BLOCKED / NOT RUN | <the count, status or address that proves it> |

## Flow edits

<Each edit the evidence supports: the step, the part it touches (command, input, Expect, order, or a note outside
the steps), the old and the new text. "None" when there were none.>

## Findings

<Defects and notes outside the flow, described, not fixed, each with its source.>

## Not run

<Each step not run, and the line of the brief or the flow that says why.>

## Can the flow be marked verified?

<One word, then: each step not passed as written, each `_(verify)_` settled, and what the next replay needs.>

## Side effects on the test environment

<Every record created, changed or left, by id. Every session and temporary folder closed or removed.>
