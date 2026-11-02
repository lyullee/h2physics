"""Deferred contracts for caller-owned component-map interpolation."""

import math

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "The map is caller-supplied and its coordinate conventions remain caller-owned.",
    "Interpolation is bilinear on a rectangular grid; no extrapolation or shaft coupling is performed.",
    "No machine performance qualification is implied.",
)


def cases():
    return (
        ValidationCase(
            identifier="turbine-component-map-interpolation",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_interpolation",
            invariants=("rectangular-map-admission", "bilinear-interpolation", "map-source-retention", "direct-result-reconstruction"),
        ),
        ValidationCase(
            identifier="turbine-component-map-domain",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_domain_guards",
            invariants=("no-speed-extrapolation", "no-pressure-ratio-extrapolation", "positive-flow", "efficiency-domain", "strict-map-metadata"),
        ),
        ValidationCase(
            identifier="turbine-component-map-integrity",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_integrity_guards",
            invariants=("positive-speed-domain", "reject-malformed-map-dimensions", "reject-nonphysical-map-efficiency", "reject-forged-interpolated-result", "reject-post-admission-map-mutation", "reject-map-reinitialization-after-mutation"),
        ),
    )


def _map(**changes):
    from h2physics.combustion import TurbineComponentMap

    values = dict(
        map_id="deferred-authored-map",
        evidence_id="deferred-map-evidence",
        source_uri="urn:h2physics:authored-turbine-map-fixture",
        license_id="NOASSERTION",
        source_sha256="0" * 64,
        speed_unit="corrected-rpm",
        pressure_ratio_convention="inlet-over-exit-total-pressure",
        corrected_mass_flow_basis="kg/s at declared correction reference",
        corrected_speed=(0.5, 1.0),
        expansion_pressure_ratio=(2.0, 4.0),
        corrected_mass_flow_kg_s=((1.0, 1.4), (1.2, 1.8)),
        isentropic_efficiency=((0.7, 0.76), (0.78, 0.84)),
    )
    values.update(changes)
    return TurbineComponentMap(**values)


def validate_interpolation(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.combustion import interpolate_turbine_map

    point = interpolate_turbine_map(_map(), corrected_speed=0.75, expansion_pressure_ratio=3.0)
    assert math.isclose(point.corrected_mass_flow_kg_s, 1.35, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(point.isentropic_efficiency, 0.77, rel_tol=0.0, abs_tol=1e-12)
    assert point.component_map.evidence_id == "deferred-map-evidence"
    return ValidationOutcome(True, {"corrected_mass_flow_kg_s": point.corrected_mass_flow_kg_s, "isentropic_efficiency": point.isentropic_efficiency}, LIMITS)


def validate_domain_guards(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.combustion import interpolate_turbine_map

    component_map = _map()
    rejected = 0
    for coordinate in ((0.49, 3.0), (1.01, 3.0), (0.75, 1.99), (0.75, 4.01)):
        try:
            interpolate_turbine_map(component_map, corrected_speed=coordinate[0], expansion_pressure_ratio=coordinate[1])
        except ValueError:
            rejected += 1
    assert rejected == 4
    return ValidationOutcome(True, {"out_of_domain_points_rejected": rejected}, LIMITS)


def validate_integrity_guards(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from h2physics.combustion import TurbineMapPoint, interpolate_turbine_map

    rejected = 0
    for changes in (
        {"corrected_speed": (-1.0, 1.0)},
        {"corrected_mass_flow_kg_s": ((1.0,), (1.2,))},
        {"isentropic_efficiency": ((0.7, 1.2), (0.78, 0.84))},
    ):
        try:
            _map(**changes)
        except ValueError:
            rejected += 1
    point = interpolate_turbine_map(_map(), corrected_speed=0.75, expansion_pressure_ratio=3.0)
    try:
        replace(point, corrected_mass_flow_kg_s=point.corrected_mass_flow_kg_s + 0.1)
    except ValueError:
        rejected += 1
    component_map = _map()
    original_efficiency = component_map.isentropic_efficiency
    object.__setattr__(component_map, "isentropic_efficiency", ((0.6, 0.65), (0.7, 0.75)))
    for operation in (
        lambda: interpolate_turbine_map(component_map, corrected_speed=0.75,
                                        expansion_pressure_ratio=3.0),
        component_map.__post_init__,
    ):
        try:
            operation()
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Post-admission turbine-map mutation was admitted")
    object.__setattr__(component_map, "isentropic_efficiency", original_efficiency)
    component_map.require_current()
    assert rejected == 6
    return ValidationOutcome(True, {"invalid_map_or_result_rejected": rejected}, LIMITS)
