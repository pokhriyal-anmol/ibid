# Slice 10: ibid setup for a clean machine

## Summary

Until now only the author could run Ibid. The README told users to fetch the source PDFs by hand, check hashes by hand and export two environment variables, and a missing tool or PDF failed late with an unhelpful message. This slice adds one command, `ibid setup`, that checks everything the product needs and prints the next action for each gap.

Five tickets are built, all marked done.

- Offline checklist (ticket 1). `data/sources.json` records the URL, byte size, SHA-256 and expected section count for the BNS and IPC source PDFs. `ibid setup` makes no network call by default. It reports each poppler tool (`pdftotext`, `pdftohtml`, `pdfseparate`, `pdfunite`), each PDF's presence and each PDF's hash, with the install command or URL and target path after each failure. A PDF whose hash differs is reported with both hashes and left untouched. A test keeps the hashes in `data/sources.json` equal to those in `data/SOURCES.md`.
- Parse proof and MCP line (ticket 2). When every check passes, setup parses both Acts and prints the section counts (`BNS 358 sections, IPC 575 sections`), then the `claude mcp add ibid -- ...` line with absolute paths. A wrong count fails the run. If an earlier check failed, the parse step is reported as not run.
- Verified fetch (ticket 3). `ibid setup --fetch bns` downloads from the manifest URL. `ibid setup --fetch ipc --url <url>` uses a user-supplied URL, because the WIPO link is signed and expires. Only `https://`, `http://127.0.0.1` and `http://localhost` are accepted. The download streams to a temporary file, is checked against the 200 MB cap (or a smaller manifest size) and the SHA-256, and only then renamed into place. An existing file is never overwritten.
- Missing-PDF messages (ticket 4). Commands that take `--bns` or `--ipc` print one `error: no such file: <path>` line plus `run: ibid setup` and exit non-zero, through one shared check.
- README (ticket 5). The Quickstart is replaced by the real sequence: `uv sync`, `uv run ibid setup --fetch bns`, the IPC step with its explanation, then `uv run ibid setup`. `AGENTS.md` and `data/SOURCES.md` are updated to match.

No ADR is contradicted. Setup does not touch retrieval (ADR 0001), and it uses the standard library only (`urllib.request`, `shutil`, `hashlib`), as ADR 0002 requires. Parsing, the index, gold sets, concordance, pins and the baseline are out of scope and unchanged.

Review fixes applied in this branch:

- The HTTP-error test now asserts "404", so a refused connection no longer satisfies it.
- The no-model import test scans `setup.py` again. `setup.py` may import `urllib`, `http` and `socket` but not the model packages. A known-bad case where `setup.py` imports `openai` was added.
- Added `test_cap_applies_when_manifest_size_is_larger` (cap patched to 10, manifest 1000 bytes, body 50). Mutating the code to ignore the cap made it fail, and the mutation was then reverted.
- Removed the unused `fetchable` keys from `data/sources.json`.

## Test plan

- [x] `uv run python -m unittest discover -s tests` ran green: 314 tests in 42.101s, OK.
- [x] Review confirmed 4 findings, all fixed, none left unfixed.
- [x] The cap test was seen failing against known-bad code (cap ignored) before being reported green.
- [x] The no-model import test has a known-bad case (`setup.py` importing `openai`).
- [x] Fetch tests run against a local `http.server` on 127.0.0.1 for the correct body, wrong hash, truncated body, oversized body, existing target file, non-local `http://` and `file://` URLs, and `--fetch ipc` without `--url`.
