"""Exact-coordinate sampler for caller-exported preferred-provider fields.

Only a static, finite H2 mole-fraction grid is accepted. Coordinates must match
grid axes exactly; this module does not interpolate or extrapolate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256

import numpy as np

from ..core import finite
from ..dispersion import HydrogenReleaseFamily
from .facility_accident_chain import FacilityDispersionHandoff
from .preferred_dispersion_alarm import (
    PreferredDispersionReceptor,
    PreferredDispersionReceptorField,
    bind_preferred_dispersion_receptor_field,
)


def _identity(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _digest(*items):
    h = sha256()
    for item in items:
        if isinstance(item, np.ndarray):
            h.update(item.dtype.str.encode())
            h.update(repr(item.shape).encode())
            h.update(item.tobytes())
        else:
            h.update(repr(item).encode("utf-8"))
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class PreferredDispersionConcentrationGrid:
    """Caller-exported finite static provider field in source coordinates.

    ``provider_result`` must be the exact result object retained by the
    accepted handoff. The caller owns exporting native arrays into this typed
    rectangular representation and supplies the evidence for that mapping.
    Axes are metres in the source frame; values are H2 mole fraction.
    """

    handoff: FacilityDispersionHandoff = field(repr=False, compare=False)
    provider_result: object = field(repr=False, compare=False)
    x_m: tuple[float, ...]
    y_m: tuple[float, ...]
    z_m: tuple[float, ...]
    h2_mole_fraction: np.ndarray = field(repr=False, compare=False)
    frame_id: str
    clock_id: str
    grid_evidence_id: str
    steady_window_evidence_id: str
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.handoff) is not FacilityDispersionHandoff:
            raise TypeError("Retain an admitted preferred-provider facility handoff")
        self.handoff.require_current()
        if self.provider_result is not self.handoff.execution.result:
            raise ValueError("Grid must retain the exact native result in the admitted execution")
        if self.handoff.family not in (
            HydrogenReleaseFamily.HIGH_PRESSURE_GAS,
            HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
        ):
            raise ValueError("Unsupported preferred-provider family")
        axes = []
        for axis, name in ((self.x_m, "x axis"), (self.y_m, "y axis"), (self.z_m, "z axis")):
            values = np.asarray(tuple(finite(v, name) for v in axis), dtype=np.float64)
            if values.ndim != 1 or values.size == 0 or np.any(np.diff(values) <= 0.0):
                raise ValueError("Each coordinate axis must be nonempty and strictly increasing")
            values.setflags(write=False)
            axes.append(values)
        values = np.array(self.h2_mole_fraction, dtype=np.float64, copy=True)
        expected_shape = tuple(axis.size for axis in axes)
        if (values.shape != expected_shape or np.any(~np.isfinite(values))
                or np.any((values < 0.0) | (values > 1.0))):
            raise ValueError("Grid values must be finite H2 mole fractions matching x/y/z axes")
        values.setflags(write=False)
        source = self.handoff.finite_source.source
        frame = _identity(self.frame_id, "grid coordinate frame")
        clock = _identity(self.clock_id, "grid clock")
        if frame != source.location.coordinate_frame_id or clock != source.location.clock_id:
            raise ValueError("Grid frame and clock must match the admitted finite source")
        grid_evidence = _identity(self.grid_evidence_id, "native-grid export evidence")
        steady_evidence = _identity(self.steady_window_evidence_id, "steady-window applicability evidence")
        for name, value in zip(("x_m", "y_m", "z_m"), axes, strict=True):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "h2_mole_fraction", values)
        object.__setattr__(self, "frame_id", frame)
        object.__setattr__(self, "clock_id", clock)
        object.__setattr__(self, "grid_evidence_id", grid_evidence)
        object.__setattr__(self, "steady_window_evidence_id", steady_evidence)
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return (
            id(self.handoff), id(self.provider_result), self.frame_id, self.clock_id,
            self.grid_evidence_id, self.steady_window_evidence_id,
            _digest(self.x_m, self.y_m, self.z_m, self.h2_mole_fraction),
        )

    def require_current(self):
        self.handoff.require_current()
        if (self.provider_result is not self.handoff.execution.result
                or self._content() != self._seal):
            raise ValueError("Provider grid identity, values or source mapping changed")
        return self


def sample_preferred_dispersion_receptor_exact(
    grid: PreferredDispersionConcentrationGrid,
    receptor: PreferredDispersionReceptor,
    *,
    expected_family: HydrogenReleaseFamily,
    expected_source_domain_id: str,
    receptor_mapping_evidence_id: str,
) -> PreferredDispersionReceptorField:
    """Bind one exact grid node to the existing sampled alarm interface.

    Axis membership uses exact float equality by design. Near matches, missing
    axes, nonmatching family/domain/frame/clock and variable source-rate windows
    are rejected. There is no temporal axis: steady applicability over the
    finite source window remains an explicitly evidenced caller assumption.
    """
    if type(grid) is not PreferredDispersionConcentrationGrid:
        raise TypeError("Supply a typed finite preferred-provider concentration grid")
    if type(receptor) is not PreferredDispersionReceptor:
        raise TypeError("Supply a typed receptor position")
    grid.require_current()
    handoff = grid.handoff
    source = handoff.finite_source.source
    family = HydrogenReleaseFamily(expected_family)
    domain = _identity(expected_source_domain_id, "caller-declared source domain")
    if handoff.family is not family:
        raise ValueError("Provider family differs from the caller-declared source family")
    if source.location.source_id != domain:
        raise ValueError("Provider source domain differs from the caller declaration")
    if receptor.frame_id != grid.frame_id or receptor.clock_id != grid.clock_id:
        raise ValueError("Receptor frame and clock must match the supplied provider grid")
    indices = []
    for coordinate, axis in zip(receptor.position_m, (grid.x_m, grid.y_m, grid.z_m), strict=True):
        exact = np.flatnonzero(axis == coordinate)
        if exact.size != 1:
            raise ValueError("Receptor coordinate must match exactly one grid node on every axis")
        indices.append(int(exact[0]))
    value = float(grid.h2_mole_fraction[tuple(indices)])
    result = bind_preferred_dispersion_receptor_field(
        handoff,
        receptor,
        value,
        expected_family=family,
        expected_source_domain_id=domain,
        clock_id=grid.clock_id,
        receptor_mapping_evidence_id="|".join((
            grid.grid_evidence_id,
            _identity(receptor_mapping_evidence_id, "exact-node mapping evidence"),
        )),
        steady_window_evidence_id=grid.steady_window_evidence_id,
    )
    grid.require_current()
    result.require_current()
    return result


__all__ = [
    "PreferredDispersionConcentrationGrid",
    "sample_preferred_dispersion_receptor_exact",
]
