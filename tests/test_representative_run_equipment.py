"""Small input-to-result examples; no native accuracy or precision campaign."""

import json
import math
from pathlib import Path

import numpy as np


def _record(name, inputs, outputs, record_property):
    record_property("representative_case", name)
    record_property("inputs", json.dumps(inputs, sort_keys=True))
    record_property("outputs", json.dumps(outputs, sort_keys=True))
    directory = Path(__file__).resolve().parents[1] / "artifacts/regression-e2e-20261102"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / ("equipment-" + name + ".json")
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps({"inputs": inputs, "outputs": outputs,
        "scope": "Basic representative input-to-output calculation, synthetic inputs"},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def test_finite_tank_transfer_input_to_product(record_property):
    from examples.finite_transfer import run_example
    from h2physics.adapters.finite_transfer_product import product_delivery_from_finite_transfer

    model, trace = run_example(with_line=False)
    final = trace.points[-1]
    product = product_delivery_from_finite_transfer(trace,
        receiver_node_id=model.receiver.node_id,
        product_boundary_evidence_id="representative-receiver-output")
    product.require_current()
    assert trace.termination == "requested-window-end"
    assert trace.actual_end_s == trace.requested_end_s == 100.4
    assert final.receiver_net_received_kg > 0.
    assert product.clock_id == trace.clock_id
    assert product.rate_series.units == ("kg/s",)
    assert math.isfinite(final.global_energy_residual_j)
    assert abs(final.global_mass_residual_kg) < 1e-8
    _record("finite-transfer", {
        "source_pressure_pa_absolute": 3e6, "receiver_pressure_pa_absolute": 1e6,
        "temperature_k": 300., "source_volume_m3": .05, "receiver_volume_m3": .01,
        "transfer_start_s": 100., "isolation_time_s": 100.2, "end_s": 100.4,
        "fluid": "Hydrogen", "with_line": False,
    }, {
        "clock_id": trace.clock_id, "termination": trace.termination,
        "actual_end_s": trace.actual_end_s,
        "source_withdrawn_kg": final.source_withdrawn_kg,
        "receiver_received_kg": final.receiver_net_received_kg,
        "source_final_mass_kg": final.inventories[model.source.node_id].mass_kg,
        "receiver_final_mass_kg": final.inventories[model.receiver.node_id].mass_kg,
        "maximum_product_rate_kg_s": max(product.interval_average_mass_rate_kg_s),
        "mass_residual_kg": final.global_mass_residual_kg,
        "energy_residual_j": final.global_energy_residual_j,
    }, record_property)


def test_finite_hydride_input_to_final_storage(record_property):
    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference,
        FiniteHydrideBed,
        FiniteHydrideDomain,
        FiniteHydrideHeatBoundary,
        FiniteHydrideHeatInput,
        HydrideGasThermodynamics,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate,
        HydrideKinetics,
        HydrideParameters,
        HydrideState,
        VanthoffPlateau,
    )

    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    material = HydrideParameters(.002, 1000., 24000., gas.molar_mass_kg_mol, 0.)
    kinetics = HydrideKinetics(VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(.01, 0., 300.), ArrheniusRate(.02, 0., 300.))
    reference = BoundHydrogenEnergyReference.from_gas(gas,
        temperature_k=300., pressure_pa=1e5, desorption_enthalpy_j_mol_h2=24000.,
        evidence_id="representative-authored-material-heat")
    bed = FiniteHydrideBed(material, kinetics, gas, reference,
        FiniteHydrideDomain(200., 600., 1e3, 1e7, 1e-7),
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.)
    boundary = FiniteHydrideHeatBoundary("representative-storage-clock", 0., 2.,
        lambda t, s: FiniteHydrideHeatInput(300.), "representative-bath")
    trace = bed.simulate(np.linspace(0., 2., 5), HydrideState(.1, 300.),
        gas.state_pt(3e5, 300.), boundary=boundary,
        clock_id=boundary.clock_id, maximum_step_s=.1)
    trace.require_current()
    final = trace.snapshots[-1]
    assert trace.termination == "window_end"
    assert trace.time_s[-1] == 2.
    assert .1 < final.fraction <= 1.
    assert final.gas_mass_kg > 0.
    assert math.isfinite(final.gas.pressure_pa)
    assert max(abs(trace.total_hydrogen_residual_kg)) < 1e-8
    _record("finite-hydride", {
        "fluid": "Hydrogen", "initial_pressure_pa_absolute": 3e5,
        "initial_temperature_k": 300., "initial_loading_fraction": .1,
        "capacity_kg": .002, "gas_volume_m3": .005, "duration_s": 2.,
        "material_coefficients": "explicit synthetic inputs, not fitted material data",
    }, {
        "termination": trace.termination, "clock_id": trace.clock_id,
        "final_time_s": float(trace.time_s[-1]), "final_loading_fraction": final.fraction,
        "final_pressure_pa_absolute": final.gas.pressure_pa,
        "final_solid_temperature_k": final.solid_temperature_k,
        "final_gas_mass_kg": final.gas_mass_kg,
        "final_solid_hydrogen_kg": final.solid_hydrogen_mass_kg,
        "absorbed_hydrogen_kg": float(trace.integrated_hydrogen_uptake_kg[-1]),
        "maximum_mass_residual_kg": float(max(abs(trace.total_hydrogen_residual_kg))),
    }, record_property)


def test_pipe_input_to_flow_result(record_property):
    from fluids.friction import friction_factor

    from h2physics.hydraulics import DarcyGeometry, solve_darcy_flow
    from h2physics.thermo import CoolPropProperties

    state = CoolPropProperties("Hydrogen").state_pt(2e5, 300.)
    result = solve_darcy_flow(DarcyGeometry(10., .01, 1e-6),
        density_kg_m3=state.density_kg_m3, viscosity_pa_s=state.viscosity_pa_s,
        driving_pressure_pa=1000., friction_law=lambda re, rough: friction_factor(re, rough))
    assert result.root_converged
    assert result.mass_flow_kg_s > 0.
    assert result.reynolds_number > 0.
    assert math.isfinite(result.velocity_m_s)
    _record("gas-pipe", {
        "fluid": "Hydrogen", "pressure_pa_absolute": 2e5, "temperature_k": 300.,
        "length_m": 10., "diameter_m": .01, "roughness_m": 1e-6,
        "driving_pressure_pa": 1000., "friction_provider": "fluids.friction.friction_factor",
    }, {
        "mass_flow_kg_s": result.mass_flow_kg_s, "velocity_m_s": result.velocity_m_s,
        "reynolds_number": result.reynolds_number,
        "darcy_friction_factor": result.darcy_friction_factor,
        "momentum_residual_pa": result.momentum_residual_pa,
    }, record_property)
