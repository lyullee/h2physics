"""Deferred actual native separated gas compartments under prescribed current."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="fuel-cell-separated-native-pressure-inventories", profile="fuel-cell-native",
        entrypoint=__name__ + ":validate_compartments",
        invariants=("actual independent native H2/O2/water-vapor volumes preserve separation",
                    "native H2/O2 pressures decline while gaseous product pressure rises",
                    "Faraday series-cell consumption and stoichiometric species mass agree",
                    "one exact accepted native pressure sample can create a sealed post-run ideal-activity stack receipt",
                    "caller fugacity service replaces ideal pressure ratios without adding an EOS",
                    "actual/reference fugacity are evaluated at the same explicit temperature",
                    "full-grid activity series retains exact native sample times and common channel-reference basis",
                    "activity-series clone or omitted-time mutation is rejected",
                    "caller-built compartment traces cannot self-assert the private binding tuple",
                    "direct receipt construction rejects mismatched sample, reference-pressure, correction or stack outputs",
                    "original native compartment depletion failure retains completed prefix",
                    "no pressure feedback or combined reaction-energy closure is inferred"),
    ),)


def build_problem(*, oxygen_volume_m3=0.01):
    import hashlib
    from pathlib import Path

    import cantera as ct

    from h2physics.adapters.cantera import MechanismBasis, ReactiveState
    from h2physics.adapters.cantera_volume import CanteraOpenGasVolume
    from h2physics.adapters.fuel_cell_compartments import (
        FuelCellGasCompartment,
        SeparatedFuelCellCompartments,
    )
    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry

    mechanism_path = next(Path(directory)/"gri30.yaml" for directory in ct.get_data_directories()
                          if (Path(directory)/"gri30.yaml").is_file())
    source_hash = hashlib.sha256(mechanism_path.read_bytes()).hexdigest()
    basis = MechanismBasis("installed-Cantera-gri30-species-only", source_hash, "BSD-3-Clause",
                           ("https://cantera.org/3.2/",), 250., 800., 1., 1e7)

    def phase_factory():
        species = [item for item in ct.Species.list_from_file(str(mechanism_path))
                   if item.name in {"H2", "O2", "H2O"}]
        return ct.Solution(thermo="ideal-gas", kinetics=None, species=species)

    reference = phase_factory()
    compartments = []
    for role, name, volume in (("hydrogen", "H2", .01), ("oxygen", "O2", oxygen_volume_m3),
                                ("water_vapor", "H2O", .01)):
        state = ReactiveState(350., 2e5, {name: 1.})
        compartments.append(FuelCellGasCompartment(
            "authored-"+role, role, name, CanteraOpenGasVolume(phase_factory, basis), state,
            volume, state, (), float(reference.molecular_weights[reference.species_index(name)])/1000.,
            "authored-pure-gas-compartment"))
    h2_mass = compartments[0].molar_mass_kg_mol
    stack = HydrogenStack(StackGeometry(2, .01, h2_mass),
        lambda temperature: ReactionEnergy(200000., 240000., "authored-polarization-only", "vapor"),
        {"authored-loss": lambda current, temperature: .05})
    return SeparatedFuelCellCompartments(stack, compartments, lambda time: (100., 350.),
                                         evidence_id="authored-prescribed-current-thermal-boundaries")


def _run(owner):
    return owner.run((0., .05, .1), clock_id="authored-compartment-clock",
                     support_start_s=0., support_end_s=.2, maximum_time_step_s=.005,
                     relative_tolerance=1e-9, absolute_tolerance=1e-15,
                     minimum_inventory_kg=1e-12, energy_ledger_scale_j=1e3)


def validate_compartments(*, work_directory, **parameters):
    from dataclasses import replace
    del work_directory, parameters
    from math import isclose

    from h2physics.adapters.fuel_cell_compartments import FuelCellCompartmentError
    from h2physics.constants import FARADAY_C_MOL

    owner = build_problem()
    trace = _run(owner)
    trace.require_current()
    from h2physics.adapters.fuel_cell_compartments import FuelCellCompartmentTrace
    try:
        FuelCellCompartmentTrace(
            owner, trace.clock_id, trace.evidence_id, trace.native_traces,
            trace.stack_evaluations, trace.stoichiometric_molar_factors,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Direct compartment trace construction asserted native provenance")
    from h2physics.adapters.fuel_cell_activity_receipt import (
        FuelCellFugacityActivityProvider,
        sample_fuel_cell_activity_receipt,
    )
    receipt = sample_fuel_cell_activity_receipt(
        trace, sample_time_s=.1, stack_temperature_k=350., current_density_a_m2=100.,
        standard_reaction_energy=owner.stack.thermochemistry(350.),
        hydrogen_reference_pressure_pa=1e5, oxygen_reference_pressure_pa=1e5,
        water_reference_pressure_pa=1e5, hydrogen_reference_id="authored-H2-1bar",
        oxygen_reference_id="authored-O2-1bar", water_reference_id="authored-H2O-vapor-1bar",
        evidence_id="authored-post-run-ideal-gas-receipt",
    )
    assert receipt.require_current() is receipt
    assert receipt.operating_state.anode_pressure_pa == trace.native_traces["hydrogen"].snapshots[-1].pressure_pa
    assert receipt.operating_state.cathode_pressure_pa == trace.native_traces["oxygen"].snapshots[-1].pressure_pa
    assert not receipt.pressure_feedback_resolved and not receipt.simultaneous_energy_closure
    assert receipt.stack_result.reaction_energy is receipt.corrected_reaction_energy
    def synthetic_fugacity(species, pressure_pa, temperature_k):
        del temperature_k
        coefficient = {"hydrogen": 0.20, "oxygen": 0.10, "water_vapor": 0.05}[species]
        return pressure_pa * (1.0 + coefficient * pressure_pa / 1e5)

    fugacity_provider = FuelCellFugacityActivityProvider(
        synthetic_fugacity,
        provider_id="synthetic-nonideal-reference-provider",
        evidence_id="authored-synthetic-fugacity-law",
    )
    nonideal_receipt = sample_fuel_cell_activity_receipt(
        trace, sample_time_s=.1, stack_temperature_k=350., current_density_a_m2=100.,
        standard_reaction_energy=owner.stack.thermochemistry(350.),
        hydrogen_reference_pressure_pa=1e5, oxygen_reference_pressure_pa=1e5,
        water_reference_pressure_pa=1e5, hydrogen_reference_id="authored-H2-fugacity-reference",
        oxygen_reference_id="authored-O2-fugacity-reference",
        water_reference_id="authored-H2O-fugacity-reference",
        evidence_id="authored-post-run-nonideal-activity-receipt",
        fugacity_activity_provider=fugacity_provider,
    )
    assert nonideal_receipt.require_current() is nonideal_receipt
    actual_h2_pressure = nonideal_receipt.operating_state.anode_pressure_pa
    expected_h2_activity = synthetic_fugacity("hydrogen", actual_h2_pressure, 350.) / synthetic_fugacity(
        "hydrogen", 1e5, 350.
    )
    assert nonideal_receipt.operating_state.hydrogen_activity == expected_h2_activity
    assert nonideal_receipt.operating_state.hydrogen_activity != actual_h2_pressure / 1e5
    from h2physics.adapters.fuel_cell_activity_receipt import sample_fuel_cell_activity_series
    series = sample_fuel_cell_activity_series(
        trace, operating_points=tuple((time, 350., 100., owner.stack.thermochemistry(350.))
                                      for time in (0., .05, .1)),
        hydrogen_reference_pressure_pa=1e5, oxygen_reference_pressure_pa=1e5,
        water_reference_pressure_pa=1e5, hydrogen_reference_id="authored-H2-1bar",
        oxygen_reference_id="authored-O2-1bar", water_reference_id="authored-H2O-vapor-1bar",
        evidence_id="authored-post-run-ideal-gas-series",
    )
    assert series.sample_times_s == (0., .05, .1)
    assert len(series.operating_states) == len(trace.native_traces["hydrogen"].time_s)
    assert all(item.compartments is trace and not item.pressure_feedback_resolved
               for item in series.receipts)
    try:
        replace(series, receipts=series.receipts[:-1])
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("Activity series accepted an omitted native output time")
    rejected_receipts = 0
    for changes in (
        {"sample_time_s": 0.},
        {"hydrogen_reference_pressure_pa": 2e5},
        {"operating_state": replace(receipt.operating_state,
                                     hydrogen_activity=2*receipt.operating_state.hydrogen_activity)},
        {"corrected_reaction_energy": owner.stack.thermochemistry(350.)},
        {"current_density_a_m2": 101.},
        {"stack_result": replace(receipt.stack_result,
                                  cell_voltage_v=receipt.stack_result.cell_voltage_v+0.01)},
        {"fugacity_activity_provider": FuelCellFugacityActivityProvider(
            lambda species, pressure, temperature: pressure * 1.5,
            provider_id="other-fugacity-model", evidence_id="different-model-evidence")},
    ):
        try:
            replace(receipt, **changes)
        except (ValueError, TypeError):
            rejected_receipts += 1
        else:
            raise AssertionError("Direct receipt constructor accepted inconsistent retained evidence")
    assert rejected_receipts == 7
    try:
        replace(trace).require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Detached compartment trace was admitted")
    native_mass = trace.native_traces["hydrogen"].mass_residual_kg
    native_mass.setflags(write=True)
    saved = native_mass[-1]
    try:
        native_mass[-1] = saved+1.
        try:
            trace.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("Changed native compartment mass ledger was admitted")
    finally:
        native_mass[-1] = saved
        native_mass.setflags(write=False)
    assert not trace.pressure_feedback_resolved and not trace.combined_reaction_energy_closed
    assert len({id(item.native.reactor) for item in trace.native_traces.values()}) == 3
    consumed_h2 = 2*.01*100./(2*FARADAY_C_MOL)*.1
    for compartment in owner.compartments:
        native = trace.native_traces[compartment.role]
        first, last = native.snapshots[0], native.snapshots[-1]
        actual_mol = (last.mass_kg-first.mass_kg)/compartment.molar_mass_kg_mol
        expected = consumed_h2*trace.stoichiometric_molar_factors[compartment.role]
        assert isclose(actual_mol, expected, rel_tol=1e-5, abs_tol=1e-11)
        assert (last.pressure_pa > first.pressure_pa) == (compartment.role == "water_vapor")
        assert all(abs(snapshot.mole_fractions[compartment.species_name]-1.) < 1e-12
                   for snapshot in native.snapshots)
    try:
        _run(build_problem(oxygen_volume_m3=1e-12))
    except FuelCellCompartmentError as error:
        assert error.failed_role == "oxygen"
        assert set(error.completed_native_traces) == {"hydrogen"}
        assert error.cause is error.native_failure
    else:
        raise AssertionError("Native O2 depletion failed to retain the completed H2 prefix")
    return ValidationOutcome(True, {"compartments": len(trace.native_traces)},
                             ("Prescribed current/T; no pressure feedback or combined reaction-energy closure",))
