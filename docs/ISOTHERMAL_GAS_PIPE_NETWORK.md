# Segmented isothermal gas-pipe inventory network

## Frozen-mixture extension and evidence boundary

Cells also accept the existing `CoolPropMixtureIsothermalEOS`. Every cell must
retain the same captured composition, component order, thermodynamic reference,
native backend/version and fixed temperature. Separate native owners are
allowed when their semantic definitions agree; owner pointers remain separately
guarded. Distinct composition identifiers are conservatively incompatible even
when their numerical mole fractions agree.

Inventories, boundary rates and link rates are total mixture masses. This level
does not solve species mixing or changing composition. It does not automatically
project hydrogen-only flow into a source, compressor or fuel-cell contract.
Hydrogen spin that is unresolved by the mixture declaration stays unresolved.
Molar mass is queried from the captured native mixture, without a local mixing
law. The existing mass ODE and shared Darcy links retain all phase, sonic,
definition and evidence gates.

The registered case is
`segmented-native-frozen-mixture-isothermal-pipe-network`. Focused native
property, hydraulic and definition guards have local evidence. The earlier
long three-level network process is no longer observable and its final outcome
was not collected; this case must not be marked passed. A fresh pinned campaign
must establish the full integration/refinement result. Qualified tables are not
yet admitted to these native cell/link types.

`IsothermalGasPipeNetwork` composes fixed-volume cell inventories with the
existing steady isothermal compressible Darcy link solver. Native cells use
`CoolPropIsothermalEOS` for density and pressure. The original explicit ideal
cell basis remains available for analytic numerical comparisons. Both paths
use the same mass ODE and inventory-floor events; no new wave solver is added.

## Native cells and network

```python
from fluids.friction import friction_factor
from h2physics.hydraulics import DarcyGeometry
from h2physics.isothermal_gas_pipe_network import (
    IsothermalGasPipeNetwork, IsothermalPipeCell, IsothermalPipeLink,
)
from h2physics.thermo import CoolPropIsothermalEOS, CoolPropProperties

cells = tuple(
    IsothermalPipeCell.from_pressure(
        cell_id=f"segment-{i}", volume_m3=0.05, temperature_k=300.0,
        pressure_pa=pressure, eos=CoolPropIsothermalEOS("Hydrogen"),
    )
    for i, pressure in enumerate((10.0e6, 9.9e6, 9.8e6))
)
# A declared representative native viscosity, then held constant per link.
viscosity = CoolPropProperties("Hydrogen").state_pt(9.9e6, 300.0).viscosity_pa_s
links = tuple(
    IsothermalPipeLink(f"link-{i}", DarcyGeometry(100.0, 0.02, 1.0e-6), viscosity)
    for i in range(2)
)
network = IsothermalGasPipeNetwork(cells, links, friction_factor, "installed-fluids-Darcy")
trace = network.simulate(
    boundary_mass_flow_kg_s=(0.0, 0.0, 0.0),
    boundary_evidence_ids=("closed-left", "closed-middle", "closed-right"),
    time_samples_s=(0.0, 0.01, 0.02),
    minimum_cell_mass_kg=1.0e-4,
    maximum_step_s=0.005,
)
trace.require_current()
```

These are authored scenario inputs. The optional `hydraulics` dependency
provides `fluids`; the `thermo` dependency provides CoolProp. The executable
native example is `examples/isothermal_gas_pipe_network.py`.

`from_pressure(..., eos=...)` requires an explicit direct HEOS owner and derives
initial mass and molar mass from native properties. A direct native constructor
can instead supply `initial_mass_kg=...` and `eos=...`; it can omit
`molecular_mass_kg_mol`, or provide a value that matches the native fluid.
`cell.pressure_for_mass(mass_kg)` evaluates the actual native pressure at the
cell's held temperature. `specific_gas_constant_j_kg_k` is `None` for native
cells because an ideal-gas constant is not their state closure.

Use canonical native fluid identifiers, including `Hydrogen`, `ParaHydrogen`
and `OrthoHydrogen`, consistently with the shared Darcy solver. Aliases such
as `H2` are rejected at cell construction in this level. Distinct EOS instances
are allowed across cells, but they must match actual fluid/spin, backend,
version, temperature, native molar mass and method definitions. Each cell also
retains its own EOS identity, native-state pointer and homogeneous-gas policy.
A network rejects mixed native/analytic cells and mismatched native bases.
Saturated, liquid, two-phase or unsupported native states are rejected.

## Explicit analytic reference

The existing positional constructor remains available:

```python
reference = IsothermalPipeCell("analytic-reference", 1.0, 300.0, 0.00201588, 4.0)
```

It requires the caller's explicit molecular mass and initial mass. Omitting
both an EOS and molecular mass is an error; there is no silent ideal fallback.
Reference cells use the analytic ideal-gas equation and must form a separate
network from native cells.

## Dynamics, signs and trace

Each link evaluates the shared steady pressure-driven closure at every ODE
trial. Positive link flow goes from cell i to i+1; swapping endpoint pressures
reverses its sign. Near-equal pressures within the explicit roundoff band
`1e-12 * max(p_left, p_right, 1 Pa)` give zero link flow. Finite pressure drops
use the shared native solver, including its whole-path phase and subsonic
checks. Invalid native paths propagate errors rather than substituting another
EOS, clipping flow or manufacturing a choked-flow result.

Positive signed external rates inject mass, negative rates withdraw it. The
rates are held over the requested interval. Intercell flows cancel in the
total network mass balance. `solve_ivp` advances the existing mass ODE and
localizes the first cell reaching `minimum_cell_mass_kg`. A terminal trace
contains the accepted output prefix and event state, `complete=False`, and
the responsible `terminal_cell_id`.

`maximum_step_s` limits the actual integrator step. `time_samples_s` selects
output samples and alone does not refine the numerical integration. The
existing BDF, Radau, RK45 and DOP853 choices remain available, with separate
relative and absolute mass tolerances.

The trace retains immutable time, mass, pressure and signed-flow arrays,
external-boundary evidence, the original network and per-cell `eos_identities`.
`require_current()` checks original issuance/content and retained definitions,
then replays native pressures, link flows and whole-network mass accounting.
Changed native methods, phase policy, state pointers, correlation definitions
or trace evidence invalidate it. Correlation parameters must remain fixed
during integration and later evidence replay.

## Physical scope

This is a segmented inventory model with quasi-steady links. It resolves
pressure and transferred mass but has no pipe momentum storage, acoustic
waves, local-loss elements, elevation, variable composition or first-law
energy state. Temperature is prescribed and held fixed; maintaining it
requires an external thermal-control model. Viscosity is supplied by the
caller and held constant per link, even when selected initially from CoolProp.
Pressure-dependent viscosity variation is not silently inferred. The validity
of that approximation and the selected Darcy correlation need application-
specific qualification over the operating range.

Use the existing isothermal/caloric wave models when momentum or wave dynamics
are required. These numerical checks do not qualify a pipeline or source
measurement set; independently licensed measured transient H2 data and its
observation mapping remain open research requirements.

## Executed local checks — 2026-11-01

The explicit-reference case `segmented-isothermal-gas-pipe-inventory-network`
passed with mass residual 2.00941964890e-15 kg and localized floor time
0.0100000069072 s. A cold process import of `h2physics` and this module passed.

The native case `segmented-native-CoolProp-isothermal-pipe-network` used
three 0.001 m3 cells at 300 K, initially 5.0/4.8/4.6 MPa, native HEOS Hydrogen,
10 m by 0.001 m Darcy links, and caller-held viscosity 8.9e-6 Pa s. Its actual
initial flows were 5.23903148700e-5 and 5.11839990832e-5 kg/s. Closed-network
mass residual was 1.73472347598e-18 kg and final pressures were
4,938,172.71473 / 4,800,841.07840 / 4,660,741.85032 Pa.

Actual RK45 maximum-step refinement 0.5 to 0.25 to 0.125 s reduced final-mass
successive differences from 1.61525523859e-12 to 4.93468113594e-14 kg. This
is numerical refinement, not measured-data agreement. Reverse, near-zero
(approximately 1.0824e-12 kg/s) and no-flow cases passed. A native floor event
was localized at 0.00100070960228 s. The final native regression passed
17 rejection checks for invalid or changed cell/network/EOS/phase/correlation/trace definitions.
Consult the current development record for the final frozen-source execution
checkpoint and remote replay status.
