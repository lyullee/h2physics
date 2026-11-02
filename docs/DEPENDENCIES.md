# Dependency decisions

## Initial choices

- Python 3.12 provides a common baseline with current process/risk packages.
- NumPy and SciPy provide arrays, optimization, integration and sparse numerical tools.
- CoolProp HEOS is the pure-fluid reference; AbstractState reuse precedes custom acceleration.
- CoolProp's released tabular providers and any custom phase-safe tables require comparison
  on hydrogen/para-hydrogen in the actual operating envelope.
- Cantera is optional for kinetics/equilibrium. Each selected reaction mechanism needs its
  own scientific applicability and rights review; installation alone qualifies neither.
- Existing domain engines are optional and imported lazily, with exact versions recorded.

Development documentation or a newer version number does not establish superiority.
Choose a supported release after license, fidelity, domain, performance and maintenance
comparison. Preserve a reference path and record adverse benchmark results.

## Known composition issues

The current PRISM full extra pins SLABx 1.0.7 / SLABx-LH2 0.1.5. Other current toolkits pin
SLABx 1.0.8 / SLABx-LH2 0.2.0. They cannot all own those imports in one interpreter as-is.
Request compatible provider interfaces and choose one tested dependency set per native
composition. Do not suppress resolver errors or rename imports to imply equivalence.

The station package caps SciPy below 1.16. A shared native environment must respect the
actual intersection, rather than assuming the latest standalone environment is compatible.

## Decisions checked on 2026 10 27

- CoolProp 8.0.0 native BICUBIC/TTSE tables pass the sampled property-error gate but
  fail the separate energy-identity gate over the broad warm-gas envelope with inverse
  inputs. An explicitly selected dependent-u closure passes both sampled gates; raw
  adjustments, negative results and mixed-workload timing remain recorded.
- Cantera 3.2.0 supplies equilibrium, stiff reactor integration and premixed flames.
  Multicomponent/Soret transport and grid/domain refinement are exercised. An installed
  example mechanism has a measurable fitted-thermochemistry jump at 1000 K; diagnostics
  retain it rather than changing coefficients or resetting an energy reference.
- Cantera's default C++ data directory loses non-ASCII characters in this Windows
  workspace. Reading the installed mechanism through Python and providing its unmodified
  text to a native phase factory works without copying a mechanism into the repository.
- FESTIM/FEniCSx is a higher-resolution material-transport candidate. Its official
  installation notes require WSL/Linux on Windows. No system-level installation was made;
  the portable planar model is a declared reduced level with independent numerical checks.

Exact installed versions are recorded under `requirements/`; this environment is not a
claim that incompatible upstream extras can share an interpreter unchanged.

The common equilibrium nozzle uses the existing SciPy bounded scalar optimizer and the
injected property provider; no extra solver dependency is required. The native LH2DT tank
continues to own time integration. Sandia HyRAM+ is now the selected optional high-pressure native provider, but its GPL-3.0 implementation is not part of this Apache-2.0 core or its default
imports. Public governing relations and our independent implementation are documented
separately in SOURCES_AND_METHODS.md. Performance and additional nonequilibrium physics
still require actual domain-specific comparisons.

The native equipment continuation uses the same pinned MIT LH2DT snapshot and existing
SciPy/CoolProp dependencies. Its structural property facade returns actual native states
after one HEOS flash. Sixty mixed state queries and viscosity/saturation checks agree;
the recorded property workload is about 22.7 times faster and the complete same-step
coupled case about 2.34 times faster. No cryogenic table is extrapolated. Unsupported native
methods and exact-type constructors remain explicit limitations. The reference path stays
available for comparison; no global dependency or external repository was modified.

Finite line/vaporizer storage and command partitioning reuse the same optional native
revision and property facade. The driver injects the native simulator factory; it does
not add another integrator or change dependency versions. Independent scalar wall-relaxation
and clock limits verify the composition. Accepted rows match the exact native solution
object rather than an assumed number of RK-stage calls. Direct native streaming remains
a receiving API improvement; snapshots are buffered for the current command interval.

The combined supply builder and explicit mode selection need no new dependency or external
repository change. The exact native main revision was checked again against the installed
snapshot. A separate complete finite-device workload compares the original property path
with the single-flash facade; its measured timing is in `research/native_finite_supply.md`.
Do not extrapolate earlier workload ratios or confuse faster state construction with new
physical fidelity. Longer reverse-transfer heating requires finer temporal resolution than
the benign short supply sequence, without relaxing the final-state gates.

The transition check subsequently found a native fixed-friction iteration inconsistency.
The common Darcy root now receives an explicitly chosen direct Churchill_1977 callback
from the separately installed MIT fluids 1.3.1 library (`hydraulics` extra). Its released
package/license and primary API documentation were checked; source is not bundled. The
generic root uses existing SciPy and has no mandatory fluids import. Native HEM viscosity
and inventory equations remain reused. The correlation change is documented separately
from root convergence and does not claim independently validated two-phase accuracy.

The `eis` extra pins the released MIT impedance 1.7.1 native circuit engine. PyPI release
metadata and the installed object are checked; the latest documentation's 1.8 label
is not treated as an available release. The package imports pandas through plotting
even though its dependency metadata does not declare pandas. Modern Altair no longer
pulls pandas into this environment, so the extra declares pandas>=2.2,<4 explicitly.
An actual import initially failed until that dependency was installed; it is not hidden.
The tested combination includes pandas 3.1.0, Altair 6.3.0 and Matplotlib 3.11.2. Core
imports do not need those packages. Prediction/introspection are checked, without claiming
all native plotting/fitting/serialization paths work in this combination. The 41-package
observed environment is `requirements/validation-windows-py312-pem-2026-10-27.txt`; the
earlier 20-package snapshot is retained as historical equipment evidence.

The `pool` extra selects MIT dynamiclh2poolx 0.2.0rc2 and CoolProp>=8,<9. This is an
explicitly selected pre-release. The released PyPI module bytes match exact GitHub
revision `6a700e8e183039bbb81803bacc416f6c9117ed71`, not just its version string.
No source data or native solver is bundled. A new 42-package observed environment is
`requirements/validation-windows-py312-pool-2026-10-27.txt`; earlier snapshots remain
historical evidence. The native normal-Hydrogen property restriction is enforced.
Property endpoint queries are startup work rather than a hot-loop table workload.
The recorded event-clock bridge delegates the actual native input only under an
explicit budget. Native pool equations and global CoolProp state are unchanged;
request 010 describes the receiving fix and missing property/source capabilities.

The gas/jet continuation selects separately installed MIT DEGALI revision
`6ead182dc19039725a0b40811b48c6d39f947790`, declaring version 0.3.0, through
`requirements/native-degali-pinned.txt`. The current PyPI 0.1.0 release is not used as
an equivalent package. A direct URL is kept in the optional installation recipe rather
than published core dependency metadata. The native base requirements include PyAMG
>=5.3,<6; the actual broad native import needs it even for the integral jet. PyAMG 5.3.0
is installed in the 43-package observed environment, while the native source snapshot
is isolated and recorded separately. CoolProp remains 8.0.0 and HEOS remains the nozzle/
gas-plane reference. No new host property table or second jet solver is introduced.

Native phase/enthalpy tables are part of the selected mixture approximation. Their
presence does not make it a complete real H2/air EOS or a qualified table envelope.
Narrow optional imports, profile-consistent forces and public conserved-flux contracts
are requested in 011. The cold-case conservation failure is retained rather than
described as a library upgrade success. The snapshot and all native sources/data stay
outside h2physics distributions. `validation-windows-py312-jets-2026-10-27.txt` records
the current main environment; it does not resolve unrelated PRISM/SLAB/station conflicts.

The measured-jet continuation adds no runtime dependency. It reuses openpyxl for the
source-specific spatial workbook profile and SciPy's bracketed scalar root around the
existing nozzle, plus the same exact native DEGALI snapshot. Main remained at 43 recorded
dependencies; supporting source-description review used bundled read-only document tools,
not a new library requirement. Optional original diagnostic plots use the already
recorded Matplotlib and require it only with --plot.

The new H2 flux-energy gauge is an explicit actual-native subclass using reviewed
protected flux/source capabilities. It changes a numerical reference consistently, not
global CoolProp state or physical coefficients, and returns audits to the original
reference/budget. C/2C full-path checks are recorded separately from field accuracy.
No native source, source illustration or external observation file is bundled. The
current native main revision was rechecked and still matches the selected snapshot.

The carrier continuation adds optional `molecules = [rdkit==2026.9.1]`. Official native
API/core license and PyPI Windows CPython 3.12 wheel metadata were checked. Core RDKit is
BSD-3-Clause; the installed wheel build wrapper's LICENSE.md is MIT, with its exact hash
and published wheel checksum in research/rdkit_dependency.toml. This is a separately
installed library, not redistributed source. NumPy/Pillow already existed in the local
environment. Neither Open Babel nor an independently written SMILES parser is added.
The new caloric adapter reuses installed Cantera 3.2.0 and the existing SciPy bracketed
root; no new reaction integrator or property fit is added. The 44-dependency observed
Windows environment is requirements/validation-windows-py312-carriers-2026-10-27.txt.

The user-selected default priorities are now HyRAM+ 6.1 for high-pressure gaseous H2 and
SLABx-LH2 0.2.0 / SLABx 1.0.8 for LH2-origin dispersion, with exact source revisions in
requirements/native-preferred-dispersion.txt. HyRAM is separately installed GPL-3.0-only;
SLAB-family sources are separately installed MIT dependencies. They are not vendored.
SciPy 1.18.1 exposed a native dopri5 callback signature failure; a distinct target with
SciPy 1.16.3 executes the case. The 212-test checkpoint passes under both default 1.18.1
and the 1.16.3 native runtime. This compatible selection does not resolve PRISM's older
exact pins or certify the failed native Gaussian source mass gate. No callback patch or
silent global replacement is used. PREFERRED_DISPERSION.md and request012 state limits.

The spin/two-side thermal/reactive/data continuation adds no runtime dependency.
It reuses the reviewed MIT LH2DT snapshot, CoolProp8, Cantera3.2, SciPy and
openpyxl already installed. Native spin functions and native fluid/wall derivatives
remain their owners; gas reactions share the existing native volume/integrator.
Separately installed gri30.yaml bytes are fingerprinted, never bundled. The
native thermochemistry reconstruction audit preserves thermo bounds and runtime
multipliers that the observed generic clone path did not fully retain. Exact owned
definition checks and a plain-native trajectory comparison remain independent
of that coefficient-copy gate. The existing observed environment record and
compatible SciPy target remain applicable; no package upgrade is implied.

The fire/heat continuation adds the optional `inverse_heat=[pifira==0.3.0]` extra.
Actual PyPI metadata/wheel and MIT license were checked, with exact hashes in
research/pifira_dependency.toml. A separate ignored native_fire_packages target
reuses the existing NumPy/SciPy/pandas/CoolProp dependencies; the main environment
was not upgraded. Native pressure/area routines remain their owners. HyRAM+6.1
already exists separately under GPL-3.0-only. New flame and public static blast
calls do not resolve its source/caloric failures or license redistribution of
native code. `requirements/native-fire-heat.txt` pins the new optional owner.

## Cryogenic, rotor and spherical-material continuation

No new numerical solver or dependency is introduced. Cryogenic composition
uses the pinned separately installed MIT LH2DT0.1.2 and current HEOS backend.
Temperature-dependent rotor functions reuse the separately installed MIT
pifira0.3.0 already reviewed for inverse heat; the same optional target/extra
can serve both. Rotor-only use is not an evolving-spin gas/liquid EOS.

Spherical transport shares SciPy BDF with the legacy planar API. Its finite
cavity reuses the existing HydrideGasThermodynamics callbacks and actual
CoolProp objects. The thermo extra is needed only for those native calculations;
core imports remain possible without optional domain/data packages. The biological
workbook profile uses the existing data extra. No native implementation or
external raw/normalized dataset is added to the distribution.

## Photon, multiphase and PSA-cycle continuation

No package upgrade or new dependency is introduced. Original photon accounting
uses NumPy and existing SciPy SI constants; finite chemistry/calorimetry reuse
the existing reaction core and optional native Cantera3.2. Its separately
installed gri30.yaml/graphite.yaml remain native thermochemical sources, with
source/owned fingerprints, rights and fit/domain identities in the multiphase
report. No mechanism or coefficient table is bundled.

The actual MIT PSA-Dyna pinned source is reused for schedules, valves, warm
beds, BDF and CSS. The host temporarily adapts Python mappings to its native
file entry point; no native implementation or automatic source archive is
copied into the host/distribution. Original integration-object and callback
access remains a receiving capability. The photocatalysis archive profile
uses Python's bounded ZIP/text handling and existing NumPy observations.

## Membrane, common-reference calorimetry and biological owner

Porous transport and gas/pure-solid calorimetry reuse separately installed
Cantera3.2 through the existing chemistry extra. No package upgrade, coefficient
bundle or second transport/EOS solver is required. The NASA/GRI source provenance
and native BSD-3-Clause license remain separate from source material validation.
The staged finite thermochemical core uses existing NumPy/reaction contracts;
its optional native checks use the same chemistry provider.

The biological owner is optional QSDsan1.5.3 with Thermosteam0.54.2 and a
source-hash-admitted official BioSTEAM revision, installed separately from the
main numerical environment. See NATIVE_BIOLOGICAL_PROCESS.md and
research/biological_dependency.toml for the immutable source, resolved artifact
hashes and NCSA license evidence. Published version strings alone do not admit
the rejected solver-initial-state alias implementation. The broad dependency
stack is deliberately absent from core installation. No native implementation
or kinetic matrix is redistributed.

## Finite device and uncertainty continuation

Finite membrane coupling reuses separately installed Cantera3.2 with public
ExtensibleIdealGasReactor hooks and the existing audited transport owner.
Hydride compression reuses existing reviewed LH2DT/CoolProp/NumPy/SciPy and
shared host kinetics/nozzle; no package upgrade, native code or new EOS is added.

The optional `uncertainty` extra requires SciPy>=1.15 for its Generator API while
core import requirements remain broader. Actual1.16.3/1.18.1 profiles are checked;
SciPy/NumPy retain statistical algorithms and their existing licenses. The real
native1-input/1-output shape failure is retained for upstream correction, without
modifying installed source or silently substituting a host estimator. The new
material profile uses existing data extras; no acquisition/distribution policy
or raw dataset was changed.

## Native safety endpoint and conditional-risk continuation

HyRAM6.1 exposure reuses the existing reviewed GPL-3.0-only installation. Its
actual probit/dose/CDF paths execute in both checked SciPy profiles without
changing native source. Existing gas/flame failure and resolver boundaries
remain separate; exposing a supplied-field response does not repair them.

Caltech's reviewed official SDToolbox archive has BSD-3-Clause terms and actual
April2026 native headers despite an older download-page label. Exact archive,
license/source and Cantera bridge evidence is in detonation_dependency.toml.
Only the separately installed native package is used; mechanisms/examples/
implementation remain outside distributions. See NATIVE_DETONATION.md for the
native file-only interface, copied-definition audits and reproduction.

The `risk` extra selects published Process Risk Consequence Toolkit0.1.0
(Apache-2.0). The current isolated profile resolves Pydantic2.14.1/core2.50.1,
annotated-types0.8.0, typing-extensions4.16.0 and typing-inspection0.4.4;
MIT/PSF installed notices and all artifact hashes are in risk_dependency.toml.
No dense/HTTP extra or core-environment upgrade is required. requirements/
native-risk.txt reproduces these direct pins. Python typed requests retain
native objects; native receipt normalization is an internal boundary.
The BLEVE profile uses existing data dependencies only.

## Cold-side state and learned monitoring

Native finite oxygen transport reuses Cantera3.2 and the existing phase-copy,
caloric, source/nozzle and finite-volume contracts. No oxygen ODE is duplicated.
The distinct ordinary-air thermal level uses actual pythermalcomfort4.7.0,
numba0.68.1 and llvmlite0.50.0; reviewed original wheel members match installed
bytes. MIT/BSD notices, bundled third-party notices and94-file thermal source
identity are in research/thermal_dependency.toml. Native JIT remains enabled;
the original disabled-JIT import failure is retained, not silently bypassed.

Process Monitoring Toolkit0.1.0 comes from its official immutable MIT GitHub
archive79b4cf52a0acd0d0cbd3addbe82c3d98d6385e5a. No PyPI release was available
at review. The isolated source-built wheel and scikit-learn1.9.1, cloudpickle3.1.2,
joblib1.6.0, threadpoolctl3.7.0 and narwhals2.28.0 have source/artifact/notice
receipts in research/monitoring_dependency.toml. requirements/native-monitoring.txt
reproduces that optional source profile; the host does not pretend an unpublished
PyPI artifact exists. Main NumPy/SciPy/pandas were not replaced.

No native implementation, physiological coefficient table, trained model or raw
experiment is bundled. Original native method/function and physical signal/model
state guards are distinct from dependency installation or scientific validation.
The original SLABx-LH2 standalone air diagnostic fails remaining-gas saturation/
composition consistency and is not an oxygen/thermal boundary. Its original
reproduction and Request022 remain separate from accepted preferred dispersion.

## Unexecuted PV and mechanical development owners

PV code targets actual optional pvlib0.16.1; original wheel/source/BSD notice
inspection is in pvlib_dependency.toml. No native PV computation was performed.
The fracture adapter targets the pinned official BSD-3 SandiaHELPR2.1.0 source,
with selected native method/source records in fracture_dependency.toml. Its
installation/runtime/transitive compatibility remains unexecuted. A GPLv3
py_fatigue candidate with a different NumPy/Numba and geometry/endpoint contract
was not selected; there is no fallback. No library/calibration coefficient table
or native source is copied into the host.

Nurion profile/environment installation is future work after connection. Existing
Windows snapshots are not Linux installation locks. Static API inspection and
source checksums do not establish native runtime acceptance.


## Coding-only dependency review — 2026-10-28 continuation

Pool fire reuses reviewed PRCT0.1.0 Apache-2.0. Vessel failure reuses pinned
HELPR2.1.0 BSD-3-Clause, with an additional source receipt in
research/vessel_failure_dependency.toml. Parcel flight reuses installed fluids
(MIT), CoolProp (MIT) and SciPy (BSD); no new correlation coefficients or
publication prose are copied. Economics reviews optional pyH2A0.0a8: MIT code,
CC-BY4.0 non-code resources, recorded separately in
research/economics_dependency.toml. ProFAST1.0.6 was rejected on use/redistribution
terms and is not a dependency. No native installation or scientific execution
was performed for these four coding lanes. Reviewed rights are not proof of
physical validity or a legal guarantee. No third-party tables are vendored.


## Cavern/MEC/impact/front coding dependencies

Optional UH2SC is pinned to d5057350df4d86c5c11a22e76beca24275518c8c,
BSD-3-Clause with HydDown MIT origin notices; reviewed source/license hashes are
in research/underground_storage_dependency.toml. Its native/transitive Linux
installation and complete dependency-rights lock remain pending. It is not
vendored. Impact reuses existing CoolProp/SciPy/DynamicLH2PoolX, with its own
review receipt. MEC uses actual Cantera Interface plus original synthetic fixture
and shared kernels. Front propagation reuses installed Cantera/SciPy and the
shared chemistry adapter; no chemistry mechanism or graph solver is copied.
No native dependency installation or scientific execution occurred in this wave.

The current MEC data receipt for DOI10.34810/data2866 records a public Dataverse
bulk acquisition and schema audit under the dataset-level CC0 grant. Its 23 data
files remain under ignored `data/raw/`; the exposed metadata contains no
file-level override fields, so public redistribution stays withheld. The schema
is insufficient for whole-cell MEC validation. See `docs/MICROBIAL_CELL.md` and
`research/microbial_electrolysis_data_candidate.toml`.


## Obstacle/fire/cost/evidence coding rights

The optional external FDS6.11.1 source notice is recorded in
research/obstacle_dispersion_dependency.toml at revision
ff928dbf68a2623ced3a007be75391c6dc6c9f90. Its NIST/US-government-work notice is
preserved without a universal MIT/GPL relabel. No binary/source/thermo table is
bundled; actual binary and MPI/OpenMP/runtime/transitive review remain pending.
Jet diagnostics reuse the separate reviewed HyRAM GPL-3.0-only and Cantera BSD
owners, including installed native NASA thermochemistry rather than copied
coefficients. Their source/license byte receipts are recorded separately.
MEC economics reuses the reviewed pyH2A owner; no financial tables/formulas are
vendored. The read-only collector uses standard-library code and existing
metadata types. No new dataset assets, native installation, simulation or
scientific qualification is claimed for this checkpoint.

Source compatibility review: NumPy trapezoid was introduced in2.0; core NumPy1.26 support uses existing SciPy integrate.trapezoid in obstacle/source and underground valve quadratures. No compatibility execution was performed. Primary API references: https://numpy.org/doc/stable/reference/generated/numpy.trapezoid.html and https://docs.scipy.org/doc/scipy-1.14.1/reference/generated/scipy.integrate.trapezoid.html .

The producer-result, carrier-conversion and facility-protection increments add no
runtime dependency. They reuse NumPy, the shared thermochemical contracts and
already reviewed optional Cantera/LH2DT/monitoring/risk owners. Compressor and
heat-exchanger provenance reads the existing pinned LH2DT Python source; it does
not install or execute the package during this coding checkpoint.

Finite adsorption, valve actuation, relief lift and facility continuity add no
runtime dependency. They reuse existing adsorption/property, LH2DT/nozzle and
shared equipment contracts. No optional package was imported or executed.

Rotating-equipment maps, flowing-HX admission and product collection add no
dependency. They use existing LH2DT/property/equipment contracts and standard
library bookkeeping. No optional provider was imported or executed.


## Primary acoustic-source audit environment

`research_pdf` is an opt-in research extraction extra, pinned to the executed
pdfplumber 0.11.10 version. Its installed license file and upstream license
were checked as MIT (https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt).
No third-party extraction code or source documents are vendored. The raw
primary manuscript has a separately recorded CC BY 4.0 grant and checksum;
its bytes and extracted numeric rows stay in the ignored data cache.

Reproduce the primary-table comparison from the repository root:

```powershell
python -m pip install -e ".[thermo,data,research_pdf]"
python scripts/audit_nguyen_acoustic_source.py --pdf data/raw/hydrogen-acoustic-primary/2024/nguyen-2024.pdf --output docs/NGUYEN_ACOUSTIC_SOURCE_AUDIT.md
```

The document download URL and required checksum are in
`research/hydrogen_acoustic_independence.toml`. The script rejects changed
source bytes, unexpected row counts and any mismatched compiled observation.
Its report contains aggregate residual/uncertainty diagnostics and source/EOS
fingerprints, not the source table. The experiment provides no model-error
budget or independent-error assumption for a statistical coverage claim.

## Thermal network extra and independent native profiles

Install `h2physics[cycles]` from the current source for tested TESPy 0.11.3 and
ExerPy 0.2.0 with CoolProp 8.0.0. Current ExerPy owns physical exergy; the removed
TESPy exergy class is not used. The chemistry extra supplies Cantera 3.2.x for
redox/PAR/mixture thermochemistry. See [the receipt](../research/extensions_dependencies_20261102.toml)
and [the extension manuals](ENHANCEMENTS_20261102.md). Optional HyRAM+ remains
separately installed/licensed. A directory containing another SciPy must be
selected at Python startup or used in a dedicated environment, not inserted
into an already imported scientific runtime.
