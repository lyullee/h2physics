"""Deferred checks for radial-gradient thermoelastic cylinder stresses."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="elastic-cylinder-radial-thermoelasticity",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_radial_thermoelasticity",
            invariants=(
                "actual isotropic radial-temperature BVP API",
                "uniform profile reduces to the existing free/fixed thermoelastic levels",
                "radial tractions match pressure at both wall boundaries",
                "free axial resultant or fixed-end reaction closes force balance",
                "adaptive solver residual and immutable stress outputs are reported",
                "point and history von Mises outputs match their three stress components",
                "exact-index stress-field extraction retains time, clock, load, profile, solver residual and iteration metadata",
                "stress-field extraction rejects booleans, noninteger indices and out-of-support indices without interpolation",
                "sample records reject equal-valued replacement field arrays",
                "exact-time radial stress path samples all total Cauchy components without time interpolation",
                "stress-path radial evaluation rejects extrapolation and post-return mutation",
                "stress-history freshness checks reject replaced output arrays and changed nested temperature samples",
                "stress records reject temperature profiles that do not span the cylinder wall",
                "supplied pressure and radial-temperature snapshots map to one ordered physical clock",
            ),
        ),
    )


def validate_radial_thermoelasticity(*, work_directory, **parameters):
    from scipy.integrate import simpson

    from h2physics.core import Origin
    from h2physics.materials.elastic_cylinder import (
        CylinderGeometry,
        CylinderPressureLoad,
        IsotropicThermoelasticMaterial,
        UniformCylinderTemperature,
        thermoelastic_lame_stress_field,
    )
    from h2physics.materials.radial_thermoelastic import (
        RadialTemperatureProfile,
        radial_thermoelastic_cylinder,
        radial_thermoelastic_history,
    )

    inner, outer = 0.08, 0.16
    radii = np.linspace(inner, outer, 101)
    profile_radii = np.linspace(inner, outer, 21)
    material = IsotropicThermoelasticMaterial(
        190.0e9,
        0.29,
        12.0e-6,
        "authored-isotropic-shell",
        "authored-material-properties",
    )
    geometry = CylinderGeometry(inner, outer, "closed", "authored-radial-shell")
    load = CylinderPressureLoad(8.0e6, 1.0e5, "authored-radial-pressure", Origin.SYNTHETIC)
    uniform_temperature = np.full_like(profile_radii, 393.15)
    profile = RadialTemperatureProfile(
        profile_radii,
        uniform_temperature,
        293.15,
        "uniform-reference-profile",
        "authored-temperature-profile",
    )

    metrics = {}
    results = {}
    for restraint in ("free", "fixed"):
        result = radial_thermoelastic_cylinder(
            geometry,
            load,
            profile,
            material,
            radii,
            axial_restraint=restraint,
            evidence_id="isotropic-axisymmetric-equilibrium-specialization",
        )
        reference = thermoelastic_lame_stress_field(
            geometry,
            load,
            radii,
            material,
            UniformCylinderTemperature(
                293.15,
                393.15,
                restraint,
                f"uniform-{restraint}-boundary",
                "authored-temperature-profile",
            ),
            evidence_id="authored-uniform-thermoelastic-reference",
        )
        assert np.allclose(result.radial_stress_pa, reference.radial_stress_pa, rtol=2.0e-6)
        assert np.allclose(result.hoop_stress_pa, reference.hoop_stress_pa, rtol=2.0e-6)
        assert np.allclose(result.axial_stress_pa, reference.axial_stress_pa, rtol=2.0e-6)
        assert np.isclose(result.radial_stress_pa[0], -load.internal_pressure_pa, atol=10.0)
        assert np.isclose(result.radial_stress_pa[-1], -load.external_pressure_pa, atol=10.0)
        assert result.max_bvp_rms_residual <= 2.0e-6
        assert result.max_normalized_boundary_residual <= 1.0e-7
        assert not result.radial_stress_pa.flags.writeable
        results[restraint] = result
        metrics[f"{restraint}_axial_strain"] = result.axial_strain
        metrics[f"{restraint}_support_reaction_n"] = result.axial_support_reaction_n
        metrics[f"{restraint}_max_bvp_rms_residual"] = result.max_bvp_rms_residual
        metrics[f"{restraint}_max_normalized_boundary_residual"] = (
            result.max_normalized_boundary_residual
        )

    fixed = results["fixed"]
    free = results["free"]
    try:
        replace(
            fixed,
            von_mises_stress_pa=fixed.von_mises_stress_pa + 1.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A von Mises vector inconsistent with stresses was admitted")
    cap_force = np.pi * (
        load.internal_pressure_pa * inner**2 - load.external_pressure_pa * outer**2
    )
    free_resultant = (
        2.0
        * np.pi
        * simpson(
            free.axial_stress_pa * free.radius_m,
            x=free.radius_m,
        )
    )
    assert np.isclose(free_resultant, cap_force, rtol=2.0e-6, atol=1.0e-4)
    metrics["free_axial_resultant_residual_n"] = free_resultant - cap_force
    wall_force = (
        2.0
        * np.pi
        * simpson(
            fixed.axial_stress_pa * fixed.radius_m,
            x=fixed.radius_m,
        )
    )
    assert np.isclose(
        fixed.axial_support_reaction_n,
        wall_force - cap_force,
        rtol=2.0e-8,
        atol=1.0e-5,
    )
    metrics["fixed_force_residual_n"] = fixed.axial_support_reaction_n - (wall_force - cap_force)

    second_profile = RadialTemperatureProfile(
        profile_radii,
        np.linspace(375.0, 410.0, profile_radii.size),
        293.15,
        "authored-radial-gradient-profile",
        "authored-temperature-profile",
    )
    second_load = CylinderPressureLoad(
        10.0e6, 1.0e5, "authored-second-radial-pressure", Origin.SYNTHETIC
    )
    history = radial_thermoelastic_history(
        geometry,
        (load, second_load),
        (profile, second_profile),
        material,
        radii,
        np.array([0.0, 60.0]),
        axial_restraint="fixed",
        clock_id="authored-radial-thermal-pressure-clock",
        evidence_id="authored-quasistatic-radial-thermoelastic-history",
    )
    second_reference = radial_thermoelastic_cylinder(
        geometry,
        second_load,
        second_profile,
        material,
        radii,
        axial_restraint="fixed",
        evidence_id="authored-quasistatic-radial-thermoelastic-history",
    )
    assert np.array_equal(history.time_s, [0.0, 60.0])
    assert history.require_current() is history
    assert history.clock_id == "authored-radial-thermal-pressure-clock"
    assert history.loads == (load, second_load)
    assert history.temperature_profiles[0] is profile
    assert history.temperature_profiles[1] is second_profile
    sample = history.stress_field_at(1)
    assert sample.require_current() is sample
    assert sample.sample_index == 1 and sample.time_s == 60.0
    assert sample.clock_id == history.clock_id
    assert sample.stress_field.load is second_load
    assert sample.stress_field.temperature is second_profile
    assert np.array_equal(sample.stress_field.hoop_stress_pa, history.hoop_stress_pa[1])
    assert sample.stress_field.bvp_iterations == history.bvp_iterations[1]
    assert not sample.stress_field.hoop_stress_pa.flags.writeable
    path_radii = np.linspace(inner, outer, 37)
    path = history.stress_path_at(1, path_radii)
    assert path.require_current() is path
    assert path.sample.history is history
    assert path.sample.time_s == history.time_s[1]
    assert path.field_convention == "total_pressure_plus_thermal"
    assert np.array_equal(path.radius_m, path_radii)
    assert np.allclose(path.radial_stress_pa[[0, -1]],
                       [-second_load.internal_pressure_pa, -second_load.external_pressure_pa],
                       rtol=2.0e-6, atol=10.0)
    assert all(not getattr(path, name).flags.writeable for name in (
        "radius_m", "radial_stress_pa", "hoop_stress_pa", "axial_stress_pa",
        "von_mises_stress_pa",
    ))
    try:
        history.stress_path_at(1, np.array([inner - 1e-6, outer]))
    except ValueError:
        pass
    else:
        raise AssertionError("Stress path extrapolated outside the cylinder wall")
    tampered_path = replace(path)
    object.__setattr__(tampered_path, "hoop_stress_pa", path.hoop_stress_pa.copy())
    try:
        tampered_path.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Stress path accepted a replaced output vector")
    for invalid_index, expected_error in ((True, TypeError), (1.0, TypeError), (-1, ValueError), (2, ValueError)):
        try:
            history.stress_field_at(invalid_index)
        except expected_error:
            continue
        raise AssertionError(f"Invalid exact stress sample index was admitted: {invalid_index!r}")
    changed_sample = replace(sample)
    object.__setattr__(
        changed_sample.stress_field,
        "hoop_stress_pa",
        changed_sample.stress_field.hoop_stress_pa.copy(),
    )
    try:
        changed_sample.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("A stress sample accepted an equal-valued replacement field array")
    assert np.allclose(history.hoop_stress_pa[0], fixed.hoop_stress_pa, rtol=1.0e-9)
    assert np.allclose(
        history.hoop_stress_pa[1], second_reference.hoop_stress_pa, rtol=1.0e-9
    )
    assert not history.hoop_stress_pa.flags.writeable
    try:
        replace(history, von_mises_stress_pa=history.von_mises_stress_pa + 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("An inconsistent history von Mises field was admitted")

    replaced_stress_history = replace(history)
    object.__setattr__(
        replaced_stress_history,
        "hoop_stress_pa",
        replaced_stress_history.hoop_stress_pa.copy(),
    )
    try:
        replaced_stress_history.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Stress history accepted an equal-valued replacement output array")

    detached_profile = replace(profile)
    changed_source_history = replace(
        history,
        temperature_profiles=(detached_profile, second_profile),
    )
    detached_profile.temperature_k.setflags(write=True)
    detached_profile.temperature_k[0] += 0.25
    try:
        changed_source_history.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Stress history accepted a changed nested temperature profile")
    metrics["stress_history_freshness_guard_verified"] = True

    incomplete_profile = RadialTemperatureProfile(
        profile_radii[1:],
        uniform_temperature[1:],
        293.15,
        "incomplete-wall-profile",
        "authored-temperature-profile",
    )
    try:
        radial_thermoelastic_cylinder(
            geometry,
            load,
            incomplete_profile,
            material,
            radii,
            axial_restraint="fixed",
            evidence_id="authored-incomplete-profile-rejection",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A stress solve accepted a profile without the inner wall surface")
    metrics["history_sample_count"] = len(history.time_s)
    metrics["history_sample_bvp_iterations"] = tuple(
        int(value) for value in history.bvp_iterations
    )
    metrics["extracted_sample_index"] = sample.sample_index
    metrics["history_max_bvp_rms_residual"] = float(
        np.max(history.max_bvp_rms_residual)
    )
    metrics["history_max_normalized_boundary_residual"] = float(
        np.max(history.max_normalized_boundary_residual)
    )

    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "elastic_cylinder_radial_thermoelasticity.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Authored numerical reduction checks only; no radial-gradient measurement, "
            "finite-length, yielding, fracture or vessel qualification.",
        ),
    )
