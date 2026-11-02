"""Deferred real-fluid compressor to isothermal pipeline linepack contract."""

from dataclasses import replace
from math import isclose

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydrogen-real-fluid-compressor-linepack-charge-handoff",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_charge",
        invariants=(
            "owner-issued-pure-H2-HEOS-compressor-run-is-retained",
            "compressor-outlet-pressure-exceeds-final-linepack-pressure",
            "compressor-throughput-over-caller-window-equals-linepack-inlet-mass",
            "conditioned-inlet-state-matches-HEOS-at-final-linepack-pressure-and-fixed-temperature",
            "signed-thermal-conditioning-energy-closes-discharge-to-linepack-state-enthalpy",
            "time-basis-hydrogen-basis-transfer-and-thermal-evidence-are-required",
            "reissued-receipt-is-rejected-and-original-source-remains-current",
            "linepack-remains-an-isothermal-mass-only-ideal-gas-model",
        ),
    ), ValidationCase(
        identifier="hydrogen-real-fluid-compressor-native-linepack-charge-handoff",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_native_charge",
        invariants=(
            "native-HEOS-linepack-pressure-and-density-use-the-compressor-fluid-spin-and-version",
            "original-compressor-and-linepack-owners-close-mass-and-inlet-conditioning-energy",
            "spin-provider-pointer-clock-pressure-and-conditioning-mismatches-are-rejected",
            "no-stored-energy-or-thermal-control-closure-is-inferred-from-the-inlet-projection",
        ),
    ))


def validate_charge(*, work_directory, **parameters):
    del work_directory, parameters
    return _validate_charge(native=False)


def validate_native_charge(*, work_directory, **parameters):
    del work_directory, parameters
    return _validate_charge(native=True)


def _validate_charge(*, native):
    from h2physics.adapters.compressor_linepack import charge_linepack_from_compressor
    from h2physics.combustion.fuel_compression import run_real_fluid_hydrogen_compression
    from h2physics.pipeline_linepack import IsothermalLinepackState
    from h2physics.real_gas_linepack import RealGasLinepackState
    from h2physics.thermo import CoolPropIsothermalEOS, CoolPropProperties
    from validation.cases.hydrogen_fuel_compression import _real_fluid_inputs

    provider = CoolPropProperties("Hydrogen", backend="HEOS")
    inputs = _real_fluid_inputs(
        process_window_id="compressor-steady-point-mapped-to-linepack-window",
        inlet_temperature_k=300., inlet_pressure_pa=1.0e6,
        discharge_pressure_pa=5.0e6,
        hydrogen_mass_flow_kg_s=.01,
        state_evidence_id="authored-compressor-inlet-state",
        efficiency_evidence_id="authored-compressor-efficiency",
        domain_evidence_id="authored-compressor-domain",
    )
    compressor = run_real_fluid_hydrogen_compression(provider, inputs)
    if native:
        initial = RealGasLinepackState.from_pressure(
            volume_m3=.01, temperature_k=300., eos=CoolPropIsothermalEOS("Hydrogen"),
            pressure_pa=1.0e6, time_s=20.,
            minimum_pressure_pa=.5e6, maximum_pressure_pa=4.9e6,
        )
    else:
        initial = IsothermalLinepackState.from_pressure(
            volume_m3=.01, temperature_k=300.,
            molecular_mass_kg_mol=.00201588,
            pressure_pa=1.0e6, time_s=20.,
        )
    duration = .1
    final, expected_ledger = initial.advance(
        duration_s=duration,
        inlet_mass_flow_kg_s=inputs.hydrogen_mass_flow_kg_s,
        outlet_mass_flow_kg_s=0., minimum_mass_kg=.001,
    )
    assert compressor.actual_outlet.pressure_pa > final.pressure_pa
    conditioned = provider.state_pt(final.pressure_pa, initial.temperature_k)
    source = provider.state_pt(compressor.actual_outlet.pressure_pa,
                               compressor.actual_outlet.temperature_k)
    expected_heat = inputs.hydrogen_mass_flow_kg_s*duration*(
        conditioned.enthalpy_j_kg-source.enthalpy_j_kg
    )
    receipt = charge_linepack_from_compressor(
        initial, compressor, duration_s=duration, start_time_s=initial.time_s,
        minimum_mass_kg=.001, conditioned_inlet_state=conditioned,
        thermal_conditioning_energy_j=expected_heat,
        time_mapping_evidence_id="authored-process-window-to-20.0-20.1-clock",
        hydrogen_basis_evidence_id="authored-pure-hydrogen-and-molar-mass-basis",
        transfer_boundary_evidence_id="authored-compressor-discharge-to-linepack-boundary",
        thermal_conditioning_evidence_id="authored-isothermal-conditioning-energy-ledger",
        absolute_energy_tolerance_j=1e-6,
        relative_energy_tolerance=1e-8,
    )
    assert receipt.require_current() is receipt
    assert receipt.ledger == expected_ledger
    assert isclose(receipt.transferred_mass_kg,
                   compressor.inputs.hydrogen_mass_flow_kg_s*duration,
                   rel_tol=1e-12, abs_tol=1e-15)
    assert isclose(receipt.conditioning_energy_residual_j, 0., abs_tol=1e-6)

    direct_reissue_rejected = False
    try:
        replace(receipt)
    except TypeError:
        direct_reissue_rejected = True
    assert direct_reissue_rejected
    rejected = []
    if native:
        def reject(name, action):
            try:
                action()
            except (TypeError, ValueError):
                rejected.append(name)
            else:
                raise AssertionError(f"Native compressor charge accepted {name}")

        def charge(candidate=initial, **overrides):
            kwargs = dict(
                duration_s=duration, start_time_s=initial.time_s, minimum_mass_kg=.001,
                conditioned_inlet_state=conditioned, thermal_conditioning_energy_j=expected_heat,
                time_mapping_evidence_id="authored-window-clock",
                hydrogen_basis_evidence_id="authored-normal-H2",
                transfer_boundary_evidence_id="authored-transfer",
                thermal_conditioning_evidence_id="authored-conditioning",
                absolute_energy_tolerance_j=1e-6, relative_energy_tolerance=1e-8,
            )
            kwargs.update(overrides)
            return charge_linepack_from_compressor(candidate, compressor, **kwargs)

        wrong_spin = RealGasLinepackState.from_pressure(
            volume_m3=.01, temperature_k=300., eos=CoolPropIsothermalEOS("ParaHydrogen"),
            pressure_pa=1.e6, time_s=20.,
        )
        reject("normal-to-para spin mismatch", lambda: charge(wrong_spin))
        reject("clock mismatch", lambda: charge(start_time_s=19.))
        reject("conditioning energy mismatch", lambda: charge(thermal_conditioning_energy_j=expected_heat+1000.))
        limited = replace(initial, maximum_pressure_pa=1.01e6)
        reject("pressure envelope exceeded", lambda: charge(limited))
        for label, owner, attribute, replacement in (
            ("EOS native pointer mutation", initial.eos, "_state", CoolPropIsothermalEOS("Hydrogen")._state),
            ("compressor native pointer mutation", provider, "_state", CoolPropProperties("Hydrogen")._state),
            ("EOS method mutation", initial.eos, "density_pt", lambda p, t: 1.),
        ):
            original = getattr(owner, attribute)
            try:
                setattr(owner, attribute, replacement)
                reject(label, receipt.require_current)
            finally:
                setattr(owner, attribute, original)
            assert receipt.require_current() is receipt
        original_eos = receipt.final.eos
        try:
            object.__setattr__(receipt.final, "eos", CoolPropIsothermalEOS("Hydrogen"))
            reject("final EOS owner substitution", receipt.require_current)
        finally:
            object.__setattr__(receipt.final, "eos", original_eos)
        assert receipt.require_current() is receipt
        assert receipt.final.eos is initial.eos
        assert receipt.ledger.eos_identity == initial.eos_identity
        assert isclose(provider.state_pt(receipt.final.pressure_pa, 300.).density_kg_m3,
                       receipt.final.density_kg_m3, rel_tol=1e-8)
    return ValidationOutcome(True, {
        "process_window_id": compressor.inputs.process_window_id,
        "time_start_s": receipt.start_time_s,
        "time_end_s": receipt.end_time_s,
        "mass_added_kg": receipt.transferred_mass_kg,
        "initial_linepack_pressure_pa": receipt.ledger.initial_pressure_pa,
        "final_linepack_pressure_pa": receipt.ledger.final_pressure_pa,
        "compressor_discharge_pressure_pa": compressor.actual_outlet.pressure_pa,
        "conditioning_energy_j": receipt.supplied_conditioning_energy_j,
        "conditioning_energy_residual_j": receipt.conditioning_energy_residual_j,
        "linepack_mass_residual_kg": receipt.ledger.mass_residual_kg,
        "direct_reissue_rejected": direct_reissue_rejected,
        "native_real_gas_linepack": native,
        "native_rejected_boundaries": rejected,
    }, (
        "Existing HEOS compressor and caller-selected native HEOS or analytic-reference isothermal linepack; no pipeline pressure-wave or friction model.",
        "Thermal-conditioning energy is a caller ledger for the inlet-state projection, not linepack stored-energy closure.",
    ))
