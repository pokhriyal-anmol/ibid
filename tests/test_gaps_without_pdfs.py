"""IB25, IB26, IB27, IB30: rules the sixth audit showed CI does not guard, checked without the source PDFs.
Exception to AGENTS.md rule 5: calls cli, concordance, index and mcp functions directly, because `ibid eval` needs both PDFs."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid import cli, concordance, index, mcp  # noqa: E402
from ibid.parse import Provision  # noqa: E402
from ibid.xref import Edge  # noqa: E402

PROVS = [Provision("IPC 2", "2. Whoever commits murder.", None, ()), Provision("IPC 20", "20. Whoever commits theft.", None, ()),
         Provision("BNS 103", "103. Whoever commits murder.", None, ())]
EDGES = [Edge("IPC 2", "section 9", None, "reason of two"), Edge("IPC 20", "section 8", None, "reason of twenty")]
PROCEDURE = [Provision("CrPC 1", "1. Short title.", None, ()), Provision("BNSS 1", "1. Short title.", None, ())]
ENTRY = {"type": "one-to-one", "ipc": ["IPC 2"], "bns": ["BNS 103"], "verified": True}


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = index.build(str(Path(cls.tmp.name) / "i.sqlite"), PROVS, EDGES)
        cls.pdb = index.build(str(Path(cls.tmp.name) / "p.sqlite"), PROCEDURE, [])

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.pdb.close()
        cls.tmp.cleanup()

    def call(self, name: str, arguments: dict, entries: list[dict] | None = None, procedure: tuple | None = None, lazy=None) -> tuple[dict, str]:
        msg = {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            reply = mcp.handle(self.db, entries or [], msg, {}, lazy or mcp.LazyModel("unused"), procedure)
        return reply, err.getvalue()


class KeywordScoringTest(unittest.TestCase):
    def test_eval_scores_keyword_items_on_the_full_packet_not_the_first_ten(self):
        provs = [Provision(f"IPC {n}", f"{n}. Whoever commits arson, case {n}.", None, ()) for n in range(1, 13)]
        with tempfile.TemporaryDirectory() as tmp:
            db = index.build(str(Path(tmp) / "i.sqlite"), provs, [])
            item = {"id": "k", "category": "keyword", "query": "arson", "expected_citations": [p.citation for p in provs]}
            self.assertEqual(index.KEYWORD_LIMIT, 100)
            self.assertTrue(cli.score_item(db, [], item)["pass"])
            db.close()


class ConcordanceToolTest(Base):
    def test_a_citation_that_is_not_in_the_index_is_an_error_not_a_silent_negative(self):
        for citation in ("IPC 99999", "ipc 2", "BNS 99999", "IPC 2(9)"):
            res = self.call("concordance", {"citation": citation}, [ENTRY])[0]["result"]
            self.assertTrue(res["isError"], citation)
            self.assertIn("not in the index", res["content"][0]["text"], citation)

    def test_a_real_citation_with_no_verified_entry_is_still_a_plain_no_concordance(self):
        res = self.call("concordance", {"citation": "IPC 20"}, [ENTRY])[0]["result"]
        self.assertFalse(res["isError"])
        self.assertEqual(res["content"][0]["text"], concordance.NONE)
        found = self.call("concordance", {"citation": "IPC 2"}, [ENTRY])[0]["result"]
        self.assertEqual(found["structuredContent"]["result"][0]["citations"], ["BNS 103"])

    def test_a_procedure_citation_without_the_second_index_says_so(self):
        res = self.call("concordance", {"citation": "CrPC 154"}, [])[0]["result"]
        self.assertTrue(res["isError"])
        self.assertIn("second index is not built", res["content"][0]["text"])

    def test_a_procedure_citation_is_checked_against_the_second_index(self):
        bnss_entry = {"type": "one-to-one", "crpc": ["CrPC 1"], "bnss": ["BNSS 1"], "verified": True}
        procedure = (self.pdb, {}, [bnss_entry])
        ok = self.call("concordance", {"citation": "CrPC 1"}, procedure=procedure)[0]["result"]
        self.assertEqual(ok["structuredContent"]["result"][0]["citations"], ["BNSS 1"])
        self.assertTrue(self.call("concordance", {"citation": "CrPC 999"}, procedure=procedure)[0]["result"]["isError"])


class LearnedModeTest(Base):
    class Lazy:
        def __init__(self, predicted: list[str]):
            self.predicted = predicted

        def get(self):
            predicted = self.predicted
            return type("M", (), {"header": {"layer_version": "v3"}, "sha256": "0" * 64, "predict": lambda _s, q: predicted})()

    def learned(self, predicted: list[str], **extra) -> dict:
        return self.call("search", {"query": "x", "mode": "learned", **extra}, [ENTRY], lazy=self.Lazy(predicted))[0]

    def test_a_learned_query_is_capped_by_length(self):
        long = self.call("search", {"query": "a" * 4001, "mode": "learned"}, lazy=self.Lazy(["IPC 2"]))[0]
        self.assertEqual(long["error"]["code"], -32602)
        self.assertNotIn("error", self.call("search", {"query": "a " * 1999, "mode": "learned"}, lazy=self.Lazy(["IPC 2"]))[0])

    def test_a_model_that_names_a_citation_missing_from_the_index_is_a_tool_error_not_a_crash(self):
        res = self.learned(["IPC 2", "IPC 777"])["result"]
        self.assertTrue(res["isError"])
        self.assertIn("IPC 777", res["content"][0]["text"])
        self.assertFalse(self.learned(["IPC 2"])["result"]["isError"])

    def test_adjacent_is_reported_as_ignored_in_learned_mode(self):
        out = self.learned(["IPC 2"], adjacent=True)["result"]["structuredContent"]
        self.assertTrue(any("adjacent is not supported" in n for n in out["notes"]))
        self.assertNotIn("notes", self.learned(["IPC 2"])["result"]["structuredContent"])


class SmallRulesTest(Base):
    def test_cross_references_list_only_the_asked_sections_unresolved_references(self):
        out = self.call("cross_references", {"citation": "IPC 2"})[0]["result"]["structuredContent"]
        self.assertEqual([u["reason"] for u in out["unresolved"]], ["reason of two"])  # IPC 20's is not IPC 2's

    def test_a_new_entry_may_not_name_an_ancestor_nor_a_removed_entry_a_successor(self):
        path = Path(self.tmp.name) / "c.json"
        for bad in ({"type": "new", "ipc": ["IPC 2"], "bns": ["BNS 103"], "verified": True},
                    {"type": "removed", "ipc": ["IPC 2"], "bns": ["BNS 103"], "verified": True}):
            path.write_text(json.dumps([bad]))
            with self.assertRaisesRegex(ValueError, "successor or ancestor"):
                concordance.load(str(path), self.db)

    def test_conformed_is_recorded_only_when_the_gold_item_says_so(self):
        base = {"id": "c", "category": "section_lookup", "query": "IPC 2", "expected_text": PROVS[0].text}
        self.assertNotIn("conformed", cli.score_item(self.db, [], base))
        self.assertIs(cli.score_item(self.db, [], {**base, "conformed": False})["conformed"], False)
        self.assertIs(cli.score_item(self.db, [], {**base, "conformed": True})["conformed"], True)

    def test_the_length_cap_is_exactly_4000_characters(self):
        self.assertNotIn("error", self.call("search", {"query": "a" * mcp.MAX_QUERY_CHARS})[0])
        self.assertEqual(self.call("search", {"query": "a" * (mcp.MAX_QUERY_CHARS + 1)})[0]["error"]["code"], -32602)

    def test_a_query_with_no_words_says_so(self):
        hits, extra = index.search_explained(self.db, "???")
        self.assertEqual(hits, [])
        self.assertIn("no words", extra["notice"])
        self.assertIn("every word", index.search_explained(self.db, "zzzzzz")[1]["notice"])

    def test_the_stderr_log_carries_the_request_id(self):
        reply, logged = self.call("nope", {})
        record = json.loads(logged.splitlines()[0])
        self.assertEqual((record["id"], record["tool"], record["code"]), (9, "nope", -32602))


if __name__ == "__main__":
    unittest.main()
