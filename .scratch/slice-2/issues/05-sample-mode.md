# 200-item sample mode for fast iteration

Status: done
Blocked by: 02

What to build: a `--sample N` option (default 200 when given without a value is fine) on the run command that selects a deterministic subset of a split (for example the first N by sorted `id`, or a fixed-seed draw recorded in the results file). The results file marks the run as a sample and records N and the selection rule so a sample score is never mistaken for a full-split score.

User stories: 11.

Acceptance criteria:
- Two sample runs with the same N, rule and data are byte-identical.
- The results file states `sample: N` and the selection rule; a full run states no sample.
- `--sample` on the test split is refused, so a sample can never use up or leak the single test scoring (ticket 07).
- On a fixture split of 5 items, `--sample 3` scores exactly 3 cases.
