# ILSI research notes (2026-10-11)

Facts about the public statute-identification benchmark, for the slice 2 spec. Every row says where it came from and whether it was checked at a primary source. Nothing here is a number to quote until the "Not confirmed" rows are closed.

## Confirmed at a primary source

| Fact | Source |
|---|---|
| ILSI is the Legal Statute Identification task of IL-TUR, a benchmark for Indian legal text understanding (ACL 2024). | [IL-TUR dataset card](https://huggingface.co/datasets/Exploration-Lab/IL-TUR), [paper](https://aclanthology.org/2024.acl-long.618.pdf) |
| Input is sentences containing only the facts of a judgment. Output is a list of relevant IPC sections (`labels`). | dataset card, LSI config columns `id`, `text` (list of strings), `labels` |
| Splits: train about 43k, dev about 10k, test about 13k, plus a `statutes` split of about 100 documents. Exact counts are not on the card. | dataset card |
| The dataset license field is `cc-by-nc-sa-4.0`. The GitHub README badge says CC BY-NC 4.0. Both are non-commercial. | dataset card, [GitHub README](https://github.com/Exploration-Lab/IL-TUR) |
| Access is gated: you must log in, share contact information and accept conditions. | dataset card |
| The best listed score for LSI is 28.08% m-F1 by LeSICiN (a graph-based method). | dataset card "Benchmark Results" |
| Total dataset size is 1.6 GB (all eight tasks). | dataset card |
| A leaderboard Space and an evaluation script (on OneDrive) exist. | dataset card, GitHub README |

## Reported by a research agent, not confirmed

| Claim | Source given | Why unconfirmed |
|---|---|---|
| Label space is the 100 most-cited IPC sections out of more than 500. | LeSICiN paper, an arXiv follow-up | secondary; not seen on the dataset card |
| Built from about 100K judgments (Supreme Court and six High Courts), 66,090 fact sets kept. | LeSICiN paper | secondary |
| Split counts differ between sources (42,884 / 10,203 / 13,043 against 42,835 / 10,200 / 13,039). | two arXiv papers | the IL-TUR copy may differ from the LeSICiN release |
| Macro-F1 baselines: BERT 18.44, LegalBERT 21.74, InLegalBERT 26.23. LeSICiN's own paper says 28.45, IL-TUR says 28.08. | IL-TUR paper, LeSICiN paper | the gap is unexplained |
| A later reproduction reports micro/macro 0.328/0.160 (logistic regression) and 0.486/0.355 (AoS). | arXiv 2512.21902 | not the official leaderboard |

## Not confirmed at all

- Whether test labels are public. The card says dev and test "have a similar structure", which suggests labels are present, but never states it.
- The exact metric protocol (micro or macro, over which label set). The paper says both "mF1" and "macro-F1".
- The terms of use of the underlying judgment texts.
- The current leaderboard values (its page returned 404).
- Whether any BNS data exists. Nothing found mentions BNS.

## What this means for Ibid

1. The labels are IPC sections that judgments cite. They are citation behaviour, not expert answers, so noise is likely and nobody has quantified it.
2. The task is multi-label classification of long fact text. Ibid is a citation-exact retrieval engine. A retrieval baseline will probably score far below a trained classifier, and that is a legitimate thing to measure, not a failure.
3. IPC only: it cannot say anything about BNS performance.
4. Non-commercial license: fine for research and for this private repo. It matters if Ibid is ever productised.
5. Slice 1's keyword search returns **zero hits** for realistic fact-style sentences (checked 2026-10-11 on three sentences). Slice 2 needs a fixed, deterministic way to turn a fact paragraph into a query.
