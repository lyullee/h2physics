"""Original native CFD fixture; no engine, case or geometry run at import."""


def authored_case(*, identifier="obstacle_pulse", cells=16, source_on=True, obstacle_on=True):
    from h2physics.adapters.obstacle_dispersion import (
        FDS_SPECIES_BASIS,
        CartesianObstacle,
        CFDAuditBudgets,
        CFDMesh,
        CFDReceptor,
        HydrogenCFDSource,
        ObstacleDispersionCase,
    )
    from h2physics.core import Origin

    obstacles = (
        (CartesianObstacle("barrier", (0.5, 1.25, 0.5, 1.5, 0.0, 1.0)),) if obstacle_on else ()
    )
    mesh = CFDMesh(
        (0.0, 2.0, 0.0, 2.0, 0.0, 2.0),
        (cells, cells, cells),
        obstacles,
        "authored-grid-aligned-impermeable-box",
        "authored-unverified-CFD-grid",
        1e-10,
    )
    rates = (0.0, 1e-3, 1e-3, 0.0, 0.0) if source_on else (0.0,) * 5
    source = HydrogenCFDSource(
        "authored_release",
        (0.0, 0.25, 2.0, 2.25, 8.0),
        rates,
        (0.25, 0.75, 0.25, 0.75),
        310.0,
        "authored-release-clock",
        "enclosure-fixed-frame",
        "synthetic-finite-rate-boundary;not-measured",
        "supplied-expanded-warm-subsonic-boundary",
        FDS_SPECIES_BASIS,
        Origin.SYNTHETIC,
    )
    case = ObstacleDispersionCase(
        identifier,
        mesh,
        source,
        (
            CFDReceptor("near", (0.25, 0.375, 0.375)),
            CFDReceptor("behind", (1.5, 1.0, 0.5)),
            CFDReceptor("above", (1.0, 1.0, 1.5)),
        ),
        8.0,
        100.0,
        300.0,
        101325.0,
        (0.0, 0.0, -9.81),
        "LES",
        0.1,
        0.001,
        0.001,
        200,
        "authored-warm-low-Mach-envelope",
        "diagnostic-sealed-adiabatic-enclosure;not-a-facility-thermal-model",
    )
    budgets = CFDAuditBudgets(
        1e-8, 0.05, 1e-3, 1e-6, 1e-5, 1e-8, 1e-8, 10.0, 0.05, 0.003, 280.0, 350.0
    )
    return case, budgets


def selected_engine():
    import os
    from pathlib import Path

    from h2physics.adapters.obstacle_dispersion import FDSEngine

    return FDSEngine(
        Path(os.environ["H2PHYSICS_FDS_BINARY"]),
        os.environ["H2PHYSICS_FDS_SHA256"],
        "caller-reviewed-separate-FDS-6.11.1-binary-and-runtime",
        1,
        1800.0,
    )


def run_example(work_directory):
    from h2physics.adapters.obstacle_dispersion import run_obstacle_dispersion

    case, budgets = authored_case()
    return run_obstacle_dispersion(case, selected_engine(), budgets, work_directory=work_directory)
