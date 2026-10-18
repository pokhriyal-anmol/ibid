# ibid setup: offline checklist of poppler tools and source PDFs from data/sources.json

Status: done
Blocked by: none

What to build:
- Commit `data/sources.json` with, for `bns` and `ipc`: target filename under `data/raw/`, URL (BNS: the PRS URL from `data/SOURCES.md`; IPC: the WIPO Lex details page, marked as not directly fetchable), byte size and SHA-256.
- A new `ibid setup` subcommand in `src/ibid/cli.py` (logic in a new small module, e.g. `src/ibid/setup.py`), with `--sources <json>` defaulting to `data/sources.json` and `--raw-dir` defaulting to `data/raw`. It makes no network call.
- One line per check, pass or fail: each of `pdftotext`, `pdftohtml`, `pdfseparate`, `pdfunite` on PATH (detected with `shutil.which`, never installed); each PDF present; each PDF's SHA-256 equal to the manifest.
- After each failed check, the single next action: for a missing tool `brew install poppler` (macOS) and `apt install poppler-utils` (Debian); for a missing PDF the URL and the absolute target path, plus `ibid setup --fetch bns` or the `--fetch ipc --url` form; for a hash mismatch "present, hash differs" with both hashes, and the file is not touched.
- Exit 0 only if every check passes.
- A test asserts that the hashes in `data/sources.json` equal the ones in `data/SOURCES.md`.

User stories: 1, 2, 3 (and Decisions 1, 2, 6).

Acceptance criteria (tests through `ibid setup`, `unittest`, invented tiny non-PDF fixture files and a small manifest passed with `--sources`):
- All fixture files present with matching hashes: every line passes, exit 0.
- A missing fixture file: a fail line naming the URL and absolute target path, exit non-zero.
- A fixture file with different bytes: "present, hash differs" with expected and actual hashes, exit non-zero, and the file's bytes and mtime are unchanged afterwards.
- A missing tool (PATH stripped in the test env): a fail line followed by both install commands, exit non-zero.
- The sources.json vs SOURCES.md test fails when one hash in a copy of sources.json is altered (run once against that known-bad input).
- No socket is opened in default mode (the test runs with no server and no network).
- The index, every results file, every pin and the baseline are byte-identical before and after (`git status` clean apart from the new files).
