# Report: set v2 section coverage by the v2 vocabulary and recall on sections v1 could not name

Status: done
Blocked by: 06

What to build: `.scratch/slice-6/v2-report.md`, short, with one diagram. It states: how many of set v2's 30 IPC sections are in the v2 vocabulary (spec expects 27 of 30 at threshold 5) and which are not; IPC recall on set v2 for v1 and v2, split into charges whose section is in v1's vocabulary (19 sections) and those that are not (11), with charge counts beside each percentage; the same for BNS where the Concordance gives a counterpart. Each figure is computed this session from the model headers and the ticket 6 predictions files by a command recorded in the report (a one-off script in the scratchpad or a `python -c` line), not copied from the spec. It repeats the label-incompleteness and in-distribution caveats and makes no claim of legal accuracy.

User stories: 6.

Acceptance criteria:
- Re-running the recorded command reproduces every number in the report.
- The split counts add up to the set's 84 IPC charges.
- The report says whether v2 beats v1 and the baseline on set v2 and on set v1, per Act, and that MCP wiring is a later slice only if it does.
- A Mermaid diagram (with subgraphs and labelled edges, per the documentation standard) shows the split of set v2 sections into the three groups: in both vocabularies, in v2 only, in neither.
