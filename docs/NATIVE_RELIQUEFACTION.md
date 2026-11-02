# Native reliquefaction and finite cold-side recovery

The optional adapter executes the actual pinned LH2DT Reliquefier and
DynamicReliquefier. The steady model resolves capacity-limited cooling toward a
supplied saturation pressure/quality target. The finite model resolves rigid
fluid mass/internal energy, wall thermal storage and a cold-reservoir boundary.
Native EOS calls, heat laws, derivatives and RK integration remain in LH2DT and
the shared CoolProp provider. No refrigeration cycle or cooling ODE is added.

The checked source is lh2dt_models 0.1.2 at
b2f276333c1b1793c39f25763703d196d36742ec:
[steady source](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/reliquefier.py)
and [finite source](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/dynamic_reliquefier.py).
Thermodynamic phase/quality follows the
[CoolProp API](https://coolprop.org/coolprop/HighLevelAPI.html) and
[hydrogen EOS](https://doi.org/10.1063/1.3160306). The signed inventory ledger
uses the [first law](https://www.grc.nasa.gov/www/k-12/airplane/thermo1.html).

## Actual native steady point

All values in this example are authored synthetic inputs.

~~~python
from pathlib import Path
import sys

sys.path.insert(0, str(Path("artifacts/native_packages").resolve()))
from lh2dt import Reliquefier, DynamicReliquefier, DynamicNetworkSimulator
from lh2dt import SteadyNetwork, dynamic_vaporizer_node
from lh2dt.properties import ThermoState as NativeState

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.adapters.lh2dt_reliquefier import (
    ColdSideBoundary, Lh2dtSteadyReliquefier, Lh2dtDynamicReliquefier,
    ReliquefactionDomain,
)
from h2physics.thermo import CoolPropProperties
from h2physics.core import Origin

eos = CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=1e-8)
properties = Lh2dtLowLevelProperties(eos, state_factory=NativeState)
bridge = Lh2dtProperties(properties, reference_id=eos.basis.reference_id)
domain = ReliquefactionDomain(1e4, 10e6, 14.1, 1000,
                              "authored-synthetic-example-domain")
steady = Lh2dtSteadyReliquefier(
    Reliquefier(cooling_capacity_W=100.0, properties=properties),
    bridge, state_factory=NativeState, domain=domain, component_id="recovery",
)
result = steady.evaluate(
    eos.saturated(2e5, 1.0),
    outlet_pressure_pa=2e5, mass_flow_kg_s=0.001, target_quality=0.0,
)
actual_liquid_outflow = result.liquid_outflow_kg_s
new_liquid_production = result.net_liquid_production_kg_s
heat_into_fluid = result.power.heat_w
native_result = result.native_result
~~~

Pressure is Pa absolute, temperature K, mass flow kg/s and energy J/kg or W.
Positive heat and shaft work enter the modeled system. Native removed heat
becomes negative BoundaryPower.heat_w; shaft work is zero. ConnectionTransfer
retains the actual inlet and transmitted outlet state. No pressure-driven
throughput, resistance, momentum or mechanical admissibility is inferred.

The constructor checks native property ownership and explicit pure-H2
normal/para/ortho basis compatibility. Every supplied inlet is checked against
a native PH reconstruction, including density, internal energy, entropy, phase
and vapor quality. Declared domain and native EOS Tmin/Tmax/pmax limits apply.
A steady target must lie strictly between the selected triple and critical
pressures. An unmodeled pressure increase, negative/zero flow, invalid quality,
wrong basis or unsupported phase fails. The zero-flow steady native evaluator
and zero-capacity native constructor remain unavailable; they are not repaired.

The target quality is a requested thermal boundary. An insufficient capacity
can leave a superheated gas with no liquid. The adapter never substitutes the
target quality for the actual PH outlet. Native total outlet liquid fraction
is checked against that actual phase.

The result distinguishes total liquid outflow from newly produced liquid.
For example, a stream containing 70% liquid already can leave fully liquid:
its total liquid outflow is the complete mass rate, while only the remaining
30% is newly condensed. net_liquid_production_kg_s can be negative when a
pressure change flashes existing liquid. A supercritical inlet has no resolved
liquid partition; its net liquid-production quantity remains None rather than
being assigned a fictitious initial phase fraction.

Each result retains native_component, native_inlet and native_result.
ReliquefierClosureError retains a rejected raw native result and violations.
No native failure selects another property or cooling model.

## Finite fluid and wall inventory

Continue with the same provider and declared domain:

~~~python
from h2physics.adapters.lh2dt_dynamics import Lh2dtDynamicEquipment
from h2physics.adapters.lh2dt_equipment import Lh2dtEquipmentNetwork

cold = ColdSideBoundary(
    "absolute-operation-clock", 10.0, 30.0,
    lambda absolute_time: 18.0 + 0.1*(absolute_time-10.0),
    "authored-cold-reservoir-history", Origin.SYNTHETIC,
)
component = DynamicReliquefier(
    fluid_volume_m3=0.001, wall_heat_capacity_J_K=2.0,
    fluid_wall_UA_W_K=20.0, cold_side_temperature_K=18.0,
    cold_side_UA_W_K=20.0, maximum_cooling_W=5.0,
    properties=properties,
)
finite = Lh2dtDynamicReliquefier(
    component, bridge, state_factory=NativeState, domain=domain,
    cold_boundary=cold,
)
initial = finite.initialize(eos.saturated(2e5, 1.0), wall_temperature_k=18.0)
binding = finite.inventory_binding("cold-volume", initial,
                                    node_factory=dynamic_vaporizer_node)
network = Lh2dtEquipmentNetwork(SteadyNetwork(properties), bridge,
                                state_factory=NativeState)
network.add_boundary("cold-volume", finite.fluid(initial))
run = Lh2dtDynamicEquipment(
    network, {"cold-volume": binding.inventory_node},
    simulator_factory=DynamicNetworkSimulator,
).run(2.0, 0.02, start_time_s=10.0, clock_id=cold.clock_id)
final_balance = run.steps[-1].balances["cold-volume"]
actual_final_state = run.steps[-1].native.states["cold-volume"]
~~~

The caller must use the boundary's clock_id in the composed driver. Finite
support, origin and source identity are explicit; callbacks reject evaluation
outside support. The existing dynamics adapter passes the absolute operation
clock to every native derivative stage and checks each accepted inventory.

The native semantic dynamic_reliquefier_node currently fixes the cold-side
temperature and has no callback keyword. Explicitly selecting the public native
dynamic_vaporizer_node over its actual DynamicReliquefier subclass supplies the
existing time-dependent boundary capability. The binding retains the original
native node, component and checked inventory node. Its native advance and
derivative-combination callbacks remain unchanged.

The actual state stores mass, fluid U and wall temperature; conserved inventory
adds native wall capacity times wall temperature. A changed wall capacity is
rejected because it changes the stored-energy contract. The finite component
needs the existing facade's rho/U, PH/PT and saturation subset. Layered
pressure-projection derivatives are not needed and are not invented.

The standalone derivative method retains the actual native derivative with
external_power, internal fluid_wall_heat_w and total storage rate. The step
method retains the actual native step result, final native derivative and
inventory. Standalone native step accepts a held constant reservoir temperature;
time-varying forcing must use the inventory-node integrator. Its returned
derivative is the final instantaneous derivative, not an RK-averaged boundary
integral. Use the existing accepted-step dynamics ledger for integrated heat
and transported enthalpy.

The replay also connects the finite condenser to two explicit shared-nozzle
valves, a feed reservoir and a delivery boundary. The common nozzle owns each
flow closure; the actual native condenser/integrator owns mass, U, wall storage
and phase feedback. Dynamic liquid hold-up is stored material. The outlet is
well mixed, with its phase changed by any downstream pressure drop. Neither
phase-separated collection nor storage-tank return efficiency follows from it.

## Capacity, reservoir signs and inactive limits

The pinned dynamic maximum_cooling_W is a symmetric cap on fluid-to-wall
exchange inherited from DynamicVaporizer. It does not cap the reservoir-to-wall
UA heat. At 35 K fluid, 25 K wall, 18 K reservoir and both UAs 20 W/K, with a
5 W exchange cap, native wall-to-fluid heat is -5 W while external reservoir
heat is -140 W. Those are separate physical boundaries. Internal exchange
cancels from the combined fluid-plus-wall ledger.

Zero hydraulic inlet/outlet flow is supported and preserves finite inventory;
it does not disable external cooling. Setting the native external cold-side UA
to zero is supported and stops reservoir heat while existing wall-fluid exchange
continues. A zero native exchange-cap constructor is unsupported. Reversed
thermal gradients retain positive heating signs rather than being clipped.
The adapter's forward inlet/outlet rate arguments reject negative values.
The deeper native inventory-node flow interface retains signed upwind streams
from the selected hydraulic model.

No COP, electrical input, compressor/chiller efficiency or warm-side rejection
power is supplied by this cold-reservoir model. A refrigeration cycle, verified
performance map or measured shaft/electrical boundary must own those quantities.
The cooling-cap field alone cannot define them.

## Reproduction and limits

~~~powershell
.venv/Scripts/python.exe -m pytest -q tests/test_lh2dt_reliquefier.py
.venv/Scripts/python.exe -X utf8 scripts/check_reliquefier_integration.py
~~~

The replay report is
[native_reliquefaction.md](../research/native_reliquefaction.md). Begin/end guards
record the actual native and executed host/test/script bytes. It executes 24
saturated latent-heat/capacity points across three H2 spin identities, warm-gas
capacity and preexisting-liquid checks, native finite condensation under three
step sizes, independent capped-fluid-U/exponential-wall and absolute-clock
limits, zero-gradient/cooling-off limits and a flowing finite recovery case.
Raw unsupported native zero-flow/capacity, above-critical saturation,
over-withdrawal and callback-interface failures remain recorded.

The selected inherited quality-roundoff tolerance is explicit at 1e-8 and the
facade's adjustment counters remain available. It is not a phase-repair or
saturation policy. No measured recovery, cold-box construction, refrigerant
cycle, catalyst, spin conversion, noncondensable mixture, stratified inventory,
phase-selective drain, complete depletion or qualified apparatus performance is
claimed. The independent mathematical limits verify numerical behavior;
the native/direct property comparisons reuse the same EOS.

Receiving work includes public time-aware cold-side naming, separate external
reservoir-capacity and internal exchange-cap semantics, RK-averaged standalone
step boundary integrals, event/depletion localization and actual phase-selective
collection/return contracts with apparatus evidence.

LH2DT remains separately installed under its checked
[MIT license](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE).
CoolProp retains its separate
[MIT license](https://github.com/CoolProp/CoolProp/blob/master/LICENSE).
No native implementation, external measurements, third-party worked examples or
equipment curves are redistributed by this feature.
