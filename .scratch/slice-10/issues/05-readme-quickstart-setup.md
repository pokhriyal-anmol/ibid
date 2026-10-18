# Replace the README Quickstart with the ibid setup sequence

Status: done
Blocked by: 02, 03

What to build:
- Replace the README Quickstart with: `uv sync`, `uv run ibid setup --fetch bns`, the IPC step with its honest explanation (the WIPO PDF link is signed and expires; open the WIPO Lex page from `data/SOURCES.md`, copy the PDF link, run `uv run ibid setup --fetch ipc --url <link>`), then `uv run ibid setup`, which prints the section counts and the `claude mcp add` line.
- Drop the manual `export IBID_*_PDF` step from the Quickstart if setup's defaults make it unneeded; keep the eval and test commands. Update `AGENTS.md` Commands with `ibid setup`.
- Note in `data/SOURCES.md` that `data/sources.json` holds the same hashes and a test keeps them equal.

User stories: 9, 10.

Acceptance criteria:
- Following the Quickstart verbatim on a checkout with `data/raw/` empty (using a local copy of the IPC PDF served over 127.0.0.1 for the `--url` step) ends with `ibid setup` exit 0 and the counts line.
- No text in the Quickstart tells the user to fetch PDFs by hand or check hashes by hand.
- The index, every results file, every pin and the baseline are byte-identical to `main` before the slice (`git diff main -- data/index results gold concordance` empty).
