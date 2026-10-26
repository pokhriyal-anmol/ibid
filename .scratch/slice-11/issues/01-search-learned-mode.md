# search gains mode, with the default unchanged and learned mode returning assoc-nb v3 hits

Status: done
Blocked by: none

## What to build
Add an optional `mode` argument (`keyword` default, `learned`) to the MCP `search` tool in `src/ibid/mcp.py`, and `--assoc-model` on `ibid mcp` (default `data/assoc-nb-v3.json`). Omitting `mode`, or passing `keyword`, takes the existing keyword path untouched, including `adjacent` and `limit`. `mode: "learned"` loads the model file on the first learned call (never at startup) through the existing `assoc` model class, unchanged, takes the raw query only (ADR 0001, ADR 0005), and returns the top-5 IPC sections in the layer's rank order. Each hit carries `citation`, `heading`, `text` (verbatim, from the index), `rank`, and `bns`: the verified BNS counterpart citations from Concordance v3 (empty list when there is no verified entry). The result carries `layer` (`assoc-nb`), `layer_version` (`v3`), `model_sha256` (hash of the model file) and a `caveat` string field (its measured wording is pinned in ticket 3; a placeholder that ticket 3 replaces is fine here). Add `mode` to the `search` inputSchema.

Fixture: a tiny invented model fitted with `ibid assoc fit` on invented posts under `tests/fixtures/`, so no gated data is needed.

## User stories
1, 2, 3, 4, and the no-change half of 11.

## Acceptance criteria
- [ ] Before changing `mcp.py`, a golden capture of `search` responses (several queries, with and without `adjacent` and `limit`) is recorded through the stdio harness `tests/mcp_harness.py`; after the change the same calls with no `mode` and with `mode: "keyword"` are byte-identical to it.
- [ ] With the invented model, `mode: "learned"` returns up to 5 IPC hits whose citations and order equal what `ibid assoc predict` writes for the same query and model.
- [ ] Each hit has `citation`, `heading`, `text`, `rank`, `bns`; the result has `layer == "assoc-nb"`, `layer_version == "v3"`, `model_sha256` equal to the sha256 of the fixture file, and `caveat`.
- [ ] An IPC hit with a verified Concordance v3 entry lists its BNS citations; one without lists `[]`.
- [ ] Starting `ibid mcp` with `--assoc-model` pointing at a nonexistent path succeeds and keyword calls work (the model is not read at startup).
- [ ] Known-bad runs seen failing once: learned output leaking into the default call breaks the golden test; loading the model at startup breaks the lazy-load test.
- [ ] No change to `src/ibid/assoc.py`, the index, the baseline, the frozen rule, any pinned file or anything under `results/` (`git diff --stat` shows none).
- [ ] Tests run via `uv run python -m unittest discover -s tests`.
