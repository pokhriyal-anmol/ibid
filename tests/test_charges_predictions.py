"""Slice 3 ticket 06: `charges score --predictions` and `charges export-baseline`. Invented fixture set and index."""
import contextlib
import hashlib
import io
import json
import unittest

from ibid.cli import main
from test_charges_score import ChargesScoreTest as _Base

FIG = ("items", "charges", "recall", "all_charges_hit", "mean_predictions", "by_charges_per_item", "missed", "predictions")


class PredictionsTest(_Base):
    """Reuses setUp, write and score from the frozen-rule tests; their own test methods are disabled below."""

    def preds(self, items=None, **over) -> dict:
        p = {"layer": "hand", "layer_version": "v1", "set_sha256": hashlib.sha256(self.write().read_bytes()).hexdigest(),
             "inputs": {"concordance": "abc"},
             "items": items if items is not None else {
                 "m1": {"ipc": ["IPC 100"], "bns": ["BNS 200"]},
                 "m2": {"ipc": ["IPC 102", "IPC 101"], "bns": ["BNS 201"]},
                 "m3": {"ipc": ["IPC 103"], "bns": ["BNS 206", "BNS 204"]},
                 "m4": {"ipc": ["IPC 101"], "bns": ["BNS 203"]}}}  # m6 missing: no predictions
        return {**p, **over}

    def run_pred(self, preds: dict, act="ipc", out="p.json", expect=0, name="preds.json"):
        (self.tmp / name).write_text(json.dumps(preds))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["charges", "score", "--set", str(self.tmp / "set.json"), "--index", str(self.tmp / "i.sqlite"),
                         "--predictions", str(self.tmp / name), "--act", act, "--out", str(self.tmp / out)])
        self.assertEqual(code, expect, err.getvalue())
        return json.loads((self.tmp / out).read_text()) if expect == 0 else err.getvalue()

    def test_hand_computed_scores_both_acts(self):
        # IPC: found m1, m2 both, m3 kidnapping, m4 = 5 of 8; items fully found m1, m2, m4 = 3 of 5; m6 has no predictions.
        i = self.run_pred(self.preds())["output"]
        self.assertEqual((i["items"], i["charges"], i["recall"], i["all_charges_hit"], i["mean_predictions"]), (5, 8, 0.625, 0.6, 1.0))
        # BNS: m1, m2 theft, m3 both, m4 none = 4 of 6; items m1, m3 = 2 of 4; predictions 1+1+2+1 over 4.
        b = self.run_pred(self.preds(), "bns", "b.json")["output"]
        self.assertEqual((b["items"], b["charges"], b["recall"], b["all_charges_hit"], b["mean_predictions"]),
                         (4, 6, round(4 / 6, 6), 0.5, 1.25))

    def test_order_is_not_scored(self):
        items = self.preds()["items"]
        items["m2"]["ipc"].reverse()
        a = self.run_pred(self.preds(), out="a.json")["output"]
        b = self.run_pred(self.preds(items), out="b.json")["output"]
        self.assertEqual({k: a[k] for k in FIG if k != "predictions"}, {k: b[k] for k in FIG if k != "predictions"})

    def test_known_bad_files_are_refused_naming_the_field(self):
        good = self.preds()
        bad = {
            "set_sha256": self.preds(set_sha256="0" * 64),
            "zz": self.preds({**good["items"], "zz": {"ipc": [], "bns": []}}),
            "IPC 999": self.preds({"m1": {"ipc": ["IPC 999"], "bns": []}}),
            "m1 field bns": self.preds({"m1": {"ipc": [], "bns": ["IPC 100"]}}),
            "field layer": {k: v for k, v in good.items() if k != "layer"},
        }
        for needle, p in bad.items():
            with self.subTest(needle):
                self.assertIn(needle, self.run_pred(p, out="bad.json", expect=1))
                self.assertFalse((self.tmp / "bad.json").exists())
        self.assertFalse((self.tmp / "set.ledger.json").exists())

    def test_exported_baseline_scores_like_the_frozen_rule(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["charges", "export-baseline", "--set", str(self.write()), "--index", str(self.tmp / "i.sqlite"),
                                   "--frozen-rule", str(self.frozen), "--out", str(self.tmp / "base.json")]), 0)
        for act in ("ipc", "bns"):
            frozen = self.score(act, out=f"f-{act}.json")
            for layer, rule in (("baseline-topk", "top_k"), ("baseline-threshold", "threshold")):
                p = json.loads((self.tmp / f"base.{layer}.json").read_text())
                self.assertEqual((p["layer"], p["layer_version"]), (layer, "v2.11"))
                got = self.run_pred(p, act, f"p-{act}-{layer}.json", name=f"{layer}.json")["output"]
                self.assertTrue(got["predictions"])
                self.assertEqual({k: got[k] for k in FIG}, {k: frozen[rule][k] for k in FIG}, (act, layer))

    def test_two_identical_runs_are_byte_identical_and_a_second_scoring_is_beside_the_first(self):
        self.run_pred(self.preds(), out="a.json")
        self.run_pred(self.preds(), out="b.json")
        self.assertEqual((self.tmp / "a.json").read_bytes(), (self.tmp / "b.json").read_bytes())
        self.assertEqual(len(json.loads((self.tmp / "a.json").read_text())["scorings_of_this_layer_version"]), 1)
        two = self.preds({"m1": {"ipc": ["IPC 100"], "bns": []}})  # same layer version, other predictions
        r = self.run_pred(two, out="c.json")["scorings_of_this_layer_version"]
        self.assertEqual(len(r), 2)
        self.assertNotEqual(r[0]["scores"], r[1]["scores"])


for _n in [n for n in dir(_Base) if n.startswith("test_")]:
    setattr(PredictionsTest, _n, None)  # the inherited frozen-rule tests already run in their own module
del _Base

if __name__ == "__main__":
    unittest.main()
