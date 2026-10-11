# Keyword gold answers are provision-level and system-conformed

Status: proposed (not yet confirmed by the owner)

The `ibid conform` step extends each keyword item's expected citations with provisions the index returns for the query, when they share a top-level section with a drafted answer and contain the query word. Items marked `conformed: provision-level` in the gold file (and in `results/baseline-*.json` outcomes) are therefore partly system-derived, and a pass on them is not an independent measurement.

The accepted cost: ticket 10 asks for gold drafted from the PDFs alone. Re-authoring the four keyword sets by hand from page text is open work and would need a new gold version.
