# `ibid assoc fit` fits assoc-nb v3 on both training files, with a leakage test

Status: done
Blocked by: none

What to build: extend `ibid assoc fit` (in `src/ibid/cli.py` and `src/ibid/assoc.py`) so one invocation takes both training files (the ILSI train split with set v1 as holdout, and the ILSIC-Lay train split with set v2 as holdout plus the Layman test split for duplicate removal) and writes `data/assoc-nb-v3.json`. Reuse the existing v1 and v2 loading and holdout rules unchanged, add their raw per-section counts with no weighting, map ILSI labels to IPC sections, keep offence sections only (drop IPC 34, 149, 120B), and keep sections with at least 5 training examples in the union. Tokenisation, smoothing and k=5 are those of v1 and v2 (ADR 0004, 0005). The header records layer `assoc-nb`, version `v3`, per source: file SHA-256, examples used, examples dropped (by reason); the section threshold; the vocabulary size. Add `data/assoc-nb-v3.json` to `.gitignore`. v1 and v2 fitting must produce byte-identical models to before.

User stories: 1, 2, 7.

Acceptance criteria:
- A `unittest` test drives `ibid assoc fit` with invented judgments and posts in the shape of the real files and asserts the header fields above, and that per-section counts equal the sum of the two single-source fits.
- A test asserts no set v1 id, no set v2 id, no Layman test post and no ILSI test or dev case is in the v3 training data. Run once against known-bad input (a fixture where a held-out id is in train with the drop removed) and seen to fail with the assertion's own message.
- A test asserts a section with 4 union examples is excluded and one with 5 is included, and IPC 34/149/120B never appear.
- Re-fitting v1 and v2 from the same inputs gives byte-identical files to the current models (hash check); `data/assoc-nb-v3.json` is not tracked by git.
- Full suite passes: `uv run python -m unittest discover -s tests`.
