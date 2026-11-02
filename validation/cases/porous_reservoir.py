"""Deferred synthetic balance contracts for radial porous-reservoir kernels."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="porous-reservoir-single-cell-ledger",
            profile="porous-reservoir",
            entrypoint=__name__ + ":validate_single_cell_ledger",
            invariants=(
                "single-cell isothermal ideal-gas pressure follows injected mass",
                "cell inventory change equals signed prescribed well mass",
                "each nonlinear cell residual is checked against that cell's old/new inventory scale without a fixed one-kilogram floor",
                "cumulative injection and per-step closure are retained",
                "outer-boundary inflow and outflow use declared donor temperatures and close mass",
                "only the completed model run issues a current, unchanged result",
                "geometry and pressure schedule reject invalid shape/order/bounds",
                "no porous geology or site qualification is inferred",
            ),
        ),
        ValidationCase(
            identifier="porous-reservoir-property-provider-binding",
            profile="porous-reservoir",
            entrypoint=__name__ + ":validate_property_provider_binding",
            parameters={},
            invariants=(
                "shared CoolProp HEOS PropertyProvider supplies each gas density and viscosity state",
                "property basis is retained and must remain compatible",
                "single-phase gas-like state gate rejects liquid/two-phase states",
                "zero-flow one-cell inventory remains mass-conservative",
                "provider integration does not imply geological or site qualification",
            ),
        ),
        ValidationCase(
            identifier="porous-reservoir-pressure-driven-well",
            profile="porous-reservoir",
            entrypoint=__name__ + ":validate_pressure_driven_well",
            invariants=(
                "well pressure is an explicit inner radial face boundary on the reservoir clock",
                "Darcy flow sign is positive into the reservoir and reverses for lower well pressure",
                "injection donor density and viscosity use the caller-declared well temperature",
                "the backward-Euler well flow closes the cell and cumulative mass ledgers",
                "schedule requires exactly one of signed rate or pressure boundary and enforces pressure bounds",
                "single-phase fixed-temperature Darcy scope does not imply wellbore or site qualification",
            ),
        ),
        ValidationCase(
            identifier="porous-reservoir-coolprop-dynamic-refinement",
            profile="porous-reservoir",
            entrypoint=__name__ + ":validate_coolprop_dynamic_refinement",
            invariants=(
                "direct HEOS density and viscosity drive nonzero radial injection",
                "closed outer boundary retains the exact integrated prescribed well mass",
                "backward-Euler time refinement reduces final-pressure differences",
                "radial mesh refinement reduces common-receptor pressure-profile differences",
                "every accepted run retains original result and checked nonlinear cell balances",
                "numerical self-convergence is not independent geological validation",
            ),
        ),
    )


def validate_single_cell_ledger(*, work_directory, **parameters):
    del work_directory, parameters
    import math

    import numpy as np

    from h2physics.storage.porous_reservoir import (
        PorousReservoir,
        PorousReservoirGeometry,
        PorousReservoirSchedule,
    )

    temperature = 300.0
    molar_mass = 0.00201588
    gas_constant = 8.31446261815324
    geometry = PorousReservoirGeometry(
        radial_faces_m=np.array([0.1, 1.0]), thickness_m=10.0,
        porosity=np.array([0.2]), permeability_m2=np.array([1e-13]),
        temperature_k=np.array([temperature]), evidence_id="synthetic geometry")
    dt = 20.0
    flow = 1e-5
    initial_pressure = 2e6
    schedule = PorousReservoirSchedule(
        time_s=np.array([0.0, dt]), initial_pressure_pa=np.array([initial_pressure]),
        minimum_pressure_pa=1e5, maximum_pressure_pa=1e8,
        well_mass_flow_kg_s=np.array([flow, flow]), clock_id="synthetic clock")
    model = PorousReservoir(
        geometry=geometry,
        density_kg_m3=lambda pressure, temp: pressure * molar_mass / (gas_constant * temp),
        viscosity_pa_s=lambda pressure, temp: 9e-6,
        property_evidence_id="synthetic ideal-gas callbacks")
    result = model.run(schedule)
    assert result.require_current() is result
    volume = float(geometry.pore_volume_m3[0])
    expected_pressure = initial_pressure + flow * dt * gas_constant * temperature / (molar_mass * volume)
    assert math.isclose(result.pressure_pa[-1, 0], expected_pressure, rel_tol=1e-8)
    assert math.isclose(result.cumulative_well_mass_kg[-1], flow * dt, rel_tol=1e-14)
    assert result.cumulative_outer_boundary_mass_kg[-1] == 0.0
    assert abs(result.per_step_mass_residual_kg[0]) < 1e-10
    assert abs(float(result.cell_gas_mass_kg[-1, 0] - result.cell_gas_mass_kg[0, 0]) - flow * dt) < 1e-10
    wrong_cell_count = PorousReservoirSchedule(
        time_s=np.array([0.0, dt]),
        initial_pressure_pa=np.array([initial_pressure, initial_pressure]),
        minimum_pressure_pa=1e5, maximum_pressure_pa=1e8,
        well_mass_flow_kg_s=np.array([flow, flow]), clock_id="wrong-cell-count")
    try:
        model.run(wrong_cell_count)
    except ValueError as error:
        assert "one initial pressure is required per radial cell" in str(error)
    else:
        raise AssertionError("Initial pressure count was not bound to radial geometry")
    from dataclasses import replace
    try:
        replace(result)
    except ValueError:
        pass
    else:
        raise AssertionError("a cloned porous-reservoir result reused its consumed issuer")
    object.__setattr__(result, "property_evidence_id", "altered evidence")
    try:
        result.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("a changed porous-reservoir result retained currentness")

    open_boundary_schedule = PorousReservoirSchedule(
        time_s=np.array([0.0, 0.01]), initial_pressure_pa=np.array([initial_pressure]),
        minimum_pressure_pa=1e5, maximum_pressure_pa=1e8,
        well_mass_flow_kg_s=np.array([0.0, 0.0]), clock_id="outer-boundary clock")
    inflow = model.run(
        open_boundary_schedule, outer_pressure_pa=np.array([3e6, 3e6]),
        outer_temperature_k=330.0)
    assert inflow.outer_boundary_temperature_k == 330.0
    assert inflow.cumulative_outer_boundary_mass_kg[-1] > 0.0
    assert abs(inflow.per_step_mass_residual_kg[0]) < 1e-9
    outflow = model.run(
        open_boundary_schedule, outer_pressure_pa=np.array([1e6, 1e6]),
        outer_temperature_k=270.0)
    assert outflow.outer_boundary_temperature_k == 270.0
    assert outflow.cumulative_outer_boundary_mass_kg[-1] < 0.0
    assert abs(outflow.per_step_mass_residual_kg[0]) < 1e-9

    invalid_inputs = (
        lambda: PorousReservoirGeometry(
            radial_faces_m=np.array([1.0, 0.5]), thickness_m=10.0,
            porosity=np.array([0.2]), permeability_m2=np.array([1e-13]),
            temperature_k=np.array([temperature]), evidence_id="invalid"),
        lambda: PorousReservoirSchedule(
            time_s=np.array([0.0, 0.0]), initial_pressure_pa=np.array([initial_pressure]),
            minimum_pressure_pa=1e5, maximum_pressure_pa=1e8,
            well_mass_flow_kg_s=np.array([flow, flow]), clock_id="invalid"),
        lambda: PorousReservoirSchedule(
            time_s=np.array([0.0, dt]), initial_pressure_pa=np.array([initial_pressure]),
            minimum_pressure_pa=1e5, maximum_pressure_pa=1e8,
            well_mass_flow_kg_s=np.array([flow]), clock_id="misaligned-flow"),
    )
    for construct_invalid in invalid_inputs:
        try:
            construct_invalid()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid porous-reservoir input was accepted")
    return ValidationOutcome(
        True,
        {
            "final_pressure_pa": float(result.pressure_pa[-1, 0]),
            "analytic_pressure_pa": expected_pressure,
            "well_injected_mass_kg": float(result.cumulative_well_mass_kg[-1]),
            "outer_injected_mass_kg": float(inflow.cumulative_outer_boundary_mass_kg[-1]),
            "outer_withdrawn_mass_kg": float(outflow.cumulative_outer_boundary_mass_kg[-1]),
            "maximum_absolute_mass_residual_kg": max(
                abs(float(result.per_step_mass_residual_kg[0])),
                abs(float(inflow.per_step_mass_residual_kg[0])),
                abs(float(outflow.per_step_mass_residual_kg[0])),
            ),
        },
        (
            "Synthetic single-cell ideal-gas and boundary-ledger contract only; no reservoir-site validation.",
            "Pressure-driven inner-well behavior is covered by a separate contract; no multiphase behavior is implied.",
        ),
    )


def validate_property_provider_binding(*, work_directory, **parameters):
    """CoolProp-to-reservoir wiring; not independent EOS or site validation."""
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.storage.porous_reservoir import (
        PorousReservoir,
        PorousReservoirGeometry,
        PorousReservoirSchedule,
    )
    from h2physics.thermo.coolprop import CoolPropProperties

    provider = CoolPropProperties("Hydrogen", backend="HEOS")
    temperature = 300.
    geometry = PorousReservoirGeometry(
        radial_faces_m=np.array([.1, 1.]), thickness_m=10.,
        porosity=np.array([.2]), permeability_m2=np.array([1e-13]),
        temperature_k=np.array([temperature]),
        evidence_id="synthetic-property-provider-geometry",
    )
    schedule = PorousReservoirSchedule(
        time_s=np.array([0., 1.]), initial_pressure_pa=np.array([2e6]),
        minimum_pressure_pa=1e5, maximum_pressure_pa=1e8,
        well_mass_flow_kg_s=np.array([0., 0.]),
        clock_id="synthetic-property-provider-clock",
    )
    model = PorousReservoir.from_property_provider(
        geometry=geometry, property_provider=provider,
        property_evidence_id=(
            f"CoolProp:{provider.version}:{provider.backend}:"
            f"{provider.basis.fluid}:{provider.basis.reference_id}"
        ),
    )
    result = model.run(schedule)
    assert result.require_current() is result
    assert np.array_equal(result.pressure_pa[0], result.pressure_pa[-1])
    assert np.array_equal(result.cell_gas_mass_kg[0], result.cell_gas_mass_kg[-1])
    assert np.all(result.per_step_mass_residual_kg == 0.)
    assert model.property_provider is provider
    class LiquidPhaseProvider:
        basis = provider.basis

        def state_pt(self, pressure_pa, temperature_k):
            return replace(provider.state_pt(pressure_pa, temperature_k), phase="liquid")

        def state_ph(self, pressure_pa, enthalpy_j_kg):
            return provider.state_ph(pressure_pa, enthalpy_j_kg)

        def state_ps(self, pressure_pa, entropy_j_kg_k):
            return provider.state_ps(pressure_pa, entropy_j_kg_k)

    liquid_model = PorousReservoir.from_property_provider(
        geometry=geometry, property_provider=LiquidPhaseProvider(),
        property_evidence_id="synthetic-rejected-liquid-phase",
    )
    try:
        liquid_model.run(schedule)
    except ValueError as error:
        assert "does not admit EOS phase" in str(error)
        liquid_phase_rejected = True
    else:
        raise AssertionError("the single-gas Darcy owner accepted a liquid phase")
    return ValidationOutcome(
        True,
        {
            "coolprop_backend": provider.backend,
            "coolprop_version": provider.version,
            "property_basis": provider.basis,
            "pressure_pa": float(result.pressure_pa[-1, 0]),
            "mass_residual_kg": float(result.per_step_mass_residual_kg[0]),
            "liquid_phase_rejected": liquid_phase_rejected,
        },
        (
            "Synthetic isothermal zero-flow provider wiring only; not an independent EOS or reservoir validation.",
            "The HEOS property provider supplies single-phase state density and viscosity; multiphase porous flow is excluded.",
        ),
    )


def validate_pressure_driven_well(*, work_directory, **parameters):
    """Deferred synthetic inner-boundary injection/withdrawal contract."""
    del work_directory, parameters
    import numpy as np

    from h2physics.storage.porous_reservoir import (
        PorousReservoir,
        PorousReservoirGeometry,
        PorousReservoirSchedule,
    )

    temperature = 300.0
    geometry = PorousReservoirGeometry(
        radial_faces_m=np.array([0.1, 1.0]), thickness_m=10.0,
        porosity=np.array([0.2]), permeability_m2=np.array([1e-13]),
        temperature_k=np.array([temperature]), evidence_id="synthetic well-boundary geometry",
    )
    dt = 0.1
    initial_pressure = 2.0e6
    model = PorousReservoir(
        geometry=geometry,
        density_kg_m3=lambda pressure, temp: pressure * 0.00201588 / (8.31446261815324 * temp),
        viscosity_pa_s=lambda pressure, temp: 9e-6,
        property_evidence_id="synthetic ideal-gas callbacks",
    )

    def run(well_pressure, clock):
        schedule = PorousReservoirSchedule(
            time_s=np.array([0.0, dt]),
            initial_pressure_pa=np.array([initial_pressure]),
            minimum_pressure_pa=1.0e5, maximum_pressure_pa=1.0e8,
            well_mass_flow_kg_s=None, clock_id=clock,
            well_pressure_pa=np.array([well_pressure, well_pressure]),
        )
        return model.run(schedule, well_temperature_k=330.0)

    injection = run(3.0e6, "well-injection clock")
    withdrawal = run(1.0e6, "well-withdrawal clock")
    assert injection.well_boundary_temperature_k == 330.0
    assert injection.cumulative_well_mass_kg[-1] > 0.0
    assert withdrawal.cumulative_well_mass_kg[-1] < 0.0
    assert injection.pressure_pa[-1, 0] > initial_pressure
    assert withdrawal.pressure_pa[-1, 0] < initial_pressure
    for result in (injection, withdrawal):
        assert abs(result.per_step_mass_residual_kg[0]) < 1e-10
        assert result.require_current() is result

    invalid = (
        lambda: PorousReservoirSchedule(
            time_s=np.array([0.0, dt]), initial_pressure_pa=np.array([initial_pressure]),
            minimum_pressure_pa=1e5, maximum_pressure_pa=1e8,
            well_mass_flow_kg_s=np.zeros(2), clock_id="both-boundaries",
            well_pressure_pa=np.full(2, initial_pressure),
        ),
        lambda: PorousReservoirSchedule(
            time_s=np.array([0.0, dt]), initial_pressure_pa=np.array([initial_pressure]),
            minimum_pressure_pa=1e5, maximum_pressure_pa=1e8,
            well_mass_flow_kg_s=None, clock_id="outside-bounds",
            well_pressure_pa=np.full(2, 2e8),
        ),
    )
    for construct in invalid:
        try:
            construct()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid pressure-driven well schedule was accepted")
    return ValidationOutcome(
        True,
        {
            "injection_well_mass_kg": float(injection.cumulative_well_mass_kg[-1]),
            "withdrawal_well_mass_kg": float(withdrawal.cumulative_well_mass_kg[-1]),
            "injection_cell_pressure_pa": float(injection.pressure_pa[-1, 0]),
            "withdrawal_cell_pressure_pa": float(withdrawal.pressure_pa[-1, 0]),
            "maximum_absolute_mass_residual_kg": max(
                abs(float(injection.per_step_mass_residual_kg[0])),
                abs(float(withdrawal.per_step_mass_residual_kg[0])),
            ),
        },
        (
            "Synthetic single-cell boundary contract only; no wellbore or reservoir validation.",
            "Single-phase Darcy flow with explicit donor temperature; multiphase flow is excluded.",
        ),
    )


def validate_coolprop_dynamic_refinement(*, work_directory, **parameters):
    """Direct-EOS radial injection with fixed geometry and numerical refinement."""
    del work_directory, parameters
    import numpy as np

    from h2physics.storage.porous_reservoir import (
        PorousReservoir,
        PorousReservoirGeometry,
        PorousReservoirSchedule,
    )
    from h2physics.thermo import CoolPropProperties

    provider = CoolPropProperties("Hydrogen")
    duration, inlet_rate, temperature = 10., 1e-3, 300.

    def run(cell_count, step_count):
        geometry = PorousReservoirGeometry(
            radial_faces_m=np.geomspace(.1, 1., cell_count+1), thickness_m=10.,
            porosity=np.full(cell_count, .2), permeability_m2=np.full(cell_count, 1e-15),
            temperature_k=np.full(cell_count, temperature),
            evidence_id="authored-homogeneous-radial-refinement-geometry")
        schedule = PorousReservoirSchedule(
            time_s=np.linspace(0., duration, step_count+1),
            initial_pressure_pa=np.full(cell_count, 2e6),
            minimum_pressure_pa=1e5, maximum_pressure_pa=1e7,
            well_mass_flow_kg_s=np.full(step_count+1, inlet_rate),
            clock_id="authored-dynamic-HEOS-injection-clock")
        model = PorousReservoir.from_property_provider(
            geometry=geometry, property_provider=provider,
            property_evidence_id=provider.basis.reference_id)
        result = model.run(schedule, max_nfev=1000, xtol=1e-12, ftol=1e-12, gtol=1e-12)
        assert result.require_current() is result
        assert np.isclose(result.cumulative_well_mass_kg[-1], duration*inlet_rate,
                          rtol=1e-12, atol=1e-14)
        assert result.cumulative_outer_boundary_mass_kg[-1] == 0.
        mass_change = float(np.sum(result.cell_gas_mass_kg[-1]-result.cell_gas_mass_kg[0]))
        closure = abs(mass_change-duration*inlet_rate)
        assert closure < 1e-8
        assert result.pressure_pa[-1, 0] > result.pressure_pa[0, 0]
        assert np.all(result.pressure_pa[-1] >= result.pressure_pa[0]-1e-5)
        return result, closure

    temporal = tuple(run(4, steps) for steps in (8, 16, 32))
    temporal_differences = tuple(float(np.max(np.abs(a[0].pressure_pa[-1]-b[0].pressure_pa[-1])))
                                 for a, b in zip(temporal[:-1], temporal[1:], strict=True))
    assert 0. < temporal_differences[1] < temporal_differences[0]
    spatial = tuple(run(cells, 64) for cells in (4, 8, 16))
    receptors = np.geomspace(.15, .7, 9)
    profiles = tuple(np.interp(np.log(receptors), np.log(result.geometry.radial_centers_m),
                               result.pressure_pa[-1]) for result, _closure in spatial)
    spatial_differences = tuple(float(np.max(np.abs(a-b)))
                                for a, b in zip(profiles[:-1], profiles[1:], strict=True))
    assert 0. < spatial_differences[1] < spatial_differences[0]
    runs = temporal+spatial
    return ValidationOutcome(True, {
        "coolprop_version": provider.version, "coolprop_backend": provider.backend,
        "injected_mass_kg": duration*inlet_rate,
        "maximum_cumulative_mass_error_kg": max(closure for _result, closure in runs),
        "maximum_step_mass_residual_kg": max(float(np.max(np.abs(result.per_step_mass_residual_kg)))
                                             for result, _closure in runs),
        "time_refinement_step_counts": (8, 16, 32),
        "time_pressure_differences_pa": temporal_differences,
        "observed_time_self_convergence_order": float(np.log2(temporal_differences[0]/temporal_differences[1])),
        "radial_refinement_cell_counts": (4, 8, 16),
        "common_receptor_radii_m": tuple(float(r) for r in receptors),
        "radial_pressure_differences_pa": spatial_differences,
        "fine_first_cell_pressure_pa": float(spatial[-1][0].pressure_pa[-1, 0]),
    }, (
        "Numerical refinement under authored homogeneous permeability and porosity only",
        "Held temperature and prescribed injection; no thermal, geomechanical or multiphase closure",
        "Common-receptor pressures use bounded log-radius interpolation across cell centers",
        "This is self-convergence against the native EOS, not independent experimental or site validation",
    ))

