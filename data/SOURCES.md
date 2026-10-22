# Source texts

The files live in `data/raw/` and are not tracked by git. Reuse terms for both are unconfirmed (see the spec's Out of Scope). Re-download from the URLs below and compare the hashes.

Downloaded 2026-10-09.

| File | Source | Pages | SHA-256 |
|---|---|---|---|
| `bns-prs.pdf` | https://prsindia.org/files/bills_acts/bills_parliament/2023/The%20Bharatiya%20Nyaya%20Sanhita,%202023.pdf | 102 | `67c92f7869420685e6cdc29b1bdde19fff91312b10241b3ed3e1163c5399600b` |
| `ipc-wipo.pdf` | WIPO Lex IN158, https://www.wipo.int/wipolex/en/legislation/details/22981 (the PDF link on that page is signed and expires) | 119 | `1f81d285b4bc912b335596ffbba44280d49169a56c0d21572c8bf3f6b6fedd4e` |

`data/sources.json` holds the same URLs, sizes and hashes for `ibid setup`, and a test (`tests/test_setup.py`) keeps its hashes equal to the table above.

## Notes

- BNS is the Gazette extraordinary of 25 Dec 2023 (CG-DL-E-25122023-250883). The Hindi text uses a legacy font and extracts as garbage.
- IPC is a PDF, not HTML: the Code as amended up to Act 34 of 2019. It has an English text layer (section 511 found by pdftotext).
- Alternative for BNS if PRS is unsuitable: India Code, https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf (consolidated, current to 6 Oct 2025, so it may differ from the gazette text).

## LeSICiN benchmark data

`data/lesicin.manifest.json` pins the name, byte count and SHA-256 of the five files in `data/raw/lesicin/`, taken on 2026-10-11 from files that matched the Zenodo MD5s (https://zenodo.org/records/6053791). `ibid bench run` refuses a split or label file whose SHA-256 differs.

## Slice 3 sources (2026-10-13), all under `data/raw/`, none committed

| File | Source | Bytes | SHA-256 | Licence |
|---|---|---|---|---|
| `capt/comparison_summary_BNS_to_IPC.pdf` | https://www.keralaprisons.gov.in/userfiles/act-and-rules/comparison_summary_BNS_to_IPC.pdf. "Correspondence table and comparison summary of the BNS to the IPC", 38 pages, by the Director of CAPT Bhopal (IPS), June 2024. A personal compilation, not an MHA publication. Its numbering is the enacted BNS (murder punishment is 103). | 716,640 | `3ad875b6162deb9d6a722244c537b1ffa72ee20e025f08a32d272f2612cf9a25` | not stated, copyright line names the author |
| `uppolice/ipc-vis-a-vis-bns.pdf` | uppolice.gov.in, "Three New Major Acts" folder. It is Project 39A's annotated comparison of the August 2023 *Bill*, 125 pages. Its clause numbers differ from the enacted BNS (murder punishment is clause 101), so it is not a source for BNS numbers. | 2,980,929 | `001386358dc793102ae4a8ac60ac7fb1bd6aff0c61c31e99b13394c57bcb082a` | not stated |
| `aila2019/AILA_2019_dataset.zip` | https://zenodo.org/records/4063986 (md5 07f9621e385ff0d4540ce8dfd76b0c21, matched) | 20,736,273 | `788bef2f15e4d6212fc3c5b4c302343c52fdbf261e1599e4f2e8d3df2a5fde55` | CC BY 4.0 |
| `ilsic/FT-Layman-test.jsonl.xz` | ILSIC (Law-AI/ilsic), Google Drive folder `Layman-new-dataset`. 836 posts, fields `instruction` and `answer` | 252,548 | `9f8eab7ba638f4413a3a30d0138c1de34173d5e9425bbfa1b9ef4d3ebdddf37d` | CC BY-NC-SA 4.0 (paper), code MIT |
| `ilsic/FT-LMsub-test.jsonl.xz` | ILSIC, folder `Layman-subset-data`. 757 posts | 232,444 | `32af14a42a93928e88afab3f2593459d3609397ce395e44fbef37b67fb5f4998` | as above |
| `ilsic/id-act-meta.json`, `id-section-meta.json`, `section-texts.json`, `queries_to_annotate.json` | ILSIC, top-level folder | 3,772, 105,306, 1,434,370, 319,818 | `e51d5e27…`, `b7c59f1d…`, `d5bf7f94…`, `27e98ac6…` | as above |

Not downloaded: the ILSIC `court-dataset` and `synthetic-layman-dataset` folders and the train and dev splits of the layperson sets. They are not needed for route D and the audit.

### CAPT correspondence table: licence and use (ticket 13)

Every page of `capt/comparison_summary_BNS_to_IPC.pdf` carries the line "© Anil Kishore Yadav, IPS, Director, CAPT Bhopal". No licence is stated, so the file stays under `data/raw/` and is not committed. Ibid reads it with `pdftotext -layout` and `ibid concordance from-table`, and keeps only section numbers and a row reference as evidence, not the table's comparison notes. Reports call it a personal compilation and not an official Ministry of Home Affairs publication.

### ILSIC-Lay posts in `gold/multicharge/v2.json`: privacy

The 30 posts are public forum text under CC BY-NC-SA 4.0 (non-commercial, share-alike, attribution to the ILSIC authors). The scrub removes emails, URLs, runs of 7 or more digits, titled names, `Name:` labels and IFSC codes. Untitled names, places and company names can remain, so the file must not leave the private repository.

### ILSIC layperson train split (2026-10-16, slice 6)

`ilsic/FT-Layman-train.jsonl.xz`: ILSIC (Law-AI/ilsic), Google Drive folder `Layman-new-dataset`. 6,465 posts, fields `instruction` and `answer`. 1,749,944 bytes. SHA-256 `6f998e08b0488c94f096db85395fac1a2f21331f1c2348aaee93d27c7a55a0d8`. CC BY-NC-SA 4.0, non-commercial. Gitignored under `data/raw/`. It names 118 distinct IPC sections (98 with at least 5 posts, 46 with at least 20), 63 of them in the 98-section ILSI label vocabulary. All 30 sections cited in `gold/multicharge/v2.json` appear in it, against 19 in the ILSI vocabulary. Approved by the owner for download on 2026-10-16; the dev split was not downloaded.

## Slice 15 sources (2026-10-22), under `data/raw/`, none committed

Downloaded 2026-10-22 with the owner's approval (D-007). Each was fetched into a fresh scratch directory, checked there (size against the server's `Content-Length`, first page read), then copied into place.

| File | Source | Bytes | SHA-256 | Notes |
|---|---|---|---|---|
| `bnss-prs.pdf` | https://prsindia.org/files/bills_acts/bills_parliament/2023/The%20Bharatiya%20Nagarik%20Suraksha%20Sanhita,%202023.pdf | 2,033,181 | `5e60e2afe30d0fe7eca4f8126301146b76c86a444e690581f81eb564843517fe` | Gazette extraordinary of 25 Dec 2023, CG-DL-E-25122023-250884, Part II Section 1, an Act of Parliament, 249 pages with the Hindi text. The BNS is …250883 |
| `capt/comparison_summary_BNSS_to_CrPC.pdf` | https://keralaprisons.gov.in/userfiles/act-and-rules/comparison_summary_BNSS_to_CrPC.pdf | 674,648 | `aa3e49147cf88141a8471a614246270ab4730cd3a4099e06de7a69792d80d33b` | 38 pages, author field "capt", created 21 Jun 2024. The BNSS is the first column. Every page carries "© Anil Kishore Yadav, IPS, Director, CAPT Bhopal" and no licence; the file stays out of git and Ibid keeps only section numbers and row references, as for the BNS table. A personal compilation, not an MHA publication |

Not yet fetched: the Code of Criminal Procedure, 1973 as in force until 30 June 2024. India Code (`https://www.indiacode.nic.in/bitstream/123456789/15381/1/ccp1973.pdf`) is the official copy but did not answer from this machine (60 second timeouts on three URLs, 2026-10-22). The WIPO Lex copy is consolidated only to 1991 and omits later amendments, so it is not a substitute.
