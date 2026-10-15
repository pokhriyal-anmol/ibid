# MCP search tool over index.search with the raw query

Status: done
Blocked by: 01

## What to build

Implement `search {query, limit?}` in `src/ibid/mcp.py`. It passes the query string unchanged to `index.search(db, query, limit)`, `limit` defaulting to 10 (an integer of at least 1; anything else is a -32602 error). The result is the ranked list of `{citation, text}` in the order `index.search` returns. A query that is not valid FTS5 syntax returns an empty list, not an error, because `index.search` already returns `[]` for it. No rewrite, no tokenising, no model (ADR 0001, ADR 0004). The input schema already declared in ticket 1 stays as is unless it was wrong.

## User stories

4, 5.

## Acceptance criteria

- [ ] Through the harness, `search` for at least two real queries returns citations and texts equal, in order, to `index.search` on the test's own index, with the default limit and with an explicit `limit`.
- [ ] `search` with an invalid FTS5 query (for example `"murder AND`) returns an empty list and `isError` is not set.
- [ ] `search` with a missing `query` or a `limit` of 0 returns a JSON-RPC error and the server keeps running.
- [ ] The tests were each run once against a known-bad server that lowercases or strips the query, and once against one that reverses the order, and seen to fail.
- [ ] Full test suite passes.
