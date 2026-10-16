# `ibid assoc fit` fits assoc-nb v2 on the ILSIC-Lay train file with the Layman test split held out

Status: done
Blocked by: none

What to build: extend `ibid assoc fit` (`src/ibid/assoc.py`, `src/ibid/cli.py`) to accept an ILSIC-Lay file (`.jsonl` or `.jsonl.xz`, read with stdlib `lzma`; rows have `instruction` and `answer` only, no id). Default CLI shape: `ibid assoc fit --source ilsic-lay --train <train.jsonl.xz> --holdout-split <FT-Layman-test.jsonl.xz> --holdout-set gold/multicharge/v2.json --min-posts 5 --out data/assoc-nb-v2.json`. The existing ILSI path (`--labels`, default source) keeps writing `assoc-nb v1` byte-identically.

Labels: from `answer`, IPC Citations only (the `Section N of The Indian Penal Code, 1860` form), IPC 34, 149 and 120B excluded, a section counted once per post, and a Citation absent from the index dropped and counted (the set v2 rule from slice 3 ticket 12). Other Acts are counted and dropped. Vocabulary: IPC sections with at least `--min-posts` train posts. A post with no offence section, or none in the vocabulary, is dropped and counted. Held out: every train post whose instruction text, after the same whitespace and case folding, equals a Layman test split post is dropped and counted; the fit refuses (exit 1) if any set v2 item's source row is not in the holdout split file. Train rows get ids `ilsic-lay-train-<row>` for the record.

Method, tokenisation (`assoc.tokens`), smoothing and k=5 are v1's and unchanged. The model header carries: layer `assoc-nb`, layer_version `v2`, train SHA-256, holdout split SHA-256, min_posts, posts read, posts fitted, posts dropped by reason (held out, no offence section, none above threshold), other-Act citations dropped, vocabulary size, tokenisation string. `.gitignore` gains `data/assoc-nb-v2.json`.

User stories: 1, 2, 7.

Acceptance criteria (through `ibid assoc fit` in `tests/test_assoc.py`, fixtures are invented posts in ILSIC-Lay shape under `tests/fixtures/`):
- Header counts equal hand-computed counts on the fixture, including each drop reason and the threshold cut.
- A fixture train post identical to a holdout-split post is absent from the counts. Known-bad run, observed once: a fit with holdout filtering disabled makes this test fail on the assertion that names the held-out post.
- IPC 34/149/120B and a non-IPC Act in `answer` never become labels.
- Two fits of the same inputs are byte-identical; one changed training byte changes `train_sha256`.
- The existing v1 fit test still passes and the v1 model on the fixture is byte-identical to before.
- The existing stdlib-only import test covers the new code (still only stdlib and `ibid`); observe it fail once with a non-stdlib import added.

## Default taken

The owner has not chosen the training data or the section threshold (spec decisions 1 and 2). Build with the spec defaults: the ILSIC-Lay train split only (no ILSI text added) and `--min-posts 5`. Both are CLI inputs to `ibid assoc fit`, so a different choice is a refit and a new layer version, not a code change.
