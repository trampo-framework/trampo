# Verification method

How a result is checked before anyone is told it is verified, done, clean or fixed. The team adds a dated entry each
time a check that looked sound turned out not to be.

## Prove the method can see a dirty result before reporting a clean one (seed)

A check that cannot fail tells you nothing when it passes.

**How to apply:** before writing "no errors", "zero rows" or "not affected", run the same check on a case you know is
dirty and see it report that.

## Read the reporter's own evidence first, attachments included (seed)

The payload, the screenshot and the log line the reporter sent are the only first-hand evidence there is. A count is
not a payload.

**How to apply:** open what was sent before opening a terminal, and say which parts you could not read.

## Name the nearest competing explanation and run the one observation that separates them (seed)

A cause that fits the evidence is not yet the cause.

**How to apply:** before stating a cause to anyone, write the next most likely one and the single check whose result
differs between the two. Run it. Brief every helper to refute, never to confirm.

## A number is measured, derived or merely shown, and the sentence says which (seed)

A cumulative count read as a rate, a delivery time read as an event time and a denominator that is not what it is
called have each produced a wrong conclusion.

**How to apply:** next to every number put the command or query behind it and its unit. Say which columns or fields
you did not look at. Chase the number that does not reconcile: it is the thread to the mechanism or proof a claim is
wrong.

## Traced is not reproduced (seed)

A conclusion read from code is legitimate, and so is one from a reproduction. Presenting one as the other is not.

**How to apply:** say in the sentence whether the claim rests on a code trace, a measurement or a reproduction. In a
triage record every material claim is `PROVEN`, `REFUTED` or `OPEN` with what settled it; keep the refuted rows.

## Code is written test first (seed)

A test written after the code describes the code. A test written first can refute it.

**How to apply:** write the failing test, see it fail for the reason you expect, then make it pass, then tidy. For a
bug, reproduce it before proposing a fix.

## A finding needs a reachable trigger (seed)

A defect nobody can reach in normal use is a note, not a finding.

**How to apply:** report a finding only with the action, job or condition that sets it off. Without one it goes in a
"noted, not reported" list.

## Confidence matches evidence, and the check comes before the report (seed)

A confident line reads as "checked just now". A claim from a document, an earlier session or inference is none of
those.

**How to apply:** if a pushback would send you to verify, verify first. Mark a claim you did not re-check as
unverified, with where it came from. Re-run the cheapest check on the one inherited claim the work rests on.

## Write the prediction before the run (seed)

A prediction written after the result is a description, and it never refutes anything.

**How to apply:** before a run whose result you will interpret, write one sentence saying what passes, what fails and
what result would prove you wrong.
