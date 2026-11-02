"""Deferred solid-reaction acceptance cases; imports/cases() never run a model.

All coefficients below are original synthetic numerical fixtures. They are not
material properties or kinetic parameters for a commercial chemical hydride.
Execution is reserved for the later Nurion validation dispatch.
"""

import hashlib
import math
from dataclasses import fields, replace
from pathlib import Path

import numpy as np


def cases():
    from h2physics.cluster_validation import ValidationCase

    definitions = (
        (
            "solid-baseline",
            "validate_baseline",
            ("finite extent", "analytic first-order refinement"),
        ),
        ("solid-heat", "validate_heat", ("formation enthalpy once", "solved thermal endpoint")),
        (
            "solid-water-feed",
            "validate_water_feed",
            ("finite water", "donor enthalpy", "H2 takeoff"),
        ),
        ("solid-reference", "validate_reference", ("elemental reference-shift invariance",)),
        ("solid-startup-gas", "validate_startup_gas", ("generated vs initially stored H2",)),
        (
            "solid-finite-failure",
            "validate_finite_failure",
            ("completed prefix", "atomic supply debit", "unreached whole-system residuals remain absent"),
        ),
        (
            "solid-negative",
            "validate_negative",
            ("invalid rates", "unbracketed heat", "basis guards"),
        ),
        ("solid-binding", "validate_binding", (
            "callback and caloric binding", "immutable inputs",
            "successful traces issued only by the native reactor",
            "dataclass cloning cannot duplicate a trace receipt",
        )),
        ("solid-reaction-heat-utility-handoff", "validate_heat_utility_handoff", (
            "exact signed external heat command preserved by accepted step",
            "native time bins and common enthalpy reference are retained",
            "source mass, element and provider-reconstructed whole-system energy closure are rechecked",
            "energy helper requires the exact retained kernel/provider identity, ordered species, and basis",
            "post-bind source mutation makes the duty stale",
            "heat availability and utility delivery are not inferred",
        )),
        ("solid-reaction-hydrogen-finite-source-handoff", "validate_hydrogen_source_handoff", (
            "finite source uses accepted H2 takeoff rather than gross reaction generation",
            "mass bins preserve exact per-step H2 withdrawal and source clock",
            "pure H2 basis and common molar-enthalpy reference are enforced",
            "representative state and whole-system enthalpy close through the original provider",
            "energy helper rejects a substitute kernel/provider, reordered species, and inventory basis mismatch",
            "co-withdrawn species and stale trace mutation are rejected",
        )),
    )
    result = [
        ValidationCase(
            identifier=identifier,
            profile="solid-reaction",
            entrypoint=__name__ + ":" + entry,
            parameters={},
            invariants=invariants,
        )
        for identifier, entry, invariants in definitions
    ]
    result.append(
        ValidationCase(
            identifier="solid-native-caloric",
            profile="solid-reaction-native",
            entrypoint=__name__ + ":validate_native_caloric",
            parameters={},
            invariants=(
                "actual Cantera phases",
                "shared molar enthalpy bridge",
                "finite elemental audit",
                "multiphase equilibrium result is issued only by native owner",
                "direct construction, replacement cloning, and forced mutation are rejected",
            ),
        )
    )
    return tuple(result)


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _outcome(metrics, limitations=()):
    from h2physics.cluster_validation import ValidationOutcome

    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Synthetic verification fixtures; no hydride experimental validation.",
            "Fixed-pressure/common-temperature additive phase enthalpy boundary.",
            *limitations,
        ),
    )


def _provider(species, offsets, capacities, shift=0.0):
    from h2physics.reactions import FunctionalMolarEnthalpy
    functions = tuple(
        lambda temperature, pressure, h=h + shift * sum(s.elements.values()), cp=cp: (
            h + cp * (temperature - 300.0)
        )
        for s, h, cp in zip(species, offsets, capacities, strict=True)
    )
    return FunctionalMolarEnthalpy(
        species, functions, f"authored:solid-fixture:shift={shift}", (200.0, 900.0), (1e4, 1e6)
    )


def _rate(state, parameters):
    return parameters["k_per_s"] * state.inventory.amounts_mol.get("rich", 0.0)


def _build(*, hydrolysis=False, rate=_rate, shift=0.0, endothermic=False):
    # A hypothetical Al-H-O bookkeeping system, not claimed stable compounds.
    from h2physics.core import Origin
    from h2physics.reactions import ChemicalSpecies, StoichiometricReaction
    from h2physics.storage.solid_reaction import (
        FiniteSolidReactionReactor,
        SolidReactionEvidence,
        SolidReactionKinetics,
    )
    from h2physics.thermochemical import ThermochemicalInventory
    rich = ChemicalSpecies("rich", {"Al": 1, "H": 2}, 0.029, "solid:authored-rich")
    hydrogen = ChemicalSpecies("H2", {"H": 2}, 0.002, "gas:authored-H2")
    if hydrolysis:
        water = ChemicalSpecies("water", {"H": 2, "O": 1}, 0.018, "liquid:authored-water")
        spent = ChemicalSpecies("spent", {"Al": 1, "O": 1}, 0.043, "solid:authored-spent")
        species, coefficients = (rich, water, spent, hydrogen), (-1, -1, 1, 2)
        provider = _provider(species, (0, -5000, -6000, 0), (20, 10, 20, 5), shift)
    else:
        spent = ChemicalSpecies("spent", {"Al": 1}, 0.027, "solid:authored-spent")
        species, coefficients = (rich, spent, hydrogen), (-1, 1, 1)
        provider = _provider(species, (-1000 if endothermic else 0, 0, 0), (30, 18, 12), shift)
    reaction = StoichiometricReaction("authored-solid-bookkeeping", species, coefficients)
    kinetics = SolidReactionKinetics(
        reaction,
        rate,
        "authored-rate",
        "authored-no-material-data",
        Origin.SYNTHETIC,
        {"k_per_s": 0.1},
    )
    evidence = SolidReactionEvidence(
        "authored-reactor",
        "authored-balanced-formulas",
        provider.basis_id,
        "common-T fixture",
        "externally maintained fixed-P",
        "prescribed component takeoff",
        Origin.SYNTHETIC,
    )
    reactor = FiniteSolidReactionReactor(
        provider,
        kinetics,
        evidence,
        hydrogen_species="H2",
        mode="hydrolysis" if hydrolysis else "decomposition",
        water_species="water" if hydrolysis else None,
    )
    initial = ThermochemicalInventory(
        {"rich": 1.0 if hydrolysis else 2.0}, 300.0, 1e5, provider.basis_id
    )
    return reactor, initial


def _step(identifier="step", start=0.0, end=1.0, **kwargs):
    from h2physics.storage.solid_reaction import SolidReactionStep
    return SolidReactionStep(
        identifier,
        start,
        end,
        "authored-seconds",
        kwargs.pop("heat_input_j", 0.0),
        kwargs.pop("temperature_bracket_k", (200.0, 900.0)),
        "authored-operating-command",
        **kwargs,
    )


def _audit(trace):
    _require(np.all(np.isfinite(trace.element_residual_mol)), "Nonfinite elemental residual")
    _require(np.max(abs(trace.element_residual_mol)) < 1e-9, "Element balance")
    _require(abs(trace.mass_residual_kg) < 1e-10, "Mass balance")
    _require(abs(trace.enthalpy_residual_j) < 1e-5, "Finite-system enthalpy balance")
    for result in trace.steps:
        _require(min(result.after.amounts_mol.values()) >= 0, "Negative reactor inventory")
        _require(abs(result.reaction.heat_residual_j) < 1e-5, "Thermal root residual")
    return trace


def validate_baseline(*, work_directory, **parameters):
    errors = []
    for count in (8, 16, 32):
        reactor, initial = _build()
        dt = 2.0 / count
        schedule = tuple(_step(f"step-{i}", i * dt, (i + 1) * dt) for i in range(count))
        trace = _audit(reactor.run(initial, schedule))
        expected_discrete = 2.0 * (1.0 - 0.1 * dt) ** count
        _require(
            math.isclose(trace.final.amounts_mol["rich"], expected_discrete, abs_tol=1e-12),
            "Frozen-start kinetic discretization differs from authored recurrence",
        )
        errors.append(abs(trace.final.amounts_mol["rich"] - 2 * math.exp(-0.2)))
    _require(
        errors[0] > errors[1] > errors[2] > 0,
        "First-order refinement must reduce exact-solution error",
    )
    _require(
        errors[0] / errors[1] > 1.8 and errors[1] / errors[2] > 1.8, "Expected first-order trend"
    )
    return _outcome(
        {
            "coarse_error_mol": errors[0],
            "fine_error_mol": errors[-1],
            "refinement_ratio": errors[1] / errors[2],
        }
    )


def validate_heat(*, work_directory, **parameters):
    reactor, initial = _build(endothermic=True)
    trace = _audit(reactor.run(initial, (_step(heat_input_j=500.0),)))
    # Capacity is invariant: 2*30 J/K. Extent .2mol consumes200J; net300J heats5K.
    _require(
        math.isclose(trace.final.temperature_k, 305.0, abs_tol=1e-7),
        "Independent endpoint calorimetry",
    )
    _require(
        math.isclose(trace.steps[0].accepted_extent_mol, 0.2, abs_tol=1e-12), "Extent normalization"
    )
    _require(
        trace.steps[0].reaction.kernel_trace.enthalpy_provider is reactor.enthalpy,
        "Actual shared provider must remain retained",
    )
    return _outcome(
        {
            "endpoint_temperature_k": trace.final.temperature_k,
            "enthalpy_residual_j": trace.enthalpy_residual_j,
        }
    )


def validate_heat_utility_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from h2physics.adapters.solid_reaction_heat import SolidReactionHeatAdapter
    from h2physics.adapters.solid_reaction_energy import inventory_enthalpy_j
    from h2physics.adapters.thermal_utilities import HeatDuty, HeatWindow

    reactor, initial = _build(endothermic=True)
    trace = _audit(reactor.run(initial, (_step(heat_input_j=500.0),)))
    window = HeatWindow(0.0, 1.0, "authored-seconds", "authored-heat-window")
    duty = HeatDuty.bind(trace, SolidReactionHeatAdapter(), window)
    duty.require_current()
    _require(duty.snapshot.scope == "external-device-heat", "External supplied heat identity")
    _require(tuple(duty.snapshot.heat_into_process_j) == (500.0,), "Exact finite heat bin")
    _require(tuple(duty.heating_j) == (500.0,), "Positive signed heat feeds an existing sink duty")
    _require(tuple(duty.rejection_j) == (0.0,), "No rejection inferred from supplied heat")
    substitute_provider = replace(trace.enthalpy_provider)
    try:
        inventory_enthalpy_j(trace.initial, species=trace.species,
            provider=substitute_provider, kernel=trace.kernel,
            energy_basis_id=trace.evidence.caloric_basis_id)
    except ValueError:
        substitute_provider_rejected = True
    else:
        raise AssertionError("Whole-system energy accepted a substitute provider with a matching basis")
    try:
        inventory_enthalpy_j(trace.initial, species=tuple(reversed(trace.species)),
            provider=trace.enthalpy_provider, kernel=trace.kernel,
            energy_basis_id=trace.evidence.caloric_basis_id)
    except ValueError:
        reordered_species_rejected = True
    else:
        raise AssertionError("Whole-system energy accepted a reordered species vector")
    original = trace.heat_input_j
    object.__setattr__(trace, "heat_input_j", original+1.0)
    try:
        duty.require_current()
    except ValueError:
        stale_rejected = True
    else:
        raise AssertionError("A changed native heat ledger remained accepted by its duty")
    object.__setattr__(trace, "heat_input_j", original)
    duty.require_current()
    return _outcome({
        "accepted_external_heat_j": float(duty.snapshot.heat_into_process_j.sum()),
        "heat_window_start_s": window.start_s,
        "heat_window_end_s": window.end_s,
        "source_energy_residual_j": trace.enthalpy_residual_j,
        "stale_source_rejected": stale_rejected,
        "substitute_provider_rejected": substitute_provider_rejected,
        "reordered_species_rejected": reordered_species_rejected,
    }, (
        "Synthetic authored reaction and prescribed heat only",
        "No heat-source availability, exchanger, network or heater performance is modeled",
    ))


def validate_hydrogen_source_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from h2physics.adapters.solid_reaction_source import source_from_solid_reaction_hydrogen
    from h2physics.adapters.solid_reaction_energy import inventory_enthalpy_j
    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.release import SourceLocation

    reactor, initial = _build(endothermic=True)
    trace = _audit(reactor.run(initial, (
        _step(heat_input_j=500.0, post_withdrawal_mol={"H2": 0.1}),
    )))
    h2_index = next(i for i, species in enumerate(trace.species) if species.identifier == "H2")
    molar_mass = trace.species[h2_index].molar_mass_kg_mol
    molar_enthalpies = reactor.enthalpy.enthalpies_j_mol(
        trace.final.temperature_k, trace.final.pressure_pa)
    molar_enthalpy = float(molar_enthalpies[h2_index])
    pressure, temperature = trace.final.pressure_pa, trace.final.temperature_k
    density = pressure*molar_mass/(8.31446261815324*temperature)
    specific_enthalpy = molar_enthalpy/molar_mass
    state = ThermoState(PropertyBasis("H2", reactor.enthalpy.basis_id), pressure,
        temperature, density, specific_enthalpy,
        specific_enthalpy-pressure/density, 0.0, "gas", vapor_mass_fraction=1.0)
    location = SourceLocation(trace.evidence.process_id, "authored-seconds",
        "authored-process-frame", (0., 0., 0.), (1., 0., 0.))
    handoff = source_from_solid_reaction_hydrogen(trace, location=location,
        gas_state=state, location_projection_evidence_id="authored-product-plane-projection")
    handoff.require_current()
    substitute_provider = replace(trace.enthalpy_provider)
    try:
        inventory_enthalpy_j(trace.initial, species=trace.species,
            provider=substitute_provider, kernel=trace.kernel,
            energy_basis_id=trace.evidence.caloric_basis_id)
    except ValueError:
        substitute_provider_rejected = True
    else:
        raise AssertionError("H2 receipt energy audit accepted a substitute retained provider")
    _require(handoff.hydrogen_species_id == "H2", "Exact H2 product identity")
    _require(tuple(handoff.source.mass_kg) == (0.1*molar_mass,), "Accepted H2 takeoff mass")
    _require(handoff.source.state is state, "Original thermodynamic state is retained")
    _require(handoff.source.origin == Origin.SYNTHETIC, "Original source origin is retained")
    wrong_basis = replace(state, basis=PropertyBasis("H2", "different-reference"))
    try:
        source_from_solid_reaction_hydrogen(trace, location=location,
            gas_state=wrong_basis, location_projection_evidence_id="authored-wrong-basis")
    except ValueError:
        wrong_basis_rejected = True
    else:
        raise AssertionError("A state with another molar-enthalpy reference was accepted")
    co_withdrawal_trace = _audit(reactor.run(initial, (
        _step(heat_input_j=500.0, post_withdrawal_mol={"H2": 0.1, "spent": 0.1}),
    )))
    try:
        source_from_solid_reaction_hydrogen(co_withdrawal_trace, location=location,
            gas_state=state, location_projection_evidence_id="authored-co-withdrawal-rejection")
    except ValueError as error:
        co_withdrawal_rejected = "co-withdrawn species" in str(error)
    else:
        raise AssertionError("A mixed H2/solid product takeoff was accepted as a pure H2 source")
    _require(co_withdrawal_rejected, "Co-withdrawal rejection must identify product purity")
    original_export_enthalpy = trace.exported_enthalpy_j
    object.__setattr__(trace, "exported_enthalpy_j", original_export_enthalpy+1.0)
    try:
        handoff.require_current()
    except ValueError:
        stale_rejected = True
    else:
        raise AssertionError("A changed producer trace remained attached to the H2 source")
    object.__setattr__(trace, "exported_enthalpy_j", original_export_enthalpy)
    handoff.require_current()
    return _outcome({
        "withdrawn_h2_mol": float(trace.exported_mol[h2_index]),
        "finite_source_mass_kg": float(handoff.source.mass_kg.sum()),
        "enthalpy_projection_residual_j": handoff.source.mass_kg[0]*state.enthalpy_j_kg
            -trace.steps[0].removed_enthalpy_j,
        "wrong_reference_rejected": wrong_basis_rejected,
        "stale_trace_rejected": stale_rejected,
        "substitute_provider_rejected": substitute_provider_rejected,
    }, (
        "Synthetic finite reaction and pure-H2 takeoff only",
        "No product separation, line pressure control, nozzle or dispersion physics is inferred",
    ))


def validate_water_feed(*, work_directory, **parameters):
    from h2physics.core import Origin
    from h2physics.storage.solid_reaction import SolidFeedDraw, SolidSupply
    from h2physics.thermochemical import ThermochemicalInventory
    reactor, initial = _build(
        hydrolysis=True, rate=lambda state, p: 10.0 * state.inventory.temperature_k / 300.0
    )
    supply = SolidSupply(
        "water-source",
        ThermochemicalInventory({"water": 0.25}, 330.0, 1e5, reactor.enthalpy.basis_id),
        "authored-finite-water",
        Origin.SYNTHETIC,
    )
    command = _step(
        feeds=(SolidFeedDraw("water-source", {"water": 0.25}),),
        post_withdrawal_mol={"H2": 0.4},
        limit_policy="truncate",
    )
    trace = _audit(reactor.run(initial, (command,), supplies=(supply,)))
    result = trace.steps[0]
    _require(result.rate_mol_extent_s > 10.0, "Kinetics must see the actual warm post-mixing state")
    expected_temperature = (20 * 300.0 + 2.5 * 330.0 + 250.0) / 22.5
    _require(
        math.isclose(trace.final.temperature_k, expected_temperature, abs_tol=1e-7),
        "Finite warm-water donor enthalpy and exothermic heat must both enter",
    )
    _require(
        result.inventory_limited and result.limiting_species == ("water",),
        "Water is the limiting reactant",
    )
    _require(
        trace.remaining_supplies[0].inventory.amounts_mol["water"] == 0.0,
        "Finite water source debit",
    )
    _require(
        math.isclose(trace.hydrogen_generated_mol, 0.5, abs_tol=1e-12),
        "Stoichiometric generated H2",
    )
    _require(math.isclose(trace.final.amounts_mol["H2"], 0.1, abs_tol=1e-12), "Finite retained H2")
    _require(result.removed_enthalpy_j > 0, "Endpoint takeoff carries actual donor enthalpy")
    return _outcome(
        {
            "temperature_k": trace.final.temperature_k,
            "generated_H2_mol": trace.hydrogen_generated_mol,
            "exported_H2_mol": float(trace.exported_mol[-1]),
            "enthalpy_residual_j": trace.enthalpy_residual_j,
        },
        ("Liquid-water calorimetry is an authored fixture, not a qualified water model.",),
    )


def validate_reference(*, work_directory, **parameters):
    traces = []
    for shift in (0.0, 1e5):
        reactor, initial = _build(endothermic=True, shift=shift)
        traces.append(_audit(reactor.run(initial, (_step(heat_input_j=500.0),))))
    _require(
        math.isclose(traces[0].final.temperature_k, traces[1].final.temperature_k, abs_tol=1e-7),
        "An element-linear reference shift cannot change solved temperature",
    )
    return _outcome(
        {
            "temperature_difference_k": abs(
                traces[0].final.temperature_k - traces[1].final.temperature_k
            )
        }
    )


def validate_startup_gas(*, work_directory, **parameters):
    reactor, initial = _build(rate=lambda state, p: 0.0)
    initial = replace(initial, amounts_mol={"rich": 2.0, "H2": 0.2})
    trace = _audit(reactor.run(initial, (_step(post_withdrawal_mol={"H2": 0.1}),)))
    _require(
        trace.hydrogen_generated_mol == 0.0, "Stored startup H2 must not become generated product"
    )
    _require(math.isclose(trace.exported_mol[-1], 0.1, abs_tol=1e-12), "Explicit startup takeoff")
    return _outcome(
        {
            "generated_H2_mol": trace.hydrogen_generated_mol,
            "exported_H2_mol": float(trace.exported_mol[-1]),
        }
    )


def validate_finite_failure(*, work_directory, **parameters):
    from h2physics.core import Origin
    from h2physics.storage.solid_reaction import SolidFeedDraw, SolidReactionError, SolidSupply
    from h2physics.thermochemical import ThermochemicalInventory
    reactor, initial = _build(hydrolysis=True, rate=lambda state, p: 1.0)
    source = SolidSupply(
        "water-source",
        ThermochemicalInventory({"water": 0.25}, 300.0, 1e5, reactor.enthalpy.basis_id),
        "authored",
        Origin.SYNTHETIC,
    )
    first = _step(feeds=(SolidFeedDraw("water-source", {"water": 0.25}),), limit_policy="truncate")
    second = _step("overdraw", 1.0, 2.0, feeds=(SolidFeedDraw("water-source", {"water": 0.01}),))
    try:
        reactor.run(initial, (first, second), supplies=(source,))
    except SolidReactionError as error:
        _require(
            len(error.completed_steps) == 1 and error.phase == "finite-feed",
            "Retain successful prefix and actual failure stage",
        )
        _require(
            error.remaining_supplies[0].inventory.amounts_mol["water"] == 0.0,
            "No negative donor inventory",
        )
        _require(
            error.__cause__ is not None and error.current is error.completed_steps[0].after,
            "Keep original cause and last actual accepted state",
        )
        _require(
            error.trace is None and error.element_residual_mol is None
            and error.mass_residual_kg is None and error.enthalpy_residual_j is None,
            "A failed finite-feed step cannot claim a completed whole-system audit",
        )
        return _outcome({"completed_steps": 1, "remaining_water_mol": 0.0})
    raise AssertionError("An exhausted finite supply must reject another draw")


def validate_negative(*, work_directory, **parameters):
    from h2physics.storage.solid_reaction import SolidReactionError
    rejected = 0
    for bad_rate in (math.nan, math.inf, -1.0):
        reactor, initial = _build(rate=lambda state, p, value=bad_rate: value)
        try:
            reactor.run(initial, (_step(),))
        except SolidReactionError as error:
            _require(
                error.phase == "kinetics"
                and error.raw_rate is not None
                and error.rate_state is not None
                and error.__cause__ is not None,
                "Invalid kinetic result and actual context must survive",
            )
            rejected += 1
        else:
            raise AssertionError("Invalid kinetic rate accepted")
    reactor, initial = _build()
    for command in (_step(heat_input_j=1e9), _step(limit_policy="reject", end=100.0)):
        try:
            reactor.run(initial, (command,))
        except SolidReactionError as error:
            _require(
                error.__cause__ is not None and not error.completed_steps,
                "No partial success on failed first step",
            )
            if command.heat_input_j:
                _require(
                    len(error.trials) >= 2 and error.trials[-1].kernel_trace is not None,
                    "Keep actual finite bracket trials when supplied heat is unbracketed",
                )
            rejected += 1
        else:
            raise AssertionError("Unbracketed heat/overlarge finite extent accepted")
    wrong = replace(initial, energy_basis_id="foreign-reference")
    try:
        reactor.run(wrong, (_step(),))
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Foreign formation reference accepted")
    return _outcome({"negative_gates_rejected": rejected})


def validate_binding(*, work_directory, **parameters):
    reactor, initial = _build()
    try:
        reactor.kinetics.parameters["k_per_s"] = 2.0
    except TypeError:
        pass
    else:
        raise AssertionError("Caller parameter alias is mutable")
    reactor.kinetics = replace(reactor.kinetics, rate=lambda state, p: 100.0)
    mutation_rejected = False
    try:
        reactor.run(initial, (_step(),))
    except ValueError:
        mutation_rejected = True
    if not mutation_rejected:
        raise AssertionError("Rebound kinetic callable bypassed original source contract")
    reactor, initial = _build()
    trace = _audit(reactor.run(initial, (_step(),)))
    try:
        replace(trace)
    except ValueError:
        return _outcome({
            "mutated_callback_rejected": 1,
            "immutable_parameters": 1,
            "trace_clone_rejected": 1,
        })
    raise AssertionError("A copied reaction trace retained native-run issuance")


def validate_native_caloric(*, work_directory, **parameters):
    from h2physics.core import Origin
    from h2physics.reactions import StoichiometricReaction
    from h2physics.storage.solid_reaction import (
        FiniteSolidReactionReactor,
        SolidReactionEvidence,
        SolidReactionKinetics,
    )
    from h2physics.thermochemical import ThermochemicalInventory
    """Small native LiH/Li/H2 caloric composition; rate/densities are synthetic."""
    import cantera as ct

    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.cantera_caloric import (
        CanteraMultiphaseMolarEnthalpy,
        SolidDensityEvidence,
    )
    from h2physics.adapters.cantera_multiphase import (
        CanteraMultiphaseEquilibrium,
        EquilibriumPhase,
        MultiphaseFeed,
    )

    directory = Path(ct.__file__).parent / "data"
    condensed, gas = (
        (directory / "nasa_condensed.yaml").read_bytes(),
        (directory / "h2o2.yaml").read_bytes(),
    )
    reference, spin = "declared-native-NASA-formation-reference", "native-H2-spin-unresolved"
    phases, densities = [], {}
    for phase_id, species_name, density in (
        ("hydride", "LiH(s)", 1000.0),
        ("spent", "Li(cr)", 500.0),
    ):

        def factory(species_name=species_name, density=density):
            source = next(
                s
                for s in ct.Species.list_from_yaml(condensed.decode(), "species")
                if s.name == species_name
            )
            values = dict(source.input_data)
            values["equation-of-state"] = {"model": "constant-volume", "density": density}
            return ct.Solution(
                thermo="fixed-stoichiometry",
                species=[ct.Species.from_dict(values)],
                name="authored-" + species_name,
                transport_model="none",
            )

        basis = MechanismBasis(
            "installed-nasa-condensed:" + phase_id,
            hashlib.sha256(condensed).hexdigest(),
            "Cantera BSD-3-Clause; installed NASA thermochemistry",
            ("https://ntrs.nasa.gov/citations/19940013151",),
            300.0,
            430.0,
            1e4,
            1e6,
        )
        phases.append(EquilibriumPhase(phase_id, "solid", factory, basis, reference, spin))
        densities[phase_id] = SolidDensityEvidence(
            density,
            "authored-density-only",
            Origin.SYNTHETIC,
            "Finite calorimetry fixture; not an independently measured LiH/Li solid EOS",
        )
    gas_basis = MechanismBasis(
        "installed-h2o2",
        hashlib.sha256(gas).hexdigest(),
        "Cantera BSD-3-Clause",
        ("https://cantera.org/3.2/python/thermo.html",),
        300.0,
        430.0,
        1e4,
        1e6,
    )
    phases.append(
        EquilibriumPhase(
            "gas",
            "gas",
            lambda: ct.Solution(yaml=gas.decode(), name="ohmech"),
            gas_basis,
            reference,
            spin,
        )
    )
    equilibrium = CanteraMultiphaseEquilibrium(tuple(phases)).equilibrate(
        MultiphaseFeed(
            350.0,
            1e5,
            {"hydride": {"LiH(s)": 1.0}, "spent": {"Li(cr)": 0.0}, "gas": {"H2": 0.1}},
            "authored-multiphase-result-issuance",
            Origin.SYNTHETIC,
        ),
        constraint="TP",
        require_accepted=False,
    )
    _require(equilibrium.require_current() is equilibrium, "Native multiphase result currentness")
    try:
        replace(equilibrium)
    except ValueError:
        pass
    else:
        raise AssertionError("Multiphase equilibrium result cloning retained native issuance")
    direct = {item.name: getattr(equilibrium, item.name) for item in fields(equilibrium)
              if item.init and item.name != "_issuer_token"}
    try:
        type(equilibrium)(**direct)
    except ValueError:
        pass
    else:
        raise AssertionError("Direct multiphase-result construction claimed native issuance")
    old_accepted = equilibrium.accepted
    object.__setattr__(equilibrium, "accepted", not old_accepted)
    try:
        equilibrium.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("A forced result mutation retained multiphase freshness")
    finally:
        object.__setattr__(equilibrium, "accepted", old_accepted)
    _require(equilibrium.require_current() is equilibrium, "Multiphase result recovers after fixture restore")
    caloric = CanteraMultiphaseMolarEnthalpy(
        tuple(phases),
        (("hydride", "LiH(s)", "rich"), ("spent", "Li(cr)", "spent"), ("gas", "H2", "H2")),
        solid_density_evidence=densities,
    )
    reaction = StoichiometricReaction(
        "explicit-LiH-decomposition-bookkeeping", caloric.species, (-2, 2, 1)
    )
    law = SolidReactionKinetics(
        reaction,
        lambda state, p: 1e-6,
        "authored-constant-rate",
        "synthetic-no-material-kinetic-qualification",
        Origin.SYNTHETIC,
    )
    evidence = SolidReactionEvidence(
        "native-caloric-fixture",
        "explicit-element-balanced-formulas",
        caloric.basis_id,
        "common-T",
        "fixed-P",
        "prescribed-takeoff",
        Origin.SYNTHETIC,
    )
    reactor = FiniteSolidReactionReactor(
        caloric, law, evidence, hydrogen_species="H2", mode="decomposition"
    )
    initial = ThermochemicalInventory({"rich": 1.0, "H2": 0.1}, 350.0, 1e5, caloric.basis_id)
    trace = _audit(reactor.run(initial, (_step(temperature_bracket_k=(300.0, 430.0)),)))
    _require(
        trace.enthalpy_provider is caloric and trace.kernel is reactor.kernel,
        "Actual native bridge identity",
    )
    _require(
        all(isinstance(p, ct.Solution) for p in caloric.owned_phases),
        "Actual owned Cantera phase objects",
    )
    return _outcome(
        {
            "generated_H2_mol": trace.hydrogen_generated_mol,
            "temperature_k": trace.final.temperature_k,
            "enthalpy_residual_j": trace.enthalpy_residual_j,
            "cantera_version": ct.__version__,
            "condensed_source_sha256": hashlib.sha256(condensed).hexdigest(),
            "gas_source_sha256": hashlib.sha256(gas).hexdigest(),
        },
        (
            "Native thermochemistry only; synthetic constant solid densities and rate.",
            "No aqueous hydrolysis or LiH material/kinetic validation.",
        ),
    )
