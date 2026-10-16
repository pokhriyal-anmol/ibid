# Fit assoc-nb v2 on the real train split, score it once per set and Act, regenerate the comparison

Status: done
Blocked by: 01, 02, 03, 04, 05

What to build: the real run, recorded as commands in the ticket's done note. Fit `data/assoc-nb-v2.json` from `data/raw/ilsic/FT-Layman-train.jsonl.xz` with `--min-posts 5`, holding out `FT-Layman-test.jsonl.xz` and set v2. Predict for `gold/multicharge/v2.json` and set v1 with `concordance/v3` (the pinned file the v1 rows use), into `results/layers/assoc-nb-v2-multicharge-{v1,v2}-predictions.json`. Score each once per Act with `ibid charges score --predictions` into `results/multicharge-{v1,v2}-assoc-v2-{ipc,bns}.json`. Regenerate `results/layer-comparison.md` with `ibid charges compare` over every existing results file plus the four new ones.

User stories: 2 (on real data), 3, 4, 5, 8.

Acceptance criteria:
- The model header reports 0 set v2 rows and every exact-text match with the test split dropped; the counts are quoted in the done note from the header, not retyped.
- The model file is untracked (`git status` does not list it); its SHA-256 appears in all four predictions files.
- Each set and Act has exactly one `assoc-nb v2` ledger entry.
- `results/layer-comparison.md` has `assoc-nb v1`, `assoc-nb v2` and baseline rows for both sets and both Acts, with both ticket 5 caveats where they apply.
- Byte-identity: `results/baseline-v1.json`, `results/baseline-v2.json`, `results/frozen-rule.json`, every gold file and every pinned concordance file match their pre-slice hashes; `ibid eval --gold gold/v2.json --concordance concordance/v2.json` reproduces the committed scores.
- `uv run python -m unittest discover -s tests` passes.
