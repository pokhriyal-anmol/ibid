# Score `links v1` on the ILSI test split, once, with the benchmark's micro-F1

Status: done
Blocked by: 02

What to build: `ibid links bench --split <ILSI split>` that runs the frozen rule's existing bench ranking (`bench.rank_sections` and `bench.predict` with the parameters recorded in `results/frozen-rule.json`, no change to either), expands each case's top-k and threshold predictions with the IPC links exactly as `links expand` does, and scores with the existing `bench.score` (micro-F1, macro-F1, Jaccard over the label vocabulary). On the pinned test split it records one entry in its own ledger (default `results/test-ledger-links.json`) and refuses a second scoring unless `--rescore-test` is passed, mirroring `assoc eval`. The results file records layer `links`, version `v1`, the split sha256, the frozen-rule hash and the link set's hash. Add the result to `results/layer-comparison.md` via `ibid charges compare --ilsi`, next to the baseline v2.11 test rows, with mean predictions per case.

User stories: 7 (ILSI half), 9. Spec Decision 5 (the micro-F1 condition).

Acceptance criteria:
- Unittest on a fixture split and fixture labels: expanded predictions are scored, originals are unchanged, and a second run on a split pinned as test exits 1 with the ledger byte-identical. Known-bad run, observed once, with the ledger check removed.
- Develop and debug only on the fixture and the dev split; the real test split is scored exactly once, after tickets 2 and 4 have landed and the code is final.
- `results/test-ledger.json`, `results/frozen-rule.json` and every existing ILSI result file are byte-identical.
- `layer-comparison.md` shows `links v1` test micro-F1 beside the baseline test rows for both output rules.
