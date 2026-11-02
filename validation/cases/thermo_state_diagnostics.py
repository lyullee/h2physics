"""Deferred metadata for state-derived thermodynamic diagnostic contracts."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="thermo-gas-state-derived-diagnostics",
        profile="gas-composition",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "compressibility uses explicit caller-supplied specific gas constant and retained SI state",
            "transport ratios are returned only when the required native properties are present",
            "two-phase and liquid phase states are rejected",
            "diagnostic arrays or EOS values are not inferred from fluid labels",
            "native provider property values remain the sole state/transport source",
            "the retained diagnostic signature and compressibility remain bound to the source state",
            "a copied or altered diagnostic fails currentness admission",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    from math import isclose

    from h2physics.core import PropertyBasis, ThermoState
    from h2physics.thermo import GasStateDiagnostics

    state = ThermoState(
        PropertyBasis("H2", "case-reference"), 2.0e6, 300., 1.6,
        1.1e6, -1.4e5, 8.0e3, "gas", cp_j_kg_k=14300., cv_j_kg_k=10170.,
        viscosity_pa_s=9.0e-6, conductivity_w_m_k=.18,
    )
    result = GasStateDiagnostics.from_state(
        state, specific_gas_constant_j_kg_k=4124.2,
    )
    expected = {
        "compressibility_factor": state.pressure_pa/(state.density_kg_m3*4124.2*state.temperature_k),
        "prandtl_number": state.viscosity_pa_s*state.cp_j_kg_k/state.conductivity_w_m_k,
        "thermal_diffusivity_m2_s": state.conductivity_w_m_k/(state.density_kg_m3*state.cp_j_kg_k),
        "kinematic_viscosity_m2_s": state.viscosity_pa_s/state.density_kg_m3,
    }
    for name, value in expected.items():
        if not isclose(getattr(result, name), value, rel_tol=1e-14, abs_tol=0.):
            raise AssertionError(f"{name} differs from its state-derived definition")
    result.require_current()
    forged = GasStateDiagnostics.from_state(
        state, specific_gas_constant_j_kg_k=4124.2,
    )
    object.__setattr__(forged, "compressibility_factor", forged.compressibility_factor * 1.01)
    try:
        forged.require_current()
    except RuntimeError:
        pass
    else:
        raise AssertionError("A copied diagnostic with changed derived output was admitted")
    partial = ThermoState(
        state.basis, state.pressure_pa, state.temperature_k, state.density_kg_m3,
        state.enthalpy_j_kg, state.internal_energy_j_kg, state.entropy_j_kg_k,
        "gas", cp_j_kg_k=state.cp_j_kg_k,
    )
    sparse = GasStateDiagnostics.from_state(partial, specific_gas_constant_j_kg_k=4124.2)
    if any(value is not None for value in (sparse.prandtl_number,
            sparse.thermal_diffusivity_m2_s, sparse.kinematic_viscosity_m2_s)):
        raise AssertionError("Missing native properties must not be filled or inferred")
    try:
        GasStateDiagnostics.from_state(
            ThermoState(state.basis, state.pressure_pa, state.temperature_k,
                state.density_kg_m3, state.enthalpy_j_kg, state.internal_energy_j_kg,
                state.entropy_j_kg_k, "two_phase"),
            specific_gas_constant_j_kg_k=4124.2,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A two-phase state was admitted as a gas diagnostic")
    return ValidationOutcome(True, {"compressibility_factor": result.compressibility_factor,
        "prandtl_number": result.prandtl_number},
        ("Definition arithmetic uses a synthetic SI state only; EOS and transport accuracy remain unqualified",))
