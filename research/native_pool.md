# Native dynamic pool and conservative mass-source verification

All process/surface inputs below are authored synthetic verification cases. No measured curve or third-party digitised observation is imported. The optional MIT [DynamicLH2PoolX](https://github.com/lyullee/DynamicLH2PoolX/tree/6a700e8e183039bbb81803bacc416f6c9117ed71) owns radial finite-volume spreading, local contact-age conduction, evaporation and time stepping. Native objects/results are retained; host code only supplies explicit boundaries and checks their ledgers.

- Version 0.2.0rc2; revision `6a700e8e183039bbb81803bacc416f6c9117ed71`; native sorted relative .py paths plus bytes SHA-256 `bac236e164f144a4269615a83fc6e3d994fa02ab06b853a43e386cfc2bbc8fd4`.
- The separately installed exact GitHub revision and released PyPI package have identical checked module bytes.
- Property basis: `PropertyBasis(fluid='Hydrogen', reference_id='CoolProp:8.0.0:HEOS:Hydrogen:default', spin_composition='normal')`; native constant saturation T 20.3689035391 K, rho liquid 70.8483459066 kg/m3 and latent difference 448711.439551 J/kg.
- Native inflow: 0.025 kg/s on [0,1.13) s, then zero through 8 s. Host absolute clock origin: 200 s, same explicitly named frame/center for both boundaries.
- Solid: k=0.16 W/(m K), alpha=7e-7 m2/s, initial T=80 K, no heat-flux cap, multiplier 1. These are numerical inputs, not fitted or claimed material coefficients.
- Radial domain 1.5 m, parabolic source radius 0.12 m, default CFL 0.2/Chezy 0.001, dry depth 1e-8 m, reported front depth 7.5e-4 m, zero retention, zero_radial_momentum_vapor evaporation closure. Initial pool inventory is zero.
- Every output independently checks the declared step integral, mass storage/evaporation/escape/adjustment, native interval mean and normal-hydrogen density/temperature. Gate: 1e-10 kg + 1e-8 times cumulative input; default allowed numerical adjustment and escaped mass are both zero.

## Native event-clock failure and explicit boundary correction

The native loop treats a next knot within 1e-12 s as already reached, while its original rate_at uses a strict time comparison. An absolute-origin subtraction or accumulated time-step roundoff can leave the clock just below isolation: the old positive rate then persists for an entire extra step. Independent input integration catches this even though the internal inventory ledger can report near-zero residual.

- Unmodified coarse case input error: 0.00025 kg; native reported final residual: 6.93889390391e-18 kg.
- Positive cases explicitly choose event_clock_roundoff_s=1e-10. A structural dataclass input proxy delegates to the actual native rate_at at a known knot only within that budget; every correction and original native object is retained. The default budget remains zero. No pool equation, time integrator or global function is patched.
- Maximum input-clock correction in the finest coupled run: 4.4408920985e-15 s. Original independent mass gates stay unchanged. Request 010 includes the receiving fix.

## Coupled spatial/time refinement

Fixed gates: maximum sample inventory difference / total supplied mass ≤0.01; maximum reported-radius difference ≤0.02 m. All compared output edges are (0.0, 0.2, 0.6, 1.13, 2.0, 4.0, 8.0) s. These are numerical agreement targets, not experimental accuracy.

| Coarse dr (m) / maximum dt (s) | Fine dr (m) / maximum dt (s) | Mass difference / supplied | Radius difference (m) | Gate |
|---|---|---:|---:|---|
| 0.02 / 0.01 | 0.01 / 0.005 | 0.02539581872 | 0 | FAIL |
| 0.01 / 0.005 | 0.005 / 0.0025 | 0.01397819186 | 0.005 | FAIL |
| 0.005 / 0.0025 | 0.0025 / 0.00125 | 0.01049241677 | 0.0025 | FAIL |
| 0.0025 / 0.00125 | 0.00125 / 0.000625 | 0.007341391668 | 0.00125 | PASS |

## Time refinement at fixed dr=0.005 m

Fixed mass target ≤0.002 of supplied mass; radius target unchanged. Values are configured maximum steps; the native CFL condition can choose smaller steps. These differences are not monotone; passing the finite agreement target does not establish an asymptotic temporal order or a Richardson uncertainty.

| Coarse / fine maximum dt (s) | Mass difference / supplied | Radius difference (m) | Gate |
|---|---:|---:|---|
| 0.01 / 0.005 | 0.0005740615027 | 0 | PASS |
| 0.005 / 0.0025 | 0.0008255597166 | 0 | PASS |
| 0.0025 / 0.00125 | 0.0008746514491 | 0 | PASS |

## Finest coupled run

| Relative time (s) | Supplied mass (kg) | Liquid inventory (kg) | Evaporated mass (kg) | Reported radius (m) | Wet area (m2) | Independent mass residual (kg) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0.2 | 0.005 | 0.004460228056 | 0.000539771944 | 0.10125 | 0.0443013652 | -3.51281504e-17 |
| 0.6 | 0.015 | 0.01375467541 | 0.001245324588 | 0.14125 | 0.0934820164 | 1.11239143e-16 |
| 1.13 | 0.02825 | 0.02441677926 | 0.003833220741 | 0.21125 | 0.246379404 | 6.72205347e-17 |
| 2 | 0.02825 | 0.01622556076 | 0.01202443924 | 0 | 0.554176944 | 1.82145965e-16 |
| 4 | 0.02825 | 0.0009617350477 | 0.02728826495 | 0 | 0.682947882 | 2.22044605e-16 |
| 8 | 0.02825 | 1.266084337e-07 | 0.02824987339 | 0 | 0.686614709 | 2.56739074e-16 |

- Exact source-interval mass sum: 0.0282498733916 kg; rebinned mass difference -3.46944695e-18 kg.
- Evaporation after liquid input isolation: 0.0244166526501 kg.
- Trapezoids of sparsely reported last-substep rates instead give 0.0319561560289 kg; this retained negative comparison is not the interval source integral.
- Derived vapor enthalpy transfer 12676.0413568 J and latent demand 12676.0413567 J use the explicit constant saturation states. Latent demand is derived, not an independently measured heat input or a checked complete energy ledger.
- Zero thermal-driving limit inventory error: 1.27935856e-16 kg; evaporation exactly zero.
- Independent capped-conduction quadrature depth error: 0 m.
- Domain 1.5 to 3 m changes mass/supply and reported radius by (0.0, 0.0).
- Deliberately inadequate 0.3 m domain rejected: escaped 0.0140753902 kg; `Liquid escaped the admissible pool domain at 201.13 s`.
- Explicit ParaHydrogen binding rejection: True.

A zero reported radius is a depth-threshold observation, not a dry pool. The native dry-depth treatment leaves a small nonzero final inventory; the run ends as window_end, not certified depletion. Numerical adjustment, domain escape and unknown properties are not erased. Interval rebinning preserves a piecewise-constant mean representation; it cannot reconstruct unobserved within-bin timing. Endpoint wet/reported areas and interval-mean/last-substep rates remain distinct. No instantaneous heat flux, vertical momentum or fully resolved atmospheric boundary is invented.

## Experimental data and unfinished contracts

The [PRESLHY E3.4 source](https://doi.org/10.35097/1319) lists eleven attachments under CC BY-SA 4.0. The default permissive-data acquisition policy withholds all eleven; metadata hashes, authors, version and omissions are recorded separately. No restricted source data or upstream digitised radius curves are redistributed or treated as independently acquired observations here. A different source or separately reviewed data workflow is required for experimental comparison.

The current native hard-coded normal-Hydrogen properties, lack of radial-state snapshots/interval-area and independent heat ledgers remain receiving extension work. The host rejects a para-Hydrogen label; it does not replace the solver or patch global property functions. Request 010 describes the actual Python contracts. Upstream component studies have their own domains and provenance and are not automatically transferred to this authored facility case.

Host SHA-256:

- `src/h2physics/sources.py`: `856e156468b43abc609c2bdce1b01ffac5221639e970cebebe8d7c1481a5be1f`
- `src/h2physics/adapters/pool.py`: `9fc009a726070ba719ed5a44bd09007eb891e5b040002a2790f3a3c7e8b3e2f7`
- `scripts/check_pool_integration.py`: `e009ba74ae13054fe2e43a96e76acbf75487c5b204483a59fd0f2e620bce3f12`
