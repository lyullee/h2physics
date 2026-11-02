# Electrolysis product to hydrogen compressor inlet

`bind_electrolysis_compressor_inlet()` binds an admitted `PVElectrolysisTrace`
to the existing `HydrogenRealFluidCompressionInputs` contract. It returns a
freshness-checked receipt and the compressor inputs remain directly usable by
`run_real_fluid_hydrogen_compression()`.

The adapter requires the exact product receiver pressure and temperature, a
compatible CoolProp HEOS property basis, the original producer clock, a draw
window beginning at or after production completion, and a caller-declared
provider/process-window/transfer identity. The withdrawal mass over that
window may not exceed the net H2 moles added during the accepted electrolyzer
trace, converted with its retained molar mass. A pre-existing receiver heel
is not counted as production or available withdrawal.

No regulator, connecting line, intermediate storage pressure trajectory,
temperature conditioning, efficiency, or compressor solution is inferred.
The stage input is steady over the caller-selected draw window; this is a
finite batch availability check, not a dynamic source-pressure simulation.

Deferred Hangang case: `pv-electrolysis-real-fluid-compressor-inlet-handoff`
under `pv-electrolysis`. It checks the Python input boundary and does not run
the compressor solver.
