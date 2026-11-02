# Externally precooled hydrogen liquefaction network

`h2physics.adapters.liquefaction_cycle` supplies an **actual solved TESPy
network**: hydrogen gas feed → compressor → external cryogenic heat exchanger
→ Joule–Thomson valve → native liquid/vapor separator. The two hydrogen
products, component duties and utility flow are native network results using
CoolProp properties. This complements the supplied-state minimum-work benchmark
in `adapters.liquefaction_performance`; it solves a process topology rather than
inferring process performance from supplied feed/product states alone.

The cold source is a declared external material stream. Its required flow and
absorbed heat are solved, but its refrigeration plant is outside the boundary.
The reported compressor shaft input is **not total liquefaction electricity**.
No coefficient of performance, cold-box work, motor efficiency or universal
compressor efficiency is invented.

## Python use and replacement

Install the optional cycle providers using the project's declared dependency
extra or separately compatible TESPy, ExerPy and CoolProp installations. The
recorded native execution used TESPy 0.11.3, ExerPy 0.2.0 and CoolProp 8.0.0.

```python
from h2physics.adapters.liquefaction_cycle import (
    HydrogenLiquefactionSpec,
    analyze_liquefaction_exergy,
    solve_hydrogen_liquefaction,
)

# Authored demonstration, not a measured/calibrated liquefaction plant.
spec = HydrogenLiquefactionSpec(
    compressor_isentropic_efficiency=0.8,
    source_id="authored-example-not-device-qualification",
    hydrogen_fluid="Hydrogen",
    feed_mass_flow_kg_s=0.01,
    feed_temperature_k=300.0,
    feed_pressure_pa_absolute=101325.0,
    compression_pressure_pa_absolute=5_000_000.0,
    precooler_outlet_temperature_k=28.0,
    separator_pressure_pa_absolute=101325.0,
    utility_fluid="Helium",
    utility_inlet_temperature_k=15.0,
    utility_outlet_temperature_k=250.0,
    utility_pressure_pa_absolute=200000.0,
)
cycle = solve_hydrogen_liquefaction(spec)
print(cycle.audit.liquid_mass_flow_kg_s)
print(cycle.audit.compressor_shaft_input_w)
print(cycle.audit.external_cold_utility_heat_absorbed_w)

exergy = analyze_liquefaction_exergy(cycle)
print(exergy.component_destruction_w)
print(exergy.balance_residual_w)

# The ordinary native object remains available for inspection and extension.
liquid = cycle.network.get_conn("h2_liquid")
print(liquid.T.val_SI, liquid.p.val_SI, liquid.h.val_SI)
```

Efficiency is a mandatory caller input. Replace it with an operating-point
value or a separately identified compressor model. The helium utility and its
15 K source are also explicit supplied boundary conditions, not a predicted
readily available refrigeration resource. This very cold stream requires
substantial upstream exergy; omitting it would seriously misstate performance.

`Hydrogen` and `ParaHydrogen` select CoolProp's distinct native fixed fluid
conventions. The same selection is retained across feed, valve and both
products. There is no change of spin convention, ortho–para conversion heat,
converter kinetics, mixture-property substitute or silent EOS fallback.

## Solved components and ports

| Native component | Solved responsibility |
| --- | --- |
| `hydrogen_compressor` | Shaft power and outlet enthalpy from the supplied isentropic efficiency and pressure |
| `external_cryogenic_precooler` | Hydrogen cooling and matched external-utility heat/flow, with specified terminal states and pressure ratios |
| `jt_valve` | Isenthalpic expansion to separator pressure |
| `hydrogen_phase_separator` | Equilibrium saturated-liquid and saturated-vapor flows at common pressure |

Connection labels are `h2_feed`, `h2_compressed`, `h2_precooled`,
`h2_jt_outlet`, `h2_liquid`, `h2_vapor`, `cold_in`, `cold_out`, and the
`compressor_shaft` power connection. All public pressures are absolute Pa,
temperatures K, enthalpies J/kg, mass flows kg/s, and heat/power W. TESPy default
units are explicitly replaced at construction.

The cryocooler is a two-stream native `SectionedHeatExchanger`. The selected level
specifies its hydrogen outlet temperature and both utility temperatures; it
solves the utility flow required by those states. Terminal temperature crossing
is rejected. The native component also evaluates a pressure/enthalpy section
profile with CoolProp and reports `td_pinch`; the host rejects a nonpositive
sampled internal approach. The default is 128 sections; `precooler_sections`
controls refinement. The audit records its sampled minimum approach and section
count. This finite-grid check can miss a narrower unsampled minimum; it is not
continuous pinch proof or exchanger-area qualification. Refinement belongs to
the declared operating case, especially near strong property changes.
There is no exchanger sizing, pressure-drop geometry, multi-pass cold-box
design or component map qualification.

Before solving the native two-product separator, direct CoolProp states check
that JT inlet enthalpy lies strictly between the saturated liquid and vapor
enthalpies at separator pressure. A warm JT feed or a fully subcooled outlet
raises `NoTwoPhaseLiquefactionError`, retaining those three enthalpies. This
model does not manufacture negative product flows, clip a vapor fraction, or
claim that an all-vapor feed yields liquid. A fully liquid process needs a
different outlet topology rather than an artificial zero-vapor separator.
The compressor also requires a native single-gas inlet state.

## Accounting and evidence

`LiquefactionCycleAudit` records liquid/vapor flows, liquid fraction, compressor
shaft input, external cold duty and utility flow. It retains overall hydrogen
first-law, utility heat, separator mass/energy and valve enthalpy residuals,
together with actual TESPy/CoolProp versions. The first law uses a common
native fluid enthalpy reference throughout:

```text
Hdot_feed + Wdot_compressor - Qdot_external_cold - Hdot_liquid - Hdot_vapor = 0
Qdot_external_cold = mdot_utility * (h_utility_out - h_utility_in)
Hdot_JT_out = Hdot_liquid + Hdot_vapor
h_JT_out = h_precooled
```

The native actual-network ExerPy handoff reuses
`thermal_cycles.analyze_physical_exergy`. Its helper's declared fuel boundary is
compressor shaft work, feed physical exergy, and the cold stream's physical
exergy decrease. Both hydrogen streams are declared material products at this
open-process boundary; this does not mean the vapor is liquefied product or
that a vapor recovery train has been solved. Applications treating vapor as a
loss can call the generic exergy API with their own explicit boundaries.
The helper rejects a cold-utility boundary that does not consume physical
exergy under the selected environment reference. No chemical exergy or
reaction formation reference is mixed into the calculation.

The actual authored 0.01 kg/s example solved to approximately 0.007248878 kg/s
liquid and 0.002751122 kg/s vapor, with 111007.6 W compressor shaft input and
149355.9 W external cold duty. The high liquid yield depends on the supplied
28 K hydrogen precooling state and the costly external 15 K cold stream.
It is not a prediction of a self-contained Linde refrigerator's yield or SEC.
The component physical-exergy destruction sum was approximately 393981.5 W;
the native total exergy-balance residual was zero at displayed precision.
These values are solver evidence on authored conditions, not measurements.

The solved `network` is intentionally editable for deep Python integration.
The frozen audit is a snapshot of its original solve. After changing native
component specifications, solve and re-audit the changed topology; do not
represent the original audit as evidence for a modified network.

## Verification and continuation

Run the bounded suite with:

```text
python -m pytest -q tests/test_liquefaction_cycle.py
```

The final recorded native run on 2026-11-03 completed **12 passing tests** in
18.21 seconds with the sectioned heat exchanger and provider versions stated above.

It covers a real native solve, an independent direct-CoolProp phase lever rule,
saturated product states, overall/component mass and energy balances,
isenthalpic expansion, extensive flow scaling, native ExerPy component handoff,
nonproducing warm-feed rejection, liquid compressor-feed rejection and selected
input domains. These checks verify new host topology/accounting and delivery;
they do not revalidate CoolProp/TESPy/ExerPy internal physics.

Higher levels can add recuperation, vapor recycling, staged compression,
matched refrigerant machinery, ortho–para conversion through the existing
appropriate owner, internal pinch analysis, equipment maps and finite storage.
Actual plant electricity and measured performance require those boundaries and
independent operating data. None is inferred from a converged single-pass
example.

Primary API references: [TESPy heat exchangers](https://tespy.readthedocs.io/en/stable/api/tespy.components.heat_exchangers.html),
[TESPy phase-separator components](https://tespy.readthedocs.io/en/stable/api/tespy.components.nodes.html),
[CoolProp Hydrogen](https://coolprop.org/fluid_properties/fluids/Hydrogen.html),
[CoolProp ParaHydrogen](https://coolprop.org/fluid_properties/fluids/ParaHydrogen.html),
and [ExerPy API](https://exerpy.readthedocs.io/en/stable/api.html).
External engine code, mechanisms, vendor tables and observations are not
redistributed by this model.
