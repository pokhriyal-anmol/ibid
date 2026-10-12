# Route B: a learned term-to-section association as an opt-in layer

Status: ready-for-agent
Blocked by: 06

What to build: a multinomial naive-Bayes classifier over the 100 ILSI labels, fitted from the train split with the standard library only (ADR 0002), as an opt-in layer that reports its own predictions file (ticket 06 format, layer `assoc-nb`). It is the first thing in Ibid that uses learned weights. It is not part of the baseline, and ADR 0001 requires it to beat the baseline on the gold set and report its own evidence packet separately.

Write ADR 0005, "A learned association layer is allowed as an opt-in, and never in the baseline". It records: what is learned (term counts per label), from which data (ILSI train fact text and labels, minus the held-out ids), that the artefact is a file with a recorded hash, that a prediction is a deterministic function of the query and that file, and that the baseline path stays untouched.

Fixed design, declared here before any score exists:

- Tokenisation: lower-case, letters only, the 44 base stop words. No stemming.
- Model: multinomial naive Bayes with add-one smoothing and class priors from the training label frequencies. Multi-label output: rank the 100 labels by log posterior and return the top 5 (k=5, as the frozen baseline). No threshold tuning.
- Training data: the ILSI train split minus the 30 item ids of `gold/multicharge/v1.json`. A test asserts those ids are absent.
- Outputs: IPC citations only for the 100 labels, then the BNS counterparts from verified concordance entries only, so the BNS side is thin by construction and the results say so.
- Artefact: `data/assoc-nb-v1.json` holds the vocabulary, the counts and a header with the split hash, the held-out ids hash and the code version, and its SHA-256 is written into every predictions file.

Commands: `ibid assoc fit --train <train.jsonl> --holdout-set <set.json> --out <model.json>`, `ibid assoc predict --model <model.json> --set <set.json> --concordance <file> --out <predictions.json>`, and `ibid assoc eval --model <model.json> --split <dev.jsonl>` which scores a split with the benchmark's own micro-F1, macro-F1 and Jaccard through the existing scorer code.

User stories: 4, 5, 6, 8.

Acceptance criteria:
- On a fixture split the model's counts equal hand-computed counts, and a query made of a label's distinctive words ranks that label first.
- Known-bad: a fixture where a held-out id is present in the training file is dropped from fitting and counted, and a mutated version that keeps it is seen failing the test.
- Two fits on the same input are byte-identical, and a changed training byte changes the artefact hash.
- No model or network call anywhere in the layer (stdlib imports only, checked by a test of the imports).
- Run by the orchestrator after the merge: fit on the real train split minus the 30 ids; report ILSI dev micro-F1, macro-F1 and Jaccard next to the baseline's; score ILSI test once with a new ledger entry for this layer and report it next to the baseline's 9.64 micro and 6.21 macro; score set v1 once through ticket 06 on both Acts.
- ILSI test scoring of this layer is guarded once-only like the baseline's, with its own ledger (`results/test-ledger-assoc.json`) keyed by layer, layer version and the pinned test-file hash. The baseline's ledger and its once-only guard are untouched, and a second scoring of this layer needs the same explicit flag.
- ADR 0005 is committed, and `docs/research/legal-retrieval-literature.md` links to it.
