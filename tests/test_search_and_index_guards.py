"""IB32, IB33: a search never answers for a different query than the one asked, and a stale second index is refused.
Exception to AGENTS.md rule 5: calls mcp functions directly, because `ibid mcp` needs the IPC PDF CI cannot fetch."""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import test_gaps_without_pdfs as gaps  # noqa: E402
from ibid import bnss, crpc, mcp  # noqa: E402


class NulAndLearnedQueryTest(gaps.Base):
    def test_a_nul_in_the_query_is_refused_in_both_modes(self):
        for mode in ("keyword", "learned"):
            err = self.call("search", {"query": "murder\x00theft", "mode": mode}, lazy=gaps.LearnedModeTest.Lazy(["IPC 2"]))[0]["error"]
            self.assertEqual(err["code"], -32602, mode)

    def test_a_learned_query_with_no_words_says_so_instead_of_answering(self):
        out = self.call("search", {"query": "???", "mode": "learned"}, [gaps.ENTRY], lazy=gaps.LearnedModeTest.Lazy(["IPC 2"]))[0]["result"]
        self.assertEqual(out["structuredContent"]["results"], [])
        self.assertIn("no words", out["structuredContent"]["notice"])

    def test_adjacent_must_be_a_boolean_in_learned_mode_too(self):
        reply = self.call("search", {"query": "x", "mode": "learned", "adjacent": "yes"}, lazy=gaps.LearnedModeTest.Lazy(["IPC 2"]))[0]
        self.assertEqual(reply["error"]["code"], -32602)


class StaleProcedureIndexTest(unittest.TestCase):
    def index(self, rows: list[tuple[str, str]]) -> sqlite3.Connection:
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        db.executemany("INSERT INTO meta VALUES (?, ?)", rows)
        return db

    def test_an_index_from_the_current_parsers_is_accepted(self):
        both = [("crpc_parser_version", crpc.CRPC_PARSER_VERSION), ("bnss_parser_version", bnss.BNSS_PARSER_VERSION)]
        self.assertIsNone(mcp._stale_procedure(self.index(both)))
        self.assertIsNone(mcp._stale_procedure(self.index(both[:1])))  # built without the BNSS

    def test_an_index_from_another_parser_version_is_refused(self):
        self.assertIn("crpc_parser_version", mcp._stale_procedure(self.index([("crpc_parser_version", "0")])))
        stale_bnss = [("crpc_parser_version", crpc.CRPC_PARSER_VERSION), ("bnss_parser_version", "0")]
        self.assertIn("bnss_parser_version", mcp._stale_procedure(self.index(stale_bnss)))

    def test_an_index_with_no_recorded_versions_is_refused(self):
        self.assertIsNotNone(mcp._stale_procedure(self.index([])))
        self.assertIsNotNone(mcp._stale_procedure(sqlite3.connect(":memory:")))


if __name__ == "__main__":
    unittest.main()
