# Native finite line/vaporizer storage and scheduled isolation

Native lh2dt_models 0.1.2, MIT revision `b2f276333c1b1793c39f25763703d196d36742ec`.
Top-level native Python-source SHA-256: `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.
Reproduce with `python scripts/check_dynamic_inventory.py` after the isolated optional install in HANDOFF.md.

All geometry, commands and heat/hydraulic parameters below are authored synthetic inputs. This verifies native composition, clocks and conservation; no experimental qualification is inferred.

The line is one 0.5 m by 10 mm mixed fluid volume (geometric volume), with wall capacity 10 J/K and fluid/wall and ambient UAs 0.05 / 0.01 W/K. Initial fluid pressure/quality is 320000 Pa / 0.1; wall temperature 30 K. The vaporizer volume is 0.0002 m3, wall capacity 20 J/K, UAs 0.2 / 0.1 W/K, symmetric fluid heat cap 100 W, initial pressure/quality 280000 Pa / 0.2 and wall temperature 35 K. Ambient is 300 K. A separate 1 m by 0.2 mm HEM restriction (roughness 1 micrometre) joins the volumes. These are separate physical volumes/restriction; line hydraulic half-segments are not also counted.

A 350000 Pa, 20 K feed and 150000 Pa delivery reservoir connect through two shared 0.15 mm nozzle valves with effective-area factor 0.8 and reverse flow enabled. Both use HEOS ParaHydrogen with an explicit 1e-8 endpoint-quality budget. The feed closes at 0.137 s and the outlet at 0.411 s; duration is 1 s. Prescribed commands partition native integration intervals, including partial end steps. The left and right hydraulic limits are retained separately while inventory remains continuous.

| Nominal step s | Accepted steps | Discharge after feed closure kg | Max node mass residual kg | Max node energy residual J | Sealed assembly mass error kg | Sealed energy/heat error J | Wall s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.1 | 11 | 4.66272298268e-06 | 4.54009659728e-19 | 7.9936057773e-14 | 0 | 1.20792265079e-13 | 0.273755800008 |
| 0.05 | 21 | 4.66272298268e-06 | 1.20702194984e-18 | 2.45137243837e-13 | 8.67361737988e-19 | 1.172395514e-13 | 0.437541799998 |
| 0.025 | 41 | 4.66272298268e-06 | 8.35174485993e-19 | 2.48689957516e-13 | 8.67361737988e-19 | 1.27897692437e-13 | 0.828626600007 |

Finest-two-run maximum relative final node mass/pressure differences: 1.31961108707e-12 / 4.25104396129e-13; each gate is 1e-6. Mass/energy gate defaults are 1e-8 kg / 1e-4 J with relative 1e-8 on changes/fluxes, not absolute reference energy. Every node is checked separately; cancelling errors cannot pass through a global sum. All accepted fluid states remain mixed-phase in this case.

Evaluating the same discontinuous controls inside unsplit 0.1 s RK steps changes final assembly mass by -6.95311679601e-07 kg relative to the finest partitioned run. That trajectory can still conserve its computed fluxes. Conservation alone therefore does not verify the intended command time; the partitioned driver preserves both.

A reversed sealed pair (270000 / 320000 Pa) transfers mass from vaporizer to line; assembly mass change is 0 kg. Each native stage retains the actual upstream enthalpy and passes the independent steady transfer checks.

A separate closed warm-fluid vaporizer has zero fluid/wall UA, wall C=2 J/K, ambient UA=1 W/K, initial wall 200 K and ambient 280+3*t K. Its absolute clock runs from 10 to 12 s and is partitioned at 10.37/11.11 s. The unchanged fluid mass/energy and the analytic wall ODE provide an independent limit, including time-varying ambient callback clock translation.
Analytic final wall temperature is 271.740538118 K; native absolute error is 1.22913718315e-07 K against a 1e-6 K gate.

Negative checks reject a doubled vaporizer wall-capacity reader (first energy residual 1.22321234685 J) and a command that replaces a dynamic fluid boundary. The driver also requires an explicit external-heat field and matches accepted native solutions by object identity; no five-solves-per-step assumption is required.

One cell per device assumes homogeneous equilibrium and instantaneous mixing; slip, wave propagation, finite valve motion, pressure-trigger localization, complete mass/phase depletion, frost, pump startup and independent apparatus data remain open. A closed outlet is not an empty inventory and nozzle liquid is not ground-reaching liquid.

Host code SHA-256:

- `src/h2physics/dynamics.py`: `d3964d476994dc12cee0113ee137cc1313c8e0d4f97dfd3167b487c8367e9abd`
- `src/h2physics/adapters/lh2dt_dynamics.py`: `24d47555c295cfd7850459933a2077b1c37bf5ffcffa292045b962cd93daec69`
- `src/h2physics/adapters/lh2dt_equipment.py`: `87c29e0b47f35da3e38baf4ca2ce1832f58a91104701a95c144e5e30f7080b33`
- `scripts/check_dynamic_inventory.py`: `599330cce958945712bf06f33d39566c24eaa69c8284580919cd32c7196032a7`
