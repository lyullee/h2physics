"""Deferred contracts for stationary HyRAM-to-finite-source projection."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="hyram-finite-source-projection",
            profile="preferred-dispersion",
            entrypoint=__name__ + ":validate_projection",
            invariants=(
                "a source-bound HyRAM jet receipt can only be issued by the checked native run path",
                "directly fabricated or dataclass-replaced HyRAM jet receipts cannot enter finite-source projection",
                "accepted HyRAM steady H2 flow integrates to the declared finite interval mass",
                "source clock, state basis, evidence and termination meaning are retained",
                "upstream and caller-projected enthalpy rates remain separate with a residual",
                "an energy-incompatible state is rejected or retained only as an explicit diagnostic",
                "a native HyRAM boundary rejected by its source gate cannot feed the projection",
                "native centreline mutation invalidates a captured finite-source projection",
                "direct component-flow receipt construction rejects a stale parent projection",
                "captured HyRAM mass and enthalpy gate budgets cannot be changed after admission",
                "captured HyRAM centreline storage cannot be made writable by a caller",
                "native HyRAM flow/flux output mutation invalidates the captured admission receipt",
                "directly constructed HyRAM flow, Gaussian summaries and accepted flag match native section fields",
                "composition allocation preserves the HyRAM hydrogen mass flow while recording caller-declared accompanying gases",
                "mixture component rates are immutable and checked against retained species identities",
            ),
        ),
    )


def validate_projection(*, work_directory, **parameters):
    from types import SimpleNamespace

    import numpy as np

    from h2physics.adapters.hyram import HyRAMJetRun, _issue_hyram_jet_run
    from h2physics.adapters.hyram_jet_source import (
        HyRAMFiniteSourceError,
        project_hyram_jet_to_finite_source,
    )
    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.release import NozzleOpening, SourceLocation

    del work_directory, parameters
    basis = PropertyBasis("Hydrogen", "hyram-finite-source-contract", "normal")
    upstream = ThermoState(basis, 2.e6, 300., 1.6, 4.e6, 2.75e6, 5.e4, "gas")
    ambient = ThermoState(PropertyBasis("Air", "hyram-finite-source-contract"),
                          101325., 298., 1.2, 3.e5, 2.14e5, 6.8e3, "gas")
    location = SourceLocation("leak", "plant-clock", "global-xz", (0., 0., 0.), (1., 0., 0.))
    opening = NozzleOpening.circular("leak", .01, effective_area_factor=1., area_basis_id="fixture")
    native = SimpleNamespace(
        S=np.array([0., 1.]), x=np.array([0., 1.]), y=np.array([0., 0.]),
        Y_cl=np.array([1., .5]), X_cl=np.array([1., .4]),
        rho_cl=np.array([1., 1.]),
        V_cl=np.array([.02*2./np.pi, .08/np.pi]),
        B=np.array([1., 1.]), lam=1., mass_flow_rate=.02,
    )
    centreline = np.c_[native.S, native.x, native.y, native.Y_cl, native.X_cl]
    native_flux = (np.pi*native.rho_cl*native.Y_cl*native.V_cl*native.B**2
                   /(1.+1./native.lam**2))
    jet_fields = dict(
        native=native, upstream=upstream, ambient=ambient, opening=opening,
        location=location, evidence_id="native-fixture", mass_flow_kg_s=.02,
        gaussian_entry_h2_flow_kg_s=float(native_flux[0]),
        maximum_transport_h2_residual_kg_s=float(np.max(np.abs(native_flux-native_flux[0]))),
        maximum_h2_flux_residual_kg_s=float(np.max(np.abs(native_flux-.02))),
        mass_budget_kg_s=1e-6, accepted=True, centreline=centreline,
    )
    try:
        HyRAMJetRun(**jet_fields)
    except ValueError as exc:
        assert "checked native run path" in str(exc)
    else:
        raise AssertionError("A caller-fabricated HyRAM jet claimed native run provenance")
    jet = _issue_hyram_jet_run(**jet_fields)
    try:
        from dataclasses import replace

        replace(jet, gaussian_entry_h2_flow_kg_s=jet.gaussian_entry_h2_flow_kg_s+1e-6)
    except ValueError:
        pass
    else:
        raise AssertionError("Direct HyRAM receipt accepted a forged Gaussian-entry summary")
    try:
        replace(jet, accepted=False)
    except ValueError:
        pass
    else:
        raise AssertionError("Direct HyRAM receipt accepted a forged acceptance flag")
    try:
        jet.centreline.setflags(write=True)
    except ValueError:
        pass
    else:
        raise AssertionError("Captured HyRAM centreline can be made writable")
    projected = project_hyram_jet_to_finite_source(
        jet, start_s=5., end_s=15., clock_id="plant-clock", source_state=upstream,
        source_state_evidence_id="source-state-fixture", origin=Origin.PREDICTED,
        end_reason="isolation",
    )
    projected.require_current()
    assert projected.source.total_mass_kg == .2
    assert projected.source.mean_rates_kg_s[0] == jet.mass_flow_kg_s
    assert projected.enthalpy_rate_residual_w == 0.
    original_energy_budget = projected.enthalpy_budget_w
    object.__setattr__(projected, "enthalpy_budget_w", original_energy_budget * 2.)
    try:
        projected.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("HyRAM projection accepted a modified enthalpy budget receipt")
    finally:
        object.__setattr__(projected, "enthalpy_budget_w", original_energy_budget)
    assert projected.require_current() is projected

    from h2physics.mixtures import GasComposition

    mixture = GasComposition(
        "declared-air-dilution", ("H2", "N2"), np.array([0.2, 0.8]),
        np.array([2.01588e-3, 28.0134e-3]),
    )
    mixture_flow = projected.component_flow(mixture)
    mixture_flow.require_current()
    from dataclasses import replace

    retained_budget = projected.enthalpy_budget_w
    object.__setattr__(projected, "enthalpy_budget_w", retained_budget + 1.0)
    try:
        try:
            replace(mixture_flow, projection=projected)
        except ValueError:
            pass
        else:
            raise AssertionError("Component-flow constructor accepted a stale parent projection")
    finally:
        object.__setattr__(projected, "enthalpy_budget_w", retained_budget)
    assert np.isclose(
        mixture_flow.component_mass_rates_kg_s[0], jet.mass_flow_kg_s,
        rtol=1e-12, atol=1e-14,
    )
    assert np.isclose(
        mixture_flow.component_mass_rates_kg_s.sum(),
        mixture_flow.total_mixture_rate_kg_s, rtol=1e-12, atol=1e-14,
    )
    try:
        mixture_flow.component_mass_rates_kg_s.setflags(write=True)
        mixture_flow.component_mass_rates_kg_s[0] *= 0.9
        mixture_flow.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Mutated component flow allocation remained current")

    changed_enthalpy_state = ThermoState(
        basis, upstream.pressure_pa, upstream.temperature_k, upstream.density_kg_m3,
        upstream.enthalpy_j_kg+1.e5, upstream.internal_energy_j_kg,
        upstream.entropy_j_kg_k, upstream.phase,
    )
    diagnostic = project_hyram_jet_to_finite_source(
        jet, start_s=5., end_s=15., clock_id="plant-clock", source_state=changed_enthalpy_state,
        source_state_evidence_id="alternate-state-fixture", origin=Origin.PREDICTED,
        require_accepted=False,
    )
    assert not diagnostic.accepted and diagnostic.enthalpy_rate_residual_w == 2000.
    try:
        project_hyram_jet_to_finite_source(
            jet, start_s=5., end_s=15., clock_id="plant-clock", source_state=changed_enthalpy_state,
            source_state_evidence_id="alternate-state-fixture", origin=Origin.PREDICTED,
        )
    except HyRAMFiniteSourceError as exc:
        assert exc.projection.enthalpy_rate_residual_w == diagnostic.enthalpy_rate_residual_w
    else:
        raise AssertionError("Energy-incompatible state was accepted")

    native_flow_bound = project_hyram_jet_to_finite_source(
        jet, start_s=5., end_s=15., clock_id="plant-clock", source_state=upstream,
        source_state_evidence_id="source-state-fixture", origin=Origin.PREDICTED,
    )
    original_native_flow = native.mass_flow_rate
    native.mass_flow_rate = original_native_flow * 1.01
    try:
        native_flow_bound.require_current()
    except ValueError as exc:
        assert "native output" in str(exc)
    else:
        raise AssertionError("Mutated native HyRAM flow retained its old admission gate")
    finally:
        native.mass_flow_rate = original_native_flow

    native.S[1] = 1.1
    try:
        projected.require_current()
    except ValueError as exc:
        assert "centreline changed" in str(exc)
    else:
        raise AssertionError("Mutated native centreline remained current")

    return ValidationOutcome(
        True,
        {
            "window_mass_kg": projected.source.total_mass_kg,
            "rate_kg_s": jet.mass_flow_kg_s,
            "matched_energy_residual_w": projected.enthalpy_rate_residual_w,
            "alternate_energy_residual_w": diagnostic.enthalpy_rate_residual_w,
        },
        (
            "This is a synthetic API contract, not a HyRAM model run or measured validation.",
            "Finite duration is caller selected; the steady native jet does not predict source history.",
            "The projection does not correct a rejected HyRAM Gaussian-entry mass mismatch.",
        ),
    )
