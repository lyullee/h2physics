# MHC v1.2 complete archive qualification

Lukas Fleming, [Experimental Dataset for a Two-Stage Metal Hydride Hydrogen Compressor, v1.2](https://doi.org/10.5281/zenodo.19036733), CC BY 4.0. The acquired repository metadata, README, license, overview, actual workbook schemas and source notes establish this profile. No publication prose, experiment values, source formulas, figures, code or source tables are reproduced here.

The offline local scan completed in 311.92 s. All 35 file members passed CRC and SHA-256 snapshotting; outer size 377874239 bytes, expanded directory 440954330 bytes. All 29 experiment workbooks and their 186 worksheets were inspected. The source overview independently contains the same 29 experiment numbers. The publisher MD5 and receipt metadata hash also matched. No member was extracted or executed.

Audit concurrency was bounded to 2 workbooks. Durable per-case checkpoints were used; resumed segments: 0. Elapsed time sums the recorded execution segments if a matching checkpoint is resumed.

## What the counts mean

XML numeric counts include stored dates, metadata, copied values and derived formula caches. Worksheet and export-grid row counts include padding. Repeated raw/selected exports are one physical experiment, so none of these counts proves independent measurement count, independent validation or experimental model acceptance.

- All-worksheet `stored_rows`: 655373.
- All-worksheet `populated_rows`: 251278.
- All-worksheet `numeric_rows`: 250224.
- All-worksheet `numeric_cells`: 11448663.
- All-worksheet `formula_cells`: 3809671.
- All-worksheet `missing_formula_caches`: 0.
- All-worksheet `error_cells`: 941985.
- All-worksheet `nonfinite_numeric_cells`: 0.

- Profile `grid_rows`: 1563461.
- Profile `populated_rows`: 520726.
- Profile `empty_rows`: 1042735.
- Profile `clocked_rows`: 516306.
- Profile `active_missing_clock`: 4420.
- Profile `nonincreasing_clock_edges`: 17.
- Profile `numeric_cells`: 5926605.
- Profile `valid_cells`: 5922270.
- Profile `negative_pressure`: 108429.
- Profile `negative_flow`: 0.
- Profile `raw_string_channels`: 10645.

## Complete experiment storage audit

| Experiment | Sheets | Stored rows | Numeric rows | Numeric cells | Formula cells | Missing formula cache | Error cells | Profile groups |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 19502 | 6360 | 228597 | 43694 | 0 | 0 | 6 |
| 2 | 5 | 21126 | 11628 | 420289 | 49637 | 0 | 11 | 7 |
| 3 | 4 | 21084 | 5929 | 313477 | 137206 | 0 | 51669 | 6 |
| 4 | 6 | 28286 | 11028 | 606464 | 279643 | 0 | 109277 | 9 |
| 5 | 4 | 21072 | 8115 | 448064 | 204109 | 0 | 76876 | 6 |
| 6 | 4 | 21079 | 6149 | 318079 | 109937 | 0 | 28503 | 8 |
| 7 | 4 | 21070 | 8951 | 441345 | 128135 | 0 | 33221 | 8 |
| 8 | 7 | 22987 | 10902 | 479059 | 165850 | 0 | 52224 | 6 |
| 9 | 7 | 22987 | 8549 | 368320 | 111846 | 0 | 34824 | 6 |
| 10 | 7 | 22989 | 7323 | 320279 | 110648 | 0 | 34823 | 6 |
| 11 | 7 | 22989 | 8595 | 369810 | 110648 | 0 | 34824 | 6 |
| 12 | 7 | 22989 | 7473 | 326129 | 111849 | 0 | 34823 | 6 |
| 13 | 7 | 22990 | 8185 | 353820 | 111851 | 0 | 34825 | 6 |
| 14 | 7 | 22990 | 10907 | 473292 | 161651 | 0 | 52225 | 6 |
| 15 | 7 | 22991 | 6116 | 273278 | 111850 | 0 | 34825 | 6 |
| 16 | 7 | 22991 | 6060 | 270601 | 110456 | 0 | 34390 | 6 |
| 17 | 7 | 22987 | 6099 | 272921 | 111846 | 0 | 34825 | 6 |
| 18 | 7 | 21188 | 12517 | 545532 | 165849 | 0 | 48623 | 6 |
| 19 | 7 | 21189 | 7307 | 322073 | 111849 | 0 | 32423 | 6 |
| 20 | 7 | 22988 | 7305 | 322054 | 111849 | 0 | 32423 | 6 |
| 21 | 7 | 22988 | 7305 | 322054 | 111849 | 0 | 32423 | 6 |
| 22 | 7 | 22986 | 11832 | 565345 | 178553 | 0 | 17991 | 6 |
| 23 | 7 | 22986 | 8558 | 401583 | 119153 | 0 | 11991 | 6 |
| 24 | 7 | 22987 | 10461 | 511886 | 178553 | 0 | 17991 | 6 |
| 25 | 7 | 22990 | 8517 | 400060 | 119152 | 0 | 11991 | 6 |
| 26 | 7 | 22991 | 11019 | 533676 | 178552 | 0 | 17991 | 6 |
| 27 | 7 | 22991 | 8042 | 381610 | 119152 | 0 | 11991 | 6 |
| 28 | 7 | 22990 | 8725 | 408133 | 119152 | 0 | 11991 | 6 |
| 29 | 7 | 22990 | 10267 | 450833 | 125152 | 0 | 11991 | 6 |

## Recorder and schema issues

Independent calendar and elapsed/time-of-day clocks remain separate. Clock missingness, duplicate/backward edges, first/last source rows, headers, unit evidence cells, sensor hardware/alias identities, profile array/mask/row fingerprints and same-grid-row clock differences are recorded in the ignored local audit. Those differences are diagnostics, not synchronization estimates or accepted clock mappings.

- Experiment 1 is an argon thermal case; its declared defective Picolog T-2_1 is masked with the source note identity while retaining its cache. Experiment 2 is a non-hydrogen thermal case with unresolved fill gas; its separate AV thermometer calibration export has a different date and retains its own clock/group.
- Experiments 6 and 7 use a loading-station export with a time-of-day field and Flow-3 strings containing commas. Its date and relationship to Labview are unresolved. Those strings remain raw and invalid as numeric observations; no decimal/thousands interpretation is guessed. Selected-cycle copies omit that export clock. Missing channel units remain unresolved instead of being filled from a generic template.
- Typed calendar fields, ISO strings (experiment 3), day.month.year recorder strings (experiment 22), unformatted Excel serial dates/datetimes (including experiment 8 Labview and selected exports in experiments 4/19/22), and fractional-day Time fields decode against the workbook's declared Excel epoch and Date/Time headers. Raw representations and epoch evidence remain available; no recorder shift is applied. Raw headers begin at different source rows in experiments 3 and 18. Experiment 4 has two selected cycles with the source nl/min spelling. Experiments 6 and 7 have distinct alias/unit layouts. Literal aliases, including unassigned raw Graphtec channels, are retained.
- Pressure bar is scaled to Pa without assigning absolute/gauge basis. Barg remains reported gauge pressure without an atmospheric offset. HTF l/min is volume flow; ln/min and nl/min are reported reference volume flow with unresolved reference P/T, never mass flow. Temperatures use K but keep their source sensor identities; no shell-to-bed or spatial averaging operator is supplied.
- PCI workbook records, material parameters and experiment mass/heat/efficiency summaries are outside the independent logger-measurement profile. Their presence is not independent validation evidence. Protocol/source notes include incomplete histories and possible unmeasured release paths; a compressor inventory/energy fit is not qualified here.

## Source member fingerprints

- Outer archive SHA-256: `91755fb1e555e0eb32d160ac140a4261b6bb47d24944c7e717b723fe2a641e32`.
- Recomputed publisher checksum: `md5:64cbe2a68c0af5dc2e4a0a9690003eac`.
- Repository metadata SHA-256: `0e6f3bca640b9c4994c04941394614142b4b789070102934859bdd4dfeb513bf`.

| Member (root prefix omitted) | Bytes | SHA-256 |
|---|---:|---|
| Dataset/Experiment 1.xlsx | 12528398 | `350af6df65d7fa97b94be527ad174f2bf52a1dc33a4dc35c2696a1a8eef4b9fe` |
| Dataset/Experiment 10.xlsx | 13763713 | `fbd160c6f9cd1eb947fa08269251fdb03ae351fc1bd813e947e1933db53736c6` |
| Dataset/Experiment 11.xlsx | 14083613 | `29e28421fb284faa1ca17e168e02b91724967f93192a907df09d0fddee3be7e0` |
| Dataset/Experiment 12.xlsx | 13794277 | `7363f18ff019f63bef44d4939d9484a46b981220c77c267b39100b30461f5ac0` |
| Dataset/Experiment 13.xlsx | 14027966 | `82134558eec650a7b38b5194974c188a60ce5a41a6fa4a738351ea1460550ef5` |
| Dataset/Experiment 14.xlsx | 15391719 | `7e03e0783fc599e63f20a17ed9a8651ba5d6599f0f896dc260f00a6b6607af0f` |
| Dataset/Experiment 15.xlsx | 13622003 | `a44c35b7391512395d7001a2c8040dacafe25247d2fa75242c26614139b74eb7` |
| Dataset/Experiment 16.xlsx | 13572301 | `9f0506ed41923d1eb0a24bed09bd4c8076e26975b167affd8cb0847cc92129b8` |
| Dataset/Experiment 17.xlsx | 13584118 | `4be3c16b4ab4321481f868bef6349b4e2e34672dcdb83a58214faa4256e6590b` |
| Dataset/Experiment 18.xlsx | 15761428 | `85b55ef1979e5d0e1e80541c8b7d54142606c41ee9a5bb6972c1e2faa3fe96d2` |
| Dataset/Experiment 19.xlsx | 13682874 | `e812ac445e8c74e9b2970d4fcba6161cd2810b7fdd8337dbd98967c12de1043d` |
| Dataset/Experiment 2.xlsx | 14413027 | `d67ed8c279e38a792c59c793c52261b7cfe4c6b69a96c3a625f2f1ca88ec606c` |
| Dataset/Experiment 20.xlsx | 13812633 | `394437b70661f539c99d265a97aad5b2aa8bc9f168f842d6676b07c8d71a0e2f` |
| Dataset/Experiment 21.xlsx | 13798246 | `3c886230a72ecf6867cfac5b5a8f3dd5f6334816e67ba0503ac49259ab5988d3` |
| Dataset/Experiment 22.xlsx | 16912962 | `971f39376900a167ad9cd1eea6031918ec8e0923adc2f4cdf822592f65bfdaa9` |
| Dataset/Experiment 23.xlsx | 15076091 | `c71892bd10a2d8467945faf49ba8db3e22895e2931ed16f3e00cee5c1963dfb5` |
| Dataset/Experiment 24.xlsx | 16508055 | `ffee1719c719fb6c005f26bdf2aa8dbf8607d1e75b393665b5f1913fdd777b49` |
| Dataset/Experiment 25.xlsx | 14999593 | `1ad4179a63d33cc7130d6dc9c6c6592150092242fdb4ace46b79162c5f2a0ab6` |
| Dataset/Experiment 26.xlsx | 16598806 | `54cba23ace8443fb9ff5b847a4af28f63337ce69af5155dc1788ca9806a99dbc` |
| Dataset/Experiment 27.xlsx | 14858506 | `f34ef231d91822e14710bbbbf5432d51bf8675e8dadf26ee0fab7f2c32113586` |
| Dataset/Experiment 28.xlsx | 15073869 | `e00a7f514cadfd3c086a922ca332291f31c2afb53f1374412f5ca9b5cec578d6` |
| Dataset/Experiment 29.xlsx | 15385391 | `b2b56433a4bfbc5a496e2c2f6c68e15c9f66586db85ae13344f292b33932309b` |
| Dataset/Experiment 3.xlsx | 13953345 | `d3e73263ab7ac88487b3436411596420a5766ecbbb9c89ff164b62a859240153` |
| Dataset/Experiment 4.xlsx | 17822440 | `08cc53523e33f2320d60dc03ed66220ee2bfbc49caaf82215718a8e760f1eee1` |
| Dataset/Experiment 5.xlsx | 15569780 | `971d14ad42f703cf7b6df070657a723c840aa231a1f7bb7fcd2acb61d5f8a191` |
| Dataset/Experiment 6.xlsx | 13563384 | `a374fc8b8515f8e7ec45ce09317c7459d080282902aa1e6d5a5795ccaac48005` |
| Dataset/Experiment 7.xlsx | 14546952 | `f95c34e02a9d750123fdeb9dfca895fa2430f9651118d3a295f848fb5a2a76f2` |
| Dataset/Experiment 8.xlsx | 15386747 | `45f38b098f1ad45802c5e173171ce7ceb9e89720ad339da13e2fc674ae2ca43b` |
| Dataset/Experiment 9.xlsx | 14105210 | `153051549773686dce0dcf5a92184659fa746b3ac2f2c7deeb2ebb784ad4683e` |
| Experiment Overview.xlsx | 11731 | `978bb9754af52cf1ec2f10a07e492e4b921c3771d5135d2056e8490262034b82` |
| LICENSE | 829 | `301f90826e9275eda9b64bca216e1a9dc3c1b267d5e650c4a2014a91b1f480f4` |
| PCI data.xlsx | 119034 | `01a4deca4e0d76d689f24b0df2dd1418a16a01daff1e2716fe8d3366837713a9` |
| README.txt | 3304 | `d408d6a6d66716e210f2555e866a9651da1e6393c26d0840f024544fd1d7bace` |
| Stage-I.STEP | 7677045 | `ccf02262f4a192654738bf42b9c5ba463dbe11a85ea9d42de02e8436a8ccb884` |
| Stage-II.STEP | 6944940 | `1118c7515bac9a1ac40e6e92195d212334efaa4d004e52c420f8597fb6ce7ed2` |

## Executed source fingerprints

Begin and end hashes matched; every listed source used LF endings.

- `src/h2physics/data/hydride_compressor.py`: `b978d09c620a9e5f24a1f4b80143969ecbdcfcbc5d525c02c0268b7808f777aa`
- `tests/test_hydride_compressor_data.py`: `feff9ee6003662d6cf5ea609779f896575bbda7c49a5d5487891010826f4d786`
- `scripts/check_hydride_compressor_data.py`: `8a24d7fed7c8e9a155c70db7ddcae4ad281ae26812dfd5708ae6470a43244be9`

The complete machine-readable audit, source notes/headers and all-sheet counts remain at ignored `data/processed/hydride-compressor/v1.2/profile-audit.json`. External raw/normalized observations are not release inputs. Receipt rights permission does not change the unchanged `validation_qualified = false` status.
