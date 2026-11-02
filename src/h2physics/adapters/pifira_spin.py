"""Native temperature-dependent rotor energy and bounded natural spin conversion.

The optional MIT pifira engine owns every partition sum and kinetic correlation.
This bridge supplies state/reference/admission and energy chain-rule contracts;
it supplies neither a mixture EOS nor another trajectory integrator.
Primary basis: doi:10.1016/j.ijhydene.2014.01.205 and doi:10.1007/BF02396837.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import immutable_array, Origin, ThermoState, finite
from ..equipment import BoundaryPower
from .lh2dt_spin import SpinDomain, SpinEquilibrium, SpinRate


@dataclass(frozen=True, slots=True)
class RotorEvidence:
    rotor_source_id: str
    rate_source_id: str
    phase_scope_id: str
    parameter_origin: Origin

    def __post_init__(self):
        if not all(isinstance(value, str) and value.strip() for value in (
                self.rotor_source_id, self.rate_source_id, self.phase_scope_id)):
            raise ValueError("Declare rotor, rate and phase-scope evidence")
        object.__setattr__(self, "parameter_origin", Origin(self.parameter_origin))
        if self.parameter_origin == Origin.UNRESOLVED:
            raise ValueError("Native parameter origin must be resolved")


@dataclass(frozen=True, slots=True)
class RotorEnergyReference:
    """One common additive shift of both native para-J=0 rotor U branches."""

    reference_id: str
    common_offset_j_kg: float = 0.

    def __post_init__(self):
        if not isinstance(self.reference_id, str) or not self.reference_id.strip():
            raise ValueError("Declare the rotor internal-energy reference identity")
        finite(self.common_offset_j_kg, "common rotor energy offset")


@dataclass(frozen=True, slots=True)
class RotorCutoffPolicy:
    energy_absolute_j_kg: float = 1e-5
    capacity_absolute_j_kg_k: float = 1e-6
    relative_tolerance: float = 1e-10

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class MilenkoAdmission:
    """Conservative public-primary density screen, additional to native strict=True.

    The publisher abstract states 0.09 g/cm3; native pifira permits 92 kg/m3.
    This host admits at most 90 kg/m3 until the additional range is evidenced.
    """

    maximum_density_kg_m3: float = 90.
    evidence_id: str = "https://doi.org/10.1007/BF02396837#publisher-abstract-density"

    def __post_init__(self):
        if not 0 < finite(self.maximum_density_kg_m3, "admitted density") <= 90:
            raise ValueError("Public-primary admission cannot exceed 90 kg/m3")
        if not self.evidence_id.strip():
            raise ValueError("Declare density-admission evidence")


@dataclass(frozen=True, slots=True)
class SpinMedium:
    """Prescribed pure-H2 kinetic medium; density/phase are not a spin-mixture EOS."""

    temperature_k: float
    density_kg_m3: float
    phase: str
    density_evidence_id: str
    phase_evidence_id: str
    origin: Origin
    frozen_density_reference: ThermoState | None = None
    composition_density_assumption_id: str = ""

    def __post_init__(self):
        finite(self.temperature_k, "kinetic temperature", positive=True)
        finite(self.density_kg_m3, "hydrogen density", positive=True)
        if self.phase not in {"liquid", "gas"}:
            raise ValueError("Choose the native liquid or gas correlation branch explicitly")
        if not all(isinstance(value, str) and value.strip() for value in (
                self.density_evidence_id, self.phase_evidence_id)):
            raise ValueError("Declare density and phase evidence; do not infer a mixture EOS")
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Kinetic medium data role must be resolved")
        if self.frozen_density_reference is not None:
            if not isinstance(self.composition_density_assumption_id, str) or not self.composition_density_assumption_id.strip():
                raise ValueError("A frozen-EOS density requires an explicit composition-density approximation")
            state = self.frozen_density_reference
            phases = ({"liquid", "supercritical_liquid"} if self.phase == "liquid"
                      else {"gas", "supercritical_gas", "supercritical"})
            if (not isinstance(state, ThermoState) or state.basis.fluid not in
                    {"Hydrogen", "ParaHydrogen", "OrthoHydrogen"}
                    or state.temperature_k != self.temperature_k or state.density_kg_m3 != self.density_kg_m3
                    or state.phase not in phases):
                raise ValueError("Kinetic medium and retained frozen density/phase reference differ")

    @classmethod
    def from_frozen_state(cls, state: ThermoState, *, density_evidence_id, phase_evidence_id,
                          composition_density_assumption_id, origin):
        """Use only existing single-phase H2 density, retaining its fixed-spin basis.

        This is a caller-evidenced density approximation, not an evolving-spin
        property provider. Native rotor energy never comes from EOS differencing.
        """
        if state.basis.fluid not in {"Hydrogen", "ParaHydrogen", "OrthoHydrogen"}:
            raise ValueError("Milenko's pure-hydrogen medium cannot use another fluid")
        if state.phase in {"liquid", "supercritical_liquid"}:
            phase = "liquid"
        elif state.phase in {"gas", "supercritical_gas", "supercritical"}:
            phase = "gas"
        else:
            raise ValueError("Two-phase or unresolved states are not a single correlation medium")
        return cls(state.temperature_k, state.density_kg_m3, phase, density_evidence_id,
            phase_evidence_id, origin, state, composition_density_assumption_id)


@dataclass(frozen=True, slots=True)
class SpinPVAssumption:
    kind: str
    phase_scope: str
    evidence_id: str

    def __post_init__(self):
        if self.kind not in {"ideal-gas-no-mole-change", "caller-spin-independent-PV"}:
            raise ValueError("Declare the explicit spin-independent PV assumption")
        if self.phase_scope not in {"gas", "liquid"} or not self.evidence_id.strip():
            raise ValueError("Declare PV phase scope and evidence")
        if self.kind == "ideal-gas-no-mole-change" and self.phase_scope != "gas":
            raise ValueError("Ideal-gas PV reasoning cannot be assigned to a liquid")


@dataclass(frozen=True, slots=True)
class RotorPoint:
    native_state: Any
    mass_kg: float
    equilibrium: SpinEquilibrium
    energy_reference: RotorEnergyReference
    para_energy_j_kg: float
    ortho_energy_j_kg: float
    para_cv_j_kg_k: float
    ortho_cv_j_kg_k: float
    conversion_energy_j_kg: float
    conversion_energy_temperature_derivative_j_kg_k: float
    mixture_rotational_energy_j: float
    frozen_rotational_capacity_j_k: float
    cutoff_errors: Any
    native_results: Any
    native_thermo: Any
    native_reference_thermo: Any

    def __post_init__(self):
        for name in ("cutoff_errors", "native_results"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


class RotorCutoffError(ValueError):
    def __init__(self, point):
        self.point = point
        super().__init__("Native rotor cutoff fails equilibrium/energy/capacity convergence")


@dataclass(frozen=True, slots=True)
class RotorStorageTerms:
    point: RotorPoint
    energy_kind: str
    energy_j: float
    frozen_capacity_j_k: float
    d_energy_d_para_fraction_j: float
    pv_assumption: SpinPVAssumption | None
    baseline_para_fraction: float | None = None
    baseline_evidence_id: str = ""

    def energy_rate_w(self, *, temperature_rate_k_s, para_fraction_rate_s):
        return (self.frozen_capacity_j_k*finite(temperature_rate_k_s, "temperature rate")
            + self.d_energy_d_para_fraction_j*finite(para_fraction_rate_s, "para-fraction rate"))


@dataclass(frozen=True, slots=True)
class PifiraSpinRate:
    shared_rate: SpinRate
    medium: SpinMedium
    point: RotorPoint
    native_forward_rate_per_s: Any
    native_ortho_fraction_rate_per_s: Any
    native_correlation: Any

    @property
    def para_fraction_rate_s(self):
        return self.shared_rate.para_fraction_rate_s

    @property
    def conversion_heat_w(self):
        return self.shared_rate.conversion_heat_w


@dataclass(frozen=True, slots=True)
class RotorThermostatPower:
    rate: PifiraSpinRate
    time_s: float
    clock_id: str
    support_start_s: float
    support_end_s: float
    boundary_evidence_id: str
    external_power: BoundaryPower
    rotor_energy_rate_w: float


@dataclass(frozen=True, slots=True)
class NativeDetailedBalanceProbe:
    medium: SpinMedium
    equilibrium_ortho_fraction: float
    ortho_fractions: np.ndarray
    native_rates_per_s: Any
    status: str = "mathematical-native-extension; outside-primary-composition-not-admitted"

    def __post_init__(self):
        values = np.array(self.ortho_fractions, dtype=float, copy=True)
        values = immutable_array(values, name="values")
        object.__setattr__(self, "ortho_fractions", values)


class PifiraSpinBridge:
    """Actual native rotor/rate objects with the existing LH2DT para-state type.

    There is no advance/trajectory method: pifira supplies no exact step. The
    existing constant-gap calorimeter cannot accept this T-dependent energy.
    Callers can inject rate points and storage tangents into a general driver.
    """

    def __init__(self, native_module, native_thermo, native_correlation, native_state_type, *,
                 evidence: RotorEvidence, domain: SpinDomain, energy_reference: RotorEnergyReference,
                 cutoff_policy: RotorCutoffPolicy = RotorCutoffPolicy(),
                 admission: MilenkoAdmission = MilenkoAdmission()):
        if (not isinstance(native_thermo, native_module.RigidRotorSpinThermo)
                or not isinstance(native_correlation, native_module.MilenkoCorrelation)):
            raise TypeError("Supply the actual native pifira rotor and Milenko objects")
        if not isinstance(native_state_type, type) or not callable(native_state_type):
            raise TypeError("Supply the actual existing LH2DT OrthoParaState type")
        if not isinstance(evidence, RotorEvidence) or not isinstance(domain, SpinDomain):
            raise TypeError("Supply explicit rotor evidence and the shared SpinDomain")
        if not isinstance(energy_reference, RotorEnergyReference):
            raise TypeError("Use a rotor-U reference, not a constant-gap enthalpy reference")
        if not isinstance(cutoff_policy, RotorCutoffPolicy) or not isinstance(admission, MilenkoAdmission):
            raise TypeError("Supply validated rotor-cutoff and published-domain policies")
        finite(native_thermo.gas_constant_J_kgK, "native rotor gas constant", positive=True)
        finite(native_thermo.gap_J_per_kg, "native rotor ground gap", positive=True)
        cutoff = native_thermo.maximum_J
        if isinstance(cutoff, bool) or not isinstance(cutoff, int) or cutoff < 8:
            raise ValueError("Native rotational cutoff must be an integer at least eight")
        if domain.reference_rotational_level <= cutoff:
            raise ValueError("The reference native rotor must retain a larger cutoff")
        canonical = native_module.MilenkoCorrelation()
        finite(native_correlation.maximum_density_kg_m3, "native correlation density limit", positive=True)
        for key in ("liquid_temperature_K", "gas_temperature_K", "primary_ortho_fraction_range"):
            selected, published = getattr(native_correlation, key), getattr(canonical, key)
            if len(selected) != 2 or not published[0] <= selected[0] < selected[1] <= published[1]:
                raise ValueError("Native correlation parameters cannot widen its published fit domain")
        if not 0 < native_correlation.maximum_density_kg_m3 <= canonical.maximum_density_kg_m3:
            raise ValueError("Native correlation density cannot widen the installed published domain")
        self.native = native_module
        self.thermo, self.correlation, self.state_type = native_thermo, native_correlation, native_state_type
        self.evidence, self.domain, self.energy_reference = evidence, domain, energy_reference
        self.cutoff_policy, self.admission = cutoff_policy, admission
        self.reference_thermo = native_module.RigidRotorSpinThermo(
            gas_constant_J_kgK=native_thermo.gas_constant_J_kgK,
            gap_J_per_kg=native_thermo.gap_J_per_kg, maximum_J=domain.reference_rotational_level)
        self.parameter_fingerprint = self._fingerprint()

    def _fingerprint(self):
        material = (asdict(self.thermo), asdict(self.reference_thermo), asdict(self.correlation))
        return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()

    def _identity(self):
        if self._fingerprint() != self.parameter_fingerprint:
            raise ValueError("Native rotor/rate parameters changed without rebinding evidence")

    def state(self, para_fraction):
        if not 0 <= finite(para_fraction, "para fraction") <= 1:
            raise ValueError("Para fraction must lie in [0,1]")
        return self.state_type(float(para_fraction))

    def _state(self, state):
        if not isinstance(state, self.state_type):
            raise TypeError("Retain the actual existing LH2DT para-fraction state")
        if not 0 <= finite(state.para_fraction, "native para fraction") <= 1:
            raise ValueError("Native para fraction lies outside [0,1]")

    @staticmethod
    def _values(rotor, temperature):
        return {"equilibrium_para": 1-rotor.equilibrium_ortho(temperature),
            "para_energy": rotor.rotational_energy_J_per_kg(temperature, "para"),
            "ortho_energy": rotor.rotational_energy_J_per_kg(temperature, "ortho"),
            "para_cv": rotor.rotational_cv_J_per_kgK(temperature, "para"),
            "ortho_cv": rotor.rotational_cv_J_per_kgK(temperature, "ortho"),
            "gap": rotor.conversion_energy_J_per_kg(temperature),
            "gap_derivative": rotor.d_conversion_energy_dT_J_per_kgK(temperature)}

    def point(self, state, temperature_k, mass_kg):
        self._identity()
        self._state(state)
        temperature = self.domain.require_temperature(temperature_k)
        mass = finite(mass_kg, "hydrogen mass", positive=True)
        raw, reference = self._values(self.thermo, temperature), self._values(self.reference_thermo, temperature)
        for name, value in raw.items():
            finite(value, "native rotor "+name)
            finite(reference[name], "reference rotor "+name)
        values = {name: float(value) for name, value in raw.items()}
        errors = {name: abs(values[name]-float(reference[name])) for name in raw}
        equilibrium = SpinEquilibrium(temperature, values["equilibrium_para"],
            float(reference["equilibrium_para"]), errors["equilibrium_para"],
            self.thermo.maximum_J, self.reference_thermo.maximum_J)
        para = state.para_fraction
        energy = mass*(para*values["para_energy"]+(1-para)*values["ortho_energy"]
                       + self.energy_reference.common_offset_j_kg)
        capacity = mass*(para*values["para_cv"]+(1-para)*values["ortho_cv"])
        finite(energy, "total rotational energy")
        finite(capacity, "total frozen rotational capacity")
        para_energy = finite(values["para_energy"]+self.energy_reference.common_offset_j_kg,
                             "referenced para rotational energy")
        ortho_energy = finite(values["ortho_energy"]+self.energy_reference.common_offset_j_kg,
                              "referenced ortho rotational energy")
        result = RotorPoint(state, mass, equilibrium, self.energy_reference,
            para_energy, ortho_energy, values["para_cv"], values["ortho_cv"],
            values["gap"], values["gap_derivative"], energy, capacity, errors, raw,
            self.thermo, self.reference_thermo)
        failed = errors["equilibrium_para"] > self.domain.cutoff_absolute_tolerance
        for name in ("para_energy", "ortho_energy", "gap", "para_cv", "ortho_cv", "gap_derivative"):
            absolute = (self.cutoff_policy.capacity_absolute_j_kg_k if name.endswith("cv")
                or name == "gap_derivative" else self.cutoff_policy.energy_absolute_j_kg)
            failed |= errors[name] > absolute+self.cutoff_policy.relative_tolerance*abs(float(reference[name]))
        if failed:
            raise RotorCutoffError(result)
        return result

    def _medium(self, medium):
        self._identity()
        if not isinstance(medium, SpinMedium):
            raise TypeError("Declare the kinetic density/phase medium explicitly")
        if medium.density_kg_m3 > self.admission.maximum_density_kg_m3:
            raise ValueError("Density exceeds the explicit conservative public-primary admission")
        return self.correlation.forward_rate_per_s(medium.temperature_k, medium.density_kg_m3,
                                                   medium.phase, strict=True)

    def rate(self, state, medium: SpinMedium, mass_kg):
        forward = self._medium(medium)
        point = self.point(state, medium.temperature_k, mass_kg)
        ortho_rate = self.correlation.ortho_fraction_rate_per_s(1-state.para_fraction,
            medium.temperature_k, medium.density_kg_m3, medium.phase, thermo=self.thermo, strict=True)
        para_rate = -finite(ortho_rate, "native ortho rate")
        heat = finite(point.mass_kg*point.conversion_energy_j_kg*para_rate, "rotor conversion power")
        shared = SpinRate(medium.temperature_k, point.mass_kg, point.equilibrium,
            para_rate, heat, state, (self.thermo, self.correlation))
        return PifiraSpinRate(shared, medium, point, forward, ortho_rate, self.correlation)

    def storage_terms(self, state, temperature_k, mass_kg, *, energy_kind="rotational_U", pv_assumption=None,
                      baseline_para_fraction=None, baseline_evidence_id=""):
        """Rotor contribution or explicit correction to a frozen-composition baseline.

        Absolute rotor terms require a nonrotational sensible baseline. Supplying
        an evidenced baseline fraction instead returns only the energy/capacity
        difference; adding absolute rotor Cv to a full frozen EOS would duplicate
        its rotational storage. These terms do not close pressure or density.
        """
        if energy_kind not in {"rotational_U", "rotational_H"}:
            raise ValueError("Choose a rotational energy contribution, not a full fluid EOS")
        if energy_kind == "rotational_H" and not isinstance(pv_assumption, SpinPVAssumption):
            raise ValueError("Rotational H requires an explicit spin-independent PV assumption/evidence")
        if energy_kind == "rotational_U" and pv_assumption is not None:
            raise ValueError("PV evidence belongs to the explicitly selected enthalpy mapping")
        point = self.point(state, temperature_k, mass_kg)
        energy, capacity = point.mixture_rotational_energy_j, point.frozen_rotational_capacity_j_k
        if baseline_para_fraction is not None:
            if not isinstance(baseline_evidence_id, str) or not baseline_evidence_id.strip():
                raise ValueError("A frozen-composition caloric correction requires baseline evidence")
            baseline = self.point(self.state(baseline_para_fraction), temperature_k, mass_kg)
            energy -= baseline.mixture_rotational_energy_j
            capacity -= baseline.frozen_rotational_capacity_j_k
        elif baseline_evidence_id:
            raise ValueError("Baseline evidence requires its explicit para fraction")
        return RotorStorageTerms(point, energy_kind, energy, capacity,
            finite(-point.mass_kg*point.conversion_energy_j_kg, "rotor composition-energy derivative"), pv_assumption,
            baseline_para_fraction, baseline_evidence_id)

    def thermostat_power(self, state, medium, mass_kg, *, time_s, clock_id,
                         support_start_s, support_end_s, boundary_evidence_id):
        if not clock_id.strip() or not boundary_evidence_id.strip():
            raise ValueError("Declare thermostat clock and rotor-bath boundary evidence")
        time = finite(time_s, "thermostat time")
        start, end = finite(support_start_s, "support start"), finite(support_end_s, "support end")
        if not start <= time <= end or start >= end:
            raise ValueError("Thermostat time lies outside increasing finite clock support")
        rate = self.rate(state, medium, mass_kg)
        return RotorThermostatPower(rate, time, clock_id, start, end, boundary_evidence_id,
            BoundaryPower(heat_w=-rate.conversion_heat_w), -rate.conversion_heat_w)

    def detailed_balance_probe(self, ortho_fractions, medium):
        self._medium(medium)
        self.point(self.state(.5), medium.temperature_k, 1.)
        fractions = np.asarray(ortho_fractions, dtype=float)
        if (fractions.ndim != 1 or not len(fractions) or not np.all(np.isfinite(fractions))
                or np.any(fractions < 0) or np.any(fractions > 1)):
            raise ValueError("Supply explicit finite mathematical probe fractions within [0,1]")
        rates = self.correlation.ortho_fraction_rate_per_s(fractions, medium.temperature_k,
            medium.density_kg_m3, medium.phase, thermo=self.thermo, strict=False)
        return NativeDetailedBalanceProbe(medium, float(self.thermo.equilibrium_ortho(medium.temperature_k)),
                                          fractions, rates)
