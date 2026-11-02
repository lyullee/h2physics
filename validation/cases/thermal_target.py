"""Deferred finite target checks; metadata discovery performs no calculation."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITATIONS = (
    "Synthetic incident flux and target properties; no material calibration.",
    "Uniform lumped temperature; no conduction gradient, phase change, damage or injury.",
    "Held convection/radiation surroundings; fire and occlusion remain external owners.",
)


def _run(**parameters):
    from examples.thermal_target import run_example

    return run_example(**parameters)


def validate_finite_pulse(*, work_directory):
    trace = _run()
    assert trace.status == "implemented_unverified"
    assert trace.maximum_temperature_k > trace.target.initial_temperature_k
    assert trace.temperature_k[-1] < trace.maximum_temperature_k
    assert max(abs(trace.energy_residual_j)) <= (
        trace.tolerances.energy_j
        + trace.tolerances.relative_energy * max(abs(trace.absorbed_incident_j))
    )
    assert all(segment.success for segment in trace.native_segments)
    assert trace.require_current() is trace
    try:
        trace.stored_energy_j.setflags(write=True)
    except ValueError:
        # Immutable bytes-backed outputs must not regain write access.
        pass
    else:
        original = float(trace.stored_energy_j[-1])
        trace.stored_energy_j[-1] = original+1.
        try:
            trace.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("Changed original target energy ledger was accepted")
        finally:
            trace.stored_energy_j[-1] = original
            trace.stored_energy_j.setflags(write=False)
    from dataclasses import replace
    try:
        replace(trace, maximum_temperature_k=trace.maximum_temperature_k+1.)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("Cloned target trace resealed a changed maximum temperature")
    return ValidationOutcome(True, {
        "maximum_temperature_k": trace.maximum_temperature_k,
        "absorbed_incident_j": trace.absorbed_incident_j[-1],
        "maximum_energy_residual_j": max(abs(trace.energy_residual_j)),
    }, LIMITATIONS)


def validate_lossless_analytic(*, work_directory):
    from examples.thermal_target import authored_model
    from h2physics.adapters.thermal_target import run_thermal_target

    history, target, tolerances = authored_model(emissivity=0.0,
                                                  convective_coefficient_w_m2_k=0.0)
    trace = run_thermal_target(history, target, tolerances, maximum_step_s=0.25)
    expected = target.initial_temperature_k + (
        target.area_m2 * target.absorptivity * history.incident_flux_w_m2[0]
        * (history.edges_s[1] - history.edges_s[0]) / target.heat_capacity_j_k
    )
    assert abs(trace.temperature_k[-1] - expected) < 1e-8
    assert max(abs(trace.convective_export_j)) == 0.0
    assert max(abs(trace.radiative_export_j)) == 0.0
    return ValidationOutcome(True, {"analytic_final_temperature_k": expected}, LIMITATIONS)


def validate_temperature_dependent_capacity(*, work_directory):
    from dataclasses import replace
    from math import sqrt

    from examples.thermal_target import authored_model
    from h2physics.adapters.thermal_target import run_thermal_target

    del work_directory
    history, target, tolerances = authored_model(
        flux_w_m2=1.0e6, emissivity=0.0, convective_coefficient_w_m2_k=0.0,
    )
    reference_capacity = target.heat_capacity_j_k
    reference_temperature = target.initial_temperature_k
    slope_per_k = 0.004
    variable = replace(
        target,
        heat_capacity_j_k=lambda temperature: reference_capacity * (
            1.0 + slope_per_k * (temperature - reference_temperature)
        ),
    )
    trace = run_thermal_target(history, variable, tolerances, maximum_step_s=0.1)
    incident_energy = (
        variable.area_m2 * variable.absorptivity * history.incident_flux_w_m2[0]
        * (history.edges_s[1] - history.edges_s[0])
    )
    delta = (
        sqrt(1.0 + 2.0 * slope_per_k * incident_energy / reference_capacity) - 1.0
    ) / slope_per_k
    expected = reference_temperature + delta
    assert abs(trace.temperature_k[trace.time_s == history.edges_s[1]][0] - expected) < 1e-7
    assert abs(trace.stored_energy_j[trace.time_s == history.edges_s[1]][0] - incident_energy) < 1e-5
    assert max(abs(trace.energy_residual_j)) <= (
        tolerances.energy_j + tolerances.relative_energy * incident_energy
    )
    return ValidationOutcome(True, {
        "analytic_variable_capacity_temperature_k": expected,
        "absorbed_energy_j": incident_energy,
        "capacity_at_final_temperature_j_k": variable.heat_capacity_j_k(expected),
    }, LIMITATIONS)


def validate_stage_refinement(*, work_directory):
    import numpy as np

    from examples.thermal_target import authored_model
    from h2physics.adapters.thermal_target import IncidentHeatHistory, run_thermal_target

    history, target, tolerances = authored_model()
    refined = IncidentHeatHistory(np.array([0.0, 5.0, 10.0, 20.0, 30.0]),
        np.array([12_000.0, 12_000.0, 0.0, 0.0]), history.clock_id,
        history.frame_id, history.source_id, history.boundary_id,
        history.evidence_id, history.origin, history.source_owner)
    coarse = run_thermal_target(history, target, tolerances, maximum_step_s=0.25)
    fine = run_thermal_target(refined, target, tolerances, maximum_step_s=0.25)
    assert abs(coarse.temperature_k[-1] - fine.temperature_k[-1]) < 1e-7
    assert abs(coarse.absorbed_incident_j[-1] - fine.absorbed_incident_j[-1]) < 1e-7
    return ValidationOutcome(
        True, {"refined_intervals": len(refined.incident_flux_w_m2)}, LIMITATIONS
    )


def validate_domain_rejection(*, work_directory):
    from examples.thermal_target import authored_model
    from h2physics.adapters.thermal_target import ThermalTargetError, run_thermal_target

    history, target, tolerances = authored_model(maximum_temperature_k=300.01)
    try:
        run_thermal_target(history, target, tolerances, maximum_step_s=0.25)
    except ThermalTargetError as error:
        assert not error.native_segments and "temperature domain" in str(error)
        return ValidationOutcome(
            True, {"completed_native_segment_prefix": len(error.native_segments),
                  "failing_rhs_context_retained": error.cause is error.__cause__}, LIMITATIONS
        )
    raise AssertionError("Out-of-domain target response was silently accepted")


def validate_exposure_history_handoff(*, work_directory):
    import numpy as np

    from h2physics.adapters.hyram_exposure import ExposureHistory, ExposureReceptor
    from h2physics.adapters.thermal_target import incident_history_from_exposure
    from h2physics.core import Origin

    receptor = ExposureReceptor("target-a", "plant-frame", (0., 0., 0.), "measurement-basis")
    history = ExposureHistory(
        receptor, np.asarray([2., 3., 5.]), np.asarray([100., 250.]),
        "incident_radiant_flux", "W/m2", "left_hold", "plant-clock",
        "sensor-series-a", "sensor-calibration-a", Origin.MEASURED,
    )
    boundary = incident_history_from_exposure(history, evidence_id="target-map-a")
    assert boundary.source_owner is history
    assert np.array_equal(boundary.edges_s, history.time_s)
    assert np.array_equal(boundary.incident_flux_w_m2, history.values)
    assert boundary.clock_id == history.clock_id
    assert boundary.frame_id == receptor.frame_id
    assert boundary.origin is Origin.MEASURED
    assert boundary.boundary_id.endswith(history.basis_id)

    for wrong in (
        ExposureHistory(receptor, np.asarray([2., 3., 5.]), np.asarray([10., 20.]),
                        "gauge_overpressure", "Pa", "left_hold", "plant-clock",
                        "pressure-series", "gauge-basis", Origin.MEASURED),
        ExposureHistory(receptor, np.asarray([2., 3., 5.]), np.asarray([100., 250., 300.]),
                        "incident_radiant_flux", "W/m2", "linear", "plant-clock",
                        "sensor-series-a", "sensor-calibration-a", Origin.MEASURED),
        ExposureHistory(receptor, np.asarray([2., 3., 5.]), np.asarray([100., 250.]),
                        "incident_radiant_flux", "W/m2", "left_hold", "plant-clock",
                        "sensor-series-a", "sensor-calibration-a", Origin.MEASURED,
                        np.asarray([True, False])),
    ):
        try:
            incident_history_from_exposure(wrong, evidence_id="target-map-a")
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("Nonincident, non-left-held, or invalid exposure was admitted")
    return ValidationOutcome(True, {"interval_count": len(boundary.incident_flux_w_m2)},
                             ("Source history retained exactly; no exposure physics or target response inferred",))


def validate_effective_area_receipt(*, work_directory):
    from dataclasses import fields, replace
    from types import SimpleNamespace

    import numpy as np

    from h2physics.adapters.pifira_heat import (
        AxialContactGeometry,
        EffectiveAreaEvidence,
        EffectiveAreaResult,
        contents_equivalent_heat_flux,
        pifira_effective_area,
    )
    from h2physics.core import Origin

    del work_directory
    angles = np.asarray([-80., -40., -20., 0., 20., 40., 80.])
    shape = np.exp(-.5*(angles/20.)**2)
    native = SimpleNamespace(
        __name__="pifira", __version__="0.3.0",
        effective_arc=lambda theta, values, T_amb_C: {"sigma": 20., "arc_deg": 120.},
        radiative_driving_force=lambda values, T_amb_C: values-T_amb_C,
        effective_height=lambda flame, wetted: min(flame, wetted),
        effective_area=lambda diameter, arc, height: diameter*height*np.deg2rad(arc),
    )
    evidence = EffectiveAreaEvidence(
        "source", "clock", 0., 2., "centre", "shape", "wetted", "instantaneous",
        Origin.PREDICTED,
    )
    geometry = AxialContactGeometry(0., 2., .2, 1.8, "axis")
    area = pifira_effective_area(
        native, angles_deg=angles, wall_temperature_k=300.+20.*shape,
        ambient_temperature_k=300., diameter_m=.4, axial_geometry=geometry,
        evidence=evidence, maximum_normalized_fit_error=1.e-10,
    )
    assert area.require_current() is area
    values = {item.name: getattr(area, item.name) for item in fields(area)
              if not item.name.startswith("_")}
    try:
        EffectiveAreaResult(**values)
    except ValueError:
        pass
    else:
        raise AssertionError("Direct effective-area results must not claim native-fit origin")
    try:
        replace(area, area_m2=area.area_m2*2.)
    except ValueError:
        pass
    else:
        raise AssertionError("A cloned area must not inherit the one-use native-fit issuer")

    original_area = area.area_m2
    object.__setattr__(area, "area_m2", original_area*2.)
    try:
        area.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Post-issuance effective-area mutation was accepted")
    try:
        contents_equivalent_heat_flux(
            None, 0, area, allocation_evidence_id="allocation",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Downstream contents-flux handoff accepted a stale area")
    return ValidationOutcome(
        True, {"issued_area_m2": original_area},
        ("Synthetic native API contract; no PIFIRA prediction or physical qualification.",),
    )


def cases():
    definitions = (
        (
            "thermal-target-pulse",
            "validate_finite_pulse",
            ("finite-storage", "signed-losses", "energy-ledger",
             "native-issued-trace-rejects-cloned-summary"),
        ),
        ("thermal-target-lossless", "validate_lossless_analytic", ("analytic-constant-flux",)),
        ("thermal-target-variable-capacity", "validate_temperature_dependent_capacity",
         ("temperature-dependent-total-capacity", "enthalpy-integral-audit",
          "independent-analytic-constant-flux-solution")),
        ("thermal-target-refinement", "validate_stage_refinement", ("interval-refinement",)),
        (
            "thermal-target-domain",
            "validate_domain_rejection",
            ("domain-rejection", "failure-context"),
        ),
        ("thermal-target-exposure-history", "validate_exposure_history_handoff",
         ("incident-radiant-flux-only", "exact-left-hold-identity",
          "structurally-valid-linear-series-rejected-by-target-adapter",
          "invalid-mask-rejection")),
        ("pifira-effective-area-receipt", "validate_effective_area_receipt",
         ("native-issued-area-only", "receipt-clone-rejected", "downstream-currentness")),
    )
    return tuple(ValidationCase(identifier=name, profile="thermal-target",
        entrypoint=f"validation.cases.thermal_target:{entry}", parameters={}, invariants=invariants)
        for name, entry, invariants in definitions)
