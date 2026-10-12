# Collect the first 30 multi-charge items from real judgment text

Status: needs-triage
Blocked by: 01

Note: this is data work. It is run by a dedicated workflow of agents after ticket 01 is built, not by `wf-build`, which would treat it as code.

What to build: the first version of the set, `gold/multicharge/v1.json` with its pin, 30 items, made by a workflow of agents and committed to this private repository. The owner decided on 2026-10-12 that agents write the labels and that the set lives in the repository.

Queries. Each query is the fact text of a real case in the LeSICiN `train` split (Zenodo record 6053791, CC BY 4.0, already anonymised by its authors), joined from its sentences and cut at a sentence boundary. No query is written by an agent. Selection is by a deterministic written rule, made without reading any case text:

- candidates are train cases whose benchmark labels hold at least two offence sections, where IPC 34, 149 and 120B are not counted as offences for the selection;
- the fact text is between 150 and 600 words;
- from the candidates, 10 items with 2 offence labels, 10 with 3 and 10 with 4 or more, taking the cases whose SHA-256 of `id` sorts first in each group.

Labels. For each item, one agent reads only the fact text and drafts the charges and, for each charge, the IPC sections and the BNS sections it would accept, working from the Act text in the index and the Act PDFs, not from the benchmark labels and not from any retrieval output. A second agent, a skeptic, tries to refute each charge and each section and defaults to refuted when unsure. Only charges that survive are written. Each item records `label_basis: agent-drafted-skeptic-refuted` and `reviewed_by` with the skeptic pass id. Benchmark labels are compared with the agents' sections afterwards and the agreement is reported as a signal, never used to correct a label. The file states plainly that no lawyer has reviewed these labels.

User stories: 1, 2, 3, 5.

Acceptance criteria:
- `ibid charges validate` passes on the file and prints 30 items with the 10, 10, 10 charge-count mix the rule asked for (item charge counts come from the agents, so the printed histogram is reported, not forced).
- Every item has `author_type: judgment-excerpt`, a `source` naming the dataset and case id, `anonymised: true` and `label_basis: agent-drafted-skeptic-refuted`.
- No agent saw a benchmark label or a retrieval result while drafting (stated in the workflow prompts and checked by reading them).
- The report of the run lists: items selected and the selection rule hash, charges drafted, charges refuted and dropped, items that lost all charges (and what replaced them under the same rule), the agreement with the benchmark labels, and the counts of charges with no BNS counterpart.
- The file is committed with its pin, the licence note and the attribution, and the repository stays private.
- No change to any file under `data/raw/`.
