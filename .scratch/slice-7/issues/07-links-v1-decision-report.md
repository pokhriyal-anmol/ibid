# Report the decision-rule outcome for `links v1` and close the slice

Status: done
Blocked by: 05, 06

What to build: `.scratch/slice-7/report.md` (generated from the committed results files by a small script kept beside it, as slice 6 did with `v2-report.py`) stating: the decision-rule outcome, kept or negative, applied exactly as fixed in spec Decision 5; per set, Act and output rule, how many Charges expansion newly found, how many predictions it added, and what share of added predictions were correct; the ILSI test micro-F1 change. If negative, the report says so plainly, `links.py` stays documented as a dead end in ADR 0007, and nothing is wired into `src/ibid/mcp.py`. If kept, it is recorded as an opt-in output only; MCP wiring stays out of scope.

User stories: 8, 9.

Acceptance criteria:
- Every figure in the report is re-derived by the script from the results files in the repo; running it twice gives byte-identical output.
- The kept/negative verdict follows mechanically from the committed numbers under the decision rule; a hand check of one cell (say set v1, IPC, top-k) matches.
- ADR 0007 is updated with the outcome.
- Slice-wide byte-identity check: `gold/`, `concordance/`, `results/frozen-rule.json`, `results/test-ledger.json`, `results/baseline-v1.json`, `results/baseline-v2.json`, every pre-existing results file and the baseline `ibid eval` output are unchanged against `main` (verified with `git diff --stat main -- <paths>` showing only new files plus `layer-comparison.md` and ledger appends).
- `src/ibid/mcp.py`, `parse.py` and `PARSER_VERSION` are unchanged.
- The full unittest suite passes.
