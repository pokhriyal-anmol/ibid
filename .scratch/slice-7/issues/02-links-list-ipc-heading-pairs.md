# `ibid links list` prints IPC definition-punishment links derived from headings

Status: done
Blocked by: none

What to build: a new module `src/ibid/links.py` and a `links` subcommand group in `src/ibid/cli.py` with `links list`. It reads top-level IPC section headings from the index, finds every section headed "Punishment for X", and links it in both directions to every other top-level section whose heading equals X after lowercasing, trimming surrounding whitespace and stripping one trailing full stop. Nothing else creates a link: no substring, fuzzy or stemmed match. Output is one line per pair of Citations, sorted by Citation in numeric section order, followed by a count line. A `--index` flag mirrors the other commands (default `data/index/ibid.sqlite`). Standard library only.

User stories: 2 (IPC half), 3.

Acceptance criteria (through `ibid links list`, unittest):
- Fixture: an invented mini-Act whose headings follow the real pattern, including "Punishment for X" with an exact match, one with no match, and a section whose heading merely contains X (for example "X by a public servant"). Output lists exactly the expected pairs and excludes the containing-heading section.
- On the real index: the output includes IPC 302 and IPC 300, IPC 376 and IPC 375, IPC 379 and IPC 378, and the IPC pair count is printed. The spec expects 23; the test asserts the measured number, and any difference from 23 is reported in the ticket's PR, not tuned away.
- Two runs produce byte-identical stdout.
- Known-bad run, observed once: switching the match to substring containment makes the fixture exclusion test fail on its assertion.
- `results/`, `gold/` and `concordance/` are byte-identical after the tests run.
