# Slice 3: a multi-charge Test set, a per-charge scorer and four layers scored against the Baseline

## Summary

Slice 2 scored the Baseline on ILSI only (micro-F1 9.6, macro-F1 6.2 on test). That says little about a query that describes several offences at once, so this slice adds a pinned multi-charge set and a scorer that reports by Charge.

What was built, by ticket:

- 01 to 04: the multi-charge set file and its validator (`ibid charges validate`), a per-Charge scorer for the IPC and the BNS, 30 items collected from ILSI train fact text by a written rule, and the frozen Baseline v2.11 scored on them. Labels are `agent-drafted-skeptic-refuted`. No lawyer has reviewed them, so scores measure agreement with drafted labels.
- 05: corpus-frequency stop words. Closed as rejected before any score. The list dropped offence words such as murder, rape and assault, and a label-free repair did not separate them from generic words. The generic commands (`df-stopwords`, `derive-rule`, `--extra-stop-words`) remain. ADR 0004 now records v3 as proposed and rejected, with the reason.
- 06: one scorer for every Layer. A Predictions file is scored by `charges score --predictions`, and the Baseline can be exported in that format.
- 07 (route A): cited-section extraction, with mapping to the other Act through verified Concordance entries only.
- 08 (route B): a learned term-to-section association from ILSI train minus the 30 item ids, an opt-in Layer under ADR 0005.
- 09 (route C): per-Charge sub-queries from a pinned file, then Baseline retrieval per sub-query. The scorer and report record `subqueries_per_item_mean` and the model-paraphrase caveat.
- 11: a comparison report across Layers and sets, with counts and caveats carried from the scorer.
- Review fixes: stopping-rule and hurts-simple tests now drive `bench round`, assoc ranking and k=5 tests go through `assoc predict`, refusal tests assert the specific message, `charges.validate` reuses `_load_set`, the citation-in-index check is one helper, and `cited.extract` uses `bench.sha256`. CONTEXT.md gained Charge, Multi-charge set, Layer and Predictions file.

Constraints held: no model in the Baseline path (ADR 0001), the frozen gold and pins are untouched, and each Layer is opt-in with its own evidence packet. Layer B has learned weights, which ADR 0004 forbids in tokenisation, and ADR 0005 permits only as an opt-in next to the Baseline. That is the one place the slice stretches an earlier ADR, and it is recorded as ADR 0005, so nothing contradicts an accepted ADR.

Caveats the report states: the 30 items come from ILSI train, which the frozen rule was tuned on, so the set is not unseen. 29 of 30 queries name their sections, so route A measures how well code reads cited sections, not how well it reads facts.

Not part of this PR: ticket 10 (route D, person-written queries) is `ready-for-human` and waits on the owner's queries, so route D has no set yet.

## Test plan

- [x] `uv run python -m unittest discover -s tests`: Ran 186 tests in 30.135s, OK.
- [x] Stopping-rule and hurts-simple tests seen to fail under each mutation of `optimise.py`.
- [x] Assoc ranking and k=5 tests seen to fail on a reversed ranking and on k=4.
- [x] Refusal tests in `test_charges_score` assert "no pin file" and "does not hold the rule it names".
- [x] Collection report counts: 108 Charges drafted in included items, 0 of 98 Charges with an empty bns (and ipc) list.
- [x] Baseline exported through `charges export-baseline` and scored through `--predictions` equals the original `--frozen-rule` figures on all four rows (IPC 3 and 5 of 98, BNS 4 and 5 of 98), re-checked after the review fixes.
- [x] Predictions of routes A, B and C regenerated after the review fixes: items identical to the committed files, so only the record fields changed. Results re-rendered with throwaway ledgers, so no extra scoring is recorded.
- [x] `results/layer-comparison.md` regenerated: it carries the layer counts, the caveats and the ILSI dev and test rows for the Baseline and route B.

## Results (set v1, 30 items, 98 charges, per-charge recall, all-charges-hit in brackets)

| Layer | IPC | BNS | What it measures |
|---|---|---|---|
| Baseline v2.11, threshold | 5.1% (0%) | 5.1% (0%) | text matching of the whole query |
| A, cited sections | 87.8% (73%) | 0% (0%) | code reading stated sections; the labels were drafted partly from the same mentions |
| B, learned association | 41.8% (10%) | 0% (0%) | words-to-sections habits over 100 labels, 30 items held out of training |
| C, sub-queries | 62.2% (20%) | 79.6% (50%) | a model's paraphrase, then Baseline retrieval per sub-query |

On ILSI test, route B scores micro-F1 35.4, macro-F1 18.0 and Jaccard 22.8, scored once, against the Baseline's 9.6, 6.2 and 5.5. Both BNS zeros for A and B come from only 12 verified Concordance entries, not from the extractors.

## Added after the first review: published sources instead of the owner's queries

- **Concordance v3** (`concordance/v3.json`, pinned): 348 served entries against 12 in v2, from the CAPT Bhopal correspondence table (a person's compilation, not an MHA publication), parsed by `ibid concordance from-table`, text-checked against the index, then challenged by an independent skeptic pass against the raw table lines (4 of 350 refuted and dropped). With v3, on set v1, route A's BNS recall goes from 0% to 82.7% and route B's from 0% to 37.8%; the IPC figures are unchanged, so it is coverage, not the extractors (`results/multicharge-v1-*-concv3.json`).
- **Set v2** (`gold/multicharge/v2.json`, pinned): 30 real layperson forum posts from ILSIC-Lay (CC BY-NC-SA 4.0, non-commercial), 84 charges, labels extracted from forum lawyers' replies by the corpus authors. Labels are incomplete, so recall is meaningful and precision is not. Per-charge recall (IPC / BNS): baseline top-k 4.8% / 9.9%, A 0% / 0%, B 39.3% / 48.1%, C 25.0% / 40.7%. See `results/multicharge-v2-report.md`.
- **Label audit of set v1** (`.scratch/slice-3/label-audit.md`, `gold/multicharge/v1.1.json`): 96 of 98 charges confirmed by 2 of 3 blind panel agents, 97 of 98 BNS pairs agree with the table (1 not covered), 23 candidate missing charges listed and not added. This is not a lawyer review.
- The set v2 file stays private (partial scrub of personal names). It is not for the public repository.

## Known issues

- Set v1 is 30 items from judgment text, 29 of them naming their sections, labelled by agents with no lawyer review. It cannot separate rules that differ by a few charges, and route A's figure is partly circular. Route D (a set of person-written queries) is the fact-only measure and does not exist yet.
- The model file `data/assoc-nb-v1.json` (45 MB) is not committed. Its SHA-256 is in every result that used it and `ibid assoc fit` rebuilds it.
- The Baseline dev ILSI row in the comparison is labelled `v2`, not `v2.11`, because `bench run` without a frozen record records the rule version constant. The rule hash equals the frozen rule's.
- Route C's score depends on the model that wrote the sub-queries, and the pinned file records which.
