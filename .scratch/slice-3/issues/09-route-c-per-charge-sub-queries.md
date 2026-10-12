# Route C: retrieve per charge from a pinned file of sub-queries

Status: ready-for-agent
Blocked by: 06

What to build: `ibid charges subquery --set <file> --subqueries <file> --index <index> --frozen-rule <file> --per-subquery 2 --out <predictions.json>`. A model splits each query into per-charge sub-queries, written in statute-like words. The sub-queries are stored in a pinned file. Code then retrieves for each sub-query with the frozen baseline rule and unions the results. This is the decomposition-and-rewriting idea from the research note, built as an opt-in layer under ADR 0001: the model's output is an input file with a recorded hash, retrieval is code, and the layer reports its own predictions file (ticket 06 format, layer `decomposed`).

Sub-queries file: `{"producer": str, "producer_note": str, "set_sha256": str, "items": {item id: [sub-query, ...]}}`, with a pin beside it. Each sub-query is a short string. An item with no sub-queries falls back to nothing (it is not silently replaced by the full query).

Retrieval: for each sub-query, the frozen rule's tokenisation, stop words, BM25 k1 and b and roll-up are used unchanged, over each Act, rolled up to sections. The top `--per-subquery` sections (default 2, declared here, one section per sub-issue being the published choice and two allowing for a definition and a punishment section) are taken, and the union over an item's sub-queries is the item's prediction. Ties break by citation string.

Producer. Agents write the sub-queries in a separate step run by the orchestrator, not by the builder. Each agent sees only an item's query text. It never sees a label, a section number from the labels, or a retrieval result, and is told to describe each distinct offence the text alleges in a short statute-style sentence without section numbers. The prompts are saved with the file.

User stories: 4, 6, 8.

Acceptance criteria (builder):
- On a fixture, a query with two charges and two sub-queries returns the union of each sub-query's top sections, with predictions equal to hand-computed values.
- Known-bad: a sub-queries file for another set hash is refused, an unknown item id is refused, and a changed byte fails the pin.
- Two identical runs are byte-identical, and the output equals scoring each sub-query separately with `ibid bench run` logic (checked once).
- The layer records the producer, the pin and the per-subquery value in `inputs`.

Acceptance criteria (orchestrator, after the merge):
- The sub-queries file for set v1 is produced by agents that saw only the query text, pinned and committed with their prompts.
- The layer is scored once per Act on set v1 through ticket 06, and the report shows the number of sub-queries per item and mean predictions per item beside the baseline's.
- The report says that the sub-queries are a model's paraphrase of the query and can carry the section numbers or legal terms the model knows, and that the result measures the combination of the model and the baseline.
