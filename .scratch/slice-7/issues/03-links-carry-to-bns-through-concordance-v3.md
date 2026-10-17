# Carry IPC links to the BNS through verified Concordance v3 entries

Status: done
Blocked by: 02

What to build: extend `links.py` and `ibid links list` (new `--concordance` flag, default `concordance/v3.json`, checked against its sha256 pin the way other commands do) so that for each IPC link A-B, every BNS section a served for A and every BNS section b served for B with a different from b are linked. Only verified entries are used; the lookup goes through the existing Concordance serving code in `src/ibid/concordance.py` so "no verified concordance" is handled the same way it is everywhere else. BNS links print after the IPC links in the same Citation-pair format, with their own count line.

User stories: 2 (BNS half), 4.

Acceptance criteria (through `ibid links list`, unittest):
- Fixture: the mini-Act from ticket 2 plus a small invented concordance with one verified entry pair that yields a BNS link, one unverified entry that must yield none, and one pair mapping to the same BNS section that must yield none.
- Known-bad run, observed once: accepting unverified entries makes the unverified-entry test fail on its assertion.
- On the real Acts with Concordance v3: the BNS count is printed and asserted at its measured value; two runs are byte-identical.
- A concordance file that does not match its pin is refused with exit 1.
- `concordance/v3.json` and `concordance/v3.sha256` are byte-identical after the tests.
