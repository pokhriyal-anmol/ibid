## Summary

Ibid had scored only a 30-item subset of the ILSIC-Lay test, so it had no standing on the published ILSIC benchmark (EACL 2026, arXiv 2602.00881). This slice adds `ibid ilsic eval`, which scores any layer on the full ILSIC-Lay test (836 queries) and ILSIC-Multi test (757 queries) and puts the paper's numbers beside ours.

What changed:

- `ibid ilsic eval` (`src/ibid/ilsic.py`, wired in `src/ibid/cli.py`) scores the frozen rule v2.11 or an `assoc-nb` or `linear-lr` model file on the raw query only, so ADR 0001 and ADR 0005 hold. It refuses a model file whose header names a different layer or version. Nothing is refit.
- The primary reading is the paper's: the label space is every statute string in the Lay train and test answers (543 labels by our count, against about 567 in the paper; the gap is unexplained). Macro-F1 averages over the whole space with 0 for a label that has no gold and no prediction. A gold label no layer can predict, such as one from another Act, counts as a miss. The secondary reading, over the labels the layer can predict, is reported in a separate block and never substituted. The zero-label assumption is ours, because the paper does not state its treatment, and is stated on every report.
- `results/test-ledger-ilsic.json` allows one look per layer version and split, keyed by the split file hash. A second scoring is refused unless `--rescore-test` is passed, and the first entry stays visible.
- Each score carries a 1,000-resample bootstrap 95% interval (seed 0). Published baselines live in one constant with their table numbers (Tables 3 and 5), are labelled "published, not re-run by us", and the verdict against each uses the primary reading only.
- `--space-from` adds a split's answers to the label space, for example the Lay test when scoring Multi.
- `results/ilsic-report.md` shows the frozen rule, `assoc-nb` v1 to v3 and `linear-lr` v1 and v2 on both tests. It also notes that the Multi test overlaps the Lay test in queries, so the two are not independent evidence, and carries the CC BY-NC-SA 4.0 and no-legal-accuracy caveat. No ILSIC data or model file is committed.
- ADR 0009 is amended to name `ibid ilsic eval` as a second scorer with its own ledger, and to record `linear-lr v2` (fitted on the original ILSI text, same licence). This extends ADR 0009 rather than contradicting it. No ADR is contradicted.

Under the primary reading every layer is below every published number on both tests. On the Lay test micro-F1 runs from 2.74 (frozen rule) to 12.70 (`linear-lr v1`) against 34.23 published.

Tickets 01 to 05 are all done.

## Test plan

- [x] Full suite: `uv run python -m unittest discover -s tests` ran 336 tests in 43.947s, OK.
- [x] Fixture tests through the `ibid ilsic eval` command check both readings against hand-computed values, including a gold label from another Act and a label with no gold.
- [x] Each new check was run once against known-bad input and seen to fail: an other-Act label dropped from the space, a no-gold label counted as 1, a second scoring accepted, a model file of another version accepted, the verdict switched to the secondary reading, and a report with "zero-label" removed.
- [x] A behaviour test spies on the retrieval and the mocked model and asserts both received the exact raw query (odd casing and whitespace).
- [x] The import allow-list tests for `linear` and `assoc` (standard library and `ibid` only) include a known-bad case (`import numpy`).
- [x] The report test derives expected ledger entries from `results/ilsic-*-*.json` and checks the report holds each result file's primary micro-F1.
- [x] Ledger holds one entry per (layer, version, split), no `--rescore-test` used.
- [x] Byte-identity: against base commit 5d487ad (the commit before slice 14; comparing with main shows `test-ledger-assoc.json` differing, which comes from slice 13), the check printed "no DIFF over 119 files". The sha256 table for `gold/v2.json`, `concordance/v2.json`, the frozen-rule record and baseline-v2 is in the report.

## Known issues

- The six committed Multi scores used a 540-label space, not the Lay-based space. `--space-from` now exists, but re-scoring needs `--rescore-test`, a changed ledger and a rewritten report, and the data and model files are outside the repo. The gap is recorded in the spec (decision 2) and the report. The owner decides: rescore, or keep the Multi-only reading and report both.
- The 543 versus about 567 label-count gap against the paper is unexplained.
