# Report: round-0 baseline, final number and published scores with caveats

Status: needs-triage
Blocked by: 04, 07, 08

What to build: a report command (or report section written by the run) that shows the round-0 baseline next to the final frozen-rule scores (micro F1, macro F1, Jaccard, for top-k and threshold), the train/dev gap, the per-label never-found list, and a table of published numbers with their source (28.08 m-F1 on IL-TUR, 28.45 macro-F1 in the LeSICiN paper) and the caveats: different models (trained classifiers), possibly different dataset copy, split counts and metric protocol, and that our metrics are our own implementation until the official evaluation script is read. It claims no rank.

User stories: 12, 7, 8.

Acceptance criteria:
- On fixture results and a fixture log, the report shows round 0 and the final round with the right numbers, re-derived from the files, not hand-typed.
- The final numbers are read from the test ledger of ticket 07; if the ledger holds more than one test score, the report shows all of them.
- The comparison table names each source and lists every caveat above.
- The report carries the data hashes, rule version and rule hash of the numbers it quotes.
- Two report runs on the same inputs are byte-identical.
