# Acoustic observation comparison

Source: Latcham, Bernardini, Richter and Trusler (2026), [dataset v1.0.0](https://doi.org/10.5281/zenodo.21355851), CC BY 4.0.

Original numeric parser; the separately supplied program is not used. Errors are 100 × (HEOS − observation)/observation. Composition-unspecified records and missing pressures are excluded. No saturation pressure is reconstructed. Source uncertainties are retained in the acquired records but are not treated as standard deviations.

This is an external consistency comparison. Overlap between historical observations and EOS development data is unresolved; it is not a blind validation or a new qualification of every state in the EOS domain.

| File | Composition | Rows | Compared | Excluded | Mean signed % | Mean abs % | Max abs % |
|---|---|---:|---:|---:|---:|---:|---:|
| H2_speedofsound_Carey_1974_nH2 | normal-H2 | 18 | 18 | 0 | 0.33216 | 0.419936 | 1.65935 |
| H2_speedofsound_Galt_1948_uH2 | unspecified-H2 | 1 | 0 | 1 | — | — | — |
| H2_speedofsound_Giacobbe_1993_nH2 | normal-H2 | 3 | 3 | 0 | -0.146738 | 0.162902 | 0.279057 |
| H2_speedofsound_Guesewell_1970_nH2 | normal-H2 | 7 | 0 | 7 | — | — | — |
| H2_speedofsound_Hodge_1937_nH2 | normal-H2 | 11 | 11 | 0 | 5.21251 | 5.21251 | 5.40457 |
| H2_speedofsound_Nguyen_2024_nH2 | normal-H2 | 57 | 57 | 0 | 0.129768 | 0.129768 | 0.444312 |
| H2_speedofsound_Pitt_1935_uH2_1 | unspecified-H2 | 2 | 0 | 2 | — | — | — |
| H2_speedofsound_Pitt_1935_uH2_2 | unspecified-H2 | 1 | 0 | 1 | — | — | — |
| H2_speedofsound_Roy_1935_nH2 | normal-H2 | 10 | 10 | 0 | 0.509121 | 0.509121 | 0.610208 |
| H2_speedofsound_Stewart_1946_uH2 | unspecified-H2 | 8 | 0 | 8 | — | — | — |
| H2_speedofsound_Tucker_1943_nH2 | normal-H2 | 1 | 0 | 1 | — | — | — |
| H2_speedofsound_VanDael_1965_nH2_1 | normal-H2 | 37 | 0 | 37 | — | — | — |
| H2_speedofsound_VanDael_1965_nH2_2 | normal-H2 | 175 | 175 | 0 | -0.464232 | 0.678605 | 65.6881 |
| H2_speedofsound_VanDael_1965_pH2 | para-H2 | 24 | 0 | 24 | — | — | — |
| H2_speedofsound_VanItterbeek_1961_nH2 | normal-H2 | 43 | 0 | 43 | — | — | — |
| H2_speedofsound_VanItterbeek_1961_pH2 | para-H2 | 49 | 0 | 49 | — | — | — |
| H2_speedofsound_VanItterbeek_1963_nH2 | normal-H2 | 111 | 111 | 0 | -0.139435 | 0.160987 | 0.306914 |
| H2_speedofsound_VanItterbeek_1963_pH2 | para-H2 | 125 | 125 | 0 | -0.682642 | 0.682642 | 1.33061 |
| H2_speedofsound_VanItterbeek_Mariens_1937A_nH2 | normal-H2 | 6 | 6 | 0 | 7.89527 | 7.89527 | 12.1547 |
| H2_speedofsound_VanItterbeek_Mariens_1937B_45pH2 | 45% para-H2 | 1 | 0 | 1 | — | — | — |
| H2_speedofsound_VanItterbeek_Mariens_1937B_nH2 | normal-H2 | 4 | 4 | 0 | 2.87586 | 5.08541 | 15.9225 |
| H2_speedofsound_VanItterbeek_Mariens_1940_uH2 | unspecified-H2 | 13 | 0 | 13 | — | — | — |
| H2_speedofsound_VanItterbeek_Thys_1938_nH2 | normal-H2 | 4 | 4 | 0 | 3.54143 | 3.59194 | 13.9858 |
| H2_speedofsound_VanItterbeek_Thys_1938_pH2 | para-H2 | 3 | 3 | 0 | -1.93307 | 1.93307 | 3.45931 |
| H2_speedofsound_VanItterbeek_VanPaemel_1938_nH2 | normal-H2 | 5 | 5 | 0 | -0.240467 | 0.240467 | 0.35169 |
| H2_speedofsound_VanItterbeek_Verhaegen_1949_uH2 | unspecified-H2 | 11 | 0 | 11 | — | — | — |
| H2_speedofsound_VanItterbeek_Vermaelen_1942_uH2 | unspecified-H2 | 24 | 0 | 24 | — | — | — |
| H2_speedofsound_Younglove_1965_nH2 | normal-H2 | 21 | 0 | 21 | — | — | — |
| H2_speedofsound_Younglove_1965_pH2_1 | para-H2 | 23 | 0 | 23 | — | — | — |
| H2_speedofsound_Younglove_1965_pH2_2 | para-H2 | 229 | 229 | 0 | -0.142926 | 0.163755 | 1.70241 |

## Reproduction and exclusions

CoolProp 8.0.0; HEOS; 30 data files, 1027 observations, 761 compared observations.

- missing observed T, p or sound speed: 205
- unsupported or unspecified spin composition: 61

Aggregate mean absolute relative deviation: 0.56033 %. The aggregate weights observations, not experiments; heterogeneous historical precision and repeated sources prevent a universal accuracy claim.
