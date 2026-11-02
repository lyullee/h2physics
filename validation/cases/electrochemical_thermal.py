"""Deferred finite electrochemical-stack thermal cases; definitions are inert."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Authored lumped heat capacity and conductance; no stack thermal calibration.",
    "Held current/coolant stages; no controller or coolant inventory.",
    "No crossover, degradation, spatial cell temperature or two-phase water transport.",
)


def cases():
    definitions = (
        ("electrochemical-thermal-adiabatic", "validate_adiabatic",
         ("shared polarization/Faraday owner", "analytic finite heat inventory")),
        ("electrochemical-thermal-cooldown", "validate_cooldown",
         ("analytic zero-current Newton cooling", "signed coolant boundary")),
        ("electrochemical-thermal-reversal", "validate_reversal",
         ("warmer coolant heat reversal", "finite auxiliary heat")),
        ("electrochemical-thermal-domains", "validate_domains",
         ("contiguous clock", "temperature/current/domain rejection")),
    )
    return tuple(ValidationCase(
        identifier=name,
        profile="electrochemical-thermal",
        entrypoint=__name__+":"+entry,
        invariants=invariants,
    ) for name, entry, invariants in definitions)


def _problem(*, conductance=0.0):
    from h2physics.electrochemical_thermal import FiniteThermalStack, ThermalStackBoundary
    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry

    stack = HydrogenStack(
        StackGeometry(series_cells=10, active_area_m2=1.0,
                      hydrogen_molar_mass_kg_mol=0.00201588),
        lambda temperature_k: ReactionEnergy(
            200_000.0, 240_000.0, "authored:thermal", "vapor"
        ),
        {"held-loss": lambda current_density_a_m2, temperature_k: 0.4 if current_density_a_m2 else 0.0},
    )
    boundary = ThermalStackBoundary(
        heat_capacity_j_k=20_000.0,
        conductance_w_k=lambda stack_k, coolant_k: conductance,
        temperature_bounds_k=(250.0, 400.0),
        reference_id="authored:lumped-stack-U",
        coolant_boundary_id="authored:held-coolant",
    )
    return FiniteThermalStack(stack, boundary, energy_tolerance_j=1e-4)


def _stage(**changes):
    from h2physics.electrochemical_thermal import ThermalStackStage

    values = dict(identifier="held", start_s=0.0, end_s=20.0,
                  current_density_a_m2=100.0, coolant_temperature_k=300.0,
                  mode="electrolysis")
    values.update(changes)
    return ThermalStackStage(**values)


def _outcome(trace, **extra):
    metrics = dict(final_temperature_k=trace.final_temperature_k,
                   generated_heat_j=trace.generated_heat_j,
                   coolant_heat_out_j=trace.coolant_heat_out_j,
                   energy_residual_j=trace.energy_residual_j)
    metrics.update(extra)
    return ValidationOutcome(accepted=True, metrics=metrics, limitations=LIMITS)


def validate_adiabatic(*, work_directory, **parameters):
    model = _problem(conductance=0.0)
    trace = model.run(300.0, (_stage(),))
    step = trace.stages[0]
    expected_heat = step.initial_stack_result.unallocated_energy_rate_w*20.0
    assert step.initial_stack_result.mode == "electrolysis"
    assert abs(trace.generated_heat_j-expected_heat) < 1e-5
    assert abs(trace.internal_energy_change_j-expected_heat) < 1e-5
    assert abs(trace.final_temperature_k-(300.0+expected_heat/20_000.0)) < 1e-8
    assert abs(trace.energy_residual_j) < 1e-5
    assert trace.status == "implemented_unverified"
    return _outcome(trace, analytic_temperature_k=300.0+expected_heat/20_000.0)


def validate_cooldown(*, work_directory, **parameters):
    import math

    model = _problem(conductance=100.0)
    command = _stage(current_density_a_m2=0.0, end_s=100.0)
    trace = model.run(350.0, (command,))
    expected = 300.0+50.0*math.exp(-100.0*100.0/20_000.0)
    assert abs(trace.final_temperature_k-expected) < 2e-6
    assert trace.generated_heat_j == 0.0
    assert trace.coolant_heat_out_j > 0.0
    assert abs(trace.energy_residual_j) < 1e-5
    return _outcome(trace, analytic_temperature_k=expected)


def validate_reversal(*, work_directory, **parameters):
    model = _problem(conductance=80.0)
    command = _stage(current_density_a_m2=0.0, coolant_temperature_k=340.0,
                     auxiliary_heat_into_w=20.0)
    trace = model.run(300.0, (command,))
    assert trace.coolant_heat_out_j < 0.0
    assert trace.auxiliary_heat_into_j == 400.0
    assert trace.final_temperature_k > trace.initial_temperature_k
    assert abs(trace.energy_residual_j) < 1e-5
    return _outcome(trace, heat_reversal=True)


def validate_domains(*, work_directory, **parameters):
    model = _problem()
    rejected = 0
    invalid = (
        lambda: model.run(249.0, (_stage(),)),
        lambda: model.run(300.0, (_stage(current_density_a_m2=-1.0),)),
        lambda: model.run(300.0, (_stage(faradaic_efficiency=0.9),)),
        lambda: model.run(300.0, (_stage(end_s=10.0), _stage(start_s=11.0))),
    )
    for call in invalid:
        try:
            call()
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("An invalid thermal-stack boundary was admitted")
    return ValidationOutcome(accepted=True, metrics={"rejected_boundaries": rejected},
                             limitations=LIMITS)
