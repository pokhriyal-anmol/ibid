# Slice 4 v1 report

## Status

Built. All 4 tickets are done and every one of the spec's 9 user stories has a done ticket, so no story is uncovered. The review pass fixed 2 findings and left none open.

## What v1 does

`ibid mcp` starts a stdio MCP server so a chat client or agent can ask Ibid for text and citations. It builds the index from the IPC and BNS PDFs on start and loads one Concordance file. It exposes four read-only tools, each a thin call into existing code with no model, no query rewrite and no embedding.

- `get_provision` takes an exact Citation and returns the verbatim text and child Citations. An unknown Citation is a tool error, never a near match.
- `search` takes a raw query and returns up to `limit` (default 10) ranked Provisions, in the order `index.search` gives. A query that is not valid FTS5 returns an empty list.
- `cross_references` returns the resolved chain in stored order plus unresolved references for that Provision with their reason.
- `concordance` takes a Citation and a direction (`ipc_to_bns` or `bns_to_ipc`) and returns verified entries only, or `no verified concordance`.

An unknown tool, a missing argument or a malformed JSON-RPC line gets a JSON-RPC error and the server keeps running. A missing PDF or Concordance file exits non-zero with a message on stderr. Only protocol messages go to stdout.

## How to run it

```bash
uv sync
export IBID_BNS_PDF=<root>/data/raw/bns-prs.pdf IBID_IPC_PDF=<root>/data/raw/ipc-wipo.pdf
uv run ibid mcp
```

Flags: `--bns`, `--ipc`, `--concordance` (default `concordance/v3.json`).

Tests:

```bash
uv run python -m unittest discover -s tests
```

## Tests

Green, per the build and review runs. The report does not claim more than that.

## What I assumed for you

No questions were queued, so no guesses were made on your behalf. One question was settled from the spec rather than asked: the default Concordance file for `ibid mcp` is `concordance/v3.json`, taken from decision 2 of the approved spec. Your handoff text did not name a version, and v2 appears only in an eval example. `--concordance concordance/v2.json` still works, and it is a one-line default to change.

## Held back

Nothing. No ticket was left unbuilt or failed.

## Your questions

0 pending, 0 blocking. That is below the batch size of 8, so none are asked yet; the work carries on without them.
