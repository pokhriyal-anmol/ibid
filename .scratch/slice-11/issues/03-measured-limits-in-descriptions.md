# Tool descriptions and the caveat state the measured limits, read-checked against layer-comparison.md

Status: done
Blocked by: 01

## What to build
Write the `search` tool description (and the other tool description that discusses search, if any, per spec decision 7 "both tool descriptions") and the fixed `caveat` string so they state: keyword search finds about 5 percent of charges on story-style queries; learned mode was fitted on court-judgment text and layperson forum posts, covers 140 IPC sections, finds 58.3 percent of IPC charges on layperson posts (set v2) and 42.9 percent on judgment text (set v1), was measured on labels that are incomplete, and is not legal advice. A test parses `results/layer-comparison.md` and checks the quoted figures against it, so the text cannot drift from the measurements.

## User stories
9, and the caveat content of 3.

## Acceptance criteria
- [ ] `tools/list` over the stdio harness shows `mode` with enum `keyword`, `learned` in the `search` inputSchema.
- [ ] A test reads the `assoc-nb | v3` IPC rows of `results/layer-comparison.md` and asserts the description and caveat quote exactly their recall figures (58.3 for set v2, 42.9 for set v1).
- [ ] The same test reads the baseline rows and asserts the quoted keyword figure is consistent with them, at the set-and-Act level (D-002), not a pooled figure.
- [ ] The 140-section figure is checked against the label count of the source it comes from (see questions), not typed as a bare constant.
- [ ] The caveat returned by a learned call equals the fixed string the test checks.
- [ ] Known-bad run seen failing once: editing a figure in the description by 0.1 fails the test.
- [ ] `results/layer-comparison.md` itself is unchanged.

## Default taken
Keyword figure: the baseline IPC recall per set in `results/layer-comparison.md` runs from 3.1 to 6.0 percent (BNS up to 9.9), so the text states the per-set IPC baseline figures read from those rows (for example "3 to 6 percent of IPC charges"), and the test checks each against its row. It does not quote a single pooled "about 5 percent" (D-002). The owner may still choose different wording.
140 sections: the test derives the count from the label set of `data/assoc-nb-v3.json` (140 entries in `docs`/`counts`) and skips that assertion with a clear message when the model file is absent; it is not typed as a bare constant.
