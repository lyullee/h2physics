"""Deferred checks for the finite line-source jet-radiation composition."""

from dataclasses import replace

import numpy as np

from h2physics.cluster_validation import ValidationCase

LIMITS = (
    "Requires an already accepted actual HyRAM steady normal-H2/air flame result.",
    "Uniform isotropic radiant power per visible centerline arclength; no obstruction or receiver normal.",
    "Atmospheric transmission is caller-owned; no independent thermal-radiation experiment is implied.",
)


def cases():
    entries = (
        ("jet-radiation-far-field", "validate_far_field"),
        ("jet-radiation-attenuation", "validate_attenuation"),
        ("jet-radiation-refinement", "validate_mesh_refinement"),
        ("jet-radiation-domain", "validate_rejections"),
        ("jet-radiation-radial-wall-source-handoff", "validate_radial_wall_handoff"),
    )
    return tuple(
        ValidationCase(
            identifier=identifier,
            profile="jet-fire-radiation",
            entrypoint=f"{__name__}:{entry}",
            parameters={},
            invariants=((
                "selected native HyRAM W/m2 at the exact global receiver point feeds radial wall intervals",
                "steady flame clock, surface projection factor/evidence, absorptivity and wall geometry are explicit",
                "circumferential mapping is caller-evidenced and radial energy residual closes",
                "source field and downstream radial trace freshness are both retained",
                "no fire dynamics, obstruction, damage, failure probability or vessel qualification is inferred",
            ) if identifier == "jet-radiation-radial-wall-source-handoff" else (
                "native-emitted-power-bound",
                "receiver-incident-flux",
                "radiation fields are issued only by the existing line-source evaluator",
                "direct construction and dataclass clones cannot reseal source-bound output",
            )),
        )
        for identifier, entry in entries
    )


def _build(**parameters):
    from examples.jet_radiation import build_policy, build_source
    from h2physics.adapters.jet_radiation import line_source_irradiance

    source = build_source(**parameters)
    policy = build_policy(**parameters)
    return source, policy, line_source_irradiance


def validate_far_field(*, work_directory, **parameters):
    from h2physics.adapters.jet_radiation import (
        _JetRadiationReceiptIssuer, incident_history_from_jet_radiation,
    )
    source, policy, run = _build(**parameters)
    flux = run(source, [[0.0, 20.0, 5.0]], relative_humidity=.5,
               transmissivity=lambda d, t, rh: d*0+1, policy=policy)
    assert flux.incident_flux_w_m2[0] > 0
    assert flux.mean_path_transmissivity == 1.0
    assert flux.atmosphere_weighted_power_w == flux.emitted_power_w
    assert flux.line_source_power_w_m > 0
    history = incident_history_from_jet_radiation(
        flux, 0, start_s=source.window.start_s, end_s=source.window.end_s,
        clock_id=source.window.clock_id, evidence_id="authored-point-history",
        steady_projection_evidence_id="authored-steady-point-irradiance-only",
    )
    assert history.source_owner is flux
    assert history.incident_flux_w_m2[0] == flux.incident_flux_w_m2[0]
    for changes in (
        {"incident_flux_w_m2": flux.incident_flux_w_m2*2.0},
        {"segment_transmissivity": np.full_like(flux.segment_transmissivity, 1.2)},
        {"atmosphere_weighted_power_w": flux.atmosphere_weighted_power_w+1.0},
    ):
        try:
            replace(flux, **changes)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("A directly constructed radiation field accepted forged output")
    try:
        type(flux)(
            flux.source, flux.receiver_points_m, flux.incident_flux_w_m2,
            flux.segment_transmissivity, flux.mean_path_transmissivity,
            flux.emitted_power_w, flux.atmosphere_weighted_power_w,
            flux.minimum_distance_m, flux.maximum_transmissivity,
            flux.line_source_power_w_m, flux.policy,
        )
    except TypeError:
        direct_construction_rejected = True
    else:
        raise AssertionError("Direct constructor forged a line-radiation evaluation receipt")
    try:
        _JetRadiationReceiptIssuer(object())
    except TypeError:
        forged_issuer_rejected = True
    else:
        raise AssertionError("A caller-created radiation issuer minted a result token")
    flux.incident_flux_w_m2.setflags(write=True)
    old = float(flux.incident_flux_w_m2[0])
    flux.incident_flux_w_m2[0] = old+1.
    try:
        flux.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Retained jet radiation mutation was not detected")
    finally:
        flux.incident_flux_w_m2[0] = old
        flux.incident_flux_w_m2.setflags(write=False)
    return {"receiver_flux_w_m2": float(flux.incident_flux_w_m2[0]),
            "direct_construction_rejected": direct_construction_rejected,
            "forged_issuer_rejected": forged_issuer_rejected}, LIMITS


def validate_attenuation(*, work_directory, **parameters):
    source, policy, run = _build(**parameters)
    point = [[0.0, 20.0, 5.0]]
    clear = run(source, point, relative_humidity=.5, transmissivity=lambda d, t, rh: d*0+1,
                policy=policy)
    dim = run(source, point, relative_humidity=.5, transmissivity=lambda d, t, rh: d*0+.4,
              policy=policy)
    assert np.allclose(dim.incident_flux_w_m2, .4*clear.incident_flux_w_m2)
    assert dim.mean_path_transmissivity < clear.mean_path_transmissivity
    assert dim.atmosphere_weighted_power_w < clear.atmosphere_weighted_power_w
    return {"attenuated_flux_ratio": float(dim.incident_flux_w_m2[0]/clear.incident_flux_w_m2[0])}, LIMITS


def validate_mesh_refinement(*, work_directory, **parameters):
    source, policy, run = _build(**parameters)
    point = [[0.0, 25.0, 8.0]]
    native_segments = len(source.centreline) - 1
    coarse = run(source, point, relative_humidity=.4,
                 transmissivity=lambda d, t, rh: d*0+1, policy=policy)
    fine = run(source, point, relative_humidity=.4,
               transmissivity=lambda d, t, rh: d*0+1,
               policy=replace(policy, segment_subdivisions=2))
    error = abs(coarse.incident_flux_w_m2[0] / fine.incident_flux_w_m2[0] - 1.0)
    assert error < 0.02
    return {"native_segments": native_segments, "midpoint_relative_error": float(error)}, LIMITS


def validate_rejections(*, work_directory, **parameters):
    from h2physics.adapters.jet_radiation import JetRadiationError

    source, policy, run = _build(**parameters)
    try:
        run(source, [[0., 0., 0.]], relative_humidity=.5,
            transmissivity=lambda d, t, rh: d*0+1, policy=policy)
    except JetRadiationError:
        return {"near_source_rejected": True}, LIMITS
    raise AssertionError("The declared source exclusion region must be enforced")


def validate_radial_wall_handoff(*, work_directory, **parameters):
    from math import pi

    from h2physics.adapters.jet_radiation_radial_wall import run_jet_radiation_radial_wall
    from h2physics.core import Origin
    from h2physics.materials.radial_heat import RadialSolidMaterial, RadialThermalBoundary

    source, policy, run = _build(**parameters)
    field = run(source, [[0., 20., 5.]], relative_humidity=.5,
                transmissivity=lambda d, t, rh: d*0+1, policy=policy)
    result = run_jet_radiation_radial_wall(
        field, 0, inner_radius_m=.09, outer_radius_m=.1, length_m=1.,
        material=RadialSolidMaterial(7800., lambda t: 500., lambda t: 15.,
                                     "authored-wall", "synthetic-wall-property-contract"),
        initial_temperature_k=300.,
        inner_boundary=RadialThermalBoundary("adiabatic", 0., "synthetic-inner-insulation"),
        surface_projection_factor=.8,
        surface_projection_evidence_id="synthetic-wall-projection-factor",
        absorptivity=.75, geometry_evidence_id="synthetic-cylinder-geometry",
        application_evidence_id="synthetic-steady-fire-wall-application",
        uniform_circumference_evidence_id="synthetic-uniform-circumference-premise",
        cells=6, maximum_step_s=.1, energy_tolerance_j=1e-2)
    assert result.require_current() is result
    assert result.receiver_point_m == (0., 20., 5.)
    assert result.receiver_frame_id == policy.geometry_frame_id
    assert result.radial_trace.incident.source_owner is field
    expected = ((2*pi*.1*1.)*.75*.8*field.incident_flux_w_m2[0]
                *(source.window.end_s-source.window.start_s))
    assert abs(result.radial_trace.absorbed_incident_j-expected) <= 1e-8*max(expected, 1.)
    return {"receiver_flux_w_m2": float(field.incident_flux_w_m2[0]),
            "absorbed_incident_j": result.radial_trace.absorbed_incident_j,
            "radial_energy_residual_j": result.radial_trace.outer_heat_residual_j,
            "steady_window_s": source.window.end_s-source.window.start_s,
            "origin": Origin.PREDICTED.value}, LIMITS
