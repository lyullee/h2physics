# Closed-charge hydrogen cylinder segment

`h2physics.combustion.SliderCrank` and
`run_closed_charge_engine_segment` provide a moving-volume, closed-charge
hydrogen cylinder interval. Cantera 3.2 owns gas thermodynamics, finite-rate
chemistry and integration. The adapter drives a native Cantera Wall from the
specified slider-crank geometry and constant crank speed.

This is a distinct level from a constant-volume ignition calculation. It can
represent homogeneous compression/expansion and native reaction evolution of a
caller-provided premixed H2/oxidizer charge. The caller sets the initial state and
the start/end crank angles. The result retains sampled pressure, temperature,
volume, mass, species mass fractions, internal energy, signed pressure-volume
work and a sampled first-law residual. When the optional piston-face schedule is
used, it also retains the source schedule and cumulative imposed heat input.

`EngineBoundarySchedule` is a source-bound scalar schedule with declared
quantity, units, source identifier, absolute clock origin, support and values.
Queries use linear interpolation and reject extrapolation. The closed-charge
solver consumes one explicit boundary level: an optional `heat_flux` schedule
in W/m² applies caller-prescribed signed heat flux through the piston face.
Cantera's native moving wall applies this imposed flux to the cylinder while
continuing to own gas reaction and integration. Positive flux enters the gas;
the integrated heat uses piston face area. No transfer coefficient or heat
correlation is inferred. Other schedule quantities remain bookkeeping inputs,
not valve flow, fuel delivery or spark behavior. Numeric schedule storage is
immutable, and `require_current()` rejects source, units, clock, support or value
changes.

`engine_schedule_from_crank_angle()` converts an increasing crank-angle/value
pair into this absolute-time schedule using a `SliderCrank` constant-speed
definition, an explicit segment start angle and clock origin. The conversion
does not interpret the quantity; the closed-charge runner accepts only the
explicit heat-flux quantity as an imposed piston-face thermal boundary. The
caller still owns its source identity and flux values.

If a native `advance()` call or trace assembly fails after earlier output targets
completed, `ClosedChargeEngineError` retains the original ReactorNet, ideal-gas
reactor, moving wall, completed sample prefix, failed target time and original
exception. The prefix contains requested output samples that returned successfully;
it does not claim access to Cantera's internal rejected or accepted RK stages. The
deferred `hydrogen-engine-failure-prefix` case injects failure after two completed
output samples and checks the retained owners and cause chain.

## Python boundary

```python
from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.combustion import (
    EngineBoundarySchedule,
    SliderCrank,
    run_closed_charge_engine_segment,
)

heat_flux_schedule = EngineBoundarySchedule(
    quantity="heat_flux", units="W/m2", source_id="caller:piston-face-heat-v1",
    clock_origin_s=absolute_start_s, time_s=absolute_schedule_times_s,
    values=caller_heat_flux_w_m2,
)

trace = run_closed_charge_engine_segment(
    phase_factory,  # returns a fresh Cantera ideal-gas Solution each call
    mechanism_basis,
    ReactiveState(temperature_k, pressure_pa, mole_fractions),
    SliderCrank(
        bore_m=bore_m,
        stroke_m=stroke_m,
        connecting_rod_m=rod_length_m,
        compression_ratio=compression_ratio,
        speed_rpm=speed_rpm,
    ),
    crank_start_rad=start_angle,
    crank_end_rad=end_angle,
    piston_heat_flux_schedule=heat_flux_schedule,  # optional W/m² into cylinder
    samples_per_revolution=720,
)
```

All properties are SI except speed in rpm and crank angle in radians. Supply a
mechanism basis with a digest, license identity, source references and
temperature/pressure envelope. No mechanism is bundled or selected implicitly.
The factory is called separately for the cylinder and static ambient reference;
each must return an ideal-gas Cantera phase with the declared mechanism's H2 and
O2 species. The initial mole fractions must already sum to one.

When supplied, the heat schedule must cover the interval from its absolute clock
origin through the segment end; its `clock_origin_s` maps elapsed engine time
zero to the absolute schedule time. Every schedule knot is included in the output
clock. The reported heat input is the exact integral of the declared piecewise-
linear flux times piston face area; it is included in the sampled first-law
residual. This ledger follows the admitted schedule and output clock; it is not
a separate accepted-internal-step conservation certificate.

The interval is limited to less than one 4-stroke cycle and does not imply that
its endpoints are valve events. There is no intake/exhaust flow, fuel injection,
spark-energy or flame-propagation model, temperature-driven heat-transfer law,
wall inertia, friction,
crevice volume, knock, turbocharger, multi-cylinder interaction or brake output.
Finite-rate chemistry may autoignite according to the selected mechanism and
initial state. Therefore this API is not a spark-ignition engine model and its
work is not shaft work or validated engine efficiency.

The trace's work is `integral(P dV)` with positive sign for work delivered by the
gas. The first-law residual uses sampled endpoint internal energy, trapezoidal
sampled pressure-volume work and the exact prescribed heat-schedule integral. It is a numerical diagnostic, not a native
accepted-step ledger. Refine crank-angle sampling and compare with native energy
integrals before interpreting it. A returned trace is implemented-unverified;
its constructor requires a one-time issuer created only after the native segment
returns, so a copied dataclass cannot reseal altered history. Direct construction
also recomputes both summaries from the retained arrays. No local numerical
execution has been performed.

## Native foundation and deferred evidence

Cantera 3.2 documents zero-dimensional reactors, moving `Wall` objects, and a
gaseous-fuel internal-combustion example. The example itself states that it uses
simplifying assumptions and is illustrative. This adapter deliberately exposes
a smaller boundary with explicit limitations; it does not copy that example's
implementation. References: [Cantera 3.2 reactor network guide](https://cantera.org/3.2/python/zerodim.html),
[Cantera 3.2 gaseous-fuel engine example](https://cantera.org/3.2/examples/python/reactors/ic_engine.html),
and [Cantera 3.2 moving-wall example](https://cantera.org/3.2/examples/python/reactors/piston.html).

The `hydrogen-engine` cluster profile contains geometry/input/schedule admission
contracts and native trajectory/conservation cases for later remote execution on
Hangang under the current user direction. Independent
hydrogen-engine pressure-trace and work data, a qualified mechanism, and accepted
cycle-boundary energy ownership are still required. Request034 defines the next
full-cycle level, including explicit valve events, spark/injection schedule,
intake/exhaust enthalpy, accepted-step ledgers, cycle closure and measurements.
Its detailed receiving contract and parallel verification matrix are in
[`integration_request_034_035.md`](../research/integration_request_034_035.md).
The open-access TU Darmstadt flame/wall dataset is recorded in
`research/data/hydrogen-engine-flame-wall.toml`. Its figure-level flame propagation
and piston surface-temperature measurements are candidates for later observation
ingestion and wall-boundary research; they do not contain the crank-angle pressure
and cycle-work evidence needed to qualify this closed-charge segment.

The attachment object schema has now been reviewed without loading measurement
arrays. No file currently supplies an unambiguous field mapping with quantity,
units, coordinate reference and sensor location together. See the
[field-by-field admission review](HYDROGEN_ENGINE_DATA_SCHEMA.md); no reader maps
the ambiguous arrays into pressure or wall-temperature model inputs.


OpenBraytonRun is issued only by run_open_cycle_brayton after native station and
conservation assembly completes. Direct construction cannot self-assert the captured
mechanism signature. The existing summary-integrity contract covers this receipt;
no additional cycle physics is implied.
