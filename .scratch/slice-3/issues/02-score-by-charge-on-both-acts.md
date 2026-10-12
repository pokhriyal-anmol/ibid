# Score a rule by charge, on the IPC and on the BNS

Status: ready-for-agent
Blocked by: 01

What to build: `ibid charges score --set <file> --index <index> --frozen-rule <file> --act ipc|bns --out <results.json>`. For each item it takes the raw `query`, runs the frozen rule (tokenisation, stop words, BM25 k1 and b, stemming, levels, roll-up, k and r) over the provisions of the chosen Act only, rolls hits up to section citations, and produces the top-k set and the above-threshold set exactly as `ibid bench run` does. It does not restrict predictions to the 100 benchmark labels, because the set is not tied to them. It reuses the same scorer code as `bench run`, not a copy.

Scores, each for the top-k rule and the threshold rule:

- per-charge recall: the share of charges (for that Act) with any accepted section predicted;
- all-charges-hit rate: the share of items in which every charge counted for that Act is found;
- by number of charges per item (1, 2, 3 or more);
- predictions per item, as a mean, so recall is read with its noise;
- the list of missed charges as item id and charge name, with the top three predicted sections, so a reader can see what was found instead.

The results file records the set's SHA-256, the rule version and hash, the index hash, the Act, the counts of charges excluded because the Act has no counterpart, and the `label_basis` counts. A second scoring of the same rule version on the same set is written to a ledger beside the set and reported next to the first, as for the test split.

User stories: 4, 6, 7, 8.

Acceptance criteria (invented fixture set and fixture index):
- Per-charge recall, all-charges-hit rate, strata and mean predictions match hand-computed values on the fixture, for both Acts and both output rules.
- A charge with several accepted sections is found when any one is predicted, and a fixture shows the result differs from counting only the first (known-bad).
- A charge with an empty list for the Act is excluded from that Act and counted in the exclusion count.
- Predictions come only from the chosen Act (a fixture query that matches an IPC provision never produces a `BNS` prediction under `--act bns`).
- A section outside the 100 benchmark labels can be predicted and found.
- Two identical runs are byte-identical.
- Scoring refuses an unpinned or mismatched set file.
- Run against the real frozen rule on the fixture index, the predictions of an item equal what `bench run` would predict for the same query on the same Act with the label-space restriction lifted. This is checked once with a small test that calls both commands.
