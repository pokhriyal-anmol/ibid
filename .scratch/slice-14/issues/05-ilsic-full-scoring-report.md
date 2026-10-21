# Score every layer once on both ILSIC tests and write results/ilsic-report.md

Status: done
Blocked by: 02, 03, 04

What to build: rebuild `assoc-nb v2` with the existing `ibid assoc fit --source ilsic-lay` as ADR 0006 describes (outside git, no change to the command). Score the frozen rule v2.11, `assoc-nb v1`, `v2`, `v3` and `linear-lr v1`, `v2` once each on `FT-Layman-test` and `FT-LMsub-test`, reading data and models by absolute path from the main checkout and `/Users/anmolpokhriyal/data/il-tur/models/`. Write `results/ilsic-report.md` with every layer on both tests under the primary reading, intervals, published baselines and verdicts, the secondary reading in a separate block, the zero-label assumption, the Lay/Multi overlap note (not independent evidence), and the CC BY-NC-SA 4.0 / no-legal-accuracy caveat.

User stories: 6, 7.

Acceptance criteria:
- `results/test-ledger-ilsic.json` holds exactly one entry per (layer, version, split); no `--rescore-test` used.
- sha256 of the baseline, the frozen rule record, every pinned file (`gold/v2.json`, `concordance/v2.json` and their pins) and every previously committed result file is identical before and after; record the check in the report or PR.
- No ILSIC data or model file is committed; `git status` shows only the new results, ledger, report and code.
- Full test suite passes.
