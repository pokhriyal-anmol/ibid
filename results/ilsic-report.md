# ILSIC full scoring report (slice 14)

Every layer is scored once per test split, none refit, with `ibid ilsic eval`. Raw results: `results/ilsic-<split>-<layer>.json`; ledger: `results/test-ledger-ilsic.json` (one entry per layer, version and split).

Scores are in percent. Published numbers are copied from the ILSIC paper (arXiv 2602.00881) with their table numbers and were not re-run by us.

## FT-Layman-test (ILSIC-Lay, 836 queries)

Published best, Table 3: macro-F1 14.83 and micro-F1 34.23 (GPT-4.1 two-shot), micro-F1 33.19 (fine-tuned Gemma-3).

### Primary reading (paper's label space, 543 labels)

| Layer | Macro-F1 [95% interval] | Micro-F1 [95% interval] | Macro P | Macro R | Verdict against published |
|---|---|---|---|---|---|
| frozen-rule | 0.67 [0.42, 0.87] | 2.74 [2.08, 3.48] | 0.67 | 2.74 | macro 0.67: below 14.83; micro 2.74: below 34.23; micro 2.74: below 33.19 |
| assoc-nb v1 | 0.66 [0.30, 0.82] | 9.51 [8.33, 10.78] | 0.55 | 1.98 | macro 0.66: below 14.83; micro 9.51: below 34.23; micro 9.51: below 33.19 |
| assoc-nb v2 | 0.62 [0.35, 0.76] | 12.68 [11.34, 13.93] | 0.51 | 1.63 | macro 0.62: below 14.83; micro 12.68: below 34.23; micro 12.68: below 33.19 |
| assoc-nb v3 | 0.67 [0.35, 0.87] | 11.91 [10.64, 13.26] | 0.51 | 2.07 | macro 0.67: below 14.83; micro 11.91: below 34.23; micro 11.91: below 33.19 |
| linear-lr v1 | 1.17 [0.77, 1.39] | 12.70 [11.21, 14.45] | 1.14 | 2.22 | macro 1.17: below 14.83; micro 12.70: below 34.23; micro 12.70: below 33.19 |
| linear-lr v2 | 0.96 [0.68, 1.14] | 11.32 [9.85, 12.86] | 0.90 | 1.54 | macro 0.96: below 14.83; micro 11.32: below 34.23; micro 11.32: below 33.19 |

### Secondary reading (labels the layer can predict; never substituted for the primary)

| Layer | Labels | Macro-F1 | Micro-F1 |
|---|---|---|---|
| frozen-rule | 119 | 3.07 | 3.52 |
| assoc-nb v1 | 63 | 5.65 | 12.42 |
| assoc-nb v2 | 96 | 3.52 | 16.11 |
| assoc-nb v3 | 103 | 3.51 | 15.19 |
| linear-lr v1 | 63 | 10.12 | 19.01 |
| linear-lr v2 | 63 | 8.30 | 18.03 |

## FT-LMsub-test (ILSIC-Multi, 757 queries)

Published best, Table 5: macro-F1 17.01 and micro-F1 33.95 (GPT-4.1 zero-shot).

### Primary reading (paper's label space, 540 labels)

| Layer | Macro-F1 [95% interval] | Micro-F1 [95% interval] | Macro P | Macro R | Verdict against published |
|---|---|---|---|---|---|
| frozen-rule | 0.68 [0.42, 0.88] | 2.94 [2.22, 3.70] | 0.72 | 2.57 | macro 0.68: below 17.01; micro 2.94: below 33.95 |
| assoc-nb v1 | 0.68 [0.33, 0.87] | 10.57 [9.23, 11.92] | 0.57 | 1.99 | macro 0.68: below 17.01; micro 10.57: below 33.95 |
| assoc-nb v2 | 0.65 [0.38, 0.79] | 14.13 [12.66, 15.57] | 0.53 | 1.64 | macro 0.65: below 17.01; micro 14.13: below 33.95 |
| assoc-nb v3 | 0.70 [0.39, 0.91] | 13.27 [11.76, 14.70] | 0.54 | 2.08 | macro 0.70: below 17.01; micro 13.27: below 33.95 |
| linear-lr v1 | 1.22 [0.83, 1.43] | 14.08 [12.40, 15.78] | 1.18 | 2.23 | macro 1.22: below 17.01; micro 14.08: below 33.95 |
| linear-lr v2 | 1.01 [0.70, 1.19] | 12.57 [10.94, 14.23] | 0.97 | 1.55 | macro 1.01: below 17.01; micro 12.57: below 33.95 |

### Secondary reading (labels the layer can predict; never substituted for the primary)

| Layer | Labels | Macro-F1 | Micro-F1 |
|---|---|---|---|
| frozen-rule | 119 | 3.10 | 3.68 |
| assoc-nb v1 | 63 | 5.86 | 13.49 |
| assoc-nb v2 | 96 | 3.68 | 17.54 |
| assoc-nb v3 | 103 | 3.66 | 16.52 |
| linear-lr v1 | 63 | 10.43 | 20.26 |
| linear-lr v2 | 63 | 8.70 | 19.13 |

## Notes

- Zero-label assumption: the label space is every statute string in the Lay train and test answers. A gold label no layer can predict (other Acts, IPC sections absent from the index) counts as a miss. Macro scores average over the whole space, a label with no gold and no prediction scoring 0. The paper does not state its own treatment, so this is our reading. For the Multi test the committed scores use the Lay train plus the Multi answers (540 labels, not the Lay space's 543); `ibid ilsic eval --space-from <Lay test>` gives the spec's space, and these scores have not been re-run with it.
- Overlap: the Multi test is described as a subset of the Lay label space with a 757-query test, so the two tests overlap and are not independent evidence.
- A layer clears a published number only if it is above it under the primary reading. The secondary reading is reported for information.
- Layers predict IPC sections only; none predicts BNS or any other Act. `assoc-nb v2` and `v3` and `linear-lr` are fitted outside this slice; `assoc-nb v2` was rebuilt with `ibid assoc fit --source ilsic-lay` (ADR 0006) and is not in git. `assoc-nb v2` and `v3` use ILSIC-Lay train text, so their Lay scores are in-distribution.
- Data caveat: ILSIC is CC BY-NC-SA 4.0 research data and stays out of git. Its labels are incomplete and no lawyer reviewed them, so none of these numbers is a claim of legal accuracy.

## Byte-identity check

Checked 2026-10-22 against `5d487ad`, the last commit before slice 14 (`8a3f7f7^`). The check hashes every file under `results/`, `gold/` and `concordance/` at that commit, except the new `ilsic` files, and compares it with the working tree (bash, not zsh, to avoid the history-modifier trap):

```bash
base=8a3f7f7^
for f in $(git ls-tree -r --name-only $base -- results gold concordance | grep -v ilsic); do
  a=$(git show "$base":"$f" | shasum -a 256 | cut -d" " -f1); b=$(shasum -a 256 "$f" | cut -d" " -f1)
  [ -n "$a" ] && [ "$a" = "$b" ] || echo "DIFF $f"
done
```

Output: no `DIFF` line over 119 files. Hashes of the files the ticket names, identical before and after:

| File | SHA-256 |
|---|---|
| `gold/v2.json` (equals `gold/v2.sha256`) | `1670c5a4a3783a3f37f12f5bcf46db4f9d8fb0b966b60c26e7c4da6429698f62` |
| `concordance/v2.json` (equals `concordance/v2.sha256`) | `365d09d0144ab93e7f4fc03cb3b2baa3baaae10952d248894f2a867b32680322` |
| `results/frozen-rule.json` | `ea01284dbbeb429e2f2c97de7d998a69b691aaab1ae1bd47b2a6a79358dbd01d` |
| `results/baseline-v2.json` | `e0fac482b3a5cd5ab743192f2e26663741dbb1419764f4c583169c315a589517` |
