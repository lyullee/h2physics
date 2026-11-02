# Upper-layer oxygen composition projection

`project_layer_oxygen()` converts the retained upper-layer hydrogen mole
fraction from `TwoVentHydrogenLayerResult` into an oxygen mole-fraction trace
for one explicit binary-composition case: hydrogen plus a fixed-composition,
dry-air carrier. For each retained sample,

\[
x_{O_2,layer}=(1-x_{H_2,layer})x_{O_2,carrier}.
\]

This follows the definition of mole fraction as constituent amount divided by
total mixture amount ([IUPAC Gold Book, amount fraction](https://goldbook.iupac.org/terms/view/A00296)).
The carrier O2 fraction is supplied by the caller. For native CoolProp layer
traces it must match the actual trace carrier. The projection retains the full
normalized N2/O2/Ar tuple as `carrier_dry_air_mole_fractions`; subsequent changes
to any carrier fraction are rejected, including changes preserving O2 alone.
Historical analytical traces without backend metadata remain explicitly
caller-declared. No humidity, impurities or changing carrier composition is inserted.

```python
from h2physics.adapters.layer_oxygen_projection import project_layer_oxygen

o2_trace = project_layer_oxygen(
    layer_trace,
    carrier_basis="fixed_dry_air",
    carrier_oxygen_mole_fraction=layer_trace.dry_air_mole_fractions[1],
)
```

The projection retains the exact layer result object and timestamp tuple. It
does not make a homogeneous-room claim and does not convert the trace into a
`CanteraOxygenRoom` result. It supplies no oxygen criterion, partial pressure,
exposure-duration reconstruction, ignition condition or physiological response
law. Those remain separate calculations with their own declared assumptions.

The calculation is admissible only while the complement of hydrogen is the
declared fixed dry-air composition. It is invalid for steam, inert purge,
combustion products, oxygen enrichment, or spatially varying carrier
composition. This conversion does not repair or extend the source layer model's
still-air, fixed-temperature, single-upper-layer or one-way-vent limits.

The deferred case `two-vent-layer-dry-air-oxygen-composition-projection`
checks algebraic closure, clock/object retention and rejection of unsupported
carrier bases. It is a synthetic software contract and is not a scientific,
occupational-exposure or facility-safety validation.
