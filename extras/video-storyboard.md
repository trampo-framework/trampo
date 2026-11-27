# Video storyboard

**Ready to record.** The video shows the lite setup on [Lite setup](../docs/wiki/Lite-setup.md), end to end. A real first run
tested that page on 2026-11-25, so every step shown is one a person has done. Nothing here is recorded yet. Times are targets for a video of 3 to 5 minutes, not measurements.

Record with a fictional team and a fictional card (`demo-1`), the slots left as stubs as the page says. Show no real
tracker, chat tool, code host or monitoring product, no real names, and no company's code.

| # | Time | Scene | What is on screen | What is said, in short |
| --- | --- | --- | --- | --- |
| 1 | 0:00 to 0:20 | What lite is | The top of [Lite setup](../docs/wiki/Lite-setup.md), "What you get, and what you do not" | The core, the card mode and runbooks. One person, one card, end to end |
| 2 | 0:20 to 0:40 | Install | A terminal running the four commands under "Set it up" | Three plugins, nothing else |
| 3 | 0:40 to 1:20 | Setup interview | `/trampo-core:setup` in an empty folder: lite chosen, then the three questions (name, repository folder, approver from git) | Three questions, one at a time. Everything else takes the full interview's recommended answers |
| 4 | 1:20 to 1:40 | Summary and agreement | The one summary, then the typed "Yes, go ahead with the setup.", then `/trampo-core:doctor` and `/trampo-runbooks:first-load` drafting the first runbooks | Nothing is built until you agree. The first runbooks are drafts read from code |
| 5 | 1:40 to 2:30 | First card | `/trampo-mode-card:card`, "run card demo-1", the card's text pasted, the intake (premise check, goal list, questions), the goal list confirmed, then slices. Beside it, the diagram in [Lite setup](../docs/wiki/Lite-setup.md), "Your first card" | Nothing is built on an unchecked premise |
| 6 | 2:30 to 2:50 | A close refused without PASS | A close as done tried before QA has passed, and the refusal message it prints | Done needs the last verdict line of the QA report to be `Verdict: PASS`. The check catches a forgotten step, not a dishonest one |
| 7 | 2:50 to 3:20 | QA report and PASS | `sessions/demo-1/qa-report.md` with its criteria table and the last line `Verdict: PASS` | An independent helper checks the card, not the one who built it |
| 8 | 3:20 to 3:50 | Close | The close-out: the memory entry or "no durable lesson" for each correction, the fact written into a file under `runbooks/systems/`, the `runbook:` line naming it, the commit | What was learned about the card goes to memory; what was learned about a system goes to its runbook |
| 9 | 3:50 to 4:10 | End card | The "Measured on the reference system" table in `README.md`, with its lead sentence | Measured on the workflow this was built from, one team, not on Trampo itself |

## Notes for whoever records it

- Before recording, run the whole page once for real and fix the page where it was wrong. Then record the same path.
- Scene 6 needs a card with no QA pass yet, or one whose last line is `Verdict: FAIL`. Do not stage a dishonest pass.
- Scene 3 shows all three questions; there is nothing to cut.
- Check every command against the docs at the version being recorded. This plan was checked against 0.4.9.

## Recording checklist

Before:

- [ ] A fresh Claude Code profile, so no account context leaks into suggestions.
- [ ] A clean demo repository with no real names, places or company code, and one open card (`demo-1`) with a small,
      real defect.
- [ ] An empty workspace folder whose name is the team name you want setup to suggest.
- [ ] Git user name set to a fictional person; it is shown as the approver.
- [ ] Terminal font large, a plain prompt, no paths that show a real user or machine name.
- [ ] Notifications off, other windows closed.
- [ ] Run the whole path once off camera at the version being recorded; fix the page where it differs.

During:

- [ ] Scenes 2 to 4 in one take, so the setup is seen to be continuous.
- [ ] Scene 6: try the close before QA has run, and keep the refusal message on screen long enough to read.
- [ ] Scene 7: QA by a separate helper, its `Verdict: PASS` line shown.
- [ ] Scene 8: show the `runbook:` line and the file it names.

After:

- [ ] Watch it once only for leaks: names, paths, account details, tool or vendor names.
- [ ] Cut waiting time; do not cut a refusal or a question.
- [ ] Record the version and date it was made with under the video.

