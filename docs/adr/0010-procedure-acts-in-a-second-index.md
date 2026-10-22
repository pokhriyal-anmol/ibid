# 0010: The CrPC and BNSS live in a second index, not a rebuilt first one

The CrPC (and later the BNSS) is built into `data/index/procedure.sqlite`, with the same tables as `data/index/ibid.sqlite` plus a `heading` table and a `meta` table that records its own parser version (`CRPC_PARSER_VERSION`). `ibid mcp` opens the second file next to the first when it exists and ignores it when it does not.

**Why:** the first index's hash is recorded inside committed results, and BM25 statistics (document frequency, average length) depend on the whole corpus. Adding two Acts to that file would change every keyword score, the frozen rule's output and every pin. A second file leaves the first, `PARSER_VERSION` for the IPC and the BNS, `results/` and the pins byte-identical, and a test checks that.

**Cost:** a keyword search does not cross the two files. `search` stays on the first index until it gains an `act` argument, and a procedure Act's scores are never comparable with the IPC's. Anything that needs both must open both.

**Rule:** a new Act that would change the first index's corpus goes in a second file. Headings of the procedure Acts come from their Arrangement of Sections.
