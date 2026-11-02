# PRESLHY conditional inventory / nozzle consistency

Source: [Jordan, T. (2023), KIT dataset](https://doi.org/10.35097/1187), CC BY 4.0, archive-1. Bundle `PRE3P1A_KIT_D1_300K_DATA.zip` SHA-256: `ff00311e65e43964906906d8c2dcfa146964ff48caf44ea4763733b0237ab3f3`.

Four different initial-pressure experiments are used. No raw workbook, apparatus illustration or source explanatory text is redistributed. Source metadata/checksums are retained in `research/data/preslhy-discharge.toml`.

This is a conditional consistency comparison, not independent mass-flow validation. Inventory is reconstructed from measured pressure and the mean of three closed vessel thermocouples using CoolProp; the nozzle uses those same P/T inputs and EOS. Temperature is observed forcing here, not a prediction from the tank energy equation. Force/balance signals are ingested but excluded from quantitative acceptance because the source identifies limited accuracy. No statistical uncertainty is inferred from the many correlated samples or from optimizer rank.

Declared assumptions: rigid volume 0.002815 m³; source pressure interpreted as gauge with an assumed ambient reference 101325 Pa; frozen normal hydrogen in CoolProp 8.0.0 HEOS; no spin conversion. A barometric record and source spin fraction are not available. The source includes finite valve/pipework; its losses are folded into an effective-area factor only for this comparison. A measured line temperature or nozzle-solid temperature is not silently substituted for reservoir stagnation temperature.

The author's synchronized PNoz-onset clocks are retained, with original recorder elapsed-time channels. No new time shift is estimated. Comparison centers span 2–10 s to avoid initial valve travel. Explicit arithmetic bins use 0.2, 0.1 and 0.05 s widths; both endpoints remain fixed. Counts describe sensor samples, not independent repeats. No missing/extrapolated bin is accepted. A three-sensor mean is a declared homogeneous-temperature observation operator, not a spatially resolved state.

| Experiment | Workbook SHA-256 | Initial absolute P Pa | Fast-pressure rows | Temperature rows |
|---|---|---:|---:|---:|
| 20190523_144939 | `b586419b4cd35eb3b8974954348e8e8cb0da81dd526bb6423cf40e4009af546d` | 20184484.5517 | 176000 | 8000 |
| 20190523_150133 | `4d8b32a2585faeb3e2229d75a4344d9c2bdb3cb1ea5252ad61b6b3520b190ed0` | 1118956.47639 | 182000 | 8300 |
| 20190523_151013 | `c1a7dc9f3d2891cc3fe4f6156fbee43394d2f43eac3c4012fbea7451e023527e` | 2160300.74408 | 128000 | 5700 |
| 20190523_151618 | `61eaaa1b7d46eee578a1a64e600a4094e7cdb6cf69a1790b5025de8ee189bc08` | 626411.34011 | 108000 | 4400 |

| Experiment | Bin s | Initial-window inventory kg | Inferred loss kg | Nominal-nozzle loss kg | Endpoint effective factor | Max closed-TC spread K | Min P samples/bin | Min T samples/bin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 20190523_144939 | 0.2 | 0.0290871262965 | 0.0188003356091 | 0.0292517575071 | 0.642707898989 | 27.724404 | 399 | 20 |
| 20190523_144939 | 0.1 | 0.0290848058738 | 0.0187984123305 | 0.0292481560271 | 0.642721281748 | 27.7452682 | 199 | 10 |
| 20190523_144939 | 0.05 | 0.0290730122102 | 0.0187868469991 | 0.0292454776117 | 0.642384687591 | 28.3256432 | 99 | 5 |
| 20190523_150133 | 0.2 | 0.0157455596927 | 0.0101147014562 | 0.0158552161684 | 0.63794156754 | 24.10941205 | 399 | 20 |
| 20190523_150133 | 0.1 | 0.0157456010904 | 0.0101162741019 | 0.0158534676172 | 0.638111127876 | 24.1612042 | 199 | 10 |
| 20190523_150133 | 0.05 | 0.0157438220078 | 0.0101122160686 | 0.0158523557426 | 0.637899895306 | 24.2555336 | 99 | 5 |
| 20190523_151013 | 0.2 | 0.00353550318733 | 0.00224150912119 | 0.00363713524779 | 0.616284237037 | 24.91604705 | 400 | 20 |
| 20190523_151013 | 0.1 | 0.00353390801819 | 0.0022395480798 | 0.00363683432538 | 0.615796013629 | 24.933615 | 199 | 10 |
| 20190523_151013 | 0.05 | 0.00353238592518 | 0.00224185851246 | 0.00363668801735 | 0.616456100102 | 24.9731634 | 99 | 5 |
| 20190523_151618 | 0.2 | 0.00105893085854 | 0.000638231261343 | 0.00113441069452 | 0.562610405936 | 20.8430182 | 399 | 20 |
| 20190523_151618 | 0.1 | 0.0010581800288 | 0.000637391995678 | 0.00113432021851 | 0.561915396796 | 20.8475501 | 199 | 10 |
| 20190523_151618 | 0.05 | 0.00105695593887 | 0.000634780942595 | 0.00113428551282 | 0.559630653323 | 20.9102318 | 99 | 5 |

The endpoint ratio is a diagnostic per experiment. The shared fit below uses full cumulative curves at 0.1 s resolution, with a declared [0.05, 1] bound. It is an effective apparatus factor, not an independently calibrated universal nozzle coefficient.

- Fitting groups: ('20190523_144939', '20190523_150133', '20190523_151618').
- Held-out group: 20190523_151013 (approximately 20 bar gauge initially).
- Fitted factor: 0.611074310718; active bounds (('effective_area_factor', 0),).
- Fitting RMSE: 0.0226498819126 of initial-window inventory.
- Held-out RMSE: 0.00361222122091 of initial-window inventory.
- Held-out max absolute error: 0.00703731797345 of initial-window inventory.
- Fitting/held-out rows: 243 / 81.
- Input fingerprints: `232378594cb244b2c3dc8e1b7739ed20dd9aaa829d41b18c1a2d0c7b4b29f73c` / `e803483a5fba966711acba7cedff50fb4ce4a86374017c27202d1eca785ae38b`.

No domain-qualification threshold is assigned to this exploratory result. An independent calibrated flow/inventory reference, pressure/temperature uncertainties, thermocouple response and spatial representativeness, verified ambient/spin basis and resolved valve/line hydraulics remain required before qualifying discharge physics.

Code SHA-256:

- `scripts/compare_discha_release.py`: `df9208ec7d402a9b5f83c561b34dcfc9e3e13c6343043a8a06898b7680887e2c`
- `src/h2physics/data/preslhy.py`: `585aa51e4f4d3dd3e139a886984fd15b791a06976b92c7b92be1636328b2dde2`
- `src/h2physics/data/sampling.py`: `b6adcf19befdaaca3d8d3cd91be690e81d94dbc3009cdd1968589b85ccd2c096`
- `src/h2physics/release.py`: `49a2d353c42d0d1fcc4144d4776267b33dd1f6baa149bb817d4bd2aa654c946b`
- `src/h2physics/core.py`: `1e40a44ef5d172d2a4255b2bdfbda4ea144f62a199927c315dd3f4155fecd048`
- `src/h2physics/thermo/coolprop.py`: `74bf3d7f49c5b3163c7a079c358a866d48d28280e25a2592ce53b3351e815d03`
