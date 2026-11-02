# Thermal cycles, physical exergy and finite redox equilibrium

These additions supply two distinct calculation levels: an actual steady thermal
cycle solved by TESPy, and a material-specific finite solid/gas equilibrium solved
by the existing Cantera multiphase owner. They receive ordinary Python objects
and return native models alongside explicit SI balances. No serialization service
or copied external solver is required.

## Installation and ownership

The executed native combination is Python 3.12, TESPy 0.11.3, ExerPy 0.2.0,
CoolProp 8.0.0 and Cantera 3.2.0. Install only the capabilities needed:

```text
python -m pip install "tespy==0.11.3" "exerpy==0.2.0" "CoolProp>=8,<9"
python -m pip install "cantera>=3.2,<3.3"
```

TESPy owns component/network solving and uses its CoolProp fluid backend.
ExerPy owns component physical-exergy balances. Cantera owns reacting phase
thermochemistry and Gibbs minimization. h2physics owns the declared process
boundary, finite-stock/extent mapping, signed ledgers and reactor composition.
There is no ideal-fluid fallback when a native solve fails.

Exergy analysis is now maintained in the separate ExerPy project; code must not
import the removed TESPy exergy-analysis class. See the official
[TESPy migration note](https://tespy.readthedocs.io/en/main/advanced_features/exergy.html)
and [ExerPy direct-network interface](https://exerpy.readthedocs.io/en/stable/api/analyses.html).

## A solved thermal cycle

`h2physics.adapters.thermal_cycles.RankineCycleSpec` specifies a pure-fluid
Rankine/organic Rankine cycle: pump, boiler, turbine and condenser, with finite
hot-water and cooling-water streams. Absolute pressures are Pa, temperature K,
mass flow kg/s, heat/work W. Isentropic efficiencies and external-side pressure
ratios are dimensionless supplied design assumptions.

```python
from dataclasses import replace
from h2physics.adapters.thermal_cycles import (
    RankineCycleSpec, solve_rankine_cycle, analyze_rankine_exergy,
)

spec = RankineCycleSpec(source_id="authored-R245fa-design-example")
cycle = solve_rankine_cycle(spec)
print(cycle.energy.net_output_w)
print(cycle.energy.first_law_residual_w)

exergy = analyze_rankine_exergy(
    cycle, environment_temperature_k=298.15,
    environment_pressure_pa=101325.0,
)
print(exergy.component_destruction_w)
print(exergy.balance_residual_w)

# Native objects support deeper Python composition and component inspection.
turbine_inlet = cycle.network.get_conn("turbine_inlet")
print(turbine_inlet.T.val_SI, turbine_inlet.p.val_SI)
larger = solve_rankine_cycle(replace(spec, mass_flow_kg_s=2.5))
```

The reference case uses R245fa at 1 kg/s, 2 MPa/400 K turbine inlet, 0.2 MPa
condensation, turbine/pump efficiencies 0.85/0.75, hot water 450→420 K and
cooling water 290→300 K. These are authored design inputs, not plant data or
fitted material/device efficiencies. The executed case gives approximately
248.197 kW heat input, 212.805 kW heat rejection and 35.3925 kW net shaft
output; its first-law residual is approximately −2.91×10⁻¹¹ W.

The solver checks actual native convergence, heat-exchanger terminal temperature
ordering and the external first-law residual. The returned object retains the
network; it does not turn a converged network into an experimentally qualified
plant. Components, property states, power ports and a new solve can be accessed
directly. A modified native network must be solved and audited again; the stored
`cycle.energy` snapshot belongs to the original solve.

Net output is **shaft power**. Feeding an electrolyzer requires a declared
generator/converter efficiency, electrical operating point and time support.
For a generator efficiency `eta_generator` selected from actual evidence, the
electrical boundary would receive `eta_generator * cycle.energy.net_output_w`.
The API does not silently assume a loss-free electrical conversion.

The executed [power-to-electrolysis example](../examples/thermal_cycle_electrolysis.py)
performs the full direct-Python handoff: it solves the actual Rankine network,
declares 95% generator efficiency, and uses SciPy's bounded `brentq` to find the
current density of the existing `HydrogenStack` at the resulting DC power.
It declares a 20,000 A/m² admissible upper current and refuses a power demand
outside that bound. Existing Butler–Volmer/ohmic losses and Faraday accounting
remain the shared stack owner. The single-state reaction energies and loss
coefficients are explicitly synthetic software fixtures. They are not an
electrolyzer fit, production thermochemical default or measured plant data.

```text
python examples/thermal_cycle_electrolysis.py
```

The example reports actual H2 flow, generator heat loss, electrical-power
residual, and a combined shaft-to-reaction enthalpy/heat residual. Its test also
checks the finite operating-current rejection. This steady calculation has no
water-feed stock, product receiver or operating-duration assumption.

This level excludes a geothermal reservoir, source extraction, recuperation,
generator/motor losses, transient rotor/control dynamics and an H2 liquefaction
cold box. The existing supplied-state liquefaction benchmark remains a distinct
reversible-work calculation; it is not relabelled as an actual liquefier.
TESPy's [Rankine tutorial](https://tespy.readthedocs.io/en/stable/basic_tutorials/rankine_cycle.html)
documents the native component approach. This package's implementation and
explanations are independently authored.

## Exergy boundary conventions

`analyze_physical_exergy` receives an actual converged TESPy network and explicit
fuel/product/loss dictionaries of connection labels. In ExerPy 0.2.0,
`inputs` means additive terms and `outputs` subtractive terms **for every one of
the three dictionaries**. They must not be interpreted automatically as physical
flow directions across a plant boundary.

`analyze_rankine_exergy` supplies the thermal-cycle boundary explicitly:

- Fuel includes the hot-water physical-exergy decrease.
- Product is turbine shaft output minus pump shaft input.
- A coolant physical-exergy increase is a rejected-stream loss.
- A coolant physical-exergy decrease is an additional consumed resource, added
  to fuel. This occurs when a sufficiently cold stream warms toward the chosen
  environment even while it absorbs heat.

At 298.15 K ambient, the reference coolant consumes physical exergy. The executed
resource/product/destruction rates are approximately 80.3547/35.3925/44.9622 kW,
with zero declared coolant exergy loss. At 288.15 K ambient, the coolant gains
exergy and is counted as a loss; component and overall balances close in both
cases. The analysis retains the actual ExerPy boundary dictionaries.

Physical exergy uses a common environmental T/P reference. Chemical exergy,
formation-energy bookkeeping for reactions and kinetic/potential exergy are
outside this adapter. A chosen useful product remains an application decision;
the generic audit exposes a residual rather than inventing the missing boundary.

## Predictive two-solid redox conversion

`h2physics.storage.redox_equilibrium.TwoSolidRedoxEquilibrium` reuses
`CanteraMultiphaseEquilibrium` and `CanteraMultiphaseMolarEnthalpy`. It predicts
conversion from the supplied finite species stocks, T and P; there is no supplied
equilibrium extent. The candidate set must contain one gas, two pure solids and
exactly one independent balanced reaction. Native output is mapped back to the
existing `StoichiometricReaction.convert` kernel, with finite limits and an
explicit maximum mapping residual.

The included `iron_oxide_steam_redox` factory selects:

```text
3 FeO(s) + H2O(g) <=> Fe3O4(s) + H2(g)
```

The named material level is restricted to 900–1500 K and 10⁴–10⁶ Pa. Its gas
candidate set contains H2 and H2O only. Solids are stoichiometric FeO and Fe3O4
with constant densities supplied through `SolidDensityEvidence`. Native NASA
thermochemistry is loaded from the independently installed Cantera data files;
the actual file hashes and common-reference identities remain in the phase
specifications. This package does not redistribute those coefficient files.

```python
from h2physics.core import Origin
from h2physics.adapters.cantera_caloric import SolidDensityEvidence
from h2physics.storage.redox_equilibrium import iron_oxide_steam_redox

# These two values are deliberately labelled software-test fixtures. Replace
# them with source-qualified density evidence for an actual material study.
def fixture_density(value):
    return SolidDensityEvidence(
        value, "authored-constant-volume-fixture", Origin.SYNTHETIC,
        "synthetic density for software integration; not measured material data",
    )

redox = iron_oxide_steam_redox(
    ferrous_density=fixture_density(5700.0),
    magnetite_density=fixture_density(5200.0),
)
equilibrium = redox.equilibrate(
    {"FeO": 3.0, "H2O": 1.0, "Fe3O4": 1.0, "H2": 0.01},
    temperature_k=1100.0, pressure_pa=101325.0,
    source_id="authored-finite-feed", origin=Origin.SYNTHETIC,
)
print(equilibrium.conversion.extent_mol)
print(dict(equilibrium.conversion.final_amounts))
print(equilibrium.heat_into_j)
equilibrium.native_result.require_current()
```

Positive extent follows the written reaction; negative extent predicts its
reverse. `heat_into_j` is externally required heat at held T/P, positive into
the system, with consistent native formation references. It does not predict
heat recovery or a heat-transfer device. The full native result retains candidate
phases, equilibrium gates, element/mass/energy residuals and failure context.

This is a **restricted candidate-phase equilibrium**, not global iron/oxygen
phase stability, measured oxygen-carrier performance, a nonstoichiometric
Fe1−xO model, vacancy δ(T,pO2), solid-solution activity, porous transport,
nucleation or an intrinsic reaction-rate law. Those limitations cannot be
removed by changing a species label or fitting an arbitrary conversion factor.

## Coupling equilibrium driving to the finite-solid reactor

`redox.relaxation_kinetics(k, identifier=..., source_id=..., origin=...)` returns
the existing `SolidReactionKinetics` type. It evaluates a new equilibrium from
the current finite inventory and uses `k * max(remaining_equilibrium_extent, 0)`
in mol extent/s. `k` is in 1/s and needs material-fit provenance, or an explicit
synthetic role for a software example. It is an optional lumped relaxation
assumption; it is not inferred from equilibrium thermodynamics.

Pass `redox.caloric`, that kinetic object and matching `SolidReactionEvidence`
to `FiniteSolidReactionReactor(..., hydrogen_species="H2", water_species="H2O",
mode="hydrolysis")`. Inventories must use `redox.basis_id`. The existing reactor
owns finite supply debits, time steps, caloric roots and the heat ledger. It is
forward-only; reverse equilibrium driving gives zero forward rate. Explicit
reverse-operation modelling requires a separately oriented reaction/reactor.
The executed test constructs the actual reactor, supplies thermostat heat for
the predicted finite step and checks H2 production, final T, element and energy
balances. See `tests/test_redox_equilibrium.py` for the complete executable handoff.

Native piecewise fits retain their own join behaviour. An initial finite-reactor
check exactly at the installed NASA 1000 K polynomial join did not return the
assumed identical thermostat temperature (the solved value was about 1000.087 K).
The recorded positive coupling check uses 1100 K inside one fit branch. This is
not a repair or validation of native thermochemical coefficients; branch-crossing
calorimetry remains a specific application concern.

## Exact native definition identity

Execution exposed a redundant native serialization issue for a pure constant-
volume Fe3O4 phase: `ct.Mixture` can change a reported molar-volume field by one
floating-point ulp although native density, molecular weight and thermochemical
coefficients stay identical. The common phase fingerprint now represents that
one-species constant-volume EOS with its **exact native density**, alongside the
existing exact molecular weights and thermochemistry. It does not relax a
tolerance or ignore real changes to density/thermochemical data. Gas and other
phase fingerprints retain their earlier representation. Tests include an actual
native phase setup and changed-density/changed-thermochemistry refusals.

## Checks and continuation

Run the focused new checks and the existing owner regressions:

```text
python -m pytest -q tests/test_thermal_cycles.py tests/test_redox_equilibrium.py
python -m pytest -q tests/test_cantera_multiphase.py tests/test_cantera_caloric.py
```

The new checks use genuine installed TESPy, ExerPy, CoolProp and Cantera. They
cover native network solves, mass and energy closure, extensive scaling, a Carnot
upper bound, component/overall exergy and both coolant-resource roles, material
equilibrium forward/reverse mapping, finite-phase bounds, temperature/domain
handling, finite-reactor handoff and physical-definition change detection.
The recorded current replay passed **12 new cases** with no skips; the relevant
existing multiphase/caloric owner suites passed **33 cases**. These were separate
invocations, including a prior combined 44-case passing replay before the final
power-to-electrolysis case was added. The standalone power-coupling example was
also executed. They are software/native-connection evidence, not new measurement
comparisons or independent validation of external-engine internal physics.
Unavailable optional providers are skipped by pytest in an unprepared clone;
such a skip must never be counted as executed native evidence. No held-out
measured plant or iron-oxide conversion comparison is claimed by these tests.

For continuation, obtain source-qualified actual material densities, examine the
complete stable phase set and thermochemical reference assumptions, then define
measured conversion/calibration and independent evaluation cases. For cycle
studies, supply actual component efficiencies/maps, stream conditions and useful
product boundaries before interpreting design results as a plant prediction.

## Scientific and dependency sources

- [TESPy Rankine cycle tutorial](https://tespy.readthedocs.io/en/stable/basic_tutorials/rankine_cycle.html)
  and [fluid-property ownership](https://tespy.readthedocs.io/en/stable/advanced_features/fluid_properties.html).
- [ExerPy native-network analysis API](https://exerpy.readthedocs.io/en/stable/api/analyses.html)
  and [project source/licensing](https://github.com/oemof/exerpy).
- [TESPy project source/licensing](https://github.com/oemof/tespy).
- [Cantera thermodynamic phases and native Mixture](https://cantera.org/3.2/python/thermo.html).
- McBride, Gordon and Reno, NASA-TM-4513 (1993),
  [NASA source record](https://ntrs.nasa.gov/citations/19940013151), identified by
  the installed condensed-species file. NASA describes this report as a US
  Government work with public use permitted. Installed species/data attribution
  remains separate from this package's original-code license.

No external code, raw observations, provider data bundle or figures are embedded
in these additions. Optional packages keep their own licenses and data provenance.
