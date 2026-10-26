# With the real model present, learned top-5 matches the committed v2 predictions

Status: done
Blocked by: 01

## What to build
A test that, when the real `data/assoc-nb-v3.json` exists, starts the MCP server with it, sends three items of Multi-charge set v2 as raw queries in learned mode, and compares the returned IPC citations and order with `results/layers/assoc-nb-v3-multicharge-v2-predictions.json`. When the model file is absent the test is skipped with a message naming the file and how to produce it.

## User stories
5.

## Acceptance criteria
- [ ] With the model present, the three items' learned IPC top-5 equal the committed predictions, in order.
- [ ] The test asserts the server's `model_sha256` equals the model hash recorded in the predictions file or `results/layers/assoc-nb-v3.ledger.json`, so a different model cannot pass.
- [ ] With the model absent, `unittest` reports the test as skipped with a message naming `data/assoc-nb-v3.json`, not as passed.
- [ ] Known-bad run seen failing once: swapping two expected citations fails the test.
- [ ] The predictions file is unchanged.
