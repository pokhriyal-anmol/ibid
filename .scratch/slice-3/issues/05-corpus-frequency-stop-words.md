# Corpus-frequency stop words: drop query terms that occur in a fixed share of ILSI train fact paragraphs

Status: ready-for-agent
Blocked by: none (02 and 04 are done)

What to build: a deterministic, label-free stop list made from the ILSI train fact text, and a derived rule `v3` that is the frozen v2.11 with that list added to its stop words. Ticket 04 showed that the frozen rule's top predictions are sections about courts, evidence and definitions (IPC 228A, 19, 193; BNS 358, 2), because court orders are full of words that those sections share. A term that occurs in a large share of fact paragraphs says little about which offence is described, so it is dropped from the query. This is a standard document-frequency stop list. It uses no labels and no model (ADR 0001, ADR 0004).

Parts:

- `ibid bench df-stopwords --split <train.jsonl> --min-df 0.05 --out data/df-stopwords-v1.json`: reads only the `text` field of each case (a test asserts the `labels` field is never read), tokenises with the same lower-case, letters-only rule as the query, and writes the sorted terms that occur in at least `min-df` of the cases. The output also records the split's SHA-256, `min-df`, the case count and the term count. `min-df` is fixed at 0.05 for the committed list, a standard "in one fact paragraph out of twenty" cut declared here before any result on the multi-charge set was seen. It is not to be varied against that set.
- `ibid bench derive-rule --from results/frozen-rule.json --stopwords data/df-stopwords-v1.json --version v3 --out results/frozen-rule-v3.json`: writes a frozen-rule record equal to the source except for the union of stop words, the `version`, the rule hash recomputed by the same function `bench freeze` uses, and a `derived_from` field naming the source rule hash and the list's SHA-256. BM25 k1 and b, k, r, stemming, levels and roll-up are copied unchanged. They are not retuned.
- `ibid bench run` accepts `--extra-stop-words <file>` so the dev split can be scored under v3 without a frozen record. The option changes the rule hash.

Split of work: the builder writes the code, the fixture tests and the ADR note. The three real-data criteria at the end (generating the committed list, the dev guard and the multi-charge scoring) are run by the orchestrator after the merge, because worktrees have no raw data.

Record the list's provenance in ADR 0004 under its rule-version note: v3, what it adds, and that the list was derived from `train` text only.

User stories: 3, 5, 8.

Acceptance criteria:
- On a fixture split, the list holds exactly the terms at or above `min-df`, sorted, and a term just below is absent.
- Known-bad: a fixture whose labels are shuffled or removed produces the identical list, and a mutated version of the code that reads `labels` is seen failing that test.
- Two runs produce byte-identical files.
- `derive-rule` output has a different rule hash and version from the source, an unchanged k, r, k1, b, roll-up, stemming and levels, and a stop word list that is the sorted union.
- The real list is generated from `data/raw/lesicin/train.jsonl`, committed with its recorded hashes, and its size and ten most frequent terms are reported.
- Dev guard, reported and not enforced: the full ILSI dev split is scored with v2.11 and with v3 through `bench run`, and the report shows micro-F1, macro-F1, Jaccard and single-label micro-F1 for both output rules, with any drop of more than 0.5 point called out. The test split is not scored.
- The multi-charge set is then scored once per Act with `results/frozen-rule-v3.json` through `ibid charges score`, and the results are reported next to v2.11's. No parameter is changed after seeing them.
- The existing suite still passes, and nothing under `data/raw/` is added to git.
