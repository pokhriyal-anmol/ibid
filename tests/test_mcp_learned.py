"""`search` with `mode`, through the MCP stdio seam. The model is an invented assoc-nb v3 fit (fixtures/assoc-nb-v3-invented.json)."""
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
from mcp_harness import Client, command
from test_charges_score import PROVS, charge, item

FIX = Path(__file__).parent / "fixtures"
MODEL = FIX / "assoc-nb-v3-invented.json"
QUERIES = ["murder knife stranger", "theft of a purse", "cheating at cards", "the zebra wandered", "zzzzqqq"]


def with_model(path: Path) -> Client:
    return Client(command() + ["--assoc-model", str(path)])


class GoldenTest(unittest.TestCase):
    """The pre-change responses, recorded before mcp.py was touched: no mode and mode keyword must be byte-identical."""

    def test_default_and_keyword_mode_match_the_recorded_bytes(self):
        gold = json.loads((FIX / "mcp-search-golden.json").read_text())
        for extra in ({}, {"mode": "keyword"}):
            c = Client()
            try:
                for args, want in zip(gold["calls"], gold["lines"]):
                    c.call("search", {**args, **extra})
                    self.assertEqual(c.lines[-1], want, (args, extra))
            finally:
                c.close()


class LearnedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        index.build(str(cls.tmp / "i.sqlite"), PROVS, []).close()
        (cls.tmp / "conc.json").write_text("[]")  # predict is compared on its IPC list only
        probe = cls.tmp / "probe.json"
        items = [item(f"q{n}", q, [charge("any", ["IPC 100"], [])]) for n, q in enumerate(QUERIES)]
        probe.write_text(json.dumps({"version": "t", "created": "2026-10-18", "licence_note": "invented", "label_policy": "invented", "items": items}))
        probe.with_suffix(".sha256").write_text(hashlib.sha256(probe.read_bytes()).hexdigest() + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["assoc", "predict", "--model", str(MODEL), "--set", str(probe), "--concordance", str(cls.tmp / "conc.json"),
                         "--index", str(cls.tmp / "i.sqlite"), "--out", str(cls.tmp / "p.json")])
        assert code == 0
        cls.predicted = json.loads((cls.tmp / "p.json").read_text())["items"]
        cls.c = with_model(MODEL)

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        shutil.rmtree(cls.tmp)

    def learned(self, query, **kw):
        return self.c.call("search", {"query": query, "mode": "learned", **kw})["result"]

    def test_hits_equal_assoc_predict_in_order(self):
        for n, q in enumerate(QUERIES):
            res = self.learned(q)
            self.assertFalse(res["isError"], q)
            got = [h["citation"] for h in res["structuredContent"]["results"]]
            self.assertEqual(got, self.predicted[f"q{n}"]["ipc"], q)
            self.assertLessEqual(len(got), 5)
        self.assertEqual(self.predicted["q0"]["ipc"][0], "IPC 100")  # the probe is not vacuous

    def test_shape_and_provenance(self):
        out = self.learned("murder knife stranger")["structuredContent"]
        self.assertEqual((out["layer"], out["layer_version"], out["model_sha256"]),
                         ("assoc-nb", "v3", hashlib.sha256(MODEL.read_bytes()).hexdigest()))
        self.assertTrue(out["caveat"])
        for rank, h in enumerate(out["results"], 1):
            self.assertEqual(set(h), {"citation", "heading", "text", "rank", "bns"})
            self.assertEqual(h["rank"], rank)
            self.assertTrue(h["text"])

    def test_bns_lists_verified_counterparts_or_is_empty(self):
        by = {h["citation"]: h for h in self.learned("murder cheating zebra")["structuredContent"]["results"]}
        self.assertEqual(by["IPC 100"]["bns"], ["BNS 38"])  # verified in concordance/v3.json
        self.assertEqual(by["IPC 50"]["bns"], [])  # no entry in concordance/v3.json

    def test_text_is_the_keyword_modes_verbatim_text(self):
        hit = self.learned("murder")["structuredContent"]["results"][0]
        self.c.call("get_provision", {"citation": hit["citation"]})
        want = json.loads(self.c.lines[-1])["result"]["structuredContent"]
        self.assertEqual((hit["text"], hit["heading"]), (want["text"], want["heading"]))

    def test_limit_below_the_model_size_is_honoured_and_an_oversized_one_is_noted(self):
        out = self.learned("murder", limit=50)["structuredContent"]
        self.assertEqual(len(out["results"]), 4)  # the invented model has 4 labels
        self.assertIn("clamped", out["notes"][0])
        self.assertEqual(len(self.learned("murder", limit=2)["structuredContent"]["results"]), 2)


class LearnedErrorsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        m = json.loads(MODEL.read_text())
        for extra in ("IPC 103", "IPC 104", "IPC 105"):  # real sections, so 7 labels can fill 5 slots
            m["docs"][extra], m["counts"][extra] = 1, {"murder": 1}
        (cls.tmp / "big.json").write_text(json.dumps(m))
        cls.c = with_model(cls.tmp / "big.json")

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        shutil.rmtree(cls.tmp)

    def learned(self, **kw):
        return self.c.call("search", {"query": "murder", "mode": "learned", **kw})["result"]

    def refused(self, model_text: str) -> str:
        path = self.tmp / "bad.json"
        path.write_text(model_text)
        c = with_model(path)
        try:
            res = c.call("search", {"query": "murder", "mode": "learned"})["result"]
            self.assertTrue(res["isError"])
            self.assertFalse(c.call("search", {"query": "murder"})["result"]["isError"])  # the server survived
            return res["content"][0]["text"]
        finally:
            c.close()

    def test_missing_model_names_the_path_and_the_fit_command(self):
        c = with_model(self.tmp / "absent.json")
        try:
            self.assertFalse(c.call("search", {"query": "murder"})["result"]["isError"])  # not read at startup
            text = c.call("search", {"query": "murder", "mode": "learned"})["result"]["content"][0]["text"]
            self.assertIn(str(self.tmp / "absent.json"), text)
            self.assertIn("ibid assoc fit --source union", text)
        finally:
            c.close()

    def test_wrong_layer_and_wrong_version_name_found_and_expected(self):
        m = json.loads(MODEL.read_text())
        m["header"]["layer"] = "other-layer"
        text = self.refused(json.dumps(m))
        self.assertTrue("other-layer" in text and "assoc-nb" in text and "v3" in text, text)
        m = json.loads(MODEL.read_text())
        m["header"]["layer_version"] = "v2"
        text = self.refused(json.dumps(m))
        self.assertTrue("v2" in text and "v3" in text and "assoc-nb" in text, text)

    def test_invalid_json_is_a_tool_error(self):
        self.refused("{not json")

    def test_wrongly_typed_model_is_a_tool_error(self):
        self.refused(json.dumps({"header": [], "docs": [], "counts": []}))

    def test_other_mode_is_a_tool_error_naming_both_values(self):
        res = self.c.call("search", {"query": "x", "mode": "other"})["result"]
        self.assertTrue(res["isError"])
        self.assertTrue("keyword" in res["content"][0]["text"] and "learned" in res["content"][0]["text"])

    def test_learned_mode_with_another_act_is_a_tool_error_not_silent_ipc_results(self):
        for act in ("crpc", "bnss", "bns"):
            res = self.c.call("search", {"query": "murder", "mode": "learned", "act": act})["result"]
            self.assertTrue(res["isError"], act)
            self.assertIn("IPC sections only", res["content"][0]["text"])
        self.assertFalse(self.c.call("search", {"query": "murder", "mode": "learned", "act": "ipc"})["result"]["isError"])

    def test_limit_clamp_is_reported_and_an_honoured_limit_is_not(self):
        out = self.learned(limit=50)["structuredContent"]
        self.assertEqual(len(out["results"]), 5)
        self.assertIn("clamped", out["notes"][0])
        out = self.learned(limit=3)["structuredContent"]
        self.assertEqual(len(out["results"]), 3)
        self.assertNotIn("notes", out)

    def test_adjacent_is_ignored_with_a_note(self):
        out = self.learned(adjacent=True)["structuredContent"]
        self.assertTrue(any("adjacent" in n and "ignored" in n for n in out["notes"]))
        for h in out["results"]:
            self.assertFalse({"previous", "next"} & set(h))
        self.assertEqual(out["results"], self.learned()["structuredContent"]["results"])


if __name__ == "__main__":
    unittest.main()
