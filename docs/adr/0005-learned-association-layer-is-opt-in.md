# 0005: A learned association layer is allowed as an opt-in, and never in the baseline

Status: accepted (owner, 2026-10-12, route B of slice 3)

[ADR 0001](0001-retrieval-independent-of-the-model.md) keeps the baseline free of any model and [ADR 0004](0004-fixed-tokenisation-of-the-raw-query.md) forbids learned weights in tokenisation. This ADR allows one thing next to the baseline: a layer with learned weights, as an opt-in that reports its own evidence packet.

**What is learned.** Term counts per label: for each of the 100 ILSI labels, how often each term occurs in the fact text of training cases carrying that label, plus the number of training cases per label. Nothing else. A prediction is multinomial naive Bayes with add-one smoothing and priors from the label frequencies, and the top 5 labels are returned.

**From which data.** The ILSI `train` split minus the item ids of the multi-charge set it is scored on (`gold/multicharge/v1.json`, 30 ids). A fit records how many training cases it dropped for that reason. No dev or test text is read by `fit`.

**Where it lives.** The model is a file, `data/assoc-nb-v1.json`. Its header holds the training file hash, the held-out ids hash and the layer version, and its SHA-256 is written into every predictions file (`inputs.model`). A prediction is a deterministic function of the query and that file. Two fits on the same bytes are byte-identical.

**What it may not do.** Call a model or a network at run time (the layer imports the standard library and `ibid` only, and a test checks it), change the baseline path, or be scored by any code other than the one scorer (`ibid charges score --predictions`, and the benchmark's own scorer for ILSI splits). The BNS side of its output comes only from verified concordance entries, so it is thin by construction.

**Cost.** The layer's numbers are measured against labels the benchmark's judges drew, and the model inherits that vocabulary and its biases. A weight trained on train text can look good on text that resembles train. The report therefore gives ILSI dev, ILSI test (once per layer version, in `results/test-ledger-assoc.json`, separate from the baseline's ledger) and the multi-charge set (once per layer version) side by side with the baseline.

**Check.** The layer is kept only if it beats the baseline on the same sets. Changing tokenisation, smoothing or k is a new layer version, never an edit.
