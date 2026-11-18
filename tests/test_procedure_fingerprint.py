"""IB29: a pinned fingerprint of the whole CrPC and BNSS parse, as test_bns_fingerprint.py does for the BNS, so a change to
either parser or to their cross-references fails CI. CI fetches both PDFs. The fingerprint holds hashes and counts only, never
the Acts' text. When a change is intended, bump CRPC_PARSER_VERSION or BNSS_PARSER_VERSION and regenerate it:

    uv run python tests/test_procedure_fingerprint.py --write
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid.bnss import BNSS_PARSER_VERSION, parse_bnss  # noqa: E402
from ibid.crpc import CRPC_PARSER_VERSION, parse_crpc  # noqa: E402
from ibid import bnss, crpc  # noqa: E402
from ibid.parse import Provision  # noqa: E402
from ibid.xref import chains, extract  # noqa: E402
from pdfs import BNSS_PDF, CRPC_PDF  # noqa: E402

PIN = Path(__file__).parent / "fixtures" / "procedure-parse-fingerprint.json"


def _hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _parse(provisions: list) -> list:
    return [(p.citation, p.text, p.parent, list(p.children)) for p in provisions]


def fingerprint() -> dict:
    crpc, crpc_arr = parse_crpc(CRPC_PDF)
    bnss, bnss_heads, bnss_arr = parse_bnss(BNSS_PDF)
    both = crpc + bnss  # the second index is built over both, as `ibid procedure build` does
    edges = extract(both)
    return {
        "crpc": {"parser_version": CRPC_PARSER_VERSION, "provisions": len(crpc), "parse_sha256": _hash(_parse(crpc)), "arrangement_sha256": _hash(crpc_arr)},
        "bnss": {"parser_version": BNSS_PARSER_VERSION, "provisions": len(bnss), "parse_sha256": _hash(_parse(bnss)),
                 "headings_sha256": _hash(bnss_heads), "arrangement_sha256": _hash(bnss_arr)},
        "xref": {"edges": len(edges), "edges_sha256": _hash([(e.source, e.matched, e.target, e.reason) for e in edges]),
                 "chains_sha256": _hash(chains(both, edges))},
    }


def _moved(want: dict, got: dict, path: str = "") -> list[str]:
    return [p for k in want for p in (_moved(want[k], got[k], f"{path}{k}.") if isinstance(want[k], dict) else [f"{path}{k}"] if want[k] != got[k] else [])]


class ProcedureParseFingerprintTest(unittest.TestCase):
    def test_the_crpc_and_bnss_parse_matches_its_pinned_fingerprint(self):
        want, got = json.loads(PIN.read_text()), fingerprint()
        moved = _moved(want, got)
        self.assertEqual(moved, [], f"CrPC or BNSS parse changed in {moved}. If intended, bump the parser version and run --write")


class HeadingFloorTest(unittest.TestCase):
    """The Arrangement check passes at 98 percent heading agreement and fails below it (HEADING_MATCH_FLOOR)."""
    N = 100

    def arrangement(self) -> list[tuple[str, str]]:
        return [(str(i), f"Heading number {i}") for i in range(1, self.N + 1)]

    def test_the_crpc_check_passes_at_98_percent_and_fails_at_97(self):
        arr = self.arrangement()
        for wrong, expect in ((0, True), (2, True), (3, False)):
            provisions = [Provision(f"CrPC {k}", f"{k} {'Wrong' if int(k) <= wrong else h}.\u2014 body", None, ()) for k, h in arr]
            self.assertIs(crpc.check(provisions, arr)[0], expect, wrong)

    def test_the_bnss_check_passes_at_98_percent_and_fails_at_97(self):
        arr = self.arrangement()
        for wrong, expect in ((0, True), (2, True), (3, False)):
            heads = [(f"BNSS {k}", "Wrong" if int(k) <= wrong else h) for k, h in arr]
            self.assertIs(bnss.check(heads, arr)[0], expect, wrong)

    def test_a_missing_section_fails_the_check_whatever_the_headings(self):
        arr = self.arrangement()
        heads = [(f"BNSS {k}", h) for k, h in arr[:-1]]
        self.assertFalse(bnss.check(heads, arr)[0])


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        PIN.write_text(json.dumps(fingerprint(), indent=1, sort_keys=True) + "\n")
        print(f"wrote {PIN}")
    else:
        unittest.main()
