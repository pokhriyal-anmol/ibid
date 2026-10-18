# assoc-nb v3 against the ADR 0008 decision rule

| # | Comparison | Reference | v3 must be | v3 | Result |
|---|---|---|---|---|---|
| 1 | Set v1 (judgment text), IPC recall | v2 15.3 | above 15.3 | 42.9 | pass |
| 2 | Set v1 (judgment text), BNS recall | v2 16.3 | above 16.3 | 39.8 | pass |
| 3 | Set v2 (forum posts), IPC recall | v2 54.8 | at least 49.8 | 58.3 | pass |
| 4 | Set v2 (forum posts), BNS recall | v2 64.2 | at least 59.2 | 65.4 | pass |
| 5 | ILSI test micro-F1 | v1 35.4 | at least 33.4 | not scored | fail |

Verdict: **not yet decided**. The four recall comparisons hold; the ILSI test split has not been scored for v3.

ADR 0008 names five comparisons (the spec's "six" counts to five). Recall is in percent, per set and Act, never pooled.

Vocabulary: 140 IPC sections (at least 5 training examples).
Training examples fitted: ilsi 41574 (94.1%), ilsic-lay 2607 (5.9%), 44181 in all.

These are benchmark figures on labels that are incomplete for forum posts. No lawyer reviewed any label; nothing here is a claim of legal accuracy.
