# Slice 7 v1 report

## Status

Built. All 7 tickets are done, every user story (1 to 9) has a done ticket, and nothing failed or was held back. The review fixed 6 findings and left none open.

## What v1 does

The cross-reference graph has no edge between the definition and punishment sections the slice targets (IPC 302 and 300, 406 and 405, 420 and 415). A test now pins that, and ADR 0007 records it.

Instead, `links` derives definition-punishment links from IPC headings. A section headed "Punishment for X" is linked both ways to the section headed exactly X. The links are carried to the BNS only through verified Concordance v3 entries. `links expand` takes a baseline predictions file and appends each predicted section's partners after the original predictions, as layer `links` v1. The frozen rule, the ranking and every pinned file are unchanged, and no model is used.

The decision rule fixed in the spec was applied to the scores. The build reports KEPT as an opt-in output only, nothing wired into the MCP server. Across the two multi-charge sets, charges found went from 17 to 21 on v1 and from 22 to 30 on v2. ILSI test micro-F1 rose from 9.37 to 11.37 (top-k) and from 9.64 to 11.81 (threshold). Expansion newly found 12 charges with 74 added predictions, 16.2 percent of them correct. The verdict depends on how the rule is read, see Q-003 below.

## How to run it

From `AGENTS.md` and the CLI help:

```
uv sync
export IBID_BNS_PDF=<root>/data/raw/bns-prs.pdf IBID_IPC_PDF=<root>/data/raw/ipc-wipo.pdf
uv run python -m unittest discover -s tests
uv run ibid links list
uv run ibid links expand --predictions <file from ibid charges export-baseline> --out <file>
uv run ibid links bench --split <ILSI split> --out <file>
```

The verdict figures come from `.scratch/slice-7/report.py`, which writes `.scratch/slice-7/report.md`.

## Tests

The full unittest suite was green at build and again after review. I did not rerun it for this note.

## What I assumed for you

Q-003: pooled reading taken, so the verdict is KEPT. Recall is compared per set, pooled over both Acts and both output rules. Read per set and Act, or per cell, the verdict is NEGATIVE because set v2 BNS gains nothing. Changing it means editing the verdict in the report and ADR 0007. No scores are rerun.

The build also settled these without queuing them. They are craft or already fixed by the spec:
- Expanded partners outside the 100-label ILSI vocabulary are dropped from scoring like the baseline, but counted in mean predictions per case.
- The second output rule (threshold) is scored in its own ledger, `gold/multicharge/{v1,v2}.links-threshold.ledger.json`, so each output is scored once without `--rescore`.
- The real ILSI test split was scored once, as the spec requires, recorded in `results/test-ledger-links.json`. A rescore is refused unless `--rescore-test` is passed. This cannot be undone.
- The IPC pair count is whatever the rule measures, not tuned to the 23 the spec expected.

## Held back

Nothing. All 7 tickets were built.

## Your questions

2 pending, 0 blocking: Q-002 (slice 6, assoc-nb v2 training data and threshold) and Q-003 above. That is below the batch size of 8, so none are asked yet and the work carries on.
