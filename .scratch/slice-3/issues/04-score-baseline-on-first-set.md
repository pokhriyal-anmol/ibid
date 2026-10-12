# Score the frozen baseline on the first 30 items, on the IPC and on the BNS

Status: done
Blocked by: 02, 03

What to build: run `ibid charges score` with the frozen rule v2.11 (`results/frozen-rule.json`) on `gold/multicharge/v1.json`, once per Act, and publish the results and a short report. This is the number every later layer in slice 3 must beat.

User stories: 4, 5, 7, 8.

Acceptance criteria:
- `results/multicharge-v1-ipc.json` and `results/multicharge-v1-bns.json` exist, each with the set hash, rule hash and index hash.
- `results/multicharge-report.md` shows, for each Act and each output rule: per-charge recall, all-charges-hit rate, the split by number of charges, mean predictions per item, and the list of missed charges with the top predicted sections.
- The report states the label basis counts and that no lawyer reviewed the labels, that the 30 items come from the ILSI train split which was used in aggregate for tuning, and that 30 items cannot separate rules that differ by a few points.
- Each Act was scored once. Any second scoring is reported beside the first.
- A note for the owner lists what the misses look like and which of them match the research note (definition against punishment section, long-section bias).
