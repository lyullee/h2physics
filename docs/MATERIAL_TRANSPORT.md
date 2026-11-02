# Material hydrogen transport interfaces

## Prescribed hydrostatic-stress drift — implementation only

`HydrostaticStressPotential` adds the previously absent stress-gradient term
to the existing `DiffusionDomain` finite-volume owner. Pass it as
`simulate(..., stress_potential=...)`; `DiffusionSlab`, `HydrogenDiffusionShell`
and `AxialAnnulusDiffusion` forward the same optional keyword. No test, model
calculation or numerical replay was run for this addition. It is
**implemented_unverified**.

The dilute solid closure is `mu = mu0 + R*T*ln(c) - V_H*sigma_h`, hence
`J = -D*(grad(c) - c*V_H*grad(sigma_h)/(R*T))` at spatially uniform T and V_H.
Here `sigma_h` is the arithmetic mean of the three normal stresses, with
tension positive; it is not positive-compressive pressure or the stress trace.
The partial molar volume is per mole of the exact mobile `HydrogenCarrier`
(H or H2), with no automatic factor of two. Both the stress callback and its
material molar volume are caller supplied. No material coefficients are defaults.
See the primary studies on
[stress and hydrogen chemical potential](https://doi.org/10.1016/0001-6160(71)90054-X)
and [stress-dependent hydrogen transport](https://www.sciencedirect.com/science/article/pii/S0925838816326901).

The stress callback receives `(time_s, positions_m)` and returns Pa at the two
material surfaces plus each cell center. Positions are immutable. The declared
`clock_id` refers to the same seconds/origin as the diffusion simulation; no
clock conversion is inferred. Material temperature bounds, stress-field identity,
volume-parameter evidence and origin are mandatory. The actual stress object is
retained on `TransportResult.stress_potential`. Arbitrary callback hidden state
and its physical applicability remain caller responsibilities.

```python
from h2physics.materials import HydrostaticStressPotential

stress = HydrostaticStressPotential(
    carrier=carrier,
    hydrostatic_stress_pa=prescribed_mean_stress,
    partial_molar_volume_m3_mol=material_partial_molar_volume,
    temperature_domain_k=material_temperature_bounds,
    stress_field_id=stress_source_id,
    partial_molar_volume_evidence_id=volume_source_id,
    clock_id=operation_clock_id,
    origin=parameter_origin,
)
result = domain.simulate(
    output_times, initial_mobile,
    boundary=surface_conditions,
    temperature_k=prescribed_temperature,
    stress_potential=stress,
)
```

Each interface uses its existing integrated geometric conductance `G` and a
potential jump `dpsi`, where `psi = V_H*sigma_h/(R*T)`. Exponential fitting gives
`Q = D*G*(B(-dpsi)*c_left - B(dpsi)*c_right)`, with `B(x)=x/(exp(x)-1)`.
Potential is piecewise linear in the geometric-resistance coordinate across
each segment, not necessarily linear in physical radius. The small-jump series
and separate large-positive/negative formulas avoid direct exponential overflow;
unrepresentable potentials, coefficients or flows reject rather than clip.
This scheme is an implementation choice, not an experimentally qualified law.

With zero stress difference, the original Fick and film path is used. With
nonzero differences, existing surface concentration or finite-inventory states
remain solid-basis concentrations. Linear surface films are eliminated
algebraically against the fitted half-cell equation; zero film transfer gives
zero transfer. Prescribed flux boundaries retain their supplied sign and value.
The same extensive face rates update adjacent cells, the surface reservoirs and
both boundary integrals. Trap kinetics keep their existing law. No second
integration or source ledger is introduced.

The algebra has the zero-flux equilibrium `c_right/c_left = exp(dpsi)` and a
positive drift toward increasing tensile mean stress for positive V_H. These
are derivation targets for later numerical checks, not observed test results.
This is one-way prescribed stress: no stress solver, swelling feedback,
plasticity, changing trap density, non-dilute activity, thermal diffusion or
fluid EOS is added. Fluid-side fugacity/property owners remain CoolProp-based.

`DiffusionMesh.cylindrical_shell(inner_radius_m, outer_radius_m, length_m, cells)`
adds radial-only transport through a finite-length hollow cylinder to the shared
mobile/trap finite-volume solver. The radial face area is `2*pi*r*L`, the shell
inventory uses the exact annular volume, and each face-to-center conductance uses
the integrated cylindrical resistance. It therefore resolves curvature that a
flat slab approximation omits, while retaining the same material transport law.
End-face fluxes and axial gradients are excluded. Prescribed stress drift is
available only through the explicit optional potential described above. A
constant-d steady logarithmic-profile and inventory contract is registered for
Nurion; it has not been run and does not validate material coefficients.

`HydrogenDiffusionShell` is the public device-geometry facade over the shared
finite-volume solver. Select `geometry="cylindrical"` with an explicit positive
`length_m`, or `geometry="spherical"` with no length. Both modes require inner
and outer radii, a cell count, an explicit hydrogen carrier, and a caller-owned
diffusivity callback. The facade forwards trap parameters, boundary conditions,
temperature, finite surface inventories, and solver tolerances to
`DiffusionDomain`; it does not implement another diffusion law. Results retain
whole-shell inventory in mol and face transfer in mol/s, unlike `DiffusionSlab`'s
unit-area mol/m² contract. A Hangang-discoverable
`radial-hydrogen-diffusion-shell-api` case records the geometry and ledger
contract; it is deferred and has not been run. Both geometries are radial-only:
cylindrical end faces, axial gradients, stress feedback, and heat transfer remain
outside the API. The wrapper does not qualify material coefficients or model
applicability.

`AxialAnnulusDiffusion` represents axial transport through a constant-section
annulus. It computes `A = pi * (ro - ri) * (ro + ri)` and delegates the mesh to
`DiffusionMesh.planar(length_m, cells, area_m2=A)`; its `DiffusionDomain`
integration is shared with the other one-dimensional material models. Cell
volumes are `A * dz`, and every axial face uses area `A`. The explicit carrier,
diffusivity callback and trap tuple remain on the facade and are forwarded to
the shared owner. This is an axial-only approximation: it has no radial
gradient, r-z coupling, variable section, heat/stress feedback, or material
qualification. Supply and retain applicable material-property evidence in the
calling application. The metadata contract
`axial-annulus-diffusion-geometry-contract` checks geometry and API lineage only;
it does not run diffusion or qualify physical performance.

Finite-volume face integrals use the positive left-to-right coordinate at both
faces. A positive left-face integral enters the wall from its inner/left boundary;
a positive right-face integral exits the wall at its outer/right boundary. The
net wall inventory change is left-face inflow minus right-face outflow. Thus a
steady shell gradient from higher inner concentration to lower outer concentration
has positive integrals at both faces; the right-face ledger is not signed as
inward-to-the-wall.

An accepted planar slab diffusion result can feed the shared finite-source API
through [DIFFUSION_FINITE_SOURCE_HANDOFF.md](DIFFUSION_FINITE_SOURCE_HANDOFF.md).
That boundary conversion requires an explicit membrane area, clock alignment,
product-state projection, and atomic-H recombination evidence when applicable.
It conserves only the signed species mass crossing the right face; no gas-state
energy equation or downstream discharge is added.
`DiffusionDomain.simulate()` issues a `TransportResult` tied to the original
successful SciPy integration. Its public concentration fields and inventory/face
ledgers must still reproduce that native state when `require_current()` is called;
altering one projected field invalidates the result rather than silently detaching
it from the integration receipt. This guards result lineage only and does not validate
the numerical solver or constitutive inputs.

`DiffusionMesh.steady_concentration_profile_mol_m3()` returns the constant-
diffusivity steady solution at the mesh cell centers using those same integrated
face resistances. Pair it with `steady_transport_rate_mol_s()` for an analytic
profile/rate reference or to initialize a transient run. The returned profile is
read-only. Temperature-dependent diffusivity, traps, finite boundary inventories,
and transient lag are not represented by this steady solution; callers must retain
their own material and boundary evidence. Resistance or output values outside
floating-point range are rejected rather than returned as nonfinite results.

`PowerLawSolubilityBoundary` connects the existing `PowerLawSolubility` parameter
model to `DiffusionSlab` or `DiffusionDomain`. Pass it as the diffusion
`boundary`; at each solver right-hand-side evaluation, it receives the exact time
and the same spatially uniform temperature already used by the bulk diffusivity
callback. It converts the caller-provided upstream and downstream hydrogen
fugacities to molar concentrations of the declared carrier and supplies those as
Dirichlet surface conditions. Time-varying fugacity callbacks are supported.

This object expresses a caller-selected local-equilibrium surface mapping. It
does not add adsorption kinetics, a surface resistance, dissociation/recombination,
fugacity estimation, or a gas-side boundary model. The solubility carrier must
match the diffusion carrier. An evidence identity is required for the caller's
surface-equilibrium mapping.

The transport layer still requires material-specific solubility, diffusivity,
trap-capacity and kinetic parameters from an applicable source. The current
embrittlement compilation reports hydrogen content and mechanical outcomes but
does not establish a matched solubility/diffusivity parameter set for a specific
material heat and surface condition. No such coefficients are inferred or
bundled here. The deferred contract
`power-law-solubility-diffusion-boundary` checks the interface mapping and carrier
mismatch rejection; it remains unexecuted. Its synthetic coefficients verify
API arithmetic only.

`quasi_steady_permeation_history()` evaluates the existing planar steady-flux
relation at each caller-supplied temperature and pair of surface fugacities. It
uses a common strictly increasing clock and integrates signed hydrogen mass flux
by trapezoidal quadrature, reporting cumulative mass per unit membrane area. A
diffusivity may be a constant or a temperature callback. The caller must retain
separate evidence for the surface mapping and for treating the history as
quasi-steady. This utility does not solve transient bulk diffusion, infer whether
the membrane can track the boundary, include a surface resistance, or estimate
whole-component throughput without an independently specified area. Its deferred
`quasi-steady-permeation-history` contract is unexecuted; synthetic values only
exercise arithmetic and basis checks.

`steady_permeation_with_surface_resistance()` adds a bounded steady level for
two caller-specified linear surface-transfer films in series with planar bulk
diffusion. It first maps each H2 fugacity into the declared mobile-entity
concentration using `PowerLawSolubility`, then computes
`J = (c_up - c_down) / (1/h_up + L/D + 1/h_down)`. Here `h` is a transfer
velocity in m/s, `L/D` is the bulk resistance, and every term is on one
solid-basis concentration potential. The result retains both boundary
concentrations, both membrane-side concentrations, all three resistances and
separate evidence IDs for the boundary mapping and surface-transfer values.
This is a linear engineering closure; it does not resolve adsorption,
dissociation, recombination, oxide state or nonlinear surface kinetics. A
caller must supply applicable transfer coefficients and qualification evidence.
The physical distinction between bulk diffusion and surface-controlled
permeation is supported by [Shu and Watanabe (1997)](https://doi.org/10.1103/PhysRevB.55.9348);
the resistance expression here follows from the declared linear film law,
steady flux continuity and Fickian bulk relation. The deferred synthetic
`steady-permeation-surface-resistance` case has not been run and does not qualify
material properties.

For time-dependent bulk diffusion, `PowerLawSolubilityFilmBoundary` combines
fugacity histories, the same declared equilibrium solubility map, and separate
left/right film transfer velocities. Pass it directly as the finite-volume
boundary; the solver's current temperature is used for both the solubility
coefficient and film callbacks. This retains finite diffusion lag and the
existing film-to-cell resistance calculation without inventing gas-side
kinetics. The `transient-fugacity-driven-surface-films` deferred contract covers
callback timing, carrier mapping and evidence lineage only. It has not been
executed and does not qualify any material or transfer coefficient.

## Source-bound normalized permeation observations

The version-1 Mendeley record [Hydrogen diffusivity in MS1700 and QP1180 AHSS](https://doi.org/10.17632/zj7zh24frt.1)
provides a CC BY 4.0 MAT attachment and a publisher SHA-256. Its variables
`Msdata` and `QPdata` are preserved by
`h2physics.data.load_mendeley_normalized_permeation()` after the resolved `Dataset`
metadata, attachment-list bytes, filename, size and file hash agree with the pinned
record. `MendeleyPermeationDataset` retains the DOI, version, contributors, measured
origin and CC BY 4.0 identity. SciPy is imported lazily when this loader is called.

```python
from pathlib import Path

from h2physics.data import DATASETS, load_mendeley_normalized_permeation, resolve_dataset

seed = next(item for item in DATASETS
            if item.key == "hydrogen-diffusivity-ms1700-qp1180")
source = resolve_dataset(seed)
observations = load_mendeley_normalized_permeation(
    Path("data/raw/hydrogen-diffusivity-ms1700-qp1180/1/MS1700_QP1180_permeation.mat"),
    dataset=source,
)
ms1700 = observations.for_grade("MS1700")
time_coordinate = ms1700.normalized_time_s_m2
flux_coordinate = ms1700.normalized_flux
```

The reader leaves row order and both coordinate columns unchanged. The first
coordinate retains the publisher's stated s/m² scale; the second is only labeled
normalized flux because a dimensional unit is not established by the available
record. The normalization formula, specimen thickness basis, and conversion to an
effective diffusivity require independent source evidence. This dataset does not
currently parameterize `PowerLawSolubility`, `DiffusionSlab`, or the trap solver.
The raw file remains outside the source distribution under ignored `data/raw` and
must be staged explicitly for the deferred
`mendeley-ms1700-qp1180-normalized-permeation-ingest`
Nurion contract. This checks data lineage and reader behavior only; it is not a
material-property or model validation.

The separate [MS AHSS grade 1300 record](https://doi.org/10.17632/tnsgf7v76z.1)
contains measured time/current traces, not normalized MAT coordinates. Its source-
bound reader is `h2physics.data.load_ahss1300_permeation()`. Both worksheets have
row-1 headers and material label E3; original observations span rows 2 through 1261
and 2 through 600, retaining 1,260 and 599 numeric pairs and their source row IDs.
The original UTF-8 workbook XML and parsed cells contain Greek mu (U+03BC),
unambiguously identifying microampere. Earlier console rendering obscured this
character. `current_unit` returns `"uA"`; `current_ampere(sheet_name)` returns
immutable current in A using the exact factor 1e-6. `observations(sheet_name)`
retains the original seconds/current pairs.

The pinned publisher metadata reports a 50 by 50 by 1.2 mm specimen, Pd on the
anodic face and 0.1 M NaOH; the workbook reports 293 K. Specimen planform is not
verified exposed electrode area. Exposed area, entry boundary history and initial
concentration profile remain unresolved; cathodic current is not absorbed atomic-H
flux without an independently justified efficiency. Do not feed measured current
directly to `DiffusionSlab` or the cylindrical transport-to-eigenstrain adapter.
No diffusivity, trap law or material qualification follows from this intake.

The `mendeley-ahss1300-source-bound-observations` contract passed locally on the
exact acquired 88,885-byte workbook, SHA-256
`117d75a3f8329456732beada95b8f2be8bda688da88e6b8c7c83a9ee49698b3b`.
It checks both source clocks/row IDs, SI current conversion, altered publisher
receipts, changed bytes, immutable observations and stale-result rejection. Five
additional parser checks reject a changed second-sheet header, missing material
label, extra column, numeric-string observation and duplicate time. These use
private in-memory workbook views; production intake verifies original bytes first.
This is source ingestion evidence, not measured diffusion-model validation.
For offline replay, stage the three checksummed cache files under one directory and
set `H2_AHSS1300_SOURCE_DIR` to that path; this case makes no network request.
