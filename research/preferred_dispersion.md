# Preferred native dispersion-provider checks

The user selects HyRAM+ for high-pressure gaseous-H2 dispersion and SLABx-LH2 for LH2-origin dispersion. These actual native checks are authored numerical/software cases, not new independent experimental validation. Existing DEGALI comparison records retain their results and limits.

Native versions: {'hyram': '6.1', 'slabx': '1.0.8', 'slabx-lh2': '0.2.0'}; SciPy 1.16.3; NumPy 2.5.4.

HyRAM+ 6.1 is separately installed under GPL-3.0-only. The default SciPy 1.18.1 run raised a dopri5 solout callback TypeError; the compatible target uses SciPy 1.16.3 without changing native equations or patching global callbacks. SLABx 1.0.8 and SLABx-LH2 0.2.0 are separately installed MIT source revisions, not assumed equal to the PyPI LH2 0.1.5 release. Native code/mechanisms/data are not bundled by this host.

## High-pressure gas case

Authored normal H2 at 2 MPa/300 K, 2 mm opening, native Cd 0.8, calm air at 101325 Pa/293.15 K, horizontal source 2 m above the declared datum. HyRAM owns its orifice, notional expansion, establishment and jet. An already solved shared nozzle is not passed through another choking stage. Requested arclength is 2 m; actual native integration extent is retained, including its endpoint overshoot.

Native flow 0.00309566981064 kg/s, maximum Gaussian-section H2 flux residual 0.000721705074549 kg/s, budget 3.19566981064e-07 kg/s; material/finite-output gate FAIL. Actual final S=2.0230163423 m; 71 centreline samples. This gate does not independently audit native constant-Cp energy or field accuracy.

Gaussian-entry H2 transport is 0.00237396473609 kg/s (0.766866262006 of upstream native flow). Maximum downstream drift from that entry is 1.62978659214e-10 kg/s. The initialization jump is therefore distinct from ODE transport drift. The native expanded plug preserves the upstream mass in this case; host audit rejects the plug-to-Gaussian mismatch without changing lambda or fitting a scalar correction.

## Gaussian-entry mass-gap source audit — 2026-10-29

A read-only review of the official HyRAM public `master` sources points to `PlugNode.establish()` in `_jet.py` as a plausible location for the expanded-plug to Gaussian-entry change. The reviewed path derives Gaussian width and centerline state from the plug and ambient fields; it does not visibly solve a separate constraint for integrated H2 mass, axial momentum, or total energy at that conversion. The public nozzle path in `_comps.py` computes flow from density, velocity, orifice area and discharge coefficient. The radial profile definitions in `_govEqns` are consistent with the host's integrated `rho*Y*V` flux expression.

This is a hypothesis based on the current public `master` branch, not a confirmed explanation for the separately installed HyRAM 6.1 package: its exact source revision has not been pinned or compared. No host correction is made. Keep the current mass-gap rejection. A future alternate initialization must declare its thermodynamic and profile assumptions and independently close H2 mass, axial momentum (including pressure thrust where applicable), and total energy. Preserve the original native result as a separate versioned identity; do not fit lambda or apply a downstream scalar multiplier. Primary source references: https://raw.githubusercontent.com/sandialabs/hyram/master/src/hyram/phys/_jet.py and https://raw.githubusercontent.com/sandialabs/hyram/master/src/hyram/phys/_comps.py.

## LH2-origin resolved vapor case

Authored atmospheric saturated normal-H2 vapor, fixed horizontal area 1 m2, upward mass flux 0.001 kg/s over absolute source-clock [10,30] s; total 0.02 kg, ending by declared isolation. The native duration is 20 s and its relative time must not be confused with that absolute clock. No nozzle-to-ground fraction or real pool radius is inferred. Native CoolProp emission and water/ice providers and explicitly enabled width coupling are retained. A steady source cannot silently consume variable bins.

| Wind m/s at 10 m | Native max w_c/u | Premise violated | Area change m2 | Source mass residual kg | Host gate |
|---:|---:|---|---:|---:|---|
| 5 | 0.00186516073017 | False | 0 | 0 | PASS |
| 0.2 | 3.66921357404 | True | 0 | 0 | FAIL |

A violated/nonfinite post-run premise or changed fixed-source area is rejected by default, with the raw native result retained. It does not route to DEGALI. Source mass agreement is separate from native plume/puff energy, finite-source travel, physical footprint and experimental concentration qualification.

Local native call times: HyRAM 0.146323 s; SLAB high/low wind 1.70117/3.08257 s. These are observed calls during concurrent local development, excluding imports; they are not a comparative benchmark.

## Fingerprints

| Component | SHA-256 |
|---|---|
| installed hyram Python paths/bytes | `d5865e1ae7b5c77b985e06b45d7a5607543703c1834fc50f7c5d96f32a0c22de` |
| installed slabx Python paths/bytes | `3f8d37baf91ac46eceec11a0219d1fe0e4c41029be356ada90aba995215c6fe5` |
| installed slabx_lh2 Python paths/bytes | `374bc73a9b5c0605ad846db397369e2493d9b5d5cc416a21b5e619785ec0da67` |
| src/h2physics/dispersion.py | `794bbd170172ca3dfd5863e4c24cda96d8bb8d9139b664ef356b187d057b7950` |
| src/h2physics/adapters/hyram.py | `2ecadcd46cd54b0ed9c77ffeae655a2f0869c199a213d4f92972d09fa94d803b` |
| src/h2physics/adapters/slabx_lh2.py | `063feb3fdeee0355e3f8a99d094364e3c5adf071456d222af66caa7263b794d4` |
| scripts/check_preferred_dispersion.py | `9df0b5ed1e72041c2fa5475409f6adaa31dad1d30a1a4e2e0721d47c697192d1` |
