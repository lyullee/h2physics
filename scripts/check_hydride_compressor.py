"""Actual finite source/bed/receiver thermal transfer; synthetic parameters only."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter


def make_case(*, fluid="Hydrogen", absorption=.02, desorption=.05, gas_solid_ua=1.,
              solid_ua=20., solid_capacity=300., free_volume=.0005,
              source_pressure=5e5, receiver_pressure=1e6, floor_fraction=None):
    from h2physics.core import Origin
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening, NozzleSearch
    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference,
        FiniteHydrideBed,
        FiniteHydrideDomain,
        HydrideGasThermodynamics,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate,
        HydrideKinetics,
        HydrideParameters,
        VanthoffPlateau,
    )
    from h2physics.storage.hydride_compressor import (
        FiniteHydrideGasVessel,
        HydrideCompressorEvidence,
        HydrideCompressorNative,
        HydrideThermalCompressor,
    )

    native = HydrideCompressorNative.from_installed(
        source_id="LH2DT:b2f276333c1b1793c39f25763703d196d36742ec")
    gas = HydrideGasThermodynamics.coolprop(fluid)
    reference = BoundHydrogenEnergyReference.from_gas(gas, temperature_k=300., pressure_pa=1e5,
        desorption_enthalpy_j_mol_h2=24000., evidence_id="authored-compressor-bound-H-reference")
    parameters = HydrideParameters(.005, solid_capacity, 24000., gas.molar_mass_kg_mol, solid_ua)
    kinetics = HydrideKinetics(VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(absorption, 0., 300.), ArrheniusRate(desorption, 0., 300.))
    floor = 1e-7
    if floor_fraction is not None:
        floor = gas.state_pt(2e5, 300.).density_kg_m3*free_volume*floor_fraction
    bed = FiniteHydrideBed(parameters, kinetics, gas, reference,
        FiniteHydrideDomain(200., 600., 10., 1e7, floor), free_gas_volume_m3=free_volume,
        gas_solid_conductance_w_k=gas_solid_ua)
    vessels = []
    for name, pressure in (("finite-source", source_pressure), ("finite-receiver", receiver_pressure)):
        vessels.append(FiniteHydrideGasVessel.coolprop(native, gas, vessel_id=name,
            native_geometry=native.tank.TankGeometry(.03, 500., 2., 10.),
            pressure_pa=pressure, temperature_k=300., wall_temperature_k=300.,
            minimum_gas_mass_kg=1e-7, source_id="authored-native-finite-vessel"))
    nozzle = HomogeneousIsentropicNozzle(gas.native_objects[0], search=NozzleSearch(
        initial_grid_points=9, maximum_refinements=3,
        relative_flux_tolerance=1e-6, relative_pressure_tolerance=1e-5))
    opening = NozzleOpening("authored-MHC-port", 1e-7, 1., "authored-effective-area-not-measured")
    evidence = HydrideCompressorEvidence("authored-finite-thermal-compressor",
        "synthetic-unfitted-plateau-and-kinetics", "synthetic-capacity-geometry-UA",
        "authored-finite-initial-inventories", "authored-four-stage-schedule",
        "authored-absolute-operation-clock", Origin.SYNTHETIC)
    return HydrideThermalCompressor(native, bed=bed, source=vessels[0], receiver=vessels[1],
        nozzle=nozzle, inlet_opening=opening, outlet_opening=opening, evidence=evidence)


def stages(model, *, start=100., durations=(200., 120., 200., 200.), isolated=False):
    from h2physics.storage.finite_hydride import FiniteHydrideHeatBoundary, FiniteHydrideHeatInput
    from h2physics.storage.hydride_compressor import HydrideCompressorStage

    result = []
    time = start
    for (name, inlet, outlet, bath), duration in zip((
        ("cold-admission", 1., 0., 300.), ("isolated-heating", 0., 0., 450.),
        ("hot-delivery", 0., 1., 450.), ("isolated-cooling", 0., 0., 300.)), durations, strict=True):
        end = time+duration
        heat = FiniteHydrideHeatBoundary(model.evidence.clock_id, time, end,
            lambda t, s, bath=bath: FiniteHydrideHeatInput(bath), "authored-stage-bath-utility")
        result.append(HydrideCompressorStage(name, time, end, 0. if isolated else inlet,
            0. if isolated else outlet, heat, 300., 300.))
        time = end
    return tuple(result)


def fingerprints():
    from importlib.util import find_spec

    root = Path(__file__).resolve().parents[1]
    files = ("src/h2physics/storage/hydride_compressor.py", "src/h2physics/storage/finite_hydride.py",
             "tests/test_hydride_compressor.py", "scripts/check_hydride_compressor.py",
             "docs/HYDRIDE_COMPRESSOR.md")
    result = {f: hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files if (root/f).exists()}
    spec = find_spec("lh2dt")
    if spec and spec.origin:
        digest = hashlib.sha256()
        for path in sorted(Path(spec.origin).parent.glob("*.py")):
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
        result["native:lh2dt"] = digest.hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-target", default="artifacts/native_packages")
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.native_target).resolve()))

    from h2physics.constants import R_J_MOL_K
    from h2physics.storage.finite_hydride import FiniteHydrideHeatInput, HydrideGasThermodynamics
    from h2physics.storage.hydride import HydrideState

    before = fingerprints()
    begin = perf_counter()
    model = make_case(solid_capacity=50.)
    schedule = stages(model, durations=(50., 40., 60., 50.))

    def run(m, schedule, *, loading=.01, step=1., rtol=1e-8):
        return m.run(schedule, initial_solid=HydrideState(loading, 300.),
            initial_bed_gas=m.bed.gas.state_pt(2e5, 300.), sample_interval_s=2.,
            maximum_step_s=step, relative_tolerance=rtol)

    trace = run(model, schedule)
    last = trace.points[-1]
    gates = {
        "full_four_stage_sequence": trace.termination == "schedule_end" and len(trace.segments) == 4,
        "actual_finite_admission": trace.admitted_hydrogen_kg > 5e-4,
        "actual_delivery_above_source": trace.delivered_hydrogen_kg > trace.initial_snapshot.bed.total_hydrogen_mass_kg
            and abs(trace.delivered_above_source_mass_kg-trace.delivered_hydrogen_kg) < 1e-13,
        "finite_source_receiver_feedback": last.snapshot.source.pressure_pa < trace.initial_snapshot.source.pressure_pa
            and last.snapshot.receiver.pressure_pa > trace.initial_snapshot.receiver.pressure_pa,
        "all_body_hydrogen": max(abs(p.total_hydrogen_residual_kg) for p in trace.points) < 1e-12,
        "all_body_U": max(abs(p.total_energy_residual_j) for p in trace.points) < 1e-5,
        "each_body_U": max(abs(b.energy_residual_j) for p in trace.points for b in p.body_balances.values()) < 1e-5,
        "separate_bed_gas_solid_U": max(max(abs(p.bed_gas_energy_residual_j), abs(p.bed_solid_energy_residual_j))
                                        for p in trace.points) < 1e-5,
        "actual_heating_and_cooling_duties": last.integrated["positive_bed_thermal_duty_j"] > 1000
            and last.integrated["negative_bed_thermal_duty_j"] < -1000,
        "actual_native_objects_retained": all(isinstance(p.source_native_derivative, model.native.tank.TankDerivative)
                                               and isinstance(p.snapshot.receiver_native_state, model.native.tank.TankState)
                                               for p in trace.points),
        "shared_nozzle_enthalpy_kinetic_closure": max(max(abs(p.inlet_nozzle.energy_residual_w),
                                                          abs(p.outlet_nozzle.energy_residual_w))
                                                     for p in trace.points) < 1e-7,
        "isolated_commands_no_flow": all(p.inlet_nozzle.mass_flow_kg_s == p.outlet_nozzle.mass_flow_kg_s == 0
                                          for s in (trace.segments[1], trace.segments[3]) for p in s.points),
        "thermal_sorption_reversal": trace.segments[0].points[-1].snapshot.bed.fraction
            > trace.segments[0].points[0].snapshot.bed.fraction
            and trace.segments[2].points[-1].snapshot.bed.fraction < trace.segments[2].points[0].snapshot.bed.fraction
            and trace.segments[3].points[-1].snapshot.bed.fraction > trace.segments[3].points[0].snapshot.bed.fraction,
    }
    extra = {}
    fresh = HydrideGasThermodynamics.coolprop("Hydrogen")
    h_ref = fresh.state_pt(1e5, 300.).enthalpy_j_kg*fresh.molar_mass_kg_mol-24000.
    independent_mass_error = independent_energy_error = 0.
    for point in trace.points[::8]:
        s = point.snapshot
        mass = model.bed.parameters.hydrogen_capacity_kg*s.bed.fraction
        energy = 50.*(s.bed.solid_temperature_k-300.)+mass/fresh.molar_mass_kg_mol*h_ref
        for thermo, volume in ((s.bed.gas, model.bed.free_gas_volume_m3),
                              (s.source, model.source.native_tank.geometry.volume_m3),
                              (s.receiver, model.receiver.native_tank.geometry.volume_m3)):
            state = fresh.state_pt(thermo.pressure_pa, thermo.temperature_k)
            m = state.density_kg_m3*volume
            mass += m
            energy += m*state.internal_energy_j_kg
        energy += 500.*(s.source_native_state.wall_temperature_K-300.)
        energy += 500.*(s.receiver_native_state.wall_temperature_K-300.)
        independent_mass_error = max(independent_mass_error, abs(mass-s.total_hydrogen_mass_kg))
        independent_energy_error = max(independent_energy_error, abs(energy-s.total_internal_energy_j))
    extra.update(independent_PT_hydrogen_mass_error_kg=independent_mass_error,
                 independent_PT_total_U_error_j=independent_energy_error)
    gates["independent_native_PT_mass_U"] = independent_mass_error < 1e-10 and independent_energy_error < 1e-4
    if not args.probe_only:
        fine_model = make_case(solid_capacity=50.)
        fine = run(fine_model, stages(fine_model, durations=(50., 40., 60., 50.)), step=.5, rtol=2e-9)
        delivery_change = abs(trace.delivered_hydrogen_kg-fine.delivered_hydrogen_kg)
        loading_change = abs(last.snapshot.bed.fraction-fine.points[-1].snapshot.bed.fraction)
        temperature_change = abs(last.snapshot.bed.solid_temperature_k-fine.points[-1].snapshot.bed.solid_temperature_k)
        gates["full_common_time_refinement"] = delivery_change < 1e-8 and loading_change < 1e-6 and temperature_change < .001
        extra.update(refinement_delivered_mass_difference_kg=delivery_change,
                     refinement_loading_difference=loading_change,
                     refinement_final_solid_temperature_difference_k=temperature_change)
        isolated_model = make_case(solid_capacity=50.)
        isolated = run(isolated_model, stages(isolated_model, durations=(1., 40., 1., 40.), isolated=True), loading=.1)
        gates["isolated_pressure_rise_is_not_delivery"] = (
            max(p.snapshot.bed.gas.pressure_pa for p in isolated.points) > 1e6
            and isolated.delivered_hydrogen_kg == 0)
        floor_model = make_case(floor_fraction=.99)
        floor = run(floor_model, stages(floor_model, durations=(1., 1., 1., 1.), isolated=True), loading=.1, step=.01)
        gates["positive_bed_floor_localized"] = floor.termination == "bed_gas_inventory_floor" and (
            abs(floor.points[-1].snapshot.bed.gas_mass_kg-floor_model.bed.domain.minimum_gas_mass_kg) < 1e-14)
        extra["bed_floor_time_s"] = floor.event_time_s
        reverse_model = make_case(absorption=0., desorption=0., solid_ua=0., gas_solid_ua=0.,
                                  source_pressure=1e5, receiver_pressure=3e5)
        reverse = run(reverse_model, stages(reverse_model, durations=(.5, .5, .5, .5)))
        gates["zero_kinetics_native_reverse_blocked"] = reverse.delivered_hydrogen_kg == reverse.admitted_hydrogen_kg == 0
        zero_gas = reverse_model.bed.gas.state_pt(100., 300.)
        mzero = zero_gas.density_kg_m3*reverse_model.bed.free_gas_volume_m3
        state = reverse_model.bed.snapshot_from_inventory(100., .2, mzero,
            mzero*zero_gas.internal_energy_j_kg, 300., isothermal_temperature_k=300.)
        rate = reverse_model.bed.rates(state, FiniteHydrideHeatInput(300.),
            gas_mass_flow_kg_s=1e-6, gas_enthalpy_flow_w=1e-6*zero_gas.enthalpy_j_kg,
            isothermal_temperature_k=300.)
        expected = -1e-6*R_J_MOL_K/reverse_model.bed.gas.molar_mass_kg_mol*300.
        ideal_relative_error = abs(rate.gas_thermostat_heat_w-expected)/abs(expected)
        gates["variable_mass_isothermal_ideal_limit"] = ideal_relative_error < 1e-4
        extra["native_isothermal_ideal_thermostat_relative_error"] = ideal_relative_error
    after = fingerprints()
    gates["host_native_bytes_unchanged"] = before == after
    gates = {k: bool(v) for k, v in gates.items()}
    print(json.dumps({"seconds": perf_counter()-begin, "termination": trace.termination,
        "admitted_mass_kg": trace.admitted_hydrogen_kg,
        "delivered_mass_kg": trace.delivered_hydrogen_kg,
        "delivered_above_source_mass_kg": trace.delivered_above_source_mass_kg,
        "final_bed_loading": trace.points[-1].snapshot.bed.fraction,
        "final_bed_temperature_k": trace.points[-1].snapshot.bed.solid_temperature_k,
        "max_mass_residual_kg": max(abs(p.total_hydrogen_residual_kg) for p in trace.points),
        "max_energy_residual_j": max(abs(p.total_energy_residual_j) for p in trace.points),
        "positive_bed_thermal_duty_j": trace.points[-1].integrated["positive_bed_thermal_duty_j"],
        "negative_bed_thermal_duty_j": trace.points[-1].integrated["negative_bed_thermal_duty_j"],
        "initial_bed_total_hydrogen_kg": trace.initial_snapshot.bed.total_hydrogen_mass_kg,
        "initial_source_pressure_pa": trace.initial_snapshot.source.pressure_pa,
        "final_source_pressure_pa": last.snapshot.source.pressure_pa,
        "initial_receiver_pressure_pa": trace.initial_snapshot.receiver.pressure_pa,
        "final_receiver_pressure_pa": last.snapshot.receiver.pressure_pa,
        "minimum_positive_delivery_receiver_source_pressure_ratio": min(
            p.snapshot.receiver.pressure_pa/p.snapshot.source.pressure_pa for p in trace.points
            if p.outlet_nozzle.mass_flow_kg_s > 0),
        "stages": [{"id": s.stage.stage_id, "final_P_bed_pa": s.points[-1].snapshot.bed.gas.pressure_pa,
                    "final_T_bed_k": s.points[-1].snapshot.bed.solid_temperature_k,
                    "final_x": s.points[-1].snapshot.bed.fraction,
                    "nfev": s.native_solution.nfev} for s in trace.segments],
        "gates": gates, "begin": before, "end": after, **extra}, indent=2), flush=True)
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
