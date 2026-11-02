"""Frozen native ideal-gas mixture flashes for the common property contract.

Cantera owns the EOS, species fits and TPY/HP/SP flashes. The common nozzle in
``h2physics.release`` owns the discharge calculation. No equilibrium or kinetic
calculation is performed here. API and thermochemistry definitions:
https://cantera.org/3.2/python/thermo.html
https://cantera.org/3.2/reference/thermo/species-thermo.html
"""

import hashlib
import json
import math
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from ..core import immutable_array, PropertyBasis, ThermoState, finite
from ..mixtures import GasComposition
from .cantera import MechanismBasis


def _fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode("utf-8")).hexdigest()


def _phase_identity(phase):
    """Thermodynamic definition, excluding mutable state, kinetics and transport."""
    return {
        "name": phase.name, "thermo": phase.thermo_model,
        "species": [
            {"name": species.name, "composition": dict(species.composition),
             "charge": species.charge, "molecular_weight": float(weight).hex(),
             "thermo_type": type(species.thermo).__name__,
             "reference_pressure": float(species.thermo.reference_pressure).hex(),
             "minimum_temperature": float(species.thermo.min_temp).hex(),
             "maximum_temperature": float(species.thermo.max_temp).hex(),
             "coefficients": [float(c).hex() for c in species.thermo.coeffs]}
            for species, weight in zip(phase.species(), phase.molecular_weights, strict=True)
        ],
    }


@dataclass(frozen=True, slots=True)
class FrozenCompositionCorrection:
    """Explicit native-boundary sum repair; no negative species are clipped."""

    raw_mass_fractions: Mapping[str, float]
    raw_sum: float
    corrected_sum: float
    declared_tolerance: float
    corrected_species: str
    mass_fraction_change: float
    correction_id: str

    def __post_init__(self):
        object.__setattr__(self, "raw_mass_fractions",
                           MappingProxyType(dict(self.raw_mass_fractions)))


class CanteraFrozenGasProperties:
    """An immutable composition over an actual caller-owned native Solution.

    The supplied fractions must already sum to one to floating-point precision
    (``math.fsum(Y) == 1.0``). Amounts are never accepted as fractions. Zero entries
    are omitted from identity; all absent native species receive zero mass.
    A caller can explicitly budget a native-boundary sum correction with
    composition_sum_tolerance and composition_correction_id. Its raw vector and
    signed repair are retained. This can declare an off-simplex numerical trial
    extension, which is distinct from accepted-state floating-point roundoff.

    Each call resets native mass basis, composition and temperature before a
    flash, so earlier native state changes cannot leak into results. The native
    thermochemical definition is fingerprinted and checked against later edits.
    Direct concurrent access to the shared native object needs caller locking.
    The mechanism record is a caller declaration, not proof of source identity.

    Molecular H2 is explicitly spin-unresolved in this model. A mechanism's H2
    fit does not supply para/ortho partition thermodynamics or a CoolProp zero.
    """

    def __init__(self, native_phase, mechanism_basis: MechanismBasis,
                 mass_fractions: Mapping[str, float], *,
                 hydrogen_partition_id: str = "mechanism-H2-spin-unresolved",
                 composition_sum_tolerance: float = 0.,
                 composition_correction_id: str | None = None,
                 composition_id: str | None = None):
        try:
            import cantera as ct
        except ImportError as error:
            raise ImportError("Install h2physics[chemistry] for native frozen gas properties") from error
        if (not isinstance(native_phase, ct.Solution)
                or native_phase.thermo_model != "ideal-gas"):
            raise ValueError("Frozen properties require an actual native ideal-gas Solution")
        if native_phase.n_selected_species != native_phase.n_species:
            raise ValueError("Pass the full native phase, not a selected-species view")
        if not isinstance(mechanism_basis, MechanismBasis):
            raise TypeError("Declare a MechanismBasis for the native phase")
        if composition_id is not None and (
            not isinstance(composition_id, str) or not composition_id.strip()
        ):
            raise ValueError("A supplied gas composition identity must be a nonblank string")
        if hydrogen_partition_id != "mechanism-H2-spin-unresolved":
            raise ValueError("Native mechanism H2 is spin-unresolved; normal/para/ortho claims are unsupported")
        if not isinstance(mass_fractions, Mapping) or not mass_fractions:
            raise ValueError("Declare a nonempty species mass-fraction mapping")
        tolerance = finite(composition_sum_tolerance, "composition_sum_tolerance")
        if not 0 <= tolerance <= 1e-6:
            raise ValueError("Composition sum tolerance must lie in [0, 1e-6]")
        if tolerance > 0 and (not isinstance(composition_correction_id, str)
                              or not composition_correction_id.strip()):
            raise ValueError("An explicit composition_correction_id is required for a sum correction policy")
        names = set(native_phase.species_names)
        fractions = {}
        for name, value in mass_fractions.items():
            if not isinstance(name, str) or name not in names:
                raise ValueError("The native phase does not contain every declared species")
            fraction = finite(value, f"mass fraction {name}")
            if not 0 <= fraction <= 1:
                raise ValueError("Mass fractions must lie in [0, 1]")
            if fraction > 0:
                fractions[name] = fraction
        total = math.fsum(fractions.values())
        self.composition_correction = None
        if total != 1.:
            if tolerance == 0 or abs(total-1) > tolerance or not fractions:
                raise ValueError("Mass fractions must already sum to one; no silent normalization "
                                 f"(sum={total:.17g}, declared tolerance={tolerance:g})")
            raw = dict(fractions)
            largest = max(fractions, key=fractions.get)
            fractions[largest] = 1-math.fsum(v for k, v in fractions.items() if k != largest)
            change = fractions[largest]-raw[largest]
            if (not 0 <= fractions[largest] <= 1 or abs(change) > tolerance
                    or math.fsum(fractions.values()) != 1.):
                raise ValueError("Composition sum repair exceeds its declared correction budget")
            self.composition_correction = FrozenCompositionCorrection(
                raw, total, math.fsum(fractions.values()), tolerance, largest, change,
                composition_correction_id)
        fractions = dict(sorted(fractions.items()))
        indices = tuple(native_phase.species_index(name) for name in fractions)
        lower = max(mechanism_basis.minimum_temperature_k,
                    *(native_phase.species(i).thermo.min_temp for i in indices))
        upper = min(mechanism_basis.maximum_temperature_k,
                    *(native_phase.species(i).thermo.max_temp for i in indices))
        if lower >= upper:
            raise ValueError("Declared domain and selected species thermochemistry fit bounds do not overlap")
        self._native_phase = native_phase
        self.mechanism_basis = mechanism_basis
        self._composition_id = composition_id
        self._composition_id_binding = composition_id
        self._mass_fractions = MappingProxyType(fractions)
        self._composition = np.array([fractions.get(name, 0.) for name in native_phase.species_names])
        self._composition = immutable_array(self._composition, name="composition")
        self._molar_mass_kg_mol = float(
            np.dot(self._composition, np.asarray(native_phase.molecular_weights, dtype=float))
            / 1000.
        )
        if not math.isfinite(self._molar_mass_kg_mol) or self._molar_mass_kg_mol <= 0:
            raise ValueError("Native frozen composition has no positive finite mixture molar mass")
        self.minimum_temperature_k, self.maximum_temperature_k = float(lower), float(upper)
        self.version = ct.__version__
        self.composition_sha256 = _fingerprint([(name, value.hex())
                                                for name, value in fractions.items()])
        self.phase_sha256 = _fingerprint(_phase_identity(native_phase))
        has_h2 = any(native_phase.species(i).composition == {"H": 2.}
                     and native_phase.species(i).charge == 0 for i in indices)
        self.hydrogen_partition_id = hydrogen_partition_id if has_h2 else "no-molecular-H2"
        self._basis = PropertyBasis(
            f"Cantera:frozen-ideal-gas:Y-sha256={self.composition_sha256}",
            f"Cantera:{self.version}:{mechanism_basis.identifier}:source-sha256="
            f"{mechanism_basis.source_sha256}:phase-thermo-sha256={self.phase_sha256}:"
            "native-species-formation-enthalpy-and-entropy-reference",
            self.hydrogen_partition_id,
        )
        self._lock = threading.RLock()

    @classmethod
    def from_gas_composition(cls, native_phase, mechanism_basis, composition: GasComposition,
                             **kwargs):
        """Create native frozen-gas properties from a declared mole-basis composition.

        ``GasComposition`` performs only composition algebra. This constructor
        checks each declared species molar mass against the native mechanism before
        converting the composition to the mass fractions required by Cantera. A
        machine-precision-sized sum repair is admitted by default and retained as
        a ``FrozenCompositionCorrection``; callers may supply a stricter zero budget.
        The native phase remains the EOS/thermochemistry owner.
        """
        if type(composition) is not GasComposition:
            raise TypeError("Supply an actual GasComposition with declared molar masses")
        supplied_id = kwargs.pop("composition_id", composition.composition_id)
        if supplied_id != composition.composition_id:
            raise ValueError("A native property binding must retain the GasComposition identity")
        try:
            import cantera as ct
        except ImportError as error:
            raise ImportError(
                "Install h2physics[chemistry] for native frozen gas properties"
            ) from error
        if (not isinstance(native_phase, ct.Solution)
                or native_phase.thermo_model != "ideal-gas"
                or native_phase.n_selected_species != native_phase.n_species):
            raise ValueError("Pass an actual full native ideal-gas Solution")
        try:
            native_masses = np.array(
                [native_phase.molecular_weights[native_phase.species_index(name)] / 1000.
                 for name in composition.species],
                dtype=float,
            )
        except Exception as error:
            raise ValueError("A declared composition species is absent from the native phase") from error
        if not np.allclose(
            native_masses, composition.molar_masses_kg_mol, rtol=2e-8, atol=1e-12
        ):
            raise ValueError("Declared component molar masses differ from native mechanism species")
        kwargs.setdefault(
            "composition_sum_tolerance",
            8.0 * np.finfo(float).eps * len(composition.species),
        )
        correction_tolerance = finite(
            kwargs["composition_sum_tolerance"], "composition_sum_tolerance"
        )
        kwargs["composition_sum_tolerance"] = correction_tolerance
        if correction_tolerance > 0:
            kwargs.setdefault(
                "composition_correction_id",
                f"mole-to-mass-roundoff:{composition.composition_id}",
            )
        provider = cls(
            native_phase,
            mechanism_basis,
            dict(zip(composition.species, composition.mass_fractions, strict=True)),
            composition_id=composition.composition_id,
            **kwargs,
        )
        return provider

    @property
    def native_phase(self):
        return self._native_phase

    @property
    def composition_id(self):
        return self._composition_id

    @property
    def molar_mass_kg_mol(self) -> float:
        """Molar mass of the selected frozen composition in kg/mol."""
        return self._molar_mass_kg_mol

    @property
    def mass_fractions(self) -> Mapping[str, float]:
        return self._mass_fractions

    @property
    def basis(self) -> PropertyBasis:
        return self._basis

    def _check_definition(self):
        phase = self.native_phase
        if self._composition_id != self._composition_id_binding:
            raise ValueError("Caller composition identity changed after provider construction")
        if (phase.thermo_model != "ideal-gas"
                or phase.n_selected_species != phase.n_species
                or _fingerprint(_phase_identity(phase)) != self.phase_sha256):
            raise ValueError("Native phase thermochemical definition changed after provider construction")

    def _pressure(self, pressure_pa):
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        if not (self.mechanism_basis.minimum_pressure_pa <= pressure
                <= self.mechanism_basis.maximum_pressure_pa):
            raise ValueError("Pressure is outside the declared mechanism domain")
        return pressure

    def _temperature(self, temperature_k):
        temperature = finite(temperature_k, "temperature_k", positive=True)
        if not self.minimum_temperature_k <= temperature <= self.maximum_temperature_k:
            raise ValueError("Temperature is outside the mechanism domain or selected species fit bounds")
        return temperature

    def _set_pt(self, pressure, temperature):
        phase = self.native_phase
        phase.basis = "mass"
        phase.TPY = temperature, pressure, self._composition
        # Native TPY normalizes its input even when fsum(Y) is exactly one.
        # Retain the declared floating-point fractions without that rescaling.
        phase.set_unnormalized_mass_fractions(self._composition)
        phase.TP = temperature, pressure

    def _snapshot(self) -> ThermoState:
        phase = self.native_phase
        # Native inversion can place an endpoint a few ulps outside its bound.
        # Only roundoff is admitted; there is no thermochemistry extrapolation.
        for value, lower, upper, name in (
            (phase.T, self.minimum_temperature_k, self.maximum_temperature_k, "Temperature fit"),
            (phase.P, self.mechanism_basis.minimum_pressure_pa,
             self.mechanism_basis.maximum_pressure_pa, "Pressure domain"),
        ):
            if ((value < lower and not math.isclose(value, lower, rel_tol=1e-12))
                    or (value > upper and not math.isclose(value, upper, rel_tol=1e-12))):
                raise ValueError(f"{name} bounds exceeded by native flash")
        if phase.phase_of_matter != "gas":
            raise ValueError("The native property result is not a gas phase")
        if not np.array_equal(phase.Y, self._composition):
            raise ValueError("Native flash changed the declared frozen composition")
        return ThermoState(self.basis, phase.P, phase.T, phase.density_mass,
                           phase.enthalpy_mass, phase.int_energy_mass, phase.entropy_mass, "gas",
                           cp_j_kg_k=phase.cp_mass, cv_j_kg_k=phase.cv_mass,
                           speed_of_sound_m_s=phase.sound_speed, vapor_mass_fraction=1.)

    def state_pt(self, pressure_pa: float, temperature_k: float) -> ThermoState:
        pressure, temperature = self._pressure(pressure_pa), self._temperature(temperature_k)
        with self._lock:
            self._check_definition()
            self._set_pt(pressure, temperature)
            return self._snapshot()

    def _flash(self, pressure_pa, target, pair, attribute):
        pressure, value = self._pressure(pressure_pa), finite(target, attribute)
        with self._lock:
            self._check_definition()
            self._set_pt(pressure, self.minimum_temperature_k)
            low = float(getattr(self.native_phase, attribute))
            if value == low:
                return self._snapshot()
            self._set_pt(pressure, self.maximum_temperature_k)
            high = float(getattr(self.native_phase, attribute))
            if value == high:
                return self._snapshot()
            if not low <= value <= high:
                raise ValueError("Flash target is outside the mechanism domain or selected species fit bounds")
            # A fixed in-domain seed removes dependency on an earlier native state.
            self._set_pt(pressure, (self.minimum_temperature_k + self.maximum_temperature_k)/2)
            setattr(self.native_phase, pair, (value, pressure))
            state = self._snapshot()
            actual = getattr(self.native_phase, attribute)
            if not math.isclose(actual, value, rel_tol=2e-8, abs_tol=1e-5):
                raise ValueError("Native frozen flash did not recover its requested property")
            return state

    def state_ph(self, pressure_pa: float, enthalpy_j_kg: float) -> ThermoState:
        return self._flash(pressure_pa, enthalpy_j_kg, "HP", "enthalpy_mass")

    def state_ps(self, pressure_pa: float, entropy_j_kg_k: float) -> ThermoState:
        return self._flash(pressure_pa, entropy_j_kg_k, "SP", "entropy_mass")
