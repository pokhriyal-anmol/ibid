# ibid setup: prove the install by parsing both Acts and print the claude mcp add line

Status: done
Blocked by: 01

What to build:
- When every check from ticket 1 passes, `ibid setup` parses both Acts with the existing parsers (`src/ibid/parse.py`, `src/ibid/ipc.py`) and prints `BNS 358 sections, IPC 575 sections`. A count other than the expected one is a failed check with a non-zero exit. Expected counts are stored per Act in `data/sources.json`.
- Then it prints the exact `claude mcp add ibid -- ...` line with this machine's absolute paths (the repo directory and both PDF paths), runnable as pasted.
- If an earlier check failed, the parse step is skipped and reported as not run, not as passed.

User stories: 7.

Acceptance criteria:
- On the real PDFs (from `IBID_BNS_PDF` / `IBID_IPC_PDF` or the main checkout's `data/raw/`, as the existing tests find them), `ibid setup` exits 0, prints `BNS 358 sections, IPC 575 sections`, and prints a `claude mcp add ibid -- ...` line whose paths are all absolute and exist.
- With a manifest whose expected BNS count is wrong (known-bad), setup prints a failed count line and exits non-zero.
- With a failing check from ticket 1, no parse is attempted and no mcp line is printed.
- Parsing output, `PARSER_VERSION`, the index, results, pins and the baseline are unchanged.
