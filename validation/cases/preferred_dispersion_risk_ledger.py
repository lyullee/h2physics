"""Synthetic source-rate lineage contract for preferred gas dispersion risk."""

from hashlib import sha256
from types import SimpleNamespace

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.core import Origin


class _SyntheticRiskBinding:
    """Structural fixture; it does not represent the optional native engine."""

    def __init__(self, release_rate_kg_s):
        self.release_rate_kg_s = release_rate_kg_s
        self.lineage_sha256 = sha256(repr(release_rate_kg_s).encode()).hexdigest()
        self.origin = Origin.SYNTHETIC
        self.frequency = object()
        self.request = SimpleNamespace(frequency=self.frequency, branches=())
        self._seal = (self.release_rate_kg_s, self.lineage_sha256, self.origin,
                      id(self.frequency), id(self.request))

    def require_current(self):
        if (self.release_rate_kg_s, self.lineage_sha256, self.origin,
                id(self.frequency), id(self.request)) != self._seal:
            raise ValueError("Synthetic risk receipt changed")
        return self


def cases():
    return (ValidationCase(
        identifier="preferred-gas-dispersion-hyram-ignition-risk-ledger",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_ledger",
        parameters={},
        invariants=(
            "accepted HyRAM finite-source projection and preferred dispersion result are retained by identity",
            "HyRAM ignition-risk branches link only when their release rate matches the exact accepted jet rate",
            "the risk protocol fixture retains its frequency object identity",
            "mismatched ignition-rate evidence is rejected",
            "synthetic contract path does not load or exercise an external risk engine",
        ),
    ),)


def validate_ledger(*, work_directory, **parameters):
    del work_directory, parameters
    from unittest.mock import patch

    from examples.facility_protection import make_case
    from h2physics.adapters.facility_accident_chain import FacilityDispersionHandoff
    from h2physics.adapters.hyram import _issue_hyram_jet_run
    from h2physics.adapters.hyram_jet_source import project_hyram_jet_to_finite_source
    from h2physics.adapters.preferred_dispersion_risk_ledger import (
        bind_preferred_dispersion_risk_ledger,
    )
    from h2physics.core import PropertyBasis, ThermoState
    from h2physics.dispersion import DispersionScenario, HydrogenReleaseFamily
    from h2physics.release import NozzleOpening

    finite_source = make_case()["source"]
    source = finite_source.source
    gas_state = ThermoState(
        source.state.basis, source.state.pressure_pa, source.state.temperature_k,
        source.state.density_kg_m3, source.state.enthalpy_j_kg,
        source.state.internal_energy_j_kg, source.state.entropy_j_kg_k, "gas",
    )
    ambient = ThermoState(
        PropertyBasis("Air", "synthetic-risk-link"), 101325., 298., 1.2,
        3.e5, 2.14e5, 6.8e3, "gas",
    )
    start, end = float(source.edges_s[0]), float(source.edges_s[-1])
    rate = float(source.total_mass_kg / (end - start))
    native_jet = SimpleNamespace(
        S=np.array([0., 1.]), x=np.array([0., 1.]), y=np.array([0., 0.]),
        Y_cl=np.array([1., .5]), X_cl=np.array([1., .4]),
        rho_cl=np.ones(2), V_cl=np.array([2*rate/np.pi, 4*rate/np.pi]),
        B=np.ones(2), lam=1., mass_flow_rate=rate,
    )
    centreline = np.c_[native_jet.S, native_jet.x, native_jet.y,
                       native_jet.Y_cl, native_jet.X_cl]
    flux = np.pi*native_jet.rho_cl*native_jet.Y_cl*native_jet.V_cl*native_jet.B**2/2.
    jet = _issue_hyram_jet_run(
        native=native_jet, upstream=gas_state, ambient=ambient,
        opening=NozzleOpening.circular("synthetic-gas-opening", .01,
                                       effective_area_factor=1., area_basis_id="fixture"),
        location=source.location, evidence_id="synthetic-hyram-jet",
        mass_flow_kg_s=rate, gaussian_entry_h2_flow_kg_s=float(flux[0]),
        maximum_transport_h2_residual_kg_s=float(np.max(np.abs(flux-flux[0]))),
        maximum_h2_flux_residual_kg_s=float(np.max(np.abs(flux-rate))),
        mass_budget_kg_s=1e-9, accepted=True, centreline=centreline,
    )
    projection = project_hyram_jet_to_finite_source(
        jet, start_s=start, end_s=end, clock_id=source.location.clock_id,
        source_state=gas_state, source_state_evidence_id="synthetic-gas-source-state",
        origin=source.origin, relative_enthalpy_tolerance=1e-8,
        absolute_enthalpy_tolerance_w=1e-4,
    )
    request = DispersionScenario(HydrogenReleaseFamily.HIGH_PRESSURE_GAS, {
        "fluid_factory": lambda *args, **kwargs: None,
        "orifice_factory": lambda *args, **kwargs: None,
        "jet_factory": lambda *args, **kwargs: None,
        "upstream": gas_state,
        "ambient": ambient,
        "opening": jet.opening,
        "location": source.location,
        "evidence_id": jet.evidence_id,
    })
    with patch("h2physics.dispersion.run_preferred_gas_dispersion", return_value=jet):
        execution = request.run()
    budget = float(np.max(np.abs(source.mass_kg - np.diff(source.edges_s)*rate)) + 1e-9)
    handoff = FacilityDispersionHandoff(
        finite_source, execution, projection, "synthetic-facility-link-evidence",
        HydrogenReleaseFamily.HIGH_PRESSURE_GAS, budget, 1e30,
    )

    risk_binding = _SyntheticRiskBinding(rate)
    ledger = bind_preferred_dispersion_risk_ledger(
        handoff, risk_binding, linkage_evidence_id="synthetic-source-risk-lineage",
        release_rate_absolute_tolerance_kg_s=0.0,
    )
    assert ledger.require_current() is ledger
    assert ledger.facility_handoff is handoff and ledger.ignition_risk is risk_binding
    assert ledger.ignition_risk.request.frequency is risk_binding.frequency

    wrong_risk = _SyntheticRiskBinding(rate + max(rate, 1.0))
    try:
        bind_preferred_dispersion_risk_ledger(
            handoff, wrong_risk, linkage_evidence_id="synthetic-rate-mismatch",
            release_rate_absolute_tolerance_kg_s=0.0,
        )
    except ValueError as error:
        assert "exact admitted HyRAM jet rate" in str(error)
        mismatch_rejected = True
    else:
        raise AssertionError("A rate-mismatched ignition ledger was accepted")
    return ValidationOutcome(True, {
        "ledger_current": ledger.require_current() is ledger,
        "frequency_identity_preserved": ledger.ignition_risk.request.frequency is risk_binding.frequency,
        "mismatched_rate_rejected": mismatch_rejected,
        "external_risk_engine_exercised": False,
    }, (
        "Synthetic provider and structural risk-interface receipts; no native risk package was imported",
        "HyRAM ignition-table applicability, branch construction and receptor harm remain caller-owned",
    ))
