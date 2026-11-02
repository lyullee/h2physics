# Stored-pressure energy and structural response

These APIs connect a finite thermodynamic stock, a declared pressure-load owner,
and a linear generalized structure. They keep mechanical pressure work separate
from combustion energy. Import directly from the modules shown below.

## Expansion reference

`h2physics.mechanical_rupture.isentropic_expansion_energy` takes a real-fluid
initial pressure and temperature, inventory mass, ambient pressure and source
identity. The initial inventory is homogeneous and at equilibrium. Direct
CoolProp HEOS evaluates both states, including a two-phase final state when
supported. No constant-gamma gas law or alternative property equation is used.

The final state has `p2 = p0` and `s2 = s1`. The returned quantities are:

| Quantity | Definition | Interpretation |
| --- | --- | --- |
| Gross expansion work | `m (u1-u2)` | Reversible adiabatic work along this path |
| Ambient displacement | `p0 m (1/rho2-1/rho1)` | Work displacing the ambient medium |
| Net mechanical work | Gross minus displacement | Useful mechanical work reference |

All energies are finite-stock joules, rather than flow powers or specific
energies. This is neither complete thermal exergy nor a rupture/blast efficiency.
Heat received later from the environment, heterogeneous liquid/gas inventories,
vessel elastic strain, crack initiation, flashing kinetics and combustion need
their own owners. There is no claim that the selected reference is an upper
bound for every cryogenic accident path. See the
[hydrogen physical-explosion model comparison](https://www.cetjournal.it/index.php/cet/article/view/CET2291071)
for the importance of selecting the actual thermodynamic scenario, and
[CoolProp's native state API](https://coolprop.org/coolprop/LowLevelAPI.html)
for property ownership. No paper-specific table or fitted blast correlation is copied.

`MechanicalEnergyAllocation` divides the net reference into caller-declared,
disjoint shock/acoustic, fragment and wall shares, retaining the unallocated
remainder. Shares must be nonnegative and sum to at most one. Evidence or an
explicit assumption identifier is mandatory. There is no default efficiency.
`DetonableHydrogenEnergy` from the chemical-overpressure adapter is a different
type and is not interchangeable with this allocation.

## Pressure history ownership

`MechanicalLoadRequest` retains allocation, receptor distance, load identity and
actual-event clock. `mechanical_rupture_load` calls a separately supplied
`MechanicalPressureProvider.pressure_history(request)`. The provider must check
its geometry, material, phase and energy applicability. It must return an
identified `PressureTimeHistory`; an indoor curve indexed by hypothetical
ignition delay is refused by type. A measured waveform may be supplied, but its
measurement provenance must not imply that the local energy estimate predicted it.

An optional low-level reference, `SphericalAcousticPulse`, normalizes a **supplied**
piecewise-linear shape and duration in an outgoing, spherical linear acoustic
field:

```text
E_acoustic = 4 pi r² / (rho_ambient c_ambient) * integral(p(t)² dt)
```

The ambient density and sound speed come from CoolProp. The square integral of
each linear segment is calculated exactly. See
[NASA/SP-2015-624](https://ntrs.nasa.gov/api/citations/20160000818/downloads/20160000818.pdf)
for the acoustic intensity/free-field basis. The caller supplies both a minimum
far-field distance and a small pressure-to-ambient acceptance limit (at most
0.1). These are admission assumptions, not an automatically qualified domain.
The mechanical shock share is interpreted as the acoustic energy crossing the
sphere under this selected approximation. It does not calculate nonlinear shock
decay, near-field rupture, shielding, reflections, venting or BLEVE loads.
Pulse duration and shape are never inferred from stored energy or peak pressure.
Input timestamps already belong to the receptor event clock; no travel time is
silently added. Rejecting a strong pulse does not invoke a replacement model.

## Linear generalized structural model

`h2physics.materials.sdof.LinearSDOF` and `solve_linear_sdof` solve
`M x'' + C x' + K x = A_eff p(t)`. The effective mass, stiffness, damping and
loaded area must correspond to **one generalized displacement coordinate**.
The waveform is the net applied differential pressure on the surface. Pressure
reflection and spatial load/mode-shape transformations belong to the supplier.
The general method is described in
[UFC 3-340-02](https://www.wbdg.org/ffc/army-coe/ufc/ufc-3-340-02);
no resistance charts or structural failure thresholds are bundled.

The implementation is linear elastic. It does not label a clipped spring as
plastic hysteresis, predict panel fracture, or qualify a building. Each waveform
corner is an integration boundary, so a pulse shorter than output sampling is
still integrated. Pressure is piecewise linear within its support and zero
outside. Nonzero endpoint pressures declare a jump. Initial displacement and
velocity refer to the first timestamp, which must equal the load's first time.
The output may extend through free vibration after pressure support ends.

Outputs include displacement, velocity, acceleration, restoring force, kinetic
and elastic energy, integrated input work, damping dissipation and the residual
`KE + strain - initial_energy - input_work + damping`. Integration uses SciPy
DOP853 with configurable tolerances, rather than integrating work only on the
requested output grid. Arrays are immutable snapshots.

## Executable conditional chain

```python
import numpy as np
from h2physics.thermo import CoolPropProperties
from h2physics.mechanical_rupture import (
    MechanicalEnergyAllocation, MechanicalLoadRequest, SphericalAcousticPulse,
    isentropic_expansion_energy, mechanical_rupture_load,
)
from h2physics.materials.sdof import LinearSDOF, solve_linear_sdof

energy = isentropic_expansion_energy(
    CoolPropProperties("Hydrogen"), source_id="demonstration-stock",
    inventory_mass_kg=2.0, initial_pressure_pa=20e6,
    initial_temperature_k=300.0, ambient_pressure_pa=101325.0,
)
# Authored numerical demonstration, not a calibrated rupture efficiency.
allocation = MechanicalEnergyAllocation(energy, 1e-5, 0.0, 0.0, "synthetic split")
wave = SphericalAcousticPulse(
    CoolPropProperties("Air"), ambient_pressure_pa=101325.0,
    ambient_temperature_k=300.0, time_s=[0.0, 0.01, 0.03],
    dimensionless_shape=[0.0, 1.0, 0.0], minimum_distance_m=10.0,
    maximum_pressure_to_ambient_ratio=0.01,
    assumption_evidence_id="synthetic weak-wave demonstration",
)
load = mechanical_rupture_load(
    MechanicalLoadRequest(allocation, 20.0, "arrival-seconds", "panel-load"), wave
)
response = solve_linear_sdof(
    LinearSDOF(10.0, 1e5, 40.0, 1.0, "synthetic generalized panel"),
    load.pressure, np.linspace(0.0, 0.5, 51),
)
print(energy.net_mechanical_work_j)
print(max(abs(response.displacement_m)))
print(max(abs(response.energy_residual_j)))
```

Install the `thermo` extra for this example. Direct pressure-to-SDOF use only
needs the core NumPy/SciPy dependencies.

## Verification and next evidence

Run `python -m pytest -q tests/test_mechanical_rupture.py tests/test_sdof.py`.
The tests compare net expansion energy with an independent pressure integral
along the native isentrope; exercise a liquid initial state and native two-phase
endpoint; check stock scaling, zero pressure difference and energy allocation;
and verify acoustic energy normalization, inverse-distance scaling and strong
pulse rejection. SDOF displacement is compared with closed-form rectangular and
triangular forcing and damped free vibration. The triangular pulse is shorter
than output spacing. Energy balances and the complete conditional chain are
checked separately from provider internals.

These tests establish the declared host equations and basic handoffs. They do
not constitute experimental rupture or structural qualification. A next study
needs independently evidenced energy partitions, measured receptor waveforms,
structure-specific generalized parameters and failure criteria. A qualified
nonlinear blast provider can implement the existing protocol without replacing
the inventory, event clock or structural contracts.
