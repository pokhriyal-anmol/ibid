# Slice 2: score the deterministic baseline on the LeSICiN statute-identification benchmark

## Summary

Slice 1 showed the harness is reproducible on 45 items written in this repo. It gave no number comparable with anything outside it. This slice adds `ibid bench`, which loads a local, gitignored copy of the LeSICiN splits, turns each fact paragraph into a query with a fixed, versioned query rule (ADR 0004), retrieves IPC provisions with the existing index, rolls them up to section labels and scores micro F1, macro F1 and Jaccard with our own implementation. No model, embedding or label-derived weight is in the path.

What is built, by ticket (01 to 09 are done):

- 01: maps the 100 benchmark labels to IPC citations and checks each exists in the index, exiting non-zero on a missing or unparseable label.
- 02, 03: `ibid bench run` scores a split with query rule v1 under both a fixed top-k and a relative threshold r, with the section roll-up as a declared parameter. Results record data hashes, rule name and version, rule hash and parser version. Two identical runs are byte-identical.
- 04: per-label counts and scores, the never-found list, and strata by gold label count and by fact-paragraph length.
- 05: `--sample N` for fast iteration, marked in the results file and refused on the test split.
- 06: a committed manifest of pinned SHA-256 hashes. A changed byte in a data file is refused, naming the file, and no results file is written.
- 07: `ibid bench freeze` writes the frozen rule. The test split is scored only against a frozen rule and only once, keyed on the pinned test-file hash in a committed ledger. A second score needs `--rescore-test`, and both scores are then reported.
- 08: `ibid bench round` logs one single-knob optimisation round to `results/optimisation-log.json` with train, dev, strata and the train/dev gap, applies the saturation rule, flags overfitting and flags a `hurts-simple` round. Freeze reads this log, takes a logged round (default last) and refuses a `hurts-simple` round unless `owner_approved` is set.
- 09: `ibid bench report` shows round 0 beside the final scores read from the test ledger, the train/dev gap, the never-found list and a published-comparison table with caveats. It claims no rank.

Changes made while closing review findings:

- The frozen record now carries the round's rule version, hash and stop words, and the test run scores with them, so the ledger, results and report agree after a stop-word round.
- Dedup and quoting of terms are now part of the hashed rule parameters and are named in ADR 0004.
- The published 28.08 figure is labelled "m-F1 (micro or macro not confirmed)", since the source does not settle which it is.
- CONTEXT.md gains Benchmark label, Query rule, Optimisation round and Frozen rule.
- `check_params` is shared by `run_bench` and `optimise`, as are `load_space`, `load_cases`, `pinned_test_hash` and `read_ledger`. A redundant stem-based `--sample` check and a dead empty-cases fallback were removed from `run_bench`.

Contradictions with the spec and ADRs: none remain. The spec lists tokenisation, BM25 parameters and indexed levels as declared knobs, but `bench round` varies only stop words, k, r and the roll-up. This is now stated as deferred in the spec and ticket 08, and a round naming a deferred knob is refused. Ticket 10 (run the optimisation on the real data, freeze, score test once) is not started, so no benchmark number is reported here.

## Test plan

- [x] Full test suite: 107 tests ran, OK, in 30.587s.
- [x] Fixture runs match hand-computed micro F1, macro F1, Jaccard, per-label counts and strata.
- [x] Known-bad checks observed failing: corrupted labels lower the score, a changed rule changes the hash, a changed data byte is refused, a second test score is refused.
- [x] Mutation checks, each caught by a test: sample-on-test is refused (exit 1, stderr message, no ledger file written); report line "ledger rule matches ... NO"; hurts-simple freeze block through `ibid bench freeze` (refused with no frozen file, succeeds once `owner_approved`, unlogged round refused); the test split is never read by name.
- [x] Round-log entries match independent single runs with the same rule.
- [ ] Not run: the benchmark's own evaluation script. Metrics are our own implementation until it is read.
- [ ] Not run: the real-data optimisation and the single test scoring (ticket 10).

## Known issues

- BM25 parameters, tokenisation and indexed-levels knobs are still not variable by a round. They are documented as deferred in ticket 08 and the spec. A BM25 knob needs a custom FTS5 ranking function, which is a new feature.
- The report labels the last logged round as the "final round" rather than the frozen round. Freeze enforces the gate, and the report's "ledger rule matches the final logged round" line shows NO when a different round was frozen, but the label can still mislead when a non-last round is frozen.
