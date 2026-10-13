# The report labels the frozen round as the final round, not the last logged round

Status: done
Blocked by: none (09 is done)

What to build: `ibid bench report` currently labels the last logged round "final round" even when the frozen rule came from an earlier logged round. Read the frozen round number from the frozen-rule record and use it for the headline row, labelled "frozen round (N)". If the frozen round is not the last logged round, also list the last logged round separately as "last logged round (M)", so the reader sees both and the test score is never attached to the wrong rule.

User stories: 8, 12.

Acceptance criteria:
- On a fixture log of three rounds where round 2 was frozen, the headline row says `frozen round (2)` with round 2's train and dev scores and the ledger's test score, and the last round appears on its own line.
- With the last round frozen, there is one row, labelled `frozen round (N)`, and no duplicate line.
- Known-bad: reverting the change makes the first test fail on the label text.
- Two report runs on the same inputs are byte-identical.
