# Request 037 — Native HyRAM input for finite time-varying hydrogen sources

## Purpose

Add a supported Python entrypoint in the receiving HyRAM project for a
caller-owned, finite hydrogen release history produced by an upstream process
or pipe model. The input must preserve the source flow already solved by that
process. HyRAM must not silently solve a second independent orifice/nozzle flow
and substitute the resulting rate.

This request follows the host implementation of a finite isothermal pipeline
reservoir coupled to a shared nozzle. The host exposes a source projection
whose left-hold integrated mass is checked against the exact mass debited from
the reservoir. That projection may vary in time; the current single-state
HyRAM adapter cannot represent its changing source history without choosing a
new modelling level.

## Existing host-side contract

The upstream Python API is `IsothermalPipeNetworkTrace.project_nozzle_source()`
and returns `NozzleSourceProjection`. It retains a `SourceHistory`, source
location, opening and a finite `IntervalMassSource`. The host has already
calculated each shared-nozzle rate and withdrawn its left-hold integral from
the reservoir. Host identities and the EOS-to-caloric mapping are checked
before projection. The source is **not** a HyRAM result and no atmospheric
dispersion is inferred from the projection.

The direct `run_hyram_gas_jet()` boundary accepts one upstream and ambient
`ThermoState` plus an opening; the native HyRAM `Jet` determines its own
stationary orifice mass flow. Passing that interface a precomputed time series
would either discard the time history or duplicate the flow calculation.

## Requested receiver API

Expose a direct Python API over immutable typed source objects or NumPy arrays;
do not require JSON, HTTP, a server, or a copied host implementation. The exact
public names are for the receiving maintainers to choose. The boundary must
accept, at minimum:

- strictly increasing absolute source times and the caller's clock identifier;
- H2 mass flow for every source interval, in kg/s, with explicit interval
  semantics (the host projection uses left-hold);
- matching upstream stagnation pressure and temperature samples, H2 identity,
  composition basis, source location/frame, and source evidence identity;
- an explicit choice between a new plume-memory transient method and a set of
  independent quasi-steady snapshots;
- caller-owned native atmosphere/property objects and documented solver options.

The API must reject nonfinite/negative flow, mismatched array lengths, repeated
or reversed time, ambiguous clock offsets, unsupported source phases or mixture
basis, and out-of-domain atmosphere/source states. It must retain the actual
native HyRAM result or per-snapshot results and identify the exact method used.
Every result must expose the requested and accepted source series, source-plane
mass closure, native solver acceptance, clock/window and failure result.

### Flow ownership

For a supplied finite source mode, HyRAM must consume the caller's H2 flow as
the declared source boundary or return an explicit incompatibility. It must
not run an orifice equation to replace that rate. If a native method requires
its own opening calculation, that is a separate stationary mode and must be
identified as such; it cannot claim to preserve the host source ledger.

### Transient versus snapshot behavior

A plume-memory solver may claim a transient result only when it evolves the
atmospheric state using the time-varying source with a declared absolute clock
and interval integration. Independent stationary HyRAM runs at selected
intervals are acceptable as a distinct quasi-steady snapshot method. Snapshot
outputs must not imply plume memory, inter-snapshot interpolation, or
continuous-time exposure.

## Acceptance contracts

Add native tests/cases for all of the following without weakening existing
stationary solver gates:

1. A constant source over one interval reproduces the corresponding stationary
   result within a predeclared numerical tolerance when the same native model
   assumptions are used.
2. A two-level time-varying source preserves interval order, absolute clock,
   location, and integrated supplied mass; deliberately permuting rates or
   shifting a clock is rejected or changes the retained source declaration.
3. A source-plane mass-flow mismatch is reported independently from plume
   numerical acceptance; an explicit tolerance controls admission.
4. Zero-flow intervals, interval-window truncation, and end-of-window behavior
   have defined and tested outcomes without inventing a residual release.
5. Solver failure retains the native failure object and the exact source
   interval at which it occurred. A failed transient run cannot be returned as
   an accepted snapshot or vice versa.
6. Results bind the original solver, forcing arrays, atmosphere, property
   basis, clock and solver options; mutation or reconstruction cannot inherit
   an earlier accepted flag.
7. If only quasi-steady snapshots are implemented, the returned type and
   documentation state that limitation and provide no transient-dose claim.

## Evidence and scope

This is an API and solver-capability request, not permission to claim that a
given HyRAM release has transient plume physics. The receiving project should
identify which component owns source expansion and which owns atmospheric
transport, document the supported hydrogen/ambient domain, and retain its own
license and provenance rules. The host remains an optional separately
installed provider; no HyRAM source code, equations, tables, or prose are to be
copied into this repository.

The host contract is registered in
`validation/cases/finite_reservoir_nozzle_sink.py`. It checks only source and
reservoir mass closure, EOS identity mapping and rejection behavior. A separate
native HyRAM contract will be required after the receiving API exists. No
HyRAM dispersion result is claimed by this request.

The host now exposes `adapters.run_hyram_finite_source_snapshots()` as an
independent quasi-steady orchestration boundary. It requires an injected
fixed-flow receiver and checks the returned source-plane H2 rate against every
left-hold interval. The existing native stationary HyRAM adapter remains
incompatible because it computes its own orifice rate. The host API does not
implement any receiving-project change, plume-memory solver or scientific
validation, so the request remains open for the receiver maintainers.
