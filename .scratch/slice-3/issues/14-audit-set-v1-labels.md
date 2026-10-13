# Audit the labels of set v1 against independent sources

Status: ready-for-agent
Blocked by: none (ticket 13 is done, concordance v3 exists)

What to build: an audit of `gold/multicharge/v1.json` that stands in for a lawyer's review as far as published sources and independent annotators can, and records its result in the file's review record. It does not remove the need for a lawyer before a score is published, and the report says so.

Checks:

1. BNS pairs against a published table. Every IPC to BNS pairing in v1 is checked against the CAPT correspondence table (ticket 13's parser). The report lists pairs that agree, pairs the table maps differently, and pairs the table does not cover.
2. IPC sections against an independent second panel. Three agents with a different prompt from the first drafting pass, each blind to the first labels, to the benchmark labels and to any retrieval output, read each query and list the IPC sections they would accept per charge. A charge counts as confirmed when at least two of the three include an accepted section of it. The report gives, per item, how many of the first pass's charges were confirmed, and the agreement as a mean pairwise Cohen's kappa over the section sets (set-level, per candidate section across the 30 items).
3. Charges the first pass left out. Sections that at least two panel agents listed and the first pass did not are listed as candidates, not added.
4. A comparison with the benchmark's own labels for the same cases, recomputed as in the collection report, reported as a signal only.

Outputs: `.scratch/slice-3/label-audit.md` and a `review` object added in a new version, `gold/multicharge/v1.1.json` with its pin (the pinned v1 is never edited in place). A charge confirmed by the panel and the table gets `label_basis: agent-checked-for-owner` only if the owner asks for it, and otherwise keeps `agent-drafted-skeptic-refuted` with the audit result recorded beside it.

User stories: 2, 3.

Acceptance criteria:
- The panel prompts are saved. Each agent's input is the query text only (the same blind file method as route C).
- The audit report states the kappa, the share of charges confirmed by at least two of three, the number of BNS pairs that agree with the table, differ, or are uncovered, and the list of candidate missing charges.
- `v1.json` and its pin are unchanged, and `v1.1.json` validates and has its own pin.
- Nothing in the report claims lawyer review.
