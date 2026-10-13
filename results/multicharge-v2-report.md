# Multi-charge set v2 (layperson forum posts) and concordance v3

Date: 2026-10-13. Set: `gold/multicharge/v2.json` (sha256 `9b4c14c5…`). Concordance: `concordance/v3.json` (sha256 in `concordance/v3.sha256`). Rule: `query-rule v2.11`. Each layer was scored once on this set.

## What the set is

30 posts written by real laypeople on a legal forum, published in ILSIC-Lay (EACL Findings 2026, CC BY-NC-SA 4.0, non-commercial use only). 84 charges, each an IPC section cited in the forum lawyers' replies, extracted by the corpus authors with a language model and regular expressions. 81 of the 84 have a BNS counterpart in concordance v3.

The selection rule was fixed before any post was read (`.scratch/slice-3/draft/ilsic-selection.json`): test split only, at least two distinct IPC offence sections, 40 to 250 words, no section number in the text, then the 30 smallest SHA-256 values. 29 of the 30 queries in set v1 name a section, and none in set v2 does, so this set measures reading a story.

**Label limitation.** The corpus authors found 5.46 statutes per query from a law graduate on 50 queries against 2.40 in the data. The labels are incomplete. Recall against them is meaningful. Precision and the all-charges-found rate are lower bounds and should not be read as a quality measure of a layer. No lawyer reviewed these labels.

**Privacy.** The scrub removes emails, URLs, runs of 7 or more digits, titled names, `Name:` labels and IFSC codes. Untitled names, places and company names can remain, so the set stays in the private repository.

## Result

Per-charge recall, a charge found when any accepted section of the Act is predicted.

| Layer | IPC recall | BNS recall | Mean predictions per item |
|---|---|---|---|
| baseline v2.11 top-k (k=5) | 4 of 84 (4.8%) | 8 of 81 (9.9%) | 5.0 |
| baseline v2.11 threshold (r=0.7) | 5 of 84 (6.0%) | 5 of 81 (6.2%) | 6.1 to 6.4 |
| A, cited sections | 0 of 84 | 0 of 81 | 0 |
| B, association (naive Bayes, fitted on ILSI) | 33 of 84 (39.3%) | 39 of 81 (48.1%) | 5.0 |
| C, agent sub-queries then baseline | 21 of 84 (25.0%) | 33 of 81 (40.7%) | 3.0 |

Reading it:

- Route A returns nothing because the selection rule removed every cited section. This confirms the extractor does only what it says, and that on set v1 its 88% IPC recall came from the queries naming sections.
- Route B is the strongest on recall. The model was fitted on ILSI court-judgment data and the labels here come from the same corpus family and the same extraction method, so B's score is flattered by label-style agreement and should not be generalised to other forum text.
- Route C is below B and above the baseline. Its sub-queries come from a model and carry that model's legal knowledge, as recorded in `gold/multicharge/v2.subqueries.json`.
- The baseline sits at about 5% on both sets, so the finding from set v1 holds on person-written text.

## Concordance v3 and the BNS side

Source: the CAPT Bhopal correspondence table (June 2024), one director's compilation and not an MHA publication. 529 rows parsed, all 358 BNS sections covered. Candidates were checked against the index (every cited provision exists, and the two sides share a distinctive word), then every served candidate was challenged by an independent skeptic pass against the raw table lines. 4 of 350 were refuted (IPC cells written with `/` separators) and dropped. 348 entries are served, against 12 in v2.

Set v1 re-run with v3, once each, through the same layers:

| Layer | BNS recall with v2 | BNS recall with v3 | IPC recall (unchanged) |
|---|---|---|---|
| A, cited | 0.0% | 82.7% | 87.8% |
| B, association | 0.0% | 37.8% | 41.8% |

The IPC figures did not move, so the BNS change is a change in coverage and not in either layer. The re-runs are in `results/multicharge-v1-*-concv3.json`. The main comparison table in `layer-comparison.md` still shows the v1 rows with concordance v2.

Limits. The table's own errors, if any, are inherited. The skeptic pass confirms agreement with the table's text, not with the law. Entries typed `merged` with many IPC sections (for example BNS 316 for IPC 405 to 409) let any one IPC section count as a hit for the BNS section, which is the intended roll-up and also the generous one.
