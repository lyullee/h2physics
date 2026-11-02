"""Metadata-only deferred microbial-cell case catalog; no local execution."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Synthetic biology/cathode/caloric fixture; no qualified organism/broth/electrode data.",
    "Fixed activity, anode potential, isothermal fixed-P batch; no pH/ATP/transport/utility model.",
    "One cathodic H2 pathway, no methane/crossover/reoxidation or measured harvest recovery.",
    "Implemented_unverified; cases defined for later HPC execution only.",
)


def cases():
    definitions = (
        (
            "microbial-native-charge",
            "validate_charge",
            ("actual Cantera cathode", "electron/H2/Faraday closure"),
        ),
        (
            "microbial-biomass-energy",
            "validate_biomass_energy",
            ("finite biomass/substrate", "phase enthalpy and electrical work"),
        ),
        (
            "microbial-disconnected",
            "validate_disconnected",
            ("explicit circuit isolation", "no inferred H2 generation"),
        ),
        (
            "microbial-finite-failure",
            "validate_finite_failure",
            ("finite shared reactants", "original native failure retention"),
        ),
        (
            "microbial-boundary-guards",
            "validate_guards",
            ("kinetic/phase/clock/reference guards", "no implicit normalization"),
        ),
        (
            "microbial-original-result-binding",
            "validate_original_result_binding",
            (
                "actual geometry/owner/admission retained",
                "original identity and mutable cache/native state rejection",
                "no verification model replay",
                "weak producer registration lifecycle",
            ),
        ),
    )
    return tuple(
        ValidationCase(
            identifier=name,
            profile="microbial-cell",
            entrypoint=__name__ + ":" + entry,
            parameters={},
            invariants=invariants,
        )
        for name, entry, invariants in definitions
    )


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _problem(**parameters):
    from examples.microbial_cell import build_problem

    return build_problem(**parameters)


def validate_charge(*, work_directory, **parameters):
    from h2physics.constants import FARADAY_C_MOL

    model, initial, stages = _problem()
    trace = model.run(initial, stages)
    _require(
        trace.native_cathode is model.cathode and trace.kernel is model.kernel,
        "Actual object ownership",
    )
    _require(trace.hydrogen_generated_mol > 0, "Positive finite H2 generation")
    for step in trace.steps:
        _require(
            step.cathode.native_interface is model.cathode.interface,
            "Native surface result identity",
        )
        _require(step.native_root_result.converged, "Actual native current root convergence")
        charge = step.current_a * (step.stage.end_s - step.stage.start_s)
        _require(
            abs(charge / FARADAY_C_MOL - 2 * step.hydrogen_generated_mol) < 1e-10,
            "Independent shared-constant Faraday count",
        )
        _require(abs(step.electron_residual_mol) < 1e-10, "Native ionic/electronic H2 balance")
    _require(
        trace.initial.amounts_mol["hydrogen"] > 0
        and trace.hydrogen_generated_mol != trace.final.amounts_mol["hydrogen"],
        "Startup H2 is not generated H2",
    )
    return ValidationOutcome(
        True,
        {
            "generated_H2_mol": trace.hydrogen_generated_mol,
            "transported_electron_mol": trace.transferred_electrons_mol,
            "maximum_current_residual_a": max(abs(s.current_residual_a) for s in trace.steps),
        },
        LIMITS,
    )


def validate_biomass_energy(*, work_directory, **parameters):
    model, initial, stages = _problem()
    trace = model.run(initial, stages)
    growth = sum(s.biomass_generated_mol for s in trace.steps)
    _require(
        abs(trace.final.amounts_mol["biomass"] - initial.amounts_mol["biomass"] - growth) < 1e-12,
        "Biomass formula-unit stock",
    )
    expected_substrate = trace.hydrogen_generated_mol / 2.0 + 5.0 * growth
    _require(
        abs(
            initial.amounts_mol["substrate"]
            - trace.final.amounts_mol["substrate"]
            - expected_substrate
        )
        < 1e-12,
        "Independent net stoichiometric growth/current substrate split",
    )
    h = model.caloric.enthalpies_j_mol(300.0, 1e5)
    change = sum(
        (
            trace.final.amounts_mol.get(s.identifier, 0.0)
            - initial.amounts_mol.get(s.identifier, 0.0)
        )
        * value
        for s, value in zip(model.species, h, strict=True)
    )
    _require(
        abs(change - trace.electric_work_into_j - trace.isothermal_heat_required_into_j) < 1e-7,
        "Independent phase-specific finite endpoint enthalpy ledger",
    )
    _require(
        abs(trace.electron_equivalent_residual_mol) < 1e-10,
        "Substrate/biomass/product reducing equivalents",
    )
    return ValidationOutcome(
        True,
        {
            "biomass_generated_mol": growth,
            "substrate_consumed_mol": expected_substrate,
            "electric_work_j": trace.electric_work_into_j,
            "required_heat_j": trace.isothermal_heat_required_into_j,
        },
        LIMITS,
    )


def validate_disconnected(*, work_directory, **parameters):
    model, initial, stages = _problem(catabolic_parameter=0.0, growth_parameter=0.0)
    trace = model.run(initial, tuple(replace(s, connected=False) for s in stages))
    _require(trace.final.amounts_mol == trace.initial.amounts_mol, "Isolated batch inventory")
    _require(
        trace.hydrogen_generated_mol == 0 and trace.electric_work_into_j == 0,
        "No spontaneous electrical/H2 boundary",
    )
    _require(
        all(s.cathode is None and not s.cathode_trials for s in trace.steps),
        "No claimed equilibrium native solve when disconnected",
    )
    return ValidationOutcome(True, {"generated_H2_mol": 0.0, "native_cathode_calls": 0}, LIMITS)


def validate_finite_failure(*, work_directory, **parameters):
    from h2physics.adapters.microbial_cell import MicrobialCellError

    model, initial, stages = _problem()
    first = model.run(initial, stages[:1])
    # Native-positive first stage is retained, then a caller-supplied unbracketed
    # potential interval must fail without a fabricated electrochemical point.
    bad = replace(stages[1], cathode_potential_bracket_v=(10.0, 11.0))
    try:
        model.run(initial, (stages[0], bad))
    except MicrobialCellError as error:
        _require(
            error.__cause__ is not None and len(error.completed_steps) == 1,
            "Completed prefix and original cause",
        )
        _require(
            error.cathode_trials or error.native_cathode.interface is not None,
            "Actual failed native context",
        )
    else:
        raise AssertionError("Unavailable cathode root was silently replaced")
    tiny = replace(initial, amounts_mol={**initial.amounts_mol, "substrate": 1e-15})
    try:
        model.run(tiny, stages)
    except MicrobialCellError as error:
        _require(
            error.__cause__ is not None and not error.completed_steps,
            "Finite substrate failure prefix",
        )
    else:
        raise AssertionError("Growth consumed unavailable substrate or clipped a trial")
    return ValidationOutcome(
        True,
        {
            "retained_completed_native_steps": 1,
            "baseline_first_H2_mol": first.hydrogen_generated_mol,
        },
        LIMITS,
    )


def validate_guards(*, work_directory, **parameters):
    from h2physics.adapters.microbial_cell import MicrobialCellError

    model, initial, stages = _problem()
    rejected = 0
    for operation in (
        lambda: model.run(replace(initial, energy_basis_id="foreign-reference"), stages),
        lambda: model.run(initial, (replace(stages[0], clock_id="foreign-clock"),)),
        lambda: replace(stages[0], native_phase_mole_fractions={"product": {"H2": 0.8}}),
        lambda: model.run(replace(initial, temperature_k=340.0), stages),
        lambda: model.run(
            replace(initial, amounts_mol={**initial.amounts_mol, "biomass": 0.0}), stages
        ),
    ):
        try:
            operation()
        except (ValueError, MicrobialCellError):
            rejected += 1
        else:
            raise AssertionError("Invalid microbial/electrode boundary accepted")
    return ValidationOutcome(True, {"negative_boundaries_rejected": rejected}, LIMITS)


def validate_original_result_binding(*, work_directory, **parameters):
    import gc
    import weakref

    from h2physics.adapters.microbial_cell import MicrobialResultVerificationError

    model, initial, stages = _problem()
    trace = model.run(initial, stages)
    _require(
        trace.owner is model and trace.geometry is model.geometry, "Actual owner and StackGeometry"
    )
    _require(trace.admission.tolerances is model.tolerances, "Actual admission tolerance binding")
    _require(
        model.verify_result(trace) is trace and trace.require_current() is trace,
        "Original trace identity",
    )
    _require(model.require_current() is model, "Producer current definition identity")
    rejected = 0

    def rejects(value):
        nonlocal rejected
        try:
            value.require_current()
        except MicrobialResultVerificationError as error:
            _require(error.result is value, "Rejected actual result retained")
            rejected += 1
        else:
            raise AssertionError("Changed original/native result binding was accepted")

    variants = [
        replace(trace, hydrogen_generated_mol=trace.hydrogen_generated_mol + 0.01),
        replace(
            trace,
            geometry=replace(trace.geometry, active_area_m2=trace.geometry.active_area_m2 * 2),
        ),
        replace(trace, owner=object()),
        replace(trace, status="validated"),
        replace(trace),
    ]
    for variant in variants:
        rejects(variant)
    variants.clear()
    variant = None

    root = trace.steps[0].native_root_result
    root_value = root.root
    root.root = root_value + 0.01
    rejects(trace)
    root.root = root_value
    _require(
        trace.require_current() is trace, "Restored original root cache, without native replay"
    )

    rates = trace.steps[0].cathode.native_production_rates_kmol_m2_s[model.cathode.phase_names[0]]
    saved, writable = rates.copy(), rates.flags.writeable
    rates.setflags(write=True)
    rates[0] += 1e-9
    rejects(trace)
    rates[:] = saved
    rates.setflags(write=writable)
    _require(trace.require_current() is trace, "Restored retained native rate array")

    geometry = model.geometry
    model.geometry = replace(geometry, active_area_m2=geometry.active_area_m2 * 2)
    rejects(trace)
    model.geometry = geometry
    function = model.caloric.functions[0]
    defaults = function.__defaults__
    function.__defaults__ = (defaults[0] + 1.0, defaults[1])
    rejects(trace)
    function.__defaults__ = defaults
    masses = model.kernel._masses
    mass = float(masses[0])
    masses[0] = mass * 2
    rejects(trace)
    masses[0] = mass
    _require(trace.require_current() is trace, "Restored original declared configuration")

    # A later native scratch-state change makes this strict current binding
    # stale. Verification must not reset potentials or recompute current.
    native = model.cathode.phases[2]
    native.electric_potential += 0.01
    rejects(trace)
    generated = trace.hydrogen_generated_mol
    reference, admission_reference = weakref.ref(trace), weakref.ref(trace.admission)
    identifier = id(trace)
    trace = None
    gc.collect()
    _require(
        reference() is None and admission_reference() is None,
        "Trace/admission are not held alive by the owner registration",
    )
    _require(identifier not in model._issued_results, "Weak issued identity entry was released")
    return ValidationOutcome(
        True,
        {
            "original_result_guards_rejected": rejected,
            "baseline_generated_H2_mol": generated,
            "weak_original_result_released": True,
        },
        LIMITS,
    )
