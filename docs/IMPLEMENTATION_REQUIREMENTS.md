# Requirement-level completion evidence

The original programme remains active. This matrix preserves its scope and names
the evidence needed for completion. A module's existence is insufficient evidence
for every physical level within its family. Hangang is the active target for
scientific contract execution; local scientific execution is also authorized
when the shared connection is slow or unavailable. Record the actual execution
host and scope; static checks cannot close numerical gates.

| Requirement | Authoritative implementation/evidence | Current missing completion evidence |
|---|---|---|
| Flexible parameter and data customization | Python dataclasses, Protocols and caller callbacks in src/h2physics; API.md | Complete per-family tutorials and executed alternate-input paths for all supported model levels |
| Public process and experiment data | research/data manifests; DATA_INVENTORY.md and DATA_QUALIFICATION.md | Qualified source-specific inputs for every supported physical claim and independently held-out comparisons |
| Original releasable code and rights | RIGHTS_AND_PROVENANCE.md; dependency/source and dataset ledgers | Fresh distribution/license/attribution audit covering all new files; no blanket legal guarantee |
| Prefer improved methods and existing engines | DEPENDENCIES.md; SOURCES_AND_METHODS.md; catalog ownership | Current per-gap method comparison and qualified runtime compatibility for new levels |
| CoolProp and acceleration | Native pure/mixture/molar-enthalpy providers; qualified table records in THERMO_ACCELERATION_QUALIFICATION.md; native pipe/linepack integration in HYDRAULICS.md and related manuals | Complete declared mixture/phase domains and independent property/model qualification; local hydrogen table error/speed checks and pipe numerical tests do not qualify every fluid, phase or hardware target |
| Existing repository integration | adapters and requests; MODEL_CATALOG.md | Receiving native capabilities and executed end-to-end paths within their actual domains |
| Reproducible manuals and research history | README, API, USER_GUIDE_KO, DEVELOPMENT_LOG, HANDOFF, deferred plan | Fresh complete tutorial/release audit; source-pinned numerical and independent validation records |
| Deep Python API | scenarios.py, native adapters and direct object receipts | Cross-module execution of all advertised combinations, without changing clocks/reference meanings |
| Plan and persistent objective | PLAN.md, PROGRESS.md and active thread goal | Full original objective remains incomplete; estimated effort and authored case counts are not completion proof |
| Receiving extension requests | requests and explicit thermal-stress receiving contract | Implemented receiving APIs where current native engines lack physical/state/event support |
| Consolidate equivalent physics | Shared nozzle, thermochemistry, native integration and property owners | Continue reviewing new levels against existing owners; retain distinct fidelity only with explicit physical/numerical difference |

The TU Darmstadt hydrogen-engine flame/wall dataset now has a metadata provider,
hash-verified local attachment acquisition and a schema-neutral HDF5 structure
inventory. Mapping dataset arrays into source-bound observation blocks still needs
schema review; this source does not provide the pressure/work measurements needed to
qualify the present cylinder model.

Concrete remaining coding and external native gaps are maintained in
IMPLEMENTATION_BACKLOG.md. The current 82-family catalog tracks first-level
implementation status (20 implemented, 37 native-adapter-verified, and 25
implemented-unverified); it does not measure completion of every physical level.
CLUSTER_EVIDENCE.md and pinned receipts track actual execution separately.
Neither establishes complete facility or scientific qualification. New compositions
must retain physical boundaries, source/evidence identity, original failures and
explicit unsupported cases. Completion requires examining each original requirement
and every claimed supported level against current files and executed evidence.

## Current physical implementation boundaries

The newest source expands the implemented physical levels, with execution still
deferred. This updates the scope matrix without treating an authored model as validated.

| Original requirement | Implemented current source | Remaining host/native/evidence work |
|---|---|---|
| CoolProp/deep property coupling | `state_rho_u_bounded` and mixture inventory adapters solve a caller-bounded frozen-composition inverse. Native PQ phase compositions and PH branch inversion feed `mixture_flash_separator.py`. | Broader phase-domain inverses, changing compositions and finite multiphase separator vessel holdup need explicit state/branch support. Hangang must check phase, energy and component closure plus domain failures; independent data validation remains separate. |
| Equipment physics reuse | `lh2dt_transient_flowing_exchanger.py` calls native DynamicVaporizer flow derivatives and native network integration for simultaneous finite fluid/wall storage. Native segmented restarts preserve known jump interval limits and carry exact state plus transport/heat ledgers. | Distributed spatial flow, pressure drop, unknown event roots and full equipment qualification remain distinct. Native scheduling plumbing is not a hydraulic solution for externally prescribed side streams. |
| Finite production/thermal coupling | `electrochemical_thermal.py` advances finite stack temperature and finite isobaric coolant enthalpy in one existing RHS; utility readout preserves internal versus external heat. | Finite reactant/current/pressure feedback, phase-changing or flowing coolant and degradation still need applicable state equations/events. Source-qualified thermal and polarization inputs remain evidence work. |
| Separated fuel-cell states | `fuel_cell_compartments.py` uses actual independent native gas volumes for H2, O2 and gaseous water, driven by shared Faraday current under prescribed stack T. Native pressure and compartment heat/U ledgers are retained. | This does not close combined reaction energy or feed compartment pressure into stack voltage. Request031 defines the native simultaneous pressure/activity/thermal contract. Liquid water, membrane crossover and device validation remain outside this gas-only level. |
| Existing adsorption owners | Native rate observation, cycle endpoint audit and finite-window product means reuse `PsaDynaBed` and `PsaDynaCycle` unchanged. | No additional host adsorption ODE is justified. Native accepted internal state/event support, cryogenic material physics and independently qualified absolute uptake/heat parameters remain open. |

Pure-fluid finite separator inventory/withdrawal now uses the original native
stratified-tank owner; changing-composition mixture inventory remains Request032.
Original-scope review additionally identified catalytic surface kinetics, now
implemented through `cantera_surface_reactor.py` at a closed rigid isothermal level
with native gas/adsorbate element/site audits. Its thermostat demand is a diagnostic;
flowing reformer and catalyst thermal qualification remain open. Typed deposited-
pool/fire and jet-radiation/target handoffs preserve original source identity.
New table qualification and catalytic native cases are assigned to Hangang.
These additions do not prove full original-scope completion.
