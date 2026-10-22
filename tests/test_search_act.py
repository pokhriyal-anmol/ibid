"""Slice 15 ticket 05: `search` takes an optional `act`; with none it is byte-identical to before the slice.
Seam: JSON-RPC over stdio to `ibid mcp`, second index built from the invented mini documents."""
import json
import tempfile
import unittest
from pathlib import Path

from mcp_harness import ROOT, Client, command
from test_crpc import MINI, build

FIXTURE = json.loads((ROOT / "tests/fixtures/search-no-act.json").read_text())  # recorded before any code change


class SearchActTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.index = str(Path(cls.tmp.name) / "procedure.sqlite")
        assert build(str(MINI), cls.index).returncode == 0
        cls.c = Client(command() + ["--procedure-index", cls.index, "--procedure-concordance", "absent.json"])

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        cls.tmp.cleanup()

    def hits(self, query: str, act: str, **kw) -> list[dict]:
        res = self.c.call("search", {"query": query, "act": act, **kw})["result"]
        self.assertFalse(res["isError"], res)
        return res["structuredContent"]["results"]

    def test_no_act_output_is_byte_identical_to_the_recorded_output(self):
        for case in FIXTURE:
            args = {k: v for k, v in case.items() if k != "line"}
            self.c.call("search", args)
            # the JSON-RPC id differs per session, so compare the serialised result, which is the same bytes
            self.assertEqual(json.dumps(json.loads(self.c.lines[-1])["result"]), json.dumps(json.loads(case["line"])["result"]), args)

    def test_crpc_returns_only_crpc_sections_with_headings(self):
        got = self.hits("bail", "crpc")
        self.assertTrue(got)
        self.assertTrue(all(h["citation"].startswith("CrPC ") for h in got), got)
        self.assertEqual({h["citation"]: h["heading"] for h in got}["CrPC 3"], "Bail where the offence is not serious.")

    def test_bnss_returns_only_bnss_sections_with_headings(self):
        got = self.hits("bail", "bnss")
        self.assertTrue(got)
        self.assertTrue(all(h["citation"].startswith("BNSS ") for h in got), got)
        self.assertEqual({h["citation"]: h["heading"] for h in got}["BNSS 3"], "Bail where the offence is not serious.")

    def test_ipc_and_bns_restrict_within_the_first_index_and_fill_the_limit(self):
        for act in ("ipc", "bns"):
            got = self.hits("murder", act, limit=10)
            self.assertEqual(len(got), 10, act)
            self.assertTrue(all(h["citation"].startswith(act.upper() + " ") for h in got), act)

    def test_adjacent_works_with_a_second_index_act(self):
        got = self.hits("bail", "crpc", adjacent=True)
        self.assertTrue(all("previous" in h and "next" in h for h in got))

    def test_an_unknown_act_is_an_invalid_params_error(self):
        for act in ("evidence", "CRPC", "", 5, None):
            self.assertEqual(self.c.call("search", {"query": "bail", "act": act})["error"]["code"], -32602, act)

    def test_a_second_index_act_without_the_index_is_a_tool_error(self):
        c = Client(command() + ["--procedure-index", str(Path(self.tmp.name) / "missing.sqlite")])
        self.addCleanup(c.close)
        self.assertTrue(c.call("search", {"query": "bail", "act": "crpc"})["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
