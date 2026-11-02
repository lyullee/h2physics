"""Audit externally integrated, phase-resolved mixture-vessel histories.

This module does not flash a changing inventory or advance a vessel. It checks
accepted records supplied by an owning native solver against retained native
equilibrium packets and cumulative boundary ledgers.
"""

from dataclasses import dataclass, field
from math import fsum

from ..core import finite
from ..thermo.mixture_phase_partition import MixtureInventoryStateAdmission

_PENDING_HISTORY_AUDITS = set()


def _issue_audit(**values):
    token = object()
    _PENDING_HISTORY_AUDITS.add(token)
    try:
        return MixtureSeparatorHistoryAudit(**values, _issuer=token)
    except Exception:
        _PENDING_HISTORY_AUDITS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class MixtureSeparatorAcceptedPoint:
    """One owner-accepted equilibrium state and cumulative boundary receipt.

    Cumulative species counters use the provider species order in mol. The
    energy counter is net cumulative energy transferred into the vessel in J,
    on the exact energy-reference basis carried by the admitted CoolProp state.
    It must include stream enthalpy, heat and shaft/electrical work as applicable.
    """

    time_s: float
    inventory: MixtureInventoryStateAdmission
    cumulative_inlet_component_moles: tuple[float, ...]
    cumulative_outlet_component_moles: tuple[float, ...]
    cumulative_net_energy_into_vessel_j: float

    def __post_init__(self):
        time_s = finite(self.time_s, "accepted time")
        if type(self.inventory) is not MixtureInventoryStateAdmission:
            raise TypeError("Each accepted point requires the native-packet inventory admission")
        self.inventory.require_current()
        n = len(self.inventory.provider.species)
        inlet = tuple(finite(v, "cumulative inlet component moles")
                      for v in self.cumulative_inlet_component_moles)
        outlet = tuple(finite(v, "cumulative outlet component moles")
                       for v in self.cumulative_outlet_component_moles)
        if len(inlet) != n or len(outlet) != n or any(v < 0. for v in (*inlet, *outlet)):
            raise ValueError("Cumulative inlet/outlet vectors must be nonnegative and follow native species order")
        energy = finite(self.cumulative_net_energy_into_vessel_j,
                        "cumulative net energy into vessel")
        object.__setattr__(self, "time_s", time_s)
        object.__setattr__(self, "cumulative_inlet_component_moles", inlet)
        object.__setattr__(self, "cumulative_outlet_component_moles", outlet)
        object.__setattr__(self, "cumulative_net_energy_into_vessel_j", energy)


@dataclass(frozen=True, slots=True)
class MixtureSeparatorHistoryRow:
    time_s: float
    component_mole_residuals: tuple[float, ...]
    internal_energy_residual_j: float
    pressure_pa: float
    temperature_k: float
    phase: str


@dataclass(frozen=True, slots=True)
class MixtureSeparatorHistoryAudit:
    """Audited balance summaries, not an integration or physical prediction."""

    native_run_id: str
    native_owner_evidence_id: str
    species: tuple[str, ...]
    rows: tuple[MixtureSeparatorHistoryRow, ...]
    accepted_points: tuple[MixtureSeparatorAcceptedPoint, ...] = field(repr=False, compare=False)
    maximum_component_mole_residuals: tuple[float, ...]
    maximum_absolute_energy_residual_j: float
    component_mole_absolute_tolerance: float
    energy_absolute_tolerance_j: float
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_HISTORY_AUDITS:
            raise TypeError("History audits are issued only after all accepted rows pass closure")
        _PENDING_HISTORY_AUDITS.remove(self._issuer)
        if (not self.rows or any(type(row) is not MixtureSeparatorHistoryRow for row in self.rows)
                or len(self.rows) != len(self.accepted_points)
                or any(type(point) is not MixtureSeparatorAcceptedPoint for point in self.accepted_points)):
            raise TypeError("Retain the exact typed accepted points and corresponding audit rows")
        species = tuple(self.species)
        maxima = tuple(finite(v, "maximum component residual")
                       for v in self.maximum_component_mole_residuals)
        if len(species) == 0 or len(set(species)) != len(species) or len(maxima) != len(species):
            raise ValueError("Retain unique species labels and one maximum per species")
        for key in ("native_run_id", "native_owner_evidence_id"):
            value = getattr(self, key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Declare native run identity and owner evidence")
        object.__setattr__(self, "species", species)
        object.__setattr__(self, "rows", tuple(self.rows))
        object.__setattr__(self, "maximum_component_mole_residuals", maxima)
        object.__setattr__(self, "maximum_absolute_energy_residual_j",
                           finite(self.maximum_absolute_energy_residual_j, "maximum energy residual"))
        object.__setattr__(self, "component_mole_absolute_tolerance",
                           finite(self.component_mole_absolute_tolerance, "component mole tolerance", positive=True))
        object.__setattr__(self, "energy_absolute_tolerance_j",
                           finite(self.energy_absolute_tolerance_j, "energy tolerance", positive=True))
        object.__setattr__(self, "accepted_points", tuple(self.accepted_points))
        species_check, rows_check, maxima_check, energy_check = _summarize_history(
            self.accepted_points, self.component_mole_absolute_tolerance,
            self.energy_absolute_tolerance_j)
        if (species_check != species or rows_check != self.rows
                or maxima_check != maxima
                or energy_check != self.maximum_absolute_energy_residual_j):
            raise ValueError("Audit summary does not reproduce its retained native accepted points")
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (self.native_run_id, self.native_owner_evidence_id, self.species,
                tuple(self.rows), self.maximum_component_mole_residuals,
                self.maximum_absolute_energy_residual_j,
                self.component_mole_absolute_tolerance, self.energy_absolute_tolerance_j,
                tuple(_accepted_point_signature(point) for point in self.accepted_points))

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Mixture separator history audit changed after issuance")
        species, rows, maxima, energy = _summarize_history(
            self.accepted_points, self.component_mole_absolute_tolerance,
            self.energy_absolute_tolerance_j)
        if (species != self.species or rows != self.rows
                or maxima != self.maximum_component_mole_residuals
                or energy != self.maximum_absolute_energy_residual_j):
            raise ValueError("Retained mixture separator source no longer reproduces its issued audit")
        return self


def _accepted_point_signature(point):
    admission = point.inventory
    admission.require_current()
    return (id(point), point.time_s, id(admission), id(admission.provider),
            id(admission.partition), admission._payload(),
            point.cumulative_inlet_component_moles,
            point.cumulative_outlet_component_moles,
            point.cumulative_net_energy_into_vessel_j)


def _summarize_history(points, mass_tol, energy_tol):
    rows_in = tuple(points)
    if len(rows_in) < 2 or any(type(p) is not MixtureSeparatorAcceptedPoint for p in rows_in):
        raise ValueError("Supply at least an initial and final exact-time native accepted point")
    first = rows_in[0]
    first.inventory.require_current()
    provider0 = first.inventory.provider
    species = tuple(provider0.species)
    molar_masses = tuple(provider0.coolprop_molar_masses_kg_mol)
    basis = first.inventory.partition.state.basis
    volume = first.inventory.vessel_volume_m3
    n = len(species)
    if first.time_s != 0.:
        raise ValueError("The first accepted row must be the declared zero-time initial inventory")
    if (first.cumulative_inlet_component_moles != (0.,)*n
            or first.cumulative_outlet_component_moles != (0.,)*n
            or first.cumulative_net_energy_into_vessel_j != 0.):
        raise ValueError("Initial cumulative boundary ledgers must be exactly zero")

    previous = first
    maxima = [0.]*n
    audited = []
    for index, point in enumerate(rows_in):
        if index and point.time_s <= previous.time_s:
            raise ValueError("Native accepted times must be strictly increasing")
        admission = point.inventory
        admission.require_current()
        provider = admission.provider
        state = admission.partition.state
        if (tuple(provider.species) != species
                or tuple(provider.coolprop_molar_masses_kg_mol) != molar_masses):
            raise ValueError("Changing mixture packets must retain the same native species order and molar-mass basis")
        basis.require_compatible(state.basis)
        if admission.vessel_volume_m3 != volume:
            raise ValueError("Vessel volume changed across fixed-volume accepted records")
        if state.phase not in {"liquid", "gas", "two_phase", "supercritical",
                               "supercritical_gas", "supercritical_liquid", "critical_point"}:
            raise ValueError("Native flash must identify a recognized CoolProp phase")
        finite(state.pressure_pa, "accepted native pressure", positive=True)
        finite(state.temperature_k, "accepted native temperature", positive=True)
        if (admission.partition.liquid_density_kg_m3 is None
                and fsum(admission.phase_amounts.liquid_component_mass_kg) > 0.
                or admission.partition.vapor_density_kg_m3 is None
                and fsum(admission.phase_amounts.vapor_component_mass_kg) > 0.):
            raise ValueError("Accepted flash must retain pressure, temperature and properties for each occupied phase")
        if len(point.cumulative_inlet_component_moles) != n:
            raise ValueError("Accepted port ledger lacks one entry per native species")
        for current, prior in zip(point.cumulative_inlet_component_moles,
                                  previous.cumulative_inlet_component_moles, strict=True):
            if current < prior:
                raise ValueError("Cumulative inlet species moles cannot decrease")
        for current, prior in zip(point.cumulative_outlet_component_moles,
                                  previous.cumulative_outlet_component_moles, strict=True):
            if current < prior:
                raise ValueError("Cumulative outlet species moles cannot decrease")
        residuals = tuple(n_i - n0 - in_i + out_i for n_i, n0, in_i, out_i in zip(
            admission.total_component_moles, first.inventory.total_component_moles,
            point.cumulative_inlet_component_moles, point.cumulative_outlet_component_moles,
            strict=True))
        residual_u = fsum((admission.target_internal_energy_j,
                           -first.inventory.target_internal_energy_j,
                           -point.cumulative_net_energy_into_vessel_j))
        for j, residual in enumerate(residuals):
            maxima[j] = max(maxima[j], abs(residual))
        row = MixtureSeparatorHistoryRow(point.time_s, residuals, residual_u,
                                         state.pressure_pa, state.temperature_k, state.phase)
        if any(abs(value) > mass_tol for value in residuals):
            raise ValueError(f"Component inventory closure failed at accepted index {index}")
        if abs(residual_u) > energy_tol:
            raise ValueError(f"Internal-energy closure failed at accepted index {index}")
        audited.append(row)
        previous = point
    return (species, tuple(audited), tuple(maxima),
            max(abs(row.internal_energy_residual_j) for row in audited))


def audit_mixture_separator_history(points, *, native_run_id, native_owner_evidence_id,
        component_mole_absolute_tolerance, energy_absolute_tolerance_j):
    """Check a native owner's exact-time accepted inventory and cumulative ledgers.

    Each inventory is admitted independently by an actual CoolProp mixture
    provider and its provider-issued phase partition. Different provider
    composition snapshots are allowed so long as species order, molar masses,
    and property basis remain identical. This function does not create accepted
    records, solve a time step, localize phase events, or establish that the
    claimed native owner really integrated them; the caller must preserve that
    original-run evidence separately.
    """
    rows_in = tuple(points)
    mass_tol = finite(component_mole_absolute_tolerance,
                      "component mole absolute tolerance", positive=True)
    energy_tol = finite(energy_absolute_tolerance_j,
                        "energy absolute tolerance", positive=True)
    if not isinstance(native_run_id, str) or not native_run_id.strip():
        raise ValueError("Declare the original native run identity")
    if not isinstance(native_owner_evidence_id, str) or not native_owner_evidence_id.strip():
        raise ValueError("Declare evidence identifying the native integration owner")
    species, audited, maxima, energy_residual = _summarize_history(rows_in, mass_tol, energy_tol)
    return _issue_audit(native_run_id=native_run_id,
        native_owner_evidence_id=native_owner_evidence_id, species=species,
        rows=audited, accepted_points=rows_in,
        maximum_component_mole_residuals=maxima,
        maximum_absolute_energy_residual_j=energy_residual,
        component_mole_absolute_tolerance=mass_tol,
        energy_absolute_tolerance_j=energy_tol)


__all__ = ["MixtureSeparatorAcceptedPoint", "MixtureSeparatorHistoryRow",
           "MixtureSeparatorHistoryAudit", "audit_mixture_separator_history"]
