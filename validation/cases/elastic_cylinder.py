"""Deferred checks for the elastic pressure-cylinder stress reference."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="elastic-cylinder-pressure-boundaries",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_boundaries",
            invariants=(
                "actual package stress-field API",
                "radial boundary tractions match pressure signs",
                "closed/open end condition distinction",
                "caller-visible von Mises principal-stress invariant",
                "returned field arrays are immutable and constructed Von Mises values are consistent",
            ),
        ),
        ValidationCase(
            identifier="elastic-cylinder-pressure-samples",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_pressure_samples",
            invariants=(
                "one stress tensor field per ordered pressure sample",
                "linear superposition with pressure difference",
                "immutable (time,radius) result arrays",
                "no inter-sample interpolation",
            ),
        ),
        ValidationCase(
            identifier="elastic-cylinder-uniform-thermoelasticity",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_uniform_thermoelasticity",
            invariants=(
                "free uniform temperature change adds no thermal stress",
                "fixed axial strain satisfies isotropic constitutive compatibility",
                "fixed-end support reaction closes axial force balance",
                "thermal and pressure contributions combine in von Mises stress",
            ),
        ),
    )


def validate_boundaries(*, work_directory, **parameters):
    from h2physics.core import Origin
    from h2physics.materials.elastic_cylinder import (
        CylinderGeometry,
        CylinderPressureLoad,
        lame_stress_field,
    )

    radii = np.array([0.08, 0.12, 0.16])
    geometry = CylinderGeometry(0.08, 0.16, "closed", "authored-thick-shell")
    load = CylinderPressureLoad(8.0e6, 1.0e5, "authored-pressure-span", Origin.SYNTHETIC)
    result = lame_stress_field(geometry, load, radii, evidence_id="Cambridge-Lame-reference")
    assert all(
        not getattr(result, name).flags.writeable
        for name in (
            "radius_m", "radial_stress_pa", "hoop_stress_pa",
            "axial_stress_pa", "von_mises_stress_pa",
        )
    )
    try:
        replace(result, von_mises_stress_pa=result.von_mises_stress_pa + 1.0)
    except ValueError:
        inconsistent_field_rejected = True
    else:
        raise AssertionError("An inconsistent constructed stress field was admitted")

    ri, ro = geometry.inner_radius_m, geometry.outer_radius_m
    pi, po = load.internal_pressure_pa, load.external_pressure_pa
    a_term = (pi * ri**2 - po * ro**2) / (ro**2 - ri**2)
    b_term = (pi - po) * ri**2 * ro**2 / (ro**2 - ri**2)
    assert np.isclose(result.radial_stress_pa[0], -pi, rtol=1e-13, atol=1e-7)
    assert np.isclose(result.radial_stress_pa[-1], -po, rtol=1e-13, atol=1e-7)
    assert np.allclose(result.hoop_stress_pa, a_term + b_term / radii**2, rtol=1e-13)
    assert np.all(result.axial_stress_pa == a_term)
    expected_vm = np.sqrt(
        0.5
        * (
            (result.hoop_stress_pa - result.radial_stress_pa) ** 2
            + (result.radial_stress_pa - a_term) ** 2
            + (a_term - result.hoop_stress_pa) ** 2
        )
    )
    assert np.allclose(result.von_mises_stress_pa, expected_vm, rtol=1e-13)
    open_end = CylinderGeometry(ri, ro, "open", "authored-open-shell")
    opened = lame_stress_field(open_end, load, radii, evidence_id="Cambridge-Lame-reference")
    assert np.all(opened.axial_stress_pa == 0.0)
    scalar = lame_stress_field(geometry, load, ri, evidence_id="Cambridge-Lame-reference")
    assert scalar.radius_m.shape == scalar.von_mises_stress_pa.shape == (1,)
    assert scalar.radial_stress_pa[0] == result.radial_stress_pa[0]

    metrics = {
        "inner_radial_stress_pa": float(result.radial_stress_pa[0]),
        "outer_radial_stress_pa": float(result.radial_stress_pa[-1]),
        "inner_hoop_stress_pa": float(result.hoop_stress_pa[0]),
        "closed_end_axial_stress_pa": float(result.axial_stress_pa[0]),
        "open_end_axial_stress_pa": float(opened.axial_stress_pa[0]),
        "inconsistent_constructed_stress_field_rejected": inconsistent_field_rejected,
    }
    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "elastic_cylinder.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Linear elastic pressure-only axisymmetric field; no end effects, thermal/residual stress, yielding, crack initiation or measured vessel qualification.",
        ),
    )


def validate_pressure_samples(*, work_directory, **parameters):
    from h2physics.core import Origin
    from h2physics.materials.elastic_cylinder import (
        CylinderGeometry,
        CylinderPressureLoad,
        lame_stress_samples,
    )

    geometry = CylinderGeometry(0.08, 0.16, "closed", "authored-pressure-series")
    loads = (
        CylinderPressureLoad(1.0e6, 1.0e5, "sample-low", Origin.SYNTHETIC),
        CylinderPressureLoad(8.0e6, 1.0e5, "sample-high", Origin.SYNTHETIC),
        CylinderPressureLoad(2.0e6, 1.0e5, "sample-return", Origin.SYNTHETIC),
    )
    result = lame_stress_samples(
        geometry,
        [0.0, 5.0, 9.0],
        loads,
        [0.08, 0.12, 0.16],
        evidence_id="authored-Lame-pressure-sample-check",
        clock_id="authored-pressure-clock",
    )
    assert result.hoop_stress_pa.shape == (3, 3)
    assert result.axial_stress_pa.shape == (3, 3)
    assert np.allclose(
        result.hoop_stress_pa[1] - result.hoop_stress_pa[0],
        7.0 * (result.hoop_stress_pa[2] - result.hoop_stress_pa[0]),
    )
    assert np.allclose(result.radial_stress_pa[:, 0], [-1e6, -8e6, -2e6])
    assert np.allclose(result.radial_stress_pa[:, -1], -1e5)
    try:
        result.hoop_stress_pa[0, 0] = 0.0
    except ValueError:
        pass
    else:
        raise AssertionError("Returned stress series must be immutable")

    metrics = {
        "sample_count": len(result.time_s),
        "radial_point_count": len(result.radius_m),
        "peak_sampled_von_mises_pa": float(np.max(result.von_mises_stress_pa)),
    }
    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "elastic_cylinder_samples.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Only supplied pressure/time samples are evaluated; no inter-sample peak, fatigue damage, thermal stress, yielding, crack response, or vessel qualification is inferred.",
        ),
    )


def validate_uniform_thermoelasticity(*, work_directory, **parameters):
    from h2physics.core import Origin
    from h2physics.materials.elastic_cylinder import (
        CylinderGeometry,
        CylinderPressureLoad,
        IsotropicThermoelasticMaterial,
        UniformCylinderTemperature,
        thermoelastic_lame_stress_field,
    )

    geometry = CylinderGeometry(0.08, 0.16, "closed", "uniform-thermal-shell")
    load = CylinderPressureLoad(8.0e6, 1.0e5, "pressure-span", Origin.SYNTHETIC)
    material = IsotropicThermoelasticMaterial(
        200.0e9,
        0.30,
        12.0e-6,
        "authored-isotropic-elastic-material",
        "authored-material-property-evidence",
    )
    radii = [0.08, 0.12, 0.16]
    free = thermoelastic_lame_stress_field(
        geometry,
        load,
        radii,
        material,
        UniformCylinderTemperature(
            293.15, 393.15, "free", "free-expansion", "authored-temperature-evidence"
        ),
        evidence_id="authored-uniform-thermoelasticity-reference",
    )
    pressure_only = thermoelastic_lame_stress_field(
        geometry,
        load,
        radii,
        material,
        UniformCylinderTemperature(
            293.15, 293.15, "free", "reference-state", "authored-temperature-evidence"
        ),
        evidence_id="authored-uniform-thermoelasticity-reference",
    )
    assert np.allclose(free.radial_stress_pa, pressure_only.radial_stress_pa)
    assert np.allclose(free.hoop_stress_pa, pressure_only.hoop_stress_pa)
    assert np.allclose(free.axial_stress_pa, pressure_only.axial_stress_pa)
    assert free.axial_support_reaction_n == 0.0

    fixed = thermoelastic_lame_stress_field(
        geometry,
        load,
        radii,
        material,
        UniformCylinderTemperature(
            293.15, 393.15, "fixed", "fixed-supports", "authored-temperature-evidence"
        ),
        evidence_id="authored-uniform-thermoelasticity-reference",
    )
    ri, ro = geometry.inner_radius_m, geometry.outer_radius_m
    a_term = (load.internal_pressure_pa * ri**2 - load.external_pressure_pa * ro**2) / (
        ro**2 - ri**2
    )
    expected_axial = (
        2 * material.poisson_ratio * a_term
        - material.young_modulus_pa
        * material.linear_expansion_per_k
        * (393.15 - 293.15)
    )
    assert np.allclose(fixed.axial_stress_pa, expected_axial, rtol=1e-14)
    axial_strain = (
        fixed.axial_stress_pa
        - material.poisson_ratio * (fixed.radial_stress_pa + fixed.hoop_stress_pa)
    ) / material.young_modulus_pa + material.linear_expansion_per_k * (393.15 - 293.15)
    assert np.allclose(axial_strain, 0.0, atol=1e-15)
    wall_area = np.pi * (ro**2 - ri**2)
    cap_thrust = np.pi * (
        load.internal_pressure_pa * ri**2 - load.external_pressure_pa * ro**2
    )
    assert np.isclose(
        fixed.axial_support_reaction_n,
        expected_axial * wall_area - cap_thrust,
        rtol=1e-14,
    )
    expected_vm = np.sqrt(
        0.5
        * (
            (fixed.hoop_stress_pa - fixed.radial_stress_pa) ** 2
            + (fixed.radial_stress_pa - fixed.axial_stress_pa) ** 2
            + (fixed.axial_stress_pa - fixed.hoop_stress_pa) ** 2
        )
    )
    assert np.allclose(fixed.von_mises_stress_pa, expected_vm, rtol=1e-14)

    metrics = {
        "free_axial_stress_pa": float(free.axial_stress_pa[0]),
        "fixed_axial_stress_pa": float(fixed.axial_stress_pa[0]),
        "fixed_support_reaction_n": fixed.axial_support_reaction_n,
    }
    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "elastic_cylinder_thermoelasticity.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Uniform-temperature, homogeneous isotropic, linear-elastic cylinder only; no "
            "radial temperature gradient, finite-end stress, yielding, fatigue, crack "
            "response or vessel qualification.",
        ),
    )
