# Multi-charge set v1: the frozen baseline scored on the IPC and on the BNS

Date: 2026-10-12. Set: `gold/multicharge/v1.json` (sha256 `9b77ae21…`). Rule: `query-rule v2.11` (hash `250c53f8…`), k=5, r=0.7, BM25 k1=4.0 and b=1.0, max roll-up. Index sha256 `efaf6fe8…`. Each Act was scored once with this rule. The untuned round-0 rule (`v2`) was also scored once per Act for context and is reported, not selected.

## Result

A charge is found when any accepted section of the Act is predicted. Predictions come from every section of the Act, not from the 100 benchmark labels.

| Rule | Act | Output | Charges found | Per-charge recall | Items with every charge found | Mean predictions per item |
|---|---|---|---|---|---|---|
| v2.11 frozen | IPC | top-k (k=5) | 3 of 98 | 3.1% | 0 of 30 | 5.0 |
| v2.11 frozen | IPC | threshold (r=0.7) | 5 of 98 | 5.1% | 0 of 30 | 8.7 |
| v2.11 frozen | BNS | top-k (k=5) | 4 of 98 | 4.1% | 0 of 30 | 5.0 |
| v2.11 frozen | BNS | threshold (r=0.7) | 5 of 98 | 5.1% | 0 of 30 | 7.5 |
| v2 round 0 | IPC | top-k (k=3) | 3 of 98 | 3.1% | 0 of 30 | 3.0 |
| v2 round 0 | IPC | threshold (r=0.8) | 2 of 98 | 2.0% | 0 of 30 | 4.6 |
| v2 round 0 | BNS | top-k (k=3) | 3 of 98 | 3.1% | 0 of 30 | 3.0 |
| v2 round 0 | BNS | threshold (r=0.8) | 4 of 98 | 4.1% | 0 of 30 | 5.9 |

By charges per item (counted for the Act), the frozen rule's recall on the threshold output is 5.0% for the 10 two-charge items and 5.1% for the 20 items with three or more. No item has a single charge, so there is no simple-query stratum in this set. The per-charge results and the missed-charge lists with the top predicted sections are in `multicharge-v1-ipc.json` and `multicharge-v1-bns.json`.

## What the misses look like

The same five charges are found on both Acts: rape and rape of a minor (IPC 376, BNS 64 and 65), criminal conspiracy (IPC 120B, BNS 61), stalking (IPC 354D, BNS 78), outraging modesty (IPC 354, found on the IPC only) and criminal breach of trust by an agent (BNS 316, found on the BNS only). These charges have a distinctive word in their section text.

Everything else is missed, including murder (IPC 302), attempt to murder (IPC 307), cheating (IPC 420) and hurt (IPC 323). The predictions are dominated by sections with generic court vocabulary. On the IPC the most frequent predictions over the 30 items are IPC 228A (disclosure of a victim's identity, 14 items), IPC 19 (the definition of a Judge, 13), IPC 193 (false evidence, 10), IPC 216B, IPC 138A and IPC 229A. On the BNS they are BNS 358 (repeal and savings, 13 items), BNS 229, BNS 2 (definitions, 11) and BNS 72. The queries are court orders and the sections that match them are sections about courts, evidence and definitions.

This agrees with two things already known. Murder queries match the definition, not the punishment, so IPC 302 was found in 4 of 3,246 ILSI test cases ([research note](../docs/research/legal-retrieval-literature.md)). And the BM25 settings that scored best on the benchmark's macro-F1 (b=1.0, k1=4.0) are not what finds charges here: the untuned round-0 rule finds the same few charges, within three charges of the frozen rule on every row.

A diagnostic outside the scorer confirms the harness: restricted to the 100 benchmark labels, the frozen rule finds 7 of 98 charges, against 3 of 98 on all 575 IPC sections. So the 100-label restriction that the ILSI benchmark score enjoys explains only part of why this set scores lower.

## What this number is and is not

- 30 items cannot separate rules that differ by a few points. A difference of a few charges out of 98 is noise.
- Labels were drafted by agents and refuted by a second agent. No lawyer has reviewed them. The BNS side has no second Act expert. See `.scratch/slice-3/collection-report.md`.
- 28 of the 30 queries name sections outright and are often a bail order or an FIR summary. The score says how well text matching finds the charges a legal document states. It is not a measure of reading bare facts told by a person.
- The 30 items come from the ILSI train split, which the frozen rule was tuned on in aggregate. The rule has no memory of 30 specific cases, but the set is not an unseen sample in the strict sense.
- The recall of 3 to 5 percent is the number every later layer in slice 3 must beat. It is a low bar, and a code-only layer that links definitions to punishments, or one that discounts sections with generic court vocabulary, could clear it. Whether to build those is the owner's call.
