# Predictions files for sets v1 and v2 under assoc-nb v3, scored once per Act

Status: done
Blocked by: 01, 02

What to build: make `ibid assoc predict` with a v3 model write predictions files naming layer `assoc-nb` version `v3`, the model hash and train source `ilsi+ilsic-lay` (the current code maps any non-v2 version to `ilsi`; fix that from the header). Then run, once each, `ibid assoc predict` for set v1 and set v2 and `ibid charges score --predictions` per set and Act, writing `results/multicharge-v1-assoc-v3-{ipc,bns}.json` and `results/multicharge-v2-assoc-v3-{ipc,bns}.json`. A second scoring of the same version on the same set and Act is refused without `--rescore`.

User stories: 3, 7.

Acceptance criteria:
- A test drives `ibid assoc predict` with a small invented v3 model and asserts layer, version `v3`, model hash and train source in the output.
- A test feeds `ibid charges score` a predictions file with the wrong layer version for its results name (known-bad) and sees it refused; a test scores a v3 file twice and sees the second refused.
- The four results files exist, each records the v3 model SHA-256 and the set hash, and each was scored once (no `--rescore` used).
- All pre-existing files under `results/`, `gold/`, `concordance/` and the frozen rule are byte-identical (`git diff --exit-code` on them).
