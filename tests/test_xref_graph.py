"""Slice 7 ticket 1: the Cross-reference graph of the real Acts has no definition-punishment edges (ADR 0007)."""
import re
import tempfile
import unittest
from pathlib import Path

from ibid import index
from ibid.ipc import parse_ipc
from ibid.parse import parse_bns
from ibid.xref import extract
from pdfs import BNS_PDF, IPC_PDF

# punishment section first, defining section second
PAIRS = [("IPC 302", "IPC 300"), ("IPC 406", "IPC 405"), ("IPC 420", "IPC 415")]
TOTAL, RESOLVED = 615, 586  # measured on the real Acts, 2026-10-17


def section(citation: str) -> str:
    return re.match(r"(?:IPC|BNS) \d+[A-Z]*", citation)[0]


def edges(db) -> list[tuple[str, str | None]]:
    return db.execute("SELECT source, target FROM xref").fetchall()


class XrefGraphTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        provs = parse_bns(BNS_PDF) + parse_ipc(IPC_PDF)
        cls.db = index.build(str(Path(cls.tmp.name) / "i.sqlite"), provs, extract(provs))

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.tmp.cleanup()

    def test_no_edge_between_a_punishment_and_its_definition(self):
        pairs = {(section(s), section(t)) for s, t in edges(self.db) if t}
        for punishment, definition in PAIRS:
            self.assertNotIn((punishment, definition), pairs)
            self.assertNotIn((definition, punishment), pairs)

    def test_edge_counts_are_pinned(self):
        e = edges(self.db)
        self.assertEqual((len(e), sum(t is not None for _, t in e)), (TOTAL, RESOLVED))


if __name__ == "__main__":
    unittest.main()
