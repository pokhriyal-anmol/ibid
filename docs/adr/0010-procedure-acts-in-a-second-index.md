# 0010: The CrPC and BNSS live in a second index, not a rebuilt first one

The CrPC and the BNSS are built together into `data/index/procedure.sqlite`, with the same tables as `data/index/ibid.sqlite` plus a `heading` table and a `meta` table that records its own parser version (`CRPC_PARSER_VERSION`). `ibid mcp` opens the second file next to the first when it exists and ignores it when it does not.

**Why:** the first index's hash is recorded inside committed results, and BM25 statistics (document frequency, average length) depend on the whole corpus. Adding two Acts to that file would change every keyword score, the frozen rule's output and every pin. A second file leaves the first, `PARSER_VERSION` for the IPC and the BNS, `results/` and the pins byte-identical, and a test checks that.

**Cost:** a keyword search does not cross the two files. `search` takes an `act` argument (`ipc`, `bns`, `crpc`, `bnss`): with none it uses the first index only, and `crpc` or `bnss` routes to the second. A procedure Act's scores are never comparable with the IPC's. Anything that needs both must open both. A citation in neither index is a tool error naming the four covered Acts, and the concordance tool takes the directions `crpc_to_bnss` and `bnss_to_crpc` beside the IPC and BNS ones.

**Rule:** a new Act that would change the first index's corpus goes in a second file. Headings of the procedure Acts come from their Arrangement of Sections.

**BNSS:** built into the same file by `ibid procedure build` (`BNSS_PARSER_VERSION` in `meta`). The PRS Gazette copy prints no Arrangement of Sections, so its headings are the margin notes and its count is checked against the published 531; a file that does print an Arrangement is checked against it as the CrPC is. A `BNSS` Citation is looked up only in this file, never in the BNS section of the same number.

**Removed entries:** the CrPC to BNSS concordance lists a CrPC section as `removed` when no table row cites it. Absence from the table is not evidence the section was repealed, so these entries are never verified and never served; a CrPC section the table does not mention answers "no verified concordance".
