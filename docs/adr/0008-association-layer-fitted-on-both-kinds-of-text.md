# 0008: The association layer may be fitted on both kinds of text

Status: accepted (owner, 2026-10-17, slice 9; decisions D-002 and D-003)

[ADR 0005](0005-learned-association-layer-is-opt-in.md) fixes the layer's training data as the ILSI `train` split. [ADR 0006](0006-association-layer-fitted-on-layperson-text.md) widens that to the ILSIC-Lay `train` split. `assoc-nb v1` suits judgment text and `assoc-nb v2` suits forum posts, and each fails on the other (set v2 IPC recall 39.3% for v1, set v1 IPC recall 15.3% for v2). The owner chose to train on both (D-003). This ADR widens the same data clause, "from which data", and nothing else.

**The new data.** `assoc-nb v3` is fitted once on the union of:
- the ILSI train split minus the 30 ids of set v1, and
- the ILSIC-Lay train split minus the 30 ids of set v2 and every post whose text equals a Layman test post (the ADR 0006 rule, unchanged).

Nothing from any test or dev split is trained on. The two sources' raw term counts and section counts are added. There is no weighting, resampling or tuning, even though judgment text is about 94 percent of the examples (ILSI 41574 of 44181 fitted). A lean toward judgments is a result to report. The vocabulary is the IPC offence sections found in at least 5 training examples of the union (IPC 34, 149 and 120B excluded, as before). The model file is `data/assoc-nb-v3.json`, gitignored like v2 because it carries the CC BY-NC-SA terms of the forum posts.

**What stands from ADR 0005 and 0006, unchanged.** The layer is opt-in and outside the Baseline path. No model call at run time. Tokenisation is that of [ADR 0004](0004-fixed-tokenisation-of-the-raw-query.md); smoothing and k = 5 are as before. The model file's SHA-256 is in every predictions file. The Act side comes only from verified Concordance entries. A layer version is scored once per set by `ibid charges score --predictions`.

**Decision rule, fixed before any score.** Per [D-002](../../.scratch/_owner/decisions.md), recall is compared per set and per Act, never pooled. Recall is in percent.

| # | Comparison | v3 must be |
|---|---|---|
| 1 | Set v1, IPC recall | above 15.3 (v2) |
| 2 | Set v1, BNS recall | above 16.3 (v2) |
| 3 | Set v2, IPC recall | at least 49.8 (v2's 54.8 minus 5) |
| 4 | Set v2, BNS recall | at least 59.2 (v2's 64.2 minus 5) |
| 5 | ILSI test micro-F1 | at least 33.4 (v1's 35.4 minus 2) |

The spec calls this a six-comparison rule, but its verbatim thresholds make five: two Acts on set v1, two on set v2, and one micro-F1. This ADR carries those five numbers and invents no sixth.

**Label space for comparison 5.** The micro-F1 is judged over v3's own label space, the procedure that produced v1's 35.4. The micro-F1 over v1's label space is computed in the same test run and recorded beside it, each labelled with its space's size. This default stands until the owner answers Q-005. A different answer changes only the verdict line, not the scoring.

**Outcome.** v3 is kept as an opt-in layer only if all five comparisons hold. Otherwise the result is recorded as negative, and v1 and v2 remain the two options.

**Outcome (2026-10-18).** Kept as an opt-in layer by owner waiver, not by passing every comparison under the strictest reading. On both multi-charge sets v3 beats the layer built for each (set v1 IPC 42.9 and BNS 39.8 against v2's 15.3 and 16.3; set v2 IPC 58.3 and BNS 65.4 against v2's 54.8 and 64.2). The ILSI test micro-F1 is 35.2 over v3's own 140-label space, which clears the 33.4 floor, and 33.3 over v1's 100-label space, which misses it by 0.1. The owner answered Q-005 by reporting both and keeping v3 as opt-in (D-005). Forum posts are 5.9 percent of the training examples (2,607 of 44,181), because 3,850 of the 6,465 posts cite no IPC offence section.
