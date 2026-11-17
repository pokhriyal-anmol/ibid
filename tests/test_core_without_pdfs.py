"""IB11: eval scoring, concordance loading and MCP contract rules, checked on a four-provision index so CI runs them
without the IPC PDF. Each test below was written against a planted bug that CI missed (see docs/readiness/ledger.md).
Exception to AGENTS.md rule 5: calls score_item, concordance.load and mcp.handle directly, because `ibid eval` needs both PDFs."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid import cli, concordance, index, mcp  # noqa: E402
from ibid.parse import Provision  # noqa: E402

PROVS = [Provision("IPC 302", "302. Whoever commits murder shall be punished with death.", None, ("IPC 302(1)",)),
         Provision("IPC 302(1)", "(1) Murder is punished.", "IPC 302", ()),
         Provision("IPC 379", "379. Whoever commits theft shall be punished.", None, ()),
         Provision("IPC 500", "500. What is the punishment for arson and fire?", None, ()),
         Provision("BNS 103", "103. Whoever commits murder shall be punished.", None, ())]


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
        base = {"category": "get_provision", "query": "IPC 302", "expected_text": PROVS[0].text}
        self.assertTrue(self.score(**base))
        self.assertTrue(self.score(**base, expected_children=["IPC 302(1)"]))
        self.assertFalse(self.score(**base, expected_children=["IPC 302(9)"]))

    def test_a_lookup_must_match_its_text_and_a_missing_citation_fails(self):
        self.assertFalse(self.score(category="get_provision", query="IPC 302", expected_text="other"))
        self.assertFalse(self.score(category="get_provision", query="IPC 999", expected_text=""))

    def test_a_cross_reference_chain_must_match_its_expected_refs(self):
        chain = {"category": "cross_reference_chain", "query": "IPC 302", "expected_text": PROVS[0].text}
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


if __name__ == "__main__":
    unittest.main()
