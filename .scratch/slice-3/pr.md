# Slice 3: a multi-charge Test set, a per-charge scorer, four layers and a published-source route D

## Summary

Slice 2 scored the Baseline on ILSI only (micro-F1 9.6, macro-F1 6.2 on test). That says little about a query that describes several offences at once, so this slice adds pinned multi-charge sets and a scorer that reports by Charge. No Layer replaces the Baseline, and each reports its own evidence packet as ADR 0001 requires.

What was built, by ticket:

- 01 to 04: the multi-charge set file and its validator (`ibid charges validate`), a per-Charge scorer for the IPC and the BNS, set v1 of 30 items collected from ILSI train fact text by a written rule, and the frozen Baseline v2.11 scored on it. Labels are `agent-drafted-skeptic-refuted`. No lawyer has reviewed them, so scores measure agreement with drafted labels.
- 05: corpus-frequency stop words, closed as rejected before any score. The list dropped offence words such as murder, rape and assault. The generic commands (`df-stopwords`, `derive-rule`, `--extra-stop-words`) remain, and ADR 0004 records v3 as proposed and rejected.
- 06: one scorer for every Layer. A Predictions file is scored by `charges score --predictions`, and the Baseline can be exported in that format.
- 07 (route A): cited-section extraction, mapping to the other Act through verified Concordance entries only.
- 08 (route B): a learned term-to-section association from ILSI train minus the 30 item ids, an opt-in Layer under ADR 0005.
- 09 (route C): per-Charge sub-queries from a pinned file, then Baseline retrieval per sub-query.
- 11: a comparison report across Layers and sets. It now keys counts by set, Act and Concordance, has a Concordance column so v2 and v3 rows sit side by side, and prints a circularity caveat for BNS labels that come from the Concordance.
- 12 (route D by published source): set v2, 30 laypeople forum posts from ILSIC-Lay, labels extracted from lawyers' replies (`lawyer-answer-extracted`), scrubbed of phone numbers, emails, URLs and long digit runs. Baseline and routes A, B and C are scored once on it. The labels are incomplete by the corpus authors' own count, so recall is meaningful and precision is not.
- 13: Concordance v3 from the CAPT correspondence table, 348 served entries (basis `source-table-checked`), with 93 of the 100 ILSI labels having a verified BNS counterpart. The table is one director's compilation and not a Ministry document, and the report says so. v2 and its pin are untouched.
- 14: audit of set v1 against the CAPT table and an independent three-agent panel, written to `.scratch/slice-3/label-audit.md` and recorded in `gold/multicharge/v1.1.json` with its own pin. 96 of 98 Charges were confirmed by at least two of three panel agents, mean pairwise kappa 0.89, 97 BNS pairs agree with the table, 0 differ, 1 is not covered, and 23 candidate missing Charges are listed and not added. This is not a lawyer review and the labels keep their basis.

Constraints held: no model in the Baseline path (ADR 0001), frozen gold and pins unedited, and every Layer opt-in. Layer B has learned weights, which ADR 0004 forbids in tokenisation and ADR 0005 permits only as an opt-in next to the Baseline, so nothing contradicts an accepted ADR.

Caveats the reports state: set v1 comes from ILSI train, which the frozen rule was tuned on, so it is not unseen. 29 of 30 v1 queries name their sections, so route A measures how well code reads cited sections, not facts. The panel agents share the drafters' legal knowledge, so agreement is consistency, not correctness. BNS recall for Layers that read the Concordance is not independent on sets whose BNS labels come from it.

Not part of this PR: ticket 10 (route D, person-written queries) is `ready-for-human` and waits on the owner's queries. Tickets 12 to 14 replace it for now.

## Test plan

- [x] `uv run python -m unittest discover -s tests`: Ran 198 tests in 30.020s, OK.
- [x] Stopping-rule and hurts-simple tests seen to fail under each mutation of `optimise.py`.
- [x] Assoc ranking and k=5 tests seen to fail on a reversed ranking and on k=4.
- [x] Refusal tests in `test_charges_score` assert "no pin file" and "does not hold the rule it names".
- [x] Comparison counts keyed by (set, Act, concordance) and the BNS circularity caveat each have a test. `results/layer-comparison.md` regenerated: set v1 shows 183 then 10 unmapped, set v2 shows its own zeros.
- [x] Ledger `gold/multicharge/v1.ledger.json` holds 18 entries after scoring cited and assoc-nb on v1 with the concv3 predictions. BNS recall on v1 reads 0.0% with Concordance v2 and 82.7% and 37.8% with v3 (cited, assoc).
- [x] Ticket 12 counts in `results/multicharge-v2-report.md`: 836 rows, 109 candidates, 138 cited sections, 50 non-IPC and 3 IPC 34/120B left out, 1 duplicate, none absent from the index.
- [x] Ticket 13 counts re-derived this session by re-running `ibid concordance from-table`: 529 rows, 354 produced, 4 refused, 4 skeptic refutations, 348 served.
- [x] Extra-stop-words test asserts the baseline predicts IPC 2 and only the filtered run predicts IPC 1.
- [x] Freeze test runs `ibid freeze` through `main()` on a real review sheet with 12 pass blocks and asserts 5 entries. The loader test goes through `ibid cited extract`, accepting the new basis and refusing an unknown one with exit 1.
- [x] Validate no-rewrite test asserts exit code 0 and `items: 6` before comparing file snapshots.
