"""Deferred absolute adsorption calibration-to-vessel API contract."""

import numpy as np

from h2physics.adapters.absolute_adsorption_bridge import (
    AbsoluteAdsorptionBridgeError,
    bind_absolute_adsorption_state,
)
from h2physics.adsorption import AdsorptionBasis, AdsorptionSourceObservation, AdsorptionState
from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="absolute-adsorption-single-point-vessel-bridge",
        profile="finite-adsorption-vessel",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "source-backed absolute loading is returned only at its exact calibrated condition",
            "off-condition requests refuse interpolation and extrapolation",
            "signed surface excess and source-defined loading are never converted to absolute inventory",
            "qualification evidence and source-state identity remain fixed after bridge construction",
            "provider loading derivatives remain tied to the qualified absolute-state anchor",
            "directional loading response is site-resolved first-order only and rejects stale bridge state",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    basis = AdsorptionBasis(
        "synthetic-carbon", ("H2",), "mol_H2_per_kg_adsorbent",
        "authored-single-point-provider", "authored-absolute-point-v1",
        ("authored synthetic contract fixture",), "absolute",
    )
    observation = AdsorptionSourceObservation(
        "H2", 1, 1., .25, source_dataset_id="synthetic-fixture",
        source_sha256="a" * 64,
    )
    state = AdsorptionState(
        basis, np.array([2e5]), 298.15, np.array([[.25]]),
        site_pressure_derivatives_mol_kg_pa=np.array([[[1e-7]]]),
        site_temperature_derivatives_mol_kg_k=np.array([[2e-3]]),
        source_observations=((observation,),),
    )
    bridge = bind_absolute_adsorption_state(
        state, qualification_evidence_id="authored-fixture-qualification",
    )
    assert bridge.equilibrium([2e5], 298.15) is state
    sensitivity = bridge.local_loading_sensitivity()
    delta = sensitivity.directional_loading_delta([1000.], 2.)
    assert delta.shape == (1, 1)
    assert np.isclose(delta[0, 0], 0.0041, rtol=0., atol=1e-15)
    original_qualification = bridge.qualification_evidence_id
    object.__setattr__(bridge, "qualification_evidence_id", "replacement-qualification")
    try:
        bridge.require_current()
    except AbsoluteAdsorptionBridgeError as error:
        assert "qualification evidence" in str(error)
    else:
        raise AssertionError("Changed absolute-uptake qualification identity was admitted")
    object.__setattr__(bridge, "qualification_evidence_id", original_qualification)
    bridge.require_current()
    from dataclasses import replace

    original_state = bridge.state
    object.__setattr__(bridge, "state", replace(original_state))
    try:
        bridge.require_current()
    except AbsoluteAdsorptionBridgeError:
        pass
    else:
        raise AssertionError("Equal-valued replacement adsorption state was admitted")
    object.__setattr__(bridge, "state", original_state)
    bridge.require_current()
    assert sensitivity.require_current() is sensitivity
    invalid_query_refused = False
    try:
        bridge.equilibrium([True], 298.15)
    except ValueError:
        invalid_query_refused = True
    assert invalid_query_refused
    off_condition_refused = False
    try:
        bridge.equilibrium([2.1e5], 298.15)
    except AbsoluteAdsorptionBridgeError:
        off_condition_refused = True
    assert off_condition_refused

    excess_basis = AdsorptionBasis(
        "synthetic-carbon", ("H2",), "mol_H2_per_kg_adsorbent",
        "authored-single-point-provider", "signed-excess-v1",
        ("authored synthetic excess fixture",), "surface_excess",
    )
    excess_observation = AdsorptionSourceObservation(
        "H2", 2, 1., -.01, source_dataset_id="synthetic-fixture",
        source_sha256="b" * 64,
    )
    excess_state = AdsorptionState(
        excess_basis, np.array([2e5]), 298.15, np.array([[-.01]]),
        source_observations=((excess_observation,),),
    )
    excess_refused = False
    try:
        bind_absolute_adsorption_state(
            excess_state, qualification_evidence_id="authored-excess-not-absolute",
        )
    except AbsoluteAdsorptionBridgeError:
        excess_refused = True
    assert excess_refused
    return ValidationOutcome(
        True,
        {"absolute_loading_mol_kg": .25,
         "off_condition_refused": off_condition_refused,
         "invalid_numeric_query_refused": invalid_query_refused,
         "surface_excess_refused": excess_refused},
        ("Synthetic API contract only; no fit, conversion, or material validation.",),
    )
