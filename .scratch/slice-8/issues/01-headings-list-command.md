# Read BNS margin headings and print them with `ibid headings list`

Status: done
Blocked by: none

What to build
A new module `src/ibid/headings.py`, a sidecar that is not part of the index. For the BNS it runs `pdftotext -layout` on the BNS PDF and reads the right-hand margin column. A section's heading is the margin text from that section's first line up to the next section's first line, with wrapped lines joined by single spaces (spec decision 1). Only top-level sections get a heading. Sub-provisions, chapter titles and group titles never do (decision 3). For the IPC, a section's heading is the text of the top-level Provision before its first em dash, read from the provisions the parser already produces, and null when there is no em dash. Add `ibid headings list --act bns|ipc` to `src/ibid/cli.py`. It prints one `citation<TAB>heading` line per section in document order, then a count of sections with and without a heading, and lists every section without one (decision 5). Nothing is written to the index, the `provision` table, `PARSER_VERSION` or any pinned file (decision 2).

User stories: 1, 2, and 7 for this module.

Acceptance criteria
- Fixture tests run through `ibid headings list` against invented layout pages shaped like the real PDF: a heading wrapped over two or more lines, a section whose body wraps past the end of its heading, and a chapter title between two sections. Each test is run once against known-bad input and seen to fail: a heading read from the wrong section, a wrapped heading cut after its first line, and a chapter title taken as a heading.
- On the real BNS PDF (path from `tests/pdfs.py`), `ibid headings list --act bns` gives a heading for at least 350 of the 358 sections and names every section without one.
- BNS 83, 85, 86 and 87 print exactly "Marriage ceremony fraudulently gone through without lawful marriage.", "Husband or relative of husband of a woman subjecting her to cruelty.", "Cruelty defined." and "Kidnapping, abducting or inducing woman to compel her marriage, etc.".
- `ibid headings list --act ipc` prints one line per IPC section and its counts, and no sub-provision appears in either Act's output.
- `PARSER_VERSION` is unchanged and `ibid eval --gold gold/v2.json --concordance concordance/v2.json` still reproduces `results/baseline-v2.json` byte for byte. `gold/v2.sha256` and the concordance pin still match.
- `uv run python -m unittest discover -s tests` passes.
