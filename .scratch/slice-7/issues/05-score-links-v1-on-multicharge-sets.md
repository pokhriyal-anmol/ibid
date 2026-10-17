# Score `links v1` once per Multi-charge set and Act, and show it in the layer comparison

Status: done
Blocked by: 04

What to build: run `ibid charges export-baseline` and `ibid links expand` for Multi-charge sets v1 and v2, score each `links v1` file once per set and Act with `ibid charges score --predictions` (the existing scorer and its existing second-scoring refusal, slice 6), commit the predictions files under `results/layers/` and the results files under `results/`, and regenerate `results/layer-comparison.md` with `ibid charges compare` so the baseline and `links v1` sit side by side on sets v1 and v2 with mean predictions per item visible next to recall. If `charges compare` does not already show mean predictions per item in the per-charge table, add that column there.

User stories: 6, 7 (per-charge half), 9.

Acceptance criteria:
- A unittest through `ibid charges score --predictions` shows a second scoring of a `links v1` file on the same set and Act exits 1 and leaves the ledger and the out file byte-identical; another Act or set is accepted. Known-bad run, observed once, with the refusal bypassed.
- A unittest through `ibid charges compare` on fixture results files shows a mean-predictions-per-item figure for each layer row; known-bad run with the column removed fails on its assertion.
- `results/layer-comparison.md` shows baseline and `links v1` rows for sets v1 and v2, both Acts, both output rules.
- Every pre-existing file under `results/`, `gold/` and `concordance/` other than `layer-comparison.md` and the ledger is byte-identical; `results/baseline-v1.json` and `results/baseline-v2.json` regenerate byte-identically.
