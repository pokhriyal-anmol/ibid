"""Slice 2 ticket 02: `ibid bench run` scores a split with query rule v1 and top-k. Invented fixture only."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ibid import bench, index
from ibid.cli import main
from ibid.parse import Provision


def prov(cite, text, parent=None):
    return Provision(cite, text, parent, ())


PROVISIONS = [
    prov("IPC 1", "theft of movable property dishonestly"),
    prov("IPC 2", "murder causing death with intention"),
    prov("IPC 3", "cheating"),
    prov("IPC 3(1)", "deceiving by personation", "IPC 3"),
    prov("IPC 4", "kidnapping from lawful guardianship"),
    prov("IPC 9", "zebra"),  # outside the label space
    prov("BNS 5", "theft of movable property"),
]
L = {n: f"Section {n} in The Indian Penal Code" for n in (1, 2, 3, 4)}
CASES = [
    {"id": "c1", "text": ["He committed theft,", "of movable property."], "labels": [L[1]]},
    {"id": "c2", "text": ["A well-known cheat, deceiving the victim by personation."], "labels": [L[3], L[2]]},
    {"id": "c3", "text": ['Quotes: "zebra" -- hyphen-ated; murder!'], "labels": [L[2]]},
]


class BenchRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVISIONS, []).close()
        (self.tmp / "labels.json").write_text(json.dumps({label: i for i, label in enumerate(L.values())}))

    def run_bench(self, cases=CASES, k=1, out="out.json", sample=None, split_name="split.jsonl", expect=0):
        split = self.tmp / split_name
        split.write_text("".join(json.dumps(c) + "\n" for c in cases))
        out_path = self.tmp / out
        extra = [] if sample is None else ["--sample"] + ([str(sample)] if sample else [])
        with contextlib.redirect_stderr(io.StringIO()):
            code = main(["bench", "run", "--split", str(split), "--labels", str(self.tmp / "labels.json"),
                         "--index", str(self.tmp / "i.sqlite"), "--k", str(k), "--out", str(out_path)] + extra)
        self.assertEqual(code, expect)
        return json.loads(out_path.read_text()) if expect == 0 else None

    def test_scores_match_hand_computed(self):
        # preds c1 {1}, c2 {3}, c3 {2}. micro tp3 fp0 fn1 = 6/7; per-label F1 1, 2/3, 1, 0 so macro 2/3; jaccard 1, 1/2, 1.
        self.assertEqual(self.run_bench()["scores"], {"micro_f1": round(6 / 7, 6), "macro_f1": round(2 / 3, 6), "jaccard": round(5 / 6, 6)})

    def test_predictions_are_sections_inside_the_label_space(self):
        # c2 hits only IPC 3(1), so IPC 3 is its roll-up; IPC 9 (outside the labels) outranks IPC 2 in c3 and must be dropped.
        self.assertEqual(self.run_bench()["predictions"], {"c1": ["IPC 1"], "c2": ["IPC 3"], "c3": ["IPC 2"]})

    def test_punctuated_paragraph_returns_hits(self):
        self.assertTrue(self.run_bench(k=5)["predictions"]["c3"])

    def test_same_inputs_give_byte_identical_results(self):
        self.run_bench(out="a.json")
        self.run_bench(out="b.json")
        self.assertEqual((self.tmp / "a.json").read_bytes(), (self.tmp / "b.json").read_bytes())

    def test_stop_word_change_changes_rule_hash(self):
        base = self.run_bench()["rule"]["params_sha256"]
        with mock.patch.object(bench, "STOP_WORDS", bench.STOP_WORDS[1:]):
            self.assertNotEqual(self.run_bench()["rule"]["params_sha256"], base)

    def test_records_inputs_rule_parser_k_and_conventions(self):
        r = self.run_bench(k=2)
        self.assertEqual(set(r["inputs"]), {"split_sha256", "labels_sha256", "index_sha256"})
        self.assertEqual((r["rule"]["name"], r["rule"]["version"], r["k"]), ("query-rule", "v1", 2))
        self.assertTrue(r["parser_version"])
        self.assertIn("scores 0", r["conventions"]["macro_f1"])

    def test_shuffled_labels_lower_the_score(self):
        golds = [c["labels"] for c in CASES]
        shuffled = [{**c, "labels": g} for c, g in zip(CASES, golds[1:] + golds[:1])]
        self.assertLess(self.run_bench(shuffled)["scores"]["micro_f1"], self.run_bench()["scores"]["micro_f1"])

    def test_k_caps_the_number_of_predicted_sections(self):
        two = [{"id": "t", "text": ["theft and murder"], "labels": [L[1]]}]
        self.assertEqual(len(self.run_bench(two, k=1)["predictions"]["t"]), 1)
        self.assertEqual(sorted(self.run_bench(two, k=2)["predictions"]["t"]), ["IPC 1", "IPC 2"])

    def test_case_with_no_usable_terms_predicts_nothing(self):
        r = self.run_bench([{"id": "x", "text": ["the of and"], "labels": [L[1]]}])
        self.assertEqual((r["predictions"], r["scores"]["micro_f1"]), ({"x": []}, 0.0))

    def test_sample_scores_the_first_n_by_sorted_id_and_says_so(self):
        # file order is c3, c1, c2 on purpose: the rule is sorted id, not file order.
        shuffled = [CASES[2], CASES[0], CASES[1]]
        r = self.run_bench(shuffled, sample=2)
        self.assertEqual((r["cases"], sorted(r["predictions"])), (2, ["c1", "c2"]))
        self.assertEqual((r["sample"], r["sample_rule"]), (2, "first N cases by sorted id"))

    def test_full_run_states_no_sample(self):
        r = self.run_bench()
        self.assertNotIn("sample", r)
        self.assertNotIn("sample_rule", r)

    def test_sample_without_a_value_means_200(self):
        r = self.run_bench(sample=0)
        self.assertEqual((r["sample"], r["cases"]), (200, 3))  # fewer cases than N: all of them

    def test_two_sample_runs_are_byte_identical(self):
        self.run_bench(sample=2, out="a.json")
        self.run_bench(sample=2, out="b.json")
        self.assertEqual((self.tmp / "a.json").read_bytes(), (self.tmp / "b.json").read_bytes())

    def test_sample_on_the_test_split_is_refused_and_writes_nothing(self):
        self.run_bench(sample=2, split_name="test.jsonl", expect=1)
        self.assertFalse((self.tmp / "out.json").exists())

    def test_full_run_on_the_test_split_is_not_refused_by_sample_guard(self):
        self.assertNotIn("sample", self.run_bench(split_name="test.jsonl"))

    def test_sample_of_five_item_split_scores_exactly_three(self):
        five = [{"id": f"i{n}", "text": ["theft"], "labels": [L[1]]} for n in (5, 4, 3, 2, 1)]
        r = self.run_bench(five, sample=3)
        self.assertEqual((r["cases"], sorted(r["predictions"])), (3, ["i1", "i2", "i3"]))

    def test_sample_below_one_is_refused(self):
        self.run_bench(sample=-1, expect=1)


if __name__ == "__main__":
    unittest.main()
