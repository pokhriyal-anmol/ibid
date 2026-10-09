# Slice 1: Reproducible citation and cross-reference baseline

Status: needs-triage (awaiting your approval before ticketing)

## Problem Statement

I want an Indian criminal-law assistant whose citations are exact and whose core answer does not change with the model. Today I have no way to measure that. There is no parsed form of the IPC or BNS, no resolved cross-references, and no answer key I trust, because the public IPC-to-BNS tables disagree with each other. Without a measurement, any later claim of accuracy would be a guess.

## Solution

One command parses the IPC and the BNS into section trees, resolves their internal cross-references, answers a frozen gold set of about 50 questions, and writes a results file. Running it twice produces byte-identical output. It sets no quality target. The first score becomes the baseline that every later layer has to beat.

## User Stories

1. As the builder, I want the BNS parsed into a section tree, so that every provision has a stable address.
2. As the builder, I want the IPC parsed into a section tree, so that both Acts use the same structure.
3. As the builder, I want subsections, clauses, provisos, explanations, exceptions and illustrations kept as separate provisions, so that a citation can point at exactly the right piece.
4. As the builder, I want the parser to report how many sections it recovered against the known total for each Act, so that a silent miss cannot pass.
5. As the builder, I want the English text kept and the legacy-font Hindi text discarded, so that garbage characters never reach the index.
6. As the builder, I want every provision to have one canonical citation string, so that equality is a byte comparison.
7. As the builder, I want cross-references inside provisions detected by rule, so that no model decides what refers to what.
8. As the builder, I want each cross-reference resolved to a citation, or recorded as unresolved with its reason, so that failures are visible.
9. As the builder, I want a lookup by citation to return the verbatim provision text, so that "what does BNS 103(1) say" is exact.
10. As the builder, I want a lookup to also return the provisions it refers to, so that a cross-reference chain is followed in code.
11. As the builder, I want an IPC citation to return its concordant BNS provisions, so that the old-to-new mapping is answerable.
12. As the builder, I want a BNS citation to return its concordant IPC provisions, so that the reverse mapping is answerable.
13. As the builder, I want each concordance entry to say whether the mapping is one-to-one, split, merged or removed, so that I do not read a loose mapping as exact.
14. As the builder, I want a plain keyword query to return provisions from the same index, so that the baseline covers non-citation questions too.
15. As the builder, I want the same raw query to always return the same ordered result, so that the evidence packet is byte-identical.
16. As the builder, I want a gold set of about 50 questions, each with a gazette page citation, so that every answer can be checked at the source.
17. As the builder, I want the gold set frozen and hash-pinned before the first scored run, so that I cannot tune the answers to the system.
18. As the builder, I want a scorer that reports exact-match results per question category, so that I can see which kind of question fails.
19. As the builder, I want the results written to a file with the gold-set hash and the parser version in it, so that a score can never be separated from what produced it.
20. As the builder, I want two consecutive runs to produce byte-identical results, so that the harness itself is proven deterministic.
21. As the builder, I want a deliberately corrupted run (a scrambled section, a wrong mapping) to lower the score, so that I know the harness can fail.
22. As a later reader, I want the correspondence questions marked separately, so that the contested items are easy to find and review.

## Implementation Decisions

- One test seam, the highest available: the evaluation command. Its input is the frozen gold set plus the source texts, and its output is the results file. Everything below it (parser, graph, concordance, index, scorer) is tested through that seam, plus the parser's section-count check.
- Modules to build: an Act parser (one per source format, sharing one section-tree shape), a cross-reference resolver, a concordance loader, a lookup and keyword-search index, a gold-set loader that checks the pinned hash, and a scorer.
- The section tree is the single shared data shape. Its provisions carry a canonical citation, verbatim English text, and parent and child addresses.
- Retrieval takes the raw query only (see ADR 0001). No model is called anywhere in this slice.
- The stack is Python, SQLite and `uv` (see ADR 0002). The index is one file that can be rebuilt from source.
- The BNS source is the Gazette of India copy hosted by PRS (102 pages, English text extractable). Its section headings are irregular under a plain text pattern (a first attempt matched about 150 of 358 sections), so the parser must be layout-aware and is judged on recovering all 358.
- The IPC source is the WIPO Lex HTML copy. It is a parsing source only until its reuse terms are read.
- The concordance is built from the gazette texts and checked by hand. Web conversion tables are used only to suggest candidates, never as truth.
- Gold-set process: I draft the items with gazette page citations, you spot-check at least 10 (weighted to correspondence items), then the file is frozen and hash-pinned. Later edits create a new version.
- Item categories: section lookup, subsection and proviso lookup, cross-reference chain, IPC-to-BNS and BNS-to-IPC concordance, and a small number of keyword questions.

## Testing Decisions

- A good test checks external behaviour only: given this raw query or citation, the output equals the expected provisions. No test inspects internal parser state.
- Tested through the evaluation command: the full gold set run, determinism (two runs compared byte for byte), and the corrupted-run check that must lower the score.
- Tested directly: the parser's recovered-section count against the known totals for each Act.
- A check that has never been seen failing does not count. Each of the above must be run once against a known-bad input before it is reported as passing.
- There is no prior art in this repo. The structure follows the repo's own ADRs.

## Out of Scope

- Any language model, narration, or model comparison.
- Embeddings, reranking and the graph layer's effect on retrieval (they must later beat this baseline).
- The ILSI benchmark (slice 2).
- BNSS, CrPC, BSA, case law and any UI or MCP server.
- Any quality target for the score.
- Committing the Act texts to a public repository until their reuse terms are confirmed.

## Further Notes

- Open facts: the India Code PDFs returned errors on repeated tries, and the official government reuse license text was not opened. Both are to be resolved before the texts are published, not before development.
- If you want the score published, a lawyer should review the correspondence items first.
- This spec has not been seen by the ticket workflow yet. Approve it, and the next step is spec to tickets.
