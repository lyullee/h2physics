# Compressor map admission

`MappedCompressor` evaluates original `Lh2dtCompressorStage` points and admits
them against a caller-supplied, evidence-bearing corrected-coordinate envelope.
The native stage remains responsible for compression thermodynamics and shaft
power.

The map declares reference temperature and absolute pressure. Corrected inlet
mass flow and shaft speed are calculated explicitly. Linear interpolation occurs
only between ordered speed lines; extrapolation is rejected. Each line gives
surge/choke-style flow limits and admissible pressure-ratio/efficiency intervals.
These limits are data, not a new compressor performance correlation.

`CompressorCommand` supplies an exact clock, shaft speed, throughput and mode.
It can describe a startup schedule, but no rotor inertia, motor, controller,
thermal storage or transient gas path is solved. Isolation is the existing ideal
zero-flow native boundary. Actual manufacturer maps, uncertainty, rotating stall,
surge dynamics and independent apparatus qualification remain open.

The `compressor-map` Nurion profile and all original compressor/property suites
must pass before this source-only composition can be called executed.

The 2026-10-29 Nurion replay exposed a pairing bug in adjacent speed-line and
schedule checks: these loops compare each sequence with its one-element-shorter
shift, so `zip(..., strict=True)` rejected valid input before interpolation or native
admission. The comparisons now use ordinary adjacent pairing. The original failed
outcomes remain recorded; rerun the three affected compressor-map cases under the
next correct provider environment before claiming execution.
