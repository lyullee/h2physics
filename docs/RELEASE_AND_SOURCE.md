# Shared nozzle and native inventory coupling

## Model and boundary

`h2physics.release.HomogeneousIsentropicNozzle` is one implementation for gas, liquid,
saturated and equilibrium two-phase reservoir states. The supplied state is stagnation
state: a stationary reservoir with negligible inlet kinetic energy. A moving pipe's static
state requires a separate stagnation-state closure before this interface is applicable.

For every pressure between the specified back pressure and reservoir pressure, the injected
provider evaluates the state at the reservoir entropy. Steady adiabatic energy conservation
gives velocity `sqrt(2 * (h0 - h))`; continuity gives mass flux `rho * velocity`. The maximum
admissible flux determines the ideal short-nozzle result. A maximum at back pressure is
back-pressure limited; an interior maximum is choked. This avoids assigning a fixed critical
pressure ratio to real or two-phase hydrogen. Reverse pressure produces zero forward flow;
the model does not simulate a reverse-flow stream.

The assumptions are homogeneous instantaneous thermal equilibrium, equal phase velocities,
adiabatic flow and negligible friction. The method cannot represent delayed flashing,
metastability, separated phase velocities, long transfer lines or an external underexpanded
jet. The three catalog release families use this same kernel. Higher-fidelity alternatives
should be added only when their additional physics and evidence justify a separate level.

The implementation is original. Analytical ideal-gas verification uses
[NASA Glenn mass-flow relations](https://www.grc.nasa.gov/www/k-12/airplane/mflchk.html).
Saturation input meanings and phase limits follow the selected provider, including
[CoolProp's documented state inputs](https://coolprop.org/coolprop/HighLevelAPI.html).
No external solver source or mechanism is included in this module.

## Native Python example

```python
from h2physics.thermo import CoolPropProperties
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

properties = CoolPropProperties("ParaHydrogen")
upstream = properties.saturated(500_000., vapor_mass_fraction=0.2)
opening = NozzleOpening.circular(
    "tank-A/outlet-1", 0.002,
    effective_area_factor=0.8,
    area_basis_id="user-specified-effective-area-assumption",
)
result = HomogeneousIsentropicNozzle(properties).solve(
    upstream, back_pressure_pa=101_325., opening=opening,
)
print(result.regime, result.mass_flow_kg_s, result.exit_state)
print(result.energy_residual_w, result.diagnostics)
```

All pressures are absolute Pa; lengths are m and all flow/energy outputs use SI. The
effective area is nominal area × factor × opening fraction. The factor is explicit and
must lie in `(0, 1]`; no nominal discharge coefficient is silently supplied. Treating an
empirical mass-flow coefficient as an area reduction also assumes an exit area. It does
not separately identify contraction and velocity losses. `effective_area_thrust_n` is
momentum plus pressure force under that declared area closure, not an independently
measured thrust or a qualified external-jet source. A different momentum closure needs
its own evidence and downstream adapter.

The exit state's quality, when defined by the EOS, describes vapor mass at the solved
nozzle plane. It is not atmospheric quality and is not ground-reaching liquid. A gas or
supercritical state may have no quality field; this is not replaced with an arbitrary
zero or one. `MassPartition` is deliberately not constructed: droplet flight, flash,
impact, evaporation and ground transfer remain separate responsibilities.

## Search and failure behavior

`NozzleSearch` controls grid size/refinement, relative flux/pressure convergence, upstream
state consistency and a small absolute enthalpy roundoff allowance. Pressure endpoints
are included on a logarithmic grid. Every sampled interior local maximum and locally maximal
boundary cell is refined. A consistent single-phase provider with sound speed allows the
equivalent sonic root `v²=a²` to be bracketed with SciPy brentq; candidate flux consistency
is checked. Brackets without that optional property use bounded optimization in a local
coordinate centered on zero. Two-phase sound speed is not invented. A finer grid must reproduce
the selected maximum. This also resolves an interior peak within the first cell near the
choking transition. A maximum indistinguishable from the back endpoint within both declared
flux and pressure tolerances is reported as back-pressure limited at that numerical resolution.
Diagnostics retain property evaluation count, refinement count, both convergence errors,
sonic-refinement count and tiny enthalpy/quality adjustments within their declared allowances.
Data-driven flat-peak failures and the unchanged-gate numerical corrections are documented
in `research/nozzle_search_coordinates.md`.

CoolProp's strict default rejects quality outside [0, 1]. At a phase boundary, a numerical
flash may return a fraction only slightly outside that range. An explicit provider option,
`quality_roundoff_tolerance=1e-8`, can permit that bounded endpoint adjustment; the raw
value remains in `ThermoState.raw_vapor_mass_fraction` and the maximum adjustment is reported
by the nozzle. The default budget is zero and larger violations fail. No enthalpy/density
value is changed. This numerical policy does not justify extrapolation or delayed flashing.

The upstream state is checked by an independent pressure/entropy flash. Incompatible
fluid/spin/reference identities, bad flashes, inconsistent path pressure or entropy,
large negative enthalpy drops and failed optimization/refinement raise errors. EOS-domain
holes are not skipped to produce an apparently successful answer. Discrete refinement
cannot prove that no unresolved narrow maximum exists. Independent physical validation
also remains separate from numerical convergence. Tabular backends may be injected only
after qualifying the actual phase/path domain and resulting discharge errors; existing
warm PT/PH/PS table evidence does not qualify cryogenic discharge.

## Energy and histories

Reservoir withdrawal energy is `mass_flow * upstream_stagnation.enthalpy`. At the nozzle
it equals static enthalpy flow plus kinetic power; `energy_residual_w` exposes the balance.
Removing only exit static enthalpy from a tank would omit the kinetic-energy contribution.
Energy signs still depend on the declared thermodynamic reference and can be negative.

`SourceLocation` retains source and clock identities, coordinate-frame identity, a position
and an already normalized direction. `SourceHistory` holds immutable matching time/result
tuples, a common opening/model/property basis and a declared end reason. It provides a
read-only predicted mass-flow `TimeSeries`. No interpolation rule is implied. Use separate
windows for discontinuities; do not feed Runge–Kutta trial or rejected states to consumers.
An isolation endpoint must be a closed sample and a pressure-equalized endpoint must have
no forward pressure. An inventory-limit label is caller supplied and does not implement
a depletion event detector or certify that a physical inventory limit was reached.
`SourceHistory.interval_mass_projection()` requires nonblank quadrature and representative-
state evidence IDs even when constructing `NozzleSourceProjection` directly. The receipt
retains the selected interpolation rule, sample/interval mass and energy ledgers, and the
representative-state discrepancy; it does not infer a thermodynamic state or correct a
native source mismatch.

## Actual LH2DT coupling

`adapters.lh2dt.Lh2dtBulkNozzleOutflow` accepts the shared nozzle, opening, a scalar or
native Python back-pressure callable, a scalar or opening-fraction callable and the actual
native `MassEnergyFlow` factory. Its `sample(t, native_state)` returns a `NozzleResult`;
calling it returns native negative flow objects for `HomogeneousTank.simulate`.

The reviewed LH2DT revision forces all negative flow enthalpy to the homogeneous tank
enthalpy. Consequently this adapter supports **bulk-mixture withdrawal only**. It cannot
represent a vapor relief port or liquid dip tube merely by changing the supplied flow
enthalpy. Request 001 specifies the required receiving change. The caller must map the
actual native provider's fluid/spin/energy reference to `Lh2dtProperties`; native state
objects themselves do not yet carry that complete identity.

The callback does not store a history: the native integrator invokes it for intermediate
and possibly rejected stages. Sample accepted states afterward. A discontinuous command
is integrated as separate windows with a fixed one-sided boundary command within each
window. Sampling a step command directly inside RK4 at the endpoint can contaminate the
preceding window. The demonstration verifies zero post-isolation boundary mass this way.

Run `scripts/check_release_integration.py` with the exact optional LH2DT snapshot described
in HANDOFF.md. The generated `research/native_release.md` reports warm-gas and equilibrium
cryogenic bulk outflow, native mass/energy ledgers, source energy closure and independent
accepted-node quadrature under time-step refinement. These are synthetic numerical checks.
No measured discharge coefficient, full tank-emptying event, phase-selective withdrawal,
atmospheric jet, ground fraction or independent discharge qualification is implied.

## Consolidation with existing repositories

PRISM's reviewed HEM implementation already uses the same physical level but accepts
upstream pressure/temperature and searches interior pressures. Request 006 proposes
delegating that HEM path to this shared kernel through an injected Python protocol, retaining
PRISM's public result compatibility. The local implementation addresses phase-explicit
input, back-pressure endpoints, EOS failure visibility and convergence diagnostics. Existing
nonequilibrium models remain a distinct optional physical level pending source-specific
qualification. Other repositories were not edited or messaged.
