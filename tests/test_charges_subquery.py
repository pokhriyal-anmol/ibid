"""Slice 3 ticket 09: `charges subquery`, route C. Invented fixture set and index."""
import contextlib
import hashlib
import io
import json
import unittest

from ibid.cli import main
from test_charges_score import ChargesScoreTest as _Base, ITEMS, frozen_record

SUBQ = {"m2": ["theft", "cheating"], "m3": ["kidnapping", "perjury"], "m4": []}


class SubqueryTest(_Base):
    """Reuses setUp and write from the frozen-rule tests; their own test methods are disabled below."""

    def subq(self, items=None, **over) -> dict:
        d = {"producer": "agent-x", "producer_note": "saw only the query", "set_sha256": hashlib.sha256(self.write().read_bytes()).hexdigest(),
             "items": SUBQ if items is None else items}
        return {**d, **over}

    def call(self, f, per=2, out="p.json", rule=None) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["charges", "subquery", "--set", str(self.tmp / "set.json"), "--subqueries", str(f), "--index", str(self.tmp / "i.sqlite"),
                         "--frozen-rule", str(rule or self.frozen), "--per-subquery", str(per), "--out", str(self.tmp / out)])
        return code, err.getvalue()

    def run_sub(self, d: dict, per=2, out="p.json", expect=0, pin=True, name="sq.json"):
        f = self.tmp / name
        f.write_text(json.dumps(d))
        if pin:
            f.with_suffix(".sha256").write_text(hashlib.sha256(f.read_bytes()).hexdigest() + "\n")
        code, err = self.call(f, per, out)
        self.assertEqual(code, expect, err)
        return json.loads((self.tmp / out).read_text()) if expect == 0 else err

    def test_mean_subqueries_per_item_is_recorded_for_the_report(self):
        self.assertEqual(self.run_sub(self.subq())["counts"], {"subqueries_per_item_mean": 1.33})  # (2 + 2 + 0) / 3

    def test_union_of_each_subquerys_top_sections_matches_hand_values(self):
        r = self.run_sub(self.subq(), per=1)
        self.assertEqual(r["items"]["m2"], {"ipc": ["IPC 101", "IPC 102"], "bns": ["BNS 201", "BNS 202"]})
        self.assertEqual(r["items"]["m3"], {"ipc": ["IPC 103", "IPC 107"], "bns": ["BNS 206"]})  # no BNS kidnapping provision
        self.assertEqual(r["items"]["m4"], {"ipc": [], "bns": []})  # no sub-queries: nothing, not the full query
        self.assertNotIn("m1", r["items"])
        self.assertEqual((r["layer"], r["layer_version"]), ("decomposed", "v1"))

    def test_per_subquery_cap_is_applied(self):
        d = self.subq({"m1": ["murder theft"]})  # both words match one provision each, equal scores, tie by citation
        self.assertEqual(self.run_sub(d, per=1)["items"]["m1"]["ipc"], ["IPC 100"])
        self.assertEqual(self.run_sub(d, per=2, out="q.json")["items"]["m1"]["ipc"], ["IPC 100", "IPC 101"])

    def test_known_bad_files_are_refused(self):
        cases = {
            "set_sha256": self.run_sub(self.subq(set_sha256="0" * 64), expect=1, out="a.json"),
            "zz": self.run_sub(self.subq({"zz": ["theft"]}), expect=1, out="b.json"),
            "pin": self.run_sub(self.subq(), expect=1, pin=False, name="nopin.json", out="c.json"),
            "producer": self.run_sub(self.subq(producer=""), expect=1, out="d.json"),
            "subqueries": self.run_sub(self.subq({"m2": ["theft", ""]}), expect=1, out="e.json"),
        }
        for needle, err in cases.items():
            self.assertIn(needle, err)
        f = self.tmp / "sq.json"
        self.run_sub(self.subq(), out="ok.json")
        f.write_bytes(f.read_bytes() + b" ")  # a changed byte fails the pin
        code, err = self.call(f, out="x.json")
        self.assertEqual(code, 1)
        self.assertIn("does not match its pin", err)
        self.assertFalse(any((self.tmp / n).exists() for n in ("a.json", "b.json", "c.json", "d.json", "e.json", "x.json")))

    def test_identical_runs_are_byte_identical_and_equal_baseline_per_subquery(self):
        self.run_sub(self.subq(), out="a.json")
        self.run_sub(self.subq(), out="b.json")
        self.assertEqual((self.tmp / "a.json").read_bytes(), (self.tmp / "b.json").read_bytes())
        # each sub-query as its own item through export-baseline with a top-2 rule (the existing bench logic), then unioned.
        sub_items = [{**ITEMS[0], "id": f"{iid}-{n}", "query": q} for iid, qs in SUBQ.items() for n, q in enumerate(qs)]
        (self.tmp / "frozen2.json").write_text(json.dumps(frozen_record(k=2)))
        self.write(sub_items, "sub.json")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["charges", "export-baseline", "--set", str(self.tmp / "sub.json"), "--index", str(self.tmp / "i.sqlite"),
                                   "--frozen-rule", str(self.tmp / "frozen2.json"), "--out", str(self.tmp / "base.json")]), 0)
        base = json.loads((self.tmp / "base.baseline-topk.json").read_text())["items"]
        got = json.loads((self.tmp / "a.json").read_text())["items"]
        for iid, qs in SUBQ.items():
            for act in ("ipc", "bns"):
                want = sorted({c for n in range(len(qs)) for c in base[f"{iid}-{n}"][act]})
                self.assertEqual(got[iid][act], want, (iid, act))
        self.assertTrue(got["m2"]["ipc"])

    def test_inputs_record_producer_pin_and_per_subquery_and_score_through_the_one_scorer(self):
        r = self.run_sub(self.subq(), per=1)
        pin = (self.tmp / "sq.sha256").read_text().strip()
        self.assertEqual(r["inputs"]["producer"], "agent-x")
        self.assertEqual(r["inputs"]["subqueries_sha256"], pin)
        self.assertEqual(r["inputs"]["per_subquery"], 1)
        with contextlib.redirect_stderr(io.StringIO()):
            code = main(["charges", "score", "--set", str(self.tmp / "set.json"), "--index", str(self.tmp / "i.sqlite"),
                         "--predictions", str(self.tmp / "p.json"), "--act", "ipc", "--out", str(self.tmp / "s.json")])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((self.tmp / "s.json").read_text())["layer"], "decomposed")


for _n in [n for n in dir(_Base) if n.startswith("test_")]:
    setattr(SubqueryTest, _n, None)
del _Base

if __name__ == "__main__":
    unittest.main()
