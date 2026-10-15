# MCP cross_references tool with resolved chain and unresolved references

Status: done
Blocked by: 01

## What to build

Implement `cross_references {citation}` in `src/ibid/mcp.py`. It returns the resolved Cross-reference chain from `index.lookup` (third element) in its stored order, and the unresolved references whose `source` equals the Citation, taken from `index.unresolved` in its order, each with `matched` and `reason`. A Citation not in the index returns `isError: true`, the same as `get_provision`. No change to `index.py` is needed; filtering `index.unresolved` in the server is enough.

## User stories

6.

## Acceptance criteria

- [ ] For a Provision with resolved Cross-references (pick one from the index in the test), the returned chain equals `index.lookup(db, c)[2]` in order.
- [ ] For a Provision that has at least one unresolved reference (pick the first `source` from `index.unresolved` in the test), the unresolved list equals the filtered `index.unresolved` entries with their `reason`.
- [ ] A Provision with neither returns two empty lists, and a Citation not in the index returns `isError: true`.
- [ ] The tests were each run once against a known-bad server (one that sorts the chain, or drops unresolved references) and seen to fail.
- [ ] Full test suite passes.
