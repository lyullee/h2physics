"""Deferred native catalytic plug-flow contract; no mechanism is bundled."""

from h2physics.cluster_validation import ValidationCase


def cases():
    return (ValidationCase(
        identifier="cantera-native-catalytic-plug-flow",
        profile="counterflow-flame",
        entrypoint=__name__ + ":validate_catalytic_pfr",
        invariants=(
            "native-FlowReactor-and-ReactorSurface-own-spatial-gas-surface-kinetics",
            "inlet-mechanism-bytes-hash-phase-identities-and-declared-domain-are-retained",
            "sampled-axial-grid-is-strictly-increasing-and-internal-step-limit-is-independent",
            "gas-state-and-surface-coverage-remain-finite-normalized-and-in-domain",
            "trace-rejects-native-endpoint-or-mechanism-identity-mutation",
            "frictionless-adiabatic-PFR-does-not-claim-pressure-drop-or-process-yield-qualification",
        ),
    ),)


def validate_catalytic_pfr(*, work_directory, **parameters):
    del work_directory, parameters
    import hashlib
    from pathlib import Path

    import cantera as ct

    from h2physics.adapters.cantera import (
        MechanismBasis,
        NativeMechanismSource,
        ReactiveState,
    )
    from h2physics.adapters.cantera_catalytic_pfr import CanteraCatalyticPFR

    path = next(Path(directory) / "ptcombust.yaml"
                for directory in ct.get_data_directories()
                if (Path(directory) / "ptcombust.yaml").is_file())
    raw = path.read_bytes()
    basis = MechanismBasis(
        "installed-Cantera-ptcombust-software-contract",
        hashlib.sha256(raw).hexdigest(),
        "installed-mechanism-separate-rights-not-redistributed",
        ("https://cantera.org/3.2/",),
        600.0, 1400.0, 10_000.0, 1_000_000.0,
    )
    owner = CanteraCatalyticPFR(
        NativeMechanismSource(raw, "gas"), basis,
        gas_phase_name="gas", surface_phase_name="Pt_surf",
    )
    native_surface = ct.Interface(yaml=raw.decode("utf-8"), name="Pt_surf")
    coverages = {name: float(name == "PT(S)") for name in native_surface.species_names}
    trace = owner.run(
        ReactiveState(900.0, 101_325.0, {"H2": 0.15, "O2": 0.05, "AR": 0.80}),
        initial_coverages=coverages,
        axial_position_m=(0.0, 1e-5, 1e-4, 1e-3),
        cross_section_area_m2=1e-4,
        surface_area_to_volume_m_inv=2e4,
        mass_flow_rate_kg_s=2e-5,
        maximum_axial_step_m=1e-6,
        relative_tolerance=1e-9,
        absolute_tolerance=1e-15,
    )
    assert trace.require_current() is trace
    assert tuple(point.axial_position_m for point in trace.points) == tuple(trace.axial_position_m)
    assert all(point.pressure_pa > 0.0 and point.temperature_k > 0.0 for point in trace.points)
    assert all(abs(float(point.gas_mole_fractions.sum()) - 1.0) < 1e-8
               for point in trace.points)
    assert all(abs(float(point.surface_coverages.sum()) - 1.0) < 1e-8
               for point in trace.points)
    assert trace.points[-1].axial_position_m == 1e-3
