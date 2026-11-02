# Finite isothermal pipe-end reservoir contract

## Purpose and scope

`FiniteIsothermalPipeReservoir` represents a fixed-volume, fixed-temperature
gas inventory attached to one endpoint of the branched isothermal pipe-wave
network. It obtains endpoint pressure from its current mass and the same
single-phase isothermal EOS identity used by the network. The inventory is
changed by the signed endpoint mass flux already used to update the adjacent
pipe cell; this adds a storage balance without introducing a second boundary
flow calculation.

This differs from `FiniteReservoirPressureBoundary`. That existing boundary is
a caller-owned pressure-versus-time history. Its name describes a reservoir
source, but it does not own or deplete reservoir mass. Its accumulated exchange
is external to the modeled pipe. The finite-inventory contract instead treats
pipe and reservoir as one mass-conserving domain: positive pipe-outward flux
means reservoir mass decreases while pipe mass increases.

## State ownership and equations

The caller supplies a unique reservoir ID and node ID, state owner and
evidence IDs, a shared clock ID, EOS identity, fixed temperature and vessel
volume, initial mass, admissible mass bounds, and explicit state origin. For
reservoir mass `m` and volume `V`, the EOS is evaluated at `rho = m/V` and the
declared temperature. The resulting pressure is replayed through the inverse
EOS density relation; identity mismatch or failure to close is rejected.

For one accepted network step of duration `dt`, let `F_out` be the exact signed
Rusanov mass rate at the endpoint, positive from reservoir into pipe. The
inventory update is `m_next = m_current - dt*F_out`. No rate clipping is
performed. The endpoint step rejects if the new mass crosses its caller-defined
floor or ceiling, if the EOS cannot represent the current state, or if the
endpoint velocity is sonic or supersonic. The network implementation must
record reservoir mass and pressure at every network sample and verify
`(M_pipe + M_reservoir) - (M_pipe,0 + M_reservoir,0) = 0` to numerical
tolerance. Junction flows remain internal and cancel in the global ledger.

## Assumptions and exclusions

- Reservoir volume and temperature are constant; no reservoir energy balance,
  heat transfer, stratification, regulator, valve, or wall loss is solved.
- The reservoir is a well-mixed, single-phase endpoint state. Two-phase states
  and unsupported EOS domains must fail explicitly.
- Flow is coupled directly through the adjacent network endpoint numerical
  flux. No separate orifice/discharge law is implied.
- The pressure-history boundary remains available for externally prescribed
  source states. It must not be interpreted as an inventory model.
- These contracts are synthetic software checks, not validation against a
  physical storage vessel or a safety certification result.

## Python API

Construct `FiniteIsothermalPipeReservoir` with explicit state provenance and
its fixed-volume thermodynamic state. `pressure_at_mass(mass_kg, eos)` checks
the EOS identity and pressure-density round trip. `advance(...)` applies an
already-computed signed endpoint mass flow without recomputing it.
`require_subsonic(...)` evaluates the characteristic scope at the endpoint.
The network adapter is responsible for applying the same flux to both the pipe
finite-volume update and the reservoir ledger, then exposing the combined
inventory trace.

## Implementation lineage

The network's pipe equations and junction context are discussed by Banda,
Herty & Klar, “Coupling conditions for gas networks governed by the isothermal
Euler equations,” *Networks and Heterogeneous Media* 1(2), 295–314 (2006),
[DOI: 10.3934/nhm.2006.1.295](https://doi.org/10.3934/nhm.2006.1.295). The
finite-volume conservation framework is presented in LeVeque, *Finite Volume
Methods for Hyperbolic Problems* (Cambridge University Press, 2002),
[publisher page](https://www.cambridge.org/core/books/finite-volume-methods-for-hyperbolic-problems/). EOS property calls follow the
[CoolProp low-level API](https://coolprop.org/coolprop/LowLevelAPI.html). The
state interface and coupling are independently formulated for this
repository; no third-party source code, text, figures, or datasets are copied.
