"""Deferred carrier/ammonia cases; discovery constructs metadata only."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Implemented_unverified; no local scientific execution.",
    "Authored liquid calorimetry and imposed extents; no measured catalyst or plant qualification.",
    "Constant-P additive species enthalpy; no excess mixing/phase-equilibrium/separation model.",
)


def cases():
    definitions = (
        (
            "carrier-finite-material",
            "validate_material",
            "carrier-conversion",
            ("finite liquid inventory", "independent elemental and H2 count",
             "molar H2 ledger maps to kg on the declared species basis"),
        ),
        (
            "carrier-thermal-reference",
            "validate_thermal_reference",
            "carrier-conversion",
            ("analytic constant-Cp heat", "elemental-reference invariance", "hot finite feed"),
        ),
        (
            "carrier-reverse-cycle",
            "validate_reverse",
            "carrier-conversion",
            ("finite reverse H2 consumption", "closed inventory and signed heat"),
        ),
        (
            "carrier-packet-boundary",
            "validate_packet",
            "carrier-conversion",
            ("actual pre-withdrawal", "clock/frame/port", "stock versus generated H2"),
        ),
        (
            "carrier-rejected-input",
            "validate_rejections",
            "carrier-conversion",
            ("finite extent and feed identity", "clock/reference/phase", "original failure prefix"),
        ),
        (
            "carrier-original-binding",
            "validate_binding",
            "carrier-conversion",
            ("original identity", "cache/kernel/caloric/default mutation rejection"),
        ),
        (
            "carrier-weak-lifecycle",
            "validate_lifecycle",
            "carrier-conversion",
            ("weak producer registration", "original result and packet released"),
        ),
        (
            "carrier-native-ammonia",
            "validate_native_ammonia",
            "carrier-conversion-native",
            ("actual native ammonia thermochemistry", "independent mixture H", "owned phase guard"),
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


def _problem(**parameters):
    from examples.carrier_conversion import liquid_problem

    return liquid_problem(**parameters)


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _outcome(metrics, *limitations):
    return ValidationOutcome(True, metrics, (*LIMITS, *limitations))


def validate_material(*, work_directory, **parameters):
    import math

    model, initial, stages = _problem()
    result = model.run(initial, stages)
    _require(result.require_current() is result, "Issued original identity")
    final = result.process_trace.final.amounts_mol
    expected = {"rich": 1.1, "lean": 0.8, "H2": 2.2}
    for name, amount in expected.items():
        _require(abs(final[name] - amount) < 1e-12, "Independent finite species count")
    for element in ("C", "H", "O"):
        change = math.fsum(
            (final[s.identifier] - initial.amounts_mol[s.identifier]) * s.elements.get(element, 0)
            for s in model.kernel.species
        )
        _require(abs(change) < 1e-12, "Independent elemental inventory")
    _require(abs(result.hydrogen_formed_mol - 1.8) < 1e-12, "Generated H2 excludes startup H2")
    h2_species = next(
        item for item in model.pathway.reaction.species
        if item.identifier == model.pathway.hydrogen_id
    )
    mass_ledger = result.hydrogen_mass_ledger_kg
    _require(
        math.isclose(mass_ledger["formed_gross_kg"],
                     result.hydrogen_formed_mol * h2_species.molar_mass_kg_mol,
                     rel_tol=1e-14, abs_tol=0.0)
        and math.isclose(mass_ledger["species_residual_kg"],
                         result.hydrogen_species_residual_mol * h2_species.molar_mass_kg_mol,
                         rel_tol=1e-14, abs_tol=0.0),
        "H2 molar ledger converts to mass using the declared species basis",
    )
    _require(
        result.hydrogen_initial_mol == 0.4 and result.hydrogen_withdrawn_mol == 0.0,
        "Initial stock is separate from generated and withdrawn quantities",
    )
    return _outcome(
        {
            "H2_formed_mol": result.hydrogen_formed_mol,
            "H2_species_residual_mol": result.hydrogen_species_residual_mol,
        }
    )


def validate_thermal_reference(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.core import Origin
    from h2physics.thermochemical import ThermochemicalFeed, ThermochemicalInventory

    model, initial, stages = _problem()
    result = model.run(initial, stages)
    # Independent authored h offsets and Cp, not provider evaluation.
    conditioning = (1.7 * 100.0 + 0.2 * 70.0 + 0.4 * 10.0) * 120.0
    reaction_heat = 0.6 * (18000.0 + (70.0 + 3.0 * 10.0 - 100.0) * 120.0)
    expected = conditioning + reaction_heat
    _require(
        abs(result.process_trace.net_heat_required_j - expected) < 1e-8,
        "Independent constant-Cp conditioning plus formation heat",
    )
    shifted, shifted_initial, shifted_stages = _problem(elemental_reference_shift=523.0)
    shifted_result = shifted.run(shifted_initial, shifted_stages)
    _require(
        abs(shifted_result.process_trace.net_heat_required_j - expected) < 1e-8,
        "Element-based caloric zero shift preserves heat",
    )
    feed = ThermochemicalFeed(
        ThermochemicalInventory({"rich": 0.2}, 350.0, initial.pressure_pa, initial.energy_basis_id),
        "unique-hot-feed-packet",
        Origin.SYNTHETIC,
    )
    hot_result = model.run(initial, (replace(stages[0], feeds=(feed,)),))
    _require(
        abs(hot_result.process_trace.net_heat_required_j - expected - 0.2 * 100.0 * 70.0) < 1e-8,
        "Finite feed retains its own sensible enthalpy",
    )
    return _outcome(
        {
            "analytic_heat_j": expected,
            "shifted_heat_j": shifted_result.process_trace.net_heat_required_j,
            "hot_feed_heat_j": hot_result.process_trace.net_heat_required_j,
        }
    )


def validate_reverse(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.thermochemical import PrescribedConversion

    model, initial, stages = _problem()
    forward = replace(stages[0], endpoint_temperature_k=initial.temperature_k)
    reverse = replace(
        forward,
        identifier="reverse",
        start_s=12.0,
        end_s=24.0,
        conversions=(PrescribedConversion(model.pathway.reaction, -0.6, "imposed-reverse"),),
    )
    result = model.run(initial, (forward, reverse))
    _require(
        result.process_trace.full_inventory_closed, "Finite reaction reversal closes inventory"
    )
    _require(
        abs(result.process_trace.net_heat_required_j) < 1e-8, "Signed isothermal heat reversal"
    )
    _require(
        abs(result.hydrogen_formed_mol - result.hydrogen_consumed_mol) < 1e-12,
        "Forward and reverse H2 quantities remain separate",
    )
    return _outcome(
        {
            "net_cycle_heat_j": result.process_trace.net_heat_required_j,
            "formed_mol": result.hydrogen_formed_mol,
            "consumed_mol": result.hydrogen_consumed_mol,
        }
    )


def validate_packet(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.carrier_conversion import FiniteCarrierConversion
    from h2physics.thermochemical import ThermochemicalInventory, ThermochemicalStage

    model, initial, stages = _problem()
    takeoff = ThermochemicalStage(
        "takeoff",
        12.0,
        15.0,
        model.evidence.clock_id,
        400.0,
        (),
        "imposed-component-removal",
        pre_withdrawal_mol={"H2": 0.7, "lean": 0.1},
    )
    result = model.run(initial, (*stages, takeoff))
    packet = model.withdrawal(
        result,
        1,
        boundary_id="component-takeoff",
        frame_id="process-frame",
        evidence_id="caller-imposed-separation",
    )
    _require(packet.require_current() is packet, "Original producer-issued withdrawal")
    _require(
        packet.event_time_s == 12.0 and packet.clock_id == model.evidence.clock_id,
        "Actual start event, not an inferred uniform flow history",
    )
    _require(
        packet.temperature_k == 420.0 and packet.pressure_pa == initial.pressure_pa,
        "Pre-withdrawal temperature and absolute pressure",
    )
    expected_h = 0.7 * 10.0 * 120.0 + 0.1 * (-1000.0 + 70.0 * 120.0)
    _require(abs(packet.enthalpy_j - expected_h) < 1e-9, "Independent actual withdrawn enthalpy")
    _require(
        packet.amounts_mol["H2"] == 0.7 and result.hydrogen_withdrawn_mol == 0.7,
        "Actual finite component withdrawal",
    )
    feed = packet.as_feed(source_id="original-takeoff-to-receiver")
    receiver = FiniteCarrierConversion(
        model.pathway,
        model.caloric_source,
        replace(model.evidence, process_id="receiver", region_id="receiver-region"),
    )
    receiver_initial = ThermochemicalInventory(
        {"rich": 0.1}, 420.0, initial.pressure_pa, initial.energy_basis_id
    )
    receive = ThermochemicalStage(
        "receive",
        12.0,
        16.0,
        packet.clock_id,
        420.0,
        (),
        "immediate-original-packet-receipt",
        feeds=(feed,),
    )
    received = receiver.run(receiver_initial, (receive,), feed_bindings={feed.source_id: packet})
    _require(
        received.feed_bindings[0][1] is packet and received.require_current() is received,
        "Actual original source object retained through finite receiver composition",
    )
    _require(
        received.hydrogen_formed_mol == 0.0 and abs(received.hydrogen_final_mol - 0.7) < 1e-12,
        "Transferred H2 is not generated again in the receiver",
    )
    combined_h = (
        result.process_trace.steps[-1].after_enthalpy_j
        + received.process_trace.steps[-1].after_enthalpy_j
    )
    original_h_and_heat = (
        result.process_trace.steps[0].before_enthalpy_j
        + received.process_trace.steps[0].before_enthalpy_j
        + result.process_trace.net_heat_required_j
        + received.process_trace.net_heat_required_j
    )
    _require(
        abs(combined_h - original_h_and_heat) < 1e-8,
        "Actual sender withdrawal and receiver feed H cancel in the combined boundary",
    )
    from h2physics.adapters.carrier_conversion import CarrierBindingError, CarrierConversionError

    duplicate = replace(feed, source_id="same-withdrawal-second-name")
    try:
        receiver.run(
            receiver_initial,
            (replace(receive, feeds=(feed, duplicate)),),
            feed_bindings={feed.source_id: packet, duplicate.source_id: packet},
        )
    except CarrierConversionError as error:
        _require(len(error.feed_bindings) == 2, "Actual over-allocated source objects retained")
    else:
        raise AssertionError("Same finite source withdrawal consumed twice under different IDs")

    try:
        replace(packet, frame_id="foreign-frame").require_current()
    except CarrierBindingError as error:
        _require(error.withdrawal.frame_id == "foreign-frame", "Rejected context retained")
    else:
        raise AssertionError("Replaced packet context accepted")
    return _outcome(
        {"withdrawn_H2_mol": packet.amounts_mol["H2"], "withdrawn_enthalpy_j": packet.enthalpy_j},
        "Takeoff is imposed; H2 purity, separator work and stock provenance are not solved.",
    )


def validate_rejections(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.carrier_conversion import CarrierConversionError, lohc_pathway
    from h2physics.core import Origin
    from h2physics.thermochemical import (
        PrescribedConversion,
        ThermochemicalFeed,
        ThermochemicalInventory,
    )

    model, initial, stages = _problem()
    first = stages[0]
    excessive = replace(
        first,
        identifier="exhausted",
        start_s=12.0,
        end_s=24.0,
        conversions=(PrescribedConversion(model.pathway.reaction, 50.0, "invalid-overdraw"),),
    )
    try:
        model.run(initial, (first, excessive))
    except CarrierConversionError as error:
        _require(
            len(error.completed_steps) == 1 and error.__cause__ is error.kernel_error,
            "Actual shared-driver failure and completed prefix retained",
        )
    else:
        raise AssertionError("Finite reactant overdraw accepted")
    feed = ThermochemicalFeed(
        ThermochemicalInventory({"rich": 0.1}, 300.0, initial.pressure_pa, initial.energy_basis_id),
        "one-finite-feed",
        Origin.SYNTHETIC,
    )
    invalid_schedules = (
        (replace(first, clock_id="foreign-clock"),),
        (replace(first, feeds=(feed, feed)),),
        (
            replace(
                first,
                feeds=(
                    replace(
                        feed, inventory=replace(feed.inventory, pressure_pa=initial.pressure_pa * 2)
                    ),
                ),
            ),
        ),
        (
            replace(
                first,
                feeds=(
                    replace(
                        feed, inventory=replace(feed.inventory, energy_basis_id="foreign-zero")
                    ),
                ),
            ),
        ),
    )
    rejected = 1
    for schedule in invalid_schedules:
        try:
            model.run(initial, schedule)
        except CarrierConversionError:
            rejected += 1
        else:
            raise AssertionError("Invalid clock/feed-pressure/reference/packet accepted")
    gas_species = tuple(replace(s, phase="gas") for s in model.kernel.species)
    try:
        lohc_pathway(
            gas_species,
            rich_id="rich",
            lean_id="lean",
            hydrogen_id="H2",
            hydrogen_per_carrier=3.0,
            identifier="invalid-gas-as-liquid",
            phase_reference_id="gas-reference",
            source_id="not-liquid-data",
            origin=Origin.SYNTHETIC,
        )
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Gas-reference species relabelled as liquid by adapter")
    return _outcome({"rejected_boundaries": rejected})


def validate_binding(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.carrier_conversion import CarrierBindingError

    model, initial, stages = _problem()
    result = model.run(initial, stages)
    rejected = 0

    def reject(value):
        nonlocal rejected
        try:
            value.require_current()
        except CarrierBindingError as error:
            _require(error.result is value, "Changed original object retained")
            rejected += 1
        else:
            raise AssertionError("Changed carrier source/result accepted")

    reject(replace(result))
    reject(replace(result, hydrogen_formed_mol=50.0))
    reject(replace(result, evidence=replace(result.evidence, clock_id="foreign-clock")))
    cached = result.process_trace.exported_mol
    try:
        cached.setflags(write=True)
    except ValueError:
        readonly_backing_rejected = True
    else:
        raise AssertionError("Bytes-backed carrier cache unexpectedly became writable")
    _require(result.require_current() is result,
             "Read-only cache stayed current without mutation or model replay")
    function = model.caloric_source.provider.functions[0]
    defaults = function.__defaults__
    function.__defaults__ = (defaults[0] + 1.0, defaults[1])
    reject(result)
    function.__defaults__ = defaults
    masses = model.kernel._masses
    original = float(masses[0])
    masses[0] *= 2.0
    reject(result)
    masses[0] = original
    _require(result.require_current() is result, "Exact restoration, without model replay")
    return _outcome(
        {"rejected_binding_replacements": rejected,
         "readonly_cache_write_enable_rejected": readonly_backing_rejected},
        "Current recorded content only; no historical tamper or hidden-closure attestation.",
    )


def validate_lifecycle(*, work_directory, **parameters):
    import gc
    import weakref

    from h2physics.thermochemical import ThermochemicalStage

    model, initial, stages = _problem()
    takeoff = ThermochemicalStage(
        "takeoff",
        12.0,
        13.0,
        model.evidence.clock_id,
        420.0,
        (),
        "finite-takeoff",
        pre_withdrawal_mol={"H2": 0.2},
    )
    result = model.run(initial, (*stages, takeoff))
    packet = model.withdrawal(
        result, 1, boundary_id="port", frame_id="frame", evidence_id="takeoff"
    )
    result_ref, packet_ref = weakref.ref(result), weakref.ref(packet)
    result_id, packet_id = id(result), id(packet)
    result, packet = None, None
    gc.collect()
    _require(
        result_ref() is None and packet_ref() is None, "Owner does not retain abandoned results"
    )
    _require(
        result_id not in model._issued_results and packet_id not in model._issued_withdrawals,
        "Weak producer entries are released",
    )
    return _outcome({"weak_results_released": 2})


def validate_native_ammonia(*, work_directory, **parameters):
    import math

    from examples.carrier_conversion import ammonia_problem
    from h2physics.adapters.carrier_conversion import CarrierBindingError

    model, initial, stages = ammonia_problem()
    result = model.run(initial, stages)
    provider = model.caloric_source.provider
    native = provider.owned_phases[0]
    _require(
        native is not provider.source_phases[0], "Independent audited actual native phase ownership"
    )
    maximum = 0.0
    for step in result.process_trace.steps:
        native.TPX = (
            step.after.temperature_k,
            step.after.pressure_pa,
            dict(step.after.amounts_mol),
        )
        total = math.fsum(step.after.amounts_mol.values())
        expected = total * native.enthalpy_mole / 1000.0
        maximum = max(maximum, abs(expected - step.after_enthalpy_j))
    _require(maximum < 1e-6, "Independent native whole-mixture versus additive-species enthalpy")
    _require(
        abs(result.hydrogen_formed_mol - 0.9) < 1e-12,
        "Independent 2NH3 to 3H2 prescribed-extent count",
    )
    _require(abs(result.process_trace.mass_residual_kg) < 1e-10, "Native atomic-weight mass basis")
    gas = provider.native_gas_providers["carrier-gas"]
    original = gas.native_phase
    gas.native_phase = provider.source_phases[0]
    try:
        result.require_current()
    except CarrierBindingError:
        pass
    else:
        raise AssertionError("Actual alternate native caloric phase pointer accepted")
    gas.native_phase = original
    _require(result.require_current() is result, "Restored actual native definition owner")
    return _outcome(
        {
            "native_whole_mixture_enthalpy_error_j": maximum,
            "native_formed_H2_mol": result.hydrogen_formed_mol,
            "native_mass_residual_kg": result.process_trace.mass_residual_kg,
        },
        "Native pathway comparison, not independent measured thermochemistry or catalyst validation.",
    )
