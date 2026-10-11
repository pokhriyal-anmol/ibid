# Make BM25 parameters, stemming and indexed levels variable by an optimisation round

Status: ready-for-agent
Blocked by: none (08 is done)

What to build: the three knobs that ticket 08 refuses today as deferred, so the owner-approved protocol is fully available to the optimisation. SQLite FTS5's `bm25()` fixes k1 = 1.2 and b = 0.75, so scoring moves into Python (standard library only, ADR 0002): tokenise provision text with the same lower-case, letters-only rule as the query, build term statistics once per index, and score with the BM25 formula FTS5 documents. Retrieval stays a deterministic function of the raw query (ADR 0001, ADR 0004); no model, no learned weight, nothing derived from labels.

Knobs, each recorded in the rule parameters and therefore in the rule hash and the optimisation log:

- `bm25_k1`: float greater than 0. Default 1.2.
- `bm25_b`: float from 0 to 1. Default 0.75.
- `stem`: `none` (default) or `suffix`, a fixed, documented, versioned suffix-stripping rule for plural and `-ed`/`-ing` endings applied to both query and provision terms. A rule table in code, not a library.
- `levels`: `all` (default, every provision is a document, as today), `top` (only section-level provisions, whose text already contains their children) or `leaf` (only provisions with no children).

`ibid bench round --change <knob>=<value>` accepts them (one change per round, as today) and no longer lists them as unsupported. `ibid bench run` and `freeze` carry them through the frozen record. Update the deferred notes in ticket 08 and in `spec.md` to say they are built.

User stories: 3, 8, 10.

Acceptance criteria (fixture tests through `ibid bench run` and `ibid bench round`, plus one real-data check):
- At the defaults, the Python scorer returns the same section scores as the FTS5 path within 1e-9 on the fixture, and the same predictions. Known-bad: change one default and see this test fail.
- At the defaults, the real-data run `ibid bench run --split data/raw/lesicin/dev.jsonl --sample 200 --k 3 --r 0.8` gives micro F1 0.065667, macro F1 0.031081 and Jaccard 0.039742, the values measured on 2026-10-11 with the FTS5 path. If they differ, stop and report the difference; do not adjust the expected values.
- Each knob changes the recorded rule hash, and a round that changes two knobs, or sets an invalid value (k1 not above 0, b outside 0 to 1, unknown `stem` or `levels`), is refused.
- A fixture where `murders` in the query matches `murder` in a provision only under `stem=suffix`, and a second where a sub-provision-only term is found under `levels=all` and `levels=leaf` but the section is retrieved by its own text under `levels=top`.
- Two identical runs are byte-identical, ties still break by citation string.
- Speed is measured and reported, not assumed: seconds to score the full dev split and the first 5,000 train cases by sorted id, on the real data. If a train plus dev round would take more than 10 minutes, report the number and propose a declared train subsample for the owner to approve. Do not subsample silently.
- No file under `data/raw/` is added to git, and the existing suite still passes.
