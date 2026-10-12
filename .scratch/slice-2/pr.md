# Slice 2: score the deterministic baseline on the LeSICiN statute-identification benchmark

## Summary

Slice 1 showed the harness is reproducible on 45 items written in this repo. It gave no number comparable with anything outside it. This slice adds `ibid bench`, which loads a local, gitignored copy of the LeSICiN splits, turns each fact paragraph into a query with a fixed, versioned query rule (ADR 0004), retrieves IPC provisions with the existing index, rolls them up to section labels and scores micro F1, macro F1 and Jaccard with our own implementation. No model, embedding or label-derived weight is in the path.

What is built, by ticket (01 to 12 are done):

- 01: maps the 100 benchmark labels to IPC citations and checks each exists in the index, exiting non-zero on a missing or unparseable label.
- 02, 03: `ibid bench run` scores a split with query rule v1 under both a fixed top-k and a relative threshold r, with the section roll-up as a declared parameter. Results record data hashes, rule name and version, rule hash and parser version. Two identical runs are byte-identical.
- 04: per-label counts and scores, the never-found list, and strata by benchmark label count and by fact-paragraph length.
- 05: `--sample N` for fast iteration, marked in the results file and refused on the test split.
- 06: a committed manifest of pinned SHA-256 hashes. A changed byte in a data file is refused, naming the file, and no results file is written.
- 07: `ibid bench freeze` writes the frozen rule. The test split is scored only against a frozen rule and only once, keyed on the pinned test-file hash in a committed ledger. A second score needs `--rescore-test`, and both scores are then reported.
- 08: `ibid bench round` logs one single-knob optimisation round to `results/optimisation-log.json` with train, dev, strata and the train/dev gap, applies the saturation rule, flags overfitting and flags a `hurts-simple` round. Freeze reads this log, takes a logged round (default last) and refuses a `hurts-simple` round unless `owner_approved` is set.
- 09: `ibid bench report` shows round 0 beside the frozen round and the scores read from the test ledger, the train/dev gap, the never-found list and a published-comparison table with caveats. It claims no rank.
- 11: BM25 scoring moves into Python (`src/ibid/bm25.py`, standard library only) so `bm25_k1`, `bm25_b`, `stem` (a fixed suffix rule) and `levels` (all, top, leaf) are knobs a round can change. At the defaults it reproduces the FTS5 predictions, and on real data the 200-case dev sample gives micro 0.065667, macro 0.031081, Jaccard 0.039742, the same as FTS5. Full dev takes about 20 s and 5,000 train cases about 10 s.
- 12: the report headline and the provenance line name the frozen round, so a non-last round can be frozen without the report calling it a mismatch.

Changes made while closing review findings:

- The frozen record now carries the round's rule version, hash and stop words, and the test run scores with them, so the ledger, results and report agree after a stop-word round.
- Dedup and quoting of terms are now part of the hashed rule parameters and are named in ADR 0004.
- The published 28.08 figure is labelled "m-F1 (micro or macro not confirmed)", since the source does not settle which it is.
- The benchmark's "gold" wording is now "benchmark label" in code (`benchmark_labels`, stratum key `label_count`), matching the glossary.
- Ranking, prediction and scoring run through one path, `bench.evaluate_rule`, used by `run_bench` and `optimise`.
- BM25 corpus statistics span the IPC and BNS provisions in the index, as the FTS5 path did, while hits are restricted to IPC labels. This is a deliberate decision kept for FTS5 parity. Restricting them would change scores and needs a new rule version.
- CONTEXT.md gains Benchmark label, Query rule, Optimisation round and Frozen rule.
- `check_params` is shared by `run_bench` and `optimise`, as are `load_space`, `load_cases`, `pinned_test_hash` and `read_ledger`. A redundant stem-based `--sample` check and a dead empty-cases fallback were removed from `run_bench`.

Contradictions with the spec and ADRs: none remain. Tokenisation, BM25 parameters and indexed levels are built as knobs by ticket 11. Ticket 10 ran on 2026-10-12: see Results.

## Test plan

- [x] Full test suite: 121 tests ran, OK, in 30.002s.
- [x] Fixture runs match hand-computed micro F1, macro F1, Jaccard, per-label counts and strata.
- [x] Known-bad checks observed failing: corrupted labels lower the score, a changed rule changes the hash, a changed data byte is refused, a second test score is refused.
- [x] Mutation checks, each caught by a test: sample-on-test is refused (exit 1, stderr message, no ledger file written); report line "ledger rule matches ... NO"; hurts-simple freeze block through `ibid bench freeze` (refused with no frozen file, succeeds once `owner_approved`, unlogged round refused); the test split is never read by name.
- [x] Round-log entries match independent single runs with the same rule.
- [x] BM25 equivalence, k1, b and levels tests drive `ibid bench run` only. Known-bad mutations of the CLI default b, default k1 and levels were each observed failing.
- [x] Stem tests go through `bench run --stem suffix`, one case per rule (-ed, -ing, doubled consonant, -ies, -s, indexed-side stemming, the -ss exception). Known-bad mutations observed failing.
- [x] Report ledger check says "ledger rule matches the frozen round (N)", with a non-last frozen round case and an edited-ledger known-bad case.
- [x] Real data: dev `--sample 200` matches FTS5 exactly (micro 0.065667, macro 0.031081, Jaccard 0.039742).
- [ ] Not run: the benchmark's own evaluation script. Metrics are our own implementation until it is read.
- [x] Real-data optimisation (rounds 0 to 11), one frozen rule and one test scoring. See Results.

## Results (ticket 10, 2026-10-12)

Rule `query-rule v2.11`: k=5, r=0.7, BM25 k1=4.0, b=1.0, max roll-up, no stemming, all levels. Test split scored once, 13,039 cases, against the frozen rule committed first (42e8a67).

| output | micro-F1 | macro-F1 | Jaccard |
|---|---|---|---|
| threshold, test | 9.64 | 6.21 | 5.52 |
| top-k, test | 9.37 | 6.07 | 5.43 |
| threshold, dev | 9.71 | 6.22 | 5.62 |
| round 0 (k=3, r=0.8), dev | 6.37 | 3.66 | 4.45 |

The published scores are 28.08 and 28.45 from trained classifiers, so Ibid's deterministic text matching is about a fifth of those on macro-F1. This is not a comparison like for like (see the caveats in `results/report.md`).

- **Protocol.** Saturation fired at round 8. The owner extended the protocol with a 3-round settle phase on r (rounds 9 to 11). Round 11 is the best unflagged round on train. Every round from 1 to 8 was flagged `hurts-simple` because lowering r cut single-label cases.
- **Overfit check.** Train minus dev macro-F1 is about -0.2 points in every round, and test is within 0.1 point of dev: no overfitting to dev.
- **Section 34.** The spec expected a miss. Recall on test is 0.30 (1,107 of 3,734 cases), F1 0.32, one of the best labels.
- **Murder.** IPC 302 is found in 4 of 3,246 cases. The query matches the definition (IPC 300), not the punishment section.
- **IPC 376.** Predicted on about three quarters of cases (8,756 false positives), a length effect of the b and k1 settings. Per-label results on test were read after scoring and must not steer further tuning.
- **Metric cross-check.** Could not run. The benchmark's evaluation script is on OneDrive and was not read, so the metrics are our own implementation of micro and macro F1 and Jaccard.
- **Guard history.** The first `hurts-simple` guard read only top-k and only the previous round, and missed a 3.8 point fall. It was fixed after round 3 and rounds 0 to 3 were regenerated. The stopping metric was changed from top-k to the better of the two rules after round 2. Both changes are dated in the spec.
- **Literature.** [docs/research/legal-retrieval-literature.md](../../docs/research/legal-retrieval-literature.md) checks the published comparison against NyayGraph, which uses the same split: an untuned Llama 3.1 8B scores micro-F1 7.2 and macro-F1 4.8 there, below Ibid's 9.6 and 6.2. The report carries those rows. The note lists candidate next steps and marks which claims were not checked.
