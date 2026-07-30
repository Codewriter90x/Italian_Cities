# Legacy baseline

This directory preserves the original dataset files before the Milestone 1
normalization work.

The files under `2023-05-02-original/` are byte-for-byte copies of the files
found on the `main` branch at commit
`09986a059cdf9ff8920a944faf6fa8e2f9cb88ac`.

They are historical evidence only. They must not be edited in place and do not
contribute to the v2 canonical dataset.

## Baseline inventory

| File | Size (bytes) | SHA-256 |
| --- | ---: | --- |
| `Italian Cities.csv` | 1,580,069 | `45f31340a6f0c390927aa1224424a75c6c968e601aa2df0a746413431e82d050` |
| `Italian Cities.xlsx` | 1,452,740 | `1949e669851e87288f4baf7ff2431daed92b573c64f706b41b1eda54b44e35ba` |
| `italian Cities.sql` | 8,529,320 | `bb7b496716510a5be012726eb617766bd5116e0aaf29338350c76c86891bdac8` |

The Excel metadata records creation on `2023-05-02T06:33:52Z` and modification
on `2023-05-02T06:51:41Z`. The SQL Server export header records
`2023-05-01 11:54:55`.

No earlier source snapshot, import script, or source citation is present in the
repository history.

Milestone 2 removes the duplicate root-level exports so they cannot be
mistaken for current editable data. The v2 pipeline reads the legacy CSV only
after the canonical build to produce `reports/legacy-comparison.json`.
