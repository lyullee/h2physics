# Premixed material-front coding record

2026-10-28. Added an original discrete material-path composition of existing
native premixed flame, native HP material equilibrium and SciPy shortest paths.
The native chemistry solvers remain unchanged. This adds conditional propagation
times, finite parcel burn/expansion ledgers and material thermal-band passage;
it does not claim a geographical accident flame or dose model.

Scientific calculation/import, native installation, example/case invocation,
pytest, benchmark and remote submission counts are all zero for this wave.
Source/API/license inspection, AST and Ruff are the only permitted local checks.
Four new acceptance definitions remain pending in the `flash-front` profile.

The six-neighbour network has directional path bias. Its scope is deliberately
recorded rather than hidden by a fictitious continuum convergence claim. It
must not be reused as obstacle-resolved dispersion. Expanding HP burned parcels
retain the original initial-material lattice solely for bookkeeping; their final
volume is not a solved flow field. Fixed-person thermal exposure, ignition,
turbulence, acceleration and field validation remain open work.

The initial coding checkpoint reused CanteraGas._phase for native phase creation.
The subsequent public API increment now uses create_phase handles and explicit
bind_phase snapshots/source checks instead. The example uses from_yaml for exact
top-level source-byte identity, while ordinary legacy callbacks remain explicitly
unverified. No EOS or mechanism check is duplicated in this consumer. Mechanism
source is read from the installed distribution at execution time, never vendored.

Rights: existing Cantera BSD-3-Clause and SciPy BSD licenses remain the dependency
basis. Public native API references are in FLASH_FRONT.md. No external empirical
flammability/flame-speed correlation, parameter table or solver code is copied.

Static peer review identified loss of positive relative travel/residence at large
absolute epochs. The public run API now requires a clock projection error
budget, rejects lost positive spans/over-budget projections, and records the
budget in the trace. A deferred large-epoch rejection was added to the existing
binding case. A targeted second static review found no further concrete defect;
this is not runtime validation. No scientific execution occurred.

The public phase-factory follow-up retains four deferred front cases and adds
factory/source/state/domain/lifecycle guards inside the existing binding case.
Public definition-only source bindings permit the native flame's working state
to evolve; separate unburned/burned state bindings are frozen. Native HP, warm
material frame, relative/absolute clock and all previous rejection gates remain.
Factory/HP construction failures retain original native context through the
public factory error or existing PremixedReferenceError prefix. Current API
changes are unverified and do not create another physical family. Details and
before/after hashes are in cantera_factory_development.md; no native import,
test, case invocation or scientific execution was performed for this follow-up.

A final static SI review confirmed scalar snapshots already use explicit native
mass density and found remaining basis-sensitive flame-array aliases. The actual
installed native source and official3.2 API expose `FlameBase.density_mass`;
fingerprints, mass-flux admission and saved fields now use that array. Native
initial-guess code itself uses `gas.density`, so the shared free-flame entry
rejects molar display basis before native construction, retaining the original
phase without reset. The existing binding case defines scalar/vector and finite
mass/U/PV display-basis invariance plus that setup rejection. These are unrun
definitions; case count remains four and no additional family is claimed.
