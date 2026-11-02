# Native cyclic separation, multiphase conversion and photon boundaries

This request is for separate receiving sessions. It records capabilities that
the local Python interfaces still need; no receiving repository is modified
and proposed APIs below are not claimed to exist. Preserve one native owner
for each schedule/integrator, equilibrium solver and reaction inventory.

## 1. PSA native objects, accepted states and cyclic stream admissibility

The pinned PSA-Dyna runner executes actual warm multibed pressure/valve cycles
with native bed/thermal equations and component/energy ledgers. The host
`PsaDynaCycle` supplies Python case objects and reads hash-checked native slot
checkpoints. The runner's current integration entry point is file-oriented;
there is no public Network/state integration function. A separate native audit
Network verifies checkpoints through the existing `PsaDynaBed`. It is not the
original integrator Network or SciPy solution.

Provide a native object entry point with explicit callback and result objects:

```python
def run_network(network, initial_state, schedule, settings, *,
                start_time_s, clock_id, accepted_slot_callback=None): ...
```

Return the actual Network, effective native settings, immutable accepted
states, per-slot and per-cycle physical clocks, command/valve modes, numerical
diagnostics and original failure cause. Allow the existing file runner to
delegate to this same entry point. Keep configuration/source fingerprints and
the component/thermal ledger basis explicit. Do not create another bed/cycle
integrator in the host or require JSON/files as the user-facing protocol.

Acceptance must compare object and file entry points on the same authored
two-bed/four-slot cases. Match native slot states, cumulative inlet/product/tail
component moles, feed/product/tail enthalpy and ambient heat. Vacuum work has
its own machine/control-volume meaning; do not add it to bed energy unless
the corresponding boundary belongs there. Preserve native numerical settings
and failures rather than patching runner globals or normalizing missing states.

Distinguish startup totals, a complete final-cycle throughput ratio, state-CSS
convergence, conservation acceptance and a qualified cyclic product stream.
The product/feed H2 ratio during startup can draw on initial bed inventory.
Only an evidenced periodic inventory/energy balance can qualify it as a
recovery metric. Keep native CSS tolerances/streak, worst-state change and
cycle-limit termination visible. State CSS alone does not establish adsorbent
data, purity accuracy or release-filter qualification. A stream bridge must
retain species order, pressure, T, flow direction, interval/clock, phase and
energy-reference identity, with an explicit native validity decision.
The current H2-specific host fields must use native H2 reporting. A native
output/recovery gate evaluated for N2 cannot qualify a host H2 recovery value.
A future generic target API must bind species identity to every output-change,
ratio/domain and qualification gate and name its returned quantities accordingly.

The first level remains warm loading-LDF and a declared native gas/caloric
reference. Cryogenic properties, condensation, surface-excess conversion,
spin composition, actual valve capacity and material/cycle experiments require
their own evidence. Reproduce the existing warm bed and finite-cycle ledgers
before expanding domains or adding other native energy models.

## 2. Multiphase equilibrium ownership and finite heterogeneous processes

`CanteraMultiphaseEquilibrium` delegates directly to actual native Mixture
Gibbs minimization and HP iteration. Candidate phases are explicit, including
initially absent solids. SI mol is converted to native kmol once; total amount
is never replaced by a normalized composition. Independent owned phases
retain thermochemistry fit bounds, atomic weights, reference pressure and
solid constant-volume EOS. Gas copies reuse the existing audited native helper.

Generalize native phase serialization/copy evidence to compare physical SI
EOS parameters rather than equivalent density string spellings. Preserve
exact native thermo coefficients/fit bounds and runtime kinetics where those
exist. Keep source and owned fingerprints distinct, forbid mutable source
aliasing and expose the actual source/owned/Mixture objects in both success
and failure. A constant-volume solid is not an ideal gas and cannot be routed
through a gas-only clone to avoid its EOS checks.

Provide native diagnostics for HP iteration and candidate phases whose
elements are absent from the finite feed. The host retains actual failed
HP cases with zero initial carbon and a zero-carbon candidate; it does not
automatically delete the candidate or replace the selected solver. A native
repair needs a reproducible failing input and proof that constraints,
candidate identity and extensive amounts survive the fix. Do not assume every
temperature nonconvergence is an out-of-range final state.

Acceptance covers elemental mol, charge/atomic-weight identity, mass, TP heat,
HP enthalpy, P*dV work, entropy/Gibbs direction, populated-species chemical
potential stationarity and feasible absent-solid stability. Trace-species/
element thresholds and their omitted stationarity scope must remain explicit.
Check gas-only limit, appearance/disappearance of solid carbon, finite amount
scaling and independent mass-action cases. Preserve raw failed or completed
but host-rejected solutions with original causes; a convergence flag alone
does not qualify them.

Further gasification/redox models need source-qualified candidate phases and
formation-energy references, real feed composition and separate ash/moisture/
mineral treatment where relevant. Equilibrium does not give residence time,
char area, surface kinetics, heat-transfer hardware, catalyst activity or
industrial yield. Reuse the existing finite gas reactor only for admitted gas
kinetics; solid/phase transfer needs explicit conserved amounts and a native
surface/particle mechanism. A gas-only reaction law cannot silently consume
an externally untracked solid inventory.

## 3. Photocatalytic input and measurement contracts

The host `photochemistry` level resolves explicit incident lines or flat
wavelength bins, a nonscattering optical path and a prescribed electron-
equivalent yield. It reuses the existing stoichiometric/caloric inventory core.
It is not a recombination mechanism, a catalyst fit or a Gibbs/exergy proof.

Source experiments must provide actual wavelength spectrum/power, filter
bandwidth, incident-plane geometry, illuminated catalyst mass/basis, solution/
donor composition, T/P, collection interval/clock and gas calibration/reference.
Provide uncertainty/replicate definitions rather than borrowing another column
as sigma. A printed specific H2 rate does not determine the missing optical
input. AQY must identify incident or absorbed photon denominator, fraction
versus percent and product-molecule versus electron-equivalent convention.
Two productive electron equivalents correspond to one H2 molecule at this level.

Optical coefficients retain an exact wavelength-grid/representation identity;
matching array length is insufficient. Linear optical paths may be reused at
changed power on the same grid, while yield must be rebound with evidence to
the complete new optical input and conditions. Incident yield is not multiplied
by absorptance again. A per-band excess cannot be hidden by a surplus in a
different band. Rejected diagnostic values cannot drive finite conversion.

For variable illumination/material conditions, expose a source-qualified state/
response provider and use a shared finite-inventory/event driver. Preserve
photon, optical-energy and chemical-inventory boundaries across changes. Do
not extend a steady exposure by clipping exhausted reactants or inventing a
light shutoff. Coupled heat needs compatible phase/formation references; a
derived isothermal heat requirement is not an available utility or predicted T.
Gibbs/exergy, band alignment, carrier potentials and electrical bias require
their own physical closure before a solar-to-H2 efficiency claim.

The acquired TiO2 study has37 text members with one study group, duplicate
files and repeated controls. Read `PhotocatalysisArchive` source identities and
mapping evidence before comparison. Separate methanol photoreforming from
water/seawater cases and characterization fits from independent H2 targets.
The full methods/SI photon power, gas calibration and apparatus qualification
remain incomplete. Neither filename splits nor reconstructed AQY/rate columns
establish independent experiments or identify universal kinetic coefficients.
