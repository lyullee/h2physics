# Native gas and pure-solid equilibrium conversion

`CanteraMultiphaseEquilibrium` uses actual Cantera3.2 `Mixture` equilibrium.
The checked level has one populated ideal-gas phase and neutral, pure,
fixed-stoichiometry constant-volume solid candidates. The same core can host
appropriately evidenced carbon or solid-redox phase definitions; it contains no
gasification-specific reaction solver, kinetic ODE, new gas EOS or second gas
equilibrium implementation.

The first reference calculations use separately installed `gri30.yaml` and
`graphite.yaml`. Original finite feed cases demonstrate carbon appearance,
carbon disappearance, and adiabatic carbon/steam conversion. This is chemical
equilibrium and its caloric budget, not a measured biomass gasifier, porous-char
reactor, coke kinetic model or qualified catalyst/solid-redox cycle.

## Python objects and SI amounts

```python
import hashlib
from pathlib import Path
import cantera as ct
from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_multiphase import (
    CanteraMultiphaseEquilibrium, EquilibriumPhase, MultiphaseFeed,
)
from h2physics.core import Origin

data = Path(ct.__file__).parent / "data"
def phase(file, native_name, phase_id, role):
    raw = (data / file).read_bytes()
    basis = MechanismBasis(
        "installed-" + native_name, hashlib.sha256(raw).hexdigest(),
        "Cantera-BSD-3-Clause; upstream thermochemistry provenance retained",
        ("https://cantera.org/3.2/python/thermo.html#cantera.Mixture",),
        300., 2800., 1e4, 1e6,
    )
    return EquilibriumPhase(
        phase_id, role,
        lambda: ct.Solution(yaml=raw.decode("utf-8"), name=native_name),
        basis, "declared-native-NASA-formation-and-third-law",
        "native-mechanism-H2-spin-unresolved",
    )

engine = CanteraMultiphaseEquilibrium((
    phase("gri30.yaml", "gri30", "gas", "gas"),
    phase("graphite.yaml", "graphite", "carbon", "solid"),
))
feed = MultiphaseFeed(
    1100., 101325.,
    {"gas": {"H2O": .7, "CO2": .15, "H2": .05, "AR": .1},
     "carbon": {"C(gr)": .18}},
    "authored-finite-steam-carbon-feed", Origin.SYNTHETIC,
)
result = engine.equilibrate(feed, constraint="HP")
native_mixture = result.native_mixture
native_gas, native_carbon = result.owned_phases
hydrogen_mol = result.amount_mol("gas", "H2")
```

`species_mol` contains **absolute SI mol**, not fractions or kmol. Every candidate
phase must be explicitly included; an empty mapping or zero species amounts
declare an initially absent candidate. Missing species within that candidate
are zero; phases not declared cannot appear. Amounts must be finite,
nonnegative and have a positive total, with positive initial gas inventory.
The adapter never clips negative amounts or normalizes the user's total feed.
Native kmol amounts are explicitly divided/multiplied by1000 at the boundary.
Native mean molecular weights are kg/kmol and native molar energies J/kmol;
extensive energies are therefore J after multiplication by native kmol.
Equilibrium result receipts are issued only by the native owner. Direct construction,
dataclass replacement and changes to retained result or native phase state are
rejected by `require_current()` before amount projections are returned.

No physical time or residence-time clock is implied by an equilibrium solve.
Feed provenance/data role is retained. Computational runtime and solver
iterations are not conversion duration. The finite heat result is J; power,
cycle duty, throughput and plant efficiency require additional boundary evidence.

## Definition and energy-reference ownership

Each phase retains its `MechanismBasis`, explicit phase role, common formation-
energy reference and hydrogen-partition identity. All phase reference identities
must agree. A matching caller string is evidence metadata, not proof of source
rights or thermochemical compatibility. The checked GRI/NASA graphite assemblage
uses the native formation/third-law convention; no arbitrary CoolProp sensible
zero or normal/para hydrogen enthalpy conversion is inferred.

Factories supply native `Solution` definitions. The adapter creates independently
owned phase objects and returns both source and owned objects. Ideal gas uses
the existing audited native species/reaction reconstruction. Pure solids use
native YAML reconstruction with17-digit output and exact native thermo-class,
coefficient, reference-pressure and fit-bound restoration. Solid constant-volume
density, elemental composition, atomic/molecular weights and charge are checked.
Cantera interprets the original density-unit string and canonical SI density;
the host does not implement another solid EOS. A solid role is an evidenced
source classification, not something inferred merely from the thermo class.

Source and owned definition fingerprints can differ: gas reconstruction has
audited tiny unit roundtrips/notes, and solid EOS serialization changes native
unit representations. Neither difference is hidden by a shared hash. The actual
owned hash is checked exactly after equilibrium. Source definitions are pinned
per engine; changing them requires rebinding their evidence. Returned native
objects remain editable for Python coupling, and editing them invalidates the
recorded result. Cantera Mixture shares its heavyweight owned phases; separate
mixtures should not be constructed from them concurrently during a solve.

## Material, heat, work and equilibrium audits

Both TP and HP use one selected native solver call. `MultiphaseSettings` exposes
native VCS or Gibbs, tolerance, step/temperature-iteration limits and the native
initial-estimate flag. Automatic algorithm fallback is not selected. Cantera
owns composition minimization and the HP temperature iteration.

Snapshots retain absolute species/phase mol, elemental mol, kg, total H/U/G in J,
S in J/K, volume m3 and chemical potentials J/mol. Element counts use the native
atom matrix; atomic weights must agree between phases. Mass and element amounts
are checked independently, and the returned arrays are immutable snapshots.

For TP, temperature and pressure are prescribed and positive heat into the
assemblage is `H_final-H_initial`. For HP, pressure and total H are prescribed
and heat is zero. In both cases pressure-volume work out is `P*(V_final-V_initial)`
and the first-law residual is `delta_U+P*delta_V-Q_into`. Native formation energy
already belongs to H/U; adding a separate nominal reaction heat would duplicate
that energy. TP Gibbs decrease or HP entropy increase is checked separately.

Chemical-potential auditing fits elemental potentials to feasible populated
species independently of the native solver's convergence claim. It checks
`mu-A.T*lambda` and the formation affinity of feasible absent pure solids.
The amount threshold defaults to max(1e-14mol,1e-10*initial totalmol), and the
dimensionless affinity budget is1e-5. Species containing initially unavailable
elements are excluded; feasible trace species below the threshold are counted
but not certified individually. This is a bounded stationarity/stability audit,
not a global mathematical certificate. Gas disappearance/absent-gas tangent-plane
stability is outside this level and is rejected by the populated-gas gate.

All supplied and returned states must satisfy each phase's declared T/P envelope
and the native thermo-fit intersection, including zero-amount solid candidates
needed for phase-stability decisions. The native HP solver does not expose its
internal temperature trials or complete iteration history through this API.
Those trials cannot be independently bounded or retained here; no silent claim
of per-iteration fit-domain admission is made.

## Native failures and receiving requirements

The default raises `MultiphaseEquilibriumError` when native convergence, final
domain/definition checks or independent material/energy/potential audits fail.
It retains the actual partial/completed `native_mixture`, source and owned
phases, copy audits, initial/final snapshots when available, whether the native
call returned, an audited result when constructed, and the original cause.
`require_accepted=False` permits inspection of a completed rejected result;
native solver exceptions still propagate through the retaining wrapper. No
partial state is relabeled as a converged final equilibrium.

An actual H2/O2/Ar HP input with zero total carbon and an explicit zero graphite
candidate fails native temperature convergence in this installed version. The
failure is retained; the adapter does not remove that candidate, run a different
solver or substitute a gas-only result. Its root cause remains unestablished.
The report also preserves a deliberately insufficient native step budget and a
successful native HP solve rejected by an intentionally narrow host envelope.

Further native needs include reliable zero-amount/zero-element candidate handling,
observable equilibrium status/residual/iteration bounds, temperature-trial-domain
control, wider phase-model validation, absent-gas stability and boundary dynamics.
Finite-rate solid surface reactions, particle size/transport, ash/mineral phases
and process hardware need their own native models and evidence. This equilibrium
core does not infer them from an equilibrium H2/CO yield.

## Reproduction and rights

Run `python scripts/check_cantera_multiphase.py`; see research/multiphase_conversion.md.
Original tests include independent Boudouard mass-action extent from pure native
chemical potentials, source/owned alias separation, mol scaling, solid appearance/
disappearance, no-solid TP gas limit, HP enthalpy/PV work, native/post-run failure
retention and reference/species/amount negatives. The gas-only TP limit compares
equal elements at equal TP; atomic-carbon and graphite feeds have different H,
so no equality of their input heat is claimed.

The replay fingerprints all executed host inputs, reused copy/reference modules,
installed gas/graphite files, the Cantera compiled extension and BSD license
before/after computation, and verifies new LF text files. Reading installed YAML
through Python avoids the native non-ASCII file-path issue without copying or
modifying its contents. No mechanism, coefficient table or experimental dataset
is bundled. Cantera implementation licensing and upstream thermochemical data
provenance remain separate responsibilities.

Primary sources are the [native Mixture API and stated solver limitations](https://cantera.org/3.2/python/thermo.html#cantera.Mixture),
[installed GRI30 provenance](https://cantera.org/3.2/examples/input/gri30.html),
[native graphite definition with NASA references](https://github.com/Cantera/cantera/blob/v3.2.0/data/graphite.yaml),
and [NASA TM-4513](https://ntrs.nasa.gov/citations/19940013151).
These numerical checks establish no measured biomass/catalyst validation or
industrial gasification/coke/redox qualification.
