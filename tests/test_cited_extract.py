"""Slice 3 ticket 07: `ibid cited extract`. Invented fixture queries, index and concordance."""
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

SECTIONS = ["IPC 34", "IPC 201", "IPC 302", "IPC 304B", "IPC 307", "IPC 354D", "IPC 395", "IPC 420", "IPC 439", "IPC 498A",
            "BNS 3", "BNS 103", "BNS 105", "BNS 318", "BNS 85"]
PROVS = [Provision(c, "text", None, ()) for c in SECTIONS] + [
    Provision("IPC 376", "text", None, ("IPC 376(2)",)), Provision("IPC 376(2)", "text", "IPC 376", ())]


def entry(ipc, bns, verified=True):
    return {"ipc": ipc, "bns": bns, "type": "one-to-one", "verified": verified}


CONC = [entry(["IPC 302"], ["BNS 103"]), entry(["IPC 307"], ["BNS 105"]), entry(["IPC 420"], ["BNS 318"], verified=False),
        entry(["IPC 34"], ["BNS 3"]), entry(["IPC 498A"], ["BNS 85"])]  # IPC 201, 395, 304B, 354D, 376, 439: no entry

QUERIES = {
    "plain": "He was charged under Section 302 IPC for the death.",
    "list_of": "Sections 302/201 of the Indian Penal Code were applied.",
    "u_s_list": "Case u/s 307, 395 IPC against the group.",
    "sub_clause": "Charged with S. 376(2)(i) IPC.",
    "read_with": "Section 420 read with Section 34 IPC was added.",
    "bns": "Sec. 3 of the BNS and Bharatiya Nyaya Sanhita section 103.",
    "lettered": "Sections 304B and 498A of the IPC, and Section 354D IPC.",
    "bare": "The court noted Section 302 was added later. The accused was a minor.",
    "crpc": "Bail was sought under Section 439 CrPC after arrest.",
    "absent": "Offence under Section 999 IPC was alleged.",
    "other_act": "Section 25 of the Arms Act and u/s 302 IPC were pleaded.",
    "none": "A man was beaten with a stick by two neighbours.",
}


class CitedExtractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVS, []).close()
        (self.tmp / "c.json").write_text(json.dumps(CONC))

    def run_extract(self, queries=QUERIES, out="p.json", extra=None):
        items = [{"id": k, "query": q, **(extra or {})} for k, q in queries.items()]
        s = self.tmp / "set.json"
        s.write_text(json.dumps({"items": items}))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["cited", "extract", "--set", str(s), "--index", str(self.tmp / "i.sqlite"),
                         "--concordance", str(self.tmp / "c.json"), "--out", str(self.tmp / out)])
        self.assertEqual(code, 0, err.getvalue())
        return json.loads((self.tmp / out).read_text())

    def test_each_form_resolves_and_maps_through_verified_entries(self):
        p = self.run_extract()
        self.assertEqual((p["layer"], p["set_sha256"]), ("cited", hashlib.sha256((self.tmp / "set.json").read_bytes()).hexdigest()))
        got = {k: (v["ipc"], v["bns"]) for k, v in p["items"].items()}
        self.assertEqual(got["plain"], (["IPC 302"], ["BNS 103"]))
        self.assertEqual(got["list_of"], (["IPC 201", "IPC 302"], ["BNS 103"]))
        self.assertEqual(got["u_s_list"], (["IPC 307", "IPC 395"], ["BNS 105"]))
        self.assertEqual(got["sub_clause"], (["IPC 376"], []))
        self.assertEqual(got["read_with"], (["IPC 34", "IPC 420"], ["BNS 3"]))  # 420's entry is unverified
        self.assertEqual(got["bns"], (["IPC 302", "IPC 34"], ["BNS 103", "BNS 3"]))
        self.assertEqual(got["lettered"], (["IPC 304B", "IPC 354D", "IPC 498A"], ["BNS 85"]))

    def test_known_bad_inputs_are_not_returned_and_are_counted(self):
        p = self.run_extract()
        for k in ("bare", "crpc", "absent", "none"):
            self.assertEqual(p["items"][k], {"ipc": [], "bns": []}, k)
        self.assertEqual(p["items"]["other_act"]["ipc"], ["IPC 302"])
        c = p["counts"]
        self.assertEqual((c["ambiguous_mentions"], c["other_act_dropped"], c["not_in_act_dropped"]), (1, 2, 1))
        # unmapped: 201, 395, 376, 420 (unverified), 304B, 354D. Each has no verified entry, so no prediction for the other Act.
        self.assertEqual(c["unmapped_citations"], 6)
        self.assertEqual(p["items"]["sub_clause"]["bns"], [])

    def test_runs_are_byte_identical_and_read_no_label(self):
        self.run_extract(out="a.json")
        self.run_extract(out="b.json")
        self.assertEqual((self.tmp / "a.json").read_bytes(), (self.tmp / "b.json").read_bytes())
        labels = {"charges": [{"charge": "x", "sections": {"ipc": ["IPC 439"], "bns": []}}], "label_basis": "lawyer", "top_predicted": ["IPC 34"]}
        labelled = self.run_extract(out="c.json", extra=labels)
        plain = json.loads((self.tmp / "a.json").read_text())
        self.assertEqual(labelled["items"], plain["items"])
        self.assertEqual(labelled["counts"], plain["counts"])


if __name__ == "__main__":
    unittest.main()
