# Native frozen ideal-gas properties

CanteraFrozenGasProperties supplies the existing PropertyProvider contract from an
actual caller-created Cantera Solution. The common HomogeneousIsentropicNozzle
then executes the same pressure search, mass flow and energy accounting used by
the other property providers. There is no additional EOS, nozzle, equilibrium
solver or kinetic integrator.

The native ideal-gas EOS and selected species caloric fits own density, formation
enthalpy, internal energy, entropy including mixing, cp, cv and frozen sound
speed. Native TPY sets a temperature/pressure/composition state; native HP and SP
invert interior caloric targets. The applicable definitions are in Cantera's
[property API](https://cantera.org/3.2/python/thermo.html),
[species thermodynamic models](https://cantera.org/3.2/reference/thermo/species-thermo.html)
and [ideal-gas phase model](https://cantera.org/3.2/reference/thermo/phase-thermo.html#ideal-gas).

## Python use

Install the optional chemistry dependency. The following loads a separately
installed input through Python to preserve non-ASCII Windows paths; the input
text reaches Cantera unchanged. No mechanism is shipped by h2physics.

~~~python
import hashlib
from pathlib import Path

import cantera as ct

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_properties import CanteraFrozenGasProperties
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

raw = (Path(ct.__file__).parent / "data/h2o2.yaml").read_bytes()
gas = ct.Solution(yaml=raw.decode("utf-8"), name="ohmech")
mechanism = MechanismBasis(
    identifier=f"Cantera:{ct.__version__}:h2o2:ohmech",
    source_sha256=hashlib.sha256(raw).hexdigest(),
    license_id="Cantera-BSD-3-Clause; upstream-GRI-Mech-provenance",
    references=("https://cantera.org/3.2/examples/input/h2o2.html",),
    minimum_temperature_k=300,
    maximum_temperature_k=3000,
    minimum_pressure_pa=1e4,
    maximum_pressure_pa=2e6,
)
properties = CanteraFrozenGasProperties(
    gas, mechanism, {"H2": 0.03, "O2": 0.225, "N2": 0.745}
)
upstream = properties.state_pt(6e5, 850)
recovered = properties.state_ph(6e5, upstream.enthalpy_j_kg)
result = HomogeneousIsentropicNozzle(properties).solve(
    upstream,
    back_pressure_pa=1e5,
    opening=NozzleOpening("gas-vent", 1e-5, 1.0, "declared-effective-area"),
)
assert properties.native_phase is gas
assert result.exit_state.basis == properties.basis
~~~

That envelope and composition define a synthetic execution case. They do not
establish mechanism or ideal-gas accuracy throughout that pressure/temperature
range. The nozzle opening's effective area also needs application-specific
evidence.

## Inputs and retained identity

The constructor accepts native_phase, mechanism_basis and mass_fractions, with
the optional keyword hydrogen_partition_id fixed to the supported value
"mechanism-H2-spin-unresolved". native_phase must be a full native ideal-gas
Solution. Nonideal, condensed and selected-species view objects are rejected.
The source record must be an explicit MechanismBasis.

The mass-fraction mapping must be nonempty, finite, nonnegative and contain only
species in that phase. By default math.fsum of its entries must equal 1.0. This
intentionally rejects amounts such as H2:2, O2:1 and also rejects an
almost-normalized mapping. Zero entries are accepted and omitted from the
composition fingerprint. The public mass_fractions mapping is read-only.

An explicit composition_sum_tolerance can be declared between zero and 1e-6.
A positive budget requires a nonempty composition_correction_id identifying the
caller's chosen policy/evidence. If the sum differs from one within that budget,
only the largest species is replaced by one minus the sum of the others. The
signed change must also fit the budget. There is no all-species normalization
and negative species remain errors at any budget. The immutable
composition_correction record retains raw_mass_fractions, raw_sum, corrected_sum,
declared_tolerance, corrected_species, mass_fraction_change and correction_id.
PropertyBasis fingerprints the corrected declared mixture. A zero correction
needs no record.

This option can declare an extension of a numerical callback away from the
physical composition simplex. In the executed evolving-mixture case, native
CVODES finite-difference Jacobian probes produced a sum offset of about 1.5e-8.
That deliberate trial perturbation differs from accepted-state floating-point
ulp deviations. The example explicitly chooses a 1e-7 trial-extension budget;
it does not classify 1.5e-8 as machine roundoff or qualify arbitrary physical
off-simplex states. The report records both the exact signed maximum correction
and the maximum sampled accepted-state sum deviation. Another integration setup
must declare and test its own applicable budget.

PropertyBasis retains:

- The SHA-256 of sorted, nonzero species names and their exact binary float
  mass-fraction values, represented with float.hex.
- The Cantera version and caller-declared mechanism identifier/source SHA-256.
- A separate SHA-256 of the actual native phase name, ideal-gas model, ordered
  species identities, elemental compositions, charges, molar masses, caloric fit
  model/coefficient values, fit limits and reference pressures.
- The native species formation-enthalpy and entropy reference, including its
  mixing entropy convention.
- The H2 spin identity "mechanism-H2-spin-unresolved", or "no-molecular-H2" when
  no positive-fraction neutral molecular H2 species is present.

Normal, para and ortho hydrogen labels are rejected. The selected mechanism does
not provide a resolved spin partition. Neither the native H2 name nor a shared
temperature gives permission to replace a CoolProp hydrogen enthalpy/entropy
reference. Composition, reference and partition changes fail common-nozzle basis
compatibility checks.

The declared file hash is provenance supplied by the caller. The native
thermochemistry fingerprint records the actual object, but cannot prove that
the object came from the claimed source. Kinetic and transport definitions are
outside this frozen property fingerprint; changing them does not change this
model's caloric states.

## Query and ownership rules

state_pt(P,T), state_ph(P,h) and state_ps(P,s) return ThermoState with absolute
Pa, K, kg/m3, J/kg, J/(kg K), positive cp/cv and frozen sound speed in m/s. The
modeled phase is gas and its modeled gas mass fraction is one. Viscosity and
conductivity remain None; transport is not required by the common nozzle.

The usable temperature interval is the intersection of the declared mechanism
interval and the thermochemistry fit intervals of positive-fraction species.
An unused native species does not shrink it. The declared pressure interval is
checked on every input. PH/PS targets are first bracketed by native endpoint
states at that pressure, preventing accepted caloric extrapolation. An exact
endpoint target reuses its already evaluated native TPY state; interior targets
use native HP/SP and are checked on return. Returned endpoint deviations up to
1e-12 relative are admitted as roundoff without modifying the reported native
state. Failed fits, phases, domain checks or flashes are surfaced.

Each query resets the native mass unit basis and every species mass fraction,
and interior flashes use a fixed in-domain temperature seed. The native
unnormalized-fraction setter restores the exact accepted vector after TPY's
automatic normalization. Earlier caller changes to temperature, pressure,
composition or mass/molar basis therefore do not contaminate results. Later
native thermochemical definition changes are detected and rejected.

The exact native_phase remains available for deep Python composition. Successful
queries leave it at the returned state; rejected queries may leave it at an
intermediate native state. The next query resets it. The adapter locks its own
queries, but external native access must use caller synchronization. A nozzle
callback for a live reactor must use a separate property phase: nozzle flashes
must not mutate the reactor's current state. For an evolving enclosure mixture,
construct a provider for the declared current composition over that separate
phase, then inject the existing nozzle result into the enclosure's vent callback.
For example, after supplying a separate nozzle_phase with matching native
thermochemistry:

~~~python
def vent_flow(time_s, current_volume_phase):
    properties = CanteraFrozenGasProperties(
        nozzle_phase,
        mechanism,
        dict(zip(current_volume_phase.species_names, current_volume_phase.Y, strict=True)),
        composition_sum_tolerance=1e-7,
        composition_correction_id="native-CVODES-Jacobian-largest-species-trial-extension",
    )
    state = properties.state_pt(current_volume_phase.P, current_volume_phase.T)
    result = HomogeneousIsentropicNozzle(properties).solve(
        state,
        back_pressure_pa=1e5,
        opening=NozzleOpening("volume-vent", 1e-5, 0.8, "declared-effective-area"),
    )
    return result.mass_flow_kg_s
~~~

The callback must preserve the active reactor phase. The native volume removes
its own current well-mixed composition and enthalpy; the correction belongs only
to the declared nozzle callback's numerical trial extension.

## Executed evidence and limits

Run from the repository:

~~~powershell
.venv/Scripts/python.exe -m pytest -q tests/test_cantera_properties.py
.venv/Scripts/python.exe scripts/check_cantera_properties.py
~~~

The reproduction script writes
[frozen_gas_properties.md](../research/frozen_gas_properties.md). It executes
72 original constant-cp PT oracle states, 72 PH and 72 PS roundtrips, nine
analytic mixture-nozzle cases including the choking boundary, and four
installed h2o2/gri30 frozen-nozzle cases. It also runs an actual finite native
enclosure with changing H2 fraction, a feed and this shared-nozzle vent callback.
Tests additionally exercise invalid
composition, phase, mechanism domain, selected fit bounds, reference mismatch,
definition mutation and state contamination. The analytic nozzle oracle follows
the [NASA Glenn ideal-gas mass-flow relation](https://www.grc.nasa.gov/www/k-12/airplane/mflchk.html);
the original constant-cp coefficients are synthetic fixtures.

These are software and conservation checks. The two installed inputs share
thermochemistry ancestry; their agreement is not an independent experimental
comparison. No real-gas, cryogenic, condensation, spin conversion, reactive
nozzle, transport, discharge-coefficient or measured mixed-gas vent qualification
is claimed. The provider also supplies no atmospheric source plane, ignition
criterion or enclosure dynamics.

Cantera is separately installed under its
[BSD-3-Clause license](https://github.com/Cantera/cantera/blob/v3.2.0/License.txt).
The example mechanisms have their own declared GRI-Mech-derived provenance.
Neither those input files, third-party code, worked examples nor external data
are copied into this feature. A separately selected mechanism requires its own
source, rights, reference and applicability review.
