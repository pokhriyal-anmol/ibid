# ibid setup reports the optional model, and the README explains it is a research option

Status: done
Blocked by: none

## What to build
`ibid setup` (`src/ibid/setup.py`) prints one optional line for `data/assoc-nb-v3.json`: present with its sha256, or absent with the fit command. It never changes the exit status. The README says how to produce the model, that the training data (ILSI, ILSIC-Lay) are gated and non-commercial, and that learned mode is a research option outside the standard install.

## User stories
10, and spec decision 8.

## Acceptance criteria
- [ ] With all tools and source PDFs present and no model file, `ibid setup` prints the optional absent line with the fit command and exits 0 (tested through `ibid setup`, as in `tests/test_setup.py`).
- [ ] With an invented model file at the path, it prints present and that file's sha256, and exits 0.
- [ ] A setup failure on a required item still exits non-zero regardless of the model line.
- [ ] README names the fit command, the gated non-commercial data, and that learned mode is opt-in; `tests/test_readme_quickstart.py` still passes.
- [ ] Known-bad run seen failing once: making an absent model fail setup breaks the exit-0 test.
