"""IB2: a punctuated question or a query no section fully matches must not come back as a silent empty list.
Exception to AGENTS.md rule 5: calls mcp.handle on a three-provision index so it runs without the source PDFs."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid import index, mcp  # noqa: E402
from ibid.parse import Provision  # noqa: E402

PROVS = [Provision("IPC 302", "What is the punishment for murder: the punishment for murder is death.", None, ()),
         Provision("IPC 378", "Whoever intends to take dishonestly any movable property commits theft.", None, ()),
         Provision("IPC 379", "Whoever commits theft shall be punished with imprisonment.", None, ())]


class SearchNoticeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = index.build(str(Path(cls.tmp.name) / "i.sqlite"), PROVS, [])

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.tmp.cleanup()

    def search(self, query: str) -> dict:
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {"query": query}}}
        res = mcp.handle(self.db, [], msg, {}, mcp.LazyModel("unused"))["result"]
        self.assertFalse(res["isError"], res)
        return res["structuredContent"]

    def test_a_question_mark_does_not_hide_the_hits(self):
        got = self.search("what is the punishment for murder?")
        self.assertEqual([r["citation"] for r in got["results"]], ["IPC 302"])
        self.assertEqual(got["searched_as"], '"what" "is" "the" "punishment" "for" "murder"')

    def test_no_match_says_every_word_must_match(self):
        got = self.search("theft of a mobile phone")
        self.assertEqual(got["results"], [])
        self.assertIn("every word", got["notice"])

    def test_a_valid_query_with_hits_is_unchanged(self):
        self.assertEqual(self.search("murder"), {"results": [{"citation": "IPC 302", "text": PROVS[0].text, "heading": None}]})


if __name__ == "__main__":
    unittest.main()
