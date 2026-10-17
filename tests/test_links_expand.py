"""Slice 7 ticket 04: `ibid links expand` over the invented mini-Act of the links list tests."""
import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import index
from ibid.cli import main
from ibid.parse import Provision
from test_links_list import CONC, MINI

SET_SHA = "a" * 64
# IPC links: 10<->11, 9<->9A, 13<->15. BNS link: 1<->2.
ITEMS = {"a": {"ipc": ["IPC 15", "IPC 10", "IPC 13"], "bns": ["BNS 2", "BNS 4"]},
         "b": {"ipc": ["IPC 9A", "IPC 11"], "bns": []},
         "c": {"ipc": ["IPC 14"], "bns": ["BNS 1"]}}


class LinksExpandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        provs = [Provision(c, t, c.split("(")[0] if "(" in c else None, ()) for c, t in MINI]
        index.build(str(self.tmp / "i.sqlite"), provs, []).close()
        (self.tmp / "c.json").write_text(json.dumps(CONC))

    def expand(self, items=ITEMS, layer="baseline-topk", name="in.json", out="out.json") -> dict:
        (self.tmp / name).write_text(json.dumps({"layer": layer, "layer_version": "v2", "set_sha256": SET_SHA,
                                                  "inputs": {}, "items": items}))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["links", "expand", "--predictions", str(self.tmp / name), "--index", str(self.tmp / "i.sqlite"),
                         "--concordance", str(self.tmp / "c.json"), "--out", str(self.tmp / out)])
        self.assertEqual(code, 0, err.getvalue())
        return json.loads((self.tmp / out).read_text())

    def test_originals_first_in_order_partners_after_no_duplicates(self):
        got = self.expand()["items"]
        # 13 is already predicted, so 15's partner is not appended again; 10's partner 11 is.
        self.assertEqual(got["a"]["ipc"], ["IPC 15", "IPC 10", "IPC 13", "IPC 11"])
        self.assertEqual(got["a"]["bns"], ["BNS 2", "BNS 4", "BNS 1"])
        self.assertEqual(got["b"]["ipc"], ["IPC 9A", "IPC 11", "IPC 9", "IPC 10"])  # partners in rank order
        self.assertEqual(got["c"], {"ipc": ["IPC 14"], "bns": ["BNS 1", "BNS 2"]})  # IPC 14 has no link

    def test_records_layer_and_baseline_hash_and_it_follows_the_bytes(self):
        d = self.expand()
        self.assertEqual((d["layer"], d["layer_version"], d["set_sha256"]), ("links", "v1", SET_SHA))
        for key, name in (("baseline", "in.json"), ("concordance", "c.json"), ("index", "i.sqlite")):
            self.assertEqual(d["inputs"][key], hashlib.sha256((self.tmp / name).read_bytes()).hexdigest())
        self.assertEqual(d["inputs"]["baseline_layer"], "baseline-topk")
        other = self.expand(layer="baseline-topl", out="o2.json")  # one byte of the baseline differs
        self.assertNotEqual(d["inputs"]["baseline"], other["inputs"]["baseline"])

    def test_both_output_rules_are_expanded(self):
        for layer in ("baseline-topk", "baseline-threshold"):
            d = self.expand(layer=layer, name=f"{layer}.json", out=f"{layer}.out.json")
            self.assertEqual(d["items"]["a"]["ipc"][-1], "IPC 11")
            self.assertEqual(d["items"]["a"]["bns"][-1], "BNS 1")

    def test_two_runs_are_byte_identical_and_baseline_unchanged(self):
        self.expand()
        raw_in, first = (self.tmp / "in.json").read_bytes(), (self.tmp / "out.json").read_bytes()
        self.expand(out="out2.json")
        self.assertEqual(first, (self.tmp / "out2.json").read_bytes())
        self.assertEqual(raw_in, (self.tmp / "in.json").read_bytes())

    def test_bad_input_is_refused(self):
        (self.tmp / "bad.json").write_text("{}")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["links", "expand", "--predictions", str(self.tmp / "bad.json"), "--index", str(self.tmp / "i.sqlite"),
                         "--concordance", str(self.tmp / "c.json"), "--out", str(self.tmp / "x.json")])
        self.assertEqual(code, 1)
        self.assertFalse((self.tmp / "x.json").exists())


if __name__ == "__main__":
    unittest.main()
