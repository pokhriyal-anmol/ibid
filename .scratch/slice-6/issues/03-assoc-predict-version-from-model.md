# `ibid assoc predict` names the layer version and training source from the model header

Status: done
Blocked by: 02

What to build: `assoc.predict` takes `layer_version` from the model file's header instead of the module constant, and copies the header's train SHA-256 and a `train_source` (`ilsi` or `ilsic-lay`) into the predictions file's `inputs`. A v1 model keeps `layer_version: v1`. No change to ranking, k, or the BNS side (verified Concordance entries only).

User stories: 3.

Acceptance criteria (through `ibid assoc predict` and `ibid charges score --predictions` in `tests/test_assoc.py`):
- A v2 model fitted on the ticket 2 fixture writes predictions with `layer: assoc-nb`, `layer_version: v2`, and the model hash in `inputs.model`.
- A v1 model still writes `layer_version: v1`; its predictions for the existing fixture differ from before only by the added `inputs` fields.
- Known-bad run, observed once: hard-coding `v1` makes the v2 assertion fail.
- The v2 predictions file passes the scorer's existing predictions validation.
