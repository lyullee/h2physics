# Hydrogen acoustic EOS replay

Source: https://doi.org/10.5281/zenodo.21355851 ; CC BY 4.0.
Attribution: Riley Latcham, Luca Bernardini, Markus Richter and Martin Trusler.
Archive SHA-256: `38a5c10a9fb06c41a32f4fbba4ac0d1dabb3b38a7e80490ebc587a2e6dcfd553`.
Metadata SHA-256: `1d83651ff168e7eae59c3688e25957392169034ebbdbd05c2cefe3c8b75ee3ad`.
CoolProp version: 8.0.0; backend HEOS.

Each source row is evaluated at its reported T and p with the declared spin basis.
These literature measurements may overlap EOS development. Independence and
experimental uncertainty remain unresolved; this is a replay diagnostic.
Errors below are descriptive and have no imposed accuracy pass threshold.

Phase mismatch rows are retained in the all-row residuals and flagged separately.

| Member | Compared | Excluded | Phase mismatches | RMS error (m/s) | Max absolute error (%) |
|---|---:|---:|---:|---:|---:|
| `H2_speedofsound_dataset/H2_speedofsound_Carey_1974_nH2.txt` | 18 | 0 | 0 | 8.69721756 | 1.6593545 |
| `H2_speedofsound_dataset/H2_speedofsound_Galt_1948_uH2.txt` | 0 | 1 | unavailable | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_Giacobbe_1993_nH2.txt` | 3 | 0 | 0 | 2.54220458 | 0.279056911 |
| `H2_speedofsound_dataset/H2_speedofsound_Guesewell_1970_nH2.txt` | 0 | 7 | 0 | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_Hodge_1937_nH2.txt` | 11 | 0 | 0 | 64.7363415 | 5.40457036 |
| `H2_speedofsound_dataset/H2_speedofsound_Nguyen_2024_nH2.txt` | 57 | 0 | 0 | 3.45030441 | 0.444311708 |
| `H2_speedofsound_dataset/H2_speedofsound_Pitt_1935_uH2_1.txt` | 0 | 2 | unavailable | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_Pitt_1935_uH2_2.txt` | 0 | 1 | unavailable | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_Roy_1935_nH2.txt` | 10 | 0 | 0 | 6.75922488 | 0.610207828 |
| `H2_speedofsound_dataset/H2_speedofsound_Stewart_1946_uH2.txt` | 0 | 8 | unavailable | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_Tucker_1943_nH2.txt` | 0 | 1 | 0 | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_VanDael_1965_nH2_1.txt` | 0 | 37 | 0 | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_VanDael_1965_nH2_2.txt` | 175 | 0 | 1 | 53.1030577 | 65.6881137 |
| `H2_speedofsound_dataset/H2_speedofsound_VanDael_1965_pH2.txt` | 0 | 24 | 0 | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_1961_nH2.txt` | 0 | 43 | 0 | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_1961_pH2.txt` | 0 | 49 | 0 | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_1963_nH2.txt` | 111 | 0 | 0 | 2.48722195 | 0.306913673 |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_1963_pH2.txt` | 125 | 0 | 0 | 9.99748194 | 1.33060577 |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Mariens_1937A_nH2.txt` | 6 | 0 | 0 | 66.1081991 | 12.1546947 |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Mariens_1937B_45pH2.txt` | 0 | 1 | unavailable | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Mariens_1937B_nH2.txt` | 4 | 0 | 0 | 90.4470156 | 15.9225493 |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Mariens_1940_uH2.txt` | 0 | 13 | unavailable | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Thys_1938_nH2.txt` | 4 | 0 | 0 | 86.5838009 | 13.9858428 |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Thys_1938_pH2.txt` | 3 | 0 | 0 | 19.8356117 | 3.45930745 |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_VanPaemel_1938_nH2.txt` | 5 | 0 | 0 | 0.915349983 | 0.351689539 |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Verhaegen_1949_uH2.txt` | 0 | 11 | unavailable | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Vermaelen_1942_uH2.txt` | 0 | 24 | unavailable | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_Younglove_1965_nH2.txt` | 0 | 21 | 0 | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_Younglove_1965_pH2_1.txt` | 0 | 23 | 0 | unavailable | unavailable |
| `H2_speedofsound_dataset/H2_speedofsound_Younglove_1965_pH2_2.txt` | 229 | 0 | 0 | 2.98663781 | 1.70241028 |

Total compared: 761; total excluded: 266.

Exclusion accounting:

- `H2_speedofsound_dataset/H2_speedofsound_Carey_1974_nH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_Carey_1974_nH2.txt:loop-1:row-11`; source phase `gas`, native EOS phase `supercritical`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_Galt_1948_uH2.txt`: unsupported/unknown declared spin `unspecified-h2`.
- `H2_speedofsound_dataset/H2_speedofsound_Giacobbe_1993_nH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_Giacobbe_1993_nH2.txt:loop-1:row-1`; source phase `gas`, native EOS phase `supercritical_gas`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_Guesewell_1970_nH2.txt`: 7 rows excluded: missing or non-finite T, p, or sound speed.
- `H2_speedofsound_dataset/H2_speedofsound_Hodge_1937_nH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_Hodge_1937_nH2.txt:loop-1:row-11`; source phase `gas`, native EOS phase `supercritical`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_Nguyen_2024_nH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_Nguyen_2024_nH2.txt:loop-2:row-9`; source phase `gas`, native EOS phase `supercritical`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_Pitt_1935_uH2_1.txt`: unsupported/unknown declared spin `unspecified-h2`.
- `H2_speedofsound_dataset/H2_speedofsound_Pitt_1935_uH2_2.txt`: unsupported/unknown declared spin `unspecified-h2`.
- `H2_speedofsound_dataset/H2_speedofsound_Roy_1935_nH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_Roy_1935_nH2.txt:loop-1:row-5`; source phase `gas`, native EOS phase `supercritical_gas`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_Stewart_1946_uH2.txt`: unsupported/unknown declared spin `unspecified-h2`.
- `H2_speedofsound_dataset/H2_speedofsound_Tucker_1943_nH2.txt`: 1 rows excluded: missing or non-finite T, p, or sound speed.
- `H2_speedofsound_dataset/H2_speedofsound_VanDael_1965_nH2_1.txt`: 37 rows excluded: missing or non-finite T, p, or sound speed.
- `H2_speedofsound_dataset/H2_speedofsound_VanDael_1965_nH2_2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_VanDael_1965_nH2_2.txt:loop-1:row-28`; source phase `liquid`, native EOS phase `gas`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_VanDael_1965_pH2.txt`: 24 rows excluded: missing or non-finite T, p, or sound speed.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_1961_nH2.txt`: 43 rows excluded: missing or non-finite T, p, or sound speed.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_1961_pH2.txt`: 49 rows excluded: missing or non-finite T, p, or sound speed.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_1963_nH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_1963_nH2.txt:loop-1:row-81`; source phase `liquid`, native EOS phase `supercritical_liquid`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_1963_pH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_1963_pH2.txt:loop-1:row-95`; source phase `liquid`, native EOS phase `supercritical_liquid`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Mariens_1937A_nH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Mariens_1937A_nH2.txt:loop-1:row-6`; source phase `gas`, native EOS phase `supercritical_gas`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Mariens_1937B_45pH2.txt`: unsupported/unknown declared spin `45% para-h2`.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Mariens_1937B_nH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Mariens_1937B_nH2.txt:loop-1:row-4`; source phase `gas`, native EOS phase `supercritical_gas`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Mariens_1940_uH2.txt`: unsupported/unknown declared spin `unspecified-h2`.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Thys_1938_nH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Thys_1938_nH2.txt:loop-1:row-1`; source phase `gas`, native EOS phase `supercritical_gas`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Thys_1938_pH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Thys_1938_pH2.txt:loop-1:row-2`; source phase `gas`, native EOS phase `supercritical_gas`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_VanPaemel_1938_nH2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_VanPaemel_1938_nH2.txt:loop-1:row-4`; source phase `gas`, native EOS phase `gas`. Source phase/metastability is not reconstructed.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Verhaegen_1949_uH2.txt`: unsupported/unknown declared spin `unspecified-h2`.
- `H2_speedofsound_dataset/H2_speedofsound_VanItterbeek_Vermaelen_1942_uH2.txt`: unsupported/unknown declared spin `unspecified-h2`.
- `H2_speedofsound_dataset/H2_speedofsound_Younglove_1965_nH2.txt`: 21 rows excluded: missing or non-finite T, p, or sound speed.
- `H2_speedofsound_dataset/H2_speedofsound_Younglove_1965_pH2_1.txt`: 23 rows excluded: missing or non-finite T, p, or sound speed.
- `H2_speedofsound_dataset/H2_speedofsound_Younglove_1965_pH2_2.txt`: largest-error row `10.5281/zenodo.21355851:H2_speedofsound_dataset/H2_speedofsound_Younglove_1965_pH2_2.txt:loop-1:row-87`; source phase `fluid`, native EOS phase `supercritical`. Source phase/metastability is not reconstructed.
