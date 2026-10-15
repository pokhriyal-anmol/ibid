# Slice 5 v1 report

## Status

Built. All 9 user stories have a done ticket (tickets 1, 2 and 3 are done, none failed), and the tests are green.

## What v1 does

Three fixes to the `ibid mcp` server, prompted by gaps a real client hit.

A `concordance` call for a sub-provision such as `BNS 318(4)` now falls back to its section (`BNS 318`) when the sub-provision has no verified entry. The result carries a `via` field naming the section. If the section has no entry either, the answer is `no verified concordance`, not an error. A section Citation behaves as before.

`concordance` no longer needs `direction`. It is inferred from the prefix (`IPC` means `ipc_to_bns`, `BNS` means `bns_to_ipc`). A direction that contradicts the prefix is a tool error naming the conflict.

`search` takes an optional `adjacent: true`. Each hit then lists the previous and next section of the same Act with a heading. Ranking and hit order are unchanged. This makes IPC 405 visible next to IPC 406 for "criminal breach of trust". Review also found and fixed a bug where nested sub-provisions (e.g. IPC 376(2)(a)) got their own section as previous.

## How to run it

```bash
uv sync
uv run ibid mcp
uv run python -m unittest discover -s tests
```

The README does not mention `mcp`. The `ibid mcp` command comes from the spec and the PDFs must be reachable as described in AGENTS.md (`IBID_BNS_PDF`, `IBID_IPC_PDF`).

## Tests

`uv run python -m unittest discover -s tests`: Ran 226 tests in 33.097s, OK. The new tests were each seen failing against known-bad behaviour, including the sub-provision neighbour test against the old `index.py`.

## What I assumed for you

Q-001: default taken, a BNS neighbour's heading is the first line of the section text cut at the first em dash, capped at 100 characters. For most BNS sections this reads as a truncated opening sentence, not a title.

Also settled as craft, not queued: the fallback field is named `via`.

## Held back

Nothing. All three tickets were built.

## Your questions

1 pending, 0 blocking. That is below the batch size of 8, so none are asked yet; the work carries on without them. Q-001 is at `.scratch/_owner/questions/Q-001.md`.
