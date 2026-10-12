# One scorer for every layer: score a predictions file

Status: done
Blocked by: 02

What to build: `ibid charges score --set <file> --predictions <file> --act ipc|bns --out <results.json>`, which scores any layer's predictions file with exactly the figures `ibid charges score --frozen-rule` produces today, and a way to export the baseline in the same format so there is one scoring path.

Predictions file (also documented in `spec.md`): `{"layer": str, "layer_version": str, "set_sha256": str, "inputs": {name: sha256}, "items": {item id: {"ipc": [citations], "bns": [citations]}}}`. Order is not scored.

Parts:

- `--predictions` is accepted by `charges score` as an alternative to `--frozen-rule`. `set_sha256` must equal the set file's hash, every item id must be in the set, every citation must exist in the index and belong to its list's Act, and a missing item counts as no predictions. Any violation exits non-zero and names the item and field, and no results file is written.
- `ibid charges export-baseline --set <file> --index <index> --frozen-rule <file> --out <predictions.json>` writes the baseline's predictions (both output rules as two layers: `baseline-topk` and `baseline-threshold`, each with the rule version) so the frozen-rule path and the predictions path give identical scores. The old `--frozen-rule` option may stay and must call the same scoring function.
- The ledger beside the set is keyed by layer and layer version and set hash. A second scoring of the same layer version on the same set is written and reported beside the first.

User stories: 4, 6, 7, 8.

Acceptance criteria (invented fixture set and fixture index):
- Scores from `--predictions` equal hand-computed values for both Acts.
- Known-bad: a predictions file for another set hash, an unknown item id, a citation not in the index, an IPC citation in the `bns` list, and a missing `layer` are each refused, naming the field.
- A baseline exported and scored through `--predictions` equals the result of `--frozen-rule` on the same fixture (same recall, all-charges-hit, mean predictions and strata), checked once for each output rule.
- Two identical runs are byte-identical.
- On the real data, the exported baseline reproduces `results/multicharge-v1-ipc.json` and `results/multicharge-v1-bns.json` figures exactly (3 and 5 of 98 on the IPC, 4 and 5 of 98 on the BNS). The orchestrator runs this after the merge.
- A second scoring of one layer version is shown beside the first in the results file.
