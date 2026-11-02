"""Metadata-only deferred thermal utility composition cases; all remain unrun."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Implemented_unverified; no local model/native/module/case/example/test execution.",
    "Finite declared budgets and temperature bounds are not predicted utility availability.",
    "No pinch, COP, exergy calculation, price, annualization or full-plant energy qualification.",
    "Native closed HX transfer is already settled; standalone process-duty mappings do not rerun thermal physics.",
)


def cases():
    definitions = (
        (
            "thermal-declared-balance",
            "validate_declared_balance",
            (
                "finite taken=delivered+explicit loss",
                "oriented SI utility quantities",
                "original finite budgets",
            ),
        ),
        (
            "thermal-negative-gates",
            "validate_negative_gates",
            (
                "same clock/window/bins",
                "temperature/reference compatibility",
                "finite budget and alias rejection",
            ),
        ),
        (
            "thermal-native-HX",
            "validate_native_exchanger",
            (
                "actual same-original native side transfer",
                "finite opposite heat integrals",
                "no external utility double credit",
            ),
        ),
        (
            "thermal-process-readers",
            "validate_process_readers",
            (
                "original PV/MEC/carrier heat ledgers",
                "correct signed process boundary",
                "no implicit clock alignment",
            ),
        ),
        (
            "thermal-native-devices",
            "validate_native_devices",
            (
                "actual native reliquefier/vaporizer duties",
                "explicit steady hold",
                "external fluid-plus-wall heat",
            ),
        ),
        (
            "thermal-mutation-failure",
            "validate_mutation_failure",
            (
                "source/native/cache mutation rejection",
                "original objects and failure cause retained",
            ),
        ),
        (
            "thermal-public-adapter-exports",
            "validate_public_adapter_exports",
            (
                "source-bound duty readers available from h2physics.adapters",
                "thermal accounting/result types retain original object identity",
            ),
        ),
    )
    return tuple(
        ValidationCase(
            identifier=name,
            profile="thermal-utilities",
            entrypoint=__name__ + ":" + function,
            parameters={},
            invariants=invariants,
        )
        for name, function, invariants in definitions
    )


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_public_adapter_exports(*, work_directory, **parameters):
    del work_directory, parameters
    import h2physics.adapters as public_api
    import h2physics.adapters.thermal_utilities as implementation

    names = (
        "CarrierHeatAdapter", "DynamicDeviceHeatAdapter", "ExergyReference",
        "FiniteExchangerHeatAdapter", "HeatAllocation", "HeatAvailability",
        "HeatComponent", "HeatDuty", "HeatDutyAdapter", "HeatSnapshot", "HeatWindow",
        "NativeExchangeReceipt", "ProjectionHeatAdapter", "SteadyNativeHeatAdapter",
        "TemperatureLevel", "ThermalUtilityLedger", "ThermalUtilityError", "account_heat",
    )
    _require(all(getattr(public_api, name) is getattr(implementation, name) for name in names),
             "Thermal utility adapter exports must preserve implementation identities")
    _require(set(names) <= set(public_api.__all__),
             "Thermal utility adapter names must be declared in public __all__")
    return ValidationOutcome(
        True, {"public_thermal_api_symbols": len(names)}, LIMITS,
    )


def validate_declared_balance(*, work_directory, **parameters):
    import numpy as np

    from examples.thermal_utilities import declared_case
    from h2physics.adapters.physical_economics import quantity_definition

    ledger, donor, sink, budget, transfer = declared_case()
    ledger.require_current()
    _require(
        np.array_equal(transfer.taken_j, transfer.delivered_j + transfer.loss_j),
        "Explicit finite heat conservation",
    )
    _require(
        ledger.quantities["required_heat_input_j"] == 0.0
        and ledger.quantities["required_heat_rejection_j"] == 10.0
        and ledger.declared_loss_j == 2.0,
        "Independent finite authored accounting",
    )
    _require(
        ledger.profiles[0] is donor
        and ledger.profiles[1] is sink
        and ledger.allocations[0].availability is budget,
        "Original source/budget identity",
    )
    _require(quantity_definition("required_heat_input_j").unit == "J", "Actual public SI registry")
    return ValidationOutcome(
        True,
        {
            "remaining_heat_input_j": 0.0,
            "remaining_rejection_j": 10.0,
            "explicit_loss_j": ledger.declared_loss_j,
        },
        LIMITS,
    )


def validate_negative_gates(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.thermal_utilities import DeclaredHeatAdapter, declared_case
    from h2physics.adapters.thermal_utilities import HeatDuty, HeatWindow, account_heat

    _, donor, sink, budget, transfer = declared_case()
    other_clock = HeatDuty.bind(
        replace(sink.source, clock_id="unmapped-independent-clock"),
        DeclaredHeatAdapter(),
        HeatWindow(0.0, 2.0, "unmapped-independent-clock", "no-clock-mapping"),
    )
    alias = HeatDuty.bind(donor.source, DeclaredHeatAdapter(), donor.window)
    cold = transfer.sink_levels[0]
    wrong_environment = replace(
        cold, exergy_reference=replace(cold.exergy_reference, identifier="other-environment")
    )
    hotter_sink = replace(cold, minimum_k=450.0, maximum_k=460.0)
    half = replace(
        transfer,
        identifier="first-half",
        taken_j=[5.5, 10.5],
        delivered_j=[5.0, 10.0],
        loss_j=[0.5, 0.5],
    )
    alias_budget = replace(budget)
    second = replace(half, identifier="second-half", availability=alias_budget)
    rejected = 0
    for operation in (
        lambda: account_heat(
            (donor, other_clock), (), evidence_id="wrong-clock", energy_tolerance_j=1e-9
        ),
        lambda: account_heat(
            (donor, alias, sink), (), evidence_id="aliased-boundary", energy_tolerance_j=1e-9
        ),
        lambda: account_heat(
            (donor, sink),
            (replace(transfer, availability=None),),
            evidence_id="missing-availability",
            energy_tolerance_j=1e-9,
        ),
        lambda: account_heat(
            (donor, sink),
            (replace(transfer, taken_j=[14.0, 24.0], loss_j=[4.0, 4.0]),),
            evidence_id="finite-budget-exceeded",
            energy_tolerance_j=1e-9,
        ),
        lambda: account_heat(
            (donor, sink),
            (replace(transfer, source_levels=(None, None)),),
            evidence_id="unknown-temperature",
            energy_tolerance_j=1e-9,
        ),
        lambda: account_heat(
            (donor, sink),
            (replace(transfer, sink_levels=(hotter_sink,) * 2),),
            evidence_id="passive-temperature-lift",
            energy_tolerance_j=1e-9,
        ),
        lambda: account_heat(
            (donor, sink),
            (replace(transfer, sink_levels=(wrong_environment,) * 2),),
            evidence_id="different-reference",
            energy_tolerance_j=1e-9,
        ),
        lambda: account_heat(
            (donor, sink),
            (half, second),
            evidence_id="copied-finite-budget",
            energy_tolerance_j=1e-9,
        ),
    ):
        try:
            operation()
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Unresolved/double-counted/incompatible heat allocation admitted")
    return ValidationOutcome(True, {"explicit_thermal_admission_rejections": rejected}, LIMITS)


def validate_native_exchanger(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.thermal_utilities import native_exchanger_case
    from h2physics.adapters.thermal_utilities import NativeExchangeReceipt, account_heat

    ledger, model, trace, donor, sink, allocation = native_exchanger_case()
    ledger.require_current()
    _require(
        donor.source is trace and sink.source is trace and allocation.native_receipt.donor is donor,
        "Actual same native exchanger/source identity",
    )
    _require(
        ledger.native_internal_transfer_j > 0.0
        and ledger.quantities["required_heat_input_j"] == 0.0
        and ledger.quantities["required_heat_rejection_j"] == 0.0,
        "Native internal transfer cannot become an external utility credit",
    )
    for point in trace.points:
        _require(
            380.0 <= point.sides["left"].native_state.wall_temperature_K <= 405.0
            and 245.0 <= point.sides["right"].native_state.wall_temperature_K <= 270.0,
            "Retained native temperatures remain within the authored case bounds",
        )
    try:
        NativeExchangeReceipt(
            donor,
            donor,
            "forged-same-side-transfer",
            donor.snapshot.heat_into_process_j,
            1e-4,
            "caller-computed-content",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Direct same-side native exchange receipt was admitted")
    try:
        replace(allocation.native_receipt)
    except ValueError:
        pass
    else:
        raise AssertionError("A copied native exchange receipt reused its consumed issuer")

    try:
        account_heat(
            (donor, sink),
            (replace(allocation, native_receipt=None),),
            evidence_id="invalid-free-native-internal-utility",
            energy_tolerance_j=1e-4,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Already settled native internal heat treated as free utility")
    return ValidationOutcome(
        True,
        {
            "native_transfer_recorded_once_j": ledger.native_internal_transfer_j,
            "native_points": len(trace.points),
            "separate_original_finite_sides": len(trace.finite_sides),
        },
        LIMITS,
    )


def validate_process_readers(*, work_directory, **parameters):
    import numpy as np

    from examples.thermal_utilities import process_duties
    from h2physics.adapters.thermal_utilities import account_heat

    duties = process_duties()
    pv = duties["pv_stack"].source.source
    mec = duties["mec"].source.source
    carrier = duties["carrier"].source
    _require(
        np.array_equal(
            duties["pv_stack"].snapshot.heat_into_process_j,
            [-s.stack_heat_rejected_j for s in pv.steps],
        ),
        "PV rejection sign",
    )
    _require(
        np.array_equal(
            duties["pv_receiver"].snapshot.heat_into_process_j,
            [s.receiver_heat_into_j for s in pv.steps],
        ),
        "Actual receiver heat direction",
    )
    _require(
        np.array_equal(
            duties["mec"].snapshot.heat_into_process_j,
            [s.isothermal_heat_required_into_j for s in mec.steps],
        ),
        "Actual finite MEC signed duty",
    )
    _require(
        np.array_equal(
            duties["carrier"].snapshot.heat_into_process_j,
            [s.heat_required_j for s in carrier.process_trace.steps],
        ),
        "Original carrier kernel stage heat",
    )
    for duty in duties.values():
        duty.require_current()
    try:
        account_heat(
            tuple(duties.values()),
            (),
            evidence_id="unsupported-clock-alignment",
            energy_tolerance_j=1e-6,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Independent process clocks silently aligned")
    return ValidationOutcome(
        True,
        {"original_process_heat_profiles": len(duties), "no_utility_availability_inferred": True},
        LIMITS,
    )


def validate_native_devices(*, work_directory, **parameters):
    import numpy as np

    from examples.thermal_utilities import native_device_duties

    cold, hot, dynamic = native_device_duties()
    _require(
        cold.snapshot.heat_into_process_j[0] == -cold.source.native_result.heat_removed_W * 0.25,
        "Original removed heat W times explicit hold seconds",
    )
    _require(
        hot.snapshot.heat_into_process_j[0] == hot.source.heat_into_hydrogen_W * 0.25,
        "Original vaporizer W times explicit hold seconds",
    )
    expected = np.diff(
        [0.0, *(r.balances["cold-volume"].external_heat_j for r in dynamic.source.steps)]
    )
    _require(
        np.array_equal(dynamic.snapshot.heat_into_process_j, expected),
        "Actual native external fluid-plus-wall heat; no internal wall heat double counting",
    )
    for profile in (cold, hot, dynamic):
        profile.require_current()
    return ValidationOutcome(
        True,
        {
            "native_steady_cold_j": cold.snapshot.heat_into_process_j[0],
            "native_steady_vaporizer_j": hot.snapshot.heat_into_process_j[0],
            "native_dynamic_external_heat_j": float(np.sum(expected)),
            "cop_or_warm_condenser_rejection_inferred": False,
        },
        LIMITS,
    )


def validate_mutation_failure(*, work_directory, **parameters):
    from examples.thermal_utilities import declared_case, native_exchanger_case
    from h2physics.adapters.thermal_utilities import ThermalUtilityError, account_heat

    ledger, *_ = declared_case()
    ledger.heating_remaining_j[0].setflags(write=True)
    ledger.heating_remaining_j[0][0] += 1.0
    rejected = 0
    try:
        ledger.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed returned utility residual array accepted")
    _, donor, *_ = declared_case()
    donor.source.original_boundary_owner["changed"] = True
    try:
        donor.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed original source context accepted")
    _, _, trace, hot, cold, allocation = native_exchanger_case()
    trace.native_components[0].ambient_UA *= 2.0
    try:
        account_heat(
            (hot, cold),
            (allocation,),
            evidence_id="mutated-native-definition",
            energy_tolerance_j=1e-4,
        )
    except ThermalUtilityError as error:
        _require(
            error.original_error is error.__cause__ and error.profiles[0].source is trace,
            "Retain original native source and actual original owner failure",
        )
        rejected += 1
    else:
        raise AssertionError("Mutated actual native exchanger conductance accepted")
    return ValidationOutcome(
        True, {"source_native_and_returned_cache_rejections": rejected}, LIMITS
    )
