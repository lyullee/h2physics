# Cryogenic storage, evolving-spin calorics and finite material/process contracts

Receiving candidates: LH2DT, pifira and source-specific material/biological
process providers. This request describes missing capabilities against actual
host contracts. It does not modify those repositories or assert that any
receiving work is complete. Retain native physical owners and Python objects.

## 1. Accepted-step cryo-compressed events and ports

The host `adapters.cryo_compressed.CryoCompressedStorage` composes the actual
LH2DT homogeneous tank, low-level properties, native wall storage, existing
`Lh2dtReliefTankDriver` and the one `HomogeneousIsentropicNozzle`. Actual normal,
para and ortho native paths start at20MPa(abs)/25K. The same EOS/ODE warms above
each native critical temperature while staying above critical pressure. This
does not cross the critical point or require an alternate warm-gas equation.

Expose an accepted-step callback and stop-at-first-pressure capability using
the existing native event mechanism. Return the bracket, root residual,
state before/at/after the event, native time, command/latch history and all
accepted mass/enthalpy/wall-power integrals. A pressure opening, a user-requested
stop and a mass floor are distinct events. A stop must not silently close a
valve or discard residual inventory. State which assumptions exclude hidden
within-step crossings. Keep failed native trial states visible.

Acceptance: reproduce the host's declared six-second21MPa opening cases with
step0.5/0.25/0.125s. Preserve mass/energy, converge the event time and return a
true stop state when requested. Preserve the existing positive-floor event;
do not clip mass or convert a pressure stop into a floor/closure. Independently
invert PT and Prho against actual native properties at accepted states.
Document solid exclusion, single-fluid phase bounds, fixed-spin identity and
geometry/heat-transfer evidence. Refueling, a refrigeration cycle, selective
phase ports and mechanical rating require their own resolved inputs and tests.

The pinned native `TankGeometry` requires strictly positive ambient and
fluid/wall UA, confirmed by actual zero-UA constructor failures. To support
exact adiabatic and thermally decoupled limits, retain positive volume/wall C
but admit nonnegative UA in the native geometry. Test both zero limits and
their energy ledgers there. The host preserves the current native restriction;
it does not replace a zero coefficient with a hidden small positive value.

## 2. One shared evolving-spin energy driver

`PifiraSpinBridge` now supplies actual native temperature-dependent rotor U,
Cv, ortho-minus-para energy and its derivative, plus strictly admitted natural
conversion. The existing `Lh2dtSpinCalorimeter` owns a separate constant-gap
reference level. Generalize a shared driver to consume a constitutive protocol
rather than adding a pifira-specific trajectory integrator:

```python
class SpinCaloricClosure(Protocol):
    def storage_terms(self, state, temperature_k, mass_kg, *, baseline): ...
    def rate(self, state, medium, mass_kg): ...
```

Storage terms must return energy J, derivative with respect to T in J/K,
derivative with respect to para fraction in J, reference/phase/baseline identity
and underlying native objects. Rate returns signed fraction derivative per
second with actual native correlation and its admissibility evidence. Support
held-T and freely evolving-T cases through one driver. At fixed mass, include
both partial derivatives in dE/dt. Reject nonpositive total heat capacity.

Absolute rotor storage may be added to a genuinely nonrotating baseline.
A frozen-spin EOS already includes rotor sensible heat; use a documented
composition-relative correction before coupling to it. Adding absolute rotor
U/Cv to that EOS would count the contribution twice. This bridge is not an
evolving-spin liquid EOS. For H=U+PV, require an evidenced spin-independent-PV
assumption or an actual composition-dependent PV derivative. Do not relabel
rotor U as a liquid enthalpy gap. Density, phase and a compatible energy zero
remain explicit; keep rotor-only thermostat power distinguishable from whole
fluid/tank heat.

The reviewed native Milenko envelope permits liquid17–32K, gas40–120K and
ortho fraction0.62–0.75. The accessible primary abstract gives90kg/m3 density;
the native package permits92kg/m3. Host admission stays at or below90 until
additional primary evidence is reviewed. Do not extend a short-time, high-ortho
fit to low-ortho storage dwell or reverse conversion without new evidence.

Acceptance: rotor-cutoff convergence, independently evaluated chain-rule
derivatives, positive-capacity checks, fixed-T heat/inventory closure, variable-T
energy closure and correct signed heat under reversal where the selected
kinetics actually admits reversal. Compare constant-gap limit to the existing
driver. Preserve native out-of-domain rejection and any nonzero detailed-balance
diagnostic. A favorable oracle at fixed T is numerical verification, not a
catalyst or liquid-storage experiment.

## 3. General finite-gas/material capability and measured microspheres

`materials.DiffusionDomain` is now the sole mobile/trap finite-volume core.
`DiffusionMesh` provides planar or true spherical-shell volumes, face areas
and exact integrated homogeneous radial resistances. `FiniteSurfaceInventory`
couples finite boundary amounts to that same integration. Atomic-H and H2
inventories must retain the corresponding entity conversion.

`MicrosphereStorage` reuses `HydrideGasThermodynamics` density/T and fugacity
callbacks. A shared generic property name/capability can be introduced without
breaking existing hydride imports. Return the actual native fixed-spin states,
molar mass, energy zero, fugacity, and backend identity. Do not introduce a
microsphere EOS or duplicate cavity/wall ODE. Preserve inner/outer total molar
ledgers and the distinction between a surface flux density and total flow.

Needed evidence: actual glass composition, radius/thickness distribution,
source-specific D(T)/solubility and covariance, surface conditions, pressure
and gas-reference observations, temperature histories and experimental
independence. The present uniform prescribed-T model does not compute heat
duty or fracture. Add a heat/stress model only with its additional storage,
heat-transfer and strength inputs. Optical enhancement requires measured or
independently justified material response; thermal permeation alone does not
establish it. A localized cavity depletion event should reuse a common event
capability, rather than clipping negative moles or adding a second solver.

Acceptance: preserve the host planar Fourier/trap cases, exact spherical steady
rate, independent spherical startup series, thin-shell limit, cavity/wall/exterior
mass balance and grid convergence. Then identify coefficients on complete
experiments and assess a genuinely independent held-out experiment; do not call
authored coefficients experimental validation.

## 4. Biological conversion and observation evidence

The qualified `FermentationWorkbook` reads all830 source rows of Hernández's
version2 study, DOI10.17632/2nwcdx9hst.2, CC BY4.0. Its reactor labels do not
establish independent replicates; repeated day coordinates and missing fields
remain preserved. HP/MP/HY/HPR/MPR are reconstructed fields, and same-export
gas-volume algebra is not an independent biological validation target.

Before implementing/fitting a process driver, supply working/headspace volume,
finite liquid/substrate/biomass/gas initial states, feed/withdrawal and pH-control
histories, an explicit gas reference P/T and wet/dry convention, species/COD/
biomass composition, stoichiometric elemental/charge closure and applicable
growth/decay/inhibition evidence. COD concentration is not a substitute for
glucose or biomass mass. Keep the printed L/(L/d) productivity unit unresolved
until authoritative normalization evidence is supplied. Preserve the two
component-production inconsistencies at source row239.

Reuse shared reaction/energy/observation machinery for supplied species and
rates. A native finite biological liquid/gas process may need additional phase
transfer and pH closure; it must not be approximated by silently treating the
whole liquid broth as the existing ideal-gas reactor. Required acceptance is
finite inventory, elemental/charge and energy closure followed by identifiable
parameter estimation and independent whole-study assessment. No Monod fit,
physical gas mass rate or biochemical family completion is claimed from this
workbook alone.
