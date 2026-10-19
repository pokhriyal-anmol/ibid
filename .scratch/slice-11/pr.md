## Summary

The MCP `search` tool was keyword search over the Raw query only, and on story-style questions it finds a small share of the charges a lawyer would name. The learned layer `assoc-nb v3` (opt-in under ADR 0005) does better, but no client could reach it, and no tool description stated what either mode can do. This slice adds an optional `mode` to `search` and states the measured limits.

- `mode` is `keyword` (default) or `learned`. Omitting it, or passing `keyword`, takes the existing path unchanged, including `adjacent` and `limit`. A golden capture taken before the change confirms the default output is byte-identical.
- `mode: "learned"` takes the Raw query only, with no rewrite, model call or network (ADR 0001, ADR 0005). It uses the existing `assoc` code unchanged and returns the top 5 IPC Provisions in rank order. Each hit has `citation`, `heading`, `text`, `rank` and a `bns` list of verified Concordance v3 counterparts (empty when none). The result carries `layer`, `layer_version`, `model_sha256` and a fixed `caveat`.
- The model path is `--assoc-model` on `ibid mcp`, default `data/assoc-nb-v3.json`. The file is loaded on the first learned call, never at startup. A missing, unreadable, malformed or wrong-layer/version file is a tool error that names the path and the fit command (or the found and expected values), and keyword mode keeps working.
- An unknown `mode` is a tool error naming `keyword` and `learned`. `limit` above 5 is clamped to 5 with a note. `adjacent` is ignored in learned mode with a note.
- Tool descriptions and the caveat state the measured limits: 58.3 percent of IPC charges on layperson posts (set v2), 42.9 percent on judgment text (set v1), 140 IPC sections, incomplete labels, not legal advice. For keyword search the text quotes the per-set IPC baseline figures from `results/layer-comparison.md` instead of a pooled "about 5 percent" (D-002), as ticket 3 specifies. A test reads those figures from the file so the text cannot drift.
- `ibid setup` prints one optional line for the model (present with sha256, or absent with the fit command) and never changes the exit status. The README says how to produce the model, that the training data are gated and non-commercial, and that learned mode is a research option outside the standard install.

No contradiction with an ADR was found. The index, baseline, frozen rule, pinned files and `results/` are untouched.

Review fix-ups included: malformed model JSON with wrong types is now a tool error (`LazyModel.get` catches `AttributeError` and `ZeroDivisionError`); the model path default lives only in the CLI argument; duplicate and mislabeled tests were removed or corrected.

## Test plan

- [x] `uv run python -m unittest discover -s tests`: Ran 336 tests in 57.214s, OK.
- [x] Default `search` (no `mode`, and `keyword`) matches the golden capture byte for byte.
- [x] Learned hits with an invented fixture model equal `ibid assoc predict` output in citations and order.
- [x] Missing, wrong-layer, wrong-version, invalid-JSON and wrongly typed model files each return a tool error, and the next keyword call works.
- [x] Unknown `mode`, clamped `limit`, and ignored `adjacent` behave as specified.
- [x] Description and caveat figures are checked against `results/layer-comparison.md`; the 140-section count is derived from the model's label set.
- [x] With the real model, learned top-5 for three set v2 items equals the committed predictions, and `model_sha256` matches the ledger. The test skips with a message naming `data/assoc-nb-v3.json` when the file is absent.
- [x] `ibid setup` exits 0 with the model absent or present, and non-zero on a required failure.
- [x] New tests were run once against known-bad input and seen failing, including the wrongly typed model fix, which fails with the fix removed.
