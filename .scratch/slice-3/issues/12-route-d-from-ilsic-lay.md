# Route D without writing queries: a layperson set from ILSIC-Lay

Status: needs-triage
Blocked by: the owner's approval to download the ILSIC data (see `spec.md`, "Downloads awaiting approval")

What to build: set v2, `gold/multicharge/v2.json`, 30 items whose queries were written by real laypeople on a legal forum and published in the ILSIC corpus (EACL Findings 2026, https://arxiv.org/abs/2602.00881, data at https://github.com/Law-AI/ilsic, CC BY-NC-SA 4.0). This replaces the owner's step in ticket 10 with an academic source. The labels come from the lawyers' replies to each post, extracted by the corpus authors, so no agent writes or drafts a label.

Selection, a written rule applied without reading query text, on the ILSIC-Lay `test` split only (the split no layer was fitted on):

- the label list holds at least two distinct IPC sections, not counting IPC 34, 149 and 120B;
- the query is 40 to 250 words (a layperson post, not a document);
- it contains no match for the section-number pattern `SECTION_NUMBER` of `ibid charges intake`, so the set measures reading a story and not reading a citation;
- from the candidates, the 30 whose SHA-256 of `id` sorts first.

Labels. Each charge is an IPC section the lawyers' replies cite. Charges with an Act other than the IPC are left out and counted. The BNS side uses verified concordance entries only (ticket 13). `label_basis` takes a new value, `lawyer-answer-extracted`, and the validator accepts it. The file's `label_policy` says the labels are the sections cited in forum lawyers' replies, extracted automatically, that the corpus's own check found 5.46 statutes per query on 50 annotated queries against 2.40 in the data (so labels are incomplete), and that this makes recall meaningful and precision not.

Privacy. `anonymised` stays `true` only after a scrub: phone numbers, email addresses, URLs and any run of seven or more digits are replaced, and the scrub is recorded. The queries are public forum posts. No post is committed before the scrub.

User stories: 1, 2, 3, 7.

Acceptance criteria:
- The selection rule, its hash and the candidate counts are written to `.scratch/slice-3/draft/ilsic-selection.json` before any query is read.
- `ibid charges validate` passes on `v2.json` with `author_type` of `owner`, `lawyer` or `judgment-excerpt` extended by `forum-post`, a `source` naming the corpus and post id, and `label_basis: lawyer-answer-extracted`. The validator's refusals for the old values still hold.
- No item has a section-number match in its query.
- Every cited IPC section exists in the index. Citations that do not are dropped and counted.
- The collection report states the licence (non-commercial, share-alike), the label limitation, how many candidates there were, and the scrub counts.
- The baseline and routes A, B and C are each scored once on v2 through ticket 06's scorer and added to the comparison report, with the labels' incompleteness stated beside every recall.
