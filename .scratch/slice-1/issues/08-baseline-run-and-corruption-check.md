# First baseline run with determinism and corrupted-run checks

Status: needs-triage
Blocked by: 03, 04, 05, 06, 07, 09, 10

## What to build
Run `ibid eval` on the frozen gold set to produce the baseline results file, with no quality target. Prove the harness can fail: a corrupted run (a scrambled section in a source text, a wrong concordance mapping) must lower the score, and two clean runs must be byte-identical. Keep the corruption inputs as test fixtures so the check is repeatable.

## User stories
18, 19, 20, 21

## Acceptance criteria
- [ ] A baseline results file exists with per-category exact-match scores, the pinned gold-set hash and the parser version.
- [ ] Two consecutive clean runs are byte-identical.
- [ ] A run with a scrambled section scores lower than the baseline in the affected category.
- [ ] A run with a wrong concordance mapping scores lower in the correspondence category.
- [ ] Both Act parsers' section-count checks pass on the clean sources.
- [ ] No model is called anywhere in the run.
