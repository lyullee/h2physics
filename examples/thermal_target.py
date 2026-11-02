"""Authored finite thermal-target fixture; importing it performs no solve."""

import numpy as np

from h2physics.adapters.thermal_target import (
    IncidentHeatHistory,
    LumpedThermalTarget,
    ThermalTargetTolerances,
    run_thermal_target,
)
from h2physics.core import Origin


def authored_model(*, flux_w_m2=12_000.0, emissivity=0.75,
                   convective_coefficient_w_m2_k=8.0, maximum_temperature_k=900.0):
    history = IncidentHeatHistory(
        np.array([0.0, 10.0, 30.0]),
        np.array([flux_w_m2, 0.0]),
        "authored-target-clock",
        "authored-target-frame",
        "synthetic-incident-fixture",
        "front-face-radiation",
        "synthetic-energy-audit-only",
        Origin.SYNTHETIC,
        object(),
    )
    target = LumpedThermalTarget(
        area_m2=1.0,
        heat_capacity_j_k=100_000.0,
        initial_temperature_k=300.0,
        absorptivity=0.8,
        emissivity=emissivity,
        convective_coefficient_w_m2_k=convective_coefficient_w_m2_k,
        ambient_temperature_k=300.0,
        radiant_surroundings_temperature_k=300.0,
        minimum_temperature_k=250.0,
        maximum_temperature_k=maximum_temperature_k,
        material_evidence_id="synthetic-lumped-capacity",
        geometry_evidence_id="synthetic-one-square-metre-face",
        convection_evidence_id="synthetic-held-coefficient",
        radiation_evidence_id="SI-blackbody-constant-and-synthetic-emissivity",
        origin=Origin.SYNTHETIC,
    )
    return history, target, ThermalTargetTolerances(energy_j=1e-3,
                                                     relative_energy=1e-8,
                                                     clock_s=1e-10)


def run_example(**parameters):
    history, target, tolerances = authored_model(**parameters)
    return run_thermal_target(history, target, tolerances, maximum_step_s=0.25)
