# Slice 14 v1 report

## Status

Built. All five tickets are done, none failed, none held back, and the tests pass. Every one of the seven user stories is covered by a done ticket. One gap is recorded rather than fixed: the six ILSIC-Multi scores were computed on a 540-label space, not the Lay-based 543 (see Your questions).

## What v1 does

`ibid ilsic eval` scores one layer on one ILSIC test split. The layer is either the frozen rule or an assoc-nb or linear-lr model file. It writes a results file with macro-F1, micro-F1, macro precision and recall, the label-space size, and the layer name, version and model hash. Each score comes in two readings. The primary reading is the paper's, over the full label space, where gold labels from other Acts count as misses. The secondary reading uses only labels the layer can predict and is reported in its own block.

A test ledger keeps the first score of each layer version on each test split. A second scoring is refused unless `--rescore-test` is passed. A model file of the wrong layer or version is refused.

Each report line has a bootstrap 95% interval and the paper's published numbers for the same split, with a plain statement of which numbers each layer is above or below. `results/ilsic-report.md` shows the frozen rule v2.11 plus assoc-nb v1, v2, v3 and linear-lr v1, v2 on both Lay and Multi. That is six rows per test set. Scoring needs no network and no model call beyond the layers' own offline predictions. The frozen rule sees the raw query only.

## How to run it

```bash
uv sync
export IBID_BNS_PDF=<root>/data/raw/bns-prs.pdf IBID_IPC_PDF=<root>/data/raw/ipc-wipo.pdf
uv run ibid ilsic eval --split <split-file> --train <Lay-train-file> --out <results-file> [--model <model-file> --layer <layer> --layer-version <version>] [--benchmark lay|multi] [--space-from <split>] [--ledger <ledger-file>] [--rescore-test]
uv run python -m unittest discover -s tests
```

The ILSIC data files are in `data/raw/ilsic/` of the main checkout. They are gitignored research data.

## Tests

The full unittest suite is green. Review fixed several weak tests and each new test was checked against known-bad input.

## What I assumed for you

- Q-001: The threshold output (sections scoring at least 0.7 of the top score) is scored for the frozen rule, recorded as `output_rule` in the results file.
- Q-002: The frozen rule's vocabulary for the secondary reading is the labels that parse as IPC sections and have a matching citation in the index.
- Q-003: Lay numbers are labelled Table 3 and Multi numbers Table 5.
- Q-004: Strictly greater counts as above a published number. A tie reads as below.
- Q-005: The Multi label space was built the way ticket 1 did it (Lay train plus the scored split's answers), giving 540 labels.

These five were settled by the build and review steps and are not in your queue. Q-006 and Q-007 below are.

## Held back

Nothing. All five tickets were built.

## Checks made after the build (2026-10-22, by the session, not by the workflow)

- Full suite: 336 tests, OK, with `__pycache__` cleared first.
- Independent recount of `assoc-nb v3` on the Lay test from the raw files: micro-F1 11.60 (tp 357, fp 3,823, fn 1,616) against the report's 11.91. The 0.31 gap is explained: `src/ibid/ilsic.py` (`_model`) drops a predicted section that is not in the label space before scoring, so it is never a false positive. It cannot change a verdict (every layer is far below every published number) but it favours the layer slightly and is not stated in the report. Open: document it, or score such predictions as false positives.
- Ceiling: 724 of the 1,973 gold labels in the Lay test (37%) are IPC sections, and 681 are inside `assoc-nb v3`'s vocabulary, so even a perfect IPC-only layer would reach about 51 micro-F1 on this test. The ILSIC label space spans many Acts; Ibid predicts the IPC only.
- The workflow also tightened `tests/test_linear.py` (its import check can now fail) and noted in the spec that the files give 543 labels where the paper says about 567.

## Result in one line

No layer clears any published ILSIC number under the primary reading, so goal G3 is not met: best micro-F1 is 14.1 (`assoc-nb v2`, Multi test) against 33.95 to 34.23 published, best macro-F1 is 1.2 against 14.8 to 17.0. The earlier 58% charge recall on set v2 was measured on 30 hand-picked multi-charge items with 2 to 3 IPC charges each and is not comparable.

## Your questions

2 pending, 0 blocking. That is below the batch size of 8, so none are asked yet and the work carries on without them.

- Q-006: Rescore the six Multi results on the Lay-based 543-label space (this spends a second test look), or keep the 540-label scores. The `--space-from` option exists for the rescore.
- Q-007: Which frozen-rule output rule is scored on ILSIC: threshold 0.7, top-k 5, or both. Default taken is the threshold.
