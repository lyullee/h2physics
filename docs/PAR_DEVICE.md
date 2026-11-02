# Coupled passive catalytic recombiner device

`h2physics.adapters.par_device` adds a **lumped device model**, combining a
source-identified removal-capacity law, a buoyancy-driven channel, gas heat
transport and a finite catalyst temperature. It is a performance-map level:
Cantera owns gas thermochemistry, while a supplied device map owns the catalytic
capacity. This level does not solve catalyst surface coverages or replace the
existing native catalytic CSTR/PFR adapters.

## Python contract

The entry point is `PARDevice(gas, parameters, capacity)`:

- `gas` is the existing `CanteraGas` owner with an explicit `MechanismBasis`.
  `CanteraGas.from_yaml` binds caller-supplied native mechanism bytes and their
  SHA-256. Mechanisms and upstream solver code remain separately installed.
- `PARDeviceParameters` carries geometry, loss coefficient, catalyst heat
  capacity, gas/room conductances, radiating area, emissivity, heat partition,
  a flow-solve bound and an explicit imposed background exchange flow.
- `PARCapacityLaw` returns a whole-device **mol H2/s** capacity. Its source or
  calibration identifier, temperature/pressure/composition envelope and maximum
  flow are mandatory. The callback receives a `PARCapacityCondition` containing
  catalyst temperature, inlet state and trial mass flow. It must be deterministic
  and side-effect free because the channel solver evaluates multiple trial flows.

`evaluate(inlet, catalyst_temperature_k)` returns a `PARDevicePoint`. The shared
`ReactiveState` uses kelvin, absolute pascals and mole fractions summing to one.
The result retains both inlet and outlet, species molar flow rates, mass flow,
H2 removal, heat ports, catalyst heating, pressure head, mass/momentum/energy
residuals, device/capacity evidence IDs, native version and mechanism basis.
It also reports combined entropy generation in W/K and rejects a resolved
negative value; a source label alone does not make a supplied map admissible.
Returned species-rate mappings are immutable. The outlet state can be passed
directly to a compatible Python consumer; it is not a finite room inventory.

`integrate` evolves the catalyst and cumulative ports at a **fixed prescribed
inlet**. It requires increasing observation times and an explicit `clock_id`.
Elapsed time is measured from the first supplied observation; cumulative ports
are zero there. The output is `PARThermalTrace.samples`, with each sample retaining
its point, removed H2, inlet/outlet enthalpy integrals, room heat and cumulative
energy residual. A finite room needs its own mass/energy integrator receiving
these ports; repeatedly holding the inlet fixed does not model room depletion.

The following complete example deliberately uses a **synthetic constant capacity
and synthetic device coefficients** to exercise the interface. It makes no
claim about a real PAR. Install the `chemistry` extra first.

```python
import hashlib
from pathlib import Path
import cantera as ct
from h2physics.adapters.cantera import CanteraGas, MechanismBasis, ReactiveState
from h2physics.adapters.par_device import (
    PARCapacityLaw, PARDevice, PARDeviceParameters,
)

raw = (Path(ct.__file__).parent / "data" / "h2o2.yaml").read_bytes()
basis = MechanismBasis(
    "Cantera:h2o2:synthetic-device-example", hashlib.sha256(raw).hexdigest(),
    "Cantera-BSD-3-Clause; upstream-mechanism-provenance",
    ("https://cantera.org/3.2/examples/input/h2o2.html",),
    250.0, 3000.0, 10_000.0, 1_000_000.0,
)
native_gas = CanteraGas.from_yaml(raw, basis, phase_name="ohmech")
boundary = ReactiveState(300.0, 101325.0, {"H2": 0.04, "O2": 0.20, "N2": 0.76})
device_parameters = PARDeviceParameters(
    evidence_id="synthetic:software-example-not-a-real-device",
    chimney_height_m=0.5, inlet_area_m2=0.001, loss_coefficient=4.0,
    catalyst_heat_capacity_j_k=100.0, catalyst_to_gas_ua_w_k=1.0,
    catalyst_to_room_ua_w_k=0.2, radiating_area_m2=0.02, emissivity=0.5,
    reaction_heat_to_catalyst_fraction=0.8,
    maximum_mass_flow_kg_s=0.1, background_mass_flow_kg_s=0.0001,
)
capacity = PARCapacityLaw(
    evidence_id="synthetic:constant-capacity-not-a-calibration",
    hydrogen_capacity_mol_s=lambda condition: 0.0001,
    catalyst_temperature_bounds_k=(300.0, 900.0),
    inlet_temperature_bounds_k=(290.0, 350.0),
    pressure_bounds_pa=(90_000.0, 110_000.0),
    hydrogen_mole_fraction_bounds=(0.01, 0.04),
    oxygen_mole_fraction_bounds=(0.15, 0.22),
    maximum_mass_flow_kg_s=0.1,
)
device = PARDevice(native_gas, device_parameters, capacity)
point = device.evaluate(boundary, catalyst_temperature_k=350.0)
trace = device.integrate(
    boundary, initial_catalyst_temperature_k=350.0,
    time_s=[0.0, 1.0, 2.0], clock_id="experiment:run-start-seconds",
)
print(point.hydrogen_removed_mol_s, point.energy_residual_w)
print(trace.samples[-1].point.catalyst_temperature_k)
```

Replace the synthetic law and coefficients with independently reviewed device
data, and replace all bounds with their actual calibration/physical domains.
No universal removal law, heat-transfer coefficient,
loss coefficient or manufacturer performance curve is bundled.

## Device equations and sign conventions

The only admitted net transformation is H2 + 0.5 O2 → H2O vapor. The molar
extent rate is the minimum of device capacity, inlet H2 flow and twice inlet O2
flow. Other admitted inlet species are N2, Ar and He. Nonzero reactive
contaminants are refused; CO poisoning is not hidden inside an inert-gas label.

All formation and sensible enthalpies share the native gas mechanism reference.
The positive reaction heat is the negative stoichiometric molar enthalpy change
at inlet temperature times extent rate. `reaction_heat_to_catalyst_fraction`
allocates part of that heat to the catalyst; it is a supplied reduced-model
parameter, not a prediction of spatial surface heat transfer.

The pressure head is `g H (rho_in - rho_out)`. The lumped channel uses the mean
inlet/outlet density and inlet area: natural mass flow is
`A sqrt(2 max(head, 0) rho_mean / K)`. The root equation equates trial mass flow
to this natural flow plus the declared imposed background exchange flow. `K`
therefore follows this mean-density/inlet-area convention. The background term
is an independent imposed exchange-flow floor, not a fan pressure curve.
The maximum flow is a search/domain bound; exceeding it raises an error rather
than clipping the solution.

For gas transfer, the effective conductance is
`m_dot cp_in [1 - exp(-UA_gas / (m_dot cp_in))]`. It multiplies the catalyst minus
inlet temperature difference. This constant-inlet-cp effectiveness reduction
approaches zero heat transport as mass flow vanishes. It is not a resolved
channel heat-transfer correlation. Cantera's native enthalpy inversion then
determines the outlet temperature at the changed composition.

Positive `catalyst_to_room_heat_w` leaves the catalyst. It includes the supplied
room conductance and gray-surface radiation to an environment at inlet
temperature. Positive `catalyst_to_gas_heat_w` enters the throughflow. With `f`
the reaction-heat fraction and `Qrxn` the positive reaction heat:

```text
Hdot_out = Hdot_in - f Qrxn + Q_catalyst_to_gas
C_catalyst dT_catalyst/dt = f Qrxn - Q_catalyst_to_gas - Q_to_room
Hdot_in - Hdot_out - Q_to_room - C_catalyst dT_catalyst/dt = 0
```

Chemical formation energy is already included in inlet/outlet enthalpy. Adding
`Qrxn` a second time to the combined control-volume balance would double count
the chemical energy. Water generation remains in the vapor stream; no
condensation, liquid holdup, latent-heat plate model or cryogenic EOS is implied.
Cantera supplies the explicitly selected reacting ideal-gas level. CoolProp
remains the owner for nonreacting real-fluid equipment; no fallback EOS is used.

The additional native entropy check uses
`Sgen = m_out s_out - m_in s_in + Q_to_room/T_room + Q_catalyst_storage/T_catalyst`.
Here the prescribed room reservoir has `T_room = T_inlet`; the finite catalyst
entropy storage rate is `C/T_catalyst * dT_catalyst/dt`. A negative value below
`-(1e-10 + 1e-9 * max(abs(each entropy-flow term))) W/K` is refused. Small
negative roundoff is retained in the diagnostic. This is a necessary overall
thermodynamic gate, not a local surface-affinity model or evidence that a
performance map is experimentally valid.

## Startup and limits

With zero background exchange and a catalyst no hotter than the inlet, this
level returns `not_started_no_background_exchange`, zero throughflow and zero
removal. It contains no diffusion-to-surface startup calculation. An initially
hot catalyst can drive a buoyant solution if catalyst-to-gas heat transfer is
present. Without that coupling it returns `not_started_no_gas_heating`. Thus
the model does not create a cold-start feed from a zero-flow algebraic state.
Real autonomous startup needs reviewed diffusion/surface kinetics or measured
startup data supplied at a more appropriate model level.

The channel is quasi-steady with one catalyst temperature and one outlet state.
It does not predict spatial mixing, layered room concentrations, flame onset,
gas-phase combustion, poisoning, catalyst aging, condensation, multi-channel
maldistribution or equipment qualification. High catalyst temperature can be
relevant to ignition risk, but this model provides no ignition certificate or
universal temperature threshold. Domain failures remain explicit.

## Executed verification and continuation

The focused native suite is:

```text
python -m pytest -q tests/test_par_device.py
```

On 2026-11-02 the suite completed **21 passing cases** using Cantera 3.2.0
and its separately installed `h2o2.yaml`. Checks cover native thermochemical
delivery, stoichiometry, H2/O2 starvation, mass and combined energy balance,
chimney-root closure, no-exchange startup refusal, hot-catalyst buoyancy, an
independent exponential-cooling solution, reacting time-step refinement,
cumulative energy ports, ordinary outlet-state coupling, fresh native phase
ownership, frozen map-domain inputs and selected input domains. Synthetic device parameters are explicitly labeled and are not
measurements or calibration data. These tests verify the new host device
equations/interfaces; they do not requalify the native chemical engine.
An intentionally inconsistent forward-capacity law in hot, steam-rich gas is
refused by the entropy gate despite closing the first-law balance.

To continue device validation, acquire a source-identified performance map and
geometry, review its rights and uncertainty, reserve independent operating
conditions, and compare removal, mass flow, catalyst temperature and outlet
temperature jointly. REKO and THAI are candidates for experimental comparison;
no dataset or validated device calibration is included here.

The [PARUPM original paper](https://doi.org/10.1051/epjn/2022046) describes a
more detailed surface-chemistry/transport model. It motivates the distinction
between chemistry, gas flow and catalyst heat storage; this implementation does
not reproduce its code or fitted parameter set. The
[JRC REKO facility record](https://storage-thermal-reactor-safety-analysis-data.jrc.ec.europa.eu/facilities/reko)
identifies a relevant experimental facility. Native thermodynamic API details
are in [Cantera's documentation](https://cantera.org/3.2/python/thermo.html).
These citations do not grant redistribution rights for external figures,
mechanisms or raw observations.
