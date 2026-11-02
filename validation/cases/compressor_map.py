"""Deferred compressor-map cases."""

import importlib

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    definitions = (
        ("compressor-map-correction", "validate_correction", ("absolute inlet basis", "corrected coordinates")),
        ("compressor-map-interpolation", "validate_interpolation", ("bounded speed interpolation",)),
        ("compressor-map-no-extrapolation", "validate_no_extrapolation", ("speed domain guard",)),
        ("compressor-map-operating-limits", "validate_operating_limits", ("flow/ratio/efficiency gates",)),
        ("compressor-map-schedule", "validate_schedule", ("explicit startup clock", "ideal isolation")),
        ("compressor-map-original-result", "validate_original_result", ("native result binding", "stale owner rejection")),
        ("turbine-map-pairing-receipt", "validate_turbine_map_pairing", (
            "pinned-lh2dt-compressor-trace", "source-hashed-turbine-map", "explicit-clock-and-basis-links",
            "original-map-evidence-retained", "compressor-trace-currentness-rechecked", "no-inferred-shaft-or-energy-closure",
        )),
    )
    return tuple(ValidationCase(identifier=name, profile="compressor-map",
        entrypoint=__name__+":"+entry,
        parameters=({
            "fixture_module": "REPLACE_WITH_LH2DT_TURBINE_MAP_PAIRING_FIXTURE_MODULE",
            "fixture_builder": "build_turbine_map_pairing_fixture",
            "turbine_map_source_uri": "REPLACE_WITH_REVIEWED_TURBINE_MAP_SOURCE_URI",
            "turbine_map_source_sha256": "REPLACE_WITH_64_HEX_SOURCE_SHA256",
            "turbine_map_license_id": "REPLACE_WITH_REVIEWED_LICENSE_ID",
        } if name == "turbine-map-pairing-receipt" else {}),
        invariants=invariants)
        for name, entry, invariants in definitions)


def _map():
    from h2physics.adapters.compressor_map import (
        CompressorMapEvidence,
        CompressorMapLine,
        CompressorOperatingMap,
    )

    evidence = CompressorMapEvidence("authored-map", "urn:h2physics:authored-map",
        "Apache-2.0", "0"*64)
    return CompressorOperatingMap("map", 300.0, 1e5, (
        CompressorMapLine(100.0, 0.01, 0.03, 1.2, 2.0, 0.5, 0.9),
        CompressorMapLine(200.0, 0.02, 0.06, 1.4, 3.0, 0.6, 0.95)), evidence)


def _state():
    from h2physics.core import PropertyBasis, ThermoState
    return ThermoState(PropertyBasis("Hydrogen", "case", "normal"), 1e5, 300.0,
        0.08, 4e6, 2.75e6, 5e4, "gas")


def validate_correction(*, work_directory, **parameters):
    flow, speed = _map().corrected_coordinates(_state(), 0.02, 150.0)
    assert flow == 0.02 and speed == 150.0
    return ValidationOutcome(True, {"corrected_flow": flow, "corrected_speed": speed},
        ("Authored coordinate case only.",))


def validate_interpolation(*, work_directory, **parameters):
    limits = _map().limits(150.0)
    assert limits.minimum_corrected_flow_kg_s == 0.015
    return ValidationOutcome(True, {"minimum_flow": limits.minimum_corrected_flow_kg_s},
        ("Linear envelope interpolation only.",))


def validate_no_extrapolation(*, work_directory, **parameters):
    rejected = 0
    for speed in (99.0, 201.0):
        try:
            _map().limits(speed)
        except ValueError:
            rejected += 1
    assert rejected == 2
    return ValidationOutcome(True, {"rejections": rejected}, ("No map extrapolation.",))


def validate_operating_limits(*, work_directory, **parameters):
    limits = _map().limits(150.0)
    assert limits.minimum_pressure_ratio < limits.maximum_pressure_ratio
    return ValidationOutcome(True, {"pressure_ratio_span": limits.maximum_pressure_ratio-limits.minimum_pressure_ratio},
        ("Full native admission deferred to configured cluster provider.",))


def validate_schedule(*, work_directory, **parameters):
    from h2physics.adapters.compressor_map import CompressorCommand
    rows = (CompressorCommand(0.0, 0.0, 0.0, "isolated"),
            CompressorCommand(1.0, 150.0, 0.02))
    assert rows[0].mode == "isolated" and rows[1].time_s > rows[0].time_s
    return ValidationOutcome(True, {"commands": len(rows)}, ("No rotor dynamics inferred.",))


def validate_original_result(*, work_directory, **parameters):
    return ValidationOutcome(True, {"configured_native_replay_required": 1},
        ("Execute with the pinned LH2DT compressor profile; no fake native result is created here.",))


def validate_turbine_map_pairing(*, work_directory, **parameters):
    """Replay a caller fixture from the pinned LH2DT profile; never fabricate native traces."""
    module_name = parameters.get("fixture_module")
    builder_name = parameters.get("fixture_builder")
    if (not isinstance(module_name, str) or not module_name.strip()
            or "REPLACE_WITH" in module_name or not isinstance(builder_name, str)
            or not builder_name.isidentifier()):
        raise ValueError(
            "Supply a project fixture module that constructs a real pinned-LH2DT "
            "MappedCompressorTrace and a source-hashed TurbineMapPoint"
        )
    for field in ("turbine_map_source_uri", "turbine_map_source_sha256", "turbine_map_license_id"):
        value = parameters.get(field)
        if not isinstance(value, str) or not value.strip() or "REPLACE_WITH" in value:
            raise ValueError(f"Supply reviewed turbine-map provenance in {field}")
    module = importlib.import_module(module_name)
    builder = getattr(module, builder_name, None)
    if not callable(builder):
        raise ValueError("Configured pairing fixture must expose the named builder")
    fixture = builder(work_directory=work_directory, parameters=parameters)
    if not isinstance(fixture, dict):
        raise TypeError("Pairing fixture builder must return TurbineMapPairingReceipt constructor fields")
    from h2physics.combustion import TurbineMapPairingReceipt

    receipt = TurbineMapPairingReceipt(**fixture)
    receipt.require_current()
    observation = receipt.compressor_observation
    if receipt.compressor_map_evidence_id != receipt.compressor_trace.evidence_id:
        raise AssertionError("Compressor map evidence identity was not retained")
    if receipt.turbine_map_evidence_id != receipt.turbine_point.component_map.evidence_id:
        raise AssertionError("Turbine map evidence identity was not retained")
    if receipt.turbine_point.component_map.source_uri != parameters["turbine_map_source_uri"]:
        raise AssertionError("Turbine map source URI differs from the reviewed fixture input")
    if receipt.turbine_point.component_map.source_sha256 != parameters["turbine_map_source_sha256"].lower():
        raise AssertionError("Turbine map source digest differs from the reviewed fixture input")
    if receipt.turbine_point.component_map.license_id != parameters["turbine_map_license_id"]:
        raise AssertionError("Turbine map license differs from the reviewed fixture input")
    return ValidationOutcome(True, {
        "pairing_id": receipt.pairing_id,
        "compressor_map_evidence_id": receipt.compressor_map_evidence_id,
        "turbine_map_evidence_id": receipt.turbine_map_evidence_id,
        "compressor_corrected_flow_kg_s": observation.corrected_flow_kg_s,
        "turbine_corrected_flow_kg_s": receipt.turbine_point.corrected_mass_flow_kg_s,
    }, (
        "Pairing receipt only; no common flow correction, cycle state, mass balance, "
        "shaft balance or energy closure is inferred.",
        "Requires a project fixture using the pinned native LH2DT compressor and "
        "reviewed turbine-map data; no local native result is synthesized.",
    ))
