# Card proof comment

The one comment put on a card before it is offered for release, filled from the evidence in `sessions/<card>/`. A
person reviews and merges.

## How to fill it

- The four headings below are fixed and in this order. A section with nothing to say says `none` and why.
- Product words, not a change description: paths, function names and build numbers stay in the session record.
- One row in the Proof table per acceptance criterion or scenario. The table carries the length; the text stays short.
- Every claim has its evidence beside it (a log line, a count, a commit id, a picture). A claim with none is left out,
  or listed under Not proven with the reason.
- When the card changes anything a person sees, Proof shows each changed screen, before and after where a before
  exists. A card with no visible change says `No interface change.`
- Not proven is never shortened to save space.
- No email address, account number or secret. Say pass or fail with counts; the reviewer decides. Never call the card
  done or ready to merge: say it waits for a person.

## Template

    **<card>: <what now works, in product words, and where it was proven>**

    ### What changed
    <two or three lines>

    ### Proof
    | Check | Before | With the change | Evidence |
    | --- | --- | --- | --- |

    ### Not proven
    <what could not be shown and why, or "none">

    ### What a person must do
    - Review and merge: <reference>. Merging <is | is not> the production release (<what the pipeline does on merge>).
    - <any manual step after the merge, or "none">
