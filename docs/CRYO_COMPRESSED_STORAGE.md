# Finite native cryo-compressed hydrogen storage

`h2physics.adapters.cryo_compressed.CryoCompressedStorage` composes an actual
LH2DT homogeneous finite fluid/wall tank, direct CoolProp HEOS, the existing
transactional pressure-relief driver and the one shared nozzle. It reuses their
physical equations, integration, event localization and flow laws. No new EOS,
tank ODE, choking closure, heat law or pressure-event algorithm is added.

This resolves a cryogenic high-pressure initial inventory, finite wall response,
warming/cooling and pressure-dependent protection. The authored25K/20MPa case
differs from warm300K gas and low-pressure LH2 through its actual native state
and explicit domain. These are model-level distinctions, not a new fitted
hydrogen fluid or a manufacturer-qualified storage design.

## Native capability and physical boundary

The separately installed MIT LH2DT0.1.2 source is pinned at
`b2f276333c1b1793c39f25763703d196d36742ec`. `HomogeneousTank` recovers state
through native density/internal-energy flashes. The existing
`Lh2dtLowLevelProperties` forwards those calls to strict direct-HEOS pure
normal, para or ortho hydrogen. `TankState` holds finite hydrogen mass/U and
wall temperature; actual native geometry holds rigid volume and wall C/UAs.

Native pressure above its critical value is supported. The replay starts at
20MPa(abs)/25K and crosses the native **critical temperature** while pressure
stays above critical pressure, using the same property provider and tank.
`supercritical_liquid` becomes `supercritical`; no liquid/vapor coexistence
transition or passage through the critical point is claimed. The exact critical
point and numerical phase names come from the selected native EOS.

The native tank owns signed heat into its wall, finite fluid-wall exchange,
bulk outflow enthalpy and RK4 steps. The existing `Lh2dtReliefTankDriver` owns
physical pressure events and a positive inventory-floor termination. A host
guard checks native T/P/phase/mass before flow probes and wall temperature at
each heat callback. Every EOS/domain failure propagates; no ideal-gas, warm-tank
or alternate EOS fallback is selected.

The declared domain includes source evidence excluding solids. HEOS fluid phase
classification alone does not qualify melting/freezing or every low-T/high-P
state. The current example20–350K/2–120MPa envelope is authored verification
scope, not a material or pressure-vessel operating certificate. Coexistence and
exact critical-point states are excluded from this first level.

## Python composition

Select/install the reviewed native source separately, as in HANDOFF.md. Native
imports happen only when `CryoCompressedNative.from_installed` is called.
Alternatively inject the four actual native modules directly into that object.

```python
from h2physics.adapters.cryo_compressed import (
    CryoCompressedDomain, CryoCompressedEvidence, CryoCompressedGeometry,
    CryoCompressedNative, CryoCompressedStorage,
)
from h2physics.adapters.lh2dt_relief import ReliefTankBoundary
from h2physics.core import Origin
from h2physics.release import NozzleOpening
from h2physics.thermo import CoolPropProperties

native = CryoCompressedNative.from_installed(
    source_id="LH2DT:b2f276333c1b1793c39f25763703d196d36742ec",
)
storage = CryoCompressedStorage(
    native, properties=CoolPropProperties("ParaHydrogen"),
    geometry=CryoCompressedGeometry(.01, 100., 1., 100.),
    domain=CryoCompressedDomain(
        20., 350., 2e6, 120e6, .01, 80., 2.,
        ("supercritical_liquid", "supercritical", "supercritical_gas"),
        "authored-single-fluid-no-solid-envelope",
    ),
    evidence=CryoCompressedEvidence(
        "authored20MPa25K", "authored-fixed-volume-wall",
        "authored-constant-UAs", "authored-binary-relief",
        "authored-phase-and-solid-exclusion", Origin.SYNTHETIC,
    ),
    initial_pressure_pa_absolute=20e6, initial_temperature_k=25.,
    initial_wall_temperature_k=25.,
    opening=NozzleOpening("authored-PRV", 1e-8, 1., "authored-effective-area"),
    set_pressure_pa_absolute=100e6, reseat_pressure_pa_absolute=99e6,
)
boundary = ReliefTankBoundary(
    "operation-clock", 100., 200.,
    storage.properties.state_pt(19e6, 25.),  # Explicit high-pressure receiver.
    lambda time: 300.,
    lambda time, native_fluid, wall: 1000.-1.*(300.-wall),
    "authored-constant-net1000W-to-wall",
)
trace = storage.run(duration_s=100., maximum_step_s=.5, start_time_s=100.,
                    clock_id="operation-clock", boundary=boundary)
last = trace.points[-1]
print(last.fluid.temperature_k, last.fluid.pressure_pa,
      last.balance.energy_residual_j)
```

These are synthetic verification parameters. The supplied callback cancels the
native ambient-UA term so that net external heat is exactly1000W. It establishes
an analytic total-energy limit; it is not a measured insulation heat leak or a
refrigeration model. Signed cooling is allowed when all actual fluid/wall trial
states stay in the domain. Refrigeration capacity, cycle power and COP require
their own models/evidence.

`CryoCompressedGeometry` uses m3, J/K and W/K. Native geometry requires all four
entries strictly positive. Pressures are Pa absolute, temperatures K, inventory
kg, energy J, time s. `CryoCompressedDomain` explicitly selects the initial cold
limit and minimum initial P/Pcritical ratio, in addition to the full transient
domain. The example rejects300K and150kPa starts; these remain valid inputs to
their appropriate existing warm-gas/LH2 levels. No universal80K definition of
cryo-compressed storage is inferred from this example's initial scope.

## Protection, clocks and finite inventory

Each run constructs fresh actual native protection state, so reusing a builder
does not inherit a previous run's open latch. The native initial tank state is
retained and is not reset during a run. Below set pressure the tank is sealed.
When set pressure is reached, the actual native valve opens and shared-nozzle
bulk withdrawal proceeds to the end of the requested window or inventory floor.
This is **not** stop-at-pressure or ideal isolation. The replay's19MPa25K
receiver is a prescribed pressure/thermodynamic boundary, not atmosphere or a
finite receiving vessel. It does not produce a qualified atmospheric source.

The pressure driver retains actual accepted before/after latch copies, event
brackets, source limits, tank steps and RK stage heat/enthalpy ledgers. Its
existing0.001Pa/1e-8s event budgets and1e-9s minimum native interval remain
unchanged. Endpoint bracketing assumes a resolved first crossing; arbitrary
hidden nonmonotonic crossings inside a step are not guaranteed detected.
No sensor lag or other pressure signal replaces physical tank actuation.

Native positive trial inventories may cross the configured positive floor while
the existing event driver localizes it. The final floor state is checked with
the explicit1e-12kg event tolerance. No accepted mass is clipped and reaching
the floor does not close the native valve. T/P/phase failures may precede a
floor event and remain failures. Pressure, wall-heat and receiver boundaries
must retain compatible material/reference identities and complete explicit
clock support; no extrapolation or recorder synchronization is performed.

## Independent ledgers and result API

`CryoCompressedTrace` retains the builder, native driver/trace, actual protection,
separate independent HEOS provider, boundary, immutable configuration/evidence
objects, critical values and all audit budgets. `points` contains the initial
and each accepted native state, physical `ThermoState`, fresh native PT/P-rho
reconstructions, `ConservedInventory`, `InventoryBalance` and their residuals.

Each accepted total energy is fluid U plus Cwall*Twall. The existing signed
boundary is external heat minus discharged stagnation enthalpy. Mass is initial
mass minus discharged mass. Physical conservation defaults remain1e-12kg,
1e-5J and relative1e-10. Distinct EOS inversion gates are1e-10kg,1e-4J and1e-7K.
The separate native P-rho flash can differ by approximately2e-9K here, giving
approximately1e-5J U discrepancy; it is a numerical flash-roundtrip error,
not a relaxed physical energy ledger or independent measured EOS accuracy.
Every post-run domain, native-state reconstruction, independent EOS query,
residual or final configuration-check exception becomes `CryoCompressedAuditError`.
It retains the completed `native_trace`, actual failing accepted `native_state`,
`accepted_time_s`, and immutable `audited_points` prefix. `point` is the complete
failed audit point when constructed, or `None` if the failure occurs earlier.
The original exception remains at `__cause__`. Thus an accepted native RK endpoint
that leaves the wall domain after all stage inputs passed remains inspectable,
as do independent PT/P-rho exceptions; a partially audited run is never returned
as a successful trace.
Native integration errors retain actual components and last accepted state.

Native objects and the advanced builder remain mutable. External or concurrent
modification invalidates their correspondence to a trace; use a new evidenced
builder for changed configuration. The audit catches changed native tank/property
ownership and incompatible reference identity. Trace clocks/integral arrays
inherited from the existing driver are read-only.

```powershell
.venv\Scripts\python -m pytest tests/test_cryo_compressed.py -q
.venv\Scripts\python -X utf8 scripts/check_cryo_compressed.py
```

The replay checks three spin-specific pure fluids, sealed critical-temperature
crossing, exact external-power total energy, independent finite-wall equilibrium,
signed cooling/zero heat, time refinement, actual pressure events and positive
inventory termination. [research/cryo_compressed.md](../research/cryo_compressed.md)
records completed native calculations, fixed gates, timing and begin/end native/
host/test/script hashes. No experimental calibration or manufacturer qualification
is claimed.

Refueling, a cooling plant, actual vacuum-insulation construction, pressure-vessel
strength/fatigue, spatial stratification, selective liquid/vapor pickup, evolving
spin conversion and finite receiving vessels require their own evidence and
native connections. A public accepted-step/stop-at-first-event hook would permit
a distinct pressure-stop workflow without reproducing the existing event code.

Primary context: [LLNL/DOE cryo-compressed storage](https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/progress07/vi_a_6_aceves.pdf),
[NIST separate H2 EOS](https://doi.org/10.1063/1.3160306),
[CoolProp](https://doi.org/10.1021/ie4033999), and
[actual native LH2DT](https://github.com/lyullee/lh2dt_models).
Original composition/verification cases are authored here. Native source, data,
coefficient tables and experimental records are not bundled or copied.
