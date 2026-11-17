"""IB11: eval scoring, concordance loading and MCP contract rules, checked on a four-provision index so CI runs them
without the IPC PDF. Each test below was written against a planted bug that CI missed (see docs/readiness/ledger.md).
Exception to AGENTS.md rule 5: calls score_item, concordance.load and mcp.handle directly, because `ibid eval` needs both PDFs."""
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
from ibid.xref import Edge, chains  # noqa: E402
from pdfs import BNS_PDF  # noqa: E402

PROVS = [Provision("IPC 100", "100. Definitions of terms.", None, ()),
         Provision("IPC 302", "302. Whoever commits murder shall be punished with death.", None, ("IPC 302(1)",)),
         Provision("IPC 302(1)", "(1) Murder is punished.", "IPC 302", ()),
         Provision("IPC 379", "379. Whoever commits theft shall be punished.", None, ()),
         Provision("IPC 500", "500. What is the punishment for arson and fire?", None, ()),
         Provision("BNS 103", "103. Whoever commits murder shall be punished.", None, ())]

P302 = PROVS[1]


class Stub:
    """A learned model with a fixed answer, so learned mode runs without a model file."""
    header = {"layer_version": "v3"}
    sha256 = "0" * 64

    def predict(self, query: str) -> list[str]:
        return ["IPC 302"]


class StubLazy:
    def get(self) -> Stub:
        return Stub()


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = index.build(str(Path(cls.tmp.name) / "i.sqlite"), PROVS, [])

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.tmp.cleanup()


class ScoreItemTest(Base):
    def score(self, **item) -> bool:
        return cli.score_item(self.db, [], {"id": "t", **item})["pass"]

    def test_keyword_is_scored_as_an_exact_set(self):
        both = ["IPC 302", "IPC 302(1)", "BNS 103"]
        self.assertTrue(self.score(category="keyword", query="murder", expected_citations=both))
        self.assertFalse(self.score(category="keyword", query="murder", expected_citations=["IPC 302", "BNS 103"]))  # a subset is not a pass
        self.assertFalse(self.score(category="keyword", query="murder", expected_citations=both + ["IPC 379"]))

    def test_a_lookup_must_match_its_children_when_the_gold_names_them(self):
        base = {"category": "get_provision", "query": "IPC 302", "expected_text": P302.text}
        self.assertTrue(self.score(**base))
        self.assertTrue(self.score(**base, expected_children=["IPC 302(1)"]))
        self.assertFalse(self.score(**base, expected_children=["IPC 302(9)"]))

    def test_a_lookup_must_match_its_text_and_a_missing_citation_fails(self):
        self.assertFalse(self.score(category="get_provision", query="IPC 302", expected_text="other"))
        self.assertFalse(self.score(category="get_provision", query="IPC 999", expected_text=""))

    def test_a_cross_reference_chain_must_match_its_expected_refs(self):
        chain = {"category": "cross_reference_chain", "query": "IPC 302", "expected_text": P302.text}
        self.assertTrue(self.score(**chain, expected_refs=[]))
        self.assertFalse(self.score(**chain, expected_refs=["IPC 379"]))

    def test_concordance_items_are_scored_against_verified_entries_only(self):
        entries = [{"type": "one-to-one", "ipc": ["IPC 302"], "bns": ["BNS 103"], "verified": False}]
        item = {"id": "t", "category": "ipc_to_bns", "query": "IPC 302", "expected": [{"type": "one-to-one", "citations": ["BNS 103"]}]}
        self.assertFalse(cli.score_item(self.db, entries, item)["pass"])
        self.assertTrue(cli.score_item(self.db, [{**entries[0], "verified": True}], item)["pass"])

    def test_an_invalid_fts5_query_scores_as_no_hits_and_is_never_rewritten(self):  # ADR 0001 and 0004
        self.assertEqual(index.search(self.db, '"arson AND'), [])
        self.assertEqual(index.search(self.db, "what is the punishment for arson?"), [])
        self.assertEqual([c for c, _ in index.search(self.db, "what is the punishment for arson")], ["IPC 500"])  # the same words, valid syntax


class ConcordanceLoadTest(Base):
    def load(self, *entries: dict) -> list[dict]:
        path = Path(self.tmp.name) / "c.json"
        path.write_text(json.dumps(list(entries)))
        return concordance.load(str(path), self.db)

    GOOD = {"type": "one-to-one", "ipc": ["IPC 302"], "bns": ["BNS 103"], "verified": True}

    def test_a_good_entry_loads(self):
        self.assertEqual(self.load(self.GOOD), [self.GOOD])

    def test_a_citation_absent_from_the_index_is_refused(self):
        with self.assertRaisesRegex(ValueError, "not in the index"):
            self.load({**self.GOOD, "bns": ["BNS 999"]})

    def test_entries_that_are_not_well_formed_objects_are_a_value_error_not_a_traceback(self):
        for bad in ({"type": "one-to-one", "verified": True, "ipc": ["IPC 302"]},          # no bns key
                    {"type": "one-to-one", "verified": True, "ipc": "IPC 302", "bns": ["BNS 103"]},  # not a list
                    {"type": "one-to-one", "verified": True, "ipc": [], "bns": ["BNS 103"]},          # a one-to-one needs both sides
                    {**self.GOOD, "bns": []}, [1, 2], "text", None):
            with self.assertRaises(ValueError, msg=str(bad)):
                self.load(bad)

    def test_malformed_entries_are_refused(self):
        for bad in ({**self.GOOD, "type": "nope"}, {**self.GOOD, "verified": "yes"}, {**self.GOOD, "basis": "x"},
                    {**self.GOOD, "type": "removed"}, {**self.GOOD, "ipc": ["BNS 103"]}):
            with self.assertRaises(ValueError, msg=str(bad)):
                self.load(bad)


class McpContractTest(Base):
    def call(self, name: str, arguments: dict, entries: list[dict] | None = None, lazy=None) -> dict:
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
        return mcp.handle(self.db, entries or [], msg, {}, lazy or mcp.LazyModel("unused"))

    def test_an_unknown_citation_is_a_tool_error_naming_the_acts(self):
        res = self.call("get_provision", {"citation": "IPC 999"})["result"]
        self.assertTrue(res["isError"])
        self.assertIn("Covered Acts", res["content"][0]["text"])
        self.assertFalse(self.call("get_provision", {"citation": "IPC 302"})["result"]["isError"])

    def test_keyword_limit_must_be_a_positive_integer(self):
        for bad in ("3", True, 1.5, 0, -1, None):
            self.assertEqual(self.call("search", {"query": "murder", "limit": bad})["error"]["code"], -32602, repr(bad))

    def test_learned_mode_serves_only_verified_concordance_entries(self):
        entries = [{"type": "one-to-one", "ipc": ["IPC 302"], "bns": ["BNS 103"], "verified": True},
                   {"type": "one-to-one", "ipc": ["IPC 302"], "bns": ["BNS 999"], "verified": False}]
        out = self.call("search", {"query": "x", "mode": "learned"}, entries, StubLazy())["result"]["structuredContent"]
        self.assertEqual(out["results"][0]["bns"], ["BNS 103"])
        self.assertEqual(out["results"][0]["citation"], "IPC 302")


class IndexRulesTest(Base):
    def test_lookup_is_an_exact_byte_match_on_the_citation(self):
        self.assertIsNotNone(index.lookup(self.db, "IPC 302"))
        self.assertIsNone(index.lookup(self.db, "ipc 302"))
        self.assertIsNone(index.lookup(self.db, " IPC 302 "))

    def test_neighbours_are_the_previous_and_next_section_of_the_same_act(self):
        prev, nxt = index.neighbours(self.db, "IPC 379")
        self.assertEqual((prev[0], nxt[0]), ("IPC 302", "IPC 500"))
        self.assertEqual(index.neighbours(self.db, "IPC 302")[0][0], "IPC 100")  # the nearest earlier section, not the first one
        self.assertIsNone(index.neighbours(self.db, "IPC 100")[0])
        self.assertEqual(index.neighbours(self.db, "IPC 302")[1][0], "IPC 379")  # the nearest later section, not the last one
        self.assertIsNone(index.neighbours(self.db, "IPC 500")[1])  # BNS 103 is another Act, so not IPC 500 next
        self.assertEqual(index.neighbours(self.db, "IPC 302(1)"), index.neighbours(self.db, "IPC 302"))  # a sub-provision gets its section's


class CrossReferenceRulesTest(unittest.TestCase):
    def test_a_provision_never_lists_itself_but_keeps_its_descendants_targets(self):  # CONTEXT.md, AGENTS.md
        edges = [Edge("IPC 302", "this section", "IPC 302", None), Edge("IPC 302", "section 302(1)", "IPC 302(1)", None),
                 Edge("IPC 302(1)", "section 379", "IPC 379", None), Edge("IPC 379", "section 9", None, "unresolved")]
        got = chains(PROVS, edges)
        self.assertEqual(got["IPC 302"], ["IPC 302(1)", "IPC 379"])
        self.assertEqual(got["IPC 379"], [])


class McpProtocolTest(Base):
    def handle(self, msg: dict) -> dict | None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            return mcp.handle(self.db, [], msg, {}, mcp.LazyModel("unused"))

    def test_a_notification_gets_no_reply_whatever_its_method(self):
        for msg in ({"jsonrpc": "2.0", "method": "notifications/initialized"}, {"jsonrpc": "2.0", "method": "ping"},
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search", "arguments": {"query": "murder"}}}):
            self.assertIsNone(self.handle(msg), msg["method"])
        self.assertEqual(self.handle({"jsonrpc": "2.0", "id": 1, "method": "ping"})["result"], {})

    def test_adjacent_must_be_a_boolean(self):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {"query": "murder", "adjacent": "yes"}}}
        self.assertEqual(self.handle(msg)["error"]["code"], -32602)

    def test_a_direction_that_contradicts_the_citation_prefix_is_a_tool_error(self):
        def ask(direction: str) -> dict:
            msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "concordance", "arguments": {"citation": "IPC 302", "direction": direction}}}
            return self.handle(msg)["result"]
        wrong = ask("bns_to_ipc")
        self.assertTrue(wrong["isError"])
        self.assertIn("contradicts", wrong["content"][0]["text"])
        self.assertFalse(ask("ipc_to_bns")["isError"])


class SourceFigureTest(unittest.TestCase):
    def test_the_section_totals_in_code_match_the_pinned_source_record(self):
        from ibid.ipc import IPC_TOTAL
        from ibid.parse import BNS_TOTAL
        sources = json.loads((Path(__file__).parent.parent / "data/sources.json").read_text())
        self.assertEqual((BNS_TOTAL, IPC_TOTAL), (sources["bns"]["sections"], sources["ipc"]["sections"]))


class EvalGateTest(unittest.TestCase):
    def test_a_section_count_that_does_not_match_stops_eval_before_it_writes_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                # the BNS PDF stands in for the IPC one: it parses to 0 of 575 IPC sections
                rc = cli.run_eval("gold/draft.json", BNS_PDF, BNS_PDF, f"{tmp}/i.sqlite", f"{tmp}/r.json", None, "draft")
            self.assertEqual(rc, 1)
            self.assertIn("IPC section count does not match", err.getvalue())
            self.assertFalse((Path(tmp) / "r.json").exists())


if __name__ == "__main__":
    unittest.main()
