"""Deferred contract for caller-parameterized hydrogen surface-film transfer."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydrogen-diffusion-surface-film-boundary",
        profile="material-transport",
        entrypoint=__name__ + ":validate_surface_film",
        invariants=(
            "film transfer uses explicitly supplied same-carrier solid-basis concentration and m/s coefficient",
            "half-cell solid diffusion resistance and film resistance combine in series at each wall face",
            "left and right oriented transfer rates preserve the global inventory ledger",
            "zero film coefficient isolates the wall while large film coefficient tends to the prescribed-concentration boundary",
            "temperature/time callbacks and evidence identity remain caller-owned",
            "no gas fugacity, surface kinetics, hydrogen solubility, or coefficient is inferred",
        ),
    ),)


def validate_surface_film(*, work_directory, **parameters):
    from math import isclose

    import numpy as np

    from h2physics.materials import (
        DiffusionDomain,
        DiffusionMesh,
        HydrogenCarrier,
        SurfaceFilmCondition,
        TransportBoundary,
    )

    del work_directory, parameters
    length = 0.01
    diffusivity = 2e-9
    left_bulk, right_bulk = 5.0, 1.0
    left_velocity, right_velocity = 4e-6, 2e-6
    mesh = DiffusionMesh.planar(length, 12)
    flux = (left_bulk-right_bulk) / (
        1/left_velocity + length/diffusivity + 1/right_velocity
    )
    # Exact steady linear profile for the continuum film + bulk resistances.
    centers = mesh.cell_centers_m
    initial = left_bulk - flux/left_velocity - flux*centers/diffusivity
    def boundary(time):
        return TransportBoundary(
            SurfaceFilmCondition(left_bulk, left_velocity, "synthetic-left-film"),
            SurfaceFilmCondition(right_bulk, right_velocity, "synthetic-right-film"),
        )
    result = DiffusionDomain(
        HydrogenCarrier("atomic_hydrogen", 1.008e-3), mesh,
        lambda temperature: diffusivity,
    ).simulate(
        [0., 1., 10.], initial, boundary=boundary,
        temperature_k=lambda time: 298.15,
        relative_tolerance=2e-10, absolute_tolerance_mol_m3=1e-12,
    )
    result.require_current()
    if not np.allclose(result.mobile_mol_m3, initial[None, :], rtol=2e-8, atol=2e-10):
        raise AssertionError("The continuum steady film-diffusion profile drifted")
    expected = flux * (result.time_s-result.time_s[0]) * mesh.face_areas_m2[0]
    if not np.allclose(result.left_integrated_mol, expected, rtol=2e-8, atol=1e-14):
        raise AssertionError("Left film flux disagrees with the series-resistance solution")
    if not np.allclose(result.right_integrated_mol, expected, rtol=2e-8, atol=1e-14):
        raise AssertionError("Right film flux disagrees with the series-resistance solution")
    if not np.allclose(result.total_residual_mol, 0., atol=2e-13):
        raise AssertionError("Film-driven diffusion failed the global inventory ledger")

    isolated = SurfaceFilmCondition(2.0, 0.0, "zero-film-velocity").at(0., 298.15)
    if isolated != (2., 0.):
        raise AssertionError("Zero transfer velocity must be a valid no-flux surface")
    limiting_profile = mesh.steady_concentration_profile_mol_m3(left_bulk, right_bulk)
    def limiting_boundary(time):
        return TransportBoundary(
            SurfaceFilmCondition(left_bulk, 1e6, "large-left-film-velocity"),
            SurfaceFilmCondition(right_bulk, 1e6, "large-right-film-velocity"),
        )
    limiting = DiffusionDomain(
        HydrogenCarrier("atomic_hydrogen", 1.008e-3), mesh,
        lambda temperature: diffusivity,
    ).simulate(
        [0., 1.], limiting_profile, boundary=limiting_boundary,
        temperature_k=lambda time: 298.15,
        relative_tolerance=2e-10, absolute_tolerance_mol_m3=1e-12,
    )
    limiting.require_current()
    dirichlet_rate = diffusivity * (left_bulk-right_bulk) / length
    limiting_rate = limiting.left_integrated_mol[-1] / (
        (limiting.time_s[-1]-limiting.time_s[0]) * mesh.face_areas_m2[0]
    )
    if not isclose(limiting_rate, dirichlet_rate, rel_tol=2e-5, abs_tol=1e-14):
        raise AssertionError("Large film velocity did not approach prescribed-concentration transport")
    return ValidationOutcome(True, {
        "steady_flux_mol_m2_s": flux,
        "film_velocities_m_s": (left_velocity, right_velocity),
        "global_inventory_residual_mol": float(np.max(np.abs(result.total_residual_mol))),
        "zero_transfer_velocity_admitted": True,
    }, (
        "Synthetic coefficients exercise the boundary and ledger only; surface kinetics and material coefficients remain unqualified.",
    ))
