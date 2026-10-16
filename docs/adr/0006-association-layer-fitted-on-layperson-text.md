# 0006: The association layer may be fitted on the ILSIC-Lay train split

Status: accepted (owner, 2026-10-16, slice 6)

[ADR 0005](0005-learned-association-layer-is-opt-in.md) lets a learned layer exist next to the Baseline and fixes its training data as the ILSI `train` split. That layer, `assoc-nb v1`, finds 39.3% of the IPC charges in set v2, a set of layperson forum posts. Only 19 of the 30 IPC sections that set cites are in its vocabulary, and its training text is court judgments. This ADR widens one clause of ADR 0005, "from which data", and nothing else.

**The new data.** `assoc-nb v2` is fitted on the ILSIC-Lay train split and on nothing else: `data/raw/ilsic/FT-Layman-train.jsonl.xz`, 6,465 posts, SHA-256 `6f998e08b0488c94f096db85395fac1a2f21331f1c2348aaee93d27c7a55a0d8` (recorded in `data/SOURCES.md`). No ILSI text, no ILSIC Layman test split and no dev split is read by `fit`. The 30 post ids of set v2 are dropped from the train data before fitting, and a fit records how many posts it dropped.

**Licence.** The posts are CC BY-NC-SA 4.0: non-commercial, share-alike, with attribution to the ILSIC authors. A model fitted on them carries those terms. The fitted file, `data/assoc-nb-v2.json`, is therefore gitignored and never leaves the private repository, as the source file under `data/raw/` already does.

**What stands from ADR 0005, unchanged.**
- The layer is opt-in and never part of the Baseline path.
- No model call, no network and no query rewrite at run time. The layer imports the standard library and `ibid` only.
- Tokenisation is the fixed one of [ADR 0004](0004-fixed-tokenisation-of-the-raw-query.md).
- What is learned is term counts per section plus post counts per section. Prediction is multinomial naive Bayes with add-one smoothing and priors from section frequencies, with k = 5.
- The model is a file whose SHA-256 is written into every predictions file, and two fits on the same bytes are byte-identical.
- The Act side of an output comes only from verified Concordance entries.
- A layer version is scored once per set, by the one scorer (`ibid charges score --predictions`), and any change to tokenisation, smoothing or k is a new layer version.

**Cost.** A model fitted on forum text can look good on forum text. Set v2 is itself ILSIC-Lay text, so its v2 score is in-distribution, and its labels are incomplete because a forum answer rarely cites every applicable Provision. Both caveats go beside the number in the report.

**Check.** The layer is kept only if `assoc-nb v2` beats `assoc-nb v1` and the Baseline on the same sets.
