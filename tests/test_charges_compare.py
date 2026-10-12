"""Slice 3 ticket 11: `charges compare`. Invented results files and sets; nothing here is a measured score."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ibid.cli import main

INDEX = "i" * 64
LABELS = {"agent-drafted-skeptic-refuted": 2}


def figs(f):
    return {**f, "charges": 10, "items": 2}


class CompareTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sets = {}
        for name, queries in (("setA", ["he caused harm under section 302", "he took the bag"]), ("setB", ["a quarrel", "a theft"])):
            p = self.tmp / f"{name}.json"
            p.write_text(json.dumps({"items": [{"id": f"{name}{n}", "query": q} for n, q in enumerate(queries)]}))
            self.sets[name] = (p, hashlib.sha256(p.read_bytes()).hexdigest())

    def baseline(self, name, act, topk, thr, extra=()):
        v = "v2.11"
        rule = {"name": "query-rule", "version": v, "params_sha256": "r" * 64}
        entries = [{"rule": rule, "scores": {"top_k": topk, "threshold": thr}}, *extra]
        return self.write(f"base-{name}-{act}", {
            "inputs": {"set_sha256": self.sets[name][1], "index_sha256": INDEX}, "act": act, "rule": rule, "label_basis": LABELS,
            "top_k": figs(topk), "threshold": figs(thr), "scorings_of_this_rule_version": entries})

    def layer(self, layer, name, act, out, inputs, extra=(), counts=None):
        entries = [{"scores": {"output": out}}, *[{"scores": {"output": e}} for e in extra]]
        return self.write(f"{layer}-{name}-{act}", {
            "inputs": {"set_sha256": self.sets[name][1], "index_sha256": INDEX, "layer": inputs}, "act": act, "layer": layer,
            "layer_version": "v1", "label_basis": LABELS, "output": figs(out), "layer_counts": counts or {}, "scorings_of_this_layer_version": entries})

    def write(self, stem, d):
        p = self.tmp / f"{stem}.json"
        p.write_text(json.dumps(d))
        return str(p)

    def run_compare(self, results, ilsi=(), sets=("setA", "setB"), out="r.md", expect=0):
        args = ["charges", "compare", "--out", str(self.tmp / out)]
        for r in results:
            args += ["--results", r]
        for s in sets:
            args += ["--set", str(self.sets[s][0])]
        for i in ilsi:
            args += ["--ilsi", i]
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(args)
        self.assertEqual(code, expect, err.getvalue())
        return (self.tmp / out).read_text() if expect == 0 else err.getvalue()

    def fixture(self):
        t = lambda r, h, m: {"recall": r, "all_charges_hit": h, "mean_predictions": m}  # noqa: E731
        res = []
        for name, shift in (("setA", 0.0), ("setB", 0.1)):
            res.append(self.baseline(name, "IPC", t(0.1 + shift, 0.0, 5.0), t(0.2 + shift, 0.0, 8.0)))
            res.append(self.layer("cited", name, "IPC", t(0.6 + shift, 0.5, 2.0), {"concordance": "c" * 64}, counts={"unmapped_citations": 7}))
            res.append(self.layer("assoc-nb", name, "IPC", t(0.5, 0.0, 5.0), {"model": "m" * 64, "concordance": "c" * 64},
                                  extra=[t(0.45, 0.0, 5.0)] if name == "setA" else ()))
            res.append(self.layer("decomposed", name, "IPC", t(0.4, 0.5, 8.0), {"producer": "sub-agents sonnet", "per_subquery": 2},
                                  counts={"subqueries_per_item_mean": 4.5}))
        return res

    def lines(self, text, start):
        return [ln for ln in text.splitlines() if ln.startswith(start)]

    def test_table_values_and_differences_equal_the_hand_computed_ones(self):
        text = self.run_compare(self.fixture())
        row = next(ln for ln in text.splitlines() if ln.startswith("| assoc-nb | v1 | setA"))
        # 5 of 10 found; recall 50.0, minus top-k 10.0 and threshold 20.0; all-hit 0.0 minus 0.0 and 0.0; 5.00 predictions.
        self.assertEqual([c.strip() for c in row.strip("|").split("|")][6:],
                         ["5 of 10", "50.0", "+40.0", "+30.0", "0.0", "+0.0", "+0.0", "5.00"])
        row = next(ln for ln in text.splitlines() if ln.startswith("| cited | v1 | setB"))
        self.assertEqual([c.strip() for c in row.strip("|").split("|")][6:],
                         ["7 of 10", "70.0", "+50.0", "+40.0", "50.0", "+50.0", "+50.0", "2.00"])
        self.assertIn("setA | " + self.sets["setA"][1][:12], text)

    def test_baseline_rows_come_first(self):
        text = self.run_compare(list(reversed(self.fixture())))
        table = [ln for ln in text.splitlines() if ln.startswith("| ") and "| IPC" in ln and "set sha256" not in ln][:8]
        self.assertEqual([r.split("|")[1].strip() for r in table[:4]], ["baseline"] * 4)
        self.assertEqual([r.split("|")[6].strip() for r in table[:2]], ["top-k", "threshold"])

    def test_each_caveat_appears_only_for_the_layers_it_applies_to(self):
        text = self.run_compare(self.fixture())
        section = {p.split("\n")[0]: p for p in text.split("### ")[1:]}
        self.assertEqual(sorted(section), ["assoc-nb v1", "baseline v2.11", "cited v1", "decomposed v1"])
        for name, p in section.items():
            self.assertEqual("Learned weights" in p, name == "assoc-nb v1", name)
            self.assertEqual("A model produced an input" in p, name == "decomposed v1", name)
            self.assertEqual("paraphrase" in p, name == "decomposed v1", name)
            self.assertEqual("drafted from the sections the queries name" in p, name == "cited v1", name)
            self.assertEqual("unmapped_citations 7" in p, name == "cited v1", name)
            self.assertEqual("subqueries_per_item_mean 4.5" in p, name == "decomposed v1", name)
            self.assertIn("1 of 2 queries name their sections", p)  # setA has one query citing "section 302"
            self.assertIn("0 of 2 queries name their sections", p)

    def test_two_scorings_of_one_layer_version_are_both_shown(self):
        text = self.run_compare(self.fixture())
        p = next(p for p in text.split("### ")[1:] if p.startswith("assoc-nb"))
        self.assertIn("2 scorings of this layer version on set setA, IPC", p)
        self.assertIn("recall 50.0", p)
        self.assertIn("recall 45.0", p)
        self.assertIn("1 scoring of this layer version on set setB", p)

    def test_two_runs_are_byte_identical(self):
        a = self.run_compare(self.fixture(), out="a.md")
        b = self.run_compare(list(reversed(self.fixture())), out="b.md")
        self.assertEqual(a, b)

    def test_every_row_carries_its_set_hash_layer_version_and_input_hashes(self):
        text = self.run_compare(self.fixture())
        for _, h in self.sets.values():
            self.assertIn(h, text)
        self.assertIn(INDEX, text)
        self.assertIn("m" * 64, text)
        self.assertIn("r" * 64, text)
        self.assertEqual(len([ln for ln in text.splitlines() if ln.startswith("| ") and self.sets["setA"][1] in ln]), 5)  # 2 baseline outputs and 3 layers

    def test_ilsi_is_a_separate_table_labelled_as_a_different_task(self):
        rule = {"version": "v2.11", "params_sha256": "r" * 64}
        sc = lambda m, a, j: {"micro_f1": m, "macro_f1": a, "jaccard": j}  # noqa: E731
        b = self.write("ilsi-base", {"cases": 5, "inputs": {"split_sha256": "s" * 64}, "rule": rule, "scores": sc(0.0937, 0.0607, 0.0543),
                                    "test_scores": [{"split_sha256": "s" * 64, "rule": rule, "threshold_scores": sc(0.0964, 0.0621, 0.0552)}]})
        a = self.write("ilsi-assoc", {"cases": 5, "k": 5, "layer": "assoc-nb", "layer_version": "v1", "model_sha256": "m" * 64, "split_sha256": "s" * 64,
                                     "scores": sc(0.3538, 0.1797, 0.2276), "test_scores": []})
        d = self.write("ilsi-assoc-dev", {"cases": 6, "k": 5, "layer": "assoc-nb", "layer_version": "v1", "model_sha256": "m" * 64,
                                         "split_sha256": "d" * 64, "scores": sc(0.352, 0.1792, 0.226)})
        text = self.run_compare(self.fixture(), ilsi=[a, b, d])
        head, _, ilsi = text.partition("## ILSI splits, a different task")
        self.assertIn("not comparable", ilsi)
        self.assertIn("| assoc-nb | v1 | test | " + "s" * 64 + " | top-5 | " + "m" * 64 + " | 5 | 35.4 | 18.0 | 22.8 |", ilsi)
        self.assertIn("| assoc-nb | v1 | dev | " + "d" * 64 + " | top-5 | " + "m" * 64 + " | 6 | 35.2 | 17.9 | 22.6 |", ilsi)
        self.assertIn("| baseline | v2.11 | test | " + "s" * 64 + " | top-k | " + "r" * 64 + " | 5 | 9.4 | 6.1 | 5.4 |", ilsi)
        self.assertIn("| baseline | v2.11 | test | " + "s" * 64 + " | threshold | " + "r" * 64 + " | 5 | 9.6 | 6.2 | 5.5 |", ilsi)
        self.assertNotIn("35.4", head)
        self.assertNotIn("## ILSI", self.run_compare(self.fixture(), out="n.md"))

    def test_known_bad_inputs_are_refused(self):
        res = self.fixture()
        no_base = [r for r in res if "base-setB" not in r]
        self.assertIn("no baseline", self.run_compare(no_base, expect=1, out="x.md"))
        self.assertIn("is not among the --set files", self.run_compare(res, sets=("setA",), expect=1, out="y.md"))
        self.assertFalse((self.tmp / "x.md").exists() or (self.tmp / "y.md").exists())


if __name__ == "__main__":
    unittest.main()
