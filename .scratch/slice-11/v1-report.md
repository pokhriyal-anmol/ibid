# Slice 11 v1 report

## Status

Built. All five tickets are done and every one of the spec's 11 user stories has a done ticket. Code review found 6 issues, all fixed, none left open. The work is on branch `feat/slice-11`, with the PR text in `.scratch/slice-11/pr.md`.

## What v1 does

The MCP `search` tool gets an optional `mode`. The default is `keyword` and behaves as before. With `mode: "learned"` the server asks the `assoc-nb v3` model for the top 5 IPC sections for the raw query. It adds their verified BNS counterparts from Concordance v3 and returns each with its heading and verbatim text. The result carries the layer name, version, model hash and a fixed caveat.

The model file is read on the first learned call, not at startup. If it is missing, unreadable or the wrong layer or version, the call returns a tool error that names the file and the fit command, and keyword search keeps working. An unknown mode is a tool error. A `limit` above 5 is clamped and the result says so. `adjacent` is ignored in learned mode with a note.

The tool descriptions and the caveat state the measured limits: keyword search finds about 5 percent of charges on story-style queries, and learned mode covers 140 IPC sections and is not legal advice. A test reads the figures from `results/layer-comparison.md`. `ibid setup` prints an optional model line and never fails because of it. The README says the model is a research option, since the training data are gated and non-commercial.

## How to run it

```bash
uv sync
uv run ibid setup
uv run python -m unittest discover -s tests
```

To use learned mode you first fit the model yourself: `ibid assoc fit --source union`. It is written to `data/assoc-nb-v3.json`, which is the default for `--assoc-model` on `ibid mcp`. `uv run ibid setup` prints the `claude mcp add` line for this machine.

## Tests

The suite ran green after the review fixes. Each fix was checked: the new wrong-type-model test fails with the fix removed. I have no separate count to report. The real-model checks (story 5 and the real-model limits check) need the model file and are skipped with a message when it is absent.

## What I assumed for you

- Q-006: default taken. The tool text quotes per-set IPC ranges from the baseline rows (3.1 to 5.1 percent on set v1, 4.8 to 6.0 percent on set v2), not the spec's single "about 5 percent".

## Held back

Nothing. No ticket failed or was left unbuilt.

## Your questions

1 pending, 0 blocking. That is below the batch size of 8, so none are asked yet. The work carries on without them.
