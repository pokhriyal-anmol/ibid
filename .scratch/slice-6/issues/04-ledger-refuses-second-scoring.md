# `ibid charges score --predictions` refuses a second scoring of the same layer version on the same set and Act

Status: done
Blocked by: none

What to build: in `charges.score_predictions` (`src/ibid/charges.py`), before writing anything, look up the ledger for an entry with the same `layer`, `layer_version`, `set_sha256` and `act`. If one exists, print an error naming it and exit 1, writing neither the ledger nor the results file, unless `--rescore` is passed (new flag on `charges score`, mirroring `assoc eval --rescore-test`). A rescoring is appended to the ledger and listed under `scorings_of_this_layer_version`, as now. The frozen-rule path (`charges.score` without `--predictions`) is unchanged.

User stories: 4, 8 (baseline unchanged).

Acceptance criteria (through `ibid charges score` in `tests/test_charges_predictions.py` or `tests/test_charges_score.py`):
- A second `score --predictions` of the same layer version on the same set and Act exits 1, and the ledger and the out file are byte-identical to before the call.
- The same layer version on the other Act, or on another set, is accepted.
- `--rescore` scores again and the ledger then holds two entries.
- Known-bad run, observed once: with the check removed, the refusal test fails on its exit-code assertion.
- Existing tests that score the same predictions twice are updated to pass `--rescore` or use a fresh ledger; no other test changes. `results/baseline-v1.json` and `results/baseline-v2.json` regenerate byte-identically.
