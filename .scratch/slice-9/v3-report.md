# assoc-nb v3 against the ADR 0008 decision rule

| # | Comparison | Reference | v3 must be | v3 | Result |
|---|---|---|---|---|---|
| 1 | Set v1 (judgment text), IPC recall | v2 15.3 | above 15.3 | 42.9 | pass |
| 2 | Set v1 (judgment text), BNS recall | v2 16.3 | above 16.3 | 39.8 | pass |
| 3 | Set v2 (forum posts), IPC recall | v2 54.8 | at least 49.8 | 58.3 | pass |
| 4 | Set v2 (forum posts), BNS recall | v2 64.2 | at least 59.2 | 65.4 | pass |
| 5 | ILSI test micro-F1 | v1 35.4 | at least 33.4 | 35.2 | pass |

Verdict: **kept as opt-in, by owner waiver (D-005)**. All five comparisons hold in v3's own label space, but over v1's 100-label space the ILSI micro-F1 is 33.3, 0.1 below the 33.4 floor. The owner (Q-005, 2026-10-18) chose to report both and keep v3 as opt-in on the strength of its wins on both multi-charge sets. The pre-registered floor is not claimed as passed under the like-for-like reading.

ADR 0008 names five comparisons (the spec's "six" counts to five). Recall is in percent, per set and Act, never pooled.

Vocabulary: 140 IPC sections (at least 5 training examples).
Training examples fitted: ilsi 41574 (94.1%), ilsic-lay 2607 (5.9%), 44181 in all.

ILSI test micro-F1 by label space (one test run):
- own space, 140 labels: 35.2
- v1 space, 100 labels: 33.3
- reference v1 (its own space): 35.4

These are benchmark figures on labels that are incomplete for forum posts. No lawyer reviewed any label; nothing here is a claim of legal accuracy.
