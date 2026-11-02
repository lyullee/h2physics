"""Native two-point multicomponent/Knudsen/Darcy transport through porous solid.

Cantera owns the gas EOS, transport fits and DustyGas molar-flux solve.
https://cantera.org/3.2/python/transport.html#cantera.DustyGasTransport
This constitutive result is not a membrane device, recovery or thermal closure.
"""

import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass

import numpy as np

from ..core import immutable_array, Origin, finite
from .cantera import MechanismBasis
from .cantera_volume import NativePhaseCopyAudit, _phase_fingerprint, _private_native_phase

COMPOSITION_ROUNDOFF = 8 * np.finfo(float).eps
TRANSPORT_COPY_RELATIVE_LIMIT = 2e-13
FLUX_FRAME = "signed total species transport relative to stationary porous solid; positive left to right"


def _ids(*values):
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Declare boundary, phase, geometry, source and reference identities")


def _array(values, *, finite_only=True):
    raw = np.asarray(values)
    if raw.dtype.kind in {"b", "c"} or any(isinstance(item, (bool, np.bool_))
            for item in np.asarray(values, dtype=object).flat):
        raise ValueError("Physical arrays cannot contain booleans or complex values")
    result = np.array(values, dtype=float, copy=True)
    if finite_only and not np.all(np.isfinite(result)):
        raise ValueError("Native transport arrays must be finite")
    result = immutable_array(result, name="result")
    return result


def _hash(value):
    def scalar(item):
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError(f"Unsupported fingerprint field {type(item).__name__}")
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False, default=scalar).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PorousTransportGeometry:
    porosity: float
    tortuosity: float
    mean_pore_radius_m: float
    permeability_m2: float
    thickness_m: float
    geometry_id: str
    evidence_id: str
    origin: Origin

    def __post_init__(self):
        for name in ("porosity", "tortuosity", "mean_pore_radius_m", "permeability_m2", "thickness_m"):
            object.__setattr__(self, name, finite(getattr(self, name), name))
        if not 0 < finite(self.porosity, "porosity") < 1:
            raise ValueError("Porosity must lie strictly inside (0,1)")
        if finite(self.tortuosity, "native tortuosity factor") < 1:
            raise ValueError("Use an explicit native tortuosity factor >=1; no squared convention is inferred")
        finite(self.mean_pore_radius_m, "mean pore radius", positive=True)
        finite(self.thickness_m, "positive left-to-right separation", positive=True)
        if finite(self.permeability_m2, "explicit permeability") < 0:
            raise ValueError("Explicit permeability must be nonnegative; no native default correlation")
        _ids(self.geometry_id, self.evidence_id)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Resolve pore-parameter provenance before transport")


@dataclass(frozen=True, slots=True)
class MembraneEndpoint:
    temperature_k: float
    pressure_pa_absolute: float
    species: tuple[str, ...]
    fractions: np.ndarray
    composition_basis: str
    boundary_id: str
    phase_id: str
    geometry_id: str
    source_id: str
    origin: Origin

    def __post_init__(self):
        object.__setattr__(self, "temperature_k", finite(self.temperature_k, "endpoint temperature", positive=True))
        object.__setattr__(self, "pressure_pa_absolute", finite(self.pressure_pa_absolute, "endpoint absolute pressure", positive=True))
        _ids(self.boundary_id, self.phase_id, self.geometry_id, self.source_id)
        names, values = tuple(self.species), _array(self.fractions)
        if (not names or len(set(names)) != len(names) or any(not isinstance(n, str) or not n for n in names)
                or values.shape != (len(names),) or np.any(values < 0)
                or abs(math.fsum(values)-1) > COMPOSITION_ROUNDOFF):
            raise ValueError("Declare exact species order and nonnegative normalized fractions; no native normalization repair")
        if self.composition_basis not in {"mole", "mass"}:
            raise ValueError("Declare mole or mass fraction basis explicitly")
        object.__setattr__(self, "species", names)
        object.__setattr__(self, "fractions", values)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Resolve endpoint observation/operating role")

    @property
    def content_sha256(self):
        return _hash({**asdict(self), "fractions": self.fractions.tolist()})


@dataclass(frozen=True, slots=True)
class MembraneTransportEvidence:
    transport_source_id: str
    gas_phase_id: str
    gas_scope_id: str
    energy_reference_id: str
    hydrogen_partition_id: str

    def __post_init__(self):
        _ids(self.transport_source_id, self.gas_phase_id, self.gas_scope_id,
             self.energy_reference_id, self.hydrogen_partition_id)


@dataclass(frozen=True, slots=True)
class MembraneGasSnapshot:
    temperature_k: float
    pressure_pa_absolute: float
    density_kg_m3: float
    mole_fractions: np.ndarray
    mass_fractions: np.ndarray
    partial_molar_enthalpies_j_mol: np.ndarray

    def __post_init__(self):
        for name in ("temperature_k", "pressure_pa_absolute", "density_kg_m3"):
            finite(getattr(self, name), name, positive=True)
        for name in ("mole_fractions", "mass_fractions", "partial_molar_enthalpies_j_mol"):
            object.__setattr__(self, name, _array(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class NativeTransportCopyAudit:
    source_sha256: str
    owned_sha256: str
    maximum_relative_roundtrip: float
    relative_roundtrip_limit: float = TRANSPORT_COPY_RELATIVE_LIMIT


def _transport_data(phase):
    n = phase.n_species
    return {"model": phase.transport_model, "CK_mode": phase.CK_mode,
        "viscosity": [phase.get_viscosity_polynomial(i).tolist() for i in range(n)],
        "binary_diffusion": [phase.get_binary_diff_coeffs_polynomial(i, j).tolist()
                             for i in range(n) for j in range(i, n)],
        "collision_integrals": [[p.tolist() for p in phase.get_collision_integral_polynomials(i, j)]
                                for i in range(n) for j in range(i, n)]}


def _transport_copy_audit(source, owned):
    before, after = _transport_data(source), _transport_data(owned)
    errors = []
    for name in ("viscosity", "binary_diffusion", "collision_integrals"):
        a, b = np.asarray(before[name]), np.asarray(after[name])
        if a.shape != b.shape or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
            raise ValueError("Invalid native transport fits or changed coefficient axes")
        denominator = np.maximum(abs(a), abs(b))
        relative = np.divide(abs(a-b), denominator, out=np.zeros_like(a), where=denominator > 0)
        errors.append(float(np.max(relative)))
    maximum = max(errors)
    if before["model"] != after["model"] or before["CK_mode"] != after["CK_mode"] or maximum > TRANSPORT_COPY_RELATIVE_LIMIT:
        raise ValueError("Native transport copy lost runtime-modified fits; no silent transport replacement")
    return NativeTransportCopyAudit(_hash(before), _hash(after), maximum)


def _snapshot(phase):
    return MembraneGasSnapshot(phase.T, phase.P, phase.density_mass, phase.X, phase.Y,
                               phase.partial_molar_enthalpies/1000.)


def _input_fingerprint(left, right, geometry, basis, evidence, source_phase, source_transport):
    return _hash(dict(left=left.content_sha256, right=right.content_sha256,
        geometry=asdict(geometry), mechanism=asdict(basis), evidence=asdict(evidence),
        source_phase=source_phase, source_transport=source_transport))


@dataclass(frozen=True, slots=True)
class MembraneFlux:
    left: MembraneEndpoint
    right: MembraneEndpoint
    geometry: PorousTransportGeometry
    mechanism_basis: MechanismBasis
    evidence: MembraneTransportEvidence
    species: tuple[str, ...]
    left_state: MembraneGasSnapshot
    right_state: MembraneGasSnapshot
    native_mean_state: MembraneGasSnapshot
    native_flux_kmol_m2_s: np.ndarray
    molar_flux_mol_m2_s: np.ndarray
    mass_flux_kg_m2_s: np.ndarray
    molecular_weights_kg_mol: np.ndarray
    native_multi_diffusion_m2_s: np.ndarray
    source_phase: object
    owned_endpoint_phases: tuple
    native_dusty_gas: object
    phase_copy_audits: tuple[NativePhaseCopyAudit, ...]
    transport_copy_audits: tuple[NativeTransportCopyAudit, ...]
    source_phase_sha256: str
    owned_phase_sha256: str
    input_sha256: str
    frame: str = FLUX_FRAME
    thermal_closure: str = "unresolved; endpoint enthalpies are native reference diagnostics, not an energy balance"

    def __post_init__(self):
        n = len(self.species)
        if (self.species != self.left.species or self.species != self.right.species
                or self.left.geometry_id != self.geometry.geometry_id
                or self.right.geometry_id != self.geometry.geometry_id
                or self.left.phase_id != self.evidence.gas_phase_id
                or self.right.phase_id != self.evidence.gas_phase_id
                or self.left.boundary_id == self.right.boundary_id
                or self.left.temperature_k != self.right.temperature_k
                or len(self.phase_copy_audits) != 2 or len(self.transport_copy_audits) != 2):
            raise ValueError("Flux endpoint, phase, geometry or copy-audit identities differ")
        expected_input = _input_fingerprint(self.left, self.right, self.geometry, self.mechanism_basis,
            self.evidence, self.source_phase_sha256, self.transport_copy_audits[0].source_sha256)
        if self.input_sha256 != expected_input:
            raise ValueError("Flux input fingerprint differs from actual endpoints/geometry/evidence")
        for name in ("native_flux_kmol_m2_s", "molar_flux_mol_m2_s", "mass_flux_kg_m2_s",
                     "molecular_weights_kg_mol", "native_multi_diffusion_m2_s"):
            value = _array(getattr(self, name))
            if value.shape != ((n, n) if name == "native_multi_diffusion_m2_s" else (n,)):
                raise ValueError("Native flux/transport arrays must share the full species axes")
            object.__setattr__(self, name, value)
        if (not np.array_equal(self.molar_flux_mol_m2_s, self.native_flux_kmol_m2_s*1000.)
                or not np.array_equal(self.mass_flux_kg_m2_s, self.molar_flux_mol_m2_s*self.molecular_weights_kg_mol)
                or np.any(self.molecular_weights_kg_mol <= 0) or self.frame != FLUX_FRAME):
            raise ValueError("Flux units, molecular masses or stationary-solid orientation differ")


class MembraneTransportError(RuntimeError):
    """Keep completed raw flux, mutable native objects and original cause on failure."""

    def __init__(self, message, *, source_phase, owned_endpoint_phases, native_dusty_gas,
                 raw_native_flux, left, right, geometry, phase_copy_audits=(), transport_copy_audits=()):
        self.source_phase, self.owned_endpoint_phases = source_phase, tuple(owned_endpoint_phases)
        self.native_dusty_gas = native_dusty_gas
        self.raw_native_flux = None if raw_native_flux is None else _array(raw_native_flux, finite_only=False)
        self.left, self.right, self.geometry = left, right, geometry
        self.phase_copy_audits, self.transport_copy_audits = tuple(phase_copy_audits), tuple(transport_copy_audits)
        self.native_state = None if native_dusty_gas is None else _array(native_dusty_gas.state, finite_only=False)
        self.owned_native_states = tuple(_array(phase.state, finite_only=False) for phase in owned_endpoint_phases)
        super().__init__(message)


class CanteraDustyGasTransport:
    """Fresh actual native objects per call; no finite device or reaction integration.

    A factory may expose a shared source Solution: audited independent copies
    protect its state. Returned mutable native diagnostics are never reused.
    The source's full thermo/transport definitions must remain unchanged.
    """

    def __init__(self, phase_factory: Callable, mechanism_basis: MechanismBasis, *,
                 evidence: MembraneTransportEvidence):
        import cantera as ct

        if tuple(int(part) for part in ct.__version__.split(".")[:2]) != (3, 2):
            raise ValueError("This native DustyGas level is checked with Cantera3.2")
        if not callable(phase_factory) or mechanism_basis.minimum_temperature_k < 200:
            raise ValueError("Supply an explicit native factory and warm >=200K mechanism domain")
        self.ct, self.phase_factory = ct, phase_factory
        self.mechanism_basis, self.evidence = mechanism_basis, evidence
        self._source_definition = None

    def flux(self, left: MembraneEndpoint, right: MembraneEndpoint,
             geometry: PorousTransportGeometry) -> MembraneFlux:
        if (left.phase_id != self.evidence.gas_phase_id or right.phase_id != left.phase_id
                or left.geometry_id != geometry.geometry_id or right.geometry_id != geometry.geometry_id
                or left.boundary_id == right.boundary_id):
            raise ValueError("Declare two different boundaries with the admitted phase/geometry identities")
        if left.temperature_k != right.temperature_k:
            raise ValueError("This constitutive level requires isothermal endpoints; no thermal-diffusion closure")
        for state in (left, right):
            self.mechanism_basis.require_state(state.temperature_k, state.pressure_pa_absolute)
        source = dusty = raw_flux = None
        owned, phase_audits, transport_audits = [], [], []
        try:
            source = self.phase_factory()
            if (not isinstance(source, self.ct.Solution) or source.thermo_model != "ideal-gas"
                    or source.transport_model != "multicomponent" or source.n_reactions != 0
                    or source.n_species < 2 or source.n_selected_species != source.n_species
                    or np.any(source.charges != 0)):
                raise ValueError("Supply a full neutral frozen native ideal-gas multicomponent phase with >=2 species")
            names = tuple(source.species_names)
            if left.species != names or right.species != names:
                raise ValueError("Endpoint species order must exactly match the full native phase")
            if not source.min_temp <= left.temperature_k <= source.max_temp:
                raise ValueError("Endpoint temperature exceeds native species fit intersection")
            original_state, original_basis = source.state.copy(), source.basis
            source_fp = _phase_fingerprint(source, include_reactions=True)
            source_transport = _hash(_transport_data(source))
            definition = (source_fp, source_transport)
            if self._source_definition is not None and definition != self._source_definition:
                raise ValueError("Native gas/transport definition changed without rebinding source evidence")
            for endpoint in (left, right):
                copy, audit = _private_native_phase(source, self.ct)
                owned.append(copy)
                phase_audits.append(audit)
                transport_audits.append(_transport_copy_audit(source, copy))
                if endpoint.composition_basis == "mole":
                    copy.TPX = endpoint.temperature_k, endpoint.pressure_pa_absolute, endpoint.fractions
                    actual = copy.X
                else:
                    copy.TPY = endpoint.temperature_k, endpoint.pressure_pa_absolute, endpoint.fractions
                    actual = copy.Y
                if (copy.phase_of_matter != "gas" or not np.allclose(actual, endpoint.fractions,
                        rtol=COMPOSITION_ROUNDOFF, atol=COMPOSITION_ROUNDOFF)):
                    raise ValueError("Native gas state changed endpoint composition beyond declared roundoff")
            dusty = self.ct.DustyGas(thermo="ideal-gas", species=owned[0].species())
            if (_phase_fingerprint(dusty) != _phase_fingerprint(owned[0])
                    or tuple(dusty.species_names) != names or dusty.transport_model != "DustyGas"):
                raise ValueError("Native DustyGas construction changed gas species/thermo definitions")
            # All pore values are explicitly set. Native properties are write-only;
            # this object is private until return and never reused by the adapter.
            dusty.porosity = geometry.porosity
            dusty.tortuosity = geometry.tortuosity
            dusty.mean_pore_radius = geometry.mean_pore_radius_m
            dusty.permeability = geometry.permeability_m2
            a, b = (_snapshot(phase) for phase in owned)
            raw_flux = dusty.molar_fluxes(a.temperature_k, b.temperature_k, a.density_kg_m3,
                b.density_kg_m3, a.mass_fractions, b.mass_fractions, geometry.thickness_m)
            molar = np.asarray(raw_flux)*1000.
            molecular_weights = dusty.molecular_weights/1000.
            mean = _snapshot(dusty)
            matrix = dusty.multi_diff_coeffs
            if (not np.array_equal(source.state, original_state) or source.basis != original_basis
                    or _phase_fingerprint(source, include_reactions=True) != source_fp
                    or _hash(_transport_data(source)) != source_transport):
                raise ValueError("Source phase state or definition changed during native transport")
            for phase, audit, fit_audit in zip(owned, phase_audits, transport_audits, strict=True):
                if (_phase_fingerprint(phase, include_reactions=True) != audit.owned_fingerprint
                        or _hash(_transport_data(phase)) != fit_audit.owned_sha256):
                    raise ValueError("Owned native phase/transport definition changed during transport")
            inputs = _input_fingerprint(left, right, geometry, self.mechanism_basis,
                                        self.evidence, source_fp, source_transport)
            result = MembraneFlux(left, right, geometry, self.mechanism_basis, self.evidence, names,
                a, b, mean, raw_flux, molar, molar*molecular_weights, molecular_weights, matrix,
                source, tuple(owned), dusty, tuple(phase_audits), tuple(transport_audits),
                source_fp, _phase_fingerprint(owned[0]), inputs)
            self._source_definition = definition
            return result
        except Exception as error:
            raise MembraneTransportError(f"Native porous-gas transport failed: {error}",
                source_phase=source, owned_endpoint_phases=owned, native_dusty_gas=dusty,
                raw_native_flux=raw_flux, left=left, right=right, geometry=geometry,
                phase_copy_audits=phase_audits, transport_copy_audits=transport_audits) from error
