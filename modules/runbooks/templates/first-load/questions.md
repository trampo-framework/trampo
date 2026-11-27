# Questions for a person

What reading did not settle. One row each. An answered row keeps its answer and who gave it, and the runbook it
changed is corrected in the same session. A question the session settled itself (from a README, by inference from
another answer, or by choosing) keeps its row, with the answer it took and `assumed, not asked` under By, so the
person sees it and can correct it.

| Q | System | Question | What was read | What an answer changes | Answer | By |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | orders-service | Where are refunds handled? | `orders-service@3f2a91c04b7e:app/` holds no refund handler | whether a refund flow is written here or in another system's runbook | | |
| Q2 | orders-service | Which port does it listen on? | the README says 8080 | the local run step | 8080, from the README | assumed, not asked |
