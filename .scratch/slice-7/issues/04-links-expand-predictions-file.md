# `ibid links expand` writes a `links v1` predictions file from a baseline predictions file

Status: done
Blocked by: 03

What to build: `ibid links expand --predictions <file from ibid charges export-baseline> --out <file>` (plus `--index`, `--concordance`). For each item and each output rule present in the input (top-k k=5 and threshold r=0.7), keep the original predicted sections in their order, then for each predicted section in rank order append its linked partners (IPC links for IPC, carried links for BNS) that are not already in the list, partners of one section in Citation order. The output has the same shape as the input predictions files, with layer `links`, layer version `v1`, and in its inputs the sha256 of the baseline file, the index and the concordance. The frozen rule is not run and not imported for ranking; the command only reads the baseline file.

User stories: 5. Spec Decisions 3 and 4.

Acceptance criteria (through `ibid links expand`, unittest):
- Fixture predictions over the mini-Act: originals first and in order, partners after, no duplicates, a partner already predicted is not appended again.
- Known-bad run, observed once: an expansion that sorts the combined list (reordering the originals) fails the order test on its assertion.
- The output records `layer: links`, `layer_version: v1` and the baseline file's sha256; changing one byte of the baseline changes that recorded hash.
- Both output rules and both Acts are expanded.
- Two runs on the same input are byte-identical.
- The input baseline predictions file is byte-identical after the run.
