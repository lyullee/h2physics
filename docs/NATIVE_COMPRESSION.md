# Native gas compression and staged cooling

The 2026-10-28 provenance/source-boundary increment is **implemented_unverified**.
It was reviewed with source inspection, AST, Ruff and LF checks only. Previous
executed evidence below belongs to its recorded original inputs; these changed
bytes and eight new equipment boundary case definitions have not been run.

Lh2dtCompressorStage executes the actual optional LH2DT Compressor operating
point. Lh2dtCompressionTrain serially composes those native stages with
explicitly prescribed interstage and final cooling boundaries. The same
CoolProp HEOS provider, native state factory, PropertyBasis, BoundaryPower and
ConnectionTransfer contracts used by the existing equipment layer remain in
use. There is no additional compressor, flow/nozzle solver or EOS.

The checked native source is lh2dt_models 0.1.2 at revision
b2f276333c1b1793c39f25763703d196d36742ec. Its
[compressor implementation](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/compressor.py)
uses a supplied pressure ratio and isentropic efficiency to evaluate a native
PS reference state and PH actual state. Shaft work enters the fluid; it is not
electrical input power. The ideal-gas verification follows the
[NASA isentropic compression relation](https://www.grc.nasa.gov/www/k-12/airplane/compexp.html).
The real-fluid path uses the
[CoolProp property API](https://coolprop.org/coolprop/LowLevelAPI.html) and
[Leachman et al. hydrogen EOS](https://doi.org/10.1063/1.3160306).

## Native provenance and result correspondence

Every stage now exposes `native_provenance: Lh2dtNativeProvenance`, retaining the
installed native directory, exact per-file and aggregate Python source hashes,
immutable revision, original class/function/method bindings, source URL and
reviewed MIT license identity. Capture reads already-loaded source only; the
adapter does not import an optional engine to discover it. A different native
revision requires an explicit dependency review. Unknown/rebound native classes,
methods or changed installed source fail admission. Caller property facades are
bound separately; native equipment provenance does not attest a callback's EOS.

`point.require_current()` and `train_result.require_current()` check original
owner-issued identity, native input/output/PS records, summaries, flow, reference,
phase, envelope/EOS limits, tolerances and the current component configuration.
Copied/relabelled dataclasses cannot become original results. Owners retain weak
result/witness registries rather than all historical native results. Keep the
returned result for deep native coupling and call its guard before reuse.
These guards address stale research inputs, not deliberate private-field attacks.

Pressure is explicitly `Pa_absolute`; mass flow is kg/s and mass-specific h/u/s
remain J/kg and J/(kg K) on the original `PropertyBasis`. The native outlet and
independent PS state now also receive same-provider PT consistency checks. Native
ratio/rise metadata must match the actual absolute states. No reference reset or
phase repair is performed. Positive shaft/heat signs remain into the fluid.

Ratio and efficiency remain replaceable native operating-point inputs: after a
parameter change a fresh evaluation is allowed, while the previous result's guard
rejects its stale correspondence. This is not a machine map. Capacity, speed,
surge/choke and electrical/motor efficiency are unavailable. An authored envelope
is an admission boundary, not a fitted manufacturer's map. The existing HEOS
facade remains a reference-EOS path; recognized tabular backends are rejected
without an independent table qualification contract. Unknown caller providers
remain caller-evidenced and gain no native EOS/table qualification by wrapping.

## Finite source snapshot handoff

`stage.bind_finite_source(native_owner, native_step, node_id=...,
local_time_origin_s=..., clock_tolerance_s=..., clock_id=..., source_id=...)`
binds a caller-supplied original native `DynamicNetworkStepResult` row to the
actual finite source component. It retains the original owner/row/state, mass,
fluid U, property basis, absolute clock and source evidence. The selected row's
thermodynamic state must agree with the source's native mass/U EOS recovery and
the stage provider. The explicit clock projection budget rejects lost elapsed
time. `source.require_current()` rejects changed row dictionaries, cached mass,
source geometry, native methods, property ownership or clock summaries.

Pass this owner-issued witness as `stage.evaluate(source.fluid, flow,
finite_source=source)` or to the first stage of `train.evaluate`. The inlet must
be exactly its bound host state. The result labels this as
`finite-native-accepted-snapshot-not-time-integrated-withdrawal`. This contract
does not independently reconstruct the caller's solver acceptance history.
It does not withdraw mass, authorize `flow*duration`, enforce available delivery
or connect a receiver. A surrounding actual native dynamic network must own
withdrawal, replenishment, receiver pressure and heat/shaft/enthalpy integrals
at every solver stage. An unbound point explicitly says
`prescribed-steady-inlet-no-source-inventory`. No infinite inventory is inferred.

`CompressorBoundaryError` retains the original cause and available native inlet,
raw result and PS state; a serial failure also retains all completed stages and
coolers. `CompressionClosureError` still retains its actual attempted result.
No failed outlet or earlier accepted stage is replaced by a fallback.

The definitions in `examples/lh2dt_compressor.py` and four
`compressor-boundaries` deferred cases cover actual HEOS ledgers, parameter/method/
copy rejection, finite-source snapshot ownership and a failed serial prefix.
Nothing in those files has been invoked locally for this increment.

## Executable Python composition

The example uses the separately installed pinned package under the same
repository-local target as the other native equipment checks. All numerical
inputs below are authored synthetic inputs, without manufacturer qualification.

~~~python
from pathlib import Path
import sys

sys.path.insert(0, str(Path("artifacts/native_packages").resolve()))
from lh2dt.compressor import Compressor
from lh2dt.properties import ThermoState as NativeState

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_compressor import (
    CompressorEnvelope,
    Lh2dtCompressorStage,
    Lh2dtCompressionTrain,
    PrescribedIntercooling,
)
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.thermo import CoolPropProperties

eos = CoolPropProperties("Hydrogen")
native_properties = Lh2dtLowLevelProperties(eos, state_factory=NativeState)
bridge = Lh2dtProperties(native_properties, reference_id=eos.basis.reference_id)
envelope = CompressorEnvelope(
    minimum_pressure_pa=1e5,
    maximum_pressure_pa=100e6,
    minimum_temperature_k=100,
    maximum_temperature_k=1000,
    minimum_mass_flow_kg_s=1e-4,
    maximum_mass_flow_kg_s=0.1,
    evidence_id="authored-synthetic-example-envelope",
)
stages = tuple(
    Lh2dtCompressorStage(
        Compressor(native_properties, pressure_ratio=3.0, isentropic_efficiency=eta),
        bridge,
        state_factory=NativeState,
        stage_id=f"compressor-{index}",
        envelope=envelope,
    )
    for index, eta in enumerate((0.8, 0.75, 0.7))
)
train = Lh2dtCompressionTrain(
    stages,
    intercoolers=(
        PrescribedIntercooling("cooler-1", 300.0, 1e4, "supplied-outlet-PT-1"),
        PrescribedIntercooling("cooler-2", 305.0, 2e4, "supplied-outlet-PT-2"),
    ),
    aftercooler=PrescribedIntercooling("aftercooler", 310.0, 3e4, "supplied-aftercooler-PT"),
    train_id="gas-compression-train",
)
inlet = eos.state_pt(1e6, 300.0)
result = train.evaluate(inlet, mass_flow_kg_s=0.025)
shaft_into_fluid_w = result.power.shaft_work_w
heat_into_fluid_w = result.power.heat_w
delivered = result.outlet
native_stage_result = result.stages[0].native_result
assert result.native_components[0] is stages[0].native
~~~

Every pressure is Pa absolute; temperatures are K, flow is kg/s, specific
energies are J/kg and duties are W. The stage's native pressure ratio and
efficiency can be changed explicitly between evaluations; the selected values
are retained with each result. A changed property owner or contradictory
fluid/reference basis is rejected.

## Acceptance, identity and power accounting

The input ThermoState must share the bridge basis and agree with an independent
PT reconstruction of that provider. Native components must share the exact
native property instance. When that instance exposes a basis, its reference and
spin identity must also match; a different label cannot authorize a conversion.
Normal, para and ortho H2 remain separate HEOS providers and result bases.
No global enthalpy-reference or spin-partition conversion is performed.

CompressorEnvelope declares pressure, temperature and strictly positive active
throughput bounds with a caller-supplied evidence identity. Its declaration does
not qualify that envelope experimentally. For the recognized native HEOS
facade and original native HydrogenProperties, separate CoolProp Tmin, Tmax and
pmax metadata bounds also apply; stage.eos_limits retains them. The observed
three H2 providers have Tmax=1000 K and pmax=2 GPa. The accepted operating region
is the intersection with the declared envelope and phase guard. A more general
injected verification provider must supply its own applicable declared bounds.

Active compression accepts only gas, supercritical_gas and supercritical
states. It rejects liquidlike supercritical states, critical-point labels,
wet/two-phase states and even the saturated-vapor endpoint. This is stricter
than the pinned native quality tolerance and deliberately excludes wet or
near-condensing compressor operation. Inlet consistency, ideal/outlet domain,
positive work, pressure ratio, selected efficiency, nondecreasing entropy and
enthalpy/shaft-power closure are checked. A failed post-evaluation acceptance
raises CompressionClosureError retaining result, native_result,
native_component and the actual violations. No failure selects another model.

BoundaryPower is positive into the modeled fluid. An adiabatic stage has zero
heat and positive shaft work. A prescribed cooler has negative heat and zero
shaft work. Each component checks the common enthalpy-only relation:

~~~text
mdot * (h_out - h_in) = heat_into_fluid + shaft_work_into_fluid
~~~

Kinetic/potential port energies are outside this level. A train carries the
same prescribed flow through every stage and cooling boundary, so its reported
zero mass residual states the no-inventory/no-leakage topology. Its total energy
residual is independently recomputed from delivered/inlet enthalpy and summed
signed duties. Consecutive ConnectionTransfer objects share actual connecting
states and node identities. This accounting does not establish a pressure-driven
capacity or momentum closure.

Each stage result retains native_component, native_result, native_inlet and
native_isentropic_outlet; the actual discharge remains native_result.outlet.
The cooling result retains its actual native_outlet and native_properties.
They remain available for deep Python coupling. Editing them after evaluation
can invalidate the recorded summary and is the caller's responsibility.

## Cooling boundary and inactive behavior

PrescribedIntercooling supplies a target outlet temperature, a nonnegative
pressure loss and an evidence identity. The native property provider calculates
that outlet PT state. The host records the required signed enthalpy duty. A
hotter target, nonpositive resulting pressure, heat addition or a condensed
outlet is rejected. Empty intercoolers means no interstage cooling; an explicit
None means no cooler at that position. A final aftercooler is optional.

These boundaries do not predict coolant flow, UA, ambient approach, available
cooling capacity, chiller electricity, moisture removal or exchanger pressure
loss from geometry. The pinned native Vaporizer adds heat only; Reliquefier
requests saturated liquid/vapor states and cannot serve as a gas intercooler
above critical pressure. The adapter does not relabel either as such a model.

evaluate(..., mode="compressing") requires positive forward flow inside the
declared envelope. Reverse flow, zero-flow compression and unknown modes fail.
evaluate(..., mode="isolated") requires exactly zero flow, returns no transported
outlet and no native compression result, and assigns zero boundary power. It
represents an ideal external isolation boundary. Shaft coast-down, trapped gas,
motor/casing heat and a stopped-machine throughflow path require separate native
equipment and inventory contracts.

The native component accepts inlet plus prescribed mass flow, rather than the
left/right boundary-state signature of the native steady graph. This operating
point train is therefore not claimed as an already solved arbitrary
SteadyNetwork compressor link. No upstream/downstream pressure pair is converted
into throughput by this adapter. Both momentum_residual_pa and
operating_point_admissible remain None because the pinned component supplies no
capacity, efficiency map, surge/choke or mechanical admissibility result.

## Executed evidence and remaining receiving work

~~~powershell
.venv/Scripts/python.exe -m pytest -q tests/test_lh2dt_compressor.py
.venv/Scripts/python.exe scripts/check_compressor_integration.py
~~~

The script verifies 54 actual native points against an independent ideal-gas
oracle and 72 HEOS points across normal, para and ortho H2. It executes actual
three-stage serial/intercooled trains, a pressure-loss/unequal-efficiency case,
native high-level versus shared low-level property paths, inactive and negative
cases, source fingerprints and local timings. Results are recorded in
[native_compression.md](../research/native_compression.md).

The exploratory 1e-5 W energy subgate fails at a ParaHydrogen PH flash point
with about 4.17e-5 W raw residual. The established common equipment 0.05 W
absolute budget passes. The report retains both outcomes; requested enthalpy
does not replace native returned enthalpy and no reference shift conceals the
residual. These checks are numerical/interface verification, not compressor
experimental validation.

Concrete receiving needs are a native bidirectional gas intercooler with
coolant/UA/capacity/pressure-loss contracts; compressor speed/flow/efficiency and
mechanical admissibility maps with source evidence; native graph capacity
closure; and startup/isolation/reverse-flow/casing/rotor inventories where
required. Independent compressor measurements must identify the actual stage
inlet/outlet states, shaft versus electrical power, flow basis and thermal
boundaries before comparison. No such measurements are invented here.

LH2DT is separately installed under its checked
[MIT license](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE).
CoolProp is separately installed under its
[MIT license](https://github.com/CoolProp/CoolProp/blob/master/LICENSE).
No native implementation, manufacturer curve, third-party example, figure or
external dataset is copied into this feature.
