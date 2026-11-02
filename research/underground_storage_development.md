# Underground native development checkpoint

Status `implemented_unverified`. All native scientific execution is deferred to
Nurion. No provider installation/import/model, pytest, example, case, replay or
benchmark was executed locally. Static AST/TOML/Ruff/LF checks do not supply a
numerical pass. No underground family acceptance or measured validation is claimed.

The source-only review selected actual Sandia UH2SC at revision
d5057350df4d86c5c11a22e76beca24275518c8c. Its complete Model contains finite dry gas,
pure-water surrogate, water vapor, native ideal adiabatic well and transient radial
ground heat storage. Calling this actual whole model avoids duplicating the
existing Cantera/LH2DT gas ODE or writing another rock-conduction engine. Existing
strict direct CoolPropProperties supplies independent common-reference inventories.

The pyproject declares1.0.0, while package __version__ is0.0.0. The adapter records
both labels and enforces source/schema SHA. License is Revised BSD/BSD-3-Clause;
HydDown-origin files retain MIT notices. Source/license/schema files were read
only under ignored artifacts/underground_provider_review/uh2sc. No third-party
implementation, input deck, data/model coefficients or worked example is bundled.
The original example is an authored synthetic Python mapping, not copied native
test data. Isolated installation/build/version and transitive rights lock remain
pending. No environment was changed.

Native API inspection covered Model(inp,solver_options,get_independent_vars),
Model.run(), actual components/global_indices, solutions/independent_vars and
their descriptions, SaltCavern, Well and
ImplicitEulerAxisymmetricRadialHeatTransfer. The one-well native implementation
currently has algebraic adiabatic well endpoints; no finite well inventory or
well-to-rock heat exchange is claimed. The cavern and surrounding thermal nodes
are finite. Native frozen geometry does not solve creep/fracture/leakage.

The host independently counts H2, liquid water and water vapor; reconstructs
internal energy with direct EOS; counts all finite native ground node capacities
from cylindrical dual volumes; and integrates actual signed mass/enthalpy and
rock/farfield boundary heat over native implicit steps. EOS mass/volume/partial-P,
phase, P/T, complete output support and original requested-flow integral gates
are strict. Omitted mechanical energies require explicit evidence. No native
reported enthalpy energy is used as a substitute for U. The fluid/rock/boundary
audits remain separate so one cancellation cannot mask a bad native ground ledger.

Retained static concerns: native GHE range(0,n) uses Cg[idx-1] and Qg[idx-1]; n+1
positive node capacities/temperatures coexist with n transient residuals and a
boundary constraint. The named radial-thickness argument is divided by two to
form actual outer radius. Native cavern stored energy is h*m plus a separate
pressure/expansion convention. None was patched, recalibrated or runtime tested.
The independent gates may reject dynamic cases; such rejection must remain visible
and must not promote a merely installed facade to accepted underground storage.

Prepared dormant cases, all profile underground-storage: equilibrium,
rock-exchange, injection-withdrawal and refinement. The handler stores rejected
actual native prefixes and re-raises native/audit failures. It cannot assign a
cached local pass. New tests/negative native API/mutation paths, independent
ground analytic limits and measured cavern comparisons remain follow-up work.
The source-only specialised owner was preferred to a new Fourier extension;
SafeInCave/FEniCSx geomechanics and HydDown are comparison sources, not installed
fallbacks. No wrapper silently switches them in.

Primary sources inspected: official Sandia UH2SC repository and project
presentation SAND2024-03166C; Sandia subsurface hydrogen programme; Environment
Agency SC240045/S geomechanics report. These support ownership and application
boundaries, not a validated rock data set or site pressure envelope. No salt creep,
fracture probability, aquifer microbiology, chemistry, permeability or saline
water law was inferred. Final source hashes and static preparation results are
reported at handoff; scientific execution remains pending.

2026-10-28 source-only compatibility change: use existing SciPy integrate.trapezoid for the same quadrature while retaining NumPy1.26 minimum. No replay or numerical acceptance performed.
