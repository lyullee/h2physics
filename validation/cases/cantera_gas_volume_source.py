"""Deferred pure-H2 Cantera gas-volume vent to finite-source contract."""

from pathlib import Path
from hashlib import sha256

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="cantera-gas-volume-vent-finite-source-handoff",
        profile="counterflow-flame",
        entrypoint=__name__ + ":validate_handoff",
        parameters={},
        invariants=(
            "only a frozen pure-H2, no-feed, single named vent trace is admitted",
            "each source mass interval equals the native cumulative named-vent mass difference",
            "mechanism, H2 spin/reference basis and source clock identities are preserved",
            "native total-mass, species and energy residual budgets are enforced",
            "representative H2 enthalpy closes the native cumulative vent-energy ledger",
            "mutated trace endpoint and incompatible H2 reference are rejected",
            "no pressure-driven valve law or downstream dispersion result is inferred",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    import cantera as ct

    from dataclasses import replace

    from h2physics.adapters.cantera import MechanismBasis, ReactiveState
    from h2physics.adapters.cantera_gas_volume_source import bind_cantera_gas_volume_vent
    from h2physics.adapters.cantera_properties import CanteraFrozenGasProperties
    from h2physics.adapters.cantera_volume import CanteraOpenGasVolume, GasBoundaryRate, GasVent
    from h2physics.core import Origin, PropertyBasis
    from h2physics.release import SourceLocation

    mechanism_path = Path(ct.__file__).parent / "data" / "nasa_gas.yaml"
    raw = mechanism_path.read_bytes()
    all_species = {item.name: item for item in ct.Species.list_from_yaml(
        raw.decode("utf-8"), section="species")}
    h2 = all_species["H2"]
    phase_factory = lambda: ct.Solution(
        thermo="ideal-gas", species=[h2], name="authored-frozen-H2-vent")
    basis = MechanismBasis(
        "Hangang-H2-volume-source-contract", sha256(raw).hexdigest(),
        "Cantera-BSD-3-Clause; NASA-TM-4513-public-US-government-work",
        ("https://cantera.org/3.2/python/zerodim.html",
         "https://ntrs.nasa.gov/citations/19940013151"),
        200., 6000., 1.e4, 5.e6)
    clock = "authored-H2-vent-clock"
    vent_rate = GasBoundaryRate(
        "relief-port", clock, 0., 3., lambda time_s: 1.e-5,
        Origin.SYNTHETIC,
        "authored-relief-port-source", phase_access="time_only")
    downstream = ReactiveState(300., 101325., {"H2": 1.})
    trace = CanteraOpenGasVolume(phase_factory, basis).run(
        ReactiveState(300., 2.e5, {"H2": 1.}), (0., 1., 2.), volume_m3=.05,
        clock_id=clock, vents=(GasVent(vent_rate, downstream),),
        maximum_time_step_s=.1, relative_tolerance=1.e-9, absolute_tolerance=1.e-13)
    property_phase = phase_factory()
    properties = CanteraFrozenGasProperties(
        property_phase, basis, {"H2": 1.},
        hydrogen_partition_id=trace.hydrogen_partition_id)
    total_mass = float(trace.integral("outlet:relief-port:mass")[-1])
    mean_enthalpy = float(trace.integral("outlet:enthalpy")[-1])/total_mass
    representative = properties.state_ph(150000., mean_enthalpy)
    location = SourceLocation(
        "authored-relief-port-source", clock, "synthetic-facility-frame",
        (0., 0., 2.), (0., 0., 1.))
    handoff = bind_cantera_gas_volume_vent(
        trace, vent_boundary_id="relief-port", location=location,
        representative_state=representative,
        boundary_projection_evidence_id="synthetic-relief-port-plane",
        state_projection_evidence_id="synthetic-native-mean-enthalpy-state",
        mass_tolerance_kg=1.e-7, species_tolerance_kg=1.e-7,
        energy_tolerance_j=1.e-3, relative_energy_tolerance=1.e-8)
    handoff.require_current()
    assert abs(handoff.source.total_mass_kg-total_mass) <= 1.e-12
    assert len(handoff.source.mass_kg) == len(trace.time_s)-1
    assert handoff.source.location is location
    wrong_basis = replace(representative,
        basis=PropertyBasis(representative.basis.fluid, "different-native-reference",
                            representative.basis.spin_composition))
    try:
        bind_cantera_gas_volume_vent(
            trace, vent_boundary_id="relief-port", location=location,
            representative_state=wrong_basis,
            boundary_projection_evidence_id="synthetic-relief-port-plane",
            state_projection_evidence_id="synthetic-wrong-reference",
            mass_tolerance_kg=1.e-7, species_tolerance_kg=1.e-7,
            energy_tolerance_j=1.e-3, relative_energy_tolerance=1.e-8)
    except ValueError:
        wrong_basis_rejected = True
    else:
        raise AssertionError("Incompatible mechanism-energy reference was accepted")
    original = trace.phase_fingerprint
    object.__setattr__(trace, "phase_fingerprint", "changed-after-run")
    try:
        handoff.require_current()
    except ValueError:
        stale_trace_rejected = True
    else:
        raise AssertionError("A changed native source trace remained accepted")
    object.__setattr__(trace, "phase_fingerprint", original)
    handoff.require_current()
    return ValidationOutcome(True, {
        "released_mass_kg": handoff.released_mass_kg,
        "native_outlet_enthalpy_j": handoff.native_outlet_enthalpy_j,
        "projected_enthalpy_residual_j": handoff.enthalpy_residual_j,
        "mass_bins": len(handoff.source.mass_kg),
        "wrong_reference_rejected": wrong_basis_rejected,
        "stale_trace_rejected": stale_trace_rejected,
    }, (
        "Synthetic frozen pure-H2 native control volume only.",
        "One constant mean thermodynamic state is an explicit finite-source projection.",
        "No valve capacity, failure frequency, plume, ignition or consequence is modeled.",
    ))
