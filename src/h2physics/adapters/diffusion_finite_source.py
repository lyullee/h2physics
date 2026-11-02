"""Finite H2 source projection from an owner-issued slab diffusion result."""

from dataclasses import dataclass, field
from hashlib import sha256
from math import isclose

import numpy as np

from ..core import Origin, ThermoState, finite
from ..materials.transport import DiffusionResult
from ..release import SourceLocation
from ..sources import IntervalMassSource

_PENDING_DIFFUSION_SOURCE: set[object] = set()


def _signature(trace, source, area_m2, recombination_evidence_id,
               clock_alignment_evidence_id, state_projection_evidence_id):
    return sha256(repr((id(trace), trace._fingerprint, id(source), source._fingerprint,
        area_m2, recombination_evidence_id, clock_alignment_evidence_id,
        state_projection_evidence_id)).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class DiffusionFiniteSourceHandoff:
    diffusion: DiffusionResult
    source: IntervalMassSource
    area_m2: float
    clock_alignment_evidence_id: str
    state_projection_evidence_id: str
    recombination_evidence_id: str | None
    _issuer: object = field(default=None, repr=False, compare=False)
    _issued: object = field(default=None, init=False, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_DIFFUSION_SOURCE:
            raise TypeError("Create diffusion source receipts through the typed adapter")
        _PENDING_DIFFUSION_SOURCE.remove(self._issuer)
        object.__setattr__(self, "_issued", self._issuer)
        object.__setattr__(self, "_seal", self._signature())

    def _signature(self):
        return _signature(self.diffusion, self.source, self.area_m2,
            self.recombination_evidence_id, self.clock_alignment_evidence_id,
            self.state_projection_evidence_id)

    def require_current(self):
        if self._issuer is not self._issued or type(self.diffusion) is not DiffusionResult:
            raise ValueError("Diffusion source receipt lost the original solver result")
        self.diffusion.require_current()
        self.source.require_current()
        carrier = self.diffusion.carrier
        entity_out = np.diff(self.diffusion.right_integrated_flux_mol_m2)
        expected_mass = entity_out*self.area_m2*carrier.molar_mass_kg_mol
        if (not np.all(np.isfinite(expected_mass)) or np.any(expected_mass < 0.)
                or not np.array_equal(self.source.edges_s, self.diffusion.time_s)
                or not np.array_equal(self.source.mass_kg, expected_mass)
                or self.source.state.basis.fluid not in {"H2", "Hydrogen"}
                or self.source.state.phase not in {"gas", "supercritical_gas"}
                or self._signature() != self._seal):
            raise ValueError("Diffusion flux, source state, area or handoff changed")
        return self


def source_from_diffusion_result(trace: DiffusionResult, *, surface_area_m2: float,
        location: SourceLocation, clock_alignment_evidence_id: str,
        state_projection_evidence_id: str, source_evidence_id: str,
        gas_state: ThermoState, origin: Origin,
        h2_molar_mass_kg_mol: float = 0.00201588,
        recombination_evidence_id: str | None = None):
    """Convert outward integrated slab flux into finite H2 mass bins.

    The area converts the model's molar-per-area boundary ledger to total mass.
    Molecular-H2 carrier flux maps directly. Atomic-H carrier flux requires
    explicit evidence that exiting atoms form an H2 gas product. This is only
    a material-source projection: diffusion results contain no product
    temperature, pressure or energy ledger, so gas-state projection is explicit.
    """
    if type(trace) is not DiffusionResult:
        raise TypeError("Supply the original owner-issued DiffusionResult")
    trace.require_current()
    if type(location) is not SourceLocation or type(gas_state) is not ThermoState:
        raise TypeError("Supply a source location and thermodynamic gas state")
    area = finite(surface_area_m2, "surface_area_m2", positive=True)
    if location.clock_id == "" or not np.isfinite(trace.time_s).all():
        raise ValueError("Map the diffusion sample clock to an explicit physical source clock")
    for label, value in (("clock alignment", clock_alignment_evidence_id),
                         ("state projection", state_projection_evidence_id),
                         ("source", source_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {label} evidence")
    if (gas_state.basis.fluid not in {"H2", "Hydrogen"}
            or gas_state.phase not in {"gas", "supercritical_gas"}
            or gas_state.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("The receiver state must describe single-phase gaseous H2")
    h2_molar_mass = finite(h2_molar_mass_kg_mol, "H2 molar mass", positive=True)
    carrier = trace.carrier
    expected_entity_mass = (h2_molar_mass if carrier.identity == "molecular_hydrogen"
                            else h2_molar_mass/2.)
    if not isclose(carrier.molar_mass_kg_mol, expected_entity_mass,
                   rel_tol=1e-4, abs_tol=0.):
        raise ValueError("Diffusing entity molar mass is incompatible with the declared H2 product")
    if carrier.identity == "atomic_hydrogen":
        if not isinstance(recombination_evidence_id, str) or not recombination_evidence_id.strip():
            raise ValueError("Atomic-H permeation requires evidence for recombination to H2")
    elif recombination_evidence_id is not None:
        raise ValueError("Do not attach atomic recombination evidence to molecular-H2 transport")
    times = np.asarray(trace.time_s, dtype=float)
    cumulative = np.asarray(trace.right_integrated_flux_mol_m2, dtype=float)
    intervals = np.diff(cumulative)
    if (times.ndim != 1 or len(times) < 2 or intervals.shape != (len(times)-1,)
            or np.any(np.diff(times) <= 0.) or np.any(~np.isfinite(intervals))
            or np.any(intervals < 0.)):
        raise ValueError("Finite source conversion requires nonnegative outward flux in every interval")
    mass = intervals*area*carrier.molar_mass_kg_mol
    if not np.isfinite(mass).all() or mass.sum() <= 0.:
        raise ValueError("Outward transport must deliver positive finite H2 mass")
    origin = Origin(origin)
    if origin == Origin.UNRESOLVED:
        raise ValueError("Resolve the projected H2 source origin")
    evidence = ":".join((source_evidence_id.strip(), clock_alignment_evidence_id.strip(),
        state_projection_evidence_id.strip(),
        "" if recombination_evidence_id is None else recombination_evidence_id.strip()))
    source = IntervalMassSource(location, times, mass, gas_state, origin,
        evidence, "window_end")
    token = object()
    _PENDING_DIFFUSION_SOURCE.add(token)
    try:
        handoff = DiffusionFiniteSourceHandoff(trace, source, area,
            clock_alignment_evidence_id.strip(), state_projection_evidence_id.strip(),
            None if recombination_evidence_id is None else recombination_evidence_id.strip(),
            token)
    except Exception:
        _PENDING_DIFFUSION_SOURCE.discard(token)
        raise
    return handoff.require_current()
