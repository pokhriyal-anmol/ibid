# Optimisation rounds logged to results/optimisation-log.json with the declared stopping rule

Status: needs-triage
Blocked by: 03

What to build: a way to record one optimisation round (for example `ibid bench round --change <knob>=<value>`): it scores train and dev with the new rule version, appends to `results/optimisation-log.json` the round number, the single declared knob changed, rule version, rule hash, train and dev scores, and the train/dev gap. It refuses a round that changes more than one knob or a knob outside the declared list (tokenisation, stop-word list, BM25 weighting parameters, indexed provision levels, roll-up, k, r). It reports whether saturation is reached: dev macro-F1 gain below 0.5 points absolute for 3 consecutive rounds, or 20 rounds, and flags when dev stops improving while train keeps rising. Round 0 is the unmodified rule v1.

User stories: 8.

Acceptance criteria:
- On fixtures, a scripted sequence of rounds produces a log whose entries match the scores of independent single runs with the same rule.
- A round changing two knobs, or an undeclared knob such as a label-frequency prior, is refused (known-bad).
- A fixture sequence with three sub-0.5-point dev gains reports saturation; a 20-round sequence reports the cap.
- A sequence where dev falls while train rises is flagged as overfitting.
- The test split is never read by this command.
