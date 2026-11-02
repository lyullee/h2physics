# Native HyRAM+ jet-fire diagnostics

The actual HyRAM+6.1 `Flame` executes, including its source nozzle, notional
expansion, reacting flame integration and multisource radiation. The checked
cases **fail source-to-field fuel-origin mass, downstream conservation and
direct-EOS native caloric gates**. This is a diagnostic integration with default
rejection, not an accepted jet-fire prediction or a completed physical family.
The existing unignited Gaussian-jet failure remains unchanged and separate.

The optional adapter imports no HyRAM package at module import. Inject the actual
`hyram.phys.Fluid`, `Orifice`, `Flame` and
`hyram.phys._flame.calc_transmissivity` objects; no solver is copied into the host.
The installed engine is GPL-3.0-only. Native source, license, package metadata and
host/test/replay bytes are fingerprinted before and after the replay. Engine
source, coefficients, worked examples and experimental tables are not bundled
by these five files.

## Python use and physical ownership

```python
from hyram.phys import Fluid, Orifice, Flame
from hyram.phys._flame import calc_transmissivity
from h2physics.adapters.hyram_flame import run_hyram_flame, SteadyFlameWindow
from h2physics.core import Origin
from h2physics.release import NozzleOpening, SourceLocation
from h2physics.thermo.coolprop import CoolPropProperties

result = run_hyram_flame(
    fluid_factory=Fluid, orifice_factory=Orifice, flame_factory=Flame,
    transmissivity_function=calc_transmissivity,
    upstream=CoolPropProperties("Hydrogen").state_pt(2e6, 300.),
    ambient=CoolPropProperties("Air").state_pt(101325., 293.15),
    opening=NozzleOpening.circular(
        "authored-2mm", .002, effective_area_factor=.8,
        area_basis_id="native-Cd-times-geometric-area"),
    location=SourceLocation("authored-fire", "authored-incident", "global-xz",
                            (0., 2., 2.), (1., 0., 0.)),
    window=SteadyFlameWindow("operation-clock", 10., 20., "authored-source",
                             "fixed-reservoir-established-burning", Origin.SYNTHETIC),
    solver_options={"Smax": 30., "tol": 1e-7, "n_pts_integral": 300},
    require_accepted=False,  # explicit inspection of the known rejected result
)
native_flame = result.native
native_flow = native_flame.developing_flow.orifice_flow
```

The default `require_accepted=True` raises `HyRAMFlameAdmissibilityError`, whose
`result` and `native` retain the completed calculation and failed gates. Native
constructor failures propagate without inventing a completed candidate. Native
`Flame.solve` retains its output arrays but does not retain its SciPy `OdeResult`;
the adapter cannot supply the missing native status/history. Reaching the full
visible-length endpoint is checked explicitly.

Inputs are normal gaseous Hydrogen and Air at absolute Pa/K on matching native
density and enthalpy references, with reservoir pressure above twice ambient.
No ParaHydrogen or evolving spin/formation-reference conversion is inferred.
The input is an upstream reservoir: HyRAM owns the only choke and expansion
solve. An already evaluated shared-nozzle exit, prescribed `mdot`, substituted
developed flow or chemistry object cannot be passed through solver options.
This level is calm, unobstructed and two dimensional. Global x/y/z uses z upward;
the release direction lies in the x/z plane and its arbitrary global y offset
is retained in observer transformations. All geometry is in metres.

`SteadyFlameWindow` records absolute finite clock support, source data role and
the caller's evidence for a fixed established-burning source. It does not solve
ignition, source duration, blowdown, startup, isolation or event frequency. A
positive flow and full visible trajectory are required; zero flow is not silently
turned into a flame. No experimentally qualified P/T/orifice envelope is claimed;
the numerical cases cover2 and20MPa/300K with1 and2mm openings in ambient air.
Other inputs require their own mechanism, source and correlation assessment.

## Source, reacting-field and energy audits

`fuel_origin_section_flows` independently integrates `rho_prod(f)*f*v*2*pi*r`
over each actual native section, using the native f and velocity Gaussian widths
and actual reacting density. `f` includes hydrogen carried in product water and
is conserved fuel-origin material, whereas unburned H2 is consumed. The same
integrand appears in the native ODE's conserved mixture-fraction row.

The audit splits Gauss integration at native chemistry-table knots and uniform
radial panels. Default8B extent,32 panels and orders8/16 have a separate10B,
48-panel/order24 replay. Returned section flows are immutable kg/s arrays. They
are never renormalized to match source flow. `FlameAuditPolicy` exposes numerical
budgets and quadrature settings; changing a tolerance does not qualify a domain
or correct a failed field.

`centreline` columns are arclength_m, global_x_m, global_y_m, global_z_m,
velocity_m_s, width_m, angle_rad, mixture_fraction and native_temperature_K.
The native objects remain available for deep Python analysis. A signature of
the audited radiation-relevant fields rejects subsequent mutation before a
result-based radiation query. Editing native objects invalidates the evidence;
concurrent mutation is unsupported.

Throat and expanded-stream stagnation enthalpy plus kinetic energy are checked
against the declared source reference. Emitted native power is checked against
`Xrad * mdot * native_DHc`, with `0 < Xrad <= 1`. This power budget does not
establish energy closure of the reacting field. Multiplying fuel-origin flux
by DHc would likewise denote original fuel chemical potential, not residual
unburned-H2 power.

`combustion_caloric_audit` independently evaluates actual native pure-fluid EOS
enthalpies at the native product temperatures. Its nine columns are documented
in the function: f, T_K, released_heat_J_kg, native_MW_factor, reactant_h_J_kg,
product_h_J_kg, native_equation_residual_J_kg,
unscaled_reference_residual_J_kg and product_fuel_origin_fraction.
The acceptance gate checks the native as-defined caloric equation against direct
EOS evaluations. Its reactant enthalpy is multiplied by MWreactants/MWproducts
inside the native model. The unscaled mass-specific residual is diagnostic and
is not promoted to a replacement caloric convention. The independent pure-fluid
zeros are not established common species formation enthalpies.

The native chemistry table initializes at ambient temperature/pressure rather
than the cold expanded source. Its approximate `drhodf` differs from finite
differences of its actual `rho_prod`. Its100-point T interpolation also produces
direct-EOS caloric residuals. Radiation is a postprocessed correlation and does
not subtract heat from the adiabatic product-temperature field. These limitations
remain explicit; there is no invented radiatively cooled combustion solver.

## Radiation is diagnostic until the flame passes

Calling `result.irradiance` normally rejects an unaccepted flame. Explicit
`allow_rejected_flame=True` permits diagnostic native calculations:

```python
radiation = result.irradiance(
    [[0., 5., 2.], [1., 5., 2.]], relative_humidity=.5,
    minimum_source_distance_m=.1, number_of_sources=50,
    allow_rejected_flame=True,
)
assert radiation.status == "diagnostic-unaccepted-flame"
assert not radiation.accepted
```

`kernel_accepted` reports only finite/nonnegative scalar irradiance and
independent convex power/distance bounds. It cannot override `accepted=False`
from the underlying flame. `require_kernel_accepted` controls whether a failed
kernel raises an exception retaining its actual native flux array and result.
The native multisource calculation treats every emitter as independently facing
the observer. Its positive W/m2 output is incident scalar irradiance, not a
specified receiver-normal flux, absorbed heat, a signed equipment heat boundary,
flame impingement, reflection or a thermal-dose prediction.

Finite (n,3) observer positions, explicit positive emitter-exclusion distance,
integer source counts and an interior source-weight waist are required. Native
log-transmission requires0<RH<=1. All actual path transmissivities must lie
in[0,1]; unphysical values and emitter singularities are rejected without clipping.
Source-facing symmetry, global translations, far-field attenuated inverse-square
power and source-count refinement are checks of the actual radiation call.

## Reproduce and continue

Run `python scripts/check_hyram_flame.py --hyram-packages artifacts/native_hyram_packages`.
The script writes research/native_jet_fire.md and deliberately exits1 while
physical acceptance fails. `--use-main-scipy` selects the already installed main
SciPy before adding HyRAM's separate target; its result must be rerun and recorded.
Tests use actual native classes and test the retained rejection, independent
quadrature/energy checks and API guards. No artificial Flame/field is used as
verification evidence. The report distinguishes diagnostic verification gates
from physical acceptance and independent measured validation, which has not been
performed. No facility heat source or family-level acceptance follows from this
diagnostic checkpoint.

The scoped24-test suite was executed with the separate SciPy1.16.3 target and
with main SciPy1.18.1; both passed. Passing these tests verifies the diagnostic
contracts and expected rejection, and does not turn the native physical gates
into passes.

Primary sources are the [official6.1 release/manual index](https://hyram.sandia.gov/),
the [6.0 technical reference](https://doi.org/10.2172/2563814),
[Ekoto et al., buoyant jet-flame radiation](https://doi.org/10.1016/j.ijhydene.2014.03.235),
and [public native API/source and license](https://github.com/sandialabs/hyram).
The installed version, exact native/source/host hashes and retained failures
define this replay; literature validation does not replace a local measured
comparison of this adapter and its inputs.
