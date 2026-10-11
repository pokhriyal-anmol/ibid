# 0004: A fixed, documented tokenisation of the raw query is allowed

Status: accepted (owner, 2026-10-11)

Retrieval still takes the raw query and nothing else ([ADR 0001](0001-retrieval-independent-of-the-model.md)). This ADR adds one allowance: code may turn the raw string into index terms by a fixed, written, versioned rule, with no model in the path.

Slice 1's keyword search passes the raw string to SQLite FTS5. A case-facts paragraph (punctuation, quotes, hyphens, dozens of words) either is invalid FTS syntax or requires every word to match, so it returned no hits in a check on 2026-10-11. Slice 2 scores fact paragraphs, so it needs a tokenisation step.

**Rule of the allowance.** The step is deterministic code. It is named and versioned, and its version and a hash of its parameters are written into every results file. It uses no model and no learned weights. Changing it makes a new rule version, never an edit.

**What it may do:** lower-case, split on non-letters, drop words from a fixed list, drop repeated terms, quote each term so no word is read as an FTS operator, join the rest with OR. The stop-word list, dedup and quoting are all in the recorded parameter hash. **What it may not do:** call a model, expand synonyms from a model, or use the gold labels.

**Cost:** the string the index sees is no longer byte-for-byte the string the user typed. The raw query is still the only input, and the rule is public, but a reader must trust the rule version recorded beside every score.

**Check:** two runs with the same rule version and data are byte-identical, and a changed rule changes the recorded hash.
