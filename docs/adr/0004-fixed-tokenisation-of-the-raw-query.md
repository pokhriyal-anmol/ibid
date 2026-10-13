# 0004: A fixed, documented tokenisation of the raw query is allowed

Status: accepted (owner, 2026-10-11)

Retrieval still takes the raw query and nothing else ([ADR 0001](0001-retrieval-independent-of-the-model.md)). This ADR adds one allowance: code may turn the raw string into index terms by a fixed, written, versioned rule, with no model in the path.

Slice 1's keyword search passes the raw string to SQLite FTS5. A case-facts paragraph (punctuation, quotes, hyphens, dozens of words) either is invalid FTS syntax or requires every word to match, so it returned no hits in a check on 2026-10-11. Slice 2 scores fact paragraphs, so it needs a tokenisation step.

**Rule of the allowance.** The step is deterministic code. It is named and versioned, and its version and a hash of its parameters are written into every results file. It uses no model and no learned weights. Changing it makes a new rule version, never an edit.

**What it may do:** lower-case, split on non-letters, drop words from a fixed list, drop repeated terms, quote each term so no word is read as an FTS operator, join the rest with OR. The stop-word list, dedup and quoting are all in the recorded parameter hash. **What it may not do:** call a model, expand synonyms from a model, or use the gold labels.

**Cost:** the string the index sees is no longer byte-for-byte the string the user typed. The raw query is still the only input, and the rule is public, but a reader must trust the rule version recorded beside every score.

**Check:** two runs with the same rule version and data are byte-identical, and a changed rule changes the recorded hash.

**Rule versions.** v1 (2026-10-11) hashed the stop words, tokenisation, roll-up, k and r. v2 (2026-10-12) also hashes BM25 k1 and b, the stemming rule and the indexed level, and scores with a Python BM25 that reproduces the FTS5 scores at the defaults to 1e-9. No result file carries a v1 hash. Optimisation rounds are v2.1, v2.2 and so on.

**v3 (proposed and rejected 2026-10-12, slice 3 ticket 05).** v3 was to be the frozen v2.11 with a corpus-frequency stop list: every term in at least 5 percent of the fact paragraphs of the ILSI `train` split, derived from `train` text only. The list was generated and read before anything was scored, and it was rejected: the cut drops offence words such as murder, rape and assault. No list was committed, no v3 rule exists, no v3 score was computed, and every committed multi-charge result uses v2.11. `ibid bench df-stopwords`, `ibid bench derive-rule` and `--extra-stop-words` remain in the code as generic tools. A later rule would take the next version number and its own paragraph here.
