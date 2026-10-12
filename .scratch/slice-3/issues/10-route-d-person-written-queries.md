# Route D: a kit for collecting queries that a person writes in their own words

Status: done
Blocked by: none

Note: the builder does the kit, the template and the intake command only. Writing the queries is the owner's step and the ticket is not closed until they exist.

What to build: the instructions and the template that let a lawyer, or the owner, write 20 to 30 realistic multi-charge queries, and the intake step that turns them into a set file. The point of this route is a measure that is not made of court orders: the text a person with a fresh case types. Every earlier number in slice 3 comes from judgment text.

Parts the builder (or the orchestrator) writes:

- `docs/multicharge-collection-kit.md`: a one-page guide for the author. Write each query as you would describe the situation to a lawyer, three to eight sentences, in your own words, with at least two different things done wrong. Real or invented situations are both fine. Do not use names, places, dates or phone numbers. Do not write section numbers. Do not ask an AI to write the query. Include three sample shapes ("a fight and a threat", "a deal gone wrong and a forged paper", "a family dispute and a death") with no case facts copied from the benchmark.
- `docs/multicharge-queries-template.txt`: one query per block, blocks separated by a line holding only `---`, with a header comment explaining the format.
- `ibid charges intake --queries <file> --author-type owner|lawyer --author <label> --out <draft-set.json>`: reads the blocks, assigns ids `d-001`, `d-002`, writes a set file in the ticket 01 format with `charges: []` and `label_basis` unset, so that it is a draft and fails `validate` until labels are added. It refuses an empty block, a block with fewer than 20 words, a block containing a run of digits that looks like a section number ("Section 302", "u/s 420"), and a duplicate block.

Parts the owner does:

- Write the queries (20 to 30) into the template file and give it to the orchestrator, or add it to the repository. This is the only step that cannot be done by code or an agent, and it is why the ticket is `ready-for-human`.

Then the orchestrator labels them with the same blind drafting and skeptic pass used for set v1 (ticket 03 prompts), with `author_type` as given, and the result is `gold/multicharge/v2.json` with its pin. The labels remain agent-drafted unless a lawyer reviews them.

User stories: 1, 2, 3.

Acceptance criteria:
- The kit and the template exist and read clearly to someone who has not seen this repository.
- `intake` on an invented fixture of four blocks writes four draft items, and each known-bad block above is refused with its reason.
- A draft set does not pass `validate`, and the same set with labels added does.
- No benchmark text appears in the kit's samples.
