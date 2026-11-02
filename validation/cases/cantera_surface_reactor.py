"""Deferred actual native gas/surface kinetics contract; no mechanism is bundled."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="cantera-finite-gas-surface-kinetics", profile="counterflow-flame",
        entrypoint=__name__+":validate_surface",
        invariants=("actual native Interface/ReactorSurface/ReactorNet integrate finite gas and coverages",
                    "combined gas/adsorbate element inventory and site normalization close",
                    "prescribed temperature and rigid volume remain native constraints",
                    "endpoint thermostat demand is distinct from predictive heat/thermal storage",
                    "gas and surface species series reconstruct exactly from retained native accepted points",
                    "a directly cloned or forged catalytic trace cannot reuse the consumed native-run issuer"),
    ), ValidationCase(
        identifier="cantera-catalytic-fixed-wall-thermal-feedback",
        profile="counterflow-flame",
        entrypoint=__name__+":validate_thermal_wall",
        invariants=("native energy-on reactor temperature responds to surface chemistry and a fixed-temperature wall",
                    "wall heat sign follows native left-to-right wall convention",
                    "gas-plus-adsorbate internal-energy change reconciles with sampled wall heat",
                    "finer output grid reduces or bounds the independently sampled energy residual",
                    "the external thermal reservoir remains an imposed boundary, not finite catalyst storage"),
    ), ValidationCase(
        identifier="cantera-catalytic-wall-heat-utility-handoff",
        profile="counterflow-flame",
        entrypoint=__name__+":validate_wall_heat_handoff",
        invariants=("exact native accepted wall-energy increments map to heat-duty bins",
                    "signed heat into the reactor and imposed external wall scope remain explicit",
                    "HeatDuty freshness replays the original catalytic owner and thermal boundary"),
    ), ValidationCase(
        identifier="cantera-finite-flow-catalytic-cstr",
        profile="counterflow-flame",
        entrypoint=__name__+":validate_flowing_cstr",
        invariants=(
            "native Cantera mass-flow and pressure controllers operate a finite-feed stirred catalytic volume",
            "ideal-surface internal energy uses supported partial molar enthalpies, equal to internal energy because surface pressure-volume work is absent",
            "ReactorNet initializes at the declared first sample before any flow-device rate is read, without advancing the physical clock",
            "fixed reactor volume, surface site density and gas/surface thermal equilibrium are checked independently with distinct diagnostics",
            "gas and interface thermo handles are synchronized from the accepted Cantera native states before their temperatures are compared",
            "gas plus adsorbate element inventory closes against independently integrated inlet and outlet fluxes",
            "gas plus adsorbate mass closes against the signed finite-flow ledger",
            "negative gas/surface inventories beyond their declared numerical budgets are rejected and site sum closes",
            "open-reactor internal-energy change reconciles with inlet/outlet enthalpy and fixed-wall heat",
            "flow state, native controller objects and output-grid quadrature remain retained",
            "this stirred reactor does not imply plug-flow, porous transport, pressure drop or industrial process qualification",
        ),
    ))


def validate_surface(*, work_directory, **parameters):
    del work_directory, parameters
    import hashlib
    from pathlib import Path

    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis, NativeMechanismSource, ReactiveState
    from h2physics.adapters.cantera_surface_reactor import CanteraCatalyticSurfaceReactor

    path = next(Path(directory)/"ptcombust.yaml" for directory in ct.get_data_directories()
                if (Path(directory)/"ptcombust.yaml").is_file())
    raw = path.read_bytes()
    basis = MechanismBasis("installed-Cantera-ptcombust-software-contract",
        hashlib.sha256(raw).hexdigest(), "installed-mechanism-separate-rights-not-redistributed",
        ("https://cantera.org/3.2/",), 600., 1400., 1e4, 1e6)
    source = NativeMechanismSource(raw, "gas")
    owner = CanteraCatalyticSurfaceReactor(source, basis,
        surface_phase_name="Pt_surf", gas_phase_name="gas")
    native = ct.Interface(yaml=raw.decode("utf-8"), name="Pt_surf")
    coverages = {name: float(name == "PT(S)") for name in native.species_names}
    trace = owner.run(ReactiveState(900., 101325., {"H2": .1, "O2": .05, "AR": .85}),
        (0., 1e-5, 1e-4), initial_coverages=coverages, surface_area_m2=.001,
        gas_volume_m3=1e-4, clock_id="authored-catalytic-clock",
        evidence_id="installed-native-kinetic-contract-no-process-qualification",
        maximum_time_step_s=1e-6, relative_tolerance=1e-9, absolute_tolerance=1e-15,
        element_absolute_tolerance_mol=1e-9, site_fraction_tolerance=1e-8,
        minimum_gas_mass_kg=1e-12)
    assert trace.native_surface.reactor is trace.native_reactor
    assert abs(trace.native_interface.T-trace.native_gas.T) <= 9e-8
    assert trace.require_current() is trace
    assert len(trace.points) == 3
    assert all(abs(point.temperature_k-900.) < 1e-7 for point in trace.points)
    assert all(point.maximum_element_residual_mol < 1e-9 for point in trace.points)
    assert not np.array_equal(trace.points[0].coverages, trace.points[-1].coverages)
    assert trace.points[0].required_thermostat_heat_into_j == 0.
    gas_species = trace.species_inventory_series("H2", phase="gas")
    surface_species = trace.species_inventory_series("PT(S)", phase="surface")
    assert gas_species.require_current() is gas_species
    assert surface_species.require_current() is surface_species
    assert np.array_equal(gas_species.time_s, np.asarray([point.time_s for point in trace.points]))
    assert np.array_equal(gas_species.amount_mol,
                          np.asarray([point.gas_species_mol[trace.native_gas.species_index("H2")]
                                      for point in trace.points]))
    assert np.array_equal(surface_species.amount_mol,
                          np.asarray([point.surface_species_mol[
                              trace.native_interface.species_index("PT(S)")]
                                      for point in trace.points]))
    try:
        trace.species_inventory_series("UNKNOWN", phase="gas")
    except KeyError:
        pass
    else:
        raise AssertionError("Unknown native species identities must be rejected")
    from dataclasses import replace
    try:
        replace(trace, evidence_id="forged-native-run-receipt")
    except TypeError:
        pass
    else:
        raise AssertionError("Cloned catalytic receipt reused its one-time native-run issuer")
    trace.points[-1].coverages.setflags(write=True)
    trace.points[-1].coverages[0] += 1e-6
    try:
        trace.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Changed native surface output ledger retained admission")
    return ValidationOutcome(True, {"native_points": len(trace.points),
        "species_series": 2}, (
        "Installed source mechanism used only for software contract; no mechanism files redistributed",
        "Prescribed isothermal closed gas/surface reference, not a full catalytic process reformer",
    ))


def validate_thermal_wall(*, work_directory, **parameters):
    del work_directory, parameters
    import hashlib
    from pathlib import Path

    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis, NativeMechanismSource, ReactiveState
    from h2physics.adapters.cantera_surface_reactor import (
        CanteraCatalyticSurfaceReactor, CatalyticThermalBoundary,
    )

    path = next(Path(directory)/"ptcombust.yaml" for directory in ct.get_data_directories()
                if (Path(directory)/"ptcombust.yaml").is_file())
    raw = path.read_bytes()
    basis = MechanismBasis("installed-Cantera-ptcombust-wall-thermal-contract",
        hashlib.sha256(raw).hexdigest(), "installed-mechanism-separate-rights-not-redistributed",
        ("https://cantera.org/3.2/",), 600., 1400., 1e4, 1e6)
    source = NativeMechanismSource(raw, "gas")
    owner = CanteraCatalyticSurfaceReactor(source, basis,
        surface_phase_name="Pt_surf", gas_phase_name="gas")
    native = ct.Interface(yaml=raw.decode("utf-8"), name="Pt_surf")
    coverages = {name: float(name == "PT(S)") for name in native.species_names}
    wall = CatalyticThermalBoundary(
        evidence_id="authored-fixed-wall-native-heat-transfer-contract",
        wall_temperature_k=800., area_m2=.001, heat_transfer_w_m2_k=100.,
        energy_residual_absolute_tolerance_j=.5,
        energy_residual_relative_tolerance=2e-3,
    )
    trace = owner.run(
        ReactiveState(900., 101325., {"H2": .1, "O2": .05, "AR": .85}),
        np.linspace(0., 1e-4, 101), initial_coverages=coverages,
        surface_area_m2=.001, gas_volume_m3=1e-4,
        clock_id="authored-catalytic-wall-clock",
        evidence_id="installed-native-mechanism-wall-contract-no-process-qualification",
        maximum_time_step_s=1e-6, relative_tolerance=1e-9, absolute_tolerance=1e-15,
        element_absolute_tolerance_mol=1e-9, site_fraction_tolerance=1e-8,
        minimum_gas_mass_kg=1e-12, thermal_boundary=wall,
    )
    trace.require_current()
    if trace.native_wall.left_reactor is not trace.native_reactor:
        raise AssertionError("Heat-flow sign convention lost its reactor-left orientation")
    if trace.thermal_boundary is not wall or trace.native_wall.area != wall.area_m2:
        raise AssertionError("Trace does not retain the declared native wall boundary")
    if all(point.temperature_k == trace.points[0].temperature_k for point in trace.points):
        raise AssertionError("The native energy-on reactor did not respond thermally")
    if any(point.required_thermostat_heat_into_j is not None for point in trace.points):
        raise AssertionError("A finite wall path cannot report imposed thermostat heat")
    if any(point.wall_energy_residual_j is None for point in trace.points):
        raise AssertionError("Thermal trace omitted a sampled energy residual")
    residual = max(abs(point.wall_energy_residual_j) for point in trace.points)
    if residual > wall.energy_residual_absolute_tolerance_j:
        raise AssertionError("Sampled output-grid wall-energy error exceeds the declared budget")
    return ValidationOutcome(True, {
        "native_points": len(trace.points),
        "temperature_span_k": max(point.temperature_k for point in trace.points)
                               - min(point.temperature_k for point in trace.points),
        "maximum_sampled_wall_energy_residual_j": residual,
    }, (
        "Installed mechanism used only for a native software contract; no mechanism is redistributed",
        "Imposed fixed-temperature external wall; no finite catalyst support or reactor qualification",
    ))


def validate_flowing_cstr(*, work_directory, **parameters):
    """Deferred synthetic native finite-flow contract; no mechanism is bundled."""
    del work_directory, parameters
    import hashlib
    from pathlib import Path

    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis, NativeMechanismSource, ReactiveState
    from h2physics.adapters.cantera_surface_reactor import (
        CanteraCatalyticSurfaceReactor, CatalyticFlowBoundary, CatalyticThermalBoundary,
    )

    path = next(Path(directory)/"ptcombust.yaml" for directory in ct.get_data_directories()
                if (Path(directory)/"ptcombust.yaml").is_file())
    raw = path.read_bytes()
    basis = MechanismBasis("installed-Cantera-ptcombust-flow-software-contract",
        hashlib.sha256(raw).hexdigest(), "installed-mechanism-separate-rights-not-redistributed",
        ("https://cantera.org/3.2/",), 600., 1400., 1e4, 1e6)
    source = NativeMechanismSource(raw, "gas")
    owner = CanteraCatalyticSurfaceReactor(source, basis,
        surface_phase_name="Pt_surf", gas_phase_name="gas")
    initial = ReactiveState(900., 101325., {"H2": .1, "O2": .05, "AR": .85})
    flow = CatalyticFlowBoundary(
        evidence_id="synthetic-fixed-feed-pressure-controlled-exhaust",
        feed_state=initial, feed_mass_flow_kg_s=1e-5,
        outlet_pressure_pa=100000., pressure_controller_kg_s_pa=1e-9,
        mass_balance_tolerance_kg=1e-7,
        element_balance_tolerance_mol=1e-5,
        energy_balance_tolerance_j=1.,
    )
    wall = CatalyticThermalBoundary(
        evidence_id="synthetic-fixed-temperature-external-wall",
        wall_temperature_k=900., area_m2=.001,
        heat_transfer_w_m2_k=100., energy_residual_absolute_tolerance_j=1.,
        energy_residual_relative_tolerance=1e-3,
    )
    native = ct.Interface(yaml=raw.decode("utf-8"), name="Pt_surf")
    coverages = {name: float(name == "PT(S)") for name in native.species_names}
    trace = owner.run_flowing_cstr(
        initial, np.linspace(0., 1e-4, 21), initial_coverages=coverages,
        surface_area_m2=.001, gas_volume_m3=1e-4, flow_boundary=flow,
        thermal_boundary=wall, clock_id="synthetic-catalytic-flow-clock",
        evidence_id="installed-native-mechanism-flow-contract-no-process-qualification",
        maximum_time_step_s=1e-6, relative_tolerance=1e-9, absolute_tolerance=1e-15,
        site_fraction_tolerance=1e-8, minimum_gas_mass_kg=1e-12,
    ).require_current()
    assert trace.native_inlet_controller.mass_flow_rate > 0.
    assert trace.native_outlet_controller.mass_flow_rate > 0.
    assert trace.native_outlet_controller.primary is trace.native_inlet_controller
    assert trace.native_surface.reactor is trace.native_reactor
    assert trace.points[-1].cumulative_inlet_mass_kg > 0.
    assert trace.points[-1].cumulative_outlet_mass_kg > 0.
    assert max(abs(point.site_fraction_residual) for point in trace.points) <= 1e-8
    assert max(abs(point.mass_residual_kg) for point in trace.points) <= flow.mass_balance_tolerance_kg
    assert max(float(np.max(np.abs(point.element_residual_mol)))
               for point in trace.points) <= flow.element_balance_tolerance_mol
    assert max(abs(point.energy_residual_j) for point in trace.points) <= flow.energy_balance_tolerance_j
    return ValidationOutcome(True, {
        "native_points": len(trace.points),
        "cumulative_feed_mass_kg": trace.points[-1].cumulative_inlet_mass_kg,
        "cumulative_exhaust_mass_kg": trace.points[-1].cumulative_outlet_mass_kg,
        "maximum_sampled_mass_residual_kg": max(abs(p.mass_residual_kg) for p in trace.points),
        "maximum_sampled_element_residual_mol": max(
            float(np.max(np.abs(p.element_residual_mol))) for p in trace.points),
        "maximum_sampled_energy_residual_j": max(abs(p.energy_residual_j) for p in trace.points),
    }, (
        "Installed mechanism used only for native software contract; no mechanism is redistributed.",
        "Constant-feed, pressure-controlled stirred reactor with output-grid flux quadrature; no process qualification.",
    ))


def validate_wall_heat_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    import hashlib
    from pathlib import Path

    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis, NativeMechanismSource, ReactiveState
    from h2physics.adapters.cantera_surface_reactor import (
        CanteraCatalyticSurfaceReactor, CatalyticThermalBoundary,
    )
    from h2physics.adapters.cantera_catalytic_heat import CanteraCatalyticWallHeatAdapter
    from h2physics.adapters.thermal_utilities import HeatDuty, HeatWindow

    path = next(Path(directory)/"ptcombust.yaml" for directory in ct.get_data_directories()
                if (Path(directory)/"ptcombust.yaml").is_file())
    raw = path.read_bytes()
    basis = MechanismBasis("installed-Cantera-ptcombust-wall-heat-utility-contract",
        hashlib.sha256(raw).hexdigest(), "installed-mechanism-separate-rights-not-redistributed",
        ("https://cantera.org/3.2/",), 600., 1400., 1e4, 1e6)
    owner = CanteraCatalyticSurfaceReactor(NativeMechanismSource(raw, "gas"), basis,
        surface_phase_name="Pt_surf", gas_phase_name="gas")
    native = ct.Interface(yaml=raw.decode("utf-8"), name="Pt_surf")
    coverages = {name: float(name == "PT(S)") for name in native.species_names}
    wall = CatalyticThermalBoundary("authored-fixed-wall-heat-duty-contract",
        800., .001, 100., .5, 2e-3)
    trace = owner.run(ReactiveState(900., 101325., {"H2": .1, "O2": .05, "AR": .85}),
        np.linspace(0., 1e-4, 21), initial_coverages=coverages,
        surface_area_m2=.001, gas_volume_m3=1e-4,
        clock_id="authored-catalytic-wall-heat-clock",
        evidence_id="native-catalytic-wall-heat-provider-contract",
        maximum_time_step_s=1e-6, relative_tolerance=1e-9, absolute_tolerance=1e-15,
        element_absolute_tolerance_mol=1e-9, site_fraction_tolerance=1e-8,
        minimum_gas_mass_kg=1e-12, thermal_boundary=wall).require_current()
    window = HeatWindow(trace.points[0].time_s, trace.points[-1].time_s,
        trace.clock_id, "caller-thermal-reporting-window")
    duty = HeatDuty.bind(trace, CanteraCatalyticWallHeatAdapter(), window)
    duty.require_current()
    expected = np.diff([point.wall_heat_integral_into_j for point in trace.points])
    assert duty.snapshot.source is trace
    assert duty.snapshot.scope == "external-device-heat"
    assert np.array_equal(duty.snapshot.edges_s, np.asarray([point.time_s for point in trace.points]))
    assert np.array_equal(duty.snapshot.heat_into_process_j, expected)
    assert np.isclose(np.sum(duty.snapshot.heat_into_process_j),
                       trace.points[-1].wall_heat_integral_into_j, rtol=0., atol=1e-14)
    assert duty.snapshot.original_objects[0] is trace.owner
    return ValidationOutcome(True, {
        "heat_duty_interval_count": len(duty.snapshot.heat_into_process_j),
        "wall_heat_into_process_j": float(np.sum(duty.snapshot.heat_into_process_j)),
        "heat_duty_currentness_replayed": True,
    }, ("Native software contract using installed Cantera mechanism; no process utility availability is inferred.",
        "Fixed wall remains an imposed external boundary, not finite wall inventory."))
