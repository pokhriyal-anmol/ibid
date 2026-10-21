# ibid ilsic eval scores assoc-nb and linear-lr model files

Status: done
Blocked by: 01

What to build: let `ibid ilsic eval` take a model file in place of the frozen rule. Load `assoc-nb` through `assoc.open_model` and `linear-lr` through `linear.LinearModel`, predict offline on the raw `instruction`, and record layer name, layer version and model sha256 in the results file. The secondary reading uses the model's own label vocabulary. The command takes the expected layer version as an argument and refuses a model file whose header names a different layer or version. Nothing is refit.

User stories: 1 (model layers), 5.

Acceptance criteria:
- A tiny invented model of each kind in `tests/fixtures/ilsic/`; a `unittest` through the command checks both readings against hand-computed values and that layer, version and model hash appear in the results file.
- A model file of another layer version is refused with a non-zero exit and no results file written; this test is seen to fail once with the check removed.
- No network or model call at scoring time other than the layer's own offline prediction (ADR 0005, 0009).
