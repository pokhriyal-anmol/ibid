# MCP concordance tool returning verified entries only

Status: done
Blocked by: 01

## What to build

Implement `concordance {citation, direction}` in `src/ibid/mcp.py`. `direction` is `ipc_to_bns` or `bns_to_ipc` (an enum in the schema; any other value is a -32602 error). It maps to `concordance.lookup(entries, citation, src, dst)` on the entries loaded at startup and returns its result unchanged: the list of `{type, citations}` for verified entries, or the string `no verified concordance`. Unverified entries are never returned, which `concordance.lookup` already guarantees.

## User stories

7.

## Acceptance criteria

- [ ] For one `ipc_to_bns` and one `bns_to_ipc` Citation with verified entries in the loaded Concordance file, the result equals `concordance.lookup` on the same file and the test's own index.
- [ ] For a Citation whose only entries are unverified (pick one from the file in the test; if the default file has none, start the server with `--concordance` pointing at a small fixture under `tests/fixtures/` that has one), the result is `no verified concordance`.
- [ ] A missing `direction` or an unknown value returns a JSON-RPC error and the server keeps running.
- [ ] The tests were each run once against a known-bad server that ignores the `verified` flag, and one that swaps the direction, and seen to fail.
- [ ] No file under `concordance/` or `gold/` is changed. Full test suite passes.
