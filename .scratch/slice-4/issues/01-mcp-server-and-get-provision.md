# ibid mcp: stdio JSON-RPC server, startup checks, get_provision tool

Status: done
Blocked by: none

## What to build

A new `mcp` subparser in `src/ibid/cli.py` and the server in `src/ibid/mcp.py`, standard library only (ADR 0002). Flags `--bns`, `--ipc` (same defaults as `ibid eval`, `IBID_BNS_PDF` / `IBID_IPC_PDF`) and `--concordance` (default `concordance/v3.json`). On start it parses both Acts, checks the section counts as `run_eval` does, builds the index into a temp file with `index.build`, and loads the Concordance with `concordance.load`. None of the `ibid eval` progress lines go to stdout; any startup message goes to stderr. A missing PDF, a section-count mismatch, a missing Concordance file or a `ValueError` from `concordance.load` exits non-zero with one clear line on stderr.

Then it reads newline-delimited JSON-RPC 2.0 from stdin and writes one response per line to stdout. Methods: `initialize` (result has `protocolVersion`, `serverInfo`, `capabilities.tools`), `notifications/initialized` (no response), `ping`, `tools/list`, `tools/call`. `tools/list` returns exactly four tools, `get_provision`, `search`, `cross_references`, `concordance`, each with an `inputSchema` (JSON Schema, required arguments listed). This ticket implements only `get_provision`; the other three return a tool error `not implemented` until tickets 2 to 4 land, so those tickets can build in parallel without touching the list.

`get_provision {citation}` calls `index.lookup` and returns the verbatim text and the child Citations unchanged. A Citation not in the index returns a tool result with `isError: true` saying the Citation is not in the index, never a near match.

Protocol errors: a malformed JSON line gets a JSON-RPC parse error (-32700), an unknown method -32601, an unknown tool name or a missing or wrongly typed argument -32602. After any error the server keeps reading.

Also build the test harness every later ticket uses: a helper in `tests/` that starts `uv run ibid mcp` (or `python -m ibid.cli mcp`) as a subprocess with the PDF env vars resolved the way `tests/pdfs.py` does, sends JSON-RPC lines, reads responses. Start the server once per test class, since the index build takes seconds. Expected values come from `index.lookup` on an index the test builds itself from the same PDFs.

## User stories

1, 2, 3, 8, 9 (and the protocol part of every other story).

## Acceptance criteria

- [ ] `initialize` returns a result with `capabilities.tools`; `tools/list` returns exactly the four names above, each with an `inputSchema` of type object.
- [ ] `get_provision` for `BNS 103` and for one IPC Citation and one sub-provision Citation returns text and children equal byte for byte to `index.lookup` on the test's own index.
- [ ] `get_provision` for a Citation not in the index (for example `BNS 9999`, and `bns 103` in the wrong case) returns `isError: true` and no text.
- [ ] A malformed line, an unknown method, an unknown tool and a missing `citation` each return a JSON-RPC error with the right code, and a following `ping` still succeeds on the same process.
- [ ] Every line the server writes to stdout parses as a JSON-RPC message, including during startup.
- [ ] `ibid mcp --bns /no/such.pdf` and `ibid mcp --concordance /no/such.json` exit non-zero with a message on stderr and nothing on stdout.
- [ ] Each test was run once against a known-bad server (for example one that returns the nearest Citation, or prints a progress line to stdout) and seen to fail; the failure names the assertion written.
- [ ] No new dependency; `uv run python -m unittest discover -s tests` passes.

## Default taken

The `--concordance` default is `concordance/v3.json`, the newest pinned file and the one slice 3 scored with. The owner's handoff named v2. This is a one-line flag default, so the builder uses v3 and the owner can switch it to v2 later; `--concordance concordance/v2.json` works either way.
