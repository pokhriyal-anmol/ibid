"""IB7: CI skips every IPC test, so keyword ranking needs checks that do not use the IPC PDF.
These are regression pins of the order `index.search` returns today, not accuracy claims about it.
Exception to AGENTS.md rule 5: calls index.search, because `ibid eval` needs both Acts."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid import index  # noqa: E402
from ibid.parse import Provision, parse_bns  # noqa: E402
from ibid.xref import extract  # noqa: E402
from pdfs import BNS_PDF  # noqa: E402


class SyntheticOrderTest(unittest.TestCase):
    """The order is BM25 rank first, citation only to break a tie."""

    def test_rank_beats_citation_and_citation_breaks_ties(self):
        provs = [Provision("IPC 100", "theft is dealt with in the chapter on offences against property in general terms", None, ()),
                 Provision("IPC 300", "theft", None, ()),
                 Provision("IPC 200", "theft", None, ())]
        with tempfile.TemporaryDirectory() as tmp:
            db = index.build(str(Path(tmp) / "i.sqlite"), provs, [])
            self.assertEqual([c for c, _ in index.search(db, "theft")], ["IPC 200", "IPC 300", "IPC 100"])
            db.close()


class RealBnsOrderTest(unittest.TestCase):
    PINNED = {
        "murder": ["BNS 46 explanation 2 illustration 1", "BNS 48 illustration 1", "BNS 47 illustration 1", "BNS 46 explanation 2", "BNS 46 explanation 4 illustration 1"],
        "theft": ["BNS 112(1) explanation 1", "BNS 112(1)", "BNS 112", "BNS 309(2)", "BNS 304(1)"],
        "cheating": ["BNS 336(3)", "BNS 318(3)", "BNS 112(1)", "BNS 317(1)", "BNS 112"],
        "kidnapping": ["BNS 38(e)", "BNS 137(1)", "BNS 137", "BNS 140(2)", "BNS 38"],
    }

    @classmethod
    def setUpClass(cls):
        provs = parse_bns(BNS_PDF)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = index.build(str(Path(cls.tmp.name) / "bns.sqlite"), provs, extract(provs))

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.tmp.cleanup()

    def test_top_five_for_four_queries_on_the_hash_pinned_bns_text(self):
        for query, want in self.PINNED.items():
            self.assertEqual([c for c, _ in index.search(self.db, query, 5)], want, query)


if __name__ == "__main__":
    unittest.main()
