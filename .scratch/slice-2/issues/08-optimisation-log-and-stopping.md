# Optimisation rounds logged to results/optimisation-log.json with the declared stopping rule

Status: done
Blocked by: 03

What to build: a way to record one optimisation round (for example `ibid bench round --change <knob>=<value>`): it scores train and dev with the new rule version, appends to `results/optimisation-log.json` the round number, the single declared knob changed, rule version, rule hash, train and dev scores, and the train/dev gap. One knob means one entry of the declared list changed in one way (for example adding one stop word, or changing one BM25 parameter); replacing the whole stop-word list is several changes. It refuses a round that changes more than one knob or a knob outside the declared list (tokenisation, stop-word list, BM25 weighting parameters, indexed provision levels, roll-up, k, r). Each log entry also holds the stratum scores of ticket 04, and a round whose dev micro-F1 on single-label cases falls by more than 0.5 point against the previous round is flagged `hurts-simple`; a flagged round cannot become the frozen rule unless the owner says so in the log. It reports whether saturation is reached: dev macro-F1 gain below 0.5 points absolute for 3 consecutive rounds, or 20 rounds, and flags when dev stops improving while train keeps rising. Round 0 is the unmodified rule v1.

Deferred: the command varies only stop words, k, r and the roll-up. Tokenisation, BM25 parameters and indexed provision levels are declared knobs that a round refuses until they are built. `ibid bench freeze --log <log> [--round N]` takes the rule (including stop words and version) from a logged round and refuses a flagged round the owner has not approved.

User stories: 8.

Acceptance criteria:
- On fixtures, a scripted sequence of rounds produces a log whose entries match the scores of independent single runs with the same rule.
- A round changing two knobs, or an undeclared knob such as a label-frequency prior, is refused (known-bad).
- A fixture sequence with three sub-0.5-point dev gains reports saturation; a 20-round sequence reports the cap.
- A sequence where dev falls while train rises is flagged as overfitting.
- A fixture round that raises overall dev F1 but lowers the single-label stratum by more than 0.5 point is flagged `hurts-simple` (known-bad).
- The test split is never read by this command.
