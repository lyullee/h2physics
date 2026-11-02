# Measured PEM whole-spectrum parameter estimation

Data: Steffen Brundiers (2026), [version v1](https://doi.org/10.5281/zenodo.19361280), CC BY 4.0. Archive/member hashes and canonical channels: [ingestion audit](pem_ingestion.md). These are measured cell responses; complex Z is reconstructed from reported magnitude/phase.

The optional MIT [impedance.py](https://doi.org/10.21105/joss.02349) dependency owns the selected circuit, parser and elements. The actual installed CustomCircuit is injected into NativeCircuitOperator; the existing SciPy least-squares/SVD and whole-group comparison API owns estimation/diagnostics. No native circuit solver or fitting implementation is copied or replaced.

- Native release: `1.7.1`; all installed package .py files, sorted relative path plus bytes SHA-256: `2839220bf79199bfaf8548cb0d71ac09786fd85d7686af4af9fbec771f8f6fb6`.
- Analytic alpha=1 series-L/R + parallel-RC limit: maximum error 3.46944695e-18 ohm.
- Circuit: `L0-R0-p(R1,CPE1)`; native names/units: (('L0', 'H'), ('R0', 'Ohm'), ('R1', 'Ohm'), ('CPE1_0', 'Ohm^-1 sec^a'), ('CPE1_1', '')).

Selection is fixed before fitting: the first complete spectrum with reconstructed DC current in [11.8,12.2] A in POL_GEIS counter 1 of each cell. The other complete 12 A spectra in counters 1/2 are held out in their entirety. Missing DC context is not guessed from AC current. Frequencies are used as acquired, without dropping unfavorable points or extending the approximately 100–10000 Hz measured band. Adjacent DC context is limited to the same source protocol with a maximum 120 s gap.

The five bounded effective parameters use the same fixed starting values in all cells. Residual normalization 0.01 ohm is only numerical scaling. Real/imaginary parts are correlated projections of each complex reading; 46 Cartesian rows are 23 complex observations, not 46 independent experiments. No uncertainty or confidence interval is manufactured from residuals.

The predeclared illustrative complex-RMSE target is max(0.001 ohm, 0.02 mean|Z|) on each assessed whole sweep. PASS/FAIL is a diagnostic comparison only. Repeat protocols are the same cell/bench, and the four cells come from one source. None establishes independent-source or facility qualification.

| Parameter | Start | Lower | Upper | Numerical scale |
|---|---:|---:|---:|---:|
| L0 | 1e-06 | 0 | 0.0001 | 1e-06 |
| R0 | 0.05 | 1e-05 | 10 | 0.05 |
| R1 | 0.05 | 1e-06 | 10 | 0.05 |
| CPE1_0 | 0.1 | 1e-07 | 10000 | 0.1 |
| CPE1_1 | 0.9 | 0.1 | 1 | 1 |

## Reference

Fitted sweep: `pem/Reference/POL_GEIS/1/sweep-17`; DC 12.00182 A, 2.048326 V; block 353.4 K; cathode 3003350 Pa absolute. Block temperature is not a known reaction temperature.

- Cartesian input fingerprint: `2f5f6ae5331c1a93e54fcc98ac7f6f5c2de755af3c7b7433e1a365f0000a339d`.
- Complex fitting RMSE / max error: 0.00061399698 / 0.00255880145 ohm.
- Scaled Jacobian rank: 5/5; condition: 3209.26927; evaluations: 19.
- Scaled singular values: (24.46398038823219, 10.812757154366151, 3.901299483289016, 3.4705379282374538, 0.007622912972630181).
- Active bounds: (('L0', -1), ('R0', 0), ('R1', 0), ('CPE1_0', 0), ('CPE1_1', 0)).
- Effective R0×area: 1.4349669e-05 ohm m2; shared OhmicLoss at the selected DC current: 0.430555362 V. This includes unresolved contact/lead and cell contributions; it is not membrane resistivity or a qualified DC loss.

| Effective native parameter | Estimate |
|---|---:|
| L0 | 2.80503433777e-20 |
| R0 | 0.0358741725907 |
| R1 | 0.00769053395904 |
| CPE1_0 | 0.837330651221 |
| CPE1_1 | 0.764725230323 |

| Held-out whole sweep | Cartesian SHA-256 | Complex RMSE / max (ohm) | Target (ohm) | Result |
|---|---|---:|---:|---|
| `pem/Reference/POL_GEIS/1/sweep-18` | `4a23fe6f37b3fc09716b5a31bfe3ff263c1acbf1a317f2336a6e346dc8da6d3e` | 0.000432763113 / 0.00118257857 | 0.001 | PASS |
| `pem/Reference/POL_GEIS/2/sweep-17` | `c4b1372ae30fb476e3560242d3bb75c07ac9de472cd584900211067f0dfa6f03` | 0.001324248 / 0.00254846194 | 0.001 | FAIL |

## PtNano

Fitted sweep: `pem/PtNano/POL_GEIS/1/sweep-17`; DC 12.00211 A, 2.266487 V; block 353.9 K; cathode 3004740 Pa absolute. Block temperature is not a known reaction temperature.

- Cartesian input fingerprint: `fc84b435a6f99c9cc76558109132d6defa85435b594ff42ed2beb9e51ab4ec31`.
- Complex fitting RMSE / max error: 0.000141518093 / 0.000397276239 ohm.
- Scaled Jacobian rank: 5/5; condition: 69680.0846; evaluations: 74.
- Scaled singular values: (98.67815454065386, 10.90658660947353, 2.984955953029212, 0.08730105614551761, 0.0014161600855979012).
- Active bounds: (('L0', 0), ('R0', 0), ('R1', 0), ('CPE1_0', 0), ('CPE1_1', 0)).
- Effective R0×area: 9.9836788e-06 ohm m2; shared OhmicLoss at the selected DC current: 0.299563028 V. This includes unresolved contact/lead and cell contributions; it is not membrane resistivity or a qualified DC loss.

| Effective native parameter | Estimate |
|---|---:|
| L0 | 5.69590640436e-08 |
| R0 | 0.0249591970041 |
| R1 | 0.308906998719 |
| CPE1_0 | 5.36738561598 |
| CPE1_1 | 0.223221596269 |

| Held-out whole sweep | Cartesian SHA-256 | Complex RMSE / max (ohm) | Target (ohm) | Result |
|---|---|---:|---:|---|
| `pem/PtNano/POL_GEIS/2/sweep-17` | `f5bac992d720f1d22d05f4f1d1540851f3df666a7136251fba9fe5105682d8e2` | 0.00344797753 / 0.00468744403 | 0.001 | FAIL |
| `pem/PtNano/POL_GEIS/2/sweep-18` | `3ed78eff7e39c1e33f65f3789716ab165924aed510787d72a4ea54e0dd9b0c92` | 0.00423134453 / 0.00587296185 | 0.001 | FAIL |

## PtBlack

Fitted sweep: `pem/PtBlack/POL_GEIS/1/sweep-17`; DC 12.0031 A, 2.1645335 V; block 353.105 K; cathode 3011770 Pa absolute. Block temperature is not a known reaction temperature.

- Cartesian input fingerprint: `95169cbe40469574ca84aaf043b7ae626550199268f313cfe864cd9947c6d52b`.
- Complex fitting RMSE / max error: 0.000133465636 / 0.000546622201 ohm.
- Scaled Jacobian rank: 5/5; condition: 8047.08814; evaluations: 29.
- Scaled singular values: (36.23899510722145, 11.222651043445303, 4.9690905090377635, 1.4618437728012827, 0.00450336749045169).
- Active bounds: (('L0', 0), ('R0', 0), ('R1', 0), ('CPE1_0', 0), ('CPE1_1', 0)).
- Effective R0×area: 1.494707e-05 ohm m2; shared OhmicLoss at the selected DC current: 0.448527939 V. This includes unresolved contact/lead and cell contributions; it is not membrane resistivity or a qualified DC loss.

| Effective native parameter | Estimate |
|---|---:|
| L0 | 2.22876506586e-08 |
| R0 | 0.0373676749578 |
| R1 | 0.0394842317827 |
| CPE1_0 | 2.24405807005 |
| CPE1_1 | 0.440338157463 |

| Held-out whole sweep | Cartesian SHA-256 | Complex RMSE / max (ohm) | Target (ohm) | Result |
|---|---|---:|---:|---|
| `pem/PtBlack/POL_GEIS/2/sweep-17` | `4597525a5402daffe653712f443d685bbd8d0c62ff8dd929c8d4e18db183e24d` | 0.000315772364 / 0.000657595679 | 0.001 | PASS |
| `pem/PtBlack/POL_GEIS/2/sweep-18` | `902dddda63b45f260899261b574761a603967d8812256e7768308908ec5a9ea6` | 0.000306978082 / 0.000614942945 | 0.001 | PASS |

## PtC

Fitted sweep: `pem/PtC/POL_GEIS/1/sweep-17`; DC 12.000435 A, 2.101498 V; block 354.105 K; cathode 3016420 Pa absolute. Block temperature is not a known reaction temperature.

- Cartesian input fingerprint: `e649a09efba4e9a2660fb2f3b2bcad77bd4c75ed2626556327777eff3d37e1cb`.
- Complex fitting RMSE / max error: 7.8926865e-05 / 0.00022892912 ohm.
- Scaled Jacobian rank: 5/5; condition: 15774.847; evaluations: 26.
- Scaled singular values: (26.85476546884844, 11.038577600399169, 5.52828695645419, 0.6236143002500019, 0.0017023788241963367).
- Active bounds: (('L0', 0), ('R0', 0), ('R1', 0), ('CPE1_0', 0), ('CPE1_1', 0)).
- Effective R0×area: 1.54245049e-05 ohm m2; shared OhmicLoss at the selected DC current: 0.462751922 V. This includes unresolved contact/lead and cell contributions; it is not membrane resistivity or a qualified DC loss.

| Effective native parameter | Estimate |
|---|---:|
| L0 | 4.8048211821e-08 |
| R0 | 0.0385612623326 |
| R1 | 0.028310100224 |
| CPE1_0 | 3.60854914159 |
| CPE1_1 | 0.502224208807 |

| Held-out whole sweep | Cartesian SHA-256 | Complex RMSE / max (ohm) | Target (ohm) | Result |
|---|---|---:|---:|---|
| `pem/PtC/POL_GEIS/1/sweep-18` | `d9783ef6b691cb9dd6210b32642310097af3fb4873cc07b0a7ca7b67900154bb` | 0.000633453951 / 0.000893486539 | 0.001 | PASS |
| `pem/PtC/POL_GEIS/2/sweep-17` | `0fbee8b3345ba935bc212b17391459f571997f73be0771e013d2631ba5498f5a` | 0.00186321603 / 0.00407945623 | 0.001 | FAIL |

## Fixed Reference coefficients transferred to different cells

These predictions do not refit the target cells. Materials differ and all cells share a source; the exercise tests parameter portability, without claiming universal coefficients or independent-source validation.

| Target cell first eligible sweep | Complex RMSE / max (ohm) | Target (ohm) | Result |
|---|---:|---:|---|
| PtNano: `pem/PtNano/POL_GEIS/1/sweep-17` | 0.0146116317 / 0.0238278155 | 0.001 | FAIL |
| PtBlack: `pem/PtBlack/POL_GEIS/1/sweep-17` | 0.00868800845 / 0.0132607066 | 0.001 | FAIL |
| PtC: `pem/PtC/POL_GEIS/1/sweep-17` | 0.0045691848 / 0.00593469861 | 0.001 | FAIL |

The finite measured band cannot establish a unique charge-transfer, diffusion, membrane, catalyst or aging mechanism. CPE Q has alpha-dependent units and is not an ordinary capacitance unless alpha=1. An active bound or ill-conditioned Jacobian restricts parameter interpretation even when the curve fits. Linear/time-invariant behavior and Kramers–Kronig consistency have not been qualified by this replay. No crossover flux, degradation law, true reversible voltage or stack thermal inventory is inferred from this small-signal circuit.

Host code SHA-256:

- `src/h2physics/impedance.py`: `ae9306dd70ce5153928d81c6c7e1e096bdd6b3a31a09fff1b11298eb084d23df`
- `src/h2physics/data/pem.py`: `527481f9140b83e60543dca3662cd134fea05f834aa443d44e42c2f15709d857`
- `src/h2physics/adapters/impedance.py`: `29cacf895bf1671731af732befdb62aad27185ade22f5f94d28391ab0099c904`
- `scripts/fit_pem_impedance.py`: `ee637f6b5ff0a80cde152a2155ed1cb5ae9299e1061300d907cc5432c45d3156`
