# Cross-references within the CrPC and the BNSS, other-Act targets left unresolved

Status: done
Blocked by: 03

What to build: Cross-references extracted and resolved within each new Act only, stored in `data/index/procedure.sqlite`, by the same rule-based path as `src/ibid/xref.py`. A reference to another Act (for example a BNSS reference to the Bharatiya Nyaya Sanhita, or a CrPC reference to the Indian Penal Code) is recorded as unresolved with its target Act named, never guessed. A provision does not list itself. `cross_references` in `ibid mcp` accepts CrPC and BNSS Citations.

User stories: supports 1 (decision 6 of the spec; no user story names it alone).

Acceptance criteria:
- Fixture sections containing an in-Act reference ("section 41A"), a self-reference and a reference to another Act.
- A `unittest` through `ibid mcp` `cross_references`: the in-Act reference resolves to the Citation in the same Act; the other-Act reference is unresolved with its target Act; no self-reference is listed.
- Seen to fail once: a BNSS reference to a BNS offence resolved to the BNSS section of the same number is caught.
- Cross-references of IPC and BNS Citations are unchanged (existing tests pass; byte-identity test passes).
- `uv run python -m unittest discover -s tests` passes.
