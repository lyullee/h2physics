"""Deferred invariants for transient finite-cylinder radial heat transfer."""

from dataclasses import replace

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="finite-cylinder-radial-heat-transfer",
            profile="thermal-utilities",
            entrypoint=__name__ + ":validate_radial_heat_transfer",
            invariants=(
                "uniform initial condition with adiabatic faces has no heat or temperature drift",
                "prescribed boundary heat matches integrated wall enthalpy change",
                "convection boundaries use caller heat-transfer coefficients and variable properties",
                "radiative boundaries preserve signed wall heat and surface-temperature balance",
                "Dirichlet annulus approaches the analytical logarithmic steady profile",
                "boundary heat ledgers use the positive-into-wall sign at both faces",
                "all result arrays are immutable and the global thermal ledger is finite",
                "solver result receipts cannot be fabricated or modified after issuance",
                "thermal result records reject energy residuals inconsistent with the boundary ledger",
                "sampled thermal field maps to a surface-bounded thermoelastic profile",
                "thermal profile mapping requires a nonblank evidence identity",
                "material and boundary identity fields reject non-string values cleanly",
                "thermal boundary kind rejects non-string selectors explicitly",
                "quasistatic stress results preserve the thermal clock and pressure snapshots",
                "failed stress samples retain the source thermal history and completed prefix",
                "thermomechanical results reject mismatched evidence across heat, profiles and stress history",
                "post-return thermomechanical result rejects changed nested evidence or stress history",
                "material temperature-domain preflight and runtime guards reject out-of-domain calls",
                "radiative callback failure preserves its cause and solver progress boundary",
            ),
        ),
        ValidationCase(
            identifier="finite-sphere-radial-heat-transfer",
            profile="thermal-utilities",
            entrypoint=__name__ + ":validate_spherical_shell_heat_transfer",
            invariants=(
                "spherical cell volumes and areas are used in the finite-volume balance",
                "spherical-wall enthalpy change reconciles with both accepted boundary ledgers",
                "the steady spherical annulus approaches the analytical A+B/r profile",
                "positive boundary heat points into the shell at both radii",
                "material callbacks and thermal boundaries remain caller-owned",
                "no gas coupling, stress or phase-change claim is added",
                "post-solve spherical enthalpy-audit failure retains the native accepted solution and cause",
            ),
        ),
    )


def validate_radial_heat_transfer(*, work_directory, **parameters):
    from h2physics.materials import (
        RadialSolidMaterial,
        RadialThermalBoundary,
        radial_cylinder_heat_history,
    )

    del work_directory, parameters
    material = RadialSolidMaterial(
        7800.0,
        lambda temperature: 500.0,
        lambda temperature: 16.0,
        "authored-carbon-steel",
        "authored-constant-property-diagnostic",
    )
    from h2physics.materials.radial_heat import guard_radial_material_temperature_domain

    bounded_material = guard_radial_material_temperature_domain(
        material, (280.0, 450.0), preflight_samples=7
    )
    assert bounded_material.material_id == material.material_id
    assert bounded_material.evidence_id == material.evidence_id
    assert bounded_material.heat_capacity_j_kg_k(280.0) == 500.0
    assert bounded_material.conductivity_w_m_k(450.0) == 16.0
    try:
        bounded_material.conductivity_w_m_k(279.999)
    except ValueError as error:
        assert "outside its declared" in str(error)
    else:
        raise AssertionError("A bounded material callback extrapolated below its domain")
    invalid_property_material = RadialSolidMaterial(
        7800.0,
        lambda temperature: 500.0,
        lambda temperature: -1.0,
        "authored-invalid-property-material",
        "authored-invalid-property-evidence",
    )
    try:
        guard_radial_material_temperature_domain(
            invalid_property_material, (280.0, 450.0), preflight_samples=7
        )
    except ValueError as error:
        assert "positive" in str(error)
    else:
        raise AssertionError("Preflight admitted a nonpositive conductivity")
    try:
        RadialSolidMaterial(
            7800.0,
            lambda temperature: 500.0,
            lambda temperature: 16.0,
            42,
            "authored-invalid-material-identity",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A non-string material identity was admitted")
    try:
        RadialThermalBoundary("adiabatic", 0.0, 42)
    except ValueError:
        pass
    else:
        raise AssertionError("A non-string boundary evidence identity was admitted")
    try:
        RadialThermalBoundary([], 0.0, "authored-invalid-boundary-kind")
    except ValueError:
        pass
    else:
        raise AssertionError("A non-string boundary kind was admitted")
    adiabatic_inner = RadialThermalBoundary("adiabatic", 0.0, "no-inner-transfer")
    adiabatic_outer = RadialThermalBoundary("adiabatic", 0.0, "no-outer-transfer")
    times = np.linspace(0.0, 60.0, 31)
    closed = radial_cylinder_heat_history(
        0.05,
        0.10,
        1.0,
        material,
        300.0,
        times,
        adiabatic_inner,
        adiabatic_outer,
        cells=24,
        history_id="authored-adiabatic-wall-history",
        clock_id="authored-thermal-clock",
        evidence_id="axisymmetric-radial-heat-equation-diagnostic",
    )
    assert np.allclose(closed.temperature_k, 300.0, rtol=0.0, atol=1e-10)
    assert np.allclose(closed.energy_residual_j, 0.0, rtol=0.0, atol=1e-9)
    try:
        replace(closed)
    except ValueError:
        pass
    else:
        raise AssertionError("A cloned radial solver receipt was admitted")
    original_temperatures = closed.temperature_k
    try:
        object.__setattr__(closed, "temperature_k", original_temperatures + 0.25)
        try:
            closed.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("A changed radial solver receipt remained current")
    finally:
        object.__setattr__(closed, "temperature_k", original_temperatures)
    closed.require_current()

    heated = radial_cylinder_heat_history(
        0.05,
        0.10,
        1.0,
        material,
        300.0,
        times,
        RadialThermalBoundary("heat_flux", 250.0, "authored-inner-flux"),
        adiabatic_outer,
        cells=24,
        history_id="authored-heated-wall-history",
        clock_id="authored-thermal-clock",
        evidence_id="axisymmetric-radial-heat-equation-diagnostic",
    )
    assert np.all(heated.temperature_k[-1] > 300.0)
    assert heated.inner_heat_into_solid_j[-1] > 0.0
    assert np.isclose(
        heated.stored_energy_j[-1] - heated.stored_energy_j[0],
        heated.inner_heat_into_solid_j[-1],
        rtol=2e-6,
        atol=1e-5,
    )
    assert np.max(np.abs(heated.energy_residual_j)) <= 1e-5
    try:
        replace(heated, energy_residual_j=heated.energy_residual_j + 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("An inconsistent thermal energy residual was admitted")

    variable_material = RadialSolidMaterial(
        7800.0,
        lambda temperature: 500.0 + 0.1 * (temperature - 300.0),
        lambda temperature: 16.0 + 0.01 * (temperature - 300.0),
        "authored-variable-property-steel",
        "authored-variable-property-diagnostic",
    )
    convective = radial_cylinder_heat_history(
        0.05,
        0.10,
        1.0,
        variable_material,
        300.0,
        times,
        RadialThermalBoundary(
            "convection",
            340.0,
            "authored-inner-fluid-temperature",
            coefficient=lambda time: 25.0 + 0.1 * time,
        ),
        adiabatic_outer,
        cells=24,
        history_id="authored-convective-wall-history",
        clock_id="authored-thermal-clock",
        evidence_id="axisymmetric-radial-heat-equation-diagnostic",
    )
    assert convective.inner_heat_into_solid_j[-1] > 0.0
    assert convective.inner_surface_temperature_k[-1] > convective.temperature_k[-1, 0]
    assert convective.inner_surface_temperature_k[-1] < 340.0
    assert np.max(np.abs(convective.energy_residual_j)) <= 1e-4

    radiative = radial_cylinder_heat_history(
        0.05,
        0.10,
        1.0,
        material,
        300.0,
        times,
        RadialThermalBoundary(
            "radiation", 450.0, "authored-inner-radiation", coefficient=0.8
        ),
        RadialThermalBoundary(
            "radiation", 150.0, "authored-outer-radiation", coefficient=0.6
        ),
        cells=24,
        history_id="authored-radiative-wall-history",
        clock_id="authored-thermal-clock",
        evidence_id="axisymmetric-radial-heat-equation-diagnostic",
    )
    assert radiative.inner_heat_into_solid_j[-1] > 0.0
    assert radiative.outer_heat_into_solid_j[-1] < 0.0
    assert radiative.inner_surface_temperature_k[-1] < 450.0
    assert radiative.inner_surface_temperature_k[-1] > radiative.temperature_k[-1, 0]
    assert radiative.outer_surface_temperature_k[-1] > 150.0
    assert radiative.outer_surface_temperature_k[-1] < radiative.temperature_k[-1, -1]
    assert np.max(np.abs(radiative.energy_residual_j)) <= 1e-4

    steady_times = np.linspace(0.0, 60_000.0, 61)
    steady = radial_cylinder_heat_history(
        0.05,
        0.10,
        1.0,
        material,
        350.0,
        steady_times,
        RadialThermalBoundary("temperature", 400.0, "authored-inner-temperature"),
        RadialThermalBoundary("temperature", 300.0, "authored-outer-temperature"),
        cells=24,
        history_id="authored-steady-wall-history",
        clock_id="authored-steady-clock",
        evidence_id="axisymmetric-radial-heat-equation-diagnostic",
    )
    analytical = 400.0 + (300.0 - 400.0) * np.log(
        steady.radius_m / 0.05
    ) / np.log(0.10 / 0.05)
    steady_profile_error = float(np.max(np.abs(steady.temperature_k[-1] - analytical)))
    assert steady_profile_error <= 0.1
    assert steady.inner_heat_into_solid_j[-1] > 0.0
    assert steady.outer_heat_into_solid_j[-1] < 0.0
    linked_profile = heated.thermoelastic_profile(
        10,
        reference_temperature_k=293.15,
        profile_evidence_id="authored-thermal-to-elastic-boundary",
    )
    assert linked_profile.radius_m[0] == heated.inner_radius_m
    assert linked_profile.radius_m[-1] == heated.outer_radius_m
    assert linked_profile.temperature_k[1:-1].tolist() == heated.temperature_k[10].tolist()
    assert linked_profile.profile_id == (
        f"{heated.history_id}:sample-10@{heated.time_s[10]:.17g}s"
    )
    try:
        heated.thermoelastic_profile(
            10,
            reference_temperature_k=293.15,
            profile_evidence_id=" ",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A temperature-to-stress profile accepted blank evidence")
    from h2physics.core import Origin
    from h2physics.materials import (
        CylinderGeometry,
        CylinderPressureLoad,
        IsotropicThermoelasticMaterial,
    )

    geometry = CylinderGeometry(0.05, 0.10, "closed", "authored-heated-tank-wall")
    thermoelastic_material = IsotropicThermoelasticMaterial(
        190e9,
        0.29,
        12e-6,
        "authored-carbon-steel",
        "authored-constant-property-diagnostic",
    )
    loads = tuple(
        CylinderPressureLoad(
            8.0e6 + index * 1.0e4,
            1.0e5,
            f"authored-heated-pressure-{index}",
            Origin.SYNTHETIC,
        )
        for index in range(len(heated.time_s))
    )
    coupled = heated.thermoelastic_history(
        loads,
        geometry,
        thermoelastic_material,
        np.linspace(0.05, 0.10, 9),
        reference_temperature_k=293.15,
        axial_restraint="fixed",
        evidence_id="authored-quasistatic-thermal-stress-bridge",
    )
    assert coupled.heat is heated
    assert coupled.history_id == heated.history_id
    assert coupled.clock_id == heated.clock_id
    assert np.array_equal(coupled.stress.time_s, heated.time_s)
    assert coupled.stress.loads == loads
    assert len(coupled.stress.temperature_profiles) == len(heated.time_s)
    assert all(
        profile.profile_id.startswith(f"{heated.history_id}:sample-")
        for profile in coupled.stress.temperature_profiles
    )
    assert all(
        profile.reference_temperature_k == 293.15
        for profile in coupled.stress.temperature_profiles
    )
    assert coupled.require_current() is coupled
    try:
        replace(coupled, evidence_id="tampered-thermomechanical-evidence")
    except ValueError:
        pass
    else:
        raise AssertionError("Thermomechanical wrapper admitted different stress evidence")
    altered_profiles = list(coupled.stress.temperature_profiles)
    altered_profiles[0] = replace(
        altered_profiles[0], evidence_id="tampered-profile-evidence"
    )
    altered_stress = replace(coupled.stress, temperature_profiles=tuple(altered_profiles))
    try:
        replace(coupled, stress=altered_stress)
    except ValueError:
        pass
    else:
        raise AssertionError("Thermomechanical result admitted a profile with detached evidence")
    result_arrays = (
        "time_s",
        "radius_m",
        "temperature_k",
        "inner_heat_into_solid_j",
        "outer_heat_into_solid_j",
        "stored_energy_j",
        "energy_residual_j",
        "inner_surface_temperature_k",
        "outer_surface_temperature_k",
    )
    for result in (closed, heated, convective, radiative, steady):
        for name in result_arrays:
            assert not getattr(result, name).flags.writeable
    from h2physics.materials import RadialThermomechanicalHistoryError

    try:
        heated.thermoelastic_history(
            loads,
            geometry,
            thermoelastic_material,
            np.array([0.10, 0.05]),
            reference_temperature_k=293.15,
            axial_restraint="fixed",
            evidence_id="authored-failure-prefix-retention",
        )
    except RadialThermomechanicalHistoryError as error:
        assert error.heat_history is heated
        assert error.failed_index == 0
        assert len(error.completed_stress_fields) == 0
        assert isinstance(error.cause, (ValueError, RuntimeError))
    else:
        raise AssertionError("A malformed pressure sample was silently admitted")

    original_stress_evidence = coupled.stress.evidence_id
    object.__setattr__(coupled.stress, "evidence_id", "tampered-after-issue")
    try:
        coupled.require_current()
    except ValueError:
        changed_post_return_history_rejected = True
    else:
        raise AssertionError("Changed thermomechanical history was admitted after issue")
    finally:
        object.__setattr__(coupled.stress, "evidence_id", original_stress_evidence)

    from h2physics.materials import RadialHeatIntegrationError

    try:
        radial_cylinder_heat_history(
            0.05,
            0.10,
            1.0,
            material,
            300.0,
            times[:2],
            RadialThermalBoundary(
                "radiation",
                450.0,
                "authored-invalid-emissivity",
                coefficient=lambda time: 1.1,
            ),
            adiabatic_outer,
            cells=8,
            history_id="authored-invalid-radiative-wall-history",
            clock_id="authored-thermal-clock",
            evidence_id="axisymmetric-radial-heat-equation-diagnostic",
        )
    except RadialHeatIntegrationError as error:
        assert isinstance(error.cause, ValueError)
        assert error.native_solution is None
    else:
        raise AssertionError("An out-of-domain radiative coefficient was admitted")
    return ValidationOutcome(
        accepted=True,
        metrics={
            "adiabatic_temperature_span_k": float(np.ptp(closed.temperature_k)),
            "heat_input_j": float(heated.inner_heat_into_solid_j[-1]),
            "stored_energy_change_j": float(
                heated.stored_energy_j[-1] - heated.stored_energy_j[0]
            ),
            "convection_heat_into_wall_j": float(convective.inner_heat_into_solid_j[-1]),
            "radiation_net_heat_into_wall_j": float(
                radiative.inner_heat_into_solid_j[-1]
                + radiative.outer_heat_into_solid_j[-1]
            ),
            "maximum_energy_residual_j": float(np.max(np.abs(heated.energy_residual_j))),
            "steady_log_profile_max_error_k": steady_profile_error,
            "thermoelastic_profile_node_count": len(linked_profile.radius_m),
            "thermomechanical_history_sample_count": len(coupled.stress.time_s),
            "changed_post_return_history_rejected": changed_post_return_history_rejected,
            "radial_cells": len(heated.radius_m),
        },
        limitations=(
            "Authored numerical conservation checks only; no measured wall-temperature history, "
            "temperature-dependent material qualification, phase change, axial conduction or "
            "fluid/solid coupling.",
        ),
    )


def validate_spherical_shell_heat_transfer(*, work_directory, **parameters):
    from h2physics.materials import (
        RadialSolidMaterial, RadialThermalBoundary, spherical_shell_heat_history,
    )

    del work_directory, parameters
    inner, outer = .045, .05
    material = RadialSolidMaterial(
        7800.0, lambda temperature: 500.0, lambda temperature: 2.0,
        "authored-spherical-shell", "authored-thermal-demo",
    )
    result = spherical_shell_heat_history(
        inner, outer, material, 350.0, np.linspace(0.0, 2000.0, 101),
        RadialThermalBoundary("temperature", 400.0, "authored-inner-temperature"),
        RadialThermalBoundary("temperature", 300.0, "authored-outer-temperature"),
        cells=24, maximum_step_s=2.0, history_id="authored-spherical-shell-run",
        clock_id="authored-spherical-shell-clock",
        evidence_id="spherical-radial-heat-equation",
    )
    steady_b = (400.0-300.0)/(1.0/inner-1.0/outer)
    steady_a = 400.0-steady_b/inner
    expected = steady_a+steady_b/result.radius_m
    profile_error = float(np.max(np.abs(result.temperature_k[-1]-expected)))
    residual = float(np.max(np.abs(result.energy_residual_j)))
    if profile_error > 0.5:
        raise AssertionError("Long-time spherical temperature differs from the A+B/r solution")
    if residual > 1e-4:
        raise AssertionError("Spherical wall heat ledger does not close at reported samples")
    if result.inner_heat_into_solid_j[-1] <= 0 or result.outer_heat_into_solid_j[-1] >= 0:
        raise AssertionError("Spherical boundary sign convention is not positive into the solid")
    from unittest.mock import patch

    from h2physics.materials.spherical_heat import SphericalShellHeatIntegrationError

    postprocess_failure = RuntimeError("authored-spherical-enthalpy-audit-failure")
    try:
        with patch("h2physics.materials.spherical_heat.quad", side_effect=postprocess_failure):
            spherical_shell_heat_history(
                inner, outer, material, 350.0, np.array([0.0, 0.01, 0.02]),
                RadialThermalBoundary("adiabatic", 0.0, "authored-inner-adiabatic"),
                RadialThermalBoundary("adiabatic", 0.0, "authored-outer-adiabatic"),
                cells=3, history_id="authored-failed-postprocess",
                clock_id="authored-spherical-shell-clock",
                evidence_id="spherical-radial-heat-equation",
            )
    except SphericalShellHeatIntegrationError as error:
        if (error.cause is not postprocess_failure or error.__cause__ is not postprocess_failure
                or error.native_solution is None or not error.native_solution.success
                or error.native_solution.t.size < 2):
            raise AssertionError("Post-solve failure did not retain the native accepted solution")
    else:
        raise AssertionError("Injected post-solve enthalpy failure was not preserved")
    return ValidationOutcome(
        accepted=True,
        metrics={"cells": len(result.radius_m), "maximum_energy_residual_j": residual,
                 "steady_profile_error_k": profile_error,
                 "postsolve_failure_retained_native_prefix": True},
        limitations=("Authored homogeneous-material reference only; no cryogenic vessel qualification",),
    )
