## Summary

Ibid could only be queried through `ibid eval` and its siblings, which are built for scoring. This slice adds `ibid mcp`, a stdio MCP server over the existing deterministic lookups, so a chat client or agent can ask for a Provision, a keyword hit list, a Cross-reference chain or a Concordance entry.

The server is in `src/ibid/mcp.py`, with a new `mcp` subparser in `src/ibid/cli.py`. It uses the standard library only (newline-delimited JSON-RPC 2.0 on stdin/stdout), as ADR 0002 requires. On start it parses both Acts, checks section counts as `ibid eval` does, builds the index into a temp file and loads one Concordance file. Startup messages go to stderr, never stdout. A missing PDF, a section-count mismatch or a bad Concordance file exits non-zero with one line on stderr.

Four read-only tools, each a thin call into existing code:

- `get_provision {citation}` returns verbatim text and child Citations from `index.lookup`. A Citation not in the index is an `isError` result, never a near match.
- `search {query, limit?}` passes the raw query unchanged to `index.search` (default limit 10). An invalid FTS5 query returns an empty list.
- `cross_references {citation}` returns the resolved Cross-reference chain in stored order plus the unresolved references for that Provision with their reason.
- `concordance {citation, direction}` returns verified entries from `concordance.lookup`, or `no verified concordance`. Direction is `ipc_to_bns` or `bns_to_ipc`.

No model, query rewrite or embedding is in the tool path, consistent with ADR 0001 and ADR 0004. Nothing under `gold/` or `concordance/` changed. No ADR is contradicted.

One default to confirm: `--concordance` defaults to `concordance/v3.json`, the newest pinned file and the one slice 3 scored with. The owner's handoff named v2. It is a one-line flag default, and `--concordance concordance/v2.json` works either way.

Review found two issues, both fixed in this branch: an unreachable "not implemented" guard left in `call_tool`, deleted, and the direction enum validated in two places, now a single `DIRECTIONS` tuple used by both the schema and the membership check.

## Test plan

- [x] `uv run python -m unittest discover -s tests`: Ran 214 tests in 33.729s, OK.
- [x] Server tests drive the tool calls through a subprocess `ibid mcp` over stdio, with expected values taken from `index` and `concordance` on the test's own index.
- [x] Review findings: 2 confirmed, 2 fixed, 0 unfixed.
