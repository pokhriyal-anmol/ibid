## Summary

Slice 1 builds the measurement layer for Ibid. One `ibid eval` command parses the IPC and the BNS into section trees, resolves cross-references by rule, serves a verified concordance, answers a frozen and hash-pinned gold set from a SQLite index, and writes a results file that carries the gold hash, the concordance hash and the parser version. No model is called anywhere (ADR 0001). The stack is Python, SQLite and `uv` (ADR 0002). The baseline is the number later layers must beat. No quality target is set.

What is in it:

- Parsers for both Acts: BNS 358 of 358 sections, IPC 575 of 575, with sub-provisions as separate provisions.
- Rule-based cross-references with chain lookup, and deterministic provision-level keyword search.
- A concordance loader that validates every entry against the index and serves only verified entries.
- Gold v2 (45 items) with its pin, and the `ibid conform` and `ibid freeze` steps that produced it with no model.
- Baseline v2: 45 of 45, byte-identical across two runs.
- Corruption tests: a scrambled section lowers its category, a wrong mapping lowers its category, swapped source pages refuse to score.

Review round: `wf-review` found 14 issues and 11 were fixed in this branch. The notable ones: source-PDF hashes are now written into every gold item, the loader rejects malformed entries (a `removed` entry with a BNS citation, a `new` entry with an IPC citation, a wrong-act citation), and a concordance entry is served as verified only when a person or an agent acting on the owner's instruction passed it on the review sheet.

Concordance provenance in v2: 66 entries, 12 served (8 `human-checked`, 4 `agent-checked-for-owner`), 54 not served and answering "no verified concordance".

## Test plan

- [x] `uv run python -m unittest discover -s tests`: 40 tests, OK
- [x] Two scored runs of `gold/v2.json` with `concordance/v2.json` are byte-identical and equal `results/baseline-v2.json`
- [x] `gold/v1.json`, its pin and `results/baseline-v1.json` are untouched
- [x] `gold/v2.sha256` and `concordance/v2.sha256` match their files
- [x] The scorer was mutated two ways and the matching corruption test failed each time; the delegated-check label was removed and its test failed
- [x] No PDF or `data/raw/` file in any commit on any branch

## Known issues

- Keyword gold is partly system-derived (ADR 0003, status proposed). A pass on those four items is not an independent measurement.
- 54 concordance entries are not human-checked and are not served. Checking more of them is future work.
- The concordance pin is recorded in results but not enforced at eval time, because the corruption test feeds an unpinned wrong file on purpose.
- 45 of 45 is a ceiling, not a quality claim: the set is small and its conventions were settled with the system in view.
- Correspondence is a legal judgement. A lawyer should review it before any score is published.
