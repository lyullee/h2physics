"""Original synthetic UH2SC input mapping; native execution is explicitly deferred.

These dimensions/material/flow inputs are authored verification fixtures, not a
surveyed cavern, salt dataset, validated scenario or geomechanical qualification.
"""


def authored_inputs(*, mode="equilibrium", step_s=2.0, rock_cells=8):
    if mode not in {"equilibrium", "rock-exchange", "injection-withdrawal"}:
        raise ValueError("Select an explicit authored verification mode")
    end = 12.0
    times = [0.0, 4.0, 5.0, 9.0, 10.0, end + step_s]
    rates = (
        [0.01, 0.01, -0.01, -0.01, 0.0, 0.0]
        if mode == "injection-withdrawal"
        else [0.0] * len(times)
    )
    return {
        "calculation": {
            "end_time": end,
            "max_time_step": step_s,
            "min_time_step": step_s,
            "cool_prop_backend": "HEOS",
            "solution_tolerance": 1e-9,
            "run_parallel": False,
            "num_processors": 1,
        },
        "initial": {
            "fluid": "Hydrogen",
            "pressure": 6e6,
            "temperature": 300.0,
            "liquid_temperature": 300.0,
            "liquid_height": 0.5,
            "time_step": step_s,
            "start_date": "2026-10-28",
        },
        "cavern": {
            "depth": 300.0,
            "diameter": 8.0,
            "height": 18.0,
            "overburden_pressure": 12e6,
            "emissivity": 0.0,
            "min_operational_temperature": 280.0,
            "max_operational_temperature": 360.0,
            "min_operational_pressure_ratio": 0.1,
            "max_operational_pressure_ratio": 0.9,
            "max_volume_change_per_day": 2.0,
            "ghe_name": "rock",
        },
        "heat_transfer": {"h_inner": 8.0, "h_cavern_brine": 1.0},
        "ghes": {
            "rock": {
                "density": 2100.0,
                "heat_capacity": 850.0,
                "thermal_conductivity": 3.5,
                "farfield_temperature": 301.5 if mode == "rock-exchange" else 300.0,
                "distance_to_farfield_temp": 20.0,
                "modeled_radial_thickness": 60.0,
                "number_elements": rock_cells,
                "height": 18.0,
                "inner_radius": 4.0,
                "initial_conditions": {"Q0": 0.0, "Qend": 0.0},
            }
        },
        "wells": {
            "well": {
                "ideal_pipes": True,
                "pipe_diameters": [0.0, 0.0, 0.12, 0.16],
                "pipe_lengths": [310.0],
                "pipe_roughness_ratios": [1e-5],
                "pipe_thermal_conductivities": [16.0],
                "pipe_total_minor_loss_coefficients": [0.0],
                "control_volume_length": 1000.0,
                "ghe_name": "rock",
                "valves": {
                    "operation": {
                        "type": "mdot",
                        "time": times,
                        "mdot": rates,
                        "reservoir": {
                            "pressure": "follow cavern",
                            "temperature": 300.0,
                            "fluid": "Hydrogen",
                        },
                    }
                },
            }
        },
    }


def authored_owner():
    from h2physics.adapters.underground_storage import (
        Uh2scUndergroundStorage,
        UndergroundAuditBudgets,
        UndergroundDomain,
        UndergroundEvidence,
    )
    from h2physics.core import Origin

    evidence = UndergroundEvidence(
        "authored-cavern-clock",
        "cavern-fixed-frame",
        "not-a-surveyed-site",
        "authored-finite-operation",
        1000.0,
        "synthetic-cylindrical-geometry",
        "synthetic-rho-cp-k",
        "fixed-temperature-external-reservoir;finite-modeled-rock",
        "signed-prescribed-native-ideal-well",
        "native-brine-is-pure-water;not-a-salinity-fit",
        "thermal-U-control-volume;KE-PE-closure-unqualified",
        Origin.SYNTHETIC,
    )
    return Uh2scUndergroundStorage(
        evidence,
        UndergroundDomain(1e6, 10e6, 280.0, 365.0, 1e-3, "authored-warm-dilute-vapor-envelope"),
        UndergroundAuditBudgets(1e-5, 1e-5, 1.0, 1e-7, 1e-7, 1e-8),
    )


def run_example():
    """Actual native execution, only when explicitly invoked in the later profile."""
    return authored_owner().run(
        authored_inputs(mode="rock-exchange"),
        solver_options={
            "TOL": 1e-9,
            "LOG_PROGRESS": False,
            "MAXITER": 100,
            "USE_RELATIVE_CONVERGENCE": True,
        },
    )


if __name__ == "__main__":
    trace = run_example()
    print(trace.numerically_admitted, trace.residuals[-1])
