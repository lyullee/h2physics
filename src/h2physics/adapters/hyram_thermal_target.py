"""Compose accepted HyRAM irradiance with the existing lumped thermal target."""

from dataclasses import dataclass, field, replace

from .hyram_exposure import ExposureHistory, incident_history_from_hyram_radiation
from .result_provenance import recorded_content_sha256
from .thermal_target import IncidentHeatHistory, incident_history_from_exposure


@dataclass(frozen=True, slots=True)
class HyRAMThermalSourceGuard:
    radiation: object = field(repr=False, compare=False)
    observer_index: int
    start_s: float
    end_s: float
    receptor_id: str
    basis_id: str
    surface_mapping_evidence_id: str
    irradiance_projection_evidence_id: str
    history_mapping_evidence_id: str
    exposure_sha256: str
    _radiation_identity: int = field(init=False, repr=False, compare=False)
    _evidence_seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        evidence = (self.surface_mapping_evidence_id,
                    self.irradiance_projection_evidence_id,
                    self.history_mapping_evidence_id)
        if any(not isinstance(value, str) or not value.strip() for value in evidence):
            raise ValueError("HyRAM target source guard requires all three evidence identities")
        object.__setattr__(self, "_radiation_identity", id(self.radiation))
        object.__setattr__(self, "_evidence_seal", self._signature())

    def _signature(self):
        return recorded_content_sha256((
            id(self.radiation), self.observer_index, self.start_s, self.end_s,
            self.receptor_id, self.basis_id, self.surface_mapping_evidence_id,
            self.irradiance_projection_evidence_id, self.history_mapping_evidence_id,
            self.exposure_sha256,
        ))

    def require_current(self):
        if (id(self.radiation) != self._radiation_identity
                or self._signature() != self._evidence_seal):
            raise ValueError("HyRAM source identity or target-mapping evidence changed")
        current = incident_history_from_hyram_radiation(
            self.radiation, observer_index=self.observer_index,
            start_s=self.start_s, end_s=self.end_s,
            receptor_id=self.receptor_id, basis_id=self.basis_id,
        )
        if current.content_sha256 != self.exposure_sha256:
            raise ValueError("Accepted HyRAM observer field or exposure window changed")
        return self


@dataclass(frozen=True, slots=True)
class HyRAMIncidentHeatBinding:
    exposure: ExposureHistory = field(repr=False, compare=False)
    history: IncidentHeatHistory
    source_guard: HyRAMThermalSourceGuard = field(repr=False, compare=False)
    _seal: str = field(default="", repr=False, compare=False)

    def require_current(self):
        self.source_guard.require_current()
        if (self.history.source_owner is not self.source_guard
                or self.exposure.content_sha256 != self.source_guard.exposure_sha256
                or recorded_content_sha256((self.exposure, self.history)) != self._seal
                or self.history.evidence_id != self.source_guard.history_mapping_evidence_id.strip()
                or not self.source_guard.surface_mapping_evidence_id.strip()
                or not self.source_guard.irradiance_projection_evidence_id.strip()
                or not self.source_guard.history_mapping_evidence_id.strip()
                or self.history.edges_s.tolist() != self.exposure.time_s.tolist()
                or self.history.incident_flux_w_m2.tolist() != self.exposure.values.tolist()
                or self.history.clock_id != self.exposure.clock_id
                or self.history.frame_id != self.exposure.receptor.frame_id
                or self.history.source_id != self.exposure.source_id):
            raise ValueError("HyRAM-to-thermal incident history lost its accepted source mapping")
        return self


def incident_heat_history_from_hyram_radiation(
    radiation,
    *,
    observer_index: int,
    start_s: float,
    end_s: float,
    receptor_id: str,
    basis_id: str,
    surface_mapping_evidence_id: str,
    irradiance_projection_evidence_id: str,
    history_mapping_evidence_id: str,
) -> HyRAMIncidentHeatBinding:
    """Bind one accepted HyRAM point to an existing finite thermal target.

    The HyRAM output is scalar incident irradiance on a steady interval. The
    caller declares that its selected observer represents the target surface
    and supplies the projection basis. This function does not calculate a view
    factor, target normal, absorptivity, transient fire, or target properties.
    """
    evidence = (surface_mapping_evidence_id, irradiance_projection_evidence_id,
                history_mapping_evidence_id)
    if any(not isinstance(value, str) or not value.strip() for value in evidence):
        raise ValueError("Declare observer-to-surface, irradiance-projection and history mapping evidence")
    exposure = incident_history_from_hyram_radiation(
        radiation, observer_index=observer_index, start_s=start_s, end_s=end_s,
        receptor_id=receptor_id, basis_id=basis_id,
    )
    if exposure.quantity != "incident_radiant_flux" or exposure.unit != "W/m2":
        raise ValueError("Lumped thermal target requires incident irradiance in W/m2")
    history = incident_history_from_exposure(
        exposure, evidence_id=history_mapping_evidence_id.strip(),
    )
    guard = HyRAMThermalSourceGuard(
        radiation, observer_index, start_s, end_s, receptor_id, basis_id,
        surface_mapping_evidence_id.strip(), irradiance_projection_evidence_id.strip(),
        history_mapping_evidence_id.strip(), exposure.content_sha256,
    )
    history = replace(history, source_owner=guard)
    binding = HyRAMIncidentHeatBinding(
        exposure, history, guard, recorded_content_sha256((exposure, history)),
    )
    return binding.require_current()


__all__ = ["HyRAMThermalSourceGuard", "HyRAMIncidentHeatBinding",
           "incident_heat_history_from_hyram_radiation"]
