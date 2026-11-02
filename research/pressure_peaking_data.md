# USN unignited pressure-peaking data ingestion

Audit completed UTC: 2026-10-27T01:45:35.150737+00:00. Profile: `usn-pressure-unignited-v1-profile-1`.

Source: Agnieszka Lach and Andre Vagner Gaathaug, [Hydrogen safety: Pressure Peaking Phenomena-unignited releases, version 1](https://doi.org/10.23642/usn.17932439.v1), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The acquired receipt and metadata retain the rights evidence and attribution.

This offline run recomputed SHA-256, publisher MD5 and size for every acquired attachment, then consumed every row of all eight acquired MAT exports and nine XLSX exports. Two listed MAT files (source experiments 00002/00009) remain omitted by the acquisition receipt. The two DOCX guides were checksum verified; their XML had been inspected for the profile. Raw and normalized external observations remain excluded from Git/distributions.

Actual totals: `{'files_hashed': 19, 'mat_files': 8, 'xlsx_files': 9, 'sigma_rows': 7999992, 'gen3i_rows': 33310586, 'xlsx_rows': 78272, 'negative_flow_rows': 1288623, 'negative_meter_pressure_rows': 197, 'negative_concentration_rows': 16, 'xlsx_missing_cells': 364, 'xlsx_invalid_cells': 380, 'xlsx_clock_violations': 0, 'xlsx_invalid_clock_cells': 0}`.

The MAT variables named `dimensions` contain units, while `units` contain channel labels. SIGMA is seconds, signed g/s and bar at the Coriolis meter/outlet. Only unit scaling is applied; absolute/gauge pressure, a nozzle state and a physical release direction are unresolved. Negative flow and meter-pressure values remain present and are counted below. GEN3i exports time/P1 in seconds/kPa, although the guide identifies column 3 as overpressure. All four dimension labels and 35 channel labels survive; the unavailable channels are not reconstructed. Exported P1 is retained as reported pressure with the column conflict in its basis.

Recorder clocks are independent per file/matrix/device. Neither matching experiment IDs nor similar elapsed-clock starts establish synchronization. No baseline subtraction, automatic time shift, averaging between sensors or negative clipping is performed. Finite MAT values have numerical validity masks; unresolved reported-pressure bases prevent their automatic use as absolute/differential model pressures.

| MAT source file | SIGMA rows | GEN3i rows | Negative flow | Negative meter pressure | SIGMA invalid cells | GEN3i invalid cells | Exported P1 min/max (Pa) |
|---|---:|---:|---:|---:|---:|---:|---|
| HTE242USN_00011_READ190621.mat | 999999 | 998100 | 776 | 27 | 0 | 0 | -290.11068 / 7030.9578 |
| HTE242USN_00003_READ190621.mat | 999999 | 2193192 | 3550 | 30 | 0 | 0 | -8.45553502 / 697.55912 |
| HTE242USN_00005_READ190621.mat | 999999 | 3705861 | 370351 | 18 | 0 | 0 | -450.6899 / 6472.9486 |
| HTE242USN_00006_READ190621.mat | 999999 | 3803801 | 375682 | 17 | 0 | 0 | -390.88028 / 6759.2174 |
| HTE242USN_00004_READ190621.mat | 999999 | 3959832 | 375891 | 18 | 0 | 0 | -398.17598 / 2892.4048 |
| HTE242USN_00010_READ190621.mat | 999999 | 6110895 | 5621 | 26 | 0 | 0 | -9.90357652 / 6724.247 |
| HTE242USN_00007_READ190621.mat | 999999 | 6093238 | 80330 | 31 | 0 | 0 | -4.4632096 / 4078.7472 |
| HTE242USN_00008_READ190621.mat | 999999 | 6445667 | 76422 | 30 | 0 | 0 | -4.67362312 / 3972.9648 |

| Source / matrix | First/last time (s) | Minimum/maximum adjacent step (s) | SI value-stream SHA-256 | Validity-stream SHA-256 |
|---|---|---|---|---|
| HTE242USN_00011_READ190621.mat / SIGMA | 0.001 / 999.999 | 0.000999999999976 / 0.00100000000009 | `87307d2d937ddbc6e5e66febbde92f650da91767113c61f3944c49f01a5e985e` | `42bb9d464840e8c97683cd0c198a1c1a3314c1cc0036c8688b9cc2b8edde7bef` |
| HTE242USN_00011_READ190621.mat / GEN3i | 0 / 998.099 | 0.000999999999976 / 0.0010000000002 | `5e3ec24535267d796a5b1a53b7f535dcca369611d6a8683d015f1f65bd7dd6c8` | `90a8513d575d110e06eff311eae1295d63302582c61816d72949f8abc5e5683a` |
| HTE242USN_00003_READ190621.mat / SIGMA | 0.0002 / 199.9998 | 0.000199999999978 / 0.000200000000007 | `61ff654c0593ceedb1a2b7c26d734a943bbfa731855b0b649b17e38ba0ecd44f` | `42bb9d464840e8c97683cd0c198a1c1a3314c1cc0036c8688b9cc2b8edde7bef` |
| HTE242USN_00003_READ190621.mat / GEN3i | 0 / 87.72764 | 3.99999999914e-05 / 4.00000000127e-05 | `5167e59659f207c91b5807c938d09aeb4dac02e6907fce14a8941a3ea7542d49` | `0b7fd00c6fce09010a446685cab67254ea7e29aa540e92f855ef0d1e8996de05` |
| HTE242USN_00005_READ190621.mat / SIGMA | 0.0002 / 199.9998 | 0.000199999999978 / 0.000200000000007 | `ff6faa89369530beba0104741781aefb7097fde20c139167de3c4dbaea79a2f3` | `42bb9d464840e8c97683cd0c198a1c1a3314c1cc0036c8688b9cc2b8edde7bef` |
| HTE242USN_00005_READ190621.mat / GEN3i | 0 / 148.2344 | 3.99999999843e-05 / 4.00000000269e-05 | `60d8b75640574ce0bb121da104bc33abf934d7f983f6121f2ad970117ec2b92e` | `06b58fd62907996f0a8c0486a1bf7a976792aaac0b003841ef705a6b6bc60439` |
| HTE242USN_00006_READ190621.mat / SIGMA | 0.0002 / 199.9998 | 0.000199999999978 / 0.000200000000007 | `73265f1f262ef1288700ffec8d6e2d8ebff3eaadce7e52a4fc46bf4d370bb395` | `42bb9d464840e8c97683cd0c198a1c1a3314c1cc0036c8688b9cc2b8edde7bef` |
| HTE242USN_00006_READ190621.mat / GEN3i | 0 / 152.152 | 3.99999999843e-05 / 4.00000000198e-05 | `650d2946c7215f6f79851cf927fcac35d0bd70ec703dfb20ae7866bea579a3af` | `7b01029641005e590600ba38a84be4c0ae728bb32d2be0cb9ef09963b6ebedd0` |
| HTE242USN_00004_READ190621.mat / SIGMA | 0.0002 / 199.9998 | 0.000199999999978 / 0.000200000000007 | `c9c65c31bb03be766f303b6877d7dfe26a88d61227e4bbd506da450b6f8fdaad` | `42bb9d464840e8c97683cd0c198a1c1a3314c1cc0036c8688b9cc2b8edde7bef` |
| HTE242USN_00004_READ190621.mat / GEN3i | 0 / 158.39324 | 3.99999999843e-05 / 4.00000000127e-05 | `b71ae27a6c5901dc2789891949f4933e0e8b32bf732cade73b1a9d1f02f8adb4` | `3c66b5505e51a6e0ca21167ce9c95b88c7c6fbe6763eaa1ed24592b425444f59` |
| HTE242USN_00010_READ190621.mat / SIGMA | 0.0002 / 199.9998 | 0.000199999999978 / 0.000200000000007 | `34468fb8bc8ba9f2bbbda5014a9ae545023c302ec037714d61589f7a117c7102` | `42bb9d464840e8c97683cd0c198a1c1a3314c1cc0036c8688b9cc2b8edde7bef` |
| HTE242USN_00010_READ190621.mat / GEN3i | 0 / 244.43576 | 3.99999999843e-05 / 4.00000000127e-05 | `f9aa9229ea555690109c65c3300259b04608afdb3d3f09a52190812708148b96` | `3825c108cf3a2cb52578e82253d60ae99a3829bd231afae73b364a373014e929` |
| HTE242USN_00007_READ190621.mat / SIGMA | 0.0002 / 199.9998 | 0.000199999999978 / 0.000200000000007 | `83f6989d0a89a496917915e4f48f3cb874509b68cf0f843442e86289ee6424d6` | `42bb9d464840e8c97683cd0c198a1c1a3314c1cc0036c8688b9cc2b8edde7bef` |
| HTE242USN_00007_READ190621.mat / GEN3i | 0 / 243.72948 | 3.99999999843e-05 / 4.00000000127e-05 | `9f6e618b7b6a0487b4f88292f2a68998170ae14888a5ce63ab8f60dbc10529fd` | `f6459a21fe78b8258acd38e1aef6b13e224b956e2a88b7255411687598e48605` |
| HTE242USN_00008_READ190621.mat / SIGMA | 0.0002 / 199.9998 | 0.000199999999978 / 0.000200000000007 | `8c48d2f9449d190e5e897b2f0c5b981cc855cfc88fc94f1d75551ab586b7a8a7` | `42bb9d464840e8c97683cd0c198a1c1a3314c1cc0036c8688b9cc2b8edde7bef` |
| HTE242USN_00008_READ190621.mat / GEN3i | 0 / 257.82664 | 3.99999999559e-05 / 4.00000000127e-05 | `6d967d08c0b3b11f07ded4b20903310140c15ad2c33334f433e4619807afb3e9` | `83acfd20c1bac7b87a40c90fbfe9128316b40f73a7412a9210e0948632ca50b7` |

XLSX row 1/2 device/calibration metadata and literal row-3 headers are retained. The two documented Celsius glyph variants are recognized without changing the stored header. All 17 columns and each original worksheet row survive. Column B contains local time-of-day strings, despite the guide describing seconds; conversion preserves seconds since local midnight, without an inferred date/timezone or midnight unwrapping. Iteration numbers are not row identities. Output percent is scaled by 0.01 and retained as reported point-sensor concentration; its volume/mole convention, sensor location and response still need qualification. Negative/over-100-percent values are present but masked for physical concentration use. Missing cells are NaN/masked, alarms remain source codes, and the AH pressure-like column retains unresolved semantics. Pt100/Tsens are separate instrument temperatures.

| XLSX source file | Rows | Missing numeric cells | Invalid cells | Negative output | Invalid output | Clock violations | Invalid clock | Repeated iteration pairs | Nonzero alarm | Device / factory ID |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| HTE242USN00003CON190621.xlsx | 547 | 336 | 345 | 9 | 33 | 0 | 0 | 0 | 24 | 04DC07 / 04DC07 |
| HTE242USN00002CONC190621.xlsx | 753 | 14 | 14 | 0 | 1 | 0 | 0 | 0 | 753 | 04DC09 / 04DC09 |
| HTE242USN00008CON190621.xlsx | 2671 | 0 | 0 | 0 | 0 | 0 | 0 | 1335 | 50 | 04DC12 / 04DC12 |
| HTE242USN00006CON190621.xlsx | 5621 | 14 | 14 | 0 | 1 | 0 | 0 | 0 | 2 | 04DC10 / 04DC10 |
| HTE242USN00007CON190621.xlsx | 12213 | 0 | 0 | 0 | 0 | 0 | 0 | 6106 | 0 | 04DC10 / 04DC10 |
| HTE242USN00010CONC190621.xlsx | 13018 | 0 | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 04DC10 / 04DC10 |
| HTE242USN00010CONT190621.xlsx | 13018 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 32 | 04DC12 / 04DC12 |
| HTE242USN00009CONC190621.xlsx | 15211 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 04DC10 / 04DC12 |
| HTE242USN00009CONT190621.xlsx | 15220 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 04DC12 / 04DC12 |

| XLSX source file | First/last raw clock | Reported fraction min/max | SI value-stream SHA-256 | Validity-stream SHA-256 |
|---|---|---|---|---|
| HTE242USN00003CON190621.xlsx | 09:45:08.38 / 09:47:54.45 | -0.00033 / 0.28416 | `fc71ccb6535874a5638238aa216793b9db92e20e69d010335371e99f46e8e904` | `f5c0ff029e9666c175d00caf83d5c956ab6fe3ebbb9be63d4765bc4ba055fc58` |
| HTE242USN00002CONC190621.xlsx | 14:33:41.76 / 14:37:27.18 | 0.00312 / 0.13434 | `015ce9715419f8177d4600dc2e9dc705568489d035353c8b637b66203fc7ea64` | `f055d5d420521a8421eb9b382c56219f96bd9c97e394507766d36630ee3b9e2d` |
| HTE242USN00008CON190621.xlsx | 12:37:53.10 / 12:51:14.15 | 0.0055 / 0.35579 | `db0cfac08a746a2313ddaea472a57ea4a08c88de58986ae7d131a66c570ae007` | `2c3e7d13d99a50d32451a69121cc0035db043c96e557f36ca83983246dcd15b2` |
| HTE242USN00006CON190621.xlsx | 14:31:31.94 / 15:43:25.01 | 0.02167 / 0.62508 | `7e11b08f0f9e307745aba680935e183433759dc8e1aaa804e290968bf7855c71` | `b6e19a69821fb264e4ad5b9d23001947e878826d3073cf3282bccd1af15b0200` |
| HTE242USN00007CON190621.xlsx | 11:01:30.87 / 12:02:34.73 | 0 / 0.35128 | `36ee84fb4cd3eb5be2a445d76cbbe1d960461dcedef2934a3b721e2e98364606` | `b8ede04c0a1a05b8efc6461a1fe849472ba479a2a24d0594da2ba900d0e30f59` |
| HTE242USN00010CONC190621.xlsx | 09:58:15.63 / 11:03:21.01 | -0.00111 / 0.47038 | `a4b2b544234f8bc442e6a848fd6fd6602edf57d4ba73ad57ae9d94aed25ec2a2` | `ab140b6410f0eb0945161d161785d29c6954674011bbf69dec008abb38bb23b0` |
| HTE242USN00010CONT190621.xlsx | 09:58:15.64 / 11:03:21.01 | 0.00061 / 0.47373 | `9a115a4b06fb332546b928d9cc117585eabd6732396d1e1defc49bb38c9d543f` | `d24763a7dcb45249d6cab50cfda3d6df5a1f31cf69ca1c59d76c3c34e71a1dba` |
| HTE242USN00009CONC190621.xlsx | 14:18:31.87 / 15:34:35.20 | 0.00949 / 0.52841 | `ad10fc2290839783361ba098a1c885b086557a5545f2e32429908026b3309064` | `f9acc3d11ca039faecd51a5bc835656a5902bc857a27bd30dfc8b6920e38dda5` |
| HTE242USN00009CONT190621.xlsx | 14:18:29.18 / 15:34:35.21 | 0.01044 / 0.5276 | `1cd6e491cb9f8b7110cb83a4f9d7ba3e3d53c2303cb4a732c8b85dd62842f4c8` | `cafb344dc5a0b478f8430400acc1263fd62616cc1c7d4a886c00c4327d336468` |

Observed XLSX issue counts (source file / channel / reason):

- HTE242USN00003CON190621.xlsx / ah_reported_pressure / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / battery_fraction / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / battery_voltage / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / corrected_transfer / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / ih / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / ph / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / pt100_temperature / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / relative_humidity / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / reported_h2_concentration / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / sensor_temperature / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / system_voltage / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / transfer / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / uh / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / utp / `missing_or_nonnumeric`: 24.
- HTE242USN00003CON190621.xlsx / reported_h2_concentration / `outside_reported_fraction_domain`: 9.
- HTE242USN00003CON190621.xlsx: first/last row IDs `10.23642/usn.17932439.v1:HTE242USN00003CON190621.xlsx|Sheet1|row-4` / `10.23642/usn.17932439.v1:HTE242USN00003CON190621.xlsx|Sheet1|row-550`.
- HTE242USN00002CONC190621.xlsx / ah_reported_pressure / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / battery_fraction / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / battery_voltage / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / corrected_transfer / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / ih / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / ph / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / pt100_temperature / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / relative_humidity / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / reported_h2_concentration / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / sensor_temperature / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / system_voltage / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / transfer / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / uh / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx / utp / `missing_or_nonnumeric`: 1.
- HTE242USN00002CONC190621.xlsx: first/last row IDs `10.23642/usn.17932439.v1:HTE242USN00002CONC190621.xlsx|Sheet1|row-4` / `10.23642/usn.17932439.v1:HTE242USN00002CONC190621.xlsx|Sheet1|row-756`.
- HTE242USN00008CON190621.xlsx: first/last row IDs `10.23642/usn.17932439.v1:HTE242USN00008CON190621.xlsx|Sheet1|row-4` / `10.23642/usn.17932439.v1:HTE242USN00008CON190621.xlsx|Sheet1|row-2674`.
- HTE242USN00006CON190621.xlsx / ah_reported_pressure / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / battery_fraction / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / battery_voltage / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / corrected_transfer / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / ih / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / ph / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / pt100_temperature / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / relative_humidity / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / reported_h2_concentration / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / sensor_temperature / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / system_voltage / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / transfer / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / uh / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx / utp / `missing_or_nonnumeric`: 1.
- HTE242USN00006CON190621.xlsx: first/last row IDs `10.23642/usn.17932439.v1:HTE242USN00006CON190621.xlsx|Sheet1|row-4` / `10.23642/usn.17932439.v1:HTE242USN00006CON190621.xlsx|Sheet1|row-5624`.
- HTE242USN00007CON190621.xlsx: first/last row IDs `10.23642/usn.17932439.v1:HTE242USN00007CON190621.xlsx|Sheet1|row-4` / `10.23642/usn.17932439.v1:HTE242USN00007CON190621.xlsx|Sheet1|row-12216`.
- HTE242USN00010CONC190621.xlsx / reported_h2_concentration / `outside_reported_fraction_domain`: 7.
- HTE242USN00010CONC190621.xlsx: first/last row IDs `10.23642/usn.17932439.v1:HTE242USN00010CONC190621.xlsx|Sheet1|row-4` / `10.23642/usn.17932439.v1:HTE242USN00010CONC190621.xlsx|Sheet1|row-13021`.
- HTE242USN00010CONT190621.xlsx: first/last row IDs `10.23642/usn.17932439.v1:HTE242USN00010CONT190621.xlsx|Sheet1|row-4` / `10.23642/usn.17932439.v1:HTE242USN00010CONT190621.xlsx|Sheet1|row-13021`.
- HTE242USN00009CONC190621.xlsx: configured device ID differs from factory ID; no reassignment applied.
- HTE242USN00009CONC190621.xlsx: first/last row IDs `10.23642/usn.17932439.v1:HTE242USN00009CONC190621.xlsx|Sheet1|row-4` / `10.23642/usn.17932439.v1:HTE242USN00009CONC190621.xlsx|Sheet1|row-15214`.
- HTE242USN00009CONT190621.xlsx: first/last row IDs `10.23642/usn.17932439.v1:HTE242USN00009CONT190621.xlsx|Sheet1|row-4` / `10.23642/usn.17932439.v1:HTE242USN00009CONT190621.xlsx|Sheet1|row-15223`.

Checksum-pinned original attachments (all SHA-256/MD5/size checks passed):

| Source file | SHA-256 |
|---|---|
| Readme_Hydrogen safety- Pressure Peaking Phenomena-unignited releases.docx | `38a16a3e21ed6f5c14fe5876d5514ad03f9349acca4e75cf14b608e69ed4934a` |
| File handling guide.docx | `f7b54633adf9a6e71fa5d7074df17cdb34c5a76793b3dbb8f8bce770b794cd1c` |
| HTE242USN00003CON190621.xlsx | `18b88ddb67cb85d271fc24c20557fb05415331c9f2cf38fc6d097fc921be6abc` |
| HTE242USN00002CONC190621.xlsx | `dcc24131a260947d62ade62848e27573789a9c53c71d1275cb85ee6425f05c9c` |
| HTE242USN00008CON190621.xlsx | `01b0870ec6cfc6a9be5bd218eea21bebd2fe57647a3f21ec990360bee5bc70b4` |
| HTE242USN00006CON190621.xlsx | `28ffec511b48a8f4ecff9174bb7c2e224e56f0a2a241806e90dcf05ee1c381f7` |
| HTE242USN00007CON190621.xlsx | `efd608de486c9f2eb4301771e08a7071ecd5d1d87c20bfd279e3dfa88ed0b1ba` |
| HTE242USN00010CONC190621.xlsx | `ead3a891e54cbe3a3e7f59f27743877248c04b66328341510d7d7c2585c9f030` |
| HTE242USN00010CONT190621.xlsx | `1a5f19b431fbeb66317636a99bd5e6330ce2e77d1b9789223c7fee9f656e2a20` |
| HTE242USN00009CONC190621.xlsx | `d1b0dd4c9949c0068180283a8eb819e93c6d4deccd7196b81ce961019dd8e883` |
| HTE242USN00009CONT190621.xlsx | `b26bb8f23cabd7024510be88660b4fd1ddb964c22943faec7f849ee7c0213df9` |
| HTE242USN_00011_READ190621.mat | `879e516bf1338d7c28f06a9fd428522212fc6d4b9af4b5f80d8694034d4fd675` |
| HTE242USN_00003_READ190621.mat | `f74643684fac53ec8e57893f6647b33fd0313da3cb5a1038c0b8c44ce425f1f0` |
| HTE242USN_00005_READ190621.mat | `fbcb9292621636e028f3a80be0bee852656b2f8ca6941fc970d74222b8ac8bbb` |
| HTE242USN_00006_READ190621.mat | `35f463419fd7e5f1cd8c191e2d39222da005d16d6c098b36de00b77fb40bcf2c` |
| HTE242USN_00004_READ190621.mat | `d9a22faf051746eab07c3a2469e8d6c5f97bf803d2a8897d0680b0535a9a9c12` |
| HTE242USN_00010_READ190621.mat | `5397d2ac69961f80a44041ba78c70a3e3fe590b2c8bdcda8edb02383d1c2c504` |
| HTE242USN_00007_READ190621.mat | `28911d384b0bc58f150b6e8689a7570abdb7195d13f188a4c7d4c54bec5cd96f` |
| HTE242USN_00008_READ190621.mat | `3e3a400e38022c87cdbbaa1d7460cbfae78e3dd3b4dd72855394e6c8bf85f066` |

Acquisition receipt SHA-256: `8ab175b1b804b7efb07782678f8ac849f10efa23e4960e6deac78422f54cca8d`. Repository metadata SHA-256: `5f3b36592db6dec7985ee20f4c56d8cf371595f4c99fe0d1e59451b7299dfae6`.

SI value digests concatenate canonical little-endian float64 rows (MAT: time then channels; XLSX: all 17 normalized columns), while validity digests concatenate row-major boolean bytes. They are independent of block size for the same parsed values/masks; meanings are pinned by the source/profile/code hashes. No normalized observation file is released.

Host code SHA-256:

- `src/h2physics/data/pressure_peaking.py`: `44235ac1ffa7e447ebc58a42eba5368e8008af517f48bd3605fa41140507fa15`.
- `scripts/check_pressure_peaking_data.py`: `5229a3aa7ac336a1710b4c2c881279d51330382f6091cc86ccd70ae72c235bbc`.

This is an ingestion/schema/numerical-data audit, not measured model validation. Required qualification includes apparatus geometry, enclosure/vent boundaries, sensor locations and calibration/response, pressure reference, the GEN3i column discrepancy, and evidence-bearing recorder/event alignment. Source experiment labels do not establish independent trials or a well-mixed room concentration. No measured validation target is claimed.
