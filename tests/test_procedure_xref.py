"""Slice 15 ticket 04: cross-references inside the CrPC and the BNSS, other-Act targets left unresolved.
Seam: `ibid procedure build` and `cross_references` over `ibid mcp`, on the mini Acts with reference sentences added."""
import tempfile
import unittest
from pathlib import Path

from mcp_harness import Client, command
from test_crpc import BNSS_MINI, MINI, build

CRPC_OLD = "43. Saving.—Nothing in this Code affects any other law.\n"
CRPC_NEW = ("43. Saving.—Nothing in this Code affects any other law, as section 41A applies, and so does section 43, "
            "but not section 5 of the Indian Penal Code.\n")
BNSS_OLD = "Nothing in this Sanhita affects any other law.\n"
BNSS_NEW = ("Nothing in this Sanhita affects any other law, as section 3 applies, and so does section 4, "
            "but not section 3 of the Bharatiya Nyaya Sanhita, 2023.\n")


class ProcedureXrefTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        crpc, bnss = Path(cls.tmp.name, "c.txt"), Path(cls.tmp.name, "b.txt")
        for src, dst, old, new in ((MINI, crpc, CRPC_OLD, CRPC_NEW), (BNSS_MINI, bnss, BNSS_OLD, BNSS_NEW)):
            text = src.read_text()
            assert old in text  # the mutation must apply
            dst.write_text(text.replace(old, new))
        cls.index = str(Path(cls.tmp.name, "procedure.sqlite"))
        cls.built = build(str(crpc), cls.index, str(bnss))
        cls.c = Client(command() + ["--procedure-index", cls.index])

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        cls.tmp.cleanup()

    def xref(self, citation: str) -> dict:
        got = self.c.call("cross_references", {"citation": citation})["result"]
        self.assertFalse(got["isError"], got)
        return got["structuredContent"]

    def test_build_succeeds(self):
        self.assertEqual(self.built.returncode, 0, self.built.stderr)

    def test_crpc_in_act_reference_resolves_in_the_same_act_and_the_self_reference_is_not_listed(self):
        self.assertEqual(self.xref("CrPC 43")["resolved"], ["CrPC 41A"])

    def test_crpc_other_act_reference_is_unresolved_and_names_its_act(self):
        got = self.xref("CrPC 43")["unresolved"]
        self.assertEqual([u["matched"] for u in got], ["section 5"])
        self.assertIn("Indian Penal Code", got[0]["reason"])

    def test_bnss_reference_to_a_bns_section_is_not_resolved_to_the_bnss_section_of_the_same_number(self):
        got = self.xref("BNSS 4")
        # "section 3 of the Bharatiya Nyaya Sanhita" is unresolved; the in-Act "section 3" is the only BNSS 3 edge
        self.assertEqual([u["matched"] for u in got["unresolved"]], ["section 3"])
        self.assertIn("Bharatiya Nyaya Sanhita", got["unresolved"][0]["reason"])
        self.assertEqual(got["resolved"], ["BNSS 3"])
        self.assertNotIn("BNSS 4", got["resolved"])


if __name__ == "__main__":
    unittest.main()
