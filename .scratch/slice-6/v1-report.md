# Slice 6 v1 report

## Status

Built. All 7 tickets are done and every one of the spec's 8 user stories has a done ticket, so no story is uncovered. The branch is `feat/slice-6`, the review fixed 4 findings and left none open, and the PR text is in `.scratch/slice-6/pr.md`.

## What v1 does

It adds `assoc-nb v2`, a new version of the learned association layer. The method is the same as v1 (term counts per section, naive-Bayes ranking, k=5, no model call), but it is fitted on 6,465 layperson forum posts (the ILSIC-Lay train split) instead of court judgments. It stays opt-in and out of the baseline.

The fit keeps IPC sections that occur in at least 5 posts, drops train posts whose text equals a Layman test split post, and refuses to run if a set v2 post is in the training data. The scorer now refuses to score the same layer version twice on the same set and Act, unless `--rescore` is passed. The comparison report adds two caveats: forum labels are incomplete, and a layer fitted on the same corpus as the set is scored in-distribution.

On set v2 the v2 vocabulary names 27 of 30 cited IPC sections. IPC recall rises from 39.3% to 54.8%, but the whole gain is on charges whose section v1 could already name (49.3% to 68.7%). The 17 charges on sections v1 could not name are still all missed. Near-duplicate posts between train and the Layman test split are not detected, only exact matches after whitespace and case folding. No lawyer reviewed the forum labels, so this is not a claim of legal accuracy.

## How to run it

From the README:

```bash
uv sync
uv run ibid eval --gold gold/v2.json --concordance concordance/v2.json --out results/run.json
uv run python -m unittest discover -s tests
```

The README does not list the slice 6 commands. Their options are from `--help` and ticket 6 (the Layman test file path and the `--labels` option for fit are not confirmed here):

```bash
uv run ibid assoc fit --source ilsic-lay --train data/raw/ilsic/FT-Layman-train.jsonl.xz --holdout-split data/raw/ilsic/FT-Layman-test.jsonl.xz --holdout-set gold/multicharge/v2.json --min-posts 5 --out data/assoc-nb-v2.json
uv run ibid assoc predict --model data/assoc-nb-v2.json --set gold/multicharge/v2.json --concordance concordance/v3.json --out results/layers/assoc-nb-v2-multicharge-v2-predictions.json
uv run ibid charges score --set gold/multicharge/v2.json --predictions results/layers/assoc-nb-v2-multicharge-v2-predictions.json --act ipc --out results/multicharge-v2-assoc-v2-ipc.json
```

Repeat predict and score for `gold/multicharge/v1.json` and for `--act bns`. The results are already generated and in `results/layer-comparison.md`.

## Tests

`uv run python -m unittest discover -s tests` passed after the review fixes (green). The PR text records 234 tests, OK, in 33 s. Each new test was run once against known-bad input.

## What I assumed for you

Q-002: ILSIC-Lay train only, no ILSI text added, and a minimum of 5 posts per section.

## Held back

Nothing. No ticket failed or was left unbuilt.

## Your questions

1 pending (Q-002), 0 blocking. That is below the batch size of 8, so none are asked yet and the work carries on without them. If you answer differently, a lower threshold is a refit as `assoc-nb v3` with no code change. Adding ILSI text needs a code change in `src/ibid/assoc.py` and an ADR 0006 amendment.
