# 0011: The MCP search tool explains an empty result

Status: accepted (owner, 2026-11-17)

`index.search` returned `[]` for a query that is not valid FTS5 syntax (a trailing `?`, a stray quote) and for a query no section matches in full. A person asking "what is the punishment for murder?" got no hits and no warning.

`ibid mcp` now calls `index.search_explained`. A query that raises an FTS5 syntax error is retried once with each word (letters, digits, underscore) in double quotes, still joined by FTS5's implicit AND, and the result carries `searched_as` with the string that ran. An empty result carries `notice`. Responses with hits and no retry are byte-identical to before.

**Unchanged:** `index.search`, which `ibid eval`, `conform` and the baseline use, is untouched, so no score, pin or results file moves. No model, no stop-word list, no OR, no synonym step ([ADR 0001](0001-retrieval-independent-of-the-model.md), [ADR 0004](0004-fixed-tokenisation-of-the-raw-query.md)). A query that is valid FTS5 is passed as typed.

**Cost:** the MCP surface can now search a string that is not byte-for-byte what the user typed. `searched_as` names it in the response. A multi-word question can still return nothing, because every word must match: the notice says so rather than hiding it.
