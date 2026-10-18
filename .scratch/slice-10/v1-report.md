# Slice 10 v1 report

## Status

Built. All 5 tickets are done, none failed, and every one of the spec's 10 user stories has a done ticket behind it. The work is on branch feat/slice-10 and the review found and fixed 4 issues.

## What v1 does

`ibid setup` checks that a new machine can run Ibid and tells you the next step for each gap. It checks the four poppler tools and the BNS and IPC PDFs, and compares each PDF's SHA-256 with `data/sources.json`. It makes no network call unless you ask. A PDF with the wrong hash is reported with both hashes and left alone.

`ibid setup --fetch bns` downloads the BNS PDF from its recorded address. `--fetch ipc --url <link>` does the same for the IPC, because the WIPO link is signed and expires, so you must supply it. A download is checked for size (200 MB cap) and hash before it is moved into place. On any failure nothing is left behind, and an existing file is never overwritten. Only https addresses are accepted, plus localhost for tests.

When every check passes, setup parses both Acts, prints the section counts (358 BNS, 575 IPC), and prints the `claude mcp add ibid -- ...` line with this machine's absolute paths. Commands that read the PDFs (`mcp`, `eval` and the rest) now print `run: ibid setup` when a PDF is missing. The README Quickstart is replaced with this sequence.

## How to run it

From README.md:

```bash
uv sync
uv run ibid setup --fetch bns
uv run ibid setup --fetch ipc --url <link>
uv run ibid setup
```

Open the WIPO Lex page listed in `data/SOURCES.md`, copy the PDF link, and use it as `<link>`.

```bash
# Run the frozen evaluation (scored mode refuses a gold file that fails its pin)
uv run ibid eval --gold gold/v2.json --concordance concordance/v2.json --out results/run.json

# Run the test suite (about 30 seconds)
uv run python -m unittest discover -s tests
```

## Tests

Green, both after the build and after the review fixes. Nothing beyond that is claimed here.

## What I assumed for you

- Q-001: launcher for the printed mcp line. Default taken: `uv run --directory <repo> ibid mcp --bns --ipc --concordance`, all paths absolute, concordance/v3.json. Settled as craft, not your call.
- Q-002: whether setup.py may use the network inside the no-model import scan. Default taken: it may import urllib, http and socket but not model packages, and a test with a known-bad case checks that. Settled, no exemption needed.
- Q-003: exit code after a successful `--fetch`. Default taken: exit 0, even if the other PDF is still missing. A plain `ibid setup` run gives the overall verdict. Settled from ticket 3.

## Held back

Nothing. Every ticket was built.

## Your questions

0 pending, 0 blocking. That is below the batch size of 8, so none are asked yet; the work carries on without them.
