"""Build a caller-parameterized pure-H2 compression example without running it."""


def problem():
    """Return the native provider factory and explicit compressor inputs.

    The example calls no Cantera solver until the caller explicitly invokes
    ``run_hydrogen_compression`` with a fresh ideal-gas phase.
    """
    from h2physics.combustion.fuel_compression import HydrogenCompressionInputs

    inputs = HydrogenCompressionInputs(
        mechanism_id="caller-reviewed-mechanism",
        process_window_id="steady-compressor-point",
        inlet_temperature_k=298.15,
        inlet_pressure_pa=300_000.0,
        discharge_pressure_pa=800_000.0,
        hydrogen_mass_flow_kg_s=0.04,
        isentropic_efficiency=0.78,
        state_evidence_id="replace-with-fuel-source-evidence",
        efficiency_evidence_id="replace-with-machine-evidence",
    )
    return inputs


def run_example(phase, inputs=None):
    """Run only when the caller provides a reviewed native Cantera phase."""
    from h2physics.combustion.fuel_compression import run_hydrogen_compression

    return run_hydrogen_compression(phase, inputs or problem())


def real_fluid_problem():
    """Return a directly injected CoolProp HEOS provider and real-fluid inputs."""
    from h2physics.combustion.fuel_compression import HydrogenRealFluidCompressionInputs
    from h2physics.thermo import CoolPropProperties

    provider = CoolPropProperties("Hydrogen", backend="HEOS")
    inputs = HydrogenRealFluidCompressionInputs(
        provider_id="coolprop-hydrogen-heos",
        process_window_id="steady-real-fluid-fuel",
        inlet_temperature_k=298.15,
        inlet_pressure_pa=300_000.0,
        discharge_pressure_pa=800_000.0,
        hydrogen_mass_flow_kg_s=0.04,
        isentropic_efficiency=0.78,
        temperature_bounds_k=(250.0, 700.0),
        pressure_bounds_pa=(100_000.0, 20_000_000.0),
        state_evidence_id="replace-with-fuel-source-evidence",
        efficiency_evidence_id="replace-with-machine-evidence",
        domain_evidence_id="replace-with-qualified-application-envelope",
    )
    return provider, inputs


def run_real_fluid_example(provider=None, inputs=None):
    """Run only when the caller explicitly selects the real-fluid example."""
    from h2physics.combustion.fuel_compression import run_real_fluid_hydrogen_compression

    if provider is None or inputs is None:
        default_provider, default_inputs = real_fluid_problem()
        provider = provider or default_provider
        inputs = inputs or default_inputs
    return run_real_fluid_hydrogen_compression(provider, inputs)
