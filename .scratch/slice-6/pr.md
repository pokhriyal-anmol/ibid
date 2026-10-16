## Summary

Slice 6 adds `assoc-nb v2`, a new version of the learned association layer. It uses the same method as v1 (term counts per section, naive-Bayes ranking, k=5, fixed tokenisation, no model call) but is fitted on the ILSIC-Lay train split (6,465 layperson forum posts) instead of ILSI judgment text. On set v2, v1 names only 19 of the 30 IPC sections cited and was trained on judgments, so it found 39.3% of IPC charges. The layer stays opt-in and out of the Baseline, as ADR 0005 requires.

What changed:

- ADR 0006 widens only the "from which data" clause of ADR 0005 to the ILSIC-Lay train split, records the CC BY-NC-SA 4.0 licence, and keeps the rest of ADR 0005. The fitted model, `data/assoc-nb-v2.json`, is gitignored.
- `ibid assoc fit` accepts an ILSIC-Lay file. Labels are IPC offence Citations from the `answer` field (34, 149 and 120B excluded; other Acts and index-absent Citations are counted and dropped). The vocabulary is sections with at least 5 train posts. Train posts whose text equals a Layman test split post are dropped, and the fit refuses if a set v2 source row is missing from the holdout file. The v1 fit is unchanged.
- `ibid assoc predict` takes the layer version and training source from the model header.
- `ibid charges score --predictions` refuses a second scoring of the same layer version on the same set and Act unless `--rescore` is passed.
- `ibid charges compare` adds two generated caveats: label incompleteness for sets with extracted lawyer-answer labels, and in-distribution fitting for a layer trained on the same corpus as the set.
- v2 was fitted and scored once per set and Act, and `results/layer-comparison.md` was regenerated. A report in `.scratch/slice-6/v2-report.md` covers vocabulary coverage and recall.

Result on set v2: the v2 vocabulary names 27 of 30 sections. IPC recall rises from 39.3% to 54.8%, but all of the gain is on charges whose section v1 could already name (49.3% to 68.7%). The 17 charges on sections v1 could not name are still all missed. MCP wiring stays a later slice. Forum labels are incomplete and no lawyer reviewed them, so this makes no claim of legal accuracy.

ADR note: ADR 0005 says no dev or test text is read by `fit`. v2's fit reads the Layman test split, but only to drop equal-text train posts, and trains on none of it. ADR 0006 was reworded to say this, so code and ADR now agree.

Review fixes in this branch: `assoc.py` now writes `index_absent_citations_dropped` to the header, and `compare.py` parses the set file once instead of three times.

## Test plan

- [x] `uv run python -m unittest discover -s tests`: Ran 234 tests in 33.225s, OK.
- [x] Each new test was run once against known-bad input (held-out post included in fit, wrong layer version, second scoring, caveat keyed on layer name, non-stdlib import).
- [x] Fit header reports 0 set v2 rows in training and counts each drop reason; model SHA-256 appears in all four predictions files.
- [x] One `assoc-nb v2` ledger entry per set and Act.
- [x] Baseline results, frozen rule, gold files and pinned concordance files byte-identical to before the slice.
- [x] Recall figures in the report recomputed by `.scratch/slice-6/v2-report.py` from the model headers and predictions files.
