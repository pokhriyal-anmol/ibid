# Commands that read the PDFs say 'run: ibid setup' when one is missing

Status: done
Blocked by: none

What to build:
- `ibid mcp` already prints `error: no such file: <path>` (`src/ibid/mcp.py`). Add `run: ibid setup` to that message.
- Give `ibid eval`, `ibid freeze`, `ibid conform`, `ibid headings` and the other subcommands that take `--bns`/`--ipc` the same one-line error plus `run: ibid setup` and a non-zero exit, instead of whatever they do today (likely a traceback). One shared check, called once where the paths are read.

User stories: 8.

Acceptance criteria:
- For `ibid mcp` and `ibid eval`, run with `--bns` pointing at a non-existent path: stderr has one `error: no such file: <path>` line and a `run: ibid setup` line, no traceback, exit non-zero.
- The same for `--ipc`.
- With the real PDFs, `ibid eval --gold gold/v2.json --concordance concordance/v2.json` output stays byte-identical to `results/baseline-v2.json`.
