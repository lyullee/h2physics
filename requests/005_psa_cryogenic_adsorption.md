# Request 005 — native cryogenic adsorption and bed-provider extension

## Target and reason

Target: `lyullee/psa-dyna`, reviewed public revision
`a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6` (MIT).
The existing competitive equilibrium and nonisothermal bed remain the equation owner.
The local adapters already call actual native functions/Bed objects and preserve species,
uptake definition, material/domain evidence, Pa derivatives and energy-reference identity.

Native `Bed.fields` currently rejects temperatures ≤100 K or ≥1000 K. The acquired
cryo-adsorbent experiments include 20/77/87 K conditions. Changing that numerical guard
alone would not supply valid cryogenic gas/solid properties or phase/energy accounting.

## Concrete local contracts to receive

- `h2physics.adsorption.AdsorptionProvider`: `basis` and
  `equilibrium(partial_pressures_pa, temperature_k) -> AdsorptionState`.
- `AdsorptionBasis`: species order, material/parameter/engine identity, reference evidence,
  amount basis and explicit `loading_definition` (absolute / surface_excess / source_defined).
- `AdsorptionState`: species-by-site mol/kg values, site-by-species-by-species pressure
  derivatives in per Pa, optional temperature derivatives, and immutable inputs.
- `h2physics.core.PropertyProvider` / `PropertyBasis`: pure-H2 properties with explicit
  spin composition and energy reference. No comparison of unaligned CoolProp and native
  constant-Cp enthalpy zeros is permitted.
- `adapters.psa.PsaDynaBed` / `BedFaceTransfers`: actual native Bed, species component
  molar face transfers, enthalpy W in one explicit reference, SI snapshots and native RHS.
  Face orientation is positive left-to-right at both ends. The current bridge deliberately
  supports only absolute-loading LDF, not a reinterpretation of pellet pressure states.

These are structural Python contracts. The target need not depend on h2physics or add a
JSON/HTTP interface. A caller must be able to inject equivalent native providers directly.

## Requested extension

1. Publish native species order, material-state interpretation, property/energy reference,
   cell/face axes and supported constitutive domain as stable inspectable attributes.
2. Support explicit gas property and solid/adsorbate heat-capacity providers over a declared
   cryogenic domain. Implement the actual total-energy derivatives/stream enthalpies for
   that provider, rather than continuing constant room-temperature Cp silently.
3. Keep spin identity, pure-fluid versus mixture responsibility, real-gas fugacity/pressure
   interpretation and equilibrium derivative semantics explicit. Initially pure H2 is an
   acceptable declared scope; a pure-fluid provider does not authorize arbitrary mixtures.
4. Reject free-gas phase condensation unless a separately verified condensed inventory and
   latent-energy balance is implemented. Adsorbed hydrogen is not the same inventory as
   bulk condensed liquid. Do not treat every state near/above a nominal relative pressure
   of one as a single gas phase.
5. Require measured/declared surface-excess→absolute conversion information, including the
   applicable pore/adsorbed volume and reference density, before using excess loadings in
   an absolute gas/solid inventory ledger. Never manufacture that volume from a desired fit.
6. Replace the fixed temperature guard with constitutive-domain checks only after those
   properties/closures are implemented. Keep all existing warm-case results reproducible.

## Acceptance evidence

- Existing warm equilibrium/derivative and closed-bed regressions pass unchanged.
- The local synthetic bridge checks (`scripts/check_psa_integration.py`, `check_psa_bed.py`)
  pass at the exact receiving revision, including species and energy-reference rejection.
- Pure-H2 declared cryogenic states agree with the selected reference provider; unsupported
  phases/mixtures fail explicitly. PT/PH/PS and stored/stream energy use one common basis.
- Closed finite-inventory adsorption/desorption conserves every component and total energy,
  including wall/adsorbate/gas contributions. Mesh/time refinement is reported separately.
- An independently qualified isotherm and thermal experiment are compared with fixed
  observation operators and held-out runs; source ambiguity is not resolved by fitting.

## Current evidence and unresolved data

`research/native_psa.md` checks equilibrium/gradient conversion; `native_psa_bed.md` checks
one warm closed uniform bed. These are not PSA process or cryogenic validation.
`research/static_ingestion.md` preserves the open cryogenic data, including conflicting
pressure headers, unspecified STP and unspecified excess/absolute basis. Those inputs need
qualification before they can validate this extension. No receiving repository was edited.
