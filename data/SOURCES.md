# Source texts

The files live in `data/raw/` and are not tracked by git. Reuse terms for both are unconfirmed (see the spec's Out of Scope). Re-download from the URLs below and compare the hashes.

Downloaded 2026-10-09.

| File | Source | Pages | SHA-256 |
|---|---|---|---|
| `bns-prs.pdf` | https://prsindia.org/files/bills_acts/bills_parliament/2023/The%20Bharatiya%20Nyaya%20Sanhita,%202023.pdf | 102 | `67c92f7869420685e6cdc29b1bdde19fff91312b10241b3ed3e1163c5399600b` |
| `ipc-wipo.pdf` | WIPO Lex IN158, https://www.wipo.int/wipolex/en/legislation/details/22981 (the PDF link on that page is signed and expires) | 119 | `1f81d285b4bc912b335596ffbba44280d49169a56c0d21572c8bf3f6b6fedd4e` |

## Notes

- BNS is the Gazette extraordinary of 25 Dec 2023 (CG-DL-E-25122023-250883). The Hindi text uses a legacy font and extracts as garbage.
- IPC is a PDF, not HTML: the Code as amended up to Act 34 of 2019. It has an English text layer (section 511 found by pdftotext).
- Alternative for BNS if PRS is unsuitable: India Code, https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf (consolidated, current to 6 Oct 2025, so it may differ from the gazette text).

## LeSICiN benchmark data

`data/lesicin.manifest.json` pins the name, byte count and SHA-256 of the five files in `data/raw/lesicin/`, taken on 2026-10-11 from files that matched the Zenodo MD5s (https://zenodo.org/records/6053791). `ibid bench run` refuses a split or label file whose SHA-256 differs.
