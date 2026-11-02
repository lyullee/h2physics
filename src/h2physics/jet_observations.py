"""Spatial observation of actual native calm jets in a dry, single-gas envelope.

The native profile remains the owner. Positions are projected onto its computed
piecewise-linear centreline; gas mole fraction approximates the reported volume
fraction only under the explicitly selected low-pressure, dry gas assumptions.
"""

from dataclasses import dataclass

import numpy as np

from .core import Origin, finite
from .observations import GAS_VOLUME_FRACTION_BASIS, ObservationTable, Variable


@dataclass(frozen=True, slots=True)
class JetPointPrediction:
    observations: ObservationTable
    invalid_reasons: tuple[str, ...]


def observe_native_gas_jet(
    run, points_m, *, coordinate_frame_id: str, coordinate_origin: Origin,
    evidence_id: str, radial_tail_policy: str, allow_failed_run: bool = False,
) -> JetPointPrediction:
    """Evaluate declared Cartesian positions, retaining invalid/extrapolated rows.

    Choose mask or native_gaussian_continuation explicitly for radii beyond the
    native flux quadrature. The latter calls the actual public analytic radial
    profile and records every tail point. Neither option extrapolates in axial
    distance. This point operator does not resolve suction-probe aperture/time
    response, walls or a phase-selective observation in a condensing mixture.
    """
    if radial_tail_policy not in {"mask", "native_gaussian_continuation"}:
        raise ValueError("Declare the radial quadrature/tail interpretation")
    if not evidence_id.strip() or coordinate_frame_id != run.boundary.section.coordinate_frame_id:
        raise ValueError("Observation evidence and the exact declared Cartesian frame are required")
    if not run.audit.passed and not allow_failed_run:
        raise ValueError("A failed native conservation audit needs explicit diagnostic observation permission")
    points = np.array(points_m, dtype=float, copy=True)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points) or not np.all(np.isfinite(points)):
        raise ValueError("Supply finite Cartesian observation points with shape (n, 3)")
    model, result, section = run.model, run.native, run.boundary.section
    if (model.ambient_absolute_humidity != 0. or model.ambient_pressure > 200_000.
            or model.ambient_pressure <= 0.):
        raise ValueError("The reviewed gas-volume observer requires dry air and pressure at most 200 kPa")
    fuel_mw = finite(model.fuel_molecular_weight, "native fuel molar mass", positive=True)
    air_mw = finite(model.ambient_molecular_weight, "native ambient molar mass", positive=True)
    offset = points-np.array(section.origin_m)
    horizontal, vertical = np.array(section.horizontal_unit), np.array(section.vertical_unit)
    normal = np.cross(horizontal, vertical)
    planar = np.column_stack((offset@horizontal, offset@vertical))
    lateral = offset@normal
    centreline = np.column_stack((result.x, result.y))
    segments = np.diff(centreline, axis=0)
    lengths_squared = np.sum(segments**2, axis=1)
    if not np.all(np.isfinite(lengths_squared)) or np.any(lengths_squared <= 0.):
        raise ValueError("The computed native centreline has degenerate segments")
    fractions = np.sum((planar[:, None, :]-centreline[None, :-1, :])*segments, axis=2)/lengths_squared
    clipped = np.clip(fractions, 0., 1.)
    projections = centreline[None, :-1, :]+clipped[:, :, None]*segments
    distances_squared = np.sum((planar[:, None, :]-projections)**2, axis=2)
    selected = np.argmin(distances_squared, axis=1)
    values, masks, reasons = [], [], []
    for index, segment in enumerate(selected):
        weight, unbounded_weight = clipped[index, segment], fractions[index, segment]
        distance = result.S[segment]+weight*(result.S[segment+1]-result.S[segment])
        radius = float(np.sqrt(distances_squared[index, segment]+lateral[index]**2))
        outside = ((segment == 0 and unbounded_weight < -1e-12)
                   or (segment == len(segments)-1 and unbounded_weight > 1+1e-12))
        base = [*points[index], distance, radius, np.nan, np.nan, np.nan, np.nan, np.nan]
        valid = [True]*5+[False]*5
        reason = ""
        if outside:
            reason = "outside_computed_axial_window"
        else:
            state = result.state_at_s(float(distance))
            tail = radius > model.radial_limit*state[1]
            base[-1] = float(tail)
            valid[-1] = True
            if tail and radial_tail_policy == "mask":
                reason = "outside_native_radial_quadrature"
            else:
                try:
                    fraction, density, temperature = model.radial_state(state, radius)
                    physical = (np.all(np.isfinite((fraction, density, temperature)))
                                and 0. <= fraction <= 1. and density > 0. and temperature > 0.)
                    if not physical:
                        reason = "invalid_native_radial_state"
                    else:
                        base[6:9] = [fraction, density, temperature]
                        valid[6:9] = [True]*3
                        if not 200. <= temperature <= 300.:
                            reason = "outside_reviewed_dry_gas_temperature_envelope"
                        else:
                            molar_h2, molar_air = fraction/fuel_mw, (1.-fraction)/air_mw
                            base[5] = molar_h2/(molar_h2+molar_air)
                            valid[5] = True
                except (ValueError, RuntimeError, FloatingPointError) as error:
                    reason = f"native_profile_error:{type(error).__name__}"
        values.append(base)
        masks.append(valid)
        reasons.append(reason)
    variables = (Variable("x", "length", "m"), Variable("y", "length", "m"),
        Variable("z", "length", "m"), Variable("streamline_distance", "length", "m"),
        Variable("radius", "length", "m"), Variable("h2_volume_fraction", "volume_fraction", "1", GAS_VOLUME_FRACTION_BASIS),
        Variable("whole_mixture_h2_mass_fraction", "mass_fraction", "1", "H2 mass / complete mixture mass"),
        Variable("bulk_density", "density", "kg/m3"), Variable("temperature", "temperature", "K"),
        Variable("outside_radial_quadrature", "domain_flag", "1"))
    origins = (Origin(coordinate_origin),)*3+(Origin.PREDICTED,)*7
    table = ObservationTable(np.array(values), variables, np.array(masks),
        tuple(f"point-{index}" for index in range(len(points))), (evidence_id,)*len(points),
        origins, evidence_id, (("coordinate_frame", coordinate_frame_id),
        ("observation_model", "dry gas H2 mole fraction as sample gas volume fraction; 200-300 K, <=200 kPa"),
        ("geometry", "nearest piecewise-linear native centreline; native state interpolation"),
        ("radial_tail_policy", radial_tail_policy), ("native_audit", "PASS" if run.audit.passed else "FAIL"),
        ("ground", "unbounded declaration" if section.ground_vertical_coordinate_m is None else "declared ground plane")))
    return JetPointPrediction(table, tuple(reasons))
