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
_Avoid_: Link (reserved for definition-punishment link), mention

**Definition-punishment link**:
A two-way pairing of the Citation of a section headed "Punishment for X" with every other top-level section headed X, taken from IPC headings and carried to the BNS through verified Concordance entries (ADR 0007). Not a Cross-reference.
_Avoid_: Cross-reference, relation

**Cross-reference graph**:
The directed graph of resolved cross-references across both Acts, built by deterministic parsing.
_Avoid_: Knowledge graph, GraphRAG graph

**Concordance**:
The mapping between an IPC provision and the BNS provision that replaced it. One IPC provision may map to several BNS provisions, and the reverse. Each entry has a type: one-to-one, split, merged, removed (an IPC provision with no BNS successor) or new (a BNS provision with no IPC ancestor). Where several IPC provisions were regrouped into several BNS provisions (many-to-many), the entry is typed merged and lists all of both. Only verified entries are served; any other IPC provision answers "no verified concordance".
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
The first scored run of the simplest retrieval that works. Every later layer (embeddings, graph) must beat it to stay, on the same set and the same Act: the Gold set in slice 1, a Multi-charge set per charge in slice 3.
_Avoid_: Benchmark (reserved for external benchmarks such as ILSI)

**Benchmark label**:
A label string from an external benchmark (LeSICiN), mapped to a citation. Benchmark labels are not a Gold set: they were not verified against the Gazette text.
_Avoid_: Gold, ground truth

**Query rule**:
The fixed, versioned code that turns a raw query into index terms and a ranked list of sections, recorded as a rule version and a hash of its parameters ([ADR 0004](docs/adr/0004-fixed-tokenisation-of-the-raw-query.md)).
_Avoid_: Prompt, query rewriting

**Optimisation round**:
One logged change to one declared knob of the query rule, scored on train and dev, never on test.
_Avoid_: Experiment, run

**Frozen rule**:
The query rule of one logged round, recorded before the test split is scored. The test split is scored against it once.
_Avoid_: Final model, best config

**Charge**:
One alleged offence inside a query that alleges several. A Charge has its own accepted sections in each Act, and is scored as found or not found.
_Avoid_: Count, allegation, issue

**Multi-charge set**:
The frozen, hash-pinned list of queries that each allege one or more Charges, with accepted sections per Charge and Act, kept under `gold/multicharge/`. Not the Gold set: its labels have a recorded basis, some drafted by an agent and refuted by a skeptic.
_Avoid_: Test set, gold (unqualified), dataset

**Layer**:
One way of producing a predictions file for a Multi-charge set, scored by the same function as the Baseline and compared on the same set and Act. Routes A to D are cited sections, learned association, per-charge sub-queries and person-written queries. Links v1 appends Definition-punishment links to a baseline file. A layer has a name and a layer version.
_Avoid_: Model, approach, system

**Predictions file**:
The per-item sections a Layer predicts for each Act, with the hash of the set it was made for. `ibid charges score` is the only thing that scores it.
_Avoid_: Output, run, submission

**Slice**:
One tracer-bullet increment that is demoable and verifiable on its own.
_Avoid_: Phase, milestone
