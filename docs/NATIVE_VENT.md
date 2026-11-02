# Native steady vent hydraulics and finite-UA heat

`h2physics.adapters.lh2dt_vent.Lh2dtVentStack` executes the actual native LH2DT
`VentStack` with explicit port/property identities, a declared gas envelope and
independent hydraulic/thermal checks. The current level resolves steady
enthalpy transport between two connected pressure ports. It does not produce a
critical-flow outlet or an atmospheric/dispersion source.

The separately installed MIT engine is version 0.1.2 at revision
[`b2f276333c1b1793c39f25763703d196d36742ec`](https://github.com/lyullee/lh2dt_models/tree/b2f276333c1b1793c39f25763703d196d36742ec).
The native stack owns its pipe call and finite-UA RK integration; the property
provider owns every PH/PT flash. The existing `Lh2dtDarcyPipe` and shared Darcy root
are an explicitly selectable hydraulic path. No second pipe, EOS or nozzle law is
implemented here.

```powershell
.venv\Scripts\python -X utf8 scripts/check_vent_integration.py
.venv\Scripts\python -m pytest tests/test_lh2dt_vent.py -q
```

`--native-packages PATH` selects the separately installed native target. The script
requires the recorded native aggregate fingerprint and verifies begin/end hashes
of host/test/script and dependency sources. Actual errors, runtimes, refinement
and retained failures are in `research/native_vent.md`. Parameters are authored
verification inputs; no measured vent data or manufacturer stack rating is fitted.

## Native objects and explicit hydraulic selection

The adapter accepts an actual native stack, its `Lh2dtProperties` bridge, actual
native state factory, an explicit phase-viscosity callable and a `VentEnvelope`.
An actual provider sound-speed callable and its capability identity are also
required; missing sound speed never implies subsonic applicability.
`component_id` and `evidence_id` identify the component and its geometry, local
loss, ambient UA/reservoir and source assumptions. The caller must explicitly
declare `allow_reverse`, matching the native object's selected policy.

With no `hydraulic_pipe`, the original native HEMPipe remains selected, including
its original friction/iteration behavior. Supplying an existing `Lh2dtDarcyPipe`
requires that it wrap this exact native pipe and share the exact property instance.
Its friction callable and `friction_law_id` remain explicit. The replay separately
chooses the direct fluids `Churchill_1977` correlation, preserving the original
native path and its failed transition cases for comparison.

Each evaluation copies the native stack configuration and assigns a recording
proxy over the selected pipe to that evaluation copy. Native `VentStack.evaluate`
then performs its original work. The supplied stack, its pipe binding and its
source files are untouched by evaluation. `VentResult` retains:

- The actual evaluation stack, original supplied stack, native vent result,
  selected hydraulic result and generated native PH outlet state.
- Supplied left/right port states, actual transport outlet, physical signed
  `BoundaryPower` and the common `ConnectionTransfer`.
- Friction identity, independent final momentum residual, finite-UA audit,
  direction-blocked status and evidence identity.
- Explicit `energy_scope`, signed `potential_energy_change_j_kg` and the
  upstream hydraulic `v²/2` diagnostic.
- Upstream Mach and a labelled same-bore downstream pipe-section Mach estimate.

For the shared path, `hydraulic_result` is the existing `DarcyPipeEvaluation` and
retains its actual native `PipeResult`, root and correlation diagnostics. An
original native hydraulic result remains an original `PipeResult`.

```python
from fluids.friction import Churchill_1977
from lh2dt.pipe import PipeResult
from lh2dt.properties import ThermoState as NativeState

from h2physics.adapters.lh2dt_hydraulics import Lh2dtDarcyPipe
from h2physics.adapters.lh2dt_vent import Lh2dtVentStack, VentEnvelope

# This recipe uses the caller-owned low-level HEOS facade, as in the replay.
def sound_speed_from_selected_properties(native_state):
    state = bridge.native.provider.state_ph(
        native_state.pressure_Pa, native_state.specific_enthalpy_J_kg,
    )
    return state.speed_of_sound_m_s

hydraulics = Lh2dtDarcyPipe(
    native_stack.pipe, bridge,
    viscosity_reader=native_stack.pipe._effective_viscosity,
    friction_law=Churchill_1977,
    friction_law_id="explicit direct Churchill_1977",
    result_factory=PipeResult,
)
vent = Lh2dtVentStack(
    native_stack, bridge, state_factory=NativeState,
    envelope=VentEnvelope(
        50_000., 500_000., 80., 600., .05, .5, .3,
        "authored dry-gas numerical envelope; application qualification pending",
    ),
    component_id="vent-1", evidence_id="authored geometry/UA verification case",
    allow_reverse=False,
    viscosity_reader=native_stack.pipe._effective_viscosity,
    sound_speed_reader=sound_speed_from_selected_properties,
    sound_speed_capability_id="same selected HEOS provider PH sound speed",
    hydraulic_pipe=hydraulics,
)
result = vent.evaluate(
    left_state, right_state,
    left_node="vessel", right_node="remote-header",
    left_port_id="vent/base", right_port_id="vent/terminal",
)
```

The protected native viscosity capability is specific to the pinned revision and
is fingerprinted by the replay. A public native injection/capability API remains
receiving work. This example declares a synthetic envelope; its numbers are not
an installed-stack validity certificate.

## Port state, direction, heat and momentum

Pressure is absolute Pa, temperature K, enthalpy J/kg, flow kg/s and heat W.
Fluid/spin/energy reference must match the selected provider. The adapter checks
port EOS consistency and requires dry single gas within the stated pressure/T
domain; liquid, mixed-phase and saturated endpoints are outside this level.
An excessive relative pressure difference or outlet/upstream density change
violates the explicitly declared upstream-density approximation envelope.

Small pressure or density changes alone do not bound flow Mach. A required
declared limit, at most 0.3 for this low-Mach level, checks upstream hydraulic
velocity against the injected actual-provider sound speed. The PH outlet and
the same native bore also give a downstream pipe-section velocity estimate;
that Mach is checked separately and explicitly labelled as an approximation.
It is not a resolved atmospheric exit or a guarantee about every interior
station. The replay uses actual HEOS sound speed for hydrogen; the ideal-gas
sound relation exists only in its authored verification fixture. Missing,
nonfinite or nonpositive sound results fail with the raw native vent retained.
A tiny-loss path can be supersonic despite a 1% pressure drop; that actual
native case is retained and rejected rather than classified as applicable.

Native hydraulics uses upstream density/viscosity, declared pipe geometry, local
loss and signed elevation. The independent audit recomputes Darcy friction loss
from returned flow/friction and checks its sum with hydrostatic head against the
port pressure difference. It also checks returned Reynolds number and native
reported momentum/drop. A reported zero residual cannot override a failed final
constitutive check. The existing common momentum budget remains .01 Pa absolute
or its declared relative scale.

Direction follows available pressure plus gravity, not static pressure ordering
alone. In one-way mode a hydraulically reverse-driving state returns zero
transport, unavailable momentum and no outlet state. Its attempted reverse
hydraulic result remains available. Explicit reverse mode transports from the
right port and resolves its outlet at the left-port pressure. A zero flow is not
given fictitious transported states or an unearned solved momentum residual.

For nonzero flow, `outlet` is the actual PH state obtained from native transmitted
enthalpy and the real downstream pressure. The remote port supplies that pressure;
its temperature does not replace the resolved transport outlet temperature.

The native reverse-flow `heat_into_fluid_W` field is left-to-right oriented.
`oriented_native_heat_w` preserves it unchanged. Common `BoundaryPower.heat_w`
explicitly multiplies it by the actual flow direction, so heat is positive into
the transported fluid in either direction. `ConnectionTransfer` uses absolute
throughput for its enthalpy ledger. An unknown operating-point admissibility flag
stays `None`; successful transport bookkeeping is not a stack rating.

## Native finite-UA resolution audit

Native `VentStack` integrates enthalpy against total ambient UA at the downstream
pressure. It retains a finite ambient heat exchange instead of prescribing an
outlet temperature. Its implementation clamps internal/final enthalpy to the
inlet/ambient interval, which can hide an underresolved thermal trajectory even
when `abs(mdot)*(hout-hin)` exactly equals reported heat.

The independent host audit reconstructs conductance from the native endpoint:

```text
UA_reconstructed = abs(mdot) * integral_hin^hout [dh / (T_ambient - T(h, p_downstream))]
```

This inverse quadrature checks the native ODE relation; it is not a replacement
forward heat solver. Actual provider PH states and gas-domain checks are used
throughout. Defaults require conductance residual plus quadrature uncertainty
within `max(1e-8 W/K, 1e-5*configured_UA)`. A coarse failure does not select more
segments, another correlation or another provider. The caller explicitly chooses
a different native numerical resolution and retains the original result.

At finite UA an outlet reaching/crossing the ambient endpoint is rejected as a
clamping/resolution issue. The separately checked equal-temperature limit has
zero heat and cannot identify UA. Adiabatic and zero-transport cases also retain
their separate meanings. `VentClosureError.native_result`, `.native_stack` and
`.hydraulic_result` preserve a failed evaluation; `.evaluation` is available when
the complete diagnostic transport result could be constructed. A shared hydraulic
root failure retains its existing `HydraulicConvergenceError.result` before a
native vent result exists.

## Energy scope and unfinished source physics

The common equipment contract is **enthalpy-only**. Native gravity changes the
momentum equation, while native thermal transport does not include gravitational
or kinetic-energy changes in its enthalpy update. The adapter preserves that model
and labels it in `result.energy_scope`. A small enthalpy/heat residual is not a
full total-energy validation.

For flowing results `potential_energy_change_j_kg` reports signed `g*dz` in the
actual flow direction. `upstream_hydraulic_kinetic_energy_j_kg` reports `v²/2` from
the upstream constitutive pipe velocity. Neither diagnostic supplies a resolved
terminal-plane velocity nor bounds its unknown kinetic-energy change. When these
terms matter to an application, a separately qualified mechanical/total-energy
level and physical outlet-plane definition are required. No omitted energy is
silently added to native enthalpy or reported heat.

The hydraulic diameter is not automatically a qualified atmospheric source area.
There is no stagnation-to-static conversion, nozzle/choke calculation, exit
momentum, phase partition, atmospheric expansion or dispersion handoff in this API.
The native accident exporter is deliberately unused by this level. High-pressure
critical release must retain its appropriate existing source owner; this stack
does not re-choke or replace that owner.

Remaining receiving work includes public hydraulic/viscosity injection, native
thermal error/clamp diagnostics, documented reverse-heat orientation, compressible
pressure/thermal coupling and mechanical-energy/outlet ownership. Installed UA,
roughness, local losses, dry-gas applicability, transient wall inventory and
independent vent observations still require separate evidence.

Primary sources are the pinned native
[VentStack](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/vent_stack.py),
[pipe implementation](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/pipe.py),
[MIT license](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE)
and [direct Churchill documentation](https://fluids.readthedocs.io/fluids.friction.html#fluids.friction.Churchill_1977).
The original/native-law failures and separately selected continuous-correlation
results remain distinct. No vendor, measured or dispersion qualification is claimed.
