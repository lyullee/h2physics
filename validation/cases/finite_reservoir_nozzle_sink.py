"""Deferred contracts for debited pipe-reservoir nozzle release histories."""


def cases():
    from h2physics.cluster_validation import ValidationCase

    return (
        ValidationCase(
            identifier="hydrogen-pipeline-finite-reservoir-nozzle-sink-closure",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_debited_source_closure",
            invariants=(
                "the-start-of-substep-shared-nozzle-flow-is-debited-with-the-same-duration",
                "finite-reservoir-stock-and-network-pipe-mass-close-after-pipe-and-leak-exchanges",
                "endpoint-nozzle-sample-is-diagnostic-and-left-hold-source-integral-matches-leak-ledger",
                "source-retains-location-clock-opening-caloric-basis-and-caller-evidence",
                "dispersion-execution-is-not-claimed-by-this-source-projection",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-finite-reservoir-nozzle-mapping-rejections",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_mapping_rejections",
            invariants=(
                "network-EOS-and-nozzle-caloric-basis-require-explicit-identity-mapping",
                "density-agreement-is-checked-against-a-caller-declared-tolerance-and-evidence",
                "unsupported-node-edge-clock-or-opening-contracts-are-rejected",
            ),
        ),
    )


def _fixture():
    from dataclasses import replace

    from h2physics.core import Origin
    from h2physics.pipe_nozzle_coupling import (
        FiniteReservoirNozzleCoupling,
        IsothermalToCaloricStateMapping,
    )
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening, SourceLocation
    from h2physics.thermo.coolprop import CoolPropProperties

    from .finite_pipe_reservoir_network import _fixture as network_fixture

    model, nodes, edges, eos, reservoir, pressure, velocity = network_fixture()
    properties = CoolPropProperties("Hydrogen")
    mapping = IsothermalToCaloricStateMapping(
        source_eos_identity=eos.identity,
        target_basis=properties.basis,
        evidence_id="synthetic-explicit-coolprop-density-map",
        density_relative_tolerance=.10,
        density_absolute_tolerance_kg_m3=0.,
    )
    opening = NozzleOpening.circular(
        "synthetic-small-leak", .002, effective_area_factor=.8,
        area_basis_id="synthetic-effective-area-basis",
    )
    coupling = FiniteReservoirNozzleCoupling(
        identifier="synthetic-terminal-leak",
        node_id=reservoir.node_id,
        reservoir_id=reservoir.identifier,
        edge_id="branch-reservoir",
        opening=opening,
        opening_fraction=1.,
        back_pressure_pa=101325.,
        location=SourceLocation(
            "synthetic-terminal-leak", model.clock_id,
            "synthetic-network-frame", (100., 0., 0.), (1., 0., 0.),
        ),
        nozzle=HomogeneousIsentropicNozzle(properties),
        state_mapping=mapping,
        evidence_id="synthetic-opening-location-and-coupling-record",
        origin=Origin.SYNTHETIC,
    )
    return model, eos, reservoir, pressure, velocity, coupling


def validate_debited_source_closure(*, work_directory, **parameters):
    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    model, eos, reservoir, pressure, velocity, coupling = _fixture()
    trace = model.simulate(
        initial_pressure_pa=pressure,
        initial_velocity_m_s=velocity,
        time_samples_s=(0., .005, .01),
        finite_reservoirs={reservoir.node_id: reservoir},
        finite_reservoir_nozzles={reservoir.node_id: coupling},
    )
    history = trace.finite_reservoir_nozzle_history[reservoir.node_id]
    representative = coupling.nozzle.properties.state_pt(
        history.samples[0].upstream_stagnation.pressure_pa,
        history.samples[0].upstream_stagnation.temperature_k,
    )
    projection = trace.project_nozzle_source(
        reservoir.node_id,
        representative_state=representative,
        quadrature_evidence_id="synthetic-left-hold-substep-mass-ledger",
        state_projection_evidence_id="synthetic-representative-caloric-state",
    )
    leak_out = trace.finite_reservoir_nozzle_mass_out_kg[reservoir.node_id]
    assert history.location.clock_id == trace.clock_id
    assert history.location.source_id == coupling.identifier
    assert history.samples[0].opening == coupling.opening
    assert np.isclose(np.sum(projection.interval_mass_kg), leak_out[-1], rtol=2e-11, atol=2e-12)
    assert np.all(np.diff(trace.finite_inventory_mass_kg[reservoir.node_id]) < 0.)
    assert np.max(np.abs(trace.global_mass_balance_residual_kg)) < 1.e-8
    assert trace.finite_reservoir_nozzle_evidence_ids[reservoir.node_id] == coupling.evidence_id
    assert trace.finite_reservoir_nozzle_coupling_ids[reservoir.node_id] == coupling.identifier
    return ValidationOutcome(True, {
        "coupling_id": coupling.identifier,
        "reservoir_id": reservoir.identifier,
        "eos_identity": eos.identity,
        "caloric_basis": coupling.caloric_basis.reference_id,
        "time_sample_count": len(trace.time_s),
        "dense_nozzle_sample_count": len(history.time_s),
        "leak_mass_out_kg": leak_out.tolist(),
        "finite_reservoir_mass_kg": trace.finite_inventory_mass_kg[reservoir.node_id].tolist(),
        "combined_mass_residual_kg": trace.global_mass_balance_residual_kg.tolist(),
        "projected_interval_mass_kg": list(projection.interval_mass_kg),
    }, ("Synthetic nozzle-sink/source contract only; no HyRAM or dispersion execution.",))


def validate_mapping_rejections(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    model, _eos, reservoir, pressure, velocity, coupling = _fixture()
    bad_mapping = replace(coupling.state_mapping, source_eos_identity="different-eos")
    bad_coupling = replace(coupling, state_mapping=bad_mapping)
    try:
        model.simulate(
            initial_pressure_pa=pressure,
            initial_velocity_m_s=velocity,
            time_samples_s=(0., .001),
            finite_reservoirs={reservoir.node_id: reservoir},
            finite_reservoir_nozzles={reservoir.node_id: bad_coupling},
        )
    except ValueError as error:
        if "EOS identity" not in str(error):
            raise AssertionError("Mismatched EOS mapping rejected for an unrelated reason") from error
    else:
        raise AssertionError("Mismatched network-to-caloric EOS identity was accepted")
    return ValidationOutcome(True, {
        "rejected_contract": "network-to-caloric EOS identity mismatch",
        "reservoir_id": reservoir.identifier,
        "coupling_id": coupling.identifier,
    }, ("Synthetic identity rejection only; no dispersion execution.",))
