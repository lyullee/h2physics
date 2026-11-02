# USN carpark thermal source qualification

Agnieszka Lach and Andre Vagner Gaathaug, [Experimental data—hydrogen safety, thermal effects, version 1](https://doi.org/10.23642/usn.17695082.v1), CC BY 4.0. This record contains original aggregate audit results and source hashes, without reproducing source prose, figures, coordinates, tables, programs or measured traces.

The complete local native-HDF5 scan finished in 42.42s with 2 bounded workers and 0 resumed segments. All 10 acquired attachment SHA-256/publisher checksums and the pinned metadata matched. The original supporting metadata was retained and verified. DOCX metadata was inspected as ZIP/XML without executing source content.

- Acquired attachment bytes: 693385633.
- Actual MAT files: 8; numeric source vectors: 245.
- Source scalar elements (including each clock exactly once): 157964002.
- Nonfinite source cells: 0.
- Nonphysical absolute-temperature cells retained/masked: 151.
- Default export/vector profiles: 56; clock-bearing: 47; unclocked: 9.
- Profile observation rows (includes independent clock-only vectors): 43779121.
- Unclocked signal rows retained: 7774576.
- Negative radiative/combined-flux/mass-flow/reported-pressure source samples retained: 4383178/9138005/13276/714505.
- Nonincreasing source clock edges retained: 0.
- Source-reported clock unit: `source_time_unit_unresolved`. No sample rate in Hz, physical duration in seconds or inter-recorder synchronization is inferred.

These are storage/vector coverage counts, not independent measurement, fitting or validation counts. All default source vectors passed exact once-only scalar coverage. No source normalization, baseline subtraction, negative clipping, sensor inversion, calibration fit, noise sigma or per-case combustion/source condition was invented.

| MAT file | Source vectors | Source scalar elements | Profile rows | Unclocked rows | Nonphysical T cells | TS exported |
|---|---:|---:|---:|---:|---:|---|
| Exp_00001.mat | 32 | 19514981 | 4064996 | 10000 | 0 | True |
| Exp_00002.mat | 32 | 11324981 | 4039995 | 1999999 | 1 | True |
| Exp_00003.mat | 21 | 20999981 | 5999996 | 1000000 | 0 | False |
| Exp_00004.mat | 32 | 21274981 | 6024996 | 1000000 | 0 | True |
| Exp_00005.mat | 32 | 20859135 | 5559150 | 764577 | 0 | True |
| Exp_00006.mat | 32 | 21329981 | 6029996 | 1000000 | 91 | True |
| Exp_00007.mat | 32 | 21329981 | 6029996 | 1000000 | 56 | True |
| Exp_00008.mat | 32 | 21329981 | 6029996 | 1000000 | 3 | True |

## Scientific boundaries

RHF radiation, THF combined-flux export, plate temperature, Coriolis mass flow, reported pressure, instrument/bolt temperatures, point thermocouples and ventilation outputs retain different variables, units, origins and observation roles. THF processing/plate inversion is unresolved; it is not an independently qualified total-flux measurement. Source bar is not promoted to absolute pressure. Meter and bolt readings are not bulk gas temperatures. The location table is local runtime metadata in source y,x,z order and millimetres, with drawing frame and the incomplete ventilation location preserved.

RHF3 has no default paired clock. Its source vector and timech7 remain separate; matching lengths create candidate metadata only. A caller may explicitly declare an evidence-bearing association with reconstructed origin and unresolved physical time unit. Experiment 2's Vent/T and Vent/time lengths differ; every temperature survives unclocked without borrowing another group's clock or truncation. Experiment 3 does not export TS. All original vector orientations, source indices, signed fields, zeros, invalid masks and independent source clocks survive. No automatic TimeSeries conversion is available.

The acquired metadata describes ignited releases, but does not assign all required source conditions to each exported experiment. This ingestion does not qualify a flame/radiation model, sensor response, steel/gas thermal inversion, exposure dose or CFD validation. Rights permission does not change `validation_qualified = false`.

## Attachment identities

Pinned metadata SHA-256: `00c1ca9a00ed214c1e2387373c69aea8b997f63aa27a8a8aa9e6c7e7a7977b42`; receipt SHA-256: `705caf63d8a4bfb8e75f507f50425167e7b3b935647d15773b6e2d52dc6e3e69`.

| Attachment | Bytes | SHA-256 |
|---|---:|---|
| Readme_Experimental data-Hydrogen safety, thermal effects.docx | 15018 | `b1df7359aeb100408c9d7b2b3a37fcd1fc942f394caf6db983aa7b32480277d6` |
| data description.docx | 102844 | `39f1cf8519babccaa9f9b4edb7ffc0380853a9280bcf1a3315af07f30487770b` |
| Exp_00002.mat | 57386217 | `71edba106de628e04005304ba20536c61228f4d73b57938b56bdc09f8358ec8c` |
| Exp_00005.mat | 83233774 | `a6b87028127b1cae7d2ea0297f62d6e0183ee93c1834885bed253b82f88e3df3` |
| Exp_00001.mat | 87145920 | `535b0af2beabb1c25b726f55a2d0faeb77ac990c733fc1312bc604c1d4e6bf75` |
| Exp_00003.mat | 91100499 | `1435e5426e5f0439bd7936cf24b9da0fa2af857cb2961849890dcd47e2d2f8ba` |
| Exp_00007.mat | 92771285 | `9fecf52f40a5c90d15d2686944896587953cd31de7547267a2eed900dd2eec8a` |
| Exp_00004.mat | 93199247 | `a6d1394979677e736677b2250b7d7b2c56fb6ee2b0cc0e2de87e2c9a32cbcfaa` |
| Exp_00006.mat | 93423140 | `d98beedf7fbff9d0859b751b2e112428090a60144e4bdf62a35653b469f8782d` |
| Exp_00008.mat | 95007689 | `7f66421f5f0f01cd9fc907dc61c522db67ba84496fa01e4edde71cff48ae000b` |

## Executed source fingerprints

Begin and end fingerprints matched; sources used LF.

- `src/h2physics/data/thermal_effects.py`: `f353bf2270e4df7b96a15f44bb778ac876066566b5e3b69b219fd51eb7317f45`
- `tests/test_thermal_effects_data.py`: `d4aaef0ebbbb5d9d42e633ff37cefc8da4be7de387c93ffbd29c15c6e93887a7`
- `scripts/check_thermal_effects_data.py`: `4ace6c43051f5224fa86f77ee0185fa310a4d5a2b78313a59c4e238199875ecc`
- `src/h2physics/data/pressure_peaking.py`: `44235ac1ffa7e447ebc58a42eba5368e8008af517f48bd3605fa41140507fa15`
- `src/h2physics/observations.py`: `e0a6f1e26b5b6ca20fb31b8f7f19d5f86c6dbaffadfd37e2adc22de8bf6d1ba0`
- `src/h2physics/units.py`: `af252872dc63e784879d31408008151531e1992f7fe6acacde1c7bd5cc70bc0c`

Runtime: h5py 3.16.0, HDF5 2.0.0, NumPy 2.5.4.

Complete private schemas, units/roles, per-vector canonical value hashes, counts/extrema, masks/issues, source row identities, runtime location rows and durable checkpoints remain in ignored `data/processed/carpark-thermal/1/audit.json`. Raw and normalized external observations remain excluded from Git and distributions.
