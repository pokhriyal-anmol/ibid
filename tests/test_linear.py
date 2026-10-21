"""Slice 13: the linear-lr layer, scored through `ibid assoc eval`. A hand-computed two-term model, no real case text."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import bench
from ibid.cli import main
from test_assoc import LABELS, imports_of

# idf 1 and one unit-length term per case: "knife" gives x=[1,0], z(100)=4-2=2, p=0.8808; "purse" gives z(101)=2; any other
# text has x=0, so every label sits at z=-2, p=0.1192. Labels 102..105 have zero weights.
MODEL = {"header": {"layer": "linear-lr", "layer_version": "v1", "cutoff": 0.5},
         "labels": list(LABELS.values()), "vocab": ["knife", "purse"], "idf": [1.0, 1.0],
         "coef": [[4, -4], [-4, 4], [0, 0], [0, 0], [0, 0], [0, 0]], "intercept": [-2] * 6}
ROWS = [("d1", ["knife"], 100), ("d2", ["purse"], 101), ("d3", ["cheating"], 102)]


class LinearTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.dev = self.split("dev.jsonl", ROWS)
        self.test = self.split("test.jsonl", ROWS)
        (self.tmp / "man.json").write_text(json.dumps({"test.jsonl": {"sha256": bench.sha256(str(self.test))}}))

    def split(self, name, rows) -> Path:
        p = self.tmp / name
        p.write_text("".join(json.dumps({"id": i, "text": t, "labels": [LABELS[n]]}) + "\n" for i, t, n in rows))
        return p

    def model(self, **change) -> Path:
        m = json.loads(json.dumps(MODEL))
        m["header"].update(change.pop("header", {}))
        m.update(change)
        (self.tmp / "m.json").write_text(json.dumps(m))
        return self.tmp / "m.json"

    def eval(self, split, expect=0, **change):
        model = self.model(**change)
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = main(["assoc", "eval", "--model", str(model), "--split", str(split), "--manifest", str(self.tmp / "man.json"),
                         "--ledger", str(self.tmp / "ledger.json"), "--out", str(self.tmp / "e.json")])
        self.assertEqual(code, expect, err.getvalue())
        return json.loads((self.tmp / "e.json").read_text()) if expect == 0 else err.getvalue()

    def test_scores_equal_hand_computed_values(self):
        s = self.eval(self.dev)["scores"]  # d1 and d2 each find their label, d3 predicts nothing: tp 2, fn 1; Jaccard 1, 1, 0
        self.assertEqual((s["micro_f1"], s["jaccard"]), (0.8, round(2 / 3, 6)))

    def test_the_cutoff_in_the_file_decides_what_is_predicted(self):
        # known-bad input: at 0.05 every label with p >= 0.05 is predicted, tp 3, fp 13 over the three cases
        self.assertEqual(self.eval(self.dev, header={"cutoff": 0.05})["scores"]["micro_f1"], round(6 / 19, 6))

    def test_test_split_is_scored_once_and_the_ledger_names_the_layer(self):
        self.assertEqual(len(self.eval(self.test)["test_scores"]), 1)
        self.assertIn("already scored", self.eval(self.test, expect=1))
        entry = json.loads((self.tmp / "ledger.json").read_text())[0]
        self.assertEqual((entry["layer"], entry["layer_version"]), ("linear-lr", "v1"))

    def test_a_coefficient_matrix_that_does_not_match_the_vocabulary_is_refused(self):
        self.assertIn("does not match", self.eval(self.dev, expect=1, coef=[[4, -4, 1]] * 6))

    def test_layer_imports_only_the_standard_library_and_ibid(self):
        src = (Path(__file__).parents[1] / "src" / "ibid" / "linear.py").read_text()
        self.assertLessEqual(imports_of(src), {"json", "math", "re", "collections", "pathlib", ""})


if __name__ == "__main__":
    unittest.main()
