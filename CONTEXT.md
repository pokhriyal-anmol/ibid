# Ibid

A local, deterministic retrieval engine for Indian criminal statute (the IPC and the BNS) that returns verbatim text and exact citations. The language model is replaceable. The evidence is not.

## Language

**Act**:
One statute as published in the Gazette of India. v1 holds two: the IPC (1860) and the BNS (2023).
_Avoid_: Law, code, statute (unqualified)

**Section tree**:
The parsed structure of one Act: sections, subsections, clauses, provisos, explanations, exceptions and illustrations, each with a stable address.
_Avoid_: Document, chunk

**Provision**:
Any addressable node in a section tree, such as BNS 103(1) or the first proviso to BNS 8(2).
_Avoid_: Passage, snippet

**Citation**:
The canonical string form of a provision's address, such as "BNS 103(1)". Two citations are equal only if their strings are byte-identical.
_Avoid_: Reference (reserved for cross-reference)

**Cross-reference**:
A pointer inside the text of one provision to another provision, such as "as defined in section 2(8)". Resolved to a citation by rule, never by a model.
_Avoid_: Link, mention

**Cross-reference graph**:
The directed graph of resolved cross-references across both Acts, built by deterministic parsing.
_Avoid_: Knowledge graph, GraphRAG graph

**Concordance**:
The mapping between an IPC provision and the BNS provision that replaced it. One IPC provision may map to several BNS provisions, and the reverse.
_Avoid_: Conversion table, converter

## Retrieval

**Raw query**:
The exact string the user typed. The only input to retrieval.
_Avoid_: Prompt, rewritten query

**Evidence packet**:
The ordered set of verbatim provisions, citations and resolved cross-references that code returns for a raw query. Byte-identical for any model.
_Avoid_: Context, retrieved chunks

**Narration**:
The prose a model writes around an evidence packet. Every citation in it must appear in the packet.
_Avoid_: Answer, response (unqualified)

## Measurement

**Gold set**:
The frozen, hash-pinned list of questions with answers verified against the Gazette text. Edits create a new version.
_Avoid_: Test data, ground truth

**Baseline**:
The first scored run of the simplest retrieval that works. Every later layer (embeddings, graph) must beat it on the gold set to stay.
_Avoid_: Benchmark (reserved for external benchmarks such as ILSI)

**Slice**:
One tracer-bullet increment that is demoable and verifiable on its own.
_Avoid_: Phase, milestone
