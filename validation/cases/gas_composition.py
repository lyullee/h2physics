"""Deferred composition and component-flow contracts; not run locally."""

import math
import statistics
import time
from pathlib import Path

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="gas-composition-basis-and-flow-ledgers",
        profile="gas-composition",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=("mole/mass fraction round trip", "mixture molar mass",
                    "component flow partition and closure", "identity and domain guards",
                    "immutable copied composition arrays",
                    "CoolProp HEOS binary H2/N2 gas PT/PH/PS/P-rho states retain composition/property basis and energy identity",
                    "native mixture PT/PQ/TQ adapters validate state-pair inputs and preserve native mole-quality semantics",
                    "inverse bounds reject non-gas/nonmonotone or out-of-range requests; identity mismatches fail closed",
                    "PU inversion is admitted only on the explicitly configured monotone single-gas temperature interval",
                    "provider composition/property metadata cannot be reassigned after construction",
                    "exact inverse-state cache reuses immutable states, is bounded and can be cleared",
                    "optional immutable inverse PT grid is reusable only with a matching composition/property basis/domain, and brackets are rechecked at query pressure",
                    "inverse-grid axes and values are isolated read-only copies; malformed monotonicity and basis/domain mismatches are rejected",
                    "inverse grid can be round-tripped through a pickle-free compressed NumPy archive with identity and fingerprint preserved",
                    "off-node-pressure grid inversions match direct bounded inversions and report prep cost, PT flashes and wall time",
                    "grid benchmark reports whether measured per-inverse savings repay preparation cost and the resulting break-even query count, or explicitly reports no break-even",
                    "the bounded mixture provider composes with the common isentropic nozzle and retains its source basis/ledgers",
                    "finite adsorption-vessel gas binding rejects provider/composition metadata mismatches",
                    "state heat-capacity ratio is present only when both derivatives exist"),
    ),)


def validate_contract(*, work_directory, **parameters):
    from h2physics import GasComposition

    masses = np.array([2.01588e-3, 28.0134e-3, 18.01528e-3])
    source_mass_fractions = np.array([0.12, 0.78, 0.10])
    mixture = GasComposition.from_mass_fractions(
        "fixture-h2-n2-water-v1", ("H2", "N2", "H2O"), source_mass_fractions, masses,
    )
    restored = GasComposition(
        mixture.composition_id, mixture.species, mixture.mole_fractions, masses,
    )
    assert np.allclose(restored.mass_fractions, source_mass_fractions, rtol=1e-13, atol=1e-15)
    molar = restored.component_molar_flows(2.5)
    mass = restored.component_mass_flows(-0.08)
    assert np.isclose(molar.sum(), 2.5, rtol=1e-14, atol=1e-14)
    assert np.isclose(mass.sum(), -0.08, rtol=1e-14, atol=1e-14)
    assert np.isclose(restored.total_molar_flow_from_mass_flow(
        restored.total_mass_flow_from_molar_flow(2.5)), 2.5, rtol=1e-14)
    assert not restored.mole_fractions.flags.writeable
    assert not mass.flags.writeable

    gas_composition = GasComposition(
        "fixture-h2-n2-gas-v1", ("H2", "N2"), (0.5, 0.5), masses[:2],
    )

    from h2physics.core import PropertyBasis
    from h2physics.thermo import CoolPropMixtureProperties, MixtureInverseGrid

    properties = CoolPropMixtureProperties(
        gas_composition, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
        inverse_temperature_bounds_k=(280., 320.),
        inverse_cache_size=2,
    )
    state = properties.state_pt(5.0e6, 300.0)
    pu_round_trip = properties.state_pu(state.pressure_pa, state.internal_energy_j_kg)
    assert abs(pu_round_trip.temperature_k - state.temperature_k) <= 1e-7
    assert pu_round_trip.basis == state.basis
    assert state.basis == properties.basis
    assert state.basis.spin_composition == "mixture-H2-spin-unresolved"
    assert state.density_kg_m3 > 0 and state.cp_j_kg_k > 0
    if state.cp_j_kg_k is not None and state.cv_j_kg_k is not None:
        assert np.isclose(state.heat_capacity_ratio, state.cp_j_kg_k / state.cv_j_kg_k)
    else:
        assert state.heat_capacity_ratio is None
    assert abs(state.enthalpy_identity_residual_j_kg) <= max(1e-5, abs(state.enthalpy_j_kg) * 1e-10)
    assert properties.composition_id == gas_composition.composition_id
    assert len(properties.composition_sha256) == 64
    assert len(properties.coolprop_molar_masses_kg_mol) == 2
    for invalid_pressure, invalid_temperature in ((0., 300.), (5e6, float("nan"))):
        try:
            properties.state_pt(invalid_pressure, invalid_temperature)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid mixture PT inputs were admitted")
    for method, args in ((properties.state_pq, (5e6, 1.01)),
                         (properties.state_tq, (300., -0.01))):
        try:
            method(*args)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid native mixture quality was admitted")
    saturated_liquid = properties.state_pq(5e6, 0.)
    saturated_vapor = properties.state_tq(saturated_liquid.temperature_k, 1.)
    assert saturated_liquid.phase == "two_phase"
    assert saturated_vapor.phase == "two_phase"
    assert saturated_liquid.vapor_mass_fraction is None
    assert saturated_liquid.vapor_mole_fraction == 0.
    assert saturated_vapor.vapor_mass_fraction is None
    assert saturated_vapor.vapor_mole_fraction == 1.
    assert properties.saturated(5e6, 0.).vapor_mole_fraction == 0.
    assert properties.saturated_at_temperature(saturated_liquid.temperature_k, 1.).vapor_mole_fraction == 1.
    for method, args in ((properties.saturated, (5e6, .5)),
                         (properties.saturated_at_temperature, (100., .5))):
        try:
            method(*args)
        except ValueError:
            pass
        else:
            raise AssertionError("Mixture mass quality was silently interpreted as mole quality")
    interior = properties.state_pq(5e6, .5)
    try:
        properties.phase_viscosity(interior)
    except ValueError:
        pass
    else:
        raise AssertionError("Interior two-phase mixture viscosity was inferred")
    properties.basis.require_compatible(saturated_liquid.basis)
    properties.basis.require_compatible(saturated_vapor.basis)
    try:
        properties.mole_fractions = (0.6, 0.4)
    except AttributeError:
        pass
    else:
        raise AssertionError("Frozen CoolProp mixture fractions were reassigned after fingerprinting")
    try:
        properties.backend = "TTSE&HEOS"
    except AttributeError:
        pass
    else:
        raise AssertionError("CoolProp mixture backend metadata changed after construction")
    ph_state = properties.state_ph(state.pressure_pa, state.enthalpy_j_kg)
    ps_state = properties.state_ps(state.pressure_pa, state.entropy_j_kg_k)
    density_state = properties.state_prho(state.pressure_pa, state.density_kg_m3)
    cache_before_hit = properties.inverse_cache_info
    cached_ps_state = properties.state_ps(state.pressure_pa, state.entropy_j_kg_k)
    cache_after_hit = properties.inverse_cache_info
    assert cached_ps_state is ps_state
    assert cache_after_hit["hits"] == cache_before_hit["hits"] + 1
    assert cache_after_hit["maxsize"] == 2 and cache_after_hit["currsize"] == 2
    properties.clear_inverse_cache()
    assert properties.inverse_cache_info["currsize"] == 0
    assert properties.inverse_cache_info["hits"] == 0
    uncached_properties = CoolPropMixtureProperties(
        gas_composition, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
        inverse_temperature_bounds_k=(280., 320.), inverse_cache_size=0,
    )
    uncached_properties.state_ps(state.pressure_pa, state.entropy_j_kg_k)
    uncached_properties.state_ps(state.pressure_pa, state.entropy_j_kg_k)
    assert dict(uncached_properties.inverse_cache_info) == {
        "hits": 0, "misses": 0, "maxsize": 0, "currsize": 0,
    }
    grid_preparation_started = time.perf_counter()
    inverse_grid = properties.prepare_inverse_grid(
        (1.0e6, 5.0e6, 10.0e6), np.linspace(280., 320., 9),
    )
    inverse_grid_preparation_seconds = time.perf_counter() - grid_preparation_started
    grid_archive_path = Path(work_directory) / "mixture-inverse-grid.npz"
    inverse_grid.write_npz(grid_archive_path)
    restored_grid = MixtureInverseGrid.read_npz(grid_archive_path)
    assert restored_grid.fingerprint == inverse_grid.fingerprint
    assert restored_grid.property_basis == inverse_grid.property_basis
    assert restored_grid.inverse_temperature_bounds_k == inverse_grid.inverse_temperature_bounds_k
    assert not restored_grid.pressure_nodes_pa.flags.writeable
    assert all(not values.flags.writeable for values in restored_grid.property_values.values())
    assert inverse_grid.shape == (3, 9)
    grid_fingerprint = inverse_grid.fingerprint
    assert len(grid_fingerprint) == 64
    assert not inverse_grid.pressure_nodes_pa.flags.writeable
    assert not inverse_grid.temperature_nodes_k.flags.writeable
    assert all(not values.flags.writeable for values in inverse_grid.property_values.values())
    copied_pressures = np.array(inverse_grid.pressure_nodes_pa, copy=True)
    copied_temperatures = np.array(inverse_grid.temperature_nodes_k, copy=True)
    copied_values = {name: np.array(values, copy=True)
                     for name, values in inverse_grid.property_values.items()}
    copied_grid = MixtureInverseGrid(
        inverse_grid.composition_sha256, inverse_grid.property_basis,
        inverse_grid.inverse_temperature_bounds_k,
        copied_pressures, copied_temperatures, copied_values,
    )
    assert copied_grid.fingerprint == grid_fingerprint
    copied_pressures[0] *= 2.
    copied_temperatures[0] += 0.1
    copied_values["enthalpy_j_kg"][0, 0] += 1.
    assert copied_grid.pressure_nodes_pa[0] == inverse_grid.pressure_nodes_pa[0]
    assert copied_grid.temperature_nodes_k[0] == inverse_grid.temperature_nodes_k[0]
    assert copied_grid.property_values["enthalpy_j_kg"][0, 0] == \
        inverse_grid.property_values["enthalpy_j_kg"][0, 0]
    assert copied_grid.fingerprint == grid_fingerprint

    def require_grid_rejection(candidate, provider, reason):
        try:
            provider.use_inverse_grid(candidate)
        except ValueError:
            return
        raise AssertionError(f"Inverse grid with mismatched {reason} was admitted")

    reused_properties = CoolPropMixtureProperties(
        gas_composition, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
        inverse_temperature_bounds_k=(280., 320.),
    )
    assert reused_properties.use_inverse_grid(restored_grid) is restored_grid
    require_grid_rejection(MixtureInverseGrid(
        inverse_grid.composition_sha256,
        PropertyBasis(inverse_grid.property_basis.fluid + " altered",
                      inverse_grid.property_basis.reference_id,
                      inverse_grid.property_basis.spin_composition),
        inverse_grid.inverse_temperature_bounds_k,
        inverse_grid.pressure_nodes_pa, inverse_grid.temperature_nodes_k,
        inverse_grid.property_values,
    ), reused_properties, "property basis")
    require_grid_rejection(MixtureInverseGrid(
        inverse_grid.composition_sha256, inverse_grid.property_basis,
        (279., 320.), inverse_grid.pressure_nodes_pa,
        inverse_grid.temperature_nodes_k, inverse_grid.property_values,
    ), reused_properties, "temperature domain")
    nonmonotone_values = {name: np.array(values, copy=True)
                          for name, values in inverse_grid.property_values.items()}
    nonmonotone_values["enthalpy_j_kg"][0, 1] = nonmonotone_values["enthalpy_j_kg"][0, 0]
    try:
        MixtureInverseGrid(
            inverse_grid.composition_sha256, inverse_grid.property_basis,
            inverse_grid.inverse_temperature_bounds_k, inverse_grid.pressure_nodes_pa,
            inverse_grid.temperature_nodes_k, nonmonotone_values,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Nonmonotone inverse-grid property samples were admitted")
    grid_reference = properties.state_pt(4.2e6, 310.0)
    assert not np.any(inverse_grid.pressure_nodes_pa == grid_reference.pressure_pa)
    properties.clear_inverse_cache()
    grid_ph = properties.state_ph(grid_reference.pressure_pa, grid_reference.enthalpy_j_kg)
    grid_ps = properties.state_ps(grid_reference.pressure_pa, grid_reference.entropy_j_kg_k)
    grid_prho = properties.state_prho(grid_reference.pressure_pa, grid_reference.density_kg_m3)
    baseline_properties = CoolPropMixtureProperties(
        gas_composition, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
        inverse_temperature_bounds_k=(280., 320.), inverse_cache_size=0,
    )
    baseline = (
        baseline_properties.state_ph(grid_reference.pressure_pa, grid_reference.enthalpy_j_kg),
        baseline_properties.state_ps(grid_reference.pressure_pa, grid_reference.entropy_j_kg_k),
        baseline_properties.state_prho(grid_reference.pressure_pa, grid_reference.density_kg_m3),
    )
    inverse_fields = ("enthalpy_j_kg", "entropy_j_kg_k", "density_kg_m3")
    inverse_temperature_errors_k = []
    inverse_property_absolute_errors = {field: [] for field in inverse_fields}
    for accelerated, direct, field in zip((grid_ph, grid_ps, grid_prho), baseline,
                                          inverse_fields, strict=True):
        inverse_temperature_errors_k.append(
            abs(accelerated.temperature_k - direct.temperature_k),
        )
        inverse_property_absolute_errors[field].append(
            abs(getattr(accelerated, field) - getattr(direct, field)),
        )
        assert np.isclose(accelerated.temperature_k, grid_reference.temperature_k,
                          rtol=0., atol=2e-7)
        assert np.isclose(accelerated.temperature_k, direct.temperature_k,
                          rtol=0., atol=2e-7)
        assert np.isclose(getattr(accelerated, field), getattr(direct, field),
                          rtol=1e-10, atol=1e-7)
    reused_reference = reused_properties.state_pt(7.5e6, 315.0)
    reused_ph = reused_properties.state_ph(
        reused_reference.pressure_pa, reused_reference.enthalpy_j_kg,
    )
    assert np.isclose(reused_ph.temperature_k, reused_reference.temperature_k,
                      rtol=0., atol=2e-7)

    benchmark_grid_properties = CoolPropMixtureProperties(
        gas_composition, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
        inverse_temperature_bounds_k=(280., 320.), inverse_cache_size=0,
    )
    benchmark_grid_properties.use_inverse_grid(inverse_grid)
    benchmark_targets = tuple(
        (pressure, baseline_properties.state_pt(pressure, temperature))
        for pressure, temperature in (
            (2.0e6, 285.), (4.2e6, 295.), (7.5e6, 305.), (9.0e6, 315.),
        )
    )

    def measure_inverse_path(provider):
        flash_count = 0
        original_state_pt = provider.state_pt

        def counted_state_pt(pressure_pa, temperature_k):
            nonlocal flash_count
            flash_count += 1
            return original_state_pt(pressure_pa, temperature_k)

        provider.state_pt = counted_state_pt
        try:
            started = time.perf_counter()
            for pressure, target_state in benchmark_targets:
                provider.state_ph(pressure, target_state.enthalpy_j_kg)
                provider.state_ps(pressure, target_state.entropy_j_kg_k)
                provider.state_prho(pressure, target_state.density_kg_m3)
            elapsed = time.perf_counter() - started
        finally:
            provider.state_pt = original_state_pt
        return elapsed, flash_count

    baseline_timings, grid_timings = [], []
    baseline_flash_counts, grid_flash_counts = [], []
    # Warm both paths before collecting comparative timings; zero-capacity
    # inverse caches keep every measured target as a distinct calculation.
    measure_inverse_path(baseline_properties)
    measure_inverse_path(benchmark_grid_properties)
    for _ in range(3):
        ordered_paths = (
            ((baseline_properties, baseline_timings, baseline_flash_counts),
             (benchmark_grid_properties, grid_timings, grid_flash_counts))
            if len(baseline_timings) % 2 == 0 else
            ((benchmark_grid_properties, grid_timings, grid_flash_counts),
             (baseline_properties, baseline_timings, baseline_flash_counts))
        )
        for provider, timings, flash_counts in ordered_paths:
            elapsed, flashes = measure_inverse_path(provider)
            timings.append(elapsed)
            flash_counts.append(flashes)
    baseline_seconds = statistics.median(baseline_timings)
    grid_seconds = statistics.median(grid_timings)
    inversions_per_run = 3 * len(benchmark_targets)
    baseline_seconds_per_inverse = baseline_seconds / inversions_per_run
    grid_seconds_per_inverse = grid_seconds / inversions_per_run
    inverse_time_saved_per_query = baseline_seconds_per_inverse - grid_seconds_per_inverse
    grid_faster_excluding_preparation = inverse_time_saved_per_query > 0.
    grid_break_even_inverse_queries = (
        math.ceil(inverse_grid_preparation_seconds / inverse_time_saved_per_query)
        if grid_faster_excluding_preparation else None
    )
    properties.clear_inverse_grid()
    reused_properties.clear_inverse_grid()
    assert np.isclose(ph_state.temperature_k, state.temperature_k, rtol=0., atol=2e-7)
    assert np.isclose(ps_state.temperature_k, state.temperature_k, rtol=0., atol=2e-7)
    assert np.isclose(density_state.temperature_k, state.temperature_k, rtol=0., atol=2e-7)
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

    opening = NozzleOpening.circular(
        "h2-n2-validation-orifice", 0.01,
        effective_area_factor=0.8, area_basis_id="synthetic-contract-only",
    )
    release = HomogeneousIsentropicNozzle(properties).solve(
        state, back_pressure_pa=1.0e6, opening=opening,
    )
    assert np.isfinite(release.mass_flow_kg_s) and release.mass_flow_kg_s > 0.
    assert release.exit_state is not None
    assert release.exit_state.basis == properties.basis
    assert np.isclose(release.exit_state.entropy_j_kg_k, state.entropy_j_kg_k,
                      rtol=2e-6, atol=1e-5)
    assert abs(release.energy_residual_w) <= max(1e-6, abs(release.withdrawal_energy_w) * 1e-7)
    assert release.diagnostics.property_evaluations > 0
    from h2physics.adapters.finite_adsorption_vessel import FrozenGasBinding

    gas_binding = FrozenGasBinding.bind(
        properties, species=gas_composition.species, mole_fractions=gas_composition.mole_fractions,
        molar_masses_kg_mol=gas_composition.molar_masses_kg_mol,
        composition_id=gas_composition.composition_id,
    )
    assert gas_binding.property_basis == properties.basis
    assert gas_binding.composition_id == properties.composition_id
    bound_gas_state = gas_binding.state_pt(state.pressure_pa, state.temperature_k)
    assert bound_gas_state.basis == properties.basis
    assert bound_gas_state.phase in {"gas", "supercritical", "supercritical_gas"}
    from examples.finite_adsorption_vessel import AuthoredAbsoluteEquilibrium
    from h2physics.adapters.finite_adsorption_vessel import (
        AdsorptionVesselGeometry,
        FiniteAdsorptionVessel,
    )

    vessel = FiniteAdsorptionVessel(
        vessel_id="coolprop-mixture-binding-contract",
        geometry=AdsorptionVesselGeometry(
            0.12, 42., 0.035, 0.005, "synthetic-gas-binding-contract",
        ),
        adsorption=AuthoredAbsoluteEquilibrium(), gas=gas_binding,
    )
    snapshot = vessel.snapshot(state.pressure_pa, state.temperature_k)
    assert snapshot.gas_state.basis == properties.basis
    assert np.allclose(
        snapshot.total_component_mol,
        snapshot.free_gas_component_mol + snapshot.adsorbed_component_mol,
        rtol=1e-12, atol=1e-12,
    )
    mismatched_provider_inputs = (
        {"composition_id": "other-composition"},
        {"species": tuple(reversed(gas_composition.species)),
         "mole_fractions": tuple(reversed(gas_composition.mole_fractions)),
         "molar_masses_kg_mol": tuple(reversed(gas_composition.molar_masses_kg_mol))},
        {"mole_fractions": (0.6, 0.4)},
    )
    for changes in mismatched_provider_inputs:
        values = {
            "species": gas_composition.species,
            "mole_fractions": gas_composition.mole_fractions,
            "molar_masses_kg_mol": gas_composition.molar_masses_kg_mol,
            "composition_id": gas_composition.composition_id,
        }
        values.update(changes)
        try:
            FrozenGasBinding.bind(properties, **values)
        except ValueError:
            continue
        raise AssertionError(f"Provider/composition mismatch was admitted: {tuple(changes)}")
    unbounded = CoolPropMixtureProperties(
        gas_composition, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
    )
    try:
        unbounded.state_ps(state.pressure_pa, state.entropy_j_kg_k)
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Mixture inverse flash without an explicit temperature domain was admitted")
    invalid_flash_rejections = (
        (unbounded.state_pu, (True, 1.)),
        (unbounded.state_rho_u, (1., "not-energy")),
        (unbounded.state_rho_u, (0., 0.)),
    )
    for method, args in invalid_flash_rejections:
        try:
            method(*args)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid inputs reached an unsupported mixture flash")
    try:
        unbounded.state_pu(1e5, 0.)
    except NotImplementedError:
        pass
    else:
        raise AssertionError("PU inversion without a declared temperature branch was admitted")
    altered_composition = GasComposition(
        "other-h2-n2", gas_composition.species, gas_composition.mole_fractions, masses[:2],
    )
    altered_properties = CoolPropMixtureProperties(
        altered_composition, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
        inverse_temperature_bounds_k=(280., 320.),
    )
    try:
        altered_properties.use_inverse_grid(inverse_grid)
    except ValueError:
        pass
    else:
        raise AssertionError("An inverse grid from a different composition was attached")
    try:
        properties.basis.require_compatible(altered_properties.basis)
    except ValueError:
        pass
    else:
        raise AssertionError("Different mixture identities shared a thermodynamic basis")

    rejected = 0
    for args in (
        ("", ("H2",), (1.,), (2e-3,)),
        ("dup", ("H2", "H2"), (0.5, 0.5), (2e-3, 2e-3)),
        ("sum", ("H2", "N2"), (0.3, 0.6), (2e-3, 28e-3)),
        ("negative", ("H2",), (-0.01,), (2e-3,)),
        ("mass", ("H2",), (1.,), (0.,)),
        ("numeric-string", ("H2",), ("1.0",), (2e-3,)),
        ("complex", ("H2",), (1. + 0j,), (2e-3,)),
        ("boolean-object", ("H2",), np.array([True], dtype=object), (2e-3,)),
        ("mixed-boolean", ("H2", "N2"), (True, 0.5), (2e-3, 28e-3)),
    ):
        try:
            GasComposition(*args)
        except ValueError:
            rejected += 1
    assert rejected == 9
    for invalid_flow in (True, "1.0", 1.0 + 0j, (True, 1.0)):
        try:
            restored.component_molar_flows(invalid_flow)
        except ValueError:
            continue
        raise AssertionError("A non-real-numeric component flow was admitted")
    return ValidationOutcome(
        True,
        {"bookkeeping_molar_mass_kg_mol": restored.molar_mass_kg_mol,
         "coolprop_gas_molar_mass_kg_mol": gas_composition.molar_mass_kg_mol,
         "coolprop_version": properties.version,
         "inverse_grid_fingerprint": inverse_grid.fingerprint,
         "inverse_grid_composition_sha256": inverse_grid.composition_sha256,
         "inverse_grid_property_basis_reference": inverse_grid.property_basis.reference_id,
         "inverse_grid_archive_round_trip_fingerprint": restored_grid.fingerprint,
         "inverse_grid_pressure_nodes_pa": tuple(float(value)
                                                  for value in inverse_grid.pressure_nodes_pa),
         "inverse_grid_temperature_nodes_k": tuple(float(value)
                                                    for value in inverse_grid.temperature_nodes_k),
         "mole_flow_closure_mol_s": float(molar.sum()),
         "mass_flow_closure_kg_s": float(mass.sum()),
         "coolprop_mixture_density_kg_m3": state.density_kg_m3,
         "coolprop_mixture_cp_j_kg_k": state.cp_j_kg_k,
         "inverse_grid_preparation_seconds": inverse_grid_preparation_seconds,
         "baseline_inverse_seconds_per_call": baseline_seconds_per_inverse,
         "grid_inverse_seconds_per_call": grid_seconds_per_inverse,
         "baseline_pt_flashes_per_inverse": statistics.median(baseline_flash_counts) / inversions_per_run,
         "grid_pt_flashes_per_inverse": statistics.median(grid_flash_counts) / inversions_per_run,
         "inverse_grid_speedup_ratio": baseline_seconds / grid_seconds,
         "inverse_grid_faster_excluding_preparation": grid_faster_excluding_preparation,
         "inverse_grid_break_even_inverse_queries": grid_break_even_inverse_queries,
         "maximum_inverse_temperature_difference_k": max(inverse_temperature_errors_k),
         "maximum_inverse_enthalpy_difference_j_kg":
             max(inverse_property_absolute_errors["enthalpy_j_kg"]),
         "maximum_inverse_entropy_difference_j_kg_k":
             max(inverse_property_absolute_errors["entropy_j_kg_k"]),
         "maximum_inverse_density_difference_kg_m3":
             max(inverse_property_absolute_errors["density_kg_m3"]),
         "adsorption_vessel_total_component_mol": float(snapshot.total_component_mol.sum()),
         "inverse_cache_reuse_hits": cache_after_hit["hits"],
         "invalid_compositions_rejected": rejected},
        ("Synthetic composition and same-library inverse comparison only; reported break-even applies only to this benchmark and excludes no future workload costs; no independent EOS/release-data validation or universal performance claim.",),
    )
