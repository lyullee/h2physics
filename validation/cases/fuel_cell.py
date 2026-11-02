"""Deferred fuel-cell composition cases; no physics runs during discovery."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Component accounting checks do not establish independent device validation.",
    "Authored current/activities/losses; no device polarization or thermal validation.",
    "Constant-P additive material enthalpy; no compartment/EOS/utility dynamics.",
)


def cases():
    definitions = (
        (
            "fuel-cell-finite-charge",
            "validate_charge",
            "fuel-cell",
            ("actual shared fuel-cell mode", "finite H2/O2/water", "series-area-Faraday"),
        ),
        (
            "fuel-cell-isothermal-heat",
            "validate_heat",
            "fuel-cell",
            ("analytic electric/chemical/heat ledger", "water phase/reference guards"),
        ),
        (
            "fuel-cell-feed-conditioning",
            "validate_feeds",
            "fuel-cell",
            ("finite separate inlet packets", "independent feed sensible H"),
        ),
        (
            "fuel-cell-finite-failure",
            "validate_failure",
            "fuel-cell",
            ("H2 and O2 depletion reject", "actual completed prefix/cause/stack retention"),
        ),
        (
            "fuel-cell-idle-domains",
            "validate_idle",
            "fuel-cell",
            ("zero-current finite state", "explicit unity Faradaic fate", "domain/clock/port"),
        ),
        (
            "fuel-cell-finite-source",
            "validate_source",
            "fuel-cell",
            ("actual finite outlet packet", "receiver source binding", "combined H+electric+Q"),
        ),
        (
            "fuel-cell-original-binding",
            "validate_binding",
            "fuel-cell",
            ("original trace identity", "stack/cache/geometry/kernel mutation", "weak lifecycle"),
        ),
        (
            "fuel-cell-native-caloric",
            "validate_native",
            "fuel-cell-native",
            ("actual Cantera H/mu", "actual shared HydrogenStack", "native whole-mixture H"),
        ),
    )
    return tuple(
        ValidationCase(
            identifier=name,
            profile=profile,
            entrypoint=__name__ + ":" + entry,
            invariants=invariants,
        )
        for name, entry, profile, invariants in definitions
    )


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _problem(**parameters):
    from examples.fuel_cell import synthetic_problem

    return synthetic_problem(**parameters)


def _outcome(metrics, *limitations):
    return ValidationOutcome(True, metrics, (*LIMITS, *limitations))


def validate_charge(*, work_directory, **parameters):
    from h2physics.constants import FARADAY_C_MOL

    model, initial, commands = _problem()
    trace = model.run(initial, commands)
    expected = 3.0 * 0.02 * 200.0 * 10.0 / (2.0 * FARADAY_C_MOL)
    _require(
        trace.require_current() is trace and trace.stack is model.stack,
        "Actual original shared-stack result",
    )
    final = trace.final.amounts_mol
    _require(
        abs(trace.hydrogen_consumed_mol - expected) < 1e-14, "Independent stack Faraday amount"
    )
    for name, value in (
        ("H2", 0.01 - expected),
        ("O2", 0.007 - 0.5 * expected),
        ("H2O", 0.001 + expected),
    ):
        _require(abs(final[name] - value) < 1e-14, "Finite molecular species count")
    _require(trace.electricity_into_j < 0, "Fuel-cell electricity leaves the material boundary")
    _require(trace.steps[0].stack_result.mode == "fuel_cell", "Actual shared operating mode")
    return _outcome(
        {"H2_consumed_mol": trace.hydrogen_consumed_mol, "mass_residual_kg": trace.mass_residual_kg}
    )


def validate_heat(*, work_directory, **parameters):
    from h2physics.constants import FARADAY_C_MOL

    model, initial, commands = _problem()
    trace = model.run(initial, commands)
    extent = 3.0 * 0.02 * 200.0 * 10.0 / (2.0 * FARADAY_C_MOL)
    electric = -3.0 * (0.02 * 200.0) * (1.0 - 0.0005 * 200.0) * 10.0
    h = model.caloric_source.provider.enthalpies_j_mol(initial.temperature_k, initial.pressure_pa)
    heat_into = extent * (h[2] - h[0] - 0.5 * h[1]) - electric
    _require(abs(trace.electricity_into_j - electric) < 1e-10, "Independent electric output")
    _require(
        abs(trace.required_heat_into_j - heat_into) < 1e-9, "Reaction heat less electrical output"
    )
    _require(
        abs(trace.steps[0].stack_result.isothermal_heat_rejection_w * 10.0 + heat_into) < 1e-9,
        "Shared stack heat rejection uses opposite heat-into sign",
    )
    from h2physics.adapters.fuel_cell import FiniteFuelCell, FuelCellError
    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy

    # Construct a separately evidenced owner before changing its thermochemistry;
    # changed source callback on an existing owner must reject before a solve.
    original = model.stack.thermochemistry
    model.stack.thermochemistry = lambda t: ReactionEnergy(
        2 * FARADAY_C_MOL, 260001.0, model.caloric_source.provider.basis_id, "liquid"
    )
    try:
        model.run(initial, commands)
    except FuelCellError:
        pass
    else:
        raise AssertionError("Changed caloric callback under existing admission accepted")
    model.stack.thermochemistry = original
    rejected = 0
    for reference, phase, enthalpy in (
        ("foreign-reference", "liquid", 260000.0),
        (model.caloric_source.provider.basis_id, "vapor", 260000.0),
        (model.caloric_source.provider.basis_id, "liquid", 261000.0),
    ):
        wrong = HydrogenStack(
            model.stack.geometry,
            lambda t, r=reference, p=phase, h=enthalpy: ReactionEnergy(2 * FARADAY_C_MOL, h, r, p),
            model.stack.losses,
        )
        owner = FiniteFuelCell(wrong, model.caloric_source, model.boundary, model.evidence)
        try:
            owner.run(initial, commands)
        except FuelCellError as error:
            _require(error.stack_result is not None, "Actual mismatched shared result retained")
            rejected += 1
        else:
            raise AssertionError("Incompatible reaction phase/reference/enthalpy admitted")
    return _outcome(
        {
            "analytic_electric_into_j": electric,
            "analytic_heat_into_j": heat_into,
            "energy_residual_j": trace.energy_residual_j,
            "rejected_caloric_boundaries": rejected,
        }
    )


def validate_feeds(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.fuel_cell import FuelCellError
    from h2physics.core import Origin
    from h2physics.thermochemical import ThermochemicalFeed, ThermochemicalInventory

    model, initial, commands = _problem()
    base = model.run(initial, commands)
    feed = ThermochemicalFeed(
        ThermochemicalInventory({"H2": 0.002}, 350.0, initial.pressure_pa, initial.energy_basis_id),
        "finite-hot-H2",
        Origin.SYNTHETIC,
    )
    command = replace(
        commands[0], feeds=(feed,), feed_ports={feed.source_id: model.boundary.hydrogen_inlet_id}
    )
    trace = model.run(initial, (command,))
    provider = model.caloric_source.provider
    h_cold = provider.enthalpies_j_mol(initial.temperature_k, initial.pressure_pa)[0]
    h_hot = provider.enthalpies_j_mol(feed.inventory.temperature_k, initial.pressure_pa)[0]
    _require(
        abs(trace.required_heat_into_j - base.required_heat_into_j - 0.002 * (h_cold - h_hot))
        < 1e-9,
        "Independent hot finite-feed conditioning",
    )
    _require(
        abs(trace.final.amounts_mol["H2"] - base.final.amounts_mol["H2"] - 0.002) < 1e-14,
        "Finite feed is retained without changing imposed current extent",
    )
    rejected = 0
    wrong_pressure = replace(feed, inventory=replace(feed.inventory, pressure_pa=202650.0))
    foreign_reference = replace(feed, inventory=replace(feed.inventory, energy_basis_id="foreign"))
    for invalid in (
        replace(command, feed_ports={feed.source_id: model.boundary.oxidant_inlet_id}),
        replace(command, feeds=(wrong_pressure,)),
        replace(command, feeds=(foreign_reference,)),
    ):
        try:
            model.run(initial, (invalid,))
        except FuelCellError as error:
            _require(error.command is invalid, "Failed actual feed/port command retained")
            rejected += 1
        else:
            raise AssertionError("Feed inlet/pressure/reference mismatch accepted")
    return _outcome(
        {
            "feed_conditioning_j": trace.required_heat_into_j - base.required_heat_into_j,
            "rejected_feed_boundaries": rejected,
        }
    )


def validate_failure(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.fuel_cell import FuelCellError

    model, initial, commands = _problem()
    excessive = replace(commands[0], identifier="deplete", start_s=10.0, end_s=1e6)
    rejected = 0
    for stock in (initial, replace(initial, amounts_mol={"H2": 1.0, "O2": 0.001, "H2O": 0.001})):
        try:
            model.run(stock, (*commands, excessive))
        except FuelCellError as error:
            _require(
                len(error.completed_steps) == 1 and error.stack_result is not None,
                "Actual completed prefix and failing shared stack call retained",
            )
            _require(
                error.current is error.completed_steps[-1].kernel_trace.final,
                "Failed stage does not update accepted finite inventory",
            )
            _require(error.__cause__ is error.cause, "Original shared-driver cause retained")
            rejected += 1
        else:
            raise AssertionError("Finite reactant depletion was truncated or repaired")
    return _outcome({"finite_H2_or_O2_rejections": rejected})


def validate_idle(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.fuel_cell import FuelCellError

    model, initial, commands = _problem()
    idle = replace(commands[0], current_density_a_m2=0.0)
    trace = model.run(initial, (idle,))
    _require(
        dict(trace.final.amounts_mol) == dict(initial.amounts_mol),
        "Zero-current molecular inventory",
    )
    _require(
        trace.electricity_into_j == 0 and trace.required_heat_into_j == 0,
        "Isothermal zero-current electrical/heat limit",
    )
    rejected = 0
    for change in ({"faradaic_efficiency": 0.9}, {"current_density_a_m2": -1.0}):
        try:
            replace(commands[0], **change)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Unsupported current/Faradaic fate admitted")
    for change in (
        {"clock_id": "foreign-clock"},
        {"temperature_k": 450.0},
        {"current_density_a_m2": 501.0},
    ):
        try:
            model.run(initial, (replace(commands[0], **change),))
        except FuelCellError:
            rejected += 1
        else:
            raise AssertionError("Unqualified activity/current/temperature/clock admitted")
    return _outcome(
        {
            "idle_consumption_mol": trace.hydrogen_consumed_mol,
            "negative_boundaries_rejected": rejected,
        },
        "Zero current is an imposed command, not an independently validated open-circuit solve.",
    )


def validate_source(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.fuel_cell import FiniteFuelCell, FuelCellBindingError, FuelCellError

    model, initial, commands = _problem()
    takeoff = replace(
        commands[0],
        identifier="water-takeoff",
        start_s=10.0,
        end_s=12.0,
        current_density_a_m2=0.0,
        pre_withdrawal_mol={"H2O": 0.001},
    )
    trace = model.run(initial, (*commands, takeoff))
    packet = model.withdrawal(
        trace,
        1,
        boundary_id=model.boundary.product_outlet_id,
        frame_id=model.boundary.frame_id,
        evidence_id="imposed-water-takeoff",
    )
    _require(
        packet.require_current() is packet and packet.event_time_s == 10.0,
        "Actual original finite water outlet event",
    )
    feed = packet.as_feed(source_id="original-water-to-receiver")
    receiver = FiniteFuelCell(
        model.stack,
        model.caloric_source,
        model.boundary,
        replace(model.evidence, process_id="receiver", region_id="receiver-material"),
    )
    idle_receive = replace(
        commands[0],
        identifier="receive",
        start_s=10.0,
        end_s=12.0,
        current_density_a_m2=0.0,
        feeds=(feed,),
        feed_ports={feed.source_id: model.boundary.hydrogen_inlet_id},
    )
    received = receiver.run(initial, (idle_receive,), feed_bindings={feed.source_id: packet})
    _require(
        received.feed_bindings[0][1] is packet and received.water_formed_mol == 0.0,
        "Transferred product is not generated again",
    )
    hfinal = (
        trace.steps[-1].kernel_trace.steps[0].after_enthalpy_j
        + received.steps[-1].kernel_trace.steps[0].after_enthalpy_j
    )
    hinitial = (
        trace.steps[0].kernel_trace.steps[0].before_enthalpy_j
        + received.steps[0].kernel_trace.steps[0].before_enthalpy_j
    )
    _require(
        abs(
            hfinal
            - hinitial
            - trace.electricity_into_j
            - received.electricity_into_j
            - trace.required_heat_into_j
            - received.required_heat_into_j
        )
        < 1e-8,
        "Combined original sender/receiver H includes actual electricity and heat",
    )
    duplicate = replace(feed, source_id="renamed-same-source")
    for attempt, sources in (
        (replace(idle_receive, start_s=11.0, end_s=13.0), {feed.source_id: packet}),
        (
            replace(
                idle_receive,
                feeds=(feed, duplicate),
                feed_ports={
                    feed.source_id: model.boundary.hydrogen_inlet_id,
                    duplicate.source_id: model.boundary.hydrogen_inlet_id,
                },
            ),
            {feed.source_id: packet, duplicate.source_id: packet},
        ),
    ):
        try:
            receiver.run(initial, (attempt,), feed_bindings=sources)
        except FuelCellError as error:
            _require(error.feed_bindings, "Original rejected source allocation retained")
        else:
            raise AssertionError("Delayed or double-allocated finite source accepted")
    try:
        replace(packet, amounts_mol={"H2O": 0.01}).require_current()
    except FuelCellBindingError as error:
        _require(
            error.withdrawal.amounts_mol["H2O"] == 0.01, "Rejected actual changed packet retained"
        )
    else:
        raise AssertionError("Replaced downstream material packet accepted")
    return _outcome(
        {
            "finite_water_outlet_mol": packet.amounts_mol["H2O"],
            "outgoing_enthalpy_j": packet.enthalpy_j,
        }
    )


def validate_binding(*, work_directory, **parameters):
    import gc
    import weakref
    from dataclasses import replace

    from h2physics.adapters.fuel_cell import FuelCellBindingError

    model, initial, commands = _problem()
    trace = model.run(initial, commands)
    rejected = 0

    def reject(value):
        nonlocal rejected
        try:
            value.require_current()
        except FuelCellBindingError as error:
            _require(error.result is value, "Rejected actual result retained")
            rejected += 1
        else:
            raise AssertionError("Changed issued stack/material/energy evidence accepted")

    reject(replace(trace))
    reject(replace(trace, electricity_into_j=-999.0))
    geometry = model.stack.geometry
    model.stack.geometry = replace(geometry, active_area_m2=geometry.active_area_m2 * 2)
    reject(trace)
    model.stack.geometry = geometry
    cached = trace.steps[0].kernel_trace.feed_mol
    flag = cached.flags.writeable
    try:
        cached.setflags(write=True)
    except ValueError:
        _require(not cached.flags.writeable, "Native array rejects write admission")
        rejected += 1
    else:
        previous = float(cached[0])
        cached[0] = 0.01
        reject(trace)
        cached[0] = previous
        cached.setflags(write=flag)
    raw = trace.steps[0].stack_result
    electric = raw.electric_input_w
    object.__setattr__(raw, "electric_input_w", electric - 1.0)
    reject(trace)
    object.__setattr__(raw, "electric_input_w", electric)
    masses = model.kernel._masses
    mass = float(masses[0])
    masses[0] = mass * 2.0
    reject(trace)
    masses[0] = mass
    provider = model.caloric_source.provider
    original_states = provider._states
    replacements = (
        ("backend", "changed-backend"),
        ("version", "changed-version"),
        ("_cp", object()),
        ("_states", (provider._cp.AbstractState("HEOS", "Water"),) + original_states[1:]),
    )
    for name, changed in replacements:
        original = getattr(provider, name)
        try:
            setattr(provider, name, changed)
            reject(trace)
        finally:
            setattr(provider, name, original)
        _require(trace.require_current() is trace, "Restored native caloric definition")
    try:
        type(provider)(provider.species, provider.fluids, provider.reference_offsets_j_mol,
            basis_id=provider.basis_id, temperature_bounds_k=provider.temperature_bounds_k,
            pressure_bounds_pa=provider.pressure_bounds_pa, backend="BICUBIC&HEOS")
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Unqualified tabular reaction enthalpies were admitted")
    _require(trace.require_current() is trace, "Exact restoration without physical replay")
    reference = weakref.ref(trace)
    identifier = id(trace)
    trace = None
    gc.collect()
    _require(
        reference() is None and identifier not in model._results, "Weak original result lifetime"
    )
    return _outcome({"original_result_mutations_rejected": rejected})


def validate_native(*, work_directory, **parameters):
    import math

    from examples.fuel_cell import native_gas_problem
    from h2physics.adapters.fuel_cell import FuelCellBindingError

    model, initial, commands = native_gas_problem()
    trace = model.run(initial, commands)
    provider = model.caloric_source.provider
    native = provider.owned_phases[0]
    maximum = 0.0
    for step in trace.steps:
        actual = step.kernel_trace.steps[0]
        native.TPX = (
            actual.after.temperature_k,
            actual.after.pressure_pa,
            dict(actual.after.amounts_mol),
        )
        h = native.enthalpy_mole * math.fsum(actual.after.amounts_mol.values()) / 1000.0
        maximum = max(maximum, abs(h - actual.after_enthalpy_j))
    _require(
        maximum < 1e-7 and trace.electricity_into_j < 0, "Actual native mixture H and shared power"
    )
    gas = provider.native_gas_providers["gas"]
    original = gas.native_phase
    gas.native_phase = provider.source_phases[0]
    try:
        trace.require_current()
    except FuelCellBindingError:
        pass
    else:
        raise AssertionError("Actual alternate native caloric pointer admitted")
    gas.native_phase = original
    _require(trace.require_current() is trace, "Current native definition binding restored")
    return _outcome(
        {
            "native_mixture_H_error_j": maximum,
            "native_electric_into_j": trace.electricity_into_j,
            "native_energy_residual_j": trace.energy_residual_j,
        },
        "Native pathway consistency only; held activities are authored, not solved from finite stocks.",
    )
