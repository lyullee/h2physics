# Adsorption product to pipeline linepack boundary

`h2physics.adapters.charge_linepack_from_adsorption_product` connects the
existing finite adsorption-vessel delivery ledger to an existing pipeline
inventory. The same Python API and `AdsorptionLinepackCharge` receipt accept:

- `RealGasLinepackState` with direct `CoolPropIsothermalEOS` HEOS for
  `Hydrogen`, `ParaHydrogen` or `OrthoHydrogen`;
- `IsothermalLinepackState` as an explicitly selected analytic reference.

The native option uses the original linepack owner's `advance()` operation.
CoolProp evaluates the receiving inventory pressure from its mass density and
held temperature. The adapter supplies no additional fluid EOS or flow solver.

## Native use

```python
from h2physics.adapters import charge_linepack_from_adsorption_product
from h2physics.real_gas_linepack import RealGasLinepackState
from h2physics.thermo import CoolPropIsothermalEOS

initial_linepack = RealGasLinepackState.from_pressure(
    volume_m3=2.0,
    temperature_k=293.15,
    pressure_pa=5.0e6,
    eos=CoolPropIsothermalEOS("Hydrogen"),
    time_s=120.0,
    minimum_pressure_pa=1.0e5,
    maximum_pressure_pa=2.0e7,
)
receipt = charge_linepack_from_adsorption_product(
    initial_linepack,
    accepted_product_mass_flow,
    start_time_s=initial_linepack.time_s,
    end_time_s=initial_linepack.time_s + accepted_product_mass_flow.elapsed_s,
    minimum_mass_kg=0.01,
    time_mapping_evidence_id="caller-common-clock-window",
    hydrogen_basis_evidence_id="caller-selected-H2-product-basis",
    transfer_boundary_evidence_id="caller-injection-path-and-interface-basis",
    hydrogen_spin_composition="normal",
    hydrogen_spin_evidence_id="caller-source-spin-mapping-evidence",
)
receipt.require_current()
```

The numerical dimensions, state and clock in this example are authored
scenario inputs. `accepted_product_mass_flow` must come from an admitted
`AdsorptionVesselDelivery` through `AdsorptionProductMassFlow`.

## Species, spin and provenance gates

The selected delivered product must be exactly `("H2",)`. Its molar mass must
match the actual native fluid definition, and the charged/discharged source
property bases must remain compatible. A source explicitly identified as a
non-hydrogen native fluid, or with `no-molecular-H2` composition, is rejected.
A caller spin declaration cannot override that contradiction.

The two new optional keyword arguments are:

- `hydrogen_spin_composition`: exactly `"normal"`, `"para"` or `"ortho"`;
- `hydrogen_spin_evidence_id`: a nonempty caller evidence identity.

For a source with a known spin basis, the receipt can obtain that spin from
the retained source endpoints. A supplied declaration must agree with it.
The native target fluid must match the same spin; this API does not perform
spin conversion. A source whose spin is unresolved, including the frozen
mixture provider's `mixture-H2-spin-unresolved` basis, requires both explicit
keywords for native charging. Unknown or mismatched spin is rejected. That
explicit mapping remains a caller boundary claim with retained evidence;
it does not qualify the source spin through native data or measurements.
An optional supplied evidence identity must be nonempty whenever present.

The existing analytic-reference path remains available with its explicit H2
molar-mass basis. It does not acquire a native spin qualification from its
ideal inventory equation.

## Clock, mass and native-owner checks

The caller maps the delivery averaging interval to an increasing absolute
pipeline interval. Its start must equal the linepack time; its duration must
match `product.elapsed_s` with relative tolerance `1e-12` and absolute
tolerance `1e-12 s`. The
accepted linepack ledger must reproduce the requested start and end exactly.
The source's endpoint quotient defines an interval-average mass rate, rather
than a measured or predicted time-resolved delivery profile.

The receipt preserves the original product, initial/final inventory, accepted
mass ledger and evidence identities. `require_current()` rechecks source
issuance/currentness, native EOS identity and methods, native state pointer,
fluid/version/spin/molar mass, endpoint pressure recovery, time and mass
closure. The final inventory must retain the same EOS owner and held volume
and temperature. Source or EOS mutation and receipt cloning are rejected.

## Physical limits

This is a mass-inventory connection. Source pressure and temperature endpoints
do not establish a transfer trajectory or an integrated outlet enthalpy. The
receipt does not infer source enthalpy, conditioning heat, compression work,
purification, pressure compatibility or thermal control. Caller evidence must
account for the physical injection path, product selection and pressure/thermal
interface. Selecting the H2 component of a mixed-source ledger does not solve
a separator or demonstrate product purity. No complete process-energy balance
is claimed by the mass receipt.

## Executed local verification — 2026-11-01

With the existing Conda Python 3.12 environment and CoolProp 8.0.0, all three
`validation/cases/storage_product_delivery.py` contracts passed locally:

- `adsorption-delivery-component-mass-flow`: source-projection and issuance
  checks, with 0.6273927307798508 kg selected product in the authored mixture;
- `adsorption-product-h2-linepack-charge-handoff`: legacy analytic-reference
  charging and its two invalid-boundary rejection checks;
- `adsorption-product-native-real-gas-h2-linepack-charge`: native charging,
  explicit unresolved-mixture spin mapping and 15 invalid-input/mutation paths.

The native pure-H2 zero-uptake-limit case transferred
0.5489952138406358 kg. Receiving inventory increased by
0.5489952138406355 kg, pressure changed from 5,000,000 Pa to
5,352,985.210522568 Pa, and the accepted mass residual was
2.220446049250313e-16 kg. The zero-uptake source is a numerical limit using
native gas properties, not measured adsorbent performance. The mixed-source
claim was checked separately; it is not source-spin measurement evidence.

The fifteen rejections cover absent unresolved-source spin/mapping evidence,
contradictory source spin, wrong native target spin/fluid, wrong product molar
mass, a known non-H2 source alias, clock mismatch, receipt cloning and changed
EOS version/fluid/callables/source identity/spin evidence. Each retained
receipt was current again after restoration. Ruff and scoped whitespace checks
passed. These are numerical/component-contract results; independent material,
process and facility validation and remote replay of this revision remain open.
