# Label audit of set v1

Date: 2026-10-13. Set: `gold/multicharge/v1.json` (sha256 `9b77ae21…`, unchanged).

This audit is a stand-in for a lawyer's review as far as published sources and independent annotators can go. **It is not a lawyer review.** The labels keep their basis `agent-drafted-skeptic-refuted`, and a lawyer is still needed before any score is published.

## Method and caveats

- Panel: three agents, each with a different role prompt (defence lawyer, prosecutor, examiner), each reading only the query text and writing its own charges and IPC sections. They saw no first-pass labels, no benchmark labels and no retrieval output. Prompts are in `.scratch/slice-3/draft/panel-prompts.txt`.
- The panel agents are models with the same legal knowledge as the first-pass drafters. Agreement between them is evidence of consistency, not of correctness. 29 of the 30 queries name section numbers in their text, so the panel often had the answer in front of it; that makes confirmation easier than it would be on a bare story.
- Table: the CAPT correspondence table, a person's compilation and not an MHA publication.

## Results

| Check | Result |
|---|---|
| Charges confirmed by at least 2 of 3 panel agents | 96 of 98 (98.0%) |
| Mean pairwise Cohen's kappa over the (item, section) sets | 0.89 (pairs: 0.95, 0.87, 0.86) over 1650 cells (30 items x 55 candidate sections) |
| Candidate missing charges (listed by 2 or more agents, absent from v1) | 23 |
| BNS pairs against the table, charge level | 97 agree, 0 differ, 1 not covered |
| Benchmark labels, signal only | 71 of the set's offence sections are also benchmark labels; 31 are not; 40 benchmark labels are not in the set |

## Per item: charges confirmed

- 43946072: 2 of 2
- 153470110: 2 of 2
- 871051: 2 of 2
- 107892742: 3 of 3
- 105616635: 3 of 3
- 190108901: 6 of 6
- 176417778: 4 of 4
- 156132986: 4 of 4
- 155317536: 2 of 2
- 39883671: 2 of 2
- 154394117: 3 of 3
- 1733568: 3 of 3
- 71898306: 3 of 3
- 102242151: 4 of 4
- 1422198: 2 of 2
- 33467557: 4 of 4
- 40330300: 2 of 2
- 188477105: 2 of 2
- 21756622: 1 of 2
- 24605614: 4 of 4
- 1781247: 4 of 4
- 106805320: 3 of 3
- 44267882: 2 of 3
- 53071757: 2 of 2
- 43861037: 4 of 4
- 127532648: 3 of 3
- 102368932: 6 of 6
- 150846258: 5 of 5
- 19706913: 5 of 5
- 41590279: 4 of 4

## Charges not confirmed by two of three

- item 21756622, Voluntarily causing hurt (323): 1 of 3 agents
- item 44267882, Rioting (147): 1 of 3 agents

## Candidate missing charges (listed, not added)

- item 190108901: IPC 342 (2 of 3 agents)
- item 39883671: IPC 341 (2 of 3 agents)
- item 154394117: IPC 506 (3 of 3 agents)
- item 40330300: IPC 326 (3 of 3 agents)
- item 188477105: IPC 326 (2 of 3 agents)
- item 21756622: IPC 354 (3 of 3 agents)
- item 21756622: IPC 363 (3 of 3 agents)
- item 21756622: IPC 506 (3 of 3 agents)
- item 24605614: IPC 504 (2 of 3 agents)
- item 1781247: IPC 148 (3 of 3 agents)
- item 1781247: IPC 325 (2 of 3 agents)
- item 106805320: IPC 294 (3 of 3 agents)
- item 106805320: IPC 452 (2 of 3 agents)
- item 106805320: IPC 456 (3 of 3 agents)
- item 106805320: IPC 506 (3 of 3 agents)
- item 44267882: IPC 148 (3 of 3 agents)
- item 44267882: IPC 294 (3 of 3 agents)
- item 44267882: IPC 427 (3 of 3 agents)
- item 44267882: IPC 458 (3 of 3 agents)
- item 53071757: IPC 467 (3 of 3 agents)
- item 53071757: IPC 468 (3 of 3 agents)
- item 53071757: IPC 471 (3 of 3 agents)
- item 127532648: IPC 325 (3 of 3 agents)

## BNS pairs the table maps differently or does not cover

- item 71898306, Being member of unlawful assembly: labelled BNS 189 for IPC 143; table gives no row (uncovered)

## Notes

- Kappa is computed over every (item, section) cell for every section any panel agent or the first pass named, so most cells are agreed zeros. That raises kappa against a table of only the positive cells. Read it with the 96 of 98 confirmation figure, and as consistency among models.
- Benchmark signal: the figures (71 shared, 31 added by the set, 40 benchmark labels absent) reproduce the collection report's, which is a check that this script reads the same labels. The benchmark labels are the sections cited in the judgment, so neither side is the truth.
- The single uncovered BNS pair is IPC 143 (punishment for unlawful assembly) labelled BNS 189. The table's rows for BNS 189 list IPC 141, 142, 145, 144, 151, 150, 157 and 158 and omit 143, so the table is silent on it, not contradicting.
- The panel flagged 23 candidate charges the first pass left out, mostly criminal intimidation (506), kidnapping, grievous hurt (325, 326) and rioting-adjacent sections (148). They are listed, not added. Whether the text alleges them is a question for a lawyer.

- A charge counts as agreeing with the table when the labelled BNS sections are contained in, or contain, the table's BNS sections for the charge's IPC sections.
- Panel members that returned no entry for an item: 0.
- Nothing in v1 was edited. `gold/multicharge/v1.1.json` carries the same items plus a `review` object recording these counts.
