"""Deferred schema/provenance checks for the Zenodo excess-adsorption table reader."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

EXPECTED_SHA256 = "40c16cca5099e2c69dc44aceb43300854307b3a6c8351c43013afc9967e60dc6"


def cases():
    return (
        ValidationCase(
            identifier="geological-adsorption-excess-loader",
            profile="adsorption-data",
            entrypoint=__name__ + ":validate_source_loader",
            invariants=(
                "the latest Zenodo archive DOI, CC BY 4.0 identity, and SHA-256 are retained",
                "all four source material tables expose six data rows with pressure, temperature, signed excess loading, uncertainty and detection fields",
                "source row and every original CSV field remain available without extracting the archive",
                "signed excess observations explicitly reject absolute-uptake use",
                "the bounded provider preserves surface-excess basis and interpolates only inside one measured isotherm",
                "provider values and retained row identities reproduce the loader-issued source isotherm exactly",
                "dataclass replacement cannot reseal provider values that diverge from source rows",
                "weighted source-row loadings reconstruct the exact signed-excess site value",
                "source-bound isotherms can only be issued by the checksum-validating archive loader",
                "direct construction and dataclass replacement cannot claim pinned provenance for altered rows",
                "site receipts retain source-row interpolation weights and reported uncertainty/LOD/LLOQ as immutable unit-bearing Python objects",
                "invalid receipt values and per-site weights that do not sum to one are rejected",
                "temperature, pressure and multicomponent extrapolation are explicitly rejected",
                "the absolute-uptake-only finite-vessel owner rejects the excess provider",
                "no adsorption fit, conversion, bed, or vessel validation is inferred",
            ),
        ),
    )


def validate_source_loader(*, work_directory):
    import os
    from pathlib import Path

    import numpy as np

    from h2physics import AdsorptionSourceObservation
    from h2physics.data.geological_adsorption import (
        GeologicalAdsorptionIsotherm,
        load_geological_adsorption_isotherm,
    )

    raw_root = os.environ.get("H2_CLUSTER_DATA_RAW_ROOT")
    if not raw_root or not Path(raw_root).is_absolute():
        raise ValueError("Supply an absolute cluster raw-data snapshot root")
    archive = Path(raw_root) / "geological-adsorption" / "zenodo-22305898" / "submission_package.zip"
    expected_rows = {"cox": 6, "kunipia": 6, "laponite": 6, "mof177": 6}
    for material, count in expected_rows.items():
        table = load_geological_adsorption_isotherm(archive, material)
        assert table.source_sha256 == EXPECTED_SHA256
        assert table.source_doi == "10.5281/zenodo.22305898"
        assert table.license_id == "CC-BY-4.0"
        assert table.uptake_basis == "signed_excess"
        assert len(table.points) == count
        assert tuple(point.source_row for point in table.points) == tuple(range(2, count + 2))
        assert all(point.pressure_bar > 0.0 and point.temperature_k > 0.0 for point in table.points)
        assert all(point.source_fields for point in table.points)
        direct_constructor_rejected = False
        try:
            GeologicalAdsorptionIsotherm(
                table.material_id, table.source_file, table.source_sha256,
                table.source_doi, table.license_id, table.points,
            )
        except ValueError:
            direct_constructor_rejected = True
        assert direct_constructor_rejected
        from dataclasses import replace

        forged_point = replace(
            table.points[0],
            signed_excess_loading_mmol_per_g=table.points[0].signed_excess_loading_mmol_per_g + 1.,
        )
        forged_rows_rejected = False
        try:
            replace(table, points=(forged_point, *table.points[1:]))
        except ValueError:
            forged_rows_rejected = True
        assert forged_rows_rejected
        try:
            table.require_absolute_uptake()
        except ValueError:
            pass
        else:
            raise AssertionError("Excess uptake must not be accepted as absolute uptake")

    measured = load_geological_adsorption_isotherm(archive, "mof177")
    provider = measured.surface_excess_provider(
        temperature_k=measured.points[0].temperature_k,
    )
    assert provider.basis.loading_definition == "surface_excess"
    forged_loading = provider.excess_loading_mol_kg.copy()
    forged_loading[0] += 1.
    provider_forgery_rejected = False
    try:
        replace(provider, excess_loading_mol_kg=forged_loading)
    except ValueError:
        provider_forgery_rejected = True
    assert provider_forgery_rejected
    pressure = (provider.pressure_pa[0] + provider.pressure_pa[-1]) / 2.0
    state = provider.equilibrium([pressure], provider.temperature_k)
    assert state.basis.loading_definition == "surface_excess"
    assert len(state.source_observations) == 1
    assert sum(item.interpolation_weight for item in state.source_observations[0]) == 1.0
    assert all(item.source_row >= 2 for item in state.source_observations[0])
    source_by_row = {point.source_row: point for point in measured.points}
    reconstructed_loading = 0.0
    for item in state.source_observations[0]:
        point = source_by_row[item.source_row]
        assert item.species == "H2"
        assert item.source_loading_mol_kg == point.signed_excess_loading_mmol_per_g
        reconstructed_loading += item.interpolation_weight*item.source_loading_mol_kg
        assert item.standard_uncertainty_mol_kg == point.total_standard_uncertainty_mmol_per_g
        assert item.detection_limit_mol_kg == point.detection_limit_mmol_per_g
        assert item.quantification_limit_mol_kg == point.quantification_limit_mmol_per_g
    try:
        state.source_observations[0][0].interpolation_weight = 0.5
    except AttributeError:
        pass
    else:
        raise AssertionError("Adsorption source receipts must be immutable")
    assert np.isclose(reconstructed_loading, state.site_loadings_mol_kg[0, 0],
                      rtol=1e-12, atol=1e-12)
    for values in (
        ("H2", True, 1.0, 0.0, None, None, None),
        ("H2", 2, float("nan"), 0.0, None, None, None),
        ("H2", 2, 1.0, float("nan"), None, None, None),
        ("H2", 2, 1.0, 0.0, -1.0, None, None),
    ):
        try:
            AdsorptionSourceObservation(*values)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid source observation receipt was admitted")
    try:
        replace(state, source_observations=((
            AdsorptionSourceObservation(
                species="H2", source_row=2, interpolation_weight=0.2,
                source_loading_mol_kg=0.,
            ),
        ),))
    except ValueError:
        pass
    else:
        raise AssertionError("Per-site source weights that do not sum to one were admitted")
    try:
        replace(state, source_observations=((
            AdsorptionSourceObservation(
                species="H2", source_row=2, interpolation_weight=0.5,
                source_loading_mol_kg=float(state.site_loadings_mol_kg[0, 0]),
            ),
            AdsorptionSourceObservation(
                species="H2", source_row=2, interpolation_weight=0.5,
                source_loading_mol_kg=float(state.site_loadings_mol_kg[0, 0]),
            ),
        ),))
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate source rows were admitted for one adsorption site")
    # Source uncertainty and reporting limits stay attached to their source rows;
    # no independence assumption or derived combined uncertainty is introduced.
    try:
        provider.equilibrium([provider.pressure_pa[-1] * 1.01], provider.temperature_k)
    except ValueError:
        pass
    else:
        raise AssertionError("Surface-excess provider extrapolated pressure")
    try:
        provider.equilibrium([pressure], provider.temperature_k + 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("Surface-excess provider interpolated temperature")
    try:
        provider.equilibrium([pressure, pressure], provider.temperature_k)
    except ValueError:
        pass
    else:
        raise AssertionError("Single-component provider admitted a mixture")

    from h2physics.adapters.finite_adsorption_vessel import (
        AdsorptionVesselGeometry,
        FiniteAdsorptionVessel,
        FrozenGasBinding,
    )
    try:
        FiniteAdsorptionVessel(
            vessel_id="excess-data-rejection",
            geometry=AdsorptionVesselGeometry(1.0, 1.0, 0.1, 0.1, "synthetic"),
            adsorption=provider,
            gas=FrozenGasBinding.__new__(FrozenGasBinding),
        )
    except ValueError as error:
        assert "absolute uptake" in str(error)
    else:
        raise AssertionError("Absolute-uptake-only vessel admitted measured surface excess")

    return ValidationOutcome(
        accepted=True,
        metrics={"material_tables": len(expected_rows), "data_rows_per_table": 6},
        limitations=(
            "Schema/provenance ingestion only. This source reports excess loading and does not validate absolute capacity or a vessel model.",
            "The Zenodo CC BY 4.0 dataset and DOI are pinned in the source receipt.",
        ),
    )
