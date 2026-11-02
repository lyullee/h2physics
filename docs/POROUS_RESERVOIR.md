# Single-phase radial porous-reservoir model

`h2physics.storage.PorousReservoir` is an implicit, fixed-temperature, finite-volume
mass-balance component for a caller-defined, radially symmetric porous domain.
It advances gas pressure and cell inventory with a backward-Euler step and a
single-phase Darcy intercell flux. The model accepts either separate density
and viscosity callbacks or a `PropertyProvider` through
`PorousReservoir.from_property_provider(...)`. `CoolPropProperties` can be
passed directly; the exact fluid/energy-reference basis is retained and each
state must be gas-like with a defined single-phase viscosity. The provider
path does not add phase partition or porous multiphase closures.

## Inputs and boundaries

The geometry requires increasing radial faces, thickness, cell porosity,
permeability, and a prescribed temperature in every cell. Temperatures may vary
radially, but remain fixed for the full run. Initial pressure is supplied once
per radial cell and is checked against the geometry when `run()` is called.
Lower/upper pressure limits and a common clock are explicit. The schedule selects
exactly one of signed well mass flow or a sampled well-pressure boundary; either
series must match the time grid. Positive flow injects gas and negative flow
withdraws it. With a well-pressure boundary, pressure at the inner radial face
is connected to the first cell center by the same single-phase radial Darcy
transmissibility used between cells. Each interval uses the mean endpoint well
pressure and the implicit endpoint cell state; the rate sign follows the
well-to-reservoir pressure difference. Injection properties use the explicit
`well_temperature_k`, defaulting to the first-cell temperature. Withdrawal uses
the donor cell state. This boundary does not add a wellbore, skin, tubing,
pressure-loss correlation, or calibrated deliverability law. The default outer
face is closed. An optional sampled outer pressure selects a separate boundary;
its inflow temperature can be supplied separately and defaults to the outermost
cell temperature. The implicit solve is bounded with SciPy `least_squares`.
Each nonlinear cell residual is accepted against a relative budget scaled to that
cell's larger old or candidate gas inventory. This avoids a total-system scale
hiding a poor balance in a small cell, and removes the fixed one-kilogram floor
that could admit disproportionate absolute error for core-scale volumes. The
outer-boundary contribution remains explicit in each cell balance and in the
reported global residual.

The solver exclusively issues each result. `require_current()` fingerprints the
result arrays and retained geometry/schedule values so direct construction,
cloning, or later edits cannot preserve the original currentness receipt. The
result retains pressure, per-cell gas mass, cumulative signed well
mass, cumulative signed outer-boundary exchange, and a per-step total mass
closure residual. The geometry and property
evidence identifiers remain attached to the result. `property_evidence_id`
must identify the fluid, phase, EOS/backend, composition, and unit basis. In
callback mode it covers both functions; in provider mode it also identifies
the selected provider revision and retained `PropertyBasis`.

## Deliberate model limits

This component is a numerical balance kernel, not a qualified underground
hydrogen-storage model. It assumes one gas phase, fixed pore geometry and rock
properties, prescribed temperature, radial symmetry, and a caller-selected
prescribed well rate or inner-face pressure boundary. It does not infer
permeability/porosity evolution, capillary
pressure, relative permeability, dissolution, microbial reactions, heat
transfer, salt creep, damage, fracture, leakage, geomechanical safety limits,
or a wellbore/deliverability law. A site model must establish those independently
and couple only through explicit, documented boundaries.

## Executed numerical verification — 2026-11-01

Four local cases now passed from a fresh Python process. The original analytic
single-cell ledger and pressure-driven well use explicit ideal-gas reference
fixtures. The separate provider-binding case uses native CoolProp HEOS for a
single-cell zero-flow check, retains its property basis and rejects liquid
states. These scopes are separate from the new dynamic HEOS refinement case.

`porous-reservoir-coolprop-dynamic-refinement` uses normal hydrogen at 300 K,
initial pressure 2 MPa, closed outer boundary and prescribed injection
0.001 kg/s over 10 s. The radial domain is 0.1–1 m, thickness 10 m, porosity
0.2 and permeability 1e-15 m2. Geometry and material parameters are authored;
no geological data calibration is implied.

- Injected mass: 0.01 kg.
- Maximum cumulative mass discrepancy: 7.92e-13 kg.
- Maximum single-step total mass residual: 6.31e-13 kg.
- Fixed four-cell time refinement, 8/16/32 steps: final-pressure differences
  607.28 then 309.05 Pa; observed backward-Euler self-convergence order 0.9745.
- Fixed 64-step radial refinement, 4/8/16 cells: pressure differences at nine
  common receptors decrease from 1513.64 to 423.91 Pa. Projection interpolates
  in log radius within every mesh's represented cell-center support.
- Fine-mesh first-cell final pressure: 2067291.2036 Pa.

This establishes direct-EOS coupling, numerical conservation and a refinement
trend for this authored problem. Independent benchmark, measured reservoir
comparison and site qualification remain open. Temperature is imposed; no
heat, multiphase, rock-mechanics or wellbore model is inferred from the checks.

Cold execution uncovered a circular import through the adsorption-product
receipt and the adapters package. Its type-only import is now postponed and
its concrete runtime check remains at construction. Four fresh-interpreter
package-import regression checks also passed; they are packaging checks, not
additional physical validation.

## Executed porous-level source identity

Python 3.12.16; NumPy 2.5.4; SciPy 1.18.1; CoolProp 8.0.0.

- `src/h2physics/storage/porous_reservoir.py`: `51ab0b6749ad31e84a4d47058d1925e2bd06726440456b44da53823e28bcf09c`

- `validation/cases/porous_reservoir.py`: `3acfcdc3854865727704851d09b9309e85004773f8099e43232f1f687133e89d`

- `src/h2physics/thermo/coolprop.py`: `74bf3d7f49c5b3163c7a079c358a866d48d28280e25a2592ce53b3351e815d03`
