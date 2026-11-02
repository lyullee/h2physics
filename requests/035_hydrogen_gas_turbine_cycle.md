# Request 035 — Hydrogen gas-turbine cycle and combustor boundary

Status: the open Brayton reference, caller-map pair, cooling/bleed point,
staged turbine cooling, one-stage ideal-gas H2 compression and a bounded
multi-start map operating point are implemented_unverified in
`h2physics.combustion`. This request remains active for full equipment-boundary
closure, transient/control operation and independent qualification.

## Gap and ownership

The local gas equipment models cover compressor stages, prescribed intercooling,
heat exchange and rotating-equipment maps. The new `run_open_cycle_brayton()` API
does combine an air compressor, hydrogen combustor and turbine for a single steady
reference point, using caller-provided isentropic efficiencies and pressure
recovery, native Cantera HP equilibrium, and frozen-composition turbine expansion.
It is implemented_unverified; its acceptance entries are deferred. The separate
map-pair wrapper accepts caller compressor/turbine maps at one selected point. A
bounded steady solver searches three caller-declared variables against corrected-
flow and shaft-target residuals, while a distinct cooling/bleed composition
removes declared compressor air before combustion and mixes it at the turbine
inlet. A separate one-stage pure-H2 ideal-gas compressor now computes native
isentropic and efficiency-adjusted states and can debit its power from a matched
Brayton point. Real-gas high-pressure behavior, compressor maps, multistage
trains, cooling, auxiliary loads, off-design operation and qualified machine
behavior remain open. The moving-cylinder
API in `combustion.piston_engine` remains a separate reciprocating, closed-charge
level. Do not infer machine performance from either narrow reference API alone.

The reference implementation delegates gas properties and combustion equilibrium
to a caller-supplied Cantera ideal-gas phase. The map-pair composition admits
caller-supplied compressor and turbine grids, applies their efficiencies to the
existing cycle, checks separate corrected-flow links, and reports the selected-
point shaft residual. It adds no local equation of state or reaction solver. For
the remaining higher-fidelity extension, select a rights-reviewed turbine/
combustion engine to own shaft losses and off-design operation if one is adopted.
Do not copy a closed gas-turbine cycle into a second local solver.

## Remaining higher-fidelity boundary

The ideal open reference is implemented in `docs/OPEN_BRAYTON_REFERENCE.md`.
`h2physics.combustion.turbine_map` admits caller-owned turbine corrected-flow and
efficiency grids and performs bounded bilinear interpolation. The new
`run_map_bound_open_cycle_brayton()` composes one interpolated turbine point with
the single-point open reference: mapped isentropic efficiency drives the existing
native expansion, and pressure ratio plus caller-converted corrected flow must
match. The caller must provide a sourced actual-to-corrected-flow factor. This is
a turbine-boundary composition, not a complete component map or shaft solution.
Extend it only as an explicitly separate map-based single-shaft model. Require
qualified air inlet state/composition, compressor and turbine maps, combustor
pressure loss, hydrogen feed basis, mechanism and equilibrium or finite-rate
combustion choice, shaft/mechanical loss and generator efficiency. Caller-owned
values must carry units, source identity, validity range and uncertainty; no
default efficiency or pressure loss implies a validated machine.

`MapBoundBraytonInputs` and `MapBoundBraytonRun` preserve the turbine map, correction,
clock-window and flow-link evidence for this one-point reference. They do not
infer corrected-flow conventions or close shaft power. The separate
`MapMatchedBraytonInputs` pairs caller-owned compressor and turbine maps and feeds
both map efficiencies into the existing reference cycle. The result now scales its
per-kg-air compressor, gross turbine and net gas-path
work by the declared inlet-air mass flow to expose reference powers in watts; no
mechanical, generator, cooling, bleed or auxiliary terms are inferred. The new
`balance_map_bound_brayton_shaft()` accepts evidence-linked shaft mechanical loss
and generator efficiency and recomputes shaft net and electrical output from the
retained cycle. It rejects a deficit; it does not infer machine inputs or close a
coupled shaft operating point. The deferred
`hydrogen-brayton-turbine-map-boundary` case checks mapped efficiency, expansion
pressure ratio, corrected-flow linkage, mass-flow power identities, loss/generator
conversion and deficit rejection; it has not run.
The turbine map now seals its complete source metadata and grid values; interpolation
and bound result construction recheck that seal so post-admission edits are rejected.
This protects provenance binding and does not add machine physics or validation.

The separate `run_cooled_brayton_point()` boundary now reuses the existing Cantera
open-cycle runner and both admitted component-map interpolators. It removes a
declared compressor-air bleed before the combustor, passes the remaining primary
air and explicit hydrogen mass rate to the existing equilibrium stage, then mixes
the bleed once at the turbine inlet using mass-weighted species and enthalpy. The
native Cantera phase owns the mixed-state properties and frozen expansion. Map
correction factors, numerical speed link, cooling split, cooling-path pressure
drop, shaft loss and target remain caller-owned and evidence-bound. Its deferred
synthetic cases cover zero bleed, positive bleed, pressure-station rejection and
speed-link rejection. A separate `run_staged_turbine_cooling()` now advances the
frozen gas state across caller-defined expansion stages, injecting explicit
compressor-air mass and coolant enthalpy pickup after each stage. It retains
stage work, mixing energy and mass ledgers and has three deferred synthetic
contracts. This is a lumped station model: blade metal, internal passages, film
effectiveness, local aerodynamics and qualified hardware remain open.

`TurbineMapPairingReceipt` can bind one admitted LH2DT compressor-map observation
to one turbine map point only when the caller supplies explicit clock/window,
component-pairing, shaft-speed, flow-basis and pressure-ratio evidence identities.
This is a generic provenance receipt; the LH2DT compressor trace is not a gas-turbine
air-compressor result. The receipt is not cycle-state binding or shaft matching.
`CompressorOperatingPoint` and `couple_compressor_to_map_bound_brayton()` now
accept an externally computed compressor specific work and inlet-air flow when
operating-point, process-window, common-speed and flow-link evidence are supplied.
The coupled ledger reports the turbine-minus-compressor shaft residual and
rechecks both retained component results. This composes models without claiming
that the residual is zero or solving for a matched speed. The deferred map-bound
contract covers this cross-model composition; it has not run. The explicit
loss/generator ledger is also caller-parameterized accounting, not a solved
common-shaft operating point. Map correction methods, surge/choke constraints,
native off-design operation and coupled shaft closure remain unimplemented. The
higher-fidelity model should expose
per-component molar/mass flows, native
states, enthalpy changes, heat/fuel input, species and elemental balances, shaft
powers, cycle net output and independently recomputable energy residuals. Retain
all native states and solver diagnostics on both success and failure. Separate
combustor pressure/temperature limits, turbine material cooling, NOx, flashback,
autoignition, emissions, transient startup/control, recuperation and multi-spool
dynamics into explicit additional boundaries.

`run_hydrogen_compression()` supplies one steady pure-H2 compression point.
Its Cantera path is ideal-gas only; a separate CoolProp-backed route now admits
real-fluid states within the selected EOS domain.
`couple_hydrogen_compression_to_brayton()` can debit compressor power only
when fuel-feed pressure, temperature, flow ratio, mechanism identity and
operating window match the retained cycle. Neither path supplies a compressor
map, transient control or machine qualification.

## Evidence before advertising a model

The `hydrogen-engine` Nurion profile includes deferred reference-cycle contracts
for native HP equilibrium, fixed-composition turbine expansion, work signs,
element/energy closure, input rejection and forged-summary rejection. Additional
deferred contracts cover native component-map domain behavior, shaft accounting,
cooling/bleed, staged turbine cooling, single-stage fuel compression and its cycle
coupling, and relevant input/freshness guards. They have not run and do not qualify
the machinery. Compare against license-compatible public
hydrogen-capable gas-turbine data with geometry, operating point, fuel blend,
mechanism, uncertainty and rights recorded. Synthetic identities do not establish
combustor stability or machine performance.

The existing `compressor-map` profile also contains a deferred pairing-receipt case.
It requires a project fixture module that builds an original pinned-LH2DT compressor
trace and a reviewed source-hashed turbine map. The required fixture module, turbine
map URI, digest and license remain explicit placeholders in the case metadata; this
case is not runnable until project-owned fixtures and rights records are supplied.

This request covers the remaining higher-fidelity capability. The local
implemented_unverified reference is not a design recommendation or evidence of a
working or experimentally qualified gas turbine.
