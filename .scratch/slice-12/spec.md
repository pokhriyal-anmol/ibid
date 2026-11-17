# Slice 12: Score the frozen rule on IL-TUR LSI

Status: pre-registered 2026-10-22, before any IL-TUR score exists.

## What this is

IL-TUR `lsi` (Exploration-Lab/IL-TUR, CC BY-NC-SA 4.0, gated) is ILSI with names and all statute citations masked. Measured 2026-10-22: every IL-TUR id is in the matching ILSI split (42,750 of 42,835 train, 10,181 of 10,200 dev, 13,019 of 13,039 test), no id crosses splits, and all 13,019 test label sets equal ILSI's. So this is a re-measurement on harder text (citations masked), not new data. It gives one published comparison point.

## Rules

- Frozen rule v2.11 unchanged (k=5, r=0.7, BM25 k1=4, b=1). No tuning, no new stop words.
- The IL-TUR test split is scored once, in its own ledger (`results/test-ledger-iltur.json`). Dev may be sampled for a smoke check only.
- Labels map `Section N` to `Section N in The Indian Penal Code`, the same 100 labels as `label_vocab.json`.
- Data stay outside git (`~/data/il-tur`). Only score files are committed.
- Reported: macro-F1 (the IL-TUR metric), micro-F1, Jaccard, for top-k and threshold.
- Reference: LeSICiN 28.08 macro-F1, InLegalBERT+LSTM 26.23 (IL-TUR paper, arXiv 2407.05399, Table 22). The paper's test has 13,039 cases, the Hugging Face copy 13,019.
- No decision rule: the result is reported whatever it is. Our macro-F1 averages over all 100 labels with a zero for an unsupported, unpredicted label; the paper's exact averaging is not confirmed, so the comparison is approximate.

## Addendum 2026-10-22: learned layers (owner: "test assoc-nb v1 and v3 as well")

`assoc-nb v1` and `v3` are each scored once on the same IL-TUR test file, in `results/test-ledger-iltur-assoc.json`, with `ibid assoc eval`. No refit, no change. Neither model trained on any test id (ILSI train only, ADR 0005 and 0008). The question is how far each ILSI result (v1 35.4 micro, 18.0 macro; v3 35.2 micro, 12.5 macro) falls when statute citations are masked. Reported, no decision rule. Both layers were fitted on the unmasked training text, so a gap is a train/test text mismatch as much as a reliance on citations.
