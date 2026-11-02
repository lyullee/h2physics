# Caller compressor-map composition for the hydrogen Brayton reference

`h2physics.combustion.compressor_map` admits a caller-supplied compressor map
whose coordinates are corrected speed and outlet-over-inlet total pressure
ratio. Bilinear interpolation is allowed only inside the supplied rectangle.
The map retains its source URI, license label, SHA-256, corrected-flow basis,
speed unit, and evidence identity. No compressor characteristic is generated
from a generic correlation.

`MapMatchedBraytonInputs` pairs one compressor point with the existing
`TurbineComponentMap` point and `run_open_cycle_brayton()` reference. Compressor
map efficiency and pressure ratio feed the existing Cantera cycle; the existing
turbine map supplies turbine efficiency. Corrected compressor air flow must
match declared inlet-air flow through an explicit caller factor. Turbine corrected
flow separately checks actual air-plus-hydrogen mass flow using its own factor.
The two corrected-speed coordinates can use different reference conventions,
so their connection is retained as a caller evidence identity rather than
silently equated.

```python
from h2physics.combustion.compressor_map import (
    CompressorComponentMap,
    MapMatchedBraytonInputs,
    run_map_matched_brayton,
)

# Build compressor_map and turbine_map from licensed, hash-pinned source data.
# Construct cycle_inputs as h2physics.combustion.OpenBraytonInputs.
inputs = MapMatchedBraytonInputs(
    cycle_inputs=cycle_inputs,
    compressor_map=compressor_map,
    compressor_corrected_speed=compressor_speed,
    compressor_pressure_ratio=compressor_ratio,
    compressor_actual_to_corrected_flow_factor=compressor_flow_factor,
    turbine_map=turbine_map,
    turbine_corrected_speed=turbine_speed,
    turbine_actual_to_corrected_flow_factor=turbine_flow_factor,
    air_mass_flow_kg_s=air_flow,
    speed_link_evidence_id="source-backed speed/reference conversion",
    compressor_flow_evidence_id="source-backed compressor flow conversion",
    turbine_flow_evidence_id="source-backed turbine flow conversion",
)
run = run_map_matched_brayton(cantera_phase, inputs)
run.require_current()
shaft_residual_w = run.shaft_residual_w
```

The residual is the computed turbine gross power less compressor input for the
selected single operating point. A positive or negative residual is not an
operating solution. The API does not search corrected speed, solve a common
shaft, infer speed/flow correction, handle surge or choke, model bleeds/cooling,
include mechanical or generator losses, or qualify a machine. Caller map values
must have compatible component, reference, operating window and licensing
evidence. The built-in deferred case uses only authored synthetic grids and
native Cantera chemistry; it is a software contract, not turbine performance
evidence.
