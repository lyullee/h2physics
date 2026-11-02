"""Deferred accepted compressor discharge to finite release-source contract."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="compressor-discharge-finite-release-source-handoff",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_source",
        invariants=(
            "source-state-is-exact-owner-replayed-compressor-discharge-state",
            "caller-release-flow-is-explicit-and-no-greater-than-compressor-throughput",
            "explicit-source-window-and-location-clock-define-the-finite-support",
            "released-mass-and-enthalpy-equal-native-interval-source-ledgers",
            "time-flow-state-and-origin-evidence-remain-bound-to-the-source-receipt",
            "direct-reissuance-is-rejected-and-source-payload-is-current",
            "no-opening-size-nozzle-flow-or-dispersion-is-inferred",
        ),
    ),)


def validate_source(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.compressor_discharge_source import (
        bind_compressor_discharge_source,
    )
    from h2physics.combustion.fuel_compression import run_real_fluid_hydrogen_compression
    from h2physics.core import Origin
    from h2physics.release import SourceLocation
    from h2physics.thermo import CoolPropProperties
    from validation.cases.hydrogen_fuel_compression import _real_fluid_inputs

    provider = CoolPropProperties("Hydrogen", backend="HEOS")
    compressor = run_real_fluid_hydrogen_compression(
        provider, _real_fluid_inputs(
            process_window_id="steady-compressor-discharge-release-window",
            state_evidence_id="authored-compressor-state-boundary",
            efficiency_evidence_id="authored-compressor-efficiency",
            domain_evidence_id="authored-compressor-domain",
        ),
    )
    location = SourceLocation(
        "authored-compressor-leak", "authored-release-clock",
        "authored-plant-coordinate-frame", (1., 0., 2.), (1., 0., 0.),
    )
    receipt = bind_compressor_discharge_source(
        compressor, location=location, start_time_s=10., end_time_s=11.,
        release_mass_flow_kg_s=.01, origin=Origin.SYNTHETIC,
        time_mapping_evidence_id="authored-process-window-to-release-clock",
        release_flow_evidence_id="authored-throughflow-leak-boundary",
    )
    assert receipt.require_current() is receipt
    assert receipt.source.location is location
    assert receipt.source.state is receipt.state
    assert receipt.source.edges_s.tolist() == [10., 11.]
    assert receipt.source.mass_kg.tolist() == [.01]
    assert receipt.source.total_mass_kg == receipt.released_mass_kg
    assert receipt.source.enthalpy_transfer_j == receipt.released_enthalpy_j
    assert receipt.compressor_throughput_kg_s == compressor.inputs.hydrogen_mass_flow_kg_s

    overdraw_rejected = False
    try:
        bind_compressor_discharge_source(
            compressor, location=location, start_time_s=10., end_time_s=11.,
            release_mass_flow_kg_s=compressor.inputs.hydrogen_mass_flow_kg_s+1e-6,
            origin=Origin.SYNTHETIC,
            time_mapping_evidence_id="authored-overdraw-clock-map",
            release_flow_evidence_id="authored-impossible-leak-flow",
        )
    except ValueError:
        overdraw_rejected = True
    assert overdraw_rejected

    direct_reissue_rejected = False
    try:
        replace(receipt)
    except TypeError:
        direct_reissue_rejected = True
    assert direct_reissue_rejected
    return ValidationOutcome(True, {
        "compressor_process_window_id": compressor.inputs.process_window_id,
        "source_window_s": (float(receipt.source.edges_s[0]),
                            float(receipt.source.edges_s[-1])),
        "compressor_throughput_kg_s": receipt.compressor_throughput_kg_s,
        "declared_release_flow_kg_s": receipt.release_mass_flow_kg_s,
        "released_mass_kg": receipt.released_mass_kg,
        "outlet_pressure_pa": compressor.actual_outlet.pressure_pa,
        "outlet_temperature_k": compressor.actual_outlet.temperature_k,
        "released_enthalpy_j": receipt.released_enthalpy_j,
        "overdraw_rejected": overdraw_rejected,
        "direct_reissue_rejected": direct_reissue_rejected,
    }, (
        "The caller supplies a bounded throughflow leak rate; no leak aperture or flow law is validated.",
        "The finite source is ready for existing downstream source consumers; no dispersion or consequence run is performed here.",
    ))
