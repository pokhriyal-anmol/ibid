# Claims ledger rows and slice 15 report, pinned by test_claims

Status: done
Blocked by: 03, 06

What to build: `docs/claims.md` gains CrPC and BNSS rows in its coverage table with their parsed section counts (Schedules and Forms named as not covered), and a row for the check results (count match and heading-match rate per Act, concordance counts by type and verified or not). No retrieval accuracy is claimed (decision 9). `tests/test_claims.py` pins each new figure to the file it was measured from, the way it does today. A short report under `.scratch/slice-15/` states the section counts, heading-match rates, every mismatch, the concordance counts and the tripwire rate, what is not covered (Schedules, Forms, Hindi text, state amendments, post-2019 CrPC amendments), and that no lawyer reviewed text or concordance. Every figure is re-derived from a run this session, not copied.

User stories: 8, 10, 9 (final confirmation).

Acceptance criteria:
- `tests/test_claims.py` passes and fails once when a new figure in `docs/claims.md` is changed by one.
- The report lists every heading mismatch and every tripwire mismatch printed by tickets 2, 3 and 6, and names the CrPC as the November 2019 India Code revision taken from the Internet Archive capture.
- `ibid eval --gold gold/v2.json --concordance concordance/v2.json --out <tmp>` reproduces `results/baseline-v2.json` byte for byte; the byte-identity test passes.
- `uv run python -m unittest discover -s tests` passes.
