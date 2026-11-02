# AB2 shell-temperature ingestion

Source: Ramadhan, Suwarno and Hijriawan (2026), [dataset v1](https://doi.org/10.17632/8km9z62tct.1), CC BY 4.0.

Each worksheet has its own elapsed clock, reconstructed from recorded datetimes. The first datetime is the explicit local origin; no shared timezone or cross-run alignment is inferred. Five shell thermocouples are declared in degrees Celsius by the repository description and converted to kelvin. Cached derived mass, moles and volume summaries are not independent measurements. Pressure unit/basis and MFC reference conditions remain unresolved; those channels are excluded.

These are shell observations, not spatially uniform bed temperatures. Ingestion does not validate the reduced hydride model or identify its parameters.

| Workbook / worksheet | Temperature records | Duration s | Missing temperature cells | Min K | Max K | Clock status |
|---|---:|---:|---:|---:|---:|---|
| 10 SLPM.xlsx / Vacuum 4th | 1020 | 5987 | 73 | 275.15 | 308.85 | strictly increasing; 0 missing-time rows omitted |
| 10 SLPM.xlsx / 4 Absorb 10 SLPM | 55784 | 65610 | 6394 | 300.65 | 347.35 | strictly increasing; 0 missing-time rows omitted |
| 10 SLPM.xlsx / 4 desorb 5 SLPM | 40761 | 47909 | 59248 | 258.65 | 308.15 | strictly increasing; 4 missing-time rows omitted |
| 15 SLPM.xlsx / Absorb 15 SLPM | 86108 | 101179 | 7 | 294.95 | 348.65 | strictly increasing; 4 missing-time rows omitted |
| 15 SLPM.xlsx / Desorb 5 SLPM | 58759 | 69042 | 1491 | 256.15 | 302.95 | strictly increasing; 9983 missing-time rows omitted |
| 5 SLPM.xlsx / Absorb 5 SLPM | 56739 | 66668 | 48 | 296.65 | 343.35 | strictly increasing; 1 missing-time rows omitted |
| 5 SLPM.xlsx / Desorb 5 SLPM | 56217 | 66055 | 273 | 255.15 | 303.95 | strictly increasing; 22 missing-time rows omitted |

No sorting, interpolation, repeated-time averaging or pressure inference was performed.

Summary: {'sheets': 7, 'loaded': 7, 'records': 355388, 'failed': 0}.
