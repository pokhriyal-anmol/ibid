# Run the optimisation on LeSICiN, freeze the rule, score test once, cross-check metrics

Status: done
Blocked by: 01, 03, 04, 05, 06, 07, 08, 09, 11, 12

What to build: the actual measurement, run by the builder with the owner's sign-off on the protocol. Score round 0 on train and dev, run declared single-knob rounds until the saturation rule fires, freeze the rule, score the test split exactly once, and produce the report. Where the benchmark's own evaluation script can be obtained, run it once on the same predictions and record whether its F1 matches ours; otherwise record that the metric protocol is still our own implementation.

User stories: 8, 9, 12, 6, 7.

Acceptance criteria:
- `results/optimisation-log.json` holds every round from 0 to the stopping round, and the stopping reason is stated.
- The test split was scored once (or every score is reported if more than once).
- Committed results files carry the pinned data hashes and frozen rule hash, and no benchmark text is committed.
- The report states the expected Section 34 miss and the overfit check result.
- The metric cross-check outcome (matched, differed with the difference, or could not run) is written down, never omitted.
- Needs owner decisions: veto or accept the proposed optimisation protocol, and whether to request IL-TUR access.

Outcome: see `results/report.md` and the Results section of `pr.md`. The optimisation saturated at round 8, the owner extended the protocol with a 3-round settle phase, round 11 was frozen and the test split scored once. The metric cross-check could not run.
