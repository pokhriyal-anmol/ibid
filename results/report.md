# Ibid on the LeSICiN statute-identification benchmark

Scores are points, shown as micro-F1 / macro-F1 / Jaccard.

## Scores

| output | run | scores |
| --- | --- | --- |
| top-k | round 0 train | 6.20 / 3.47 / 4.04 |
| top-k | round 0 dev | 6.39 / 3.61 / 4.20 |
| top-k | frozen round (11) train | 8.96 / 5.85 / 5.23 |
| top-k | frozen round (11) dev | 9.34 / 6.01 / 5.50 |
| top-k | test score 1, k 5, r 0.7 | 9.37 / 6.07 / 5.43 |
| threshold | round 0 train | 6.18 / 3.42 / 4.26 |
| threshold | round 0 dev | 6.37 / 3.66 / 4.45 |
| threshold | frozen round (11) train | 9.20 / 5.92 / 5.36 |
| threshold | frozen round (11) dev | 9.71 / 6.22 / 5.62 |
| threshold | test score 1, k 5, r 0.7 | 9.64 / 6.21 / 5.52 |

## Train/dev gap (top-k, train minus dev, points)

| round | micro-F1 gap | macro-F1 gap |
| --- | --- | --- |
| 0 | -0.19 | -0.14 |
| 11 | -0.38 | -0.16 |

## Strata, top-k: dev round 0, dev frozen, test

| stratum | dev round 0 | dev frozen | test |
| --- | --- | --- | --- |
| label_count 1 | 1551 cases: 6.86 / 2.43 / 4.61 | 1551 cases: 6.58 / 3.30 / 3.99 | 1547 cases: 6.41 / 2.82 / 3.84 |
| label_count 2 | 1907 cases: 7.08 / 3.70 / 4.61 | 1907 cases: 9.00 / 5.77 / 5.41 | 2896 cases: 8.19 / 5.59 / 4.91 |
| label_count 3+ | 6742 cases: 6.22 / 3.61 / 3.99 | 6742 cases: 9.78 / 6.24 / 5.87 | 8596 cases: 9.96 / 6.38 / 5.89 |
| words 151-500 | 3040 cases: 5.16 / 3.32 / 3.50 | 3040 cases: 6.66 / 4.90 / 4.03 | 4046 cases: 6.84 / 4.21 / 4.11 |
| words <=150 | 1674 cases: 3.73 / 2.12 / 2.47 | 1674 cases: 4.60 / 2.56 / 2.78 | 2038 cases: 4.36 / 2.86 / 2.53 |
| words >500 | 5486 cases: 7.86 / 4.17 / 5.11 | 5486 cases: 12.22 / 7.46 / 7.14 | 6955 cases: 12.17 / 7.49 / 7.05 |

## Strata, threshold: dev round 0, dev frozen, test

| stratum | dev round 0 | dev frozen | test |
| --- | --- | --- | --- |
| label_count 1 | 1551 cases: 7.07 / 2.36 / 6.19 | 1551 cases: 7.06 / 3.57 / 5.56 | 1547 cases: 6.37 / 2.75 / 5.52 |
| label_count 2 | 1907 cases: 7.02 / 3.56 / 5.14 | 1907 cases: 8.70 / 5.73 / 5.64 | 2896 cases: 8.52 / 5.67 / 5.50 |
| label_count 3+ | 6742 cases: 6.19 / 3.69 / 3.86 | 6742 cases: 10.23 / 6.52 / 5.63 | 8596 cases: 10.23 / 6.45 / 5.53 |
| words 151-500 | 3040 cases: 4.70 / 3.04 / 3.33 | 3040 cases: 5.85 / 4.04 / 3.81 | 4046 cases: 5.77 / 3.73 / 3.96 |
| words <=150 | 1674 cases: 3.39 / 1.90 / 2.54 | 1674 cases: 3.66 / 1.79 / 2.76 | 2038 cases: 3.62 / 2.15 / 2.51 |
| words >500 | 5486 cases: 7.97 / 4.29 / 5.66 | 5486 cases: 12.58 / 7.95 / 7.49 | 6955 cases: 12.45 / 7.68 / 7.31 |

## Labels never found (test, top-k)

IPC 120, IPC 186, IPC 294(b), IPC 313, IPC 376(2), IPC 379, IPC 384, IPC 417, IPC 419, IPC 437, IPC 447, IPC 448, IPC 500

## Published scores, not comparable like for like

| metric | published | source |
| --- | --- | --- |
| m-F1 (micro or macro not confirmed) | 28.08 | IL-TUR benchmark, statute identification (arXiv 2512.21902 describes its splits) |
| macro-F1 | 28.45 | LeSICiN paper, Zenodo record 6053791 |

Caveats:

- Different models: the published scores come from trained classifiers, Ibid is deterministic retrieval with no training.
- Possibly a different dataset copy: Ibid uses the LeSICiN Zenodo release, the IL-TUR copy is gated and was not obtained.
- Split counts may differ from the published setup.
- Metric protocol may differ: our metrics are our own implementation until the official evaluation script is read.
- No rank is claimed.

## What these numbers rest on

- round 0: rule query-rule v2, rule hash 84d62cc13314d641ea3f5265fde5908bccc6f0cbe8a2e68b7659c39b49882eaa, dev_sha256 7a2b784aa79dd9148a686d53cadde5a9747e6ffc15a6a1a6c80359551b92bc12, index_sha256 efaf6fe8b342f151ac02ed110027320f39b0d99287327eb7d206453537a0d408, labels_sha256 a9d6221f39f35c8c89d8e5b03e77a8c5dd7aa97e095e895dbb40fc2e96d582df, parser 4, train_sha256 23a0aedcf52a08e22e064fdce78501698d33b576a1437e5a02ecdbb01b3a2da8
- frozen round (11): rule query-rule v2.11, rule hash 250c53f85b3dcaa5c370dcc7a0cbf8a6da7579bc0f398ea9be2341b4750a90bf, dev_sha256 7a2b784aa79dd9148a686d53cadde5a9747e6ffc15a6a1a6c80359551b92bc12, index_sha256 efaf6fe8b342f151ac02ed110027320f39b0d99287327eb7d206453537a0d408, labels_sha256 a9d6221f39f35c8c89d8e5b03e77a8c5dd7aa97e095e895dbb40fc2e96d582df, parser 4, train_sha256 23a0aedcf52a08e22e064fdce78501698d33b576a1437e5a02ecdbb01b3a2da8
- test score on split 9fc141a94b51febe3e3cd06494f13c587098afcda175fc2e3e4d6213a88b60d1: rule query-rule v2.11, rule hash 250c53f85b3dcaa5c370dcc7a0cbf8a6da7579bc0f398ea9be2341b4750a90bf
- test results file: split 9fc141a94b51febe3e3cd06494f13c587098afcda175fc2e3e4d6213a88b60d1, labels a9d6221f39f35c8c89d8e5b03e77a8c5dd7aa97e095e895dbb40fc2e96d582df, index efaf6fe8b342f151ac02ed110027320f39b0d99287327eb7d206453537a0d408, rule hash 250c53f85b3dcaa5c370dcc7a0cbf8a6da7579bc0f398ea9be2341b4750a90bf
- ledger rule matches the frozen round (11): yes
