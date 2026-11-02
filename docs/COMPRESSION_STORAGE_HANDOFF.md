# Real-fluid compressor to finite-mixture vessel handoff

`h2physics.adapters.bind_compression_to_mixture_receiver()` turns an issued
`HydrogenRealFluidCompressionRun` into one `MixtureVesselInterval` vapor inlet
for `run_finite_mixture_vu_intervals()`. The caller chooses an accepted
finite-mixture receiver point (and is responsible for selecting the latest
point), exact hydrogen species key, interval
clock, and evidence ID. The adapter checks the current compressor and receiver,
HEOS hydrogen identity, matching CoolProp release, component ordering and
declared/native molar mass, common CoolProp enthalpy-reference ID,
pure-hydrogen mass fraction, and compressor discharge pressure above the
receiver pressure.

For the caller-declared interval duration, the handoff computes hydrogen moles
from compressor mass flow and the receiver template's H2 molar mass. It carries
the compressor's actual outlet specific enthalpy as integrated vapor inlet
energy. The returned `CompressionMixtureHandoff` retains both native model
owners and the typed interval; `require_current()` rejects stale source,
receiver, or interval state.

This is a steady-flow stream translation into the existing finite-volume
inventory API. It does not calculate a valve or pipe flow, compressor map,
back-pressure response during the interval, pressure regulation, or thermal
loss. The receiver pressure is the caller-supplied accepted pressure at the
interval start. Rebuild the handoff from the next accepted receiver state for
each subsequent interval. The enthalpy-reference ID is a caller-declared
compatibility identity; matching IDs do not independently prove calibration or
thermochemical-reference equivalence.

The deferred case `hydrogen-compression-finite-mixture-storage-handoff`
combines a CoolProp HEOS compression point with a synthetic accepted H2/N2
receiver and submits the generated interval to the finite-mixture V/U solver.
The synthetic two-phase receiver uses a declared component/phase closure
tolerance of `2e-5` for this software contract.
It checks the mass-to-mole and enthalpy ledgers, pressure direction, ownership
freshness and accepted vessel update. The authored receiver is a software
contract, not experimental storage qualification.
