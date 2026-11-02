"""Deferred native H2/air counterflow and immutable-profile checks."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Cantera's native opposed-flow solution is the physics owner.",
    "An authored h2o2 mechanism case does not qualify mechanism or apparatus accuracy.",
    "No comparison to the NH3/H2 public dataset is implied.",
)


def cases():
    definitions = (
        ("counterflow-native-profile", "validate_profile"),
        ("counterflow-strain-definitions", "validate_strain_rates"),
        ("counterflow-profile-sampling", "validate_profile_sampling"),
        ("counterflow-heat-release-integral", "validate_heat_release_integral"),
        ("counterflow-pressure-admission", "validate_pressure_admission"),
        ("counterflow-result-issuer", "validate_result_issuer"),
    )
    return tuple(
        ValidationCase(
            identifier=name,
            profile="counterflow-flame",
            entrypoint=f"{__name__}:{entry}",
            parameters={},
            invariants=("native-profile-identity", "explicit-axial-units", "finite-species-ledger"),
        )
        for name, entry in definitions
    )


def validate_profile(*, work_directory, **parameters):
    from examples.counterflow_flame import build
    from h2physics.combustion import counterflow_profile, verify_counterflow_diffusion_flame

    result = build(**parameters)
    verify_counterflow_diffusion_flame(result)
    profile = counterflow_profile(result)
    mole_sum = np.sum(profile.mole_fractions, axis=0)
    mass_sum = np.sum(profile.mass_fractions, axis=0)
    assert np.allclose(mole_sum, 1.0, rtol=1e-8, atol=1e-10)
    assert np.allclose(mass_sum, 1.0, rtol=1e-8, atol=1e-10)
    assert profile.axial_position_m[0] < profile.axial_position_m[-1]
    assert profile.temperature_k.max() == result.peak_temperature_k
    assert not profile.temperature_k.flags.writeable
    return ValidationOutcome(
        True,
        {
            "grid_points": len(profile.axial_position_m),
            "peak_temperature_k": float(profile.temperature_k.max()),
            "peak_heat_release_w_m3": float(profile.heat_release_rate_w_m3.max()),
        },
        LIMITS,
    )


def validate_strain_rates(*, work_directory, **parameters):
    from examples.counterflow_flame import build
    from h2physics.combustion import counterflow_profile

    profile = counterflow_profile(build(**parameters))
    expected = {"mean", "max", "potential_flow_fuel", "potential_flow_oxidizer"}
    assert set(profile.strain_rates_s_inv) == expected
    assert all(np.isfinite(value) and value > 0 for value in profile.strain_rates_s_inv.values())
    return ValidationOutcome(
        True,
        {f"strain_rate_{name}_s_inv": value for name, value in profile.strain_rates_s_inv.items()},
        LIMITS,
    )


def validate_profile_sampling(*, work_directory, **parameters):
    from examples.counterflow_flame import build
    from h2physics.combustion import counterflow_profile

    profile = counterflow_profile(build(**parameters))
    midpoint = 0.5 * (profile.axial_position_m[0] + profile.axial_position_m[-1])
    positions = [profile.axial_position_m[0], midpoint, profile.axial_position_m[-1]]
    sampled = profile.sample(positions)
    assert np.array_equal(sampled["axial_position_m"], positions)
    assert sampled["temperature_k"][0] == profile.temperature_k[0]
    assert sampled["temperature_k"][-1] == profile.temperature_k[-1]
    assert not sampled["temperature_k"].flags.writeable
    try:
        profile.sample([profile.axial_position_m[-1] + 1e-9])
    except ValueError as error:
        assert "cannot extrapolate" in str(error)
    else:
        raise AssertionError("Profile sampling must reject extrapolation")
    return ValidationOutcome(True, {"sampled_points": len(sampled["axial_position_m"])}, LIMITS)


def validate_heat_release_integral(*, work_directory, **parameters):
    from examples.counterflow_flame import build
    from h2physics.combustion import counterflow_profile

    profile = counterflow_profile(build(**parameters))
    z = profile.axial_position_m
    full = profile.integrate_heat_release()
    split = (profile.integrate_heat_release(float(z[0]), float(z[len(z) // 2]))
             + profile.integrate_heat_release(float(z[len(z) // 2]), float(z[-1])))
    assert np.isclose(full, split, rtol=1e-12, atol=1e-12)
    assert profile.integrate_heat_release(float(z[0]), float(z[0])) == 0.0
    try:
        profile.integrate_heat_release(float(z[0]) - 1e-9, float(z[-1]))
    except ValueError as error:
        assert "cannot extrapolate" in str(error)
    else:
        raise AssertionError("Heat-release integration must reject extrapolation")
    return ValidationOutcome(
        True,
        {"integrated_heat_release_w_m2": full,
         "split_integral_w_m2": split},
        LIMITS,
    )


def validate_pressure_admission(*, work_directory, **parameters):
    import hashlib
    from pathlib import Path

    import cantera as ct

    from h2physics.adapters.cantera import CanteraGas, MechanismBasis, ReactiveState
    from h2physics.combustion import CounterflowBoundary, solve_counterflow_diffusion_flame

    source = (Path(ct.__file__).parent / "data" / "h2o2.yaml").read_bytes()
    basis = MechanismBasis(
        "Cantera-h2o2-ohmech",
        hashlib.sha256(source).hexdigest(),
        "Cantera-BSD-3-Clause",
        ("https://cantera.org/3.2/examples/python/onedim/diffusion_flame.html",),
        250.0,
        3500.0,
        1e4,
        2e6,
    )
    gas = CanteraGas.from_yaml(source, basis, phase_name="ohmech")
    fuel = CounterflowBoundary(ReactiveState(300.0, 101325.0, {"H2": 1.0}), 0.2)
    oxidizer = CounterflowBoundary(ReactiveState(300.0, 202650.0, {"O2": 0.21, "N2": 0.79}), 0.8)
    try:
        solve_counterflow_diffusion_flame(gas, fuel, oxidizer)
    except ValueError as error:
        assert "same absolute pressure" in str(error)
        return ValidationOutcome(True, {"mismatched_pressure_rejected": True}, LIMITS)
    raise AssertionError("The opposed-flow boundary contract must reject mismatched pressures")


def validate_result_issuer(*, work_directory, **parameters):
    from dataclasses import replace, fields

    from examples.counterflow_flame import build
    from h2physics.combustion import CounterflowFlameResult

    result = build(**parameters)
    try:
        replace(result)
    except ValueError:
        pass
    else:
        raise AssertionError("A copied counterflow result must not inherit solver issuance")
    values = {item.name: getattr(result, item.name) for item in fields(result)
              if not item.name.startswith("_")}
    try:
        CounterflowFlameResult(**values, _seal=object())
    except ValueError:
        return ValidationOutcome(True, {"direct_result_rejected": True,
                                        "copied_result_rejected": True}, LIMITS)
    raise AssertionError("Caller-created counterflow results must not claim native issuance")
