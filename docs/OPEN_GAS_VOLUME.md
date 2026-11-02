# Native open finite gas volume

`h2physics.adapters.cantera_volume.CanteraOpenGasVolume` is a constant-volume,
well-mixed, nonreacting thermodynamic reference level. It resolves finite gas
mass, composition, temperature, pressure and internal energy under prescribed
inlets, outward extraction and wall heat. This differs from the existing closed
`CanteraGas.closed_reactor`: mass and species cross actual native flow devices.

Cantera 3.2 owns the ideal-gas mixture EOS, species thermochemistry, physical
reactor equations and CVODES integration. Actual native `Reservoir`,
`MassFlowController`, stationary `Wall`, `ExtensibleIdealGasReactor` and
`ReactorNet` objects are retained at `trace.native`. The adapter appends boundary
integrals through documented extension hooks; it never overwrites the native
physical state derivatives or implements another reactor, choking or EOS solver.

This level supplies a finite thermodynamic control volume, with no layers,
spatial concentration or entrainment. HyRAM+ remains the preferred provider for
high-pressure gaseous-hydrogen dispersion and SLABx-LH2 for LH2-origin dispersion.
A successful well-mixed inventory calculation does not qualify a spatial
dispersion, enclosure explosion or thermal-stratification prediction.

## Python composition

Install the optional chemistry extra and use a reviewed mechanism outside the
repository. The phase factory must return fresh native ideal-gas Solutions with
zero reactions and identical species ordering, thermochemistry and molecular
data. The caller declares mechanism identity, source hash, rights, primary
references and an absolute-pressure/temperature envelope in `MechanismBasis`.
Native species fit bounds are also enforced. These records declare provenance;
the adapter cannot establish rights or scientific suitability from a filename.

This original verification example uses separately installed species data.
Mechanism text is read into Python to avoid a native Windows Unicode-path issue;
it is never copied into the repository or distribution.

```python
import hashlib
from pathlib import Path

import cantera as ct

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.cantera_volume import (
    CanteraOpenGasVolume, GasBoundaryRate, GasFeed, GasHeatBoundary, GasVent,
)
from h2physics.core import Origin

raw = (Path(ct.__file__).parent / "data/h2o2.yaml").read_bytes()
basis = MechanismBasis(
    f"Cantera:{ct.__version__}:h2o2:H2-N2-frozen-subset",
    hashlib.sha256(raw).hexdigest(),
    "Cantera-BSD-3-Clause; upstream GRI-Mech species provenance",
    ("https://cantera.org/3.2/examples/input/h2o2.html",),
    310., 1200., 2e4, 5e5,
)

def phase_factory():
    donor = ct.Solution(yaml=raw.decode("utf-8"), name="ohmech")
    return ct.Solution(
        thermo="ideal-gas", kinetics=None,
        species=[donor.species("H2"), donor.species("N2")],
    )

clock = "authored-operation-clock"
initial = ReactiveState(400., 101325., {"N2": 1.})
source = ReactiveState(420., 101325., {"H2": 1.})
sink = ReactiveState(400., 101325., {"N2": 1.})

feed_rate = GasBoundaryRate(
    "feed", clock, 100., 102., lambda t, phase: .001*(1+.5*(t-100.)),
    Origin.SYNTHETIC, "original-positive-source-case",
)
vent_rate = GasBoundaryRate(
    "extraction", clock, 100., 102., lambda t, phase: .0004,
    Origin.SYNTHETIC, "original-prescribed-extraction-case",
)
wall = GasHeatBoundary(
    "external-wall", clock, 100., 102.,
    ReactiveState(450., 101325., {"N2": 1.}),
    area_m2=1., heat_transfer_coefficient_w_m2_k=2.,
    heat_flux_w_m2=lambda t: 5.,
)
trace = CanteraOpenGasVolume(phase_factory, basis).run(
    initial, [100., 100.5, 101.], volume_m3=.5, clock_id=clock,
    feeds=(GasFeed(feed_rate, source),),
    vents=(GasVent(vent_rate, sink),), heat_boundaries=(wall,),
    maximum_time_step_s=.01,
)
last = trace.snapshots[-1]
print(last.mass_kg, last.temperature_k, last.pressure_pa)
print(last.mass_fractions["H2"], trace.energy_residual_j)
```

Inputs and outputs use kg, s, m³, K, Pa absolute, J and W. Source and sink states
use explicit species mole fractions summing to one. Snapshots expose both mass
and mole fractions with named species. H2 is the selected mechanism's
spin-unresolved molecular species; this level does not assert normal/para/ortho
thermochemistry or translate a CoolProp sensible-energy zero. Native formation
energy is retained consistently across all reservoirs and the volume.

Every feed reservoir has fixed temperature, pressure and composition within one
run. Rate callbacks receive `(absolute_time_s, native_volume_phase)` and can vary
continuously. They must treat the phase as read-only; state, basis and
thermochemistry changes are rejected. Factories, actual boundaries and native
results remain accessible for deeper composition. Editing native objects after
a run invalidates the recorded trace as a description of those edited objects.

An inlet MFC is a prescribed source: it supplies the requested mass independent
of the pressure difference. A vent MFC likewise removes a prescribed magnitude
with the current well-mixed upstream composition and enthalpy. These devices do
not predict an upstream finite supply or the work needed to establish the rate.
`GasVent.downstream_state` is explicit sink metadata and a native reservoir;
its pressure alone is not a hydraulic closure. Outward flow must already be a
nonnegative magnitude. Reverse transfer requires a separately declared inlet.

## Clock and history guards

`GasBoundaryRate` requires a boundary ID, clock ID, finite support endpoints,
callback, resolved `Origin` and source identity. Every mass/heat boundary must
use the operation clock; a second recorder clock is not silently aligned.
Callbacks are required to be continuous within the run window. This level does
not localize discontinuous commands, state changes or event-triggered isolation.

Native CVODES can evaluate beyond a requested output time while constructing its
interpolating solution. Preflight reserves one `maximum_time_step_s` after the
final output inside every boundary's support. Support must cover native trial times,
which `trace.evaluated_clock_bounds_s` records. The example intentionally declares
support through 102 s while requesting output through 101 s. Insufficient support
fails; no nearest-value extrapolation, terminal clamp or invented zero flow is
applied. A callback violation is retained even if native error recovery retries a
smaller step and subsequently reaches an output time.

`sampled_gas_rate(series, channel, boundary_id=...)` accepts an explicit
`TimeSeries` channel with quantity `mass_flow`, unit `kg/s`, complete valid samples
and a resolved origin. It preserves the exact clock/source identity and uses
linear interpolation only inside its support. Negative signed measurements,
masked gaps, unresolved units and missing support are errors. The source record
is retained in `trace.feeds` or `trace.vents`; no measured ventilation pressure
recorder or unrelated sensor flow is promoted to a boundary by implication.

## Existing shared nozzle

A vent callback can delegate `HomogeneousIsentropicNozzle` through the existing
`CanteraFrozenGasProperties` provider. Allocate a separate native phase for that
provider: its native PT/PH/PS queries change its phase state, so it must not own
the active reactor's phase. `test_existing_shared_nozzle_can_drive_native_pure_gas_vent`
executes this composition with a fixed pure-N2 physical state and an explicitly
declared opening. The nozzle owns the flow solution and the enclosure's native
MFC owns removal of upstream mass/species/enthalpy, including the stagnation
energy later partitioned by the nozzle into static enthalpy and kinetic energy.

For evolving mixtures, the native phase callback may include Jacobian trial
compositions and floating-point sum residuals. The frozen provider's strict
fraction contract and any explicit `composition_sum_tolerance` and named
`composition_correction_id` remain applicable; silently
renormalizing or clipping species would change this boundary. See
[FROZEN_GAS_PROPERTIES.md](FROZEN_GAS_PROPERTIES.md) for that separate provider.

## Accounting and verification

The appended native variables integrate each inlet and outlet mass, signed net
mass of each species, total inlet enthalpy, total outlet enthalpy and net wall
heat. Walls are oriented environment → volume, so positive `wall:heat` enters
the inventory. Flow-device rates remain nonnegative; inlet/outlet orientation
sets the sign in mass/species/energy balances. Ledger names and units are
explicit at `trace.ledger_names` / `trace.ledger_units`.

Only appended energy states are conditioned: by default one native appended
energy unit represents `energy_ledger_scale_j=1e6` J. Mass/species states remain
kg, and every returned integral/residual remains SI J or kg. The immutable
`trace.ledger_native_scale_to_si` records the multiplier for each appended row;
multiply the actual native appended state by that multiplier to recover SI.
`energy_ledger_scale_j=1` retains the original raw-joule numerical reference.
This changes the absolute-error weight of those appended variables in native
units. It leaves physical state rows, scalar rtol/atol, thermochemical reference
and all external SI acceptance budgets unchanged. A numerical scale is not an
energy-reference conversion or a proof that an application budget passes.

`mass_residual_kg`, `species_residual_kg` and `energy_residual_j` compare actual
native inventories with those independent boundary rows. These are numerical
integrals under native solver tolerances, not exact mathematical quadrature.
`run` reports a completed native solve and diagnostics; application acceptance
still needs declared inventory/energy budgets and a convergence check. It does
not label every successful native integration conserved or experimentally valid.

```powershell
.venv\Scripts\python -m pytest tests/test_cantera_volume.py -q
.venv\Scripts\python scripts/check_cantera_volume.py
```

The tests use original constant-cp verification species to check analytic sealed
feed, adiabatic extraction, equal-mass exchange, signed heating/cooling and
conductive-wall limits. They also execute actual installed mechanism-derived
thermochemistry and the shared-nozzle vent. Negative checks retain source-clock,
signed-rate, native bounds, depleted-inventory, reactive-mechanism, phase reuse
and callback mutation failures.

The reproduction script uses installed H2/N2 species, independently integrates
the authored source rate, reconstructs feed-only final state through native UVY
and vent-only final state through native SV, checks independent sampled heat and
outlet enthalpy, and compares two maximum time steps. Results and code/mechanism
hashes are in [research/open_gas_volume.md](../research/open_gas_volume.md).

One local before/after observation used fresh subprocesses and the same fourteen
test names / four-case replay. The scaled suite additionally runs an unscaled
constant-feed reference inside its existing analytic test and compares physical
states and SI integrals against unchanged budgets.
The observed raw/scaled feed differences were 4.68e-8 K, 1.97e-5 Pa and at most
7.21e-10 in SI ledger entries, below the fixed 1e-6 K / 0.001 Pa / 0.001 J gates.

| Workload | Raw J states: wall s / native step warnings | Scaled energy states: wall s / native step warnings |
|---|---:|---:|
| Fourteen tests | 42.917 / 14 | 23.705 / 12 |
| Four-case replay | 1.693 / 6 | 1.362 / 0 |

Warnings here count native `[CVode] Internal t` step-roundoff lines. The scaled
suite retains its intentional raw reference and depleted-inventory failure, so
warnings remain visible. No warning filter, clock reset or solver substitution
was used. Workstation load and import contention affect these single timings;
they are observations, not a general speedup claim. The default replay removes
the zero-energy-ledger initial-step warning and retains all eleven fixed gates.
Run `python scripts/check_cantera_volume.py --energy-ledger-scale-j 1` for the
original numerical reference; the generated report records the selected scale.

Finite inventory is enforced through `minimum_inventory_kg` at native trial and
output states. Reaching that floor rejects the run; there is no invented exact
emptying time or repaired negative mass. Failures retain actual native objects at
`GasVolumeIntegrationError.native`. Finite source reservoirs, changing inlet
thermo, bidirectional ports, pressure-trigger localization, wall heat capacity,
mechanical motion, condensation, chemical heat release and measured enclosure
qualification remain outside this level.

Primary specifications: [native control-volume equations](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html),
[native extension, flow-device and wall APIs](https://cantera.org/3.2/python/zerodim.html),
[native extension guide](https://cantera.org/3.2/userguide/extensible-reactor.html).
The adapter and verification cases are original; externally installed mechanisms
and Cantera retain their separate rights and provenance.
