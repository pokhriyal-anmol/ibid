"""Slice 2 ticket 04: per-label and strata results in the bench results file. Invented fixture only."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import index
from ibid.cli import main
from ibid.parse import Provision


def prov(cite, text):
    return Provision(cite, text, None, ())


PROVISIONS = [prov("IPC 1", "theft of movable property"), prov("IPC 2", "murder causing death"),
              prov("IPC 3", "cheating deceiving by personation"), prov("IPC 4", "kidnapping from lawful guardianship")]
L = {n: f"Section {n} in The Indian Penal Code" for n in (1, 2, 3, 4)}
FILLER = " ".join(["zzz"] * 150)
CASES = [
    {"id": "c1", "text": ["He committed theft of movable property."], "labels": [L[1]]},
    {"id": "c2", "text": ["A cheat deceiving by personation."], "labels": [L[3], L[2]]},
    {"id": "c3", "text": ["Murder!"], "labels": [L[2]]},
    # 155 words, nothing the rule can retrieve: the Section 34 pattern (gold label never named in the facts)
    {"id": "c4", "text": ["He took the child away.", FILLER], "labels": [L[4], L[1], L[2]]},
    {"id": "c5", "text": ["murder " + " ".join(["zzz"] * 500)], "labels": [L[2]]},  # 501 words
]


class PerLabelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVISIONS, []).close()
        (self.tmp / "labels.json").write_text(json.dumps({label: i for i, label in enumerate(L.values())}))

    def run_bench(self, cases=CASES):
        split = self.tmp / "split.jsonl"
        split.write_text("".join(json.dumps(c) + "\n" for c in cases))
        out = self.tmp / "out.json"
        self.assertEqual(main(["bench", "run", "--split", str(split), "--labels", str(self.tmp / "labels.json"),
                               "--index", str(self.tmp / "i.sqlite"), "--k", "1", "--out", str(out)]), 0)
        return json.loads(out.read_text())

    def test_per_label_counts_match_hand_computed(self):
        rows = {r["citation"]: r for r in self.run_bench()["per_label"]["labels"]}
        got = {c: (r["support"], r["tp"], r["fp"], r["fn"], r["precision"], r["recall"], r["f1"]) for c, r in rows.items()}
        self.assertEqual(got, {
            "IPC 1": (2, 1, 0, 1, 1.0, 0.5, round(2 / 3, 6)),
            "IPC 2": (4, 2, 0, 2, 1.0, 0.5, round(2 / 3, 6)),
            "IPC 3": (1, 1, 0, 0, 1.0, 1.0, 1.0),
            "IPC 4": (1, 0, 0, 1, 0.0, 0.0, 0.0),
        })

    def test_rows_sorted_by_citation_and_macro_is_their_mean(self):
        r = self.run_bench()
        rows = r["per_label"]["labels"]
        self.assertEqual([x["citation"] for x in rows], sorted(x["citation"] for x in rows))
        self.assertAlmostEqual(sum(x["f1"] for x in rows) / len(rows), r["scores"]["macro_f1"], places=5)

    def test_zero_support_zero_prediction_label_is_zero_and_documented(self):
        r = self.run_bench(CASES[:1])  # labels 2, 3, 4 have no gold and nothing predicted
        row = next(x for x in r["per_label"]["labels"] if x["citation"] == "IPC 4")
        self.assertEqual((row["support"], row["precision"], row["recall"], row["f1"]), (0, 0.0, 0.0, 0.0))
        self.assertNotIn("IPC 4", r["per_label"]["never_found"])
        self.assertIn("zero support and zero predictions", r["conventions"]["per_label"])

    def test_never_found_lists_the_unretrievable_label(self):
        self.assertEqual(self.run_bench()["per_label"]["never_found"], ["IPC 4"])

    def test_strata_match_hand_computed_and_cases_sum_to_split(self):
        s = self.run_bench()["strata"]
        view = {a: {b: (v["cases"], v["scores"]["micro_f1"], v["scores"]["macro_f1"], v["scores"]["jaccard"])
                    for b, v in d.items()} for a, d in s.items()}
        self.assertEqual(view, {
            "gold_label_count": {"1": (3, 1.0, 0.5, 1.0), "2": (1, round(2 / 3, 6), 0.25, 0.5), "3+": (1, 0.0, 0.0, 0.0)},
            "words": {"<=150": (3, round(6 / 7, 6), round(2 / 3, 6), round(5 / 6, 6)), "151-500": (1, 0.0, 0.0, 0.0),
                      ">500": (1, 1.0, 0.25, 1.0)},
        })
        for d in s.values():
            self.assertEqual(sum(v["cases"] for v in d.values()), len(CASES))

    def test_empty_stratum_does_not_divide_by_zero(self):
        s = self.run_bench(CASES[:1])["strata"]["words"][">500"]
        self.assertEqual((s["cases"], s["scores"]["jaccard"]), (0, 0.0))


if __name__ == "__main__":
    unittest.main()
