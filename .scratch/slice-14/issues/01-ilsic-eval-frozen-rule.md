# ibid ilsic eval scores the frozen rule on an ILSIC split under both readings

Status: done
Blocked by: none

What to build: a new `ibid ilsic eval` subcommand (in `src/ibid/cli.py`, logic in a new `src/ibid/ilsic.py`) that reads an ILSIC split (`.jsonl.xz`, rows with `instruction` and `answer`) and the Lay train file, builds the label space as every statute string in the Lay train and test answers, parses each row's gold labels (all statutes in the answer, other Acts included), runs the frozen rule v2.11 on the raw `instruction` only, maps its IPC predictions to the ILSIC statute strings ("Section N of The Indian Penal Code, 1860"), and writes a results file. Primary reading: macro-F1 over the whole label space with 0 for a label with no gold and no prediction (reuse `bench.score` / `bench.label_counts`), micro-F1 pooled, macro precision and recall; a gold label the layer cannot predict counts as a miss. Secondary reading: the same scores over the labels the layer can predict, in a separate block, never substituted. The results file records layer name, version, rule hash, split file sha256, label-space size and states the zero-label assumption in words. No network, no model call.

User stories: 1 (frozen rule part), 2, 5.

Acceptance criteria:
- Invented fixtures under `tests/fixtures/ilsic/`: a handful of queries, three Acts, one gold label from another Act no layer can predict, one label in the space with no gold.
- A `unittest` through the `ibid ilsic eval` command asserts macro-F1, micro-F1, macro P and R and label-space size equal hand-computed values for both readings.
- Seen to fail once against known-bad input: the other-Act label dropped from the label space, and a no-gold label counted as F1 = 1.
- The frozen rule receives the raw query string unchanged (ADR 0001); no import of a network or model client.
- Existing tests still pass: `uv run python -m unittest discover -s tests`.

## Default taken

Primary reading is the spec's: label space is every statute string in the Lay train and test answers, other-Act gold labels count as misses, and a label with no gold and no prediction scores F1 = 0 in the macro mean (the `bench.py` convention). The vocabulary-only reading is reported separately and never substituted. The owner may revise this; it changes only how scores are computed and reported.
