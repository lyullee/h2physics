"""Deferred contract for lumped isothermal pipeline linepack bookkeeping."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-pipeline-lumped-isothermal-linepack",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_linepack",
            parameters={
                "volume_m3": 12.0,
                "temperature_k": 293.15,
                "molecular_mass_kg_mol": 0.00201588,
                "initial_pressure_pa": 7.0e6,
                "minimum_mass_kg": 0.01,
            },
            invariants=(
                "fixed-volume-perfect-gas-inventory-pressure-relation",
                "constant-port-rates-integrate-to-exact-step-mass-ledger",
                "pressure-follows-linepack-mass-at-fixed-temperature-composition",
                "withdrawal-cannot-cross-the-caller-inventory-floor",
                "lumped-isothermal-result-is-not-spatial-transient-or-qualification",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-linepack-withdrawal-finite-source-handoff",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_source_handoff",
            parameters={},
            invariants=(
                "one accepted H2 linepack withdrawal becomes an exact finite interval source",
                "outlet mass equals the native integrated withdrawal ledger",
                "representative state preserves the exact H2 ideal-gas molecular basis",
                "state pressure remains within accepted linepack endpoint pressures",
                "post-issuance source mutation invalidates the typed receipt",
                "no nozzle flow law or pressure-time transient is inferred",
            ),
        ),
    )


def validate_source_handoff(*, work_directory, **parameters):
    """Deferred contract for linepack inventory to finite release-source coupling."""
    del work_directory, parameters
    from math import isclose

    from h2physics.adapters.linepack_source import advance_linepack_to_source
    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.pipeline_linepack import IsothermalLinepackState
    from h2physics.release import SourceLocation

    initial = IsothermalLinepackState.from_pressure(
        volume_m3=2.0, temperature_k=293.15,
        molecular_mass_kg_mol=0.00201588, pressure_pa=5.0e6, time_s=20.0,
    )
    duration, outlet_rate = 10.0, 0.02
    end_pressure = (initial.mass_kg-outlet_rate*duration)*(
        8.31446261815324/initial.molecular_mass_kg_mol
    )*initial.temperature_k/initial.volume_m3
    representative_pressure = 0.5*(initial.pressure_pa+end_pressure)
    density = representative_pressure*initial.molecular_mass_kg_mol/(
        8.31446261815324*initial.temperature_k
    )
    state = ThermoState(PropertyBasis("H2", "authored-linepack-source-state"),
        representative_pressure, initial.temperature_k, density,
        5.0e5, 5.0e5-representative_pressure/density, 0.0, "gas")
    location = SourceLocation("linepack-outlet", "authored-clock", "pipe-axis-frame",
        (0., 0., 0.), (1., 0., 0.))
    receipt = advance_linepack_to_source(initial, duration_s=duration,
        inlet_mass_flow_kg_s=0., outlet_mass_flow_kg_s=outlet_rate,
        minimum_mass_kg=0.01, location=location, gas_state=state,
        origin=Origin.SYNTHETIC, evidence_id="authored-linepack-outlet",
        state_projection_evidence_id="authored-midpoint-pressure-state-projection")
    receipt.require_current()
    assert receipt.source.location is location
    assert receipt.source.state is state
    assert isclose(float(receipt.source.mass_kg.sum()), outlet_rate*duration,
                   rel_tol=1e-12, abs_tol=1e-15)
    original = receipt.source.mass_kg
    altered = original.copy()
    altered[0] *= 1.01
    object.__setattr__(receipt.source, "mass_kg", altered)
    try:
        receipt.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Mutated linepack withdrawal source retained a current receipt")
    object.__setattr__(receipt.source, "mass_kg", original)
    receipt.require_current()
    wrong_basis = ThermoState(PropertyBasis("CH4", "authored-wrong-fluid"),
        representative_pressure, initial.temperature_k, density,
        5.0e5, 5.0e5-representative_pressure/density, 0.0, "gas")
    try:
        advance_linepack_to_source(initial, duration_s=duration,
            inlet_mass_flow_kg_s=0., outlet_mass_flow_kg_s=outlet_rate,
            minimum_mass_kg=0.01, location=location, gas_state=wrong_basis,
            origin=Origin.SYNTHETIC, evidence_id="authored-wrong-fluid-rejection",
            state_projection_evidence_id="authored-invalid-fluid-basis")
    except ValueError:
        wrong_fluid_rejected = True
    else:
        raise AssertionError("A non-H2 outlet state was accepted for an H2 linepack")
    return ValidationOutcome(True, {
        "withdrawal_mass_kg": float(original[0]),
        "source_start_s": receipt.source.edges_s[0],
        "source_end_s": receipt.source.edges_s[-1],
        "linepack_pressure_before_pa": receipt.ledger.initial_pressure_pa,
        "linepack_pressure_after_pa": receipt.ledger.final_pressure_pa,
        "mass_residual_kg": receipt.ledger.mass_residual_kg,
        "wrong_fluid_rejected": wrong_fluid_rejected,
    }, (
        "Authored perfect-gas linepack and midpoint-state projection only",
        "The interval mean source is not a nozzle or time-resolved leak model",
        "No experimental pipeline or dispersion validation is established",
    ))


def validate_linepack(*, work_directory, **parameters):
    """Check injection, withdrawal, zero-net operation and floor rejection."""
    del work_directory
    from h2physics.pipeline_linepack import IsothermalLinepackState

    initial = IsothermalLinepackState.from_pressure(
        volume_m3=parameters["volume_m3"],
        temperature_k=parameters["temperature_k"],
        molecular_mass_kg_mol=parameters["molecular_mass_kg_mol"],
        pressure_pa=parameters["initial_pressure_pa"],
    )
    injected, injection_ledger = initial.advance(
        duration_s=30.0, inlet_mass_flow_kg_s=0.04, outlet_mass_flow_kg_s=0.0,
        minimum_mass_kg=parameters["minimum_mass_kg"],
    )
    discharged, withdrawal_ledger = injected.advance(
        duration_s=20.0, inlet_mass_flow_kg_s=0.0, outlet_mass_flow_kg_s=0.03,
        minimum_mass_kg=parameters["minimum_mass_kg"],
    )
    balanced, balance_ledger = discharged.advance(
        duration_s=10.0, inlet_mass_flow_kg_s=0.02, outlet_mass_flow_kg_s=0.02,
        minimum_mass_kg=parameters["minimum_mass_kg"],
    )
    for state, ledger in ((injected, injection_ledger),
                          (discharged, withdrawal_ledger), (balanced, balance_ledger)):
        scale = max(1.0, ledger.initial_mass_kg, ledger.final_mass_kg)
        assert abs(ledger.mass_residual_kg) <= 1e-14 * scale
        assert abs(state.pressure_pa / ledger.final_pressure_pa - 1.0) <= 1e-14
    assert injected.mass_kg > initial.mass_kg
    assert injected.pressure_pa > initial.pressure_pa
    assert discharged.mass_kg < injected.mass_kg
    assert abs(balanced.mass_kg - discharged.mass_kg) <= 1e-14 * max(1.0, discharged.mass_kg)
    assert balanced.time_s == 60.0
    try:
        initial.advance(duration_s=100.0, inlet_mass_flow_kg_s=0.0,
                        outlet_mass_flow_kg_s=initial.mass_kg / 100.0,
                        minimum_mass_kg=parameters["minimum_mass_kg"])
    except ValueError as error:
        assert "mass floor" in str(error)
    else:
        raise AssertionError("A withdrawal reaching the declared inventory floor was accepted")
    return ValidationOutcome(
        True,
        {
            "initial_mass_kg": initial.mass_kg,
            "initial_pressure_pa": initial.pressure_pa,
            "injected_pressure_pa": injected.pressure_pa,
            "withdrawn_pressure_pa": discharged.pressure_pa,
            "maximum_mass_residual_kg": max(
                abs(injection_ledger.mass_residual_kg),
                abs(withdrawal_ledger.mass_residual_kg),
                abs(balance_ledger.mass_residual_kg),
            ),
        },
        (
            "Ideal-gas lumped linepack contract with constant temperature and fixed composition only.",
            "No spatial pressure transient, friction coupling, real-gas correction, heat balance or experimental qualification.",
        ),
    )
