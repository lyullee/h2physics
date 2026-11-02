"""Pressure-derived DataverseNO jet summaries to an existing finite H2 source."""

from dataclasses import dataclass, field

import numpy as np

from ..core import Origin, ThermoState, finite
from ..data.ignited_hydrogen_jet import IgnitedHydrogenJetMatrix, IgnitedJetExperiment
from ..release import SourceLocation
from ..sources import IntervalMassSource

_PENDING: set[object] = set()


def _expected(matrix, experiment, source, start_s, clock_id, flow_evidence_id,
              clock_evidence_id):
    row = matrix.experiment(experiment.experiment_number)
    duration = finite(row.hydrogen_release_time_s, "source release duration", positive=True)
    rate = finite(row.pressure_derived_average_mass_flow_kg_s,
                  "source pressure-derived average mass flow")
    if rate < 0.:
        raise ValueError("Source average mass flow must be nonnegative")
    mass = rate * duration
    if not np.isfinite(mass):
        raise ValueError("Pressure-derived finite release mass overflowed")
    return (row, duration, rate, mass)


@dataclass(frozen=True, slots=True)
class IgnitedJetFiniteSourceProjection:
    matrix: IgnitedHydrogenJetMatrix
    experiment: IgnitedJetExperiment
    source: IntervalMassSource
    start_s: float
    clock_id: str
    flow_acceptance_evidence_id: str
    clock_mapping_evidence_id: str
    source_matrix_sha256: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue pressure-derived jet projections only through the source adapter")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "_seal", self._current())

    def _current(self):
        return (id(self.matrix), id(self.experiment), id(self.source), self.start_s,
                self.clock_id, self.flow_acceptance_evidence_id,
                self.clock_mapping_evidence_id, self.source_matrix_sha256,
                self.source.evidence_id, self.source.location, self.source.state,
                self.source.edges_s.tobytes(), self.source.mass_kg.tobytes())

    def require_current(self):
        self.matrix.require_current()
        self.source.require_current()
        if self._current() != self._seal:
            raise ValueError("Jet finite-source projection lost source/model boundary evidence")
        if (self.source_matrix_sha256 != self.matrix.source_sha256
                or self.experiment is not self.matrix.experiment(self.experiment.experiment_number)):
            raise ValueError("Jet projection no longer refers to its exact pinned matrix row")
        row, duration, rate, mass = _expected(self.matrix, self.experiment,
            self.source, self.start_s, self.clock_id,
            self.flow_acceptance_evidence_id, self.clock_mapping_evidence_id)
        if (self.source.origin is not Origin.RECONSTRUCTED
                or self.source.location.clock_id != self.clock_id
                or tuple(float(x) for x in self.source.edges_s) !=
                   (self.start_s, self.start_s + duration)
                or tuple(float(x) for x in self.source.mass_kg) != (mass,)
                or not self.source.evidence_id.endswith(row.source_row_id)):
            raise ValueError("Finite source no longer reproduces from its matrix row")
        return self


def project_ignited_jet_average_source(matrix: IgnitedHydrogenJetMatrix,
        experiment_number: int, *, location: SourceLocation, state: ThermoState,
        start_s: float, clock_id: str, flow_acceptance_evidence_id: str,
        clock_mapping_evidence_id: str) -> IgnitedJetFiniteSourceProjection:
    """Project one source-row average flow and stated duration as one finite bin.

    The publisher explicitly says MFR is calculated from experimental pressure;
    this adapter uses the source's average MFR unchanged and performs no pressure
    conversion. The one-bin constant-mean representation is a caller-evidenced
    finite-source approximation, not the missing time history or measured peak.
    """
    if type(matrix) is not IgnitedHydrogenJetMatrix:
        raise TypeError("Supply the pinned DataverseNO source matrix")
    if type(location) is not SourceLocation or type(state) is not ThermoState:
        raise TypeError("Supply an explicit H2 source location and representative state")
    for name, value in (("flow acceptance", flow_acceptance_evidence_id),
                        ("clock mapping", clock_mapping_evidence_id),
                        ("clock identity", clock_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Explicit {name} evidence is required")
    if location.clock_id != clock_id.strip():
        raise ValueError("Finite-source clock must match the caller-owned source location clock")
    if (not isinstance(state.basis.fluid, str)
            or state.basis.fluid.strip().casefold() not in {"h2", "hydrogen"}
            or state.phase not in {"gas", "supercritical_gas", "supercritical"}
            or state.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Finite-source state must explicitly represent gaseous pure H2")
    start = finite(start_s, "source start time")
    matrix.require_current()
    row = matrix.experiment(experiment_number)
    duration = finite(row.hydrogen_release_time_s, "source release duration", positive=True)
    rate = finite(row.pressure_derived_average_mass_flow_kg_s,
                  "source pressure-derived average mass flow")
    if rate < 0.:
        raise ValueError("Source average mass flow must be nonnegative")
    mass = rate * duration
    evidence = (f"DataverseNO:{matrix.source_doi}:sha256:{matrix.source_sha256}:"
                f"experiment:{row.source_row_id}:mean-source-window:"
                f"{flow_acceptance_evidence_id.strip()}:clock-map:{clock_mapping_evidence_id.strip()}")
    finite_source = IntervalMassSource(location, np.asarray([start, start + duration]),
        np.asarray([mass]), state, Origin.RECONSTRUCTED, evidence, "window_end")
    token = object()
    _PENDING.add(token)
    try:
        result = IgnitedJetFiniteSourceProjection(matrix, row, finite_source, start,
            clock_id.strip(), flow_acceptance_evidence_id.strip(),
            clock_mapping_evidence_id.strip(), matrix.source_sha256, _issuer=token)
        return result.require_current()
    except Exception:
        _PENDING.discard(token)
        raise
