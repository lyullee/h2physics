"""Unverified common-reference flux diagnostics of an unchanged HyRAM Flame.

No failed field is corrected, rescaled or accepted. HyRAM retains source,
combustion, flame and radiation ownership; shared native Cantera calorimetry
provides a separate explicitly qualified reference interpretation.
"""

import dataclasses
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import immutable_array, Origin, finite
from ..reactions import StoichiometricReaction, conversion_heat_j
from .cantera_thermo import CanteraMolarEnthalpy
from .cantera_volume import _phase_fingerprint
from .hyram_flame import HyRAMFlameRun, HyRAMRadiationRun, _native_flame_signature

STATUS = "implemented_unverified"
_SPECIES = ("H2", "O2", "H2O", "N2", "CO2")
_NATIVE_FILES = {
    "_flame.py": "9a5954cdb304531ae877ce855cc3851f18fbb23d87725324c4018becdc2671d8",
    "_jet.py": "46e80d82aee29e1912e32f626a4c04f6d390e07e7dd3398c5c28c372835301a6",
    "_therm.py": "fdc042d6aa62cac4c6b99f068410bdb6e0573d1f3054caa5fa5d9fc20385840d",
    "_comps.py": "6270f56c7dc904ab4be357ba15f5b55e13b94a83f4621a204e10e21908b8ea57",
    "_notional_nozzle.py": "157b1a2861b85ff1523fea1c9ccdfdc3f0bb051fe4d044652481015486abcb66",
    "_fuel_props.py": "380432a75611da0b3f66f6a4e7ea81b425b39f3ab3150ad64d584b6f2de8181f",
}


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")


def _fields(value):
    return tuple((f.name, getattr(value, f.name)) for f in dataclasses.fields(value))


def _frozen(values):
    return MappingProxyType(dict(values))


def _method_binding(value):
    function = getattr(value, "__func__", value)
    return function, getattr(function, "__code__", None), id(getattr(value, "__self__", None))


def _native_signature(flame):
    digest = hashlib.sha256(_native_flame_signature(flame).encode())
    for function in (flame.chem.T_prod, flame.chem.drhodf):
        for array in (function.x, function.y):
            value = np.asarray(array, dtype="<f8")
            digest.update(repr(value.shape).encode())
            digest.update(value.tobytes())
    digest.update(repr((flame.chem.Treac, flame.chem.Preac, flame.chem.reac,
        sorted(flame.chem.MW.items()), flame.initial_node.__dict__,
        flame.developing_flow.fluid_exp.__dict__, id(flame.chem), id(flame.chem.T_prod),
        id(flame.chem.drhodf), _method_binding(flame.chem.rho_prod),
        _method_binding(flame.chem._Yprod))).encode())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ConservationInterpretation:
    evidence_id: str
    source_plane_id: str
    ambient_surrogate_evidence_id: str
    hydrogen_partition_assumption_id: str
    caloric_reference_evidence_id: str
    native_gaussian_field_evidence_id: str
    origin: Origin

    def __post_init__(self):
        for name in ("evidence_id", "source_plane_id", "ambient_surrogate_evidence_id",
                     "hydrogen_partition_assumption_id", "caloric_reference_evidence_id",
                     "native_gaussian_field_evidence_id"):
            _text(getattr(self, name), name)
        origin = Origin(self.origin)
        if origin == Origin.UNRESOLVED:
            raise ValueError("The cross-model caloric interpretation needs an explicit data role")
        object.__setattr__(self, "origin", origin)


@dataclass(frozen=True, slots=True)
class ConservationQuadrature:
    cutoff_widths: float
    panels: int
    order: int
    mass_difference_budget_kg_s: float
    power_difference_budget_w: float
    native_fraction_sum_budget: float

    def __post_init__(self):
        for name in ("cutoff_widths", "mass_difference_budget_kg_s",
                     "power_difference_budget_w", "native_fraction_sum_budget"):
            finite(getattr(self, name), name, positive=True)
        if self.cutoff_widths < 5:
            raise ValueError("Declare at least five native Gaussian widths")
        for value in (self.panels, self.order):
            if isinstance(value, bool) or not isinstance(value, int) or value < 8:
                raise ValueError("Use at least eight radial panels and order-eight quadrature")


@dataclass(frozen=True, slots=True)
class SectionFlux:
    native_index: int
    arclength_m: float
    total_mass_kg_s: float
    native_fuel_origin_kg_s: float
    species_mass_kg_s: Any
    element_mass_kg_s: Any
    common_reference_excess_enthalpy_w: float
    kinetic_power_w: float
    total_excess_power_w: float
    maximum_native_fraction_sum_defect: float
    native_temperature_bounds_k: tuple

    def __post_init__(self):
        object.__setattr__(self, "species_mass_kg_s", _frozen(self.species_mass_kg_s))
        object.__setattr__(self, "element_mass_kg_s", _frozen(self.element_mass_kg_s))


@dataclass(frozen=True, slots=True)
class SectionAudit:
    fine: SectionFlux
    coarse: SectionFlux
    maximum_mass_quadrature_difference_kg_s: float
    power_quadrature_difference_w: float
    quadrature_within_budget: bool


@dataclass(frozen=True, slots=True)
class JetFireConservationRun:
    source_flame: HyRAMFlameRun
    interpretation: ConservationInterpretation
    quadrature: ConservationQuadrature
    caloric_provider: CanteraMolarEnthalpy
    shared_reference_reaction: StoichiometricReaction
    reference_conversion: Any
    reference_reaction_delta_h_j_mol_h2: float
    native_caloric_phase_fingerprint: str
    native_flame_signature: str
    sections: tuple[SectionAudit, ...]
    sampled_every_native_section: bool
    source_expanded_common_excess_power_w: float
    source_to_entry_common_power_residual_w: float
    source_to_entry_hydrogen_mass_residual_kg_s: float
    visible_hydrogen_flux_change_kg_s: float
    visible_total_mass_change_kg_s: float
    two_stream_required_air_inflow_kg_s: float
    two_stream_element_residuals_kg_s: Any
    visible_energy_reference_sensitivities_kg_s: Any
    visible_excess_power_change_w: float
    native_emitted_radiative_power_w: float
    unclosed_visible_energy_rate_w: float
    required_heat_input_w: None = None
    gravitational_and_pressure_work_resolved: bool = False

    def __post_init__(self):
        object.__setattr__(self, "two_stream_element_residuals_kg_s",
                           _frozen(self.two_stream_element_residuals_kg_s))
        object.__setattr__(self, "visible_energy_reference_sensitivities_kg_s",
                           _frozen(self.visible_energy_reference_sensitivities_kg_s))

    @property
    def accepted(self):
        return False

    @property
    def status(self):
        return "diagnostic-only-unverified-native-jet-fire"

    def require_accepted(self):
        raise JetFireConservationAdmissibilityError(self)

    @property
    def held_steady_window_budgets(self):
        """Conditional steady integrals only; no transient/inventory model."""
        duration = self.source_flame.window.end_s-self.source_flame.window.start_s
        values = {"duration_s": duration,
            "source_hydrogen_mass_kg": duration*self.source_flame.mass_flow_kg_s,
            "source_to_entry_hydrogen_residual_kg": duration*self.source_to_entry_hydrogen_mass_residual_kg_s,
            "native_emitted_radiation_j": duration*self.native_emitted_radiative_power_w,
            "unclosed_energy_j": duration*self.unclosed_visible_energy_rate_w}
        if not all(math.isfinite(v) for v in values.values()):
            raise ValueError("Finite steady-window interpretation overflowed")
        return _frozen(values)


@dataclass(frozen=True, slots=True)
class DiagnosticRadiationBinding:
    conservation: JetFireConservationRun
    original_native_radiation: HyRAMRadiationRun

    @property
    def accepted(self):
        return False

    @property
    def kernel_accepted(self):
        return self.original_native_radiation.kernel_accepted


class JetFireConservationError(RuntimeError):
    def __init__(self, cause, *, auditor, source_flame, completed_sections=(),
                 native_index=None, native_radius_widths=None):
        super().__init__(str(cause))
        self.cause, self.auditor, self.source_flame = cause, auditor, source_flame
        self.completed_sections = tuple(completed_sections)
        self.native_index, self.native_radius_widths = native_index, native_radius_widths


class JetFireConservationAdmissibilityError(ValueError):
    def __init__(self, result):
        self.result, self.native = result, result.source_flame.native
        super().__init__("Diagnostic flux/reference bookkeeping does not accept or correct the native jet fire")


class HyRAMFlameConservation:
    """Audit selected unchanged native sections on a shared formation reference.

    This is a finite visible-domain residual interpretation. It does not solve
    source establishment, correct chemistry, distribute missing heat, add a
    radiating energy equation or remove native rejection.
    """

    def __init__(self, caloric: CanteraMolarEnthalpy, interpretation: ConservationInterpretation,
                 quadrature: ConservationQuadrature):
        if not isinstance(caloric, CanteraMolarEnthalpy):
            raise TypeError("Reuse the actual shared native CanteraMolarEnthalpy provider")
        for value, cls in ((interpretation, ConservationInterpretation),
                           (quadrature, ConservationQuadrature)):
            if not isinstance(value, cls):
                raise TypeError(f"Supply an actual {cls.__name__}")
            cls(**dict(_fields(value)))
        names = tuple(s.identifier for s in caloric.species)
        if set(names) != set(_SPECIES) or len(names) != len(_SPECIES):
            raise ValueError("Map exactly native H2/O2/H2O/N2/CO2 gas species on one shared caloric reference")
        if any(s.phase != "ideal-gas" or s.charge != 0 for s in caloric.species):
            raise ValueError("Only neutral native ideal-gas caloric species are admitted")
        phase = caloric.native_phase
        if phase.thermo_model != "ideal-gas":
            raise ValueError("The diagnostic reference must retain its actual ideal-gas phase")
        coefficients = {"H2": -1., "O2": -.5, "H2O": 1., "N2": 0., "CO2": 0.}
        self.reference_reaction = StoichiometricReaction("native-H2-oxidation-reference-not-field-kinetics",
            caloric.species, tuple(coefficients[name] for name in names))
        self.reference_conversion = self.reference_reaction.convert({"H2": 1., "O2": .5}, 1.)
        self.caloric, self.interpretation, self.quadrature = caloric, interpretation, quadrature
        self.names = names
        self.molar_masses = np.array([s.molar_mass_kg_mol for s in caloric.species])
        self.elements = tuple(phase.element_names)
        self.element_fractions = np.array([[phase.n_atoms(phase.species_index(name), element)
            *phase.atomic_weight(element)/phase.molecular_weights[phase.species_index(name)]
            for name in names] for element in self.elements])
        self.molar_masses = immutable_array(self.molar_masses, name="molar_masses")
        self.element_fractions = immutable_array(self.element_fractions, name="element_fractions")
        self.phase_fingerprint = _phase_fingerprint(phase, include_reactions=True)
        self._binding = (caloric, phase, tuple(caloric.species), caloric.basis_id,
            _fields(caloric.mechanism_basis), tuple(caloric._indices), _method_binding(caloric.enthalpies_j_mol),
            _fields(interpretation), _fields(quadrature), self._quantitative_binding())
        self._issued = {}

    def _guard(self):
        c = self.caloric
        current = (c, c.native_phase, tuple(c.species), c.basis_id, _fields(c.mechanism_basis),
            tuple(c._indices), _method_binding(c.enthalpies_j_mol),
            _fields(self.interpretation), _fields(self.quadrature), self._quantitative_binding())
        if current != self._binding or _phase_fingerprint(c.native_phase, include_reactions=True) != self.phase_fingerprint:
            raise ValueError("Shared native caloric definitions/ownership or diagnostic scope changed")

    def _quantitative_binding(self):
        return (self.names, self.elements, self.molar_masses.tobytes(), self.element_fractions.tobytes(),
            id(self.reference_reaction), repr(self.reference_reaction), id(self.reference_conversion),
            self.reference_conversion.extent_mol,
            self.reference_conversion.initial_mol.tobytes(), self.reference_conversion.final_mol.tobytes())

    def _species_h(self, temperature, pressure):
        values = np.asarray(self.caloric.enthalpies_j_mol(temperature, pressure), dtype=float)
        if values.shape != (len(self.names),) or not np.all(np.isfinite(values)):
            raise ValueError("Actual shared native caloric vector is nonfinite or reordered")
        return values/self.molar_masses

    def _fractions(self, chemistry, fraction):
        raw = chemistry._Yprod(fraction)
        if set(raw) != set(self.names):
            raise ValueError("Actual native product species differ from the admitted reference")
        values = np.array([finite(float(raw[name]), "actual native mass fraction") for name in self.names])
        defect = float(math.fsum(values)-1.)
        if np.any(values < 0) or abs(defect) > self.quadrature.native_fraction_sum_budget:
            raise ValueError("Native fractions violate their mass simplex; no normalization is performed")
        return values, defect

    @staticmethod
    def _require_native(run):
        from importlib import metadata

        from hyram.phys import Flame

        if not isinstance(run, HyRAMFlameRun) or type(run.native) is not Flame:
            raise TypeError("Use the actual original HyRAMFlameRun/native Flame")
        if metadata.version("hyram") != "6.1":
            raise ValueError("This diagnostic contract targets the reviewed HyRAM+6.1")
        directory = Path(Flame.__init__.__code__.co_filename).resolve().parent
        if any(hashlib.sha256((directory/name).read_bytes()).hexdigest() != digest
               for name, digest in _NATIVE_FILES.items()):
            raise ValueError("Original native source bytes differ from the reviewed failed baseline")
        if _native_flame_signature(run.native) != run.native_signature:
            raise ValueError("Native flame changed after its original audit")
        if (run.mass_flow_kg_s != run.native.mass_flow_rate
                or run.emitted_radiative_power_w != run.native.Srad
                or run.ambient.pressure_pa != run.native.ambient.P
                or run.ambient.temperature_k != run.native.ambient.T):
            raise ValueError("Original cached flow/power/ambient summaries differ from the actual native object")
        if run.location.clock_id != run.window.clock_id:
            raise ValueError("Declare one source/steady-window clock before interpreting finite budgets")
        finite(run.window.end_s-run.window.start_s, "finite steady interpretation duration", positive=True)
        if (not run.gates.get("finite positive full-visible native flame", False)
                or len(run.native.S) < 2
                or not math.isclose(run.native.S[-1], run.native.Lvis, rel_tol=1e-8, abs_tol=1e-10)):
            raise ValueError("Visible-domain energy bookkeeping requires the actual complete visible native flame")

    def _section(self, run, index, order, ambient_h, position):
        native, q = run.native, self.quadrature
        width, centre_fraction, centre_velocity = native.B[index], native.f_cl[index], native.V_cl[index]
        if not (width > 0 and 0 < centre_fraction <= 1 and centre_velocity > 0):
            raise ValueError("Actual native section leaves its positive Gaussian domain")
        knots = np.unique(native.chem.T_prod.x)
        inner = knots[(knots > 0) & (knots < centre_fraction)]
        split = native.lamf*np.sqrt(np.log(centre_fraction/inner))
        bounds = np.unique(np.r_[np.linspace(0., q.cutoff_widths, q.panels+1),
                                 split[split < q.cutoff_widths]])
        nodes, weights = np.polynomial.legendre.leggauss(order)
        totals = np.zeros(2+len(self.names)+len(self.elements)+2)
        temperature_low, temperature_high, maximum_defect = math.inf, -math.inf, 0.
        for left, right in zip(bounds[:-1], bounds[1:], strict=True):
            half = (right-left)/2
            for point, weight in zip(nodes, weights, strict=True):
                radius = float(left+half*(point+1))
                position["radius_widths"] = radius
                fraction = float(centre_fraction*np.exp(-(radius/native.lamf)**2))
                velocity = float(centre_velocity*np.exp(-(radius/native.lamv)**2))
                density = finite(float(native.chem.rho_prod(fraction)), "actual native product density", positive=True)
                temperature = finite(float(native.chem.T_prod(fraction)), "actual native product temperature", positive=True)
                composition, defect = self._fractions(native.chem, fraction)
                h = float(composition@self._species_h(temperature, run.ambient.pressure_pa))
                vector = np.r_[1., fraction, composition, self.element_fractions@composition,
                               h-ambient_h, .5*velocity**2]
                totals += (2*math.pi*width**2*radius*density*velocity*half*weight)*vector
                maximum_defect = max(maximum_defect, abs(defect))
                temperature_low, temperature_high = min(temperature_low, temperature), max(temperature_high, temperature)
        if not np.all(np.isfinite(totals)):
            raise ValueError("Nonfinite actual native field/common-reference flux integral")
        start = 2
        species = dict(zip(self.names, totals[start:start+len(self.names)], strict=True))
        start += len(self.names)
        elements = dict(zip(self.elements, totals[start:start+len(self.elements)], strict=True))
        return SectionFlux(index, float(native.S[index]), float(totals[0]), float(totals[1]),
            species, elements, float(totals[-2]), float(totals[-1]), float(totals[-2]+totals[-1]),
            maximum_defect, (temperature_low, temperature_high))

    def audit(self, source_flame: HyRAMFlameRun, *, native_section_indices) -> JetFireConservationRun:
        completed, index, position = [], None, {}
        try:
            self._guard()
            self._require_native(source_flame)
            signature = _native_signature(source_flame.native)
            native = source_flame.native
            indices = tuple(native_section_indices)
            if (not indices or any(isinstance(i, bool) or not isinstance(i, int) for i in indices)
                    or indices[0] != 0 or indices[-1] != len(native.S)-1
                    or any(b <= a for a, b in zip(indices[:-1], indices[1:], strict=True))):
                raise ValueError("Select ordered original native sections including entry and visible endpoint")
            ambient_y, _ = self._fractions(native.chem, 0.)
            pressure = source_flame.ambient.pressure_pa
            ambient_h = float(ambient_y@self._species_h(source_flame.ambient.temperature_k, pressure))
            expanded = native.developing_flow.fluid_exp
            source_h = self._species_h(expanded.T, pressure)[self.names.index("H2")]
            source_power = source_flame.mass_flow_kg_s*(source_h-ambient_h+.5*expanded.v**2)
            delta_h = conversion_heat_j(self.reference_conversion, self.caloric,
                inlet_temperature_k=source_flame.ambient.temperature_k,
                outlet_temperature_k=source_flame.ambient.temperature_k, pressure_pa=pressure)
            for index in indices:
                fine = self._section(source_flame, index, self.quadrature.order, ambient_h, position)
                coarse = self._section(source_flame, index, self.quadrature.order//2, ambient_h, position)
                differences = [abs(fine.total_mass_kg_s-coarse.total_mass_kg_s),
                    abs(fine.native_fuel_origin_kg_s-coarse.native_fuel_origin_kg_s)]
                differences.extend(abs(fine.species_mass_kg_s[n]-coarse.species_mass_kg_s[n]) for n in self.names)
                differences.extend(abs(fine.element_mass_kg_s[n]-coarse.element_mass_kg_s[n]) for n in self.elements)
                mass_difference = float(max(differences))
                power_difference = abs(fine.total_excess_power_w-coarse.total_excess_power_w)
                completed.append(SectionAudit(fine, coarse, mass_difference, power_difference,
                    mass_difference <= self.quadrature.mass_difference_budget_kg_s
                    and power_difference <= self.quadrature.power_difference_budget_w))
                self._guard()
                if _native_signature(native) != signature:
                    raise ValueError("Native source/chemistry/field changed during diagnostic quadrature")
            first, last = completed[0].fine, completed[-1].fine
            hydrogen_change = last.element_mass_kg_s["H"]-first.element_mass_kg_s["H"]
            mass_change = last.total_mass_kg_s-first.total_mass_kg_s
            air_change = mass_change-hydrogen_change
            ambient_elements = self.element_fractions@ambient_y
            fuel_elements = self.element_fractions[:, self.names.index("H2")]
            element_residuals = {name: last.element_mass_kg_s[name]-first.element_mass_kg_s[name]
                -air_change*ambient_elements[k]-hydrogen_change*fuel_elements[k]
                for k, name in enumerate(self.elements)}
            reference_sensitivities = {name: last.element_mass_kg_s[name]-first.element_mass_kg_s[name]
                -mass_change*ambient_elements[k] for k, name in enumerate(self.elements)}
            energy_change = last.total_excess_power_w-first.total_excess_power_w
            unclosed = energy_change+source_flame.emitted_radiative_power_w
            values = (source_power, delta_h, hydrogen_change, mass_change, air_change, energy_change, unclosed,
                      *element_residuals.values(), *reference_sensitivities.values())
            if not all(math.isfinite(v) for v in values):
                raise ValueError("Nonfinite visible-domain diagnostic residual")
            result = JetFireConservationRun(source_flame, self.interpretation, self.quadrature, self.caloric,
                self.reference_reaction, self.reference_conversion, delta_h, self.phase_fingerprint,
                signature, tuple(completed), len(indices) == len(native.S), source_power,
                first.total_excess_power_w-source_power,
                first.element_mass_kg_s["H"]-source_flame.mass_flow_kg_s,
                hydrogen_change, mass_change, air_change, element_residuals, reference_sensitivities,
                energy_change, source_flame.emitted_radiative_power_w, unclosed)
            self._issued[id(result)] = (result, self._result_binding(result))
            return result
        except Exception as cause:
            raise JetFireConservationError(cause, auditor=self, source_flame=source_flame,
                completed_sections=completed, native_index=index,
                native_radius_widths=position.get("radius_widths")) from cause

    @staticmethod
    def _result_binding(result):
        source = result.source_flame
        return repr((id(source), source.native_signature, source.upstream, source.ambient,
            source.opening, source.location, source.window, dict(source.gates), source.accepted,
            id(result.caloric_provider), id(result.shared_reference_reaction), id(result.reference_conversion),
            tuple((f.name, getattr(result, f.name)) for f in dataclasses.fields(result)
                if f.name not in {"source_flame", "caloric_provider", "shared_reference_reaction", "reference_conversion"})))

    def bind_native_radiation(self, conservation, radiation):
        """Bind an existing native radiation result; do not rerun its kernel."""
        self._guard()
        entry = self._issued.get(id(conservation))
        if entry is None or entry[0] is not conservation or self._result_binding(conservation) != entry[1]:
            raise ValueError("Bind the original unchanged owner-issued conservation diagnostic")
        self._require_native(conservation.source_flame)
        if _native_signature(conservation.source_flame.native) != conservation.native_flame_signature:
            raise ValueError("Native flame changed after the conservation audit")
        if not isinstance(radiation, HyRAMRadiationRun) or radiation.flame is not conservation.source_flame:
            raise ValueError("Radiation must be the original result of this same native flame")
        raw = np.asarray(radiation.native_flux, dtype=float).reshape(-1)
        if not np.array_equal(raw, radiation.irradiance_w_m2):
            raise ValueError("Cached native radiation values changed; no replacement flux is accepted")
        return DiagnosticRadiationBinding(conservation, radiation)
