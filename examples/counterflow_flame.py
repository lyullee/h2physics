"""Small native H2/air opposed-flow example for a later cluster campaign."""


def build(*, fuel_mass_flux=0.2, oxidizer_mass_flux=0.8, slope=0.1):
    import hashlib
    from pathlib import Path

    import cantera as ct

    from h2physics.adapters.cantera import CanteraGas, MechanismBasis, ReactiveState
    from h2physics.combustion import (
        CounterflowBoundary,
        CounterflowFlameSettings,
        solve_counterflow_diffusion_flame,
    )

    source = (Path(ct.__file__).parent / "data" / "h2o2.yaml").read_bytes()
    basis = MechanismBasis(
        "Cantera-h2o2-ohmech",
        hashlib.sha256(source).hexdigest(),
        "Cantera-BSD-3-Clause; upstream mechanism provenance remains attached",
        ("https://cantera.org/3.2/examples/python/onedim/diffusion_flame.html",),
        250.0,
        3500.0,
        1e4,
        2e6,
    )
    gas = CanteraGas.from_yaml(source, basis, phase_name="ohmech")
    pressure = 101325.0
    fuel = CounterflowBoundary(ReactiveState(300.0, pressure, {"H2": 1.0}), fuel_mass_flux)
    oxidizer = CounterflowBoundary(
        ReactiveState(300.0, pressure, {"O2": 0.21, "N2": 0.79}),
        oxidizer_mass_flux,
    )
    settings = CounterflowFlameSettings(
        width_m=0.02,
        transport_model="mixture-averaged",
        soret_enabled=False,
        refinement_slope=slope,
        maximum_grid_points=800,
    )
    return solve_counterflow_diffusion_flame(gas, fuel, oxidizer, settings=settings)
