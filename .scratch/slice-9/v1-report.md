# Slice 9 v1 report

## Status

Built. All 6 tickets are done, none failed or held, and every one of the 7 user stories is covered by at least one done ticket. The review confirmed 10 findings and fixed all of them.

## What v1 does

It adds a third version of the learned association layer, assoc-nb v3, fitted on both the ILSI judgment text and the ILSIC-Lay posts together. `ibid assoc fit` writes the model with a header giving each source's file hash, examples used and dropped, the section threshold and the vocabulary size. A test checks that no held-out id from sets v1 and v2, the Layman test posts, or the ILSI test and dev cases is in the training data.

`ibid assoc predict` writes v3 predictions for sets v1 and v2, and `ibid charges score --predictions` scores each once per Act and refuses a second scoring. v3 was scored once on the ILSI test split. `results/layer-comparison.md` now shows baseline, v1, v2 and v3 side by side. ADR 0008 holds the decision rule with five thresholds. `.scratch/slice-9/v3-report.md` applies it. The baseline, the frozen rule and the pinned files are untouched.

Result: the report says v3 is kept, all five comparisons pass. ILSI test micro-F1 is 35.2 in v3's own 140-label space and 33.3 in v1's 100-label space. The floor is 33.4. See Q-005 below, because the verdict depends on which space is used.

## How to run it

```bash
uv sync
export IBID_BNS_PDF=<root>/data/raw/bns-prs.pdf IBID_IPC_PDF=<root>/data/raw/ipc-wipo.pdf

uv run python -m unittest discover -s tests
uv run ibid eval --gold gold/v2.json --concordance concordance/v2.json --out results/run.json
```

The slice commands are `ibid assoc fit`, `ibid assoc predict`, `ibid assoc eval`, `ibid charges score --predictions` and `ibid charges compare`. Pass `--ledger results/layers/assoc-nb-v3.ledger.json` to the scoring commands, or the once-only guard is bypassed. Exact arguments are in each ticket's notes under `.scratch/slice-9/issues/`.

## Tests

The full unittest suite passed after the review fixes. Each new test was run once against known-bad input in the review (for example, the ADR threshold test failed when a 15.3 row was changed to 16.3).

## What I assumed for you

- Q-005: v3's own label space is used for the 33.4 micro-F1 floor, with the figure over v1's label space recorded beside it. This is the only pending question and it is not blocking.

Other guesses (ledger location, results-name version check, test file name, the in-distribution caveat) were treated as craft and decided without queueing.

## Held back

Nothing. No ticket was left unbuilt.

## Your questions

1 pending, 0 blocking. That is below the batch size of 8, so none are asked yet; the work carries on without them.

Q-005 is the one to watch: judged over v3's own space the verdict is kept (35.2), judged over v1's space it is negative (33.3 against 33.4). Both figures come from the single test run, so changing the answer needs no rerun. It also asks whether a sixth gate was intended, since the spec says six comparisons but lists five.
