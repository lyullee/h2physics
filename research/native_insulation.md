# Native vacuum-insulation verification

Completed UTC: 2026-10-27T03:13:33.079840+00:00.

Native MIT `lh2dt_models` revision `b2f276333c1b1793c39f25763703d196d36742ec` (0.1.2); aggregate native module SHA-256 `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`. The existing separately installed engine owns heat laws, geometry, EOS closure and tank RK4. No native source file or coefficient was modified.

This is synthetic numerical verification. Parameters are authored geometry/construction inputs, with helium as the declared residual-gas identity. The effective gas coefficient and 0.08 Pa molecular-flow limit are synthetic test assumptions, not qualified material or vacuum-regime measurements. No heat-leak data or vendor performance was fitted.

Primary references consulted: [2022 CODATA/NIST Stefan-Boltzmann constant](https://physics.nist.gov/cgi-bin/cuu/Value?sigma), [NASA cryogenic insulation testing](https://ntrs.nasa.gov/citations/19990053342), [NASA MLI repeatability study](https://ntrs.nasa.gov/citations/20180000366), and [NASA continuum/kinetic MLI venting model](https://ntrs.nasa.gov/citations/20180002393). These support independent thermal limits and the need for pressure/construction-specific qualification; no source table, plot or measured coefficient is reproduced. Public metadata were inspected without acquiring a dataset or claiming raw-data rights.

Static native parameters: `VacuumInsulationParameters(area_m2=2.4, effective_emissivity=0.0033, mli_solid_conductance_W_K=0.008, support_conductance_W_K=0.002, residual_gas_coefficient_W_m2K_Pa=0.025, maximum_valid_vacuum_pressure_Pa=0.08, localized_heat_paths=(LocalizedHeatPath(path_id='neck', conductance_W_K=0.0014), LocalizedHeatPath(path_id='instrument', conductance_W_K=0.0006)))`.

At 295/24 K and 0.006 Pa absolute, native parallel-path heat is 6.75055470659 W: `{'radiation': 3.400994706593174, 'mli_solid': 2.168, 'support': 0.542, 'residual_gas': 0.09756, 'localized': 0.542}`. Radiation/NIST verification error 0 W; zero gradient returns exactly 0 W for every path, and swapping boundary temperatures reverses the complete signed heat within 1e-12 W. The native reported effective UA is 0 at exactly zero gradient; it is a diagnostic ratio, not the differential conductance.

Doubling both absolute temperatures in the radiation-only case gives heat ratio 16. Equal-temperature area partition total 6.75055470659 W agrees with the unpartitioned native boundary within 1e-12 W. Three heterogeneous wall zones preserve area and separate penetration allocations; zone heat `(1.311383700441262, 1.919930687300669, 3.278521536014381)` W matches the independent reference to 2.22e-16 W. Independent reference equations are used only in this verification script, not as another solver.

| Absolute annulus pressure (Pa) | Native gas-only heat (W) |
|---:|---:|
| 0 | 0 |
| 1e-09 | 1.626e-08 |
| 1e-06 | 1.626e-05 |
| 0.001 | 0.01626 |
| 0.08 | 1.3008 |

Native pipe-envelope geometry: length 1.3 m; bore/process-outer/jacket-inner diameters .018/.022/.060 m; fluid volume 0.000330809706423 m3; process wall volume 0.000163362817987 m3; jacket-reference area 0.24504422698 m2; radial gap 0.019 m. Native `make_insulation` retains this jacket area, giving 1.2741406383 W at 295/24 K and .006 Pa. This checks the actual pipe-envelope heat law; the stock DynamicHEMPipe has no callable external heat hook, so it is not silently replaced by a state-varying UA.

## Actual native layered tank boundary

The tank is a .5 m diameter, .9 m straight cylinder with two .1 m deep ellipsoidal heads; one liquid cell, one vapor cell and three wall nodes. Its native inner area is explicitly used as an effective warm reference area. Source pressure is 200 kPa absolute, liquid fill fraction .6, and native para-H2 HEOS properties preserve their energy reference. The wall capacity is 500 J/K, partitioned using public geometric wetted-area differences. Area fractions: `(0.37063568951433107, 0.258728620971338, 0.37063568951433096)`; native tank area 1.91382796713 m2. Neck allocation is (0,0,1), instrument allocation (.2,.5,.3). Built-in ambient UA and axial wall conduction are explicitly zero to avoid double-counting. The coupled cases use .25 W/(m2 K) wall/fluid coefficients; all remaining default native phase-interface and EOS responsibilities remain native.

The analytic wall-only case removes wall/fluid exchange and radiation/gas/local paths, uses 0.08 W/K distributed solid conductance, and applies a linearly warming reservoir on absolute time 11-13 s. Native callbacks receive actual wall states and the declared operation clock. Expected final wall T 60.0704527304 K; maximum error 1.63e-13 K; independent energy residual -2.55e-11 J; 10 accepted steps / 40 callback evaluations. Fluid internal energy is unchanged within 1e-8 J.

Coupled 0.4 s cases use absolute time 7-7.4 s, initial wall 28 K, effective emissivity .0025, MLI/support conductances .008/.002 W/K, residual coefficient .025 W/(m2 K Pa), and neck/instrument .0014/.0006 W/K. Warm T is 295+.4*(t-7) K, while synthetic absolute vacuum pressure is .002*(1+.01*(mean wall T-28))+.0001*(t-7) Pa. Reversed heat uses a 10 K warm-side intercept with the same explicit laws. This state law tests a callback; it is not a vacuum-pump or gas-adsorption model.

| Case / dt (s) | Steps | Native external heat (J) | Fluid/solid energy change (J) | Max independent mass residual (kg) | Max independent energy residual (J) | Accepted-sample trapezoid error (J) | Runtime (s) |
|---|---:|---:|---|---:|---:|---:|---:|
| heating / 0.2 | 2 | 2.11499817898 | 0.995007036079 / 1.11999114295 | 0 | 4.04e-11 | 6.5e-08 | 1.63134 |
| heating / 0.1 | 4 | 2.11499817898 | 0.995007036079 / 1.11999114295 | 1.78e-15 | 4.34e-11 | 1.63e-08 | 3.2718 |
| heating / 0.05 | 8 | 2.11499817898 | 0.995007036079 / 1.11999114295 | 0 | 4.04e-11 | 4.07e-09 | 5.56169 |
| reversed / 0.05 | 8 | -0.0867690875206 | 0.994585776993 / -1.08135486451 | 0 | 7.52e-11 | 3.12e-10 | 7.79139 |

The independent reader uses sum(m*h)-p*rigid_volume plus explicitly supplied wall capacities and returns existing ConservedInventory objects. Existing InventoryBalance checks use 1e-10 kg, 1e-7 J and 1e-9 relative budgets. Independent inventory/native total energy agreement is at most 0 J. Boundary sampled quadrature is independent of native RK-stage cumulative heat; finest error 4.07e-09 J passes a 1e-6 J gate. Last two heating refinements differ by 7.11e-15 K maximum wall temperature and 5.82e-11 Pa tank pressure, against 1e-7 K / .01 Pa gates. These numerical gates are fixed before reporting the result.

Finest heating vacuum 0.002 -> 0.00204004443822 Pa, pressure 200003.683617 Pa, wall T `(28.001881876541624, 28.00206042682187, 28.002723429811635)` K. Reversed external heat -0.0867690875206 J is retained; fluid can still gain energy from a warmer wall while the complete closed inventory loses energy. Deliberately doubling wall capacity in the independent reader gives residual 1.11999114298 J (reversed -1.08135486453 J); both fail the 1e-4 J negative-check threshold.

## Preserved limitations and local receiving requests

- pressure above explicit molecular-flow bound: rejected with `Vacuum pressure lies outside the declared native molecular-flow closure`.
- unallocated native penetration: rejected with `Allocate every native localized path explicitly, without inferred area weighting`.
- native zero-area-zone incompatibility: rejected with `area_m2 must be positive`.
- The existing low-level property facade is unavailable for this layered-tank API: `'Lh2dtLowLevelProperties' object has no attribute 'specific_volume_derivatives_ph'`. Its earlier actual initialization attempt failed at LayeredTank.project_pressure. The successful cases explicitly select original native HydrogenProperties with HEOS ParaHydrogen; saturated-liquid enthalpy matches the host reference at 200 kPa within 1e-8 J/kg. No unsupported derivative is invented and no automatic property fallback is added.
- Native zero-area wall fractions pass the partition's nonnegative-fraction check but fail its positive-area zone construction. Add a public zero-zone treatment that preserves discrete penetration placement, with limits and tests; do not renormalize it silently.
- Add public callable signed external-heat inputs to DynamicHEMPipe and other lumped equipment. Preserve native wall/fluid equations, RK-stage heat ledgers, units and absolute clocks; a mutable or fitted UA is not the general nonlinear boundary.
- Expose public wall zone areas/capacities and decomposed per-zone path results. The present tank composition derives geometry through public methods and independently declares capacity; the native layered partition currently returns totals only.
- The native molecular gas law stops at the declared pressure limit. Continuum/transition transport, changing residual gas, MLI compression/aging, warm-jacket thermal storage, loss-of-vacuum ingress/condensation and measured calorimeter qualification remain open. No native default is promoted to a construction-specific material coefficient.

Static checks runtime 0.0048925 s; analytic wall case 5.60951 s. Runtimes describe this local workload only.

Source/test/script SHA-256:

- `src/h2physics/adapters/lh2dt_insulation.py`: `2d239b676034f6844f5991978184438662edc7eac6507b43058ce37399d28c1a`.
- `tests/test_lh2dt_insulation.py`: `da841c144dc56a60d37fa7dd27b54ddead9a92d429bfd2953fb165684f8fd7e4`.
- `scripts/check_insulation_integration.py`: `48c664d979f2d465f8c73cf32974fe7369b1fdc8c2f0ea18550575265ad8dac4`.
- Native `lh2dt/vacuum_insulation.py`: `02487871ef3df5420c71ffd12129f98d1444ca39de45101d891567e0ccbf7cec`.
- Native `lh2dt/vacuum_jacketed_pipe.py`: `8d20e6c234bb10c44b53c244b3ae89d15e7bcc99496ac8a388e063b13d7227fe`.
- Native `lh2dt/layered_tank.py`: `0445632196cb56fb7aed1f68957d5f369ba35387291e292e5ce28239c8a4e8d2`.

No external repository edits, messages, data downloads, new dependency installation or measured/vendor validation occurred. This first executable insulation level remains a qualified software composition with authored verification parameters.
