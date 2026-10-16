# `ibid charges compare` states the label-incompleteness and in-distribution caveats

Status: done
Blocked by: 03

What to build: in `src/ibid/compare.py` `_caveats`, two caveats generated from the inputs, never typed per run: (a) for any set whose label basis is `lawyer-answer-extracted`, a line that its labels are incomplete (the corpus's 5.46 against 2.40 statutes per query), so recall is meaningful and precision is not; (b) for a layer whose predictions carry `train_source: ilsic-lay` scored on a set whose items come from ILSIC-Lay, a line that the layer was fitted on posts from the same corpus and forum, so the score is in-distribution, while the test posts themselves were held out. Rows for `assoc-nb v1` and `assoc-nb v2` sort side by side with the baseline per set and Act, as rows already do.

User stories: 5.

Acceptance criteria (through `ibid charges compare` in `tests/test_charges_compare.py`, with invented results files):
- A v2 results file on an ILSIC-Lay set gets both caveats; the same layer on set v1 gets neither; v1 (`train_source: ilsi`) on set v2 gets only (a).
- Known-bad run, observed once: with (b) keyed on the layer name instead of `train_source`, the v1-on-set-v2 assertion fails.
- Running compare on the current committed results files reproduces `results/layer-comparison.md` except for the added caveat lines.
