# Finite-hydride desorption to mechanical compressor inlet

`bind_finite_hydride_to_compressor()` binds each accepted outward H2 interval
from one `FiniteHydrideTrace` to one existing
`HydrogenRealFluidCompressionRun`. It creates no compression run or bed model;
both solver owners remain independent.

## Admission and ledgers

The trace must retain an accepted gas port and finite external mass and
enthalpy ledgers. Those external ledgers use positive-into-bed sign, so each
desorption interval has a negative ledger increment. The adapter negates those
increments into positive withdrawn mass and exported enthalpy for comparison
with the compressor's positive inlet flow. Every mapped interval must have
positive H2 withdrawal. The compressor run must use the same HEOS release and compatible pure-H2 property
basis as the bed. The caller selects one accepted left or right bed sample for
the compressor inlet state and supplies unique process-window identities plus
clock-alignment, hydraulic-transfer and state-projection evidence for every
interval.
The compressor input type has no physical timestamps: the process-window ID
and caller clock-alignment evidence are the only time correspondence. The
adapter does not infer compressor start/end times from sequence order.

For each interval, the adapter requires the compressor inlet pressure,
temperature, density, enthalpy, entropy, phase and hydrogen fraction to match
the selected accepted bed state. It checks that the compressor's steady mass
flow integrated over the bed interval closes to the exact outward mass ledger,
and that inlet enthalpy closes to the interval-integrated bed-port energy.
Source arrays and compressor receipts are replayed by `require_current()`;
direct construction or reissuance of the coupling receipt is rejected.

## Limits and deferred contract

The edge-state selector is explicit because the compressor API is a steady
operating point while the bed trace is transient. The energy-closure tolerance
must be tight enough for the chosen accepted interval and projection. A failed
closure requires a shorter bed interval or a better supported mapped inlet
state; this adapter does not average, interpolate or alter native states.

Deferred Hangang contract: `finite-hydride-desorption-mechanical-compressor-handoff`
under `finite-hydride`. It does not validate a compressor map, mechanical
control, piping pressure loss, valves, transfer heat, or a filling protocol.
The thermally driven `HydrideCompressor` is a different model and is not
reimplemented here.
