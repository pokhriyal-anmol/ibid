# ibid setup checks the three slice 15 source files offline

Status: done
Blocked by: none

What to build: add three entries to `data/sources.json` for `bnss-prs.pdf`, `crpc-indiacode.pdf` and `capt/comparison_summary_BNSS_to_CrPC.pdf`, with bytes and SHA-256 copied from `data/SOURCES.md` and reuse terms recorded as "unconfirmed" (the table also notes the copyright line; D-007). Plain `ibid setup` reports presence, size and hash for each, offline, alongside the IPC and BNS entries. `ibid setup --fetch <name>` works for an entry only because its hash is recorded, and refuses a download whose hash differs. Nothing is downloaded by the build or the tests. `data/SOURCES.md` is updated only if a figure in it is wrong.

User stories: 2.

Acceptance criteria:
- A `unittest` through `ibid setup` (env vars or a temp dir pointing at invented files) shows each of the three entries as present with the right size and hash, and as missing when the file is absent, with no network access.
- A `unittest` through `ibid setup --fetch` with a stubbed local source shows a file with the wrong hash is rejected and not left in `data/raw/`.
- Seen to fail once against known-bad input: a wrong hash in the fixture is reported as a mismatch, not as OK.
- Run against the real main checkout, `ibid setup` reports all three files as present and matching.
- No file under `data/raw/` is tracked by git.
- `uv run python -m unittest discover -s tests` passes.
