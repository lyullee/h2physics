"""Metadata-only contract for exact preferred-provider receptor-grid sampling."""

from inspect import signature

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="preferred-dispersion-exact-receptor-grid-contract",
        profile="preferred-dispersion",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "finite 3D H2 mole-fraction grid is tied to the original provider result",
            "caller must declare provider family and source domain",
            "receptor sampling requires exact coordinate membership and matching frame/clock",
            "grid export and steady-window applicability evidence are explicit",
            "metadata inspection performs no scientific provider or field evaluation",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.preferred_dispersion_grid import (
        PreferredDispersionConcentrationGrid,
        sample_preferred_dispersion_receptor_exact,
    )

    grid_fields = PreferredDispersionConcentrationGrid.__dataclass_fields__
    required_grid = {
        "handoff", "provider_result", "x_m", "y_m", "z_m", "h2_mole_fraction",
        "frame_id", "clock_id", "grid_evidence_id", "steady_window_evidence_id",
    }
    if not required_grid.issubset(grid_fields):
        raise AssertionError("Typed provider-grid identity, axes, units or evidence fields are missing")
    sample_parameters = signature(sample_preferred_dispersion_receptor_exact).parameters
    required_sample = {
        "grid", "receptor", "expected_family", "expected_source_domain_id",
        "receptor_mapping_evidence_id",
    }
    if not required_sample.issubset(sample_parameters):
        raise AssertionError("Exact sampler does not expose the required caller declarations")
    return ValidationOutcome(True, {
        "metadata_contract": "passed",
        "exact_sampler": sample_preferred_dispersion_receptor_exact.__name__,
        "grid_type": PreferredDispersionConcentrationGrid.__name__,
        "science_execution_performed": False,
    }, (
        "Metadata-only API contract; no native result or concentration grid was sampled",
        "No plume or detector validation is established",
    ))
