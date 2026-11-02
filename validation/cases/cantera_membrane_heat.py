"""Deferred contract for native finite-membrane thermostat duty accounting."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="cantera-membrane-thermostat-heat-duty-handoff",
        profile="counterflow-flame",
        entrypoint=__name__ + ":validate_handoff",
        invariants=(
            "signed native cumulative thermostat energy maps by exact interval differences in joules",
            "both finite thermostats retain distinct physical component identities and temperature observations",
            "reporting window uses exact accepted native samples on the membrane physical-seconds clock",
            "changed native terminal state or incompatible clock is rejected by source currentness guards",
            "handoff reports imposed thermostat duty only and makes no heat-availability or utility-capacity claim",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    import hashlib
    from pathlib import Path

    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.cantera_membrane import (
        CanteraDustyGasTransport, MembraneEndpoint, MembraneTransportEvidence,
        PorousTransportGeometry,
    )
    from h2physics.adapters.cantera_membrane_device import (
        CanteraFiniteMembraneDevice, FiniteMembraneParameters,
        MembraneIntegrationSettings,
    )
    from h2physics.adapters.cantera_membrane_heat import bind_cantera_membrane_thermostat_heat
    from h2physics.adapters.thermal_utilities import HeatWindow
    from h2physics.core import Origin

    mechanism = Path(ct.__file__).parent / "data" / "gri30.yaml"
    mechanism_bytes = mechanism.read_bytes()
    phase_factory = lambda: ct.Solution(str(mechanism), transport_model="multicomponent")
    phase = phase_factory()
    species = tuple(phase.species_names)
    left_x, right_x = np.zeros(len(species)), np.zeros(len(species))
    left_x[species.index("H2")] = .7
    left_x[species.index("N2")] = .3
    right_x[species.index("H2")] = .3
    right_x[species.index("N2")] = .7
    basis = MechanismBasis(
        "Hangang-membrane-gri30-contract", hashlib.sha256(mechanism_bytes).hexdigest(),
        "Cantera-BSD-3-Clause; mechanism-distribution-scope-reviewed-at-runtime",
        ("https://cantera.org/3.2/python/transport.html#cantera.DustyGasTransport",),
        max(300., phase.min_temp), min(3000., phase.max_temp), 2.e4, 2.e6)
    geometry = PorousTransportGeometry(
        .35, 2.0, 1.e-7, 1.e-12, 1.e-3, "authored-contract-pore", "authored-synthetic-geometry",
        Origin.SYNTHETIC)
    evidence = MembraneTransportEvidence(
        "synthetic-transport-input", "synthetic-gas-phase", "frozen-neutral-gas",
        "Cantera-native-enthalpy-reference", "normal-H2-default-mechanism-partition")
    endpoint_common = dict(
        temperature_k=300., species=species, composition_basis="mole",
        phase_id=evidence.gas_phase_id, geometry_id=geometry.geometry_id,
        source_id="synthetic-membrane-endpoint", origin=Origin.SYNTHETIC)
    left = MembraneEndpoint(
        pressure_pa_absolute=2.e5, fractions=left_x, boundary_id="left-side", **endpoint_common)
    right = MembraneEndpoint(
        pressure_pa_absolute=1.e5, fractions=right_x, boundary_id="right-side", **endpoint_common)
    transport = CanteraDustyGasTransport(phase_factory, basis, evidence=evidence)
    settings = MembraneIntegrationSettings(maximum_time_step_s=.02, maximum_steps=10000)
    parameters = FiniteMembraneParameters(
        .01, .01, .01, "synthetic-membrane-clock", 0., .22,
        "authored-imposed-isothermal-thermostats", "authored-membrane-run", Origin.SYNTHETIC)
    trace = CanteraFiniteMembraneDevice(transport).run(
        left, right, geometry, parameters, (0., .1, .2), settings=settings)
    window = HeatWindow(0., .2, parameters.clock_id, "authored-thermal-report-window")
    duties = bind_cantera_membrane_thermostat_heat(trace, window)
    expected = np.diff(trace.thermostat_heat_j, axis=0)
    assert len(duties) == 2
    assert all(np.array_equal(duty.snapshot.heat_into_process_j, expected[:, side])
               for side, duty in enumerate(duties))
    assert tuple(duty.snapshot.components[0].identifier for duty in duties) == (
        "left-thermostat", "right-thermostat")
    for duty in duties:
        duty.require_current()
    try:
        bind_cantera_membrane_thermostat_heat(
            trace, HeatWindow(0., .2, "foreign-clock", "negative-clock-contract"))
    except ValueError:
        wrong_clock_rejected = True
    else:
        raise AssertionError("Foreign membrane clock was accepted")
    return ValidationOutcome(True, {
        "interval_count": len(expected),
        "side_thermostat_heat_j": [float(np.sum(expected[:, side])) for side in (0, 1)],
        "component_count": sum(len(duty.snapshot.components) for duty in duties),
        "foreign_clock_rejected": wrong_clock_rejected,
    }, ("native finite-membrane thermostat duty only",))
