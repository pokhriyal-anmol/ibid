# Bootstrap interval and published ILSIC baselines beside our score

Status: done
Blocked by: 01

What to build: add a 1,000-resample bootstrap over test queries (seed 0, stdlib `random`) giving the 95% interval for macro-F1 and micro-F1 under the primary reading, stored in the results file. Print our score, its interval and the paper's best published numbers for the same split side by side, labelled "published, not re-run by us" with their table numbers: ILSIC-Lay test macro-F1 14.83 and micro-F1 34.23 (GPT-4.1 two-shot), micro-F1 33.19 (fine-tuned Gemma-3); ILSIC-Multi test macro-F1 17.01 and micro-F1 33.95 (GPT-4.1 zero-shot). State in plain words, for each published number, whether the layer is above or below it under the primary reading only.

User stories: 4.

Acceptance criteria:
- A `unittest` checks the interval is deterministic for seed 0 on a fixture and contains the point estimate.
- The printed verdict uses the primary reading; a fixture where the layer clears a number only under the secondary reading is reported as below. This test is seen to fail once with the verdict switched to the secondary reading.
- Published numbers live in one constant with their table references.
