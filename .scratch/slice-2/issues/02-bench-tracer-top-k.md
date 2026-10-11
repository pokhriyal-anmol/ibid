# Tracer: one bench run command scores a split with query rule v1 and top-k

Status: needs-triage
Blocked by: 01

What to build: the end-to-end path through one run command (for example `ibid bench run --split <path> --index <index> --k <k> --out <results.json>`). It loads a split JSONL from a local path (`id`, `text` as a list of sentences, `labels`), joins the sentences into the raw query, applies query rule v1 (ADR 0004: lower-case, split on non-letters, drop a fixed stop-word list, join with OR), retrieves IPC provisions with the existing FTS5 index, rolls each retrieved provision up to its top-level IPC section citation, keeps the top k sections, and scores micro F1, macro F1 and Jaccard over the 100-label space with our own implementation. The results file records each input file's SHA-256, the rule name and version, a hash of the rule's parameters, the parser version, k, and the scores.

User stories: 1, 2, 3, 4, 5 (top-k half), 6, 10.

Acceptance criteria (tested through the run command on a tiny invented fixture split and fixture index, never benchmark text):
- Fixture predictions and scores match hand-computed micro F1, macro F1 and Jaccard.
- A sub-provision hit (for example a clause of a section) is predicted as its section label.
- A fact paragraph with quotes, hyphens and punctuation returns hits (the ADR 0004 failure no longer happens).
- Two runs with the same rule, data and k produce byte-identical results files.
- Changing one stop word or any rule parameter changes the recorded rule hash (known-bad).
- A corrupted label file (labels shuffled across cases) lowers the score (known-bad).
- No model, embedding or label-derived weight is in the path.
