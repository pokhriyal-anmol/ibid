# Deterministic keyword search over the same index

Status: done
Blocked by: 02

## What to build
Keyword search over provisions using SQLite FTS5 in the same index file. It takes the raw query only (ADR 0001) and returns provisions in a fully determined order (ties broken by citation), so the evidence packet for a raw query is byte-identical every time. Add a few keyword items to the draft gold file.

## User stories
14, 15

## Acceptance criteria
- [ ] Through `ibid eval`, a keyword item returns an ordered list of provisions with citations and verbatim text, scored by exact match on the expected provisions.
- [ ] The same raw query returns a byte-identical result across runs and across an index rebuild from source.
- [ ] Equal-score results have a stable tie-break. Seen failing once: removing the tie-break produces a detectable ordering difference or the check is shown able to fail.
- [ ] No query rewriting or expansion happens before search.
