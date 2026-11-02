# Transient radial heat transfer in a cylindrical wall

`h2physics.materials.radial_cylinder_heat_history` computes a one-dimensional,
axisymmetric transient temperature field through a finite cylindrical wall. It
is intended to create temperature snapshots that can be passed into
`RadialTemperatureProfile` and the radial thermoelastic solver.

## Governing balance

For a homogeneous wall with no internal heat source, the cell energy balance is

\[
\rho V_i c_p(T_i)\frac{dT_i}{dt}=\begin{cases}
Q_\mathrm{inner}-q_{1/2}, & i=0,\\
q_{i-1/2}-q_{i+1/2}, & 0<i<N-1,\\
q_{N-3/2}+Q_\mathrm{outer}, & i=N-1.
\end{cases}
\]

The internal rates \(q\) are positive radially outward. Both boundary terms
\(Q_\mathrm{inner}\) and \(Q_\mathrm{outer}\) are positive into the wall; this
means the inner and outer boundaries enter the first and last cell with a plus
sign when they heat the solid.

The radial conductive resistance between two cylindrical radii is
\[
R=\frac{\ln(r_2/r_1)}{2\pi L k},\qquad \dot Q=\frac{T_1-T_2}{R}.
\]
Cell-face rates are shared with opposite signs by adjacent volumes. Boundary heat
rates are additional solver states, so the returned global ledger checks stored
enthalpy change against integrated inner and outer boundary heat.

## API example

```python
from h2physics.materials import (
    RadialSolidMaterial,
    RadialThermalBoundary,
    radial_cylinder_heat_history,
)

steel = RadialSolidMaterial(
    density_kg_m3=7800.0,
    heat_capacity_j_kg_k=lambda temperature_k: 500.0,
    conductivity_w_m_k=lambda temperature_k: 16.0,
    material_id="replace-with-material-and-grade",
    evidence_id="replace-with-property-source-or-calibration",
)
result = radial_cylinder_heat_history(
    inner_radius_m=0.05,
    outer_radius_m=0.10,
    length_m=1.0,
    material=steel,
    initial_temperature_k=293.15,
    time_s=[0.0, 10.0, 20.0],
    inner_boundary=RadialThermalBoundary(
        "convection", 100.0, "inner-fluid-source", coefficient=50.0
    ),
    outer_boundary=RadialThermalBoundary("adiabatic", 0.0, "insulated-boundary"),
    history_id="tank-wall-run-2026-01",
    clock_id="tank-wall-operating-clock",
    evidence_id="axisymmetric-radial-conduction-model",
)
```

The callback properties receive absolute temperature in kelvin. A boundary heat
flux is positive into the solid. A convection boundary's `value` is bulk-fluid
temperature and `coefficient` is the film coefficient. A prescribed-temperature
boundary supplies the wall-face temperature. Both inner and outer face heat
rates use the same positive-into-solid sign convention.
Material, boundary and model evidence identities are required nonblank strings; invalid
identity types are rejected at construction with a validation error. Boundary `kind` is a
string selector and rejects non-string values explicitly.

For property callbacks with a known usable interval, pass the material through
`guard_radial_material_temperature_domain(material, (T_min, T_max),
preflight_samples=9)`. The returned material preserves the material/evidence IDs,
samples heat capacity and conductivity over the declared interval, and applies
runtime range checks to every subsequent solver call. `BoundedRadialProperty`
does not replace the original callbacks with interpolated data. A finite sample
grid is only a preflight screen and does not certify intermediate temperatures or
the source material record.

A radiation boundary takes an effective irradiation temperature in `value` and
an emissivity-view-factor product in `coefficient`. The surface temperature is
found from the balance between radial conduction to the adjacent cell and
\[
Q_\mathrm{rad}=\epsilon_\mathrm{eff}\,\sigma A
\left(T_\mathrm{irr}^4-T_\mathrm{surface}^4\right),
\]
where SciPy supplies the Stefan–Boltzmann constant and a bracketed Brent solver
resolves the surface balance. The irradiation temperature represents caller
radiative surroundings; this API does not infer view factors, participating-gas
radiation, spectral properties, or flame geometry. See the
[SciPy constant table](https://docs.scipy.org/doc/scipy/reference/constants.html)
and [`brentq` documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html).

`temperature_k` has shape `(time, radial_cell)` at volume-centered radii.
`inner_surface_temperature_k` and `outer_surface_temperature_k` report face
temperatures; at a prescribed-temperature boundary this equals its input. The
energy residual is

\[
E(t)-E(0)-Q_\mathrm{inner}(t)-Q_\mathrm{outer}(t),
\]

where `stored_energy_j` is enthalpy relative to `reference_temperature_k`.
The immutable result record rechecks this identity against both cumulative boundary
heat ledgers and requires each integrated boundary heat history to start at zero.
Arrays are immutable. The native SciPy solution is retained for solver
diagnostics.

`RadialHeatIntegrationError` includes `cause` for property, boundary or post-solve
audit errors and `native_solution` when SciPy returned a partial/failed result.
An exception raised inside the RHS has no returned SciPy solution, so that field
is `None` and the triggering exception remains available as `cause`.

Use `result.thermoelastic_profile(i, reference_temperature_k=...,
profile_evidence_id=...)` to package a sampled wall state as a surface-bounded
`RadialTemperatureProfile`. It preserves both surface values along with the
cell-center temperatures for the separate thermoelastic calculation. The derived
profile ID automatically includes the parent history ID, sample index and physical
sample time; the supplied evidence ID is combined with the heat-history model identity.

For sequential pressure-to-stress composition, call
`result.thermoelastic_history(loads, geometry, elastic_material, radius_m, ...)`.
It requires one pressure load per heat sample and identical inner/outer cylinder radii.
It reuses the heat history's physical clock and returns
`RadialThermomechanicalHistory`, which retains both heat and stress histories. If a
static stress solve fails, `RadialThermomechanicalHistoryError` retains the thermal input,
failed sample index and completed stress prefix. This is a sequence of independent
static solves; it does not model inertia, creep or thermal/mechanical feedback.
The combined result also rechecks that the stress-history evidence matches the
composition evidence and that each generated temperature profile carries both the
thermal-model and stress-composition evidence IDs. This prevents a structurally valid
stress history from being detached from the heat history in a downstream Python handoff.
Call `RadialThermomechanicalHistory.require_current()` before downstream evaluation to
recheck original result/load/profile object identities and a fingerprint of the thermal
and stress arrays, geometry, material declarations and evidence. This result guard does
not observe mutable values hidden inside user callbacks and provides no scientific
qualification.

## Scope and validation

The model assumes an axisymmetric long-wall section, constant density, local
thermal equilibrium within each radial cell, no internal generation, no axial
or circumferential conduction, and no phase change. Conductivity and heat
capacity may vary with temperature. It does not infer a fluid-side coefficient,
wall-contact resistance, geometry, or material data. The corresponding
`finite-cylinder-radial-heat-transfer` case is registered for Nurion execution;
it has not been run. It covers net radiative heating and cooling at opposite
faces, as well as the adiabatic, flux, convection, steady-profile and mechanics
bridge paths. A passing authored conservation case would not establish measured
wall-temperature accuracy or vessel qualification.

The deferred case covers the adiabatic limit, prescribed heat input, convection
with temperature-dependent properties and a time-varying film coefficient, the
logarithmic steady profile, and clock/pressure coupling into the thermoelastic API.
Those invariants are authored requirements only until an authorized cluster run
is completed and its output is reviewed.

The separate `RadialThermoelasticStressHistory.require_current()` guard checks retained
pressure, material and profile identities plus the immutable stress outputs before a
downstream consumer uses them. It recomputes a content fingerprint to detect deliberate
post-construction array replacement or mutation. Its deferred radial thermoelastic case
also specifies rejection of an equal-valued output-array replacement and changed nested
temperature samples. This protects handoff integrity only; it does not recalculate stress
or supply independent physical validation.

`RadialHeatResult` is now issued only by the finite-cylinder solver. A caller cannot
construct or clone a result receipt to claim native integration. The result fingerprints
its reported arrays and retained solver/material/boundary identities; thermoelastic and
failure-history adapters check that receipt before consuming the sampled field. The
existing finite-cylinder deferred contract includes fabrication, cloning and post-issue
mutation checks. Callback internals remain caller-owned and are outside this identity
guard; no measured-material qualification is implied.
