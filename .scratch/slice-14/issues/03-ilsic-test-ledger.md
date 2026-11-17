# One look per layer version and split in results/test-ledger-ilsic.json

Status: done
Blocked by: 01

What to build: on every scored run, append an entry to `results/test-ledger-ilsic.json` keyed by split file sha256 plus layer name and version (and model or rule hash), following `bench.test_guard` / `bench.read_ledger`. A second scoring of the same (layer, version, split) is refused unless `--rescore-test` is passed; with the flag the new score is appended and the first stays visible and is reported beside it.

User stories: 3.

Acceptance criteria:
- A `unittest` through `ibid ilsic eval` scores a fixture split, then a second run without `--rescore-test` exits non-zero, writes no results file and leaves the ledger byte-identical.
- With `--rescore-test` the ledger holds both entries and the first is unchanged.
- The test is seen to fail once with the guard disabled (a second scoring accepted).
- Tests write the ledger to a temp path, never to `results/`.
