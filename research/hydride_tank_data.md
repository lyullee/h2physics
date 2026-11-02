# AB2 complete-channel qualification

Ramadhan, Suwarno and Hijriawan, [version 1](https://doi.org/10.17632/8km9z62tct.1), CC BY 4.0. Three acquired workbooks are checked against their acquisition receipts. No external observations or literal source formulas are reproduced here.

All source rows survive, including rows with missing or reversed datetimes. A local elapsed clock is reconstructed only from each sheet's first datetime. Raw Date/Time/counter/flow/pressure/temperature/volume fields remain accessible. Formula caches are never executed. Flow is reference volume, not mass; the MFC reference P/T and pressure unit/basis remain unqualified. Shell temperatures are not bed temperatures. Derived totals do not independently validate sorption.

| Workbook / sheet | All source rows | Missing datetime | Nonincreasing datetime edges | Missing/nonphysical shell cells | Negative flow cells | Negative pressure cells | Max cached-vs-reconstructed time difference s |
|---|---:|---:|---:|---:|---:|---:|---:|
| 10 SLPM.xlsx / Vacuum 4th | 1020 | 0 | 0 | 73 | 0 | 0 | 4.57279384e-07 |
| 10 SLPM.xlsx / 4 Absorb 10 SLPM | 55784 | 0 | 0 | 6394 | 0 | 0 | 6.23054802e-07 |
| 10 SLPM.xlsx / 4 desorb 5 SLPM | 40765 | 4 | 0 | 59268 | 0 | 0 | 3.40864062e-07 |
| 5 SLPM.xlsx / Absorb 5 SLPM | 56740 | 1 | 0 | 52 | 0 | 0 | 4.51691449e-07 |
| 5 SLPM.xlsx / Desorb 5 SLPM | 56239 | 22 | 0 | 383 | 0 | 0 | 4.45172191e-07 |
| 15 SLPM.xlsx / Absorb 15 SLPM | 86112 | 4 | 0 | 27 | 0 | 0 | 4.22820449e-07 |
| 15 SLPM.xlsx / Desorb 5 SLPM | 68742 | 9983 | 0 | 51406 | 0 | 0 | 4.79631126e-07 |

## Summary selection audit

- 10 SLPM.xlsx / 4 Absorb 10 SLPM: summary selects source row 55785; last datetime row 55785; selected/final cached reference volume np.float64(1.1060292296982464)/1.1060292296982464 m3_ref. Four derived summary caches available: 4/4.
- 10 SLPM.xlsx / 4 desorb 5 SLPM: summary selects source row 16311; last datetime row 40762; selected/final cached reference volume np.float64(0.7286487249962752)/0.7286647683283161 m3_ref. Four derived summary caches available: 4/4.
- 5 SLPM.xlsx / Absorb 5 SLPM: summary selects source row 56740; last datetime row 56740; selected/final cached reference volume np.float64(0.931190888415756)/0.931190888415756 m3_ref. Four derived summary caches available: 4/4.
- 5 SLPM.xlsx / Desorb 5 SLPM: summary selects source row 56218; last datetime row 56218; selected/final cached reference volume np.float64(0.7783022350397378)/0.7783022350397378 m3_ref. Four derived summary caches available: 4/4.
- 15 SLPM.xlsx / Absorb 15 SLPM: summary selects source row 86109; last datetime row 86109; selected/final cached reference volume np.float64(1.089401419977002)/1.089401419977002 m3_ref. Four derived summary caches available: 4/4.
- 15 SLPM.xlsx / Desorb 5 SLPM: summary selects source row 58760; last datetime row 58760; selected/final cached reference volume np.float64(0.7848381166725585)/0.7848381166725585 m3_ref. Four derived summary caches available: 4/4.

The summary formula's ideal-gas calculation uses 293.15 K and 101.31 kPa. This documents the author's calculation convention; it does not establish the MFC calibration reference state, the pressure-channel unit, free gas volume, bed temperature or independent absorbed mass. A desorption sheet also retains an absorption-labelled summary; run direction is therefore not inferred from that label. No fitted material parameters or experimental model acceptance is claimed.

Full scan: 7 sheets, 365402 source rows; all three file receipts matched.

## Executed source fingerprints

- `src/h2physics/data/hydride_tank.py`: `b290ec9f540873f4bb7ca07188634cde1a592da6b39061eca8b8d3c8a1b9b36a`
- `scripts/check_hydride_tank_data.py`: `305cc9c9aa4c39a022974591d2fb4c6a021d67e604f807b695cc8fa1f3def0c0`
