"""Slice 14 ticket 01: `ibid ilsic eval` on invented ILSIC-format files. Scores are hand-computed in the comments."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from ibid import ilsic, index
from ibid.cli import main
from ibid.parse import Provision
from test_assoc import imports_of

ROOT = Path(__file__).parent.parent
FIX = Path(__file__).parent / "fixtures" / "ilsic"
PROVS = [Provision(f"IPC {n}", w, None, ()) for n, w in ((100, "murder"), (101, "theft"), (102, "cheating"), (103, "kidnapping"))]
# Label space (6): IPC 100, 101, 102, 103 (train only, no test gold), Dowry Act s3 and IT Act s66 (no layer predicts these).
# Predictions: q1 {100}, q2 {101,102}, q3 {100}, q4 {101}, q5 {101}.
# Per label (tp,fp,fn): 100 (2,0,1) F1 .8 P 1 R 2/3 | 101 (1,2,0) F1 .5 P 1/3 R 1 | 102 (1,0,1) F1 2/3 P 1 R .5 | other three 0.
PRIMARY = {"labels": 6, "macro_f1": 0.327778, "micro_f1": 0.571429, "macro_precision": 0.388889, "macro_recall": 0.361111}  # micro: tp 4, fp 2, fn 4
SECONDARY = {"labels": 4, "macro_f1": 0.491667, "micro_f1": 0.666667, "macro_precision": 0.583333, "macro_recall": 0.541667}  # four IPC labels, fn 2


class IlsicEvalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVS, []).close()

    def run_eval(self, train=FIX / "train.jsonl", split=FIX / "test.jsonl", frozen=ROOT / "results/frozen-rule.json", expect=0, extra=()):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = main(["ilsic", "eval", "--split", str(split), "--train", str(train), "--index", str(self.tmp / "i.sqlite"),
                         "--frozen-rule", str(frozen), "--out", str(self.tmp / "o.json"), *extra])
        self.assertEqual(code, expect, err.getvalue())
        return json.loads((self.tmp / "o.json").read_text()) if expect == 0 else err.getvalue()

    def test_both_readings_equal_hand_computed(self):
        res = self.run_eval()
        self.assertEqual(res["primary"], PRIMARY)
        self.assertEqual(res["secondary_vocabulary"], SECONDARY)
        self.assertEqual((res["label_space"], res["queries"], res["layer"], res["version"]), (6, 5, "frozen-rule", "v2.11"))
        self.assertIn("scoring 0", res["assumption"])

    def test_label_space_reads_the_train_answers_too(self):
        empty = self.tmp / "t.jsonl"
        empty.write_text(json.dumps({"instruction": "x", "answer": ["Section 100 of The Indian Penal Code, 1860"]}) + "\n")
        self.assertEqual(self.run_eval(train=empty)["label_space"], 5)  # no train-only IPC 103

    def test_a_frozen_rule_that_does_not_hold_its_hash_is_refused(self):
        bad = json.loads((ROOT / "results/frozen-rule.json").read_text())
        bad["r"] = 0.5
        (self.tmp / "f.json").write_text(json.dumps(bad))
        self.assertIn("does not hold the rule", self.run_eval(frozen=self.tmp / "f.json", expect=1))

    def test_the_rule_gets_the_raw_query_and_no_network_or_model_client_is_imported(self):
        src = (ROOT / "src/ibid/ilsic.py").read_text()
        self.assertTrue(imports_of(src) <= {"json", "random", "re", "sqlite3", "sys", "pathlib", "ibid"})
        self.assertIn('row["instruction"]', src)

    def test_interval_is_deterministic_and_holds_the_point_estimate(self):
        a, b = self.run_eval()["interval_95"], self.run_eval()["interval_95"]
        self.assertEqual(a, b)
        self.assertEqual(a, {"macro_f1": [0.066667, 0.5], "micro_f1": [0.181818, 0.823529]})  # pinned: seed 0 on this fixture
        for m, point in (("macro_f1", PRIMARY["macro_f1"]), ("micro_f1", PRIMARY["micro_f1"])):
            self.assertLessEqual(a[m][0], point)
            self.assertGreaterEqual(a[m][1], point)
            self.assertLess(a[m][0], a[m][1])

    def test_verdict_uses_the_primary_reading_only(self):
        # Fixture micro-F1: primary 57.14, secondary 66.67. A published 60 is cleared only under the secondary reading.
        with mock.patch.dict(ilsic.PUBLISHED, {"lay": [("micro_f1", 60.0, "x", "Table 3"), ("micro_f1", 50.0, "y", "Table 3")]}):
            v = self.run_eval()["verdict_primary_reading"]
        self.assertTrue(v[0].startswith("micro_f1 57.14: below 60.00"), v)
        self.assertTrue(v[1].startswith("micro_f1 57.14: above 50.00"), v)
        self.assertIn("published, not re-run by us", v[0])

    def test_benchmark_flag_picks_the_published_numbers_and_they_carry_tables(self):
        self.assertEqual(len(self.run_eval()["verdict_primary_reading"]), 3)
        self.assertEqual(len(self.run_eval(extra=("--benchmark", "multi"))["verdict_primary_reading"]), 2)
        self.assertTrue(all(len(p) == 4 and p[3].startswith("Table") for ps in ilsic.PUBLISHED.values() for p in ps))


if __name__ == "__main__":
    unittest.main()
