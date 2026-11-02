# Radial-temperature thermoelastic cylinder reference

Status: **implemented_unverified**. This module adds a radial thermal gradient
to the existing long-cylinder pressure and uniform-temperature references. No
local numerical solve was performed. A source-bound case is authored for later
Nurion execution.

`h2physics.materials.radial_thermoelastic` accepts a caller-owned set of absolute
wall temperatures at increasing radius coordinates. A non-extrapolating PCHIP
defines the in-wall profile. The model assumes a homogeneous, isotropic,
small-strain, linearly elastic long cylinder with constant properties, no body
force, axisymmetric static loading, and uniform axial strain. It solves for the
radial displacement with SciPy's two-point boundary value solver. Internal and
external surface tractions are the negative of the supplied absolute pressures.

For displacement `u(r)`, axial strain `epsilon_z`, and temperature difference
`Delta T(r)`, the isotropic constitutive law is represented with the Lamé moduli
`lambda`, `mu`, bulk modulus `K`, and expansion coefficient `alpha`. Radial
equilibrium reduces to

```text
u'' + u'/r - u/r^2 = 3 K alpha / (lambda + 2 mu) * dT/dr
```

The solver applies the constitutive stresses at both radial boundaries. In the
free axial mode, a constant axial strain is solved together with the displacement
so the axial stress resultant matches the pressure thrust for closed ends and
zero for open ends. In the fixed mode, axial strain is zero and the net axial
support reaction is returned. The result includes its adaptive-solver residual,
iteration count, geometry, load, material and source profile.

The governing axisymmetric equilibrium, radial/hoop kinematics, pressure boundary
conditions and radial-temperature problem class are independently documented in
NASA TM 102320, available from the [NASA Technical Reports Server](https://ntrs.nasa.gov/api/citations/19900003634/downloads/19900003634.pdf).
That report treats transverse isotropy; this module uses a separate reduction of
the isotropic small-strain constitutive equations and does not copy its solution
or implementation. The radial interpolation and numerical BVP are original API
choices for caller-supplied material data.

The implementation does not resolve finite-length end transitions, axial
temperature variation, local nozzles/supports, pressure transients, plasticity,
creep, residual stress, temperature-dependent properties, nonlinear material
response, fracture initiation, or code qualification. PCHIP smooths the supplied
radial samples under an explicit interpolation choice; it does not add spatial
measurement resolution or establish thermal conduction history. A converged BVP
is numerical evidence for the equations only, not vessel validation.

## Ordered quasi-static load snapshots

`radial_thermoelastic_history` applies the static boundary-value calculation to a
user-supplied sequence of pressure loads and radial temperature profiles. All samples
share one physical clock, material, geometry, axial restraint and temperature reference.
The output retains each source input and stores stresses by `(time, radius)`. No thermal
diffusion, structural transient, interpolation between load samples or extremum search is
performed. If one boundary-value solve fails, the exception records the failed sample
index and preceding completed fields so a batch driver can diagnose the partial result.
This history interface is an orchestration layer over the existing static model; it does
not introduce a second stress equation or imply a transient vessel-integrity assessment.
The history also preserves each static solve's BVP iteration count. For a downstream
consumer needing one exact-time field, `history.stress_field_at(index)` returns a typed
`RadialThermoelasticStressSample` linked to the source history, pressure load, temperature
profile, clock coordinate and solver diagnostics. The integer index selects only an
existing sample; no unobserved time is reconstructed. `sample.require_current()` checks
that the source history and returned field still match.
