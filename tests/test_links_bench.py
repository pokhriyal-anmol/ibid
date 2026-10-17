"""Slice 7 ticket 06: `ibid links bench`, links v1 scored on an ILSI split with the benchmark's scorer. Invented fixture only."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import bench, index
from ibid.cli import main
from ibid.parse import Provision

L = {n: f"Section {n} in The Indian Penal Code" for n in (1, 2, 3, 4)}
CASES = [{"id": "c1", "text": ["theft of property"], "labels": [L[1], L[2]]},
         {"id": "c2", "text": ["murder"], "labels": [L[3]]}]
PROVS = [Provision("IPC 1", "1. Theft.—theft of property", None, ()),
         Provision("IPC 2", "2. Punishment for theft.—punished", None, ()),
         Provision("IPC 3", "3. Murder.—murder", None, ()), Provision("IPC 4", "4. Zebra.—zebra", None, ())]


class LinksBenchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVS, []).close()
        (self.tmp / "labels.json").write_text(json.dumps({v: i for i, v in enumerate(L.values())}))
        self.test, self.dev = self.tmp / "test.jsonl", self.tmp / "dev.jsonl"
        self.test.write_text("".join(json.dumps(c) + "\n" for c in CASES))
        self.dev.write_text(json.dumps(CASES[0]) + "\n")
        self.manifest = self.tmp / "manifest.json"
        self.manifest.write_text(json.dumps({n: {"sha256": bench.sha256(str(p))} for n, p in
                                             {"test.jsonl": self.test, "dev.jsonl": self.dev, "labels.json": self.tmp / "labels.json"}.items()}))
        knobs = {"bm25_b": 0.75, "bm25_k1": 1.2, "levels": "all", "stem": "none"}
        stop = sorted(bench.STOP_WORDS)
        self.frozen, self.ledger = self.tmp / "frozen.json", self.tmp / "ledger.json"
        self.frozen.write_text(json.dumps({"k": 1, "r": 1.0, "section_score": "max", "stop_words": stop, "knobs": knobs,
                                           "rule": {"name": "query-rule", "version": "v9",
                                                    "params_sha256": bench.rule_hash(1, 1.0, "max", stop, knobs)}}))

    def run_bench(self, split, out="out.json", *extra):
        with contextlib.redirect_stderr(io.StringIO()):
            return main(["links", "bench", "--split", str(split), "--labels", str(self.tmp / "labels.json"),
                         "--index", str(self.tmp / "i.sqlite"), "--manifest", str(self.manifest), "--frozen-rule", str(self.frozen),
                         "--ledger", str(self.ledger), "--out", str(self.tmp / out), *extra])

    def test_expanded_predictions_are_scored_and_the_test_split_recorded(self):
        frozen_before = self.frozen.read_bytes()
        self.assertEqual(self.run_bench(self.test), 0)
        res = json.loads((self.tmp / "out.json").read_text())
        self.assertEqual((res["layer"], res["layer_version"]), ("links", "v1"))
        self.assertEqual(res["split_sha256"], bench.sha256(str(self.test)))
        self.assertEqual(res["frozen_rule_sha256"], bench.sha256(str(self.frozen)))
        self.assertEqual(len(res["link_set_sha256"]), 64)
        # c1 predicts IPC 1 and gains its partner IPC 2; without the partner micro-F1 would be 0.8
        self.assertEqual(res["outputs"]["top-k"]["scores"]["micro_f1"], 1.0)
        self.assertEqual(res["outputs"]["top-k"]["mean_predictions"], 1.5)
        self.assertEqual(res["outputs"]["threshold"]["scores"]["micro_f1"], 1.0)
        [entry] = json.loads(self.ledger.read_text())
        self.assertEqual(entry["split_sha256"], res["split_sha256"])
        self.assertEqual(self.frozen.read_bytes(), frozen_before)

    def test_second_scoring_of_the_test_split_is_refused_and_the_ledger_untouched(self):
        self.assertEqual(self.run_bench(self.test), 0)
        before = self.ledger.read_bytes()
        self.assertEqual(self.run_bench(self.test, "again.json"), 1)
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertFalse((self.tmp / "again.json").exists())
        self.assertEqual(self.run_bench(self.test, "again.json", "--rescore-test"), 0)
        self.assertEqual(len(json.loads(self.ledger.read_text())), 2)

    def test_dev_split_never_reaches_the_ledger_and_can_repeat(self):
        self.assertEqual(self.run_bench(self.dev), 0)
        self.assertEqual(self.run_bench(self.dev), 0)
        self.assertFalse(self.ledger.exists())

    def test_compare_shows_both_outputs_with_mean_predictions(self):
        self.run_bench(self.test)
        qset = self.tmp / "set.json"  # `charges compare` insists on one multi-charge set and its baseline file
        qset.write_text(json.dumps({"label_policy": "x", "items": [{"id": "s0", "query": "theft", "source": "x"}]}))
        t = {"recall": 0.1, "all_charges_hit": 0.0, "mean_predictions": 5.0, "charges": 10, "items": 1}
        rule = {"name": "query-rule", "version": "v9", "params_sha256": "r" * 64}
        base = self.tmp / "base.json"
        base.write_text(json.dumps({
            "inputs": {"set_sha256": bench.sha256(str(qset)), "index_sha256": "i" * 64}, "act": "IPC", "rule": rule,
            "label_basis": {}, "top_k": t, "threshold": t,
            "scorings_of_this_rule_version": [{"rule": rule, "scores": {"top_k": t, "threshold": t}}]}))
        report = self.tmp / "r.md"
        with contextlib.redirect_stderr(io.StringIO()):
            code = main(["charges", "compare", "--results", str(base), "--set", str(qset),
                         "--ilsi", str(self.tmp / "out.json"), "--out", str(report)])
        self.assertEqual(code, 0)
        rows = [l for l in report.read_text().splitlines() if l.startswith("| links | v1 | test |")]
        for out in ("top-k", "threshold"):
            self.assertEqual(len([r for r in rows if f"| {out} |" in r and r.rstrip(" |").endswith("| 1.50")]), 1, rows)


if __name__ == "__main__":
    unittest.main()
