"""Link an accepted HyRAM gas source/dispersion receipt to ignition-risk branches.

This is a lineage and source-rate consistency bridge. It computes no dispersion,
ignition probability, frequency, harm, or risk metric.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..core import Origin, finite
from ..dispersion import HydrogenReleaseFamily, preferred_dispersion_provider
from .facility_accident_chain import FacilityDispersionHandoff


class IgnitionRiskBinding(Protocol):
    """Structural input contract implemented by the native risk receipt.

    A synthetic implementation is suitable for a contract fixture only and
    cannot authenticate execution of an external risk engine.
    """

    release_rate_kg_s: float
    lineage_sha256: str
    origin: Origin
    request: Any
    frequency: Any

    def require_current(self): ...


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {label}")
    return value.strip()


@dataclass(frozen=True, slots=True)
class PreferredDispersionRiskLedger:
    """Exact source, accepted HyRAM execution and native conditional-risk receipt."""

    facility_handoff: FacilityDispersionHandoff = field(repr=False, compare=False)
    ignition_risk: IgnitionRiskBinding = field(repr=False, compare=False)
    linkage_evidence_id: str
    release_rate_absolute_tolerance_kg_s: float
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.facility_handoff) is not FacilityDispersionHandoff:
            raise TypeError("Retain an admitted finite-source/preferred-dispersion handoff")
        if not _is_ignition_risk_binding(self.ignition_risk):
            raise TypeError("Retain a typed HyRAM ignition-risk branch binding")
        evidence = _text(self.linkage_evidence_id, "source-to-risk linkage evidence")
        tolerance = float(self.release_rate_absolute_tolerance_kg_s)
        if not math.isfinite(tolerance) or tolerance < 0.0:
            raise ValueError("Release-rate linkage tolerance must be finite and nonnegative")
        object.__setattr__(self, "linkage_evidence_id", evidence)
        object.__setattr__(self, "release_rate_absolute_tolerance_kg_s", tolerance)
        self._validate()
        object.__setattr__(self, "_seal", self._content())

    def _validate(self):
        handoff, risk = self.facility_handoff, self.ignition_risk
        handoff.require_current()
        risk.require_current()
        if risk.request.frequency is not risk.frequency:
            raise ValueError("Risk request must retain its exact caller-owned frequency object")
        if (not isinstance(risk.lineage_sha256, str) or len(risk.lineage_sha256) != 64
                or any(c not in "0123456789abcdef" for c in risk.lineage_sha256)):
            raise ValueError("Risk receipt must retain a lowercase SHA-256 lineage identity")
        if not isinstance(risk.origin, Origin):
            raise TypeError("Risk receipt must preserve its explicit evidence origin")
        finite(risk.release_rate_kg_s, "HyRAM ignition release rate", positive=True)
        if handoff.family is not HydrogenReleaseFamily.HIGH_PRESSURE_GAS:
            raise ValueError("HyRAM ignition-risk linkage is scoped to the preferred high-pressure-gas route")
        if handoff.execution.provider_id != preferred_dispersion_provider(handoff.family):
            raise ValueError("Dispersion provider does not match the selected gas family")
        projection = handoff.gas_source_projection
        if projection is None or projection.accepted is not True:
            raise ValueError("An admitted HyRAM finite-source projection is required")
        if (projection.jet is not handoff.execution.result
                or projection.source.location != handoff.finite_source.source.location):
            raise ValueError("Risk source and accepted HyRAM dispersion execution have different lineage")
        if (projection.jet.mass_flow_kg_s <= 0.0
                or abs(risk.release_rate_kg_s - projection.jet.mass_flow_kg_s)
                > self.release_rate_absolute_tolerance_kg_s):
            raise ValueError("HyRAM ignition-table rate differs from the exact admitted HyRAM jet rate")
        return self

    def _content(self):
        return (
            id(self.facility_handoff), id(self.ignition_risk), self.linkage_evidence_id,
            id(self.facility_handoff.execution), id(self.facility_handoff.execution.result),
            self.facility_handoff.family, self.facility_handoff.execution.provider_id,
            self.facility_handoff.finite_source.source.evidence_id,
            self.ignition_risk.lineage_sha256, self.ignition_risk.release_rate_kg_s,
            self.release_rate_absolute_tolerance_kg_s,
            self.facility_handoff.finite_source.source.origin, self.ignition_risk.origin,
            id(self.ignition_risk.frequency), id(self.ignition_risk.request),
        )

    def require_current(self):
        self._validate()
        if self._content() != self._seal:
            raise ValueError("Preferred dispersion/risk lineage changed after binding")
        return self


def bind_preferred_dispersion_risk_ledger(
    facility_handoff: FacilityDispersionHandoff,
    ignition_risk: IgnitionRiskBinding,
    *,
    linkage_evidence_id: str,
    release_rate_absolute_tolerance_kg_s: float,
) -> PreferredDispersionRiskLedger:
    """Issue a source-rate-checked ledger without running any provider or risk solver."""
    return PreferredDispersionRiskLedger(
        facility_handoff, ignition_risk, linkage_evidence_id,
        release_rate_absolute_tolerance_kg_s,
    ).require_current()


__all__ = [
    "IgnitionRiskBinding",
    "PreferredDispersionRiskLedger",
    "bind_preferred_dispersion_risk_ledger",
]


def _is_ignition_risk_binding(value):
    required = ("release_rate_kg_s", "lineage_sha256", "origin", "request", "frequency")
    return all(hasattr(value, name) for name in required) and callable(
        getattr(value, "require_current", None)
    )
