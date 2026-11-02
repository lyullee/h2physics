"""Deferred source-transition conservation contract for native HyRAM snapshots."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hyram-plug-to-gaussian-transition-ledger",
        profile="preferred-dispersion",
        entrypoint=__name__ + ":validate_contract",
        invariants=(
            "same-run native-source identity and transition axes are retained",
            "radial H2 and total-mixture mass fluxes use declared annular quadrature",
            "axial momentum includes pressure thrust against a common ambient reference",
            "excess enthalpy plus kinetic energy uses one ambient caloric reference",
            "each balance and numerical integration estimate has its own fixed budget",
            "unknown transfer terms or missing profiles remain incomplete rather than zero",
            "captured snapshots and audits reject direct construction, replacement and mutation",
            "a conservation receipt does not change the HyRAM source or prove field accuracy",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.adapters.hyram_transition import (
        HyRAMRadialPlaneSnapshot,
        HyRAMTransitionBudgets,
        audit_hyram_source_transition,
        capture_hyram_radial_plane,
    )

    native = object()

    def capture(plane, *, pressure=(101325.,), enthalpy=(10.,)):
        return capture_hyram_radial_plane(
            run_id="synthetic-hyram-run", source_revision="fixture-revision",
            plane=plane, plane_id="fixture:"+plane, transition_id="fixture-transition",
            native_source=native, axis_unit_vector=(1., 0., 0.),
            plane_normal_unit_vector=(1., 0., 0.), radial_coordinate_m=np.array([0.]),
            annular_area_weight_m2=np.array([1.]), density_kg_m3=np.array([1.]),
            hydrogen_mass_fraction=np.array([.5]), normal_velocity_m_s=np.array([2.]),
            axial_velocity_m_s=np.array([2.]), speed_squared_m2_s2=np.array([4.]),
            pressure_pa=None if pressure is None else np.array(pressure, dtype=float),
            mixture_enthalpy_j_kg=None if enthalpy is None else np.array(enthalpy, dtype=float),
            ambient_pressure_pa=101325., ambient_enthalpy_j_kg=0.,
            thermo_model_id="synthetic-eos-v1", composition_basis_id="H2-air-mass-v1",
            profile_definition_id="fixture-"+plane, quadrature_id="one-annulus-v1",
            radial_cutoff_m=1.,
        )

    plug = capture("expanded_plug_exit")
    gaussian = capture("gaussian_entry")
    budgets = HyRAMTransitionBudgets(1e-6, 1e-6, 1e-6, 1e-6,
                                    1e-8, 1e-8, 1e-8, 1e-8)
    audit = audit_hyram_source_transition(
        plug, gaussian, h2_interstage_source_kg_s=0.,
        ambient_entrainment_kg_s=0., external_axial_force_n=0.,
        external_energy_rate_w=0., budgets=budgets,
        quadrature_errors=(0., 0., 0., 0.),
    )
    assert audit.overall_status == "accepted"
    assert audit.h2.inlet_flux == 1. and audit.h2.outlet_flux == 1.
    assert audit.mixture.inlet_flux == 2. and audit.mixture.outlet_flux == 2.
    assert audit.axial_momentum.inlet_flux == 4. and audit.axial_momentum.residual == 0.
    assert audit.excess_energy.inlet_flux == 24. and audit.excess_energy.residual == 0.
    assert audit.require_current() is audit

    rejected = 0
    try:
        replace(plug)
    except TypeError:
        rejected += 1
    else:
        raise AssertionError("A cloned radial-plane snapshot reused its issuance")
    try:
        HyRAMRadialPlaneSnapshot(**{name: getattr(plug, name)
            for name in HyRAMRadialPlaneSnapshot.__dataclass_fields__
            if name != "_issuer"})
    except TypeError:
        rejected += 1
    else:
        raise AssertionError("A direct radial-plane receipt claimed provider capture")
    try:
        replace(audit, overall_status="accepted")
    except TypeError:
        rejected += 1
    else:
        raise AssertionError("A cloned transition audit reused its consumed issuance")

    missing_transfer = audit_hyram_source_transition(
        capture("expanded_plug_exit"), capture("gaussian_entry"),
        h2_interstage_source_kg_s=None, ambient_entrainment_kg_s=0.,
        external_axial_force_n=0., external_energy_rate_w=0., budgets=budgets,
        quadrature_errors=(0., 0., 0., 0.),
    )
    assert missing_transfer.h2.status == "incomplete"
    assert missing_transfer.overall_status == "incomplete"
    missing_profile = audit_hyram_source_transition(
        capture("expanded_plug_exit", pressure=None),
        capture("gaussian_entry", pressure=None),
        h2_interstage_source_kg_s=0., ambient_entrainment_kg_s=0.,
        external_axial_force_n=0., external_energy_rate_w=0., budgets=budgets,
        quadrature_errors=(0., 0., None, 0.),
    )
    assert missing_profile.axial_momentum.status == "incomplete"
    assert missing_profile.overall_status == "incomplete"
    original_revision = plug.source_revision
    object.__setattr__(plug, "source_revision", "forged-revision")
    try:
        audit.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("A modified source revision left the audit current")
    finally:
        object.__setattr__(plug, "source_revision", original_revision)
    assert audit.require_current() is audit
    outside_budget = audit_hyram_source_transition(
        capture("expanded_plug_exit"), capture("gaussian_entry"),
        h2_interstage_source_kg_s=.01, ambient_entrainment_kg_s=0.,
        external_axial_force_n=0., external_energy_rate_w=0., budgets=budgets,
        quadrature_errors=(0., 0., 0., 0.),
    )
    assert outside_budget.h2.status == "rejected"
    assert outside_budget.overall_status == "rejected"
    try:
        gaussian.annular_area_weight_m2.setflags(write=True)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Captured annular weights can be modified in place")
    assert rejected >= 4
    return ValidationOutcome(True, {
        "h2_flux_kg_s": audit.h2.inlet_flux,
        "mixture_flux_kg_s": audit.mixture.inlet_flux,
        "axial_momentum_n": audit.axial_momentum.inlet_flux,
        "excess_energy_w": audit.excess_energy.inlet_flux,
        "incomplete_unknown_terms": missing_transfer.overall_status,
        "incomplete_missing_properties": missing_profile.overall_status,
        "rejected_h2_balance": outside_budget.overall_status,
        "negative_contracts_rejected": rejected,
    }, ("Source-transition conservation receipt only; no source correction, independent measurement comparison, or HyRAM field qualification is included",))
