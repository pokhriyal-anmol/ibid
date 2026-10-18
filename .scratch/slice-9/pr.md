## Summary

Slice 9 adds `assoc-nb v3`, an association layer fitted once on both kinds of text. `assoc-nb v1` was fitted on ILSI judgments and recalled well on judgment text (set v1) but poorly on forum posts. `assoc-nb v2` was fitted on ILSIC-Lay forum posts and did the reverse. The owner chose to add judgment text to the training data (Q-002, option 2), and this slice measures whether one fit can serve both.

v3 uses the same method as v1 and v2 (term counts per section, naive-Bayes ranking, k=5, fixed tokenisation, no model call). Its training data is the ILSI train split minus the 30 set v1 ids, plus the ILSIC-Lay train split minus the 30 set v2 ids and the posts that duplicate a Layman test post. Raw counts are added with no weighting, resampling or tuning. The vocabulary is offence sections with at least 5 examples in the union (IPC 34, 149 and 120B excluded). The layer stays opt-in (ADR 0005). Retrieval is untouched, so ADR 0001 is not affected.

What was built, by ticket (all six have Status: done):

1. ADR 0008 widens the data clause of ADR 0005 and ADR 0006 to the union of both sources. This is a deliberate extension of those ADRs, not a contradiction. It fixes the decision rule before any score, and it names v3's own label space as the space for the micro-F1 comparison (Q-005 default, with the figure over v1's label space recorded beside it).
2. `ibid assoc fit` takes both training files and writes `data/assoc-nb-v3.json` (gitignored), with a header giving each source's hash, examples used and dropped, the section threshold and the vocabulary size. v1 and v2 fits are byte-identical to before.
3. `ibid assoc predict` reads the layer version and training source from the model header, so v3 predictions are no longer labelled `ilsi`. v3 is scored once per set and Act.
4. `ibid assoc eval` records the model's own version in the result and in `results/test-ledger-assoc.json`, and scores v3 once on the ILSI test split.
5. `results/layer-comparison.md` shows baseline, v1, v2 and v3. The only diff is one added assoc-nb v3 test row in the ILSI table.
6. `.scratch/slice-9/v3-report.md` applies the ADR 0008 rule from the results files and model header.

Result: the verdict is **kept**, and all five comparisons pass. On the ILSI test split, v3 micro-F1 is 35.2 in its own 140-label space and 33.3 in v1's 100-label space, against a floor of 33.4. The floor is judged over v3's own label space as ADR 0008 states, so the pass depends on that choice. Q-005 is the open owner question on this point, and over v1's label space the figure would fall just below the floor.

Notes for the reviewer:

- The spec calls the rule "six comparisons" but lists five (set v1 IPC and BNS, set v2 IPC and BNS, ILSI test micro-F1). The report and tests use the five.
- The judgment-text share of the fitted examples is 94 percent (ILSI 41574 of 44181), not the 87 percent first written. ADR 0008 and spec decision 3 are corrected. The decision rule is unchanged.
- The report script no longer has a "not yet decided" branch, and a missing ILSI test file now stops it with an error.
- Ticket file names for the ILSI result were aligned to `results/layers/assoc-nb-v3-test.json`.
- A `_vocab` helper in `src/ibid/assoc.py` removes duplicated vocabulary code. The refit v3 model is byte-identical to the one before the refactor.
- The label-incompleteness caveat for set v2 stands. No lawyer reviewed any label, and nothing here claims legal accuracy.

## Test plan

- [x] `uv run python -m unittest discover -s tests`: Ran 286 tests in 36.776s, OK.
- [x] Refit `data/assoc-nb-v3.json`; its sha256 matched the recorded hash.
- [x] `ibid assoc eval` run once on `data/raw/lesicin/test.jsonl`, giving one v3 ledger entry, with the v1 entry unchanged.
- [x] Micro-F1 test in `tests/test_assoc.py` asserts hand-derived values (8/19 in a 3-label space, 8/20 in a 6-label space).
- [x] `tests/test_adr_0008.py` parses the rule table and checks each threshold in its own row. Mutating the 15.3 row to 16.3 made it fail, and restoring it made it pass.
- [x] `results/layer-comparison.md` regenerated with `ibid charges compare`; the only diff is the added v3 test row.
- [x] `.scratch/slice-9/v3-report.md` regenerated; all five comparisons pass and the verdict is kept.
- [x] Refit v3 model is byte-identical before and after the `_vocab` refactor.
