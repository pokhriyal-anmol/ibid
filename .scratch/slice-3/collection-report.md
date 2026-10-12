# Collection report for gold/multicharge/v1.json (ticket 03)

Date: 2026-10-12. File: `gold/multicharge/v1.json`, pin `gold/multicharge/v1.sha256`.

## What the set is

30 items, 98 charges, drawn from the LeSICiN ILSI `train` split (Zenodo record 6053791, CC BY 4.0). Queries are the fact text exactly as released. Section labels, for the IPC and the BNS, were drafted by agents that saw only the fact text and the Act text, then each charge and section was challenged by a second agent that defaulted to refuting. No lawyer has reviewed them.

| | |
|---|---|
| items by benchmark offence-label group | 10 with 2, 10 with 3, 10 with 4 or more |
| items by surviving charges | 10 with 2, 20 with 3 or more |
| charges | 98 |
| distinct sections | 45 IPC, 42 BNS |
| query length, words | 160 to 600, median 355 |
| label basis | 30 of 30 `agent-drafted-skeptic-refuted` |

## How items were chosen

Rule fixed before any case text was read (`draft/selection.json`, rule sha256 `b2e58c72…`): train cases with at least two offence sections among the benchmark labels (IPC 34, 149 and 120B not counted), 150 to 600 words, then per group the cases whose SHA-256 of `id` sorts first.

After the first 30 candidates were labelled, 13 had lost every charge. The inclusion rule was then fixed as "at least 2 charges must survive the skeptic", before the next candidates were read, and each group walked its hash order until it held 10. 51 candidates were read in total: 16 lost every charge, 5 kept a single charge, 30 were included.

## Things a reader must know

- 28 of the 30 queries name sections outright ("registered under Sections 302/201"). The text is often a bail order or an FIR summary. Retrieval's tokeniser drops digits, so the numbers do not leak the answer, but the queries are not what a person with a fresh case types, and for many items the charges restate what the text names. Treat the score as how well text matching finds the charges a document states, not as a measure of reading bare facts.
- The ILSI facts were used in aggregate to tune the baseline (train split). Thirty items have a negligible effect on any tuned value, but the set is not an unseen sample in the strict sense.
- Agent labels share the blind spots of the model that drafted them. The skeptic reduces this and does not remove it. The BNS side was labelled from the BNS text with no second Act expert. A cross-check of all 50 distinct IPC to BNS pairings against my own knowledge of the correspondence found no pair I would call wrong, which is a weak check.
- 10 charges were dropped inside included items, and skeptics flagged 2 further charges the first reader missed. The missed ones are in `draft/assembly-report.json` and were not added.
- Agreement with the benchmark labels, computed after assembly and used for nothing: over the 30 items the agents' IPC sections matched 71 benchmark offence labels (IPC 34, 149 and 120B excluded), added 31 the benchmark does not list and missed 40 it does. That is 70 percent of the agents' sections present in the benchmark and 64 percent of the benchmark's offence labels covered, with all benchmark offence labels covered in 13 of 30 items. The benchmark labels come from sections cited in the judgment and the agents saw only the facts, so neither side is the truth. No label was changed because of this.
