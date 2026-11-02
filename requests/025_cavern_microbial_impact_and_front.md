# Cavern, microbial cell, finite impact and front integration

These are receiving-project requests, not changes or messages to other projects.
The local code is implemented_unverified. The preceding coding checkpoint is bd2dcaa;
this continuation adds four further coding-only first levels.
All scientific execution remains deferred until the later Nurion connection.

## UH2SC native source and cavern observations

Local API: `Uh2scUndergroundStorage`, with `UndergroundEvidence`,
`UndergroundDomain` and `UndergroundAuditBudgets`. The actual native owner is
Sandia UH2SC revision d5057350df4d86c5c11a22e76beca24275518c8c. Keep the
original native Model/solver/components/solutions/independent variables and logs.

Investigate the pinned GHE residual's idx-1 capacity/flux indexing in a loop
beginning at zero, and the count of positive ground capacities versus transient
temperature residuals. Reconcile the cavern enthalpy/expansion convention with
an independent internal-energy balance. The host deliberately does not repair
these native source concerns. Supply raw boundary heat, finite rock storage,
fluid species masses and signed well enthalpy at every native step, including
initial/final support. A self-residual of the native equations cannot replace
an independent inventory audit. Resolve native pyproject/internal version labels
and the parameter-to-actual-outer-radius convention explicitly.

Independent validation needs warm H2 cavern pressure/temperature, injection and
withdrawal mass/enthalpy, ground construction and temperature histories, water
inventory and compatible clocks. Porous storage, saline/cushion mixtures,
geochemistry, microbial loss, creep and mechanical failure are separate missing
physics. The current ideal adiabatic well has no finite well inventory.

## Microbial-electrolysis activity and finite process ports

Local APIs: `CanteraMicrobialCathode` and `FiniteMicrobialCell`. Reuse actual
Cantera Interface current/species rates, shared reaction conversion and the
finite thermochemical kernel. Expose qualified organism/substrate/growth,
aqueous formation enthalpy, pH/activity, electrode kinetics/reference and anode
potential with domain and source evidence. Do not insert ordinary water-splitting
DeltaG/DeltaH or an ADM1 kgCOD rate as if it were a complete MEC closure.

Current code is a fixed-pressure isothermal batch with held stage rates and
explicit required heat/electrical work. Future ports need debit/credit of feed,
water/ions, gas harvest, receiver state, electron recovery and external thermal
utilities. Capacitive and gas-transfer histories, side reactions/methanogenesis,
H2 consumption and coupled activity evolution must have physical owners.
Annual sale/recovery or energy closure must not be inferred from generated H2.

A newly located measured-data candidate is DOI10.34810/data2866. DataCite
declares CC0, but publisher file metadata/rights exceptions are not audited and
no data assets were acquired. Its publisher API returned an HTML anti-bot
challenge; no bypass was attempted. See
research/microbial_electrolysis_data_candidate.toml for metadata SHA and next
acquisition steps. The existing collection/file totals are unchanged.

### Data acquisition update — 2026-10-29

The public Dataverse OAI and ordinary bulk-download endpoints are accessible; the
10.9 MB dataset archive is acquired to ignored `data/raw/`. The record grants CC0
at dataset level. The 23 data files match the publisher size manifest and recorded
SHA-256 values; ten publisher preview MD5 values also match. Public ODS schemas
contain electrode LSV, EIS pairs without frequency, and current-density retention,
not hydrogen output, Faradaic efficiency or microbial activity. The assets are
therefore limited electrode evidence, not MEC model calibration/validation. No
file-specific rights-override fields are exposed, so public redistribution remains
withheld pending clarification. No model execution or Nurion job was performed.

## Finite incident-to-pool surface continuation

Local owner: `FiniteSurfaceImpact`, using the actual incident `ParcelTrace`.
Qualified contact/deposition/restitution data remain required. Preserve finite
surface heat, native latent enthalpy, interfacial energy, ambient pressure work,
rebound/vapor motion, recoil/arrest energy and fixed-mount impulse. No uniform
rainout ratio or infinite thermal substrate is a substitute.

The current host path admits one original unit-count incident trajectory through
`impact_population_member()` and retains the issuing population, exact trace,
impact owner and native result in `PopulationMemberImpact`. It intentionally
rejects using a weighted representative group as repeated wall contacts. This is
an identity and mass-boundary adapter; it does not provide a spray-impact
population law or determine which members hit a surface. To extend it, a caller
must first provide source-qualified per-member launch/contact trajectories and a
finite contact schedule. An accepted wall update must consume each contact once,
in clock order, and retain the original incident trace and deposited/rebound/
vaporized split at every accepted event.

The deposited batch is an initial stock at a known event, not an invented finite
inflow interval. Native fixed-area pool initialization is available under a
separately declared continuation heat owner. A truly coupled continuation needs
a public native finite-surface state/heat port retaining the same wall energy,
clock, geometry and liquid mass. Dynamic spreading currently does not admit this
nonzero initial stock. Its local acceptance contract must pass the exact
post-contact wall temperature/internal-energy state, wall material/capacity
identity, contact-end absolute time and the residual liquid mass/enthalpy basis
into the selected pool owner. Impact heat must not be applied again at pool start;
the finite wall balance must account for the pool's outgoing heat and transferred
heat exactly once. The separate native pool energy requirements are recorded in
[Request 033](033_pool_energy_ledger.md). Reject changed cached incident/deposited
summaries before handing them to a native pool.

## Premixed front and chemistry factories

Local APIs: `premixed_reference`, `FrontCell`, `MaterialContact` and
`run_material_front`. A public qualified phase/snapshot factory should replace
direct reuse of the shared CanteraGas._phase hook without duplicating its domain
and mechanism checks. Preserve original FreeFlame/HP objects and mutation guards.

The current six-neighbour material-coordinate network has directional path bias;
it is not an obstacle CFD solver, laboratory flame or person-exposure forecast.
Future lab-frame coupling needs a resolved flow/expansion or qualified front law,
an instantaneous composition/enthalpy bridge from an accepted preferred
dispersion source, ignition support and surface heat transfer. Warm mechanism
enthalpy cannot silently replace cryogenic spin-specific enthalpy. Retain native
relative path times and reject absolute clocks unable to resolve positive travel
or contact residence within the stated projection budget. Pressure-wave or harm
models require their own qualified physical inputs.

## Deferred campaign and status

New cases:4cavern,5microbial cell,8impact and4front. Together with the previous41,
the pending campaign has62 case definitions. Profiles and Python/setup paths are
explicit in validation/nurion_plan_example.py. No local solver/test, connection,
remote job, qsub, external repository edit or publication was performed. Strict
physical rejection remains rejection; a cluster job exit alone is not validity.
