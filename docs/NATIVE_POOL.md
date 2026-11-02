# Native dynamic pools and finite-window vapor sources

The optional DynamicLH2PoolX engine owns axisymmetric shallow-layer spreading,
contact-age solid heat transfer, isothermal evaporation and time stepping. The host
adds explicit ground/source boundaries, checks native results and preserves the actual
objects. It does not create another pool solver or infer deposition from a nozzle.

The impact-to-native-pool deferred case uses the same optional provider boundary.
Install `h2physics[pool]` before running it. If `dynamiclh2poolx` is missing, the
case explains the missing extra and fails explicitly; no internal or alternate pool
implementation is selected.

## Install and reproduce

```powershell
python -m pip install -e ".[pool,test]"
python scripts/check_pool_integration.py
```

The checked pre-release is dynamiclh2poolx 0.2.0rc2, MIT. Its installed Python module
bytes match GitHub revision `6a700e8e183039bbb81803bacc416f6c9117ed71`; the exact
digest is in [native_pool.md](../research/native_pool.md). The optional extra requires
the tested CoolProp 8 major version. Importing the host adapters does not import the
native engine. `--plot` additionally uses Matplotlib for an original ignored diagnostic
image under `artifacts/pool/`. There is no required JSON or service interface.

All verification inputs are authored synthetic cases. No upstream digitised curves or
restricted source observations are imported. Upstream component studies have separate
input domains, source provenance and limitations; their status is not transferred to
this new host composition.

## Ground input and physical identity

Construct an actual native `DeclaredInflow`, then bind it with
`DeclaredGroundInflow(native, location, liquid_state, start_time_s, end_time_s,
origin, evidence_id, end_reason)`. The native schedule uses elapsed seconds from zero
and nonnegative zero-order-held kg/s. The host window uses the explicitly named absolute
clock. The final native rate persists only within that declared finite host window.
An isolation label requires a final zero rate; output after input shutoff can still
contain continuing evaporation. Supply a window long enough for the question being asked.

The history is already liquid at the ground, with explicit saturated-liquid state at
the pool ambient pressure. A pipe's liquid fraction is insufficient evidence for this
boundary. Subcooling, impact heat, splash, airborne droplets, flash transit and unknown
deposition remain separate physics. Input/source identities, clock, coordinate frame and
center survive the calculation. Output direction specifies the surface normal, without
inventing a vapor velocity or momentum flux.

The current native implementation hard-codes CoolProp normal `Hydrogen` at constant
pressure. `NativeDynamicPool` rejects para/ortho labels. It checks the input reference,
phase and saturation state and compares native temperature/density at each output.
No fluid name or energy reference is silently changed. Reference states are evaluated
twice per run; a new cryogenic interpolation table is unnecessary for this workload.
Initial radial inventory and restarts are not supported by this checked route.

```python
from dynamiclh2poolx import (
    DeclaredInflow, DynamicPoolConfig, ShallowLayerNumerics,
    SolidSemiInfiniteSurface, run_dynamic_pool,
)
from h2physics.adapters import DeclaredGroundInflow, NativeDynamicPool, PoolTolerances
from h2physics.core import Origin
from h2physics.release import SourceLocation
from h2physics.thermo import CoolPropProperties

properties = CoolPropProperties("Hydrogen")
ground_location = SourceLocation("ground-input", "facility-clock", "horizontal-frame",
                                 (0., 0., 0.), (0., 0., 1.))
vapor_location = SourceLocation("pool-vapor", "facility-clock", "horizontal-frame",
                                (0., 0., 0.), (0., 0., 1.))
inflow = DeclaredGroundInflow(
    DeclaredInflow((0., 1.13), (.025, 0.)), ground_location,
    properties.saturated(101325., 0.), 200., 208., Origin.SYNTHETIC,
    "authored-ground-boundary", "isolation",
)
config = DynamicPoolConfig(
    surface=SolidSemiInfiniteSurface("authored-solid", .16, 7e-7, 80.),
    numerics=ShallowLayerNumerics(domain_radius_m=1.5, source_radius_m=.12,
                                radial_step_m=.00125, maximum_time_step_s=.000625),
    ambient_pressure_Pa=101325.,
)
pool = NativeDynamicPool(
    run_dynamic_pool, properties,
    engine_id="dynamiclh2poolx:0.2.0rc2:6a700e8e183039bbb81803bacc416f6c9117ed71",
    tolerances=PoolTolerances(event_clock_roundoff_s=1e-10),
)
run = pool.run(config, inflow, output_times_s=(200., 200.2, 200.6, 201.13, 202., 204., 208.),
               vapor_location=vapor_location)
source = run.evaporation_source()
actual_native_result = run.native
```

These material/numerical values are authored verification parameters. Replace them with
qualified site inputs and refine the solution; they are not universal surface properties.
The `engine_id` should identify the actual version/revision used by an application.

## Accounting and clock contract

At every native output, the host independently integrates the original step schedule
and checks cumulative input + declared numerical adjustment = stored liquid + evaporated
mass + escaped liquid. It also checks native reported residuals, cumulative monotonicity,
interval means, phase properties, clocks and source status. Default mass gate is
1e-10 kg + 1e-8 times cumulative input, with zero allowed adjustment and escape budgets.
Those are numerical accounting limits, separate from mesh agreement or experimental accuracy.

`PoolCouplingError.native` and `.issues` retain failed results. `require_closed=False`
returns diagnostic `NativePoolRun` objects, but their `evaporation_source()` still refuses
an inadmissible result. Unknown native fields/statuses do not select another model.

The checked native loop has a near-knot clock inconsistency: its event search ignores
an event within 1e-12 s, whereas the original rate comparison remains strict. Roundoff
can then admit one extra supply step. The 200 s-origin authored case supplies an extra
0.00025 kg while the native internal residual is about 7e-18 kg. The independent input
gate rejects that result. Conservation of the wrong input is insufficient.

The default event-clock budget is zero. The positive example explicitly chooses
`event_clock_roundoff_s=1e-10`: `EventClockInflow` delegates the original native rate
function at a known knot only within this budget. It retains the actual original input
and every nonzero time correction in `run.input_clock`; the maximum is exposed through
`maximum_input_clock_correction_s`. Overlapping event neighborhoods are rejected.
The observed finest-run correction is about 4.44e-15 s. Independent mass gates are not
relaxed. Pool equations, integration and global property functions remain unchanged.
Request 010 specifies the receiving engine correction so this explicit bridge can later
be removed after an exact updated revision passes the retained negative case.

## Emitted mass and unresolved geometry

`IntervalMassSource(location, edges_s, mass_kg, state, origin, evidence_id, end_reason)`
stores read-only edges and one nonnegative mass per interval. `mean_rates_kg_s` uses
mass/duration. `mass_between(..., clock_id=...)` and `rebin(..., clock_id=...)` operate on
an explicitly constant-mean representation and reject extrapolation or clock changes.
Rebinning preserves the full window and total mass, without recovering within-bin detail.
The final edge is a boundary, not another emitted interval. `enthalpy_transfer_j` uses
the explicitly declared constant state/reference and can have either reference-dependent sign.

`NativePoolRun.evaporation_source()` differences native cumulative evaporation. It does
not integrate instantaneous-looking endpoint fields. In this authored case the exact
interval total is 0.0282498734 kg; trapezoids of sparse last-substep rates give 0.0319561560 kg.
After input isolation about 0.0244166527 kg still evaporates. At 2 s the reported radius
is zero, while liquid inventory is about 0.01623 kg and evaporation continues.
Reported radius is a depth-threshold observation; it does not determine wet area or dryout.

Actual native wet/reported areas and interval-mean/last-substep rates stay available
separately. Endpoint area divided into an interval mean is not a resolved instantaneous
flux. The current source supplies conservative vapor mass and a saturation state, with
no invented interval-average footprint, vertical momentum, atmospheric dilution or heat
ledger. It is a partial boundary for later dispersion coupling. Latent energy computed
from emitted mass and saturation enthalpy difference is a demand diagnostic, not an
independently checked complete energy balance.

## Verification, data and remaining work

The coupled coarse pairs fail a fixed 1% inventory/supply agreement target. Refining to
dr=0.0025/0.00125 m with maximum dt=0.00125/0.000625 s passes at about 0.734%, with
0.00125 m reported-radius change. Separate fixed-grid time comparisons meet the 0.2%
target but are not monotone; no asymptotic order or Richardson uncertainty is inferred.
Domain enlargement, a deliberately failed small-domain case, zero thermal driving and
independent capped-conduction quadrature are recorded. A tiny positive final inventory
remains under the native dry-depth treatment; the result is a finite window, not certified
complete depletion. Ten portable tests cover source semantics and failed native contracts.

[PRESLHY E3.4](https://doi.org/10.35097/1319) has eleven listed attachments under
CC BY-SA 4.0. All are withheld under this project's default permissive-data policy;
version/authors/metadata hashes/omissions remain in its receipt. This is a project reuse
decision, not a claim that the data cannot be used under their own terms. No measured
pool accuracy is claimed here. Find an appropriately reviewed numerical dataset before
experimental calibration. Arbitrary substrates, terrain, slopes, barriers, air condensation,
subcooling, jet-to-ground transfer and full atmospheric consequences remain unqualified.
