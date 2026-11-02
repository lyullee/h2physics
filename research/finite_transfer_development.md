# Finite hydrogen transfer coding record

2026-10-28. Status **implemented_unverified**, no extra executed family.
No native/project/model import, calculation, test, case discovery/invocation,
example, installation, benchmark or job was performed. Permitted evidence is
original source/API reading, public primary HTML references, AST/Ruff/LF and
source-byte checks only. No current result is promoted from historical passes.

Owned five new files: adapter `lh2dt_finite_transfer.py`, docs/FINITE_TRANSFER.md,
this record, examples/finite_transfer.py and validation/cases/finite_transfer.py.
No shared source, catalog, README, central documentation or other repository was
changed. Existing native MIT rights/receipts in research/native_lh2dt.toml remain
the dependency basis; there is no new dependency or bundled native code/data.

## Reuse and resolved boundaries

The composition reuses actual native HomogeneousTank states/cores, optional
DynamicHEMPipe with both original hydraulic halves, SteadyNetwork and
DynamicNetworkSimulator. The original shared nozzle/valve and checked
Lh2dtDynamicEquipment driver own flow, equations, simultaneous RK stages and
accepted-solution identity matching. The host partitions prescribed stages into
accepted native windows to retain an inspectable audited prefix; it adds no ODE,
pressure solver, friction equation, nozzle implementation or charging control.

Both endpoint inventories are finite; no delivery reservoir is substituted.
Native signed boundary mass, transported enthalpy and ambient heat integrals
feed per-body/global U and mass ledgers. Optional line storage is retained, so
source withdrawal is distinguished from receiver uptake. Only adiabatic,
same-height hydraulic links are admitted. Tank bulk enthalpy is the native
outflow reference; no phase-selective withdrawal or nozzle kinetic-energy double
counting is introduced. Pressure, spin, phase, source/port identity and original
energy reference are explicit across every boundary.

Original ambient TimeSeries are revalidated and bound by clock/mask/data bytes.
No extrapolation, invalid-sample fill or measured clock alignment occurs. The
line keeps the native fixed ambient contract rather than inventing time-varying
hose data. Caller schedules explicitly give both valve fractions for a stored
line, stages, mode, support and evidence. Reverse flow remains signed and uses
the caller's existing explicit shared-valve permission.

Accepted-sample stopping retains its actual time bracket and threshold overshoot;
it does not claim root localization or unseen-crossing completeness. Hard native
EOS/phase/domain/floor failures retain the earlier audited prefix. Required
completion action can apply explicit ideal isolation, retaining pre/post flow
snapshots without resetting inventory. Numerical horizon alone never implies
physical isolation. Native simulator failures expose no accepted row inside the
failing interval until their public method returns; this gap is recorded rather
than filled. A receiving native accepted-step streaming hook would avoid needing
one-window driver orchestration while retaining a complete native failure prefix.

The public result guard binds original native objects and callable/source
provenance through the existing Lh2dtNativeProvenance utility, and rejects stale
rows, summaries, references, histories, topology and modes. Its owner registry
is weak; requested native history is retained by the trace itself. No universal
tamper-proof or independent callback-parameter calibration is claimed.

## Deferred definitions and limitations

Eight cases/profile `finite-transfer`: two-tank pressure/inventory response;
isolation with remaining mass; actual optional line/hydraulic halves; one-way
versus explicitly signed reversal; accepted-sample mass stopping; retained
domain-stress prefix; original-row/cached-summary/history/clock guards; and
native maximum-step refinement. No cases() call or scientific entrypoint was
executed. The source uses synthetic warm normal-H2 inputs and a clearly extreme
positive ambient solely for domain rejection. These are not apparatus data,
calibrated vessel/line properties or an inferred process heat source.

Cold multiphase transfer, stratified port selection, phase slip, hose dynamics,
real valves/actuators, vehicle-tank thermal performance, SAE/ISO protocols and
qualified flow/temperature control remain outside this increment. Native HEM
transition/pressure-network failures are retained without alternate correlations.
Static code existence is not numerical or measured validation. Existing source
and new before/after byte identities are listed below after final static review.

Primary source/API links are in [FINITE_TRANSFER.md](../docs/FINITE_TRANSFER.md).
All explanations, orchestration and acceptance definitions are original.

## Static source record

AST parsing, Ruff, LF and trailing-whitespace checks passed for all three new
Python files. AST counted eight metadata case definitions without importing or
calling their catalog. No test or numerical acceptance result exists for these
bytes. All five owned files were new; before SHA is therefore unavailable.

| New Python input | Current unexecuted SHA256 |
| --- | --- |
| src/h2physics/adapters/lh2dt_finite_transfer.py | `4b01002cf9b047e1b4c3036c0123ebf2029e06b68ac2b4a22e6bdb1daf7c0502` |
| examples/finite_transfer.py | `ac99397d548b7a766619fa0142ad8dea9c415cbf18e9eb21e129075b4e47ae0f` |
| validation/cases/finite_transfer.py | `55130cfb2f36cfcd5bccdd909f06d65ed6db3076bbf4aee658fb7e2fb6aff884` |

Statically read native aggregate before/after is unchanged:
`5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.
This is file-byte inspection, not an executed native provenance gate.

| Existing native source | SHA256 |
| --- | --- |
| dynamic_network.py | `9a16013db2668e28b1d03b64cad4e407c87e6e9c61c87d25e43d53dfd8a45ff1` |
| dynamic_pipe.py | `fee8293c9cbc9972728b64768a6804f8406c12e89380b45bd98f52f4ab14e89b` |
| tank.py | `b921a604a9ee27b87db41737964bfe9ea111bc66a1a0ee7a237c646fba385c22` |
| network.py | `d2437197f11fb3471eb571df8abf09b1c4b3cc81bccaffbbc5a2b8cc91ebe759` |
| valve.py | `042c9cf014d78e69a0bc59982fcf4ac8752c657572b4d9e3371cd3e22c28d9e0` |

| Unchanged shared host input | SHA256 |
| --- | --- |
| src/h2physics/adapters/lh2dt_compressor.py | `73c8cb92b2079b340bcb07d9ad2d434bfa0290289b4d5a0d500e262cd924412f` |
| src/h2physics/adapters/lh2dt_heat_exchanger.py | `d8c8bc3cbfaee0f1a2e3e1a8b9538a2dae6e523572f7b9b0698c3045f9bf4a4b` |
| src/h2physics/adapters/lh2dt_dynamics.py | `24d47555c295cfd7850459933a2077b1c37bf5ffcffa292045b962cd93daec69` |
| src/h2physics/adapters/lh2dt_equipment.py | `87c29e0b47f35da3e38baf4ca2ce1832f58a91104701a95c144e5e30f7080b33` |
| src/h2physics/release.py | `eba90eb0ad07209a00b29410fea9cf2018b5225533206860ea36830d1f9e3f45` |

Final documentation/report hashes are sent separately to avoid self-reference.
