# Native membrane, staged thermal and biological receiving capabilities

## Current native and host ownership

Cantera3.2 owns DustyGas multicomponent/Knudsen/Darcy transport and gas/pure-solid
thermodynamics. Host Python contracts now retain actual native objects, source
identity and finite reaction/heat ledgers. QSDsan/BioSTEAM own ADM1 dynamics,
liquid/headspace inventories, acid/base and gas transfer. This request specifies
extensions for another development session; no receiving repository was edited.

## Finite porous separator

Accept the existing `MembraneEndpoint`, `PorousTransportGeometry` and
`MembraneFlux` objects directly. Couple signed component mol/(m2 s) to finite
feed/permeate/retentate inventories using the corresponding bulk geometric area,
full species order and one absolute clock. The native coefficients already
include porosity/tortuosity: no second porosity factor is allowed. Stationary-
solid total flux includes Darcy flow and must not be interpreted as zero-sum
relative diffusion or normalized into a product composition.

Retain actual source/owned DustyGas, immutable geometry, transport-polynomial
copy fingerprints, phase/reference identities and endpoint evidence. A new
transport fit or pore definition must produce a new admitted identity. Require
finite depletion/reversal localization and explicit upstream/downstream boundary
conditions. A spatial membrane level should reuse native local fluxes in a
conservative discretization, with numerical refinement and no duplicate transport
matrix solver. Nonisothermal, adsorption, dense/polymer, charge and phase-change
levels need their own justified contracts, property evidence and heat/work terms.

Acceptance: equal-state zero, orientation reversal, X/Y equality, fixed-pore
low-pressure Knudsen limit, Darcy increment, species/global inventories, pressure
feedback, depletion event and mesh/time refinement. Use independently qualified
material geometry/transport experiments before claiming recovery or purity.

## Staged thermochemical extension

Reuse `MolarEnthalpyProvider`, `StoichiometricReaction`, `ThermochemicalStage`
and the trace's finite before/feed/withdraw/after inventories. Preserve a common
formation-energy/phase/spin reference and source fit bounds. Pure-solid density
requires explicit evidence; authored density fixtures are not measurements.
Changes to native phase/provider bindings invalidate the previous identity.

Next source-qualified cycle work needs equilibrium/phase stability and actual
kinetics, finite gas ports, pressure/vacuum/separation work and a utility capable
of delivering the required thermal duty. Introduce those physical owners rather
than converting prescribed extent into a claimed rate. Couple heat recovery to
actual finite hot/cold/storage inventories and clocks; do not credit a chosen
fraction of gross heat. Return carrier composition, T and full inventory as
separate tests. Include mechanical/exergy/solar boundaries before any efficiency
claim. Cached property arrays must not alias earlier evaluations; finite inputs
whose extensive arithmetic overflows must retain the stage/prefix and fail.

## Native biological boundaries

Use actual ADM1/components/AnaerobicCSTR/System/OdeResult objects. Record immutable
source hashes as well as versions: BioSTEAM2.54.0's published initial-state alias
and official fixed source share a version string. The admitted official revision
is0acb320455d3c6cdaace85bf6ca27a1256706918. No copied host ODE or monkeypatch is
acceptable. Preserve explicit finite liquid/headspace initialization, source
clocks, native day-to-second conversion and component measurement bases.

Request a native zero-liquid-flow output-finalization path or accepted-state
observer before `WasteStream` conversion. Actual native integration can succeed
while output conversion rejects an empty stream. Preserve the completed native
trajectory and cause; do not add epsilon feed or silently treat it as an accepted
closed process. Native tiny-state threshold zeroing must remain disclosed and
its inventory defect tested. H2 COD-equivalent and real gas mass are distinct.

Check each native component and separately COD/C/N invariants with external
feed/liquid/gas export and reaction terms. Demonstrate postprocessing quadrature
refinement at fixed declared budgets; do not relax acceptance to hide coarse
sampling. Original native solver objects must survive every later audit failure.
A native community containing H2 consumers can yield low net H2; preserve that
result. Dedicated fermentation/microbial-electrolysis, full energy/element
closure and source-calibrated yields require separate justified mechanisms,
measurement bases and independently qualified experiments.

## Installation and evidence

Keep optional native stacks separate from the core and from incompatible SciPy
verification profiles. Retain exact artifact hashes, authoritative installed
licenses and all source evidence. NCSA notices must survive any native
redistribution decision; no native code, matrix or dataset is bundled here.
Ship receiving Python examples, actual native cases, negative boundaries,
conservation/refinement reports and a reproducible installed-package check.
