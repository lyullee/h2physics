# Measured PEM electrolysis protocol and impedance ingestion

Source: Brundiers (2026), [dataset v1](https://doi.org/10.5281/zenodo.19361280), CC BY 4.0. Associated study: [Brundiers et al.](https://doi.org/10.1039/d6ey00106h).
Recorded archive SHA-256: `ef15233374ece3af33a3f876a80d8a7c38c965dff122b884c6ebd39f391952e4`.

The first two POL_GEIS protocol counters are selected in each of four actual cells. Every CSV member is nevertheless fully consumed and hashed. These source groups contain DC holds and measured EIS sweeps; protocol counters and AC samples are not independent cell replicates. Selected arrays remain in ignored local caches.

Conversions are explicit: mA to A, degrees Celsius to K, bar absolute to Pa, micro-S/cm to S/m, and volume percent to fraction. Original source-row identities and file-specific reported elapsed clocks are retained; no sorting or clock alignment is inferred. The phase is used as arg(Z), consistent with the source's complex reconstruction example; plotting -Im(Z) does not change that convention.

The actual CSVs encode some DC EIS placeholders as 0 Hz/0 ohm, despite documentation describing missing values. Positive-frequency blocks are identified explicitly; zero-frequency entries are retained but excluded from spectra. A frequency reset ratio of two separates adjacent ascending sweeps. A preceding 10-row non-EIS tail, with explicit maximum 120 s gap, supplies reconstructed DC context. Longer gaps leave DC context unknown. Instantaneous AC current is not rounded to a setpoint. Cell block temperature is not reaction temperature. Corrected GC is only admitted in the documented H2_char/CstC phases; no GC values are interpolated or converted to membrane flux.

| Cell | Full CSV rows | Selected rows | Valid positive-frequency rows | Spectra | Spectra with DC context | Nonpositive selected frequency rows | Malformed selected numeric cells | CSV SHA-256 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Reference | 5904798 | 1946 | 828 | 36 | 28 | 1118 | 0 | `2705065f269d2c9bee6c50edaa6e3b0d5a03afa583b92d22d4cd764a15dfa6c6` |
| PtNano | 5948728 | 1945 | 828 | 36 | 36 | 1117 | 0 | `54d51fce96227c3973ceff9a11c7c515e95be83410352b04f28fb38c26c7e632` |
| PtBlack | 6003898 | 1945 | 828 | 36 | 34 | 1117 | 0 | `07036514f423c93629c69de67fe3d65d42a3a6896b1d8929d147cbe992dd2b2b` |
| PtC | 5906897 | 9135 | 828 | 36 | 18 | 8307 | 0 | `deb8b5dbcee418da3e75db618019c4dfe3aa8bc66c99672d1b3c18c2b22904b2` |

The inspected protocols contain 18 sweeps per counter; the nominal protocol describes 17 current levels ending at 12 A. The last counter-1 sweep is approximately 12 A again in Reference/PtC and 14 A in PtNano/PtBlack where DC context is admissible. Actual sweeps are kept, without forcing the nominal level count. The profile does not impute missing DC context across a longer acquisition gap.

No associated notebook was executed and no source plot or prose is redistributed. No equivalent-circuit fit, thermochemical reference, material property, crossover mechanism or independent model validation follows from this ingestion alone.

Host code SHA-256:

- `src/h2physics/data/pem.py`: `527481f9140b83e60543dca3662cd134fea05f834aa443d44e42c2f15709d857`
- `src/h2physics/impedance.py`: `ae9306dd70ce5153928d81c6c7e1e096bdd6b3a31a09fff1b11298eb084d23df`
- `scripts/check_pem_ingestion.py`: `7e649684a73d21f8fe7ee8ea7fdc9dc0fd221fd2ec6e3f73e98c580fbdcb84fa`
