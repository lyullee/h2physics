"""Deferred synthetic contracts for finite pipe-end inventory state."""


def cases():
    from h2physics.cluster_validation import ValidationCase

    return (
        ValidationCase(
            identifier="hydrogen-pipeline-finite-isothermal-reservoir-eos-and-mass-step",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_inventory_step",
            invariants=(
                "fixed-volume-mass-pressure-state-closes-through-declared-single-phase-EOS",
                "positive-Rusanov-pipe-outward-flux-depletes-reservoir-by-exact-integrated-mass",
                "reservoir-owner-evidence-clock-EOS-temperature-volume-and-origin-are-retained",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-finite-isothermal-reservoir-rejection-contracts",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_rejections",
            invariants=(
                "wrong-EOS-identity-and-depleted-or-out-of-domain-mass-are-rejected",
                "mass-step-crossing-the-explicit-reservoir-floor-or-ceiling-is-rejected-without-clipping",
                "sonic-or-supersonic-endpoint-flow-is-rejected",
            ),
        ),
    )


def _fixture():
    from h2physics.core import Origin
    from h2physics.finite_pipe_reservoir import FiniteIsothermalPipeReservoir
    from h2physics.isothermal_pipe_waves import IdealHydrogenIsothermalEOS

    eos = IdealHydrogenIsothermalEOS()
    reservoir = FiniteIsothermalPipeReservoir(
        identifier="synthetic-inventory-vessel",
        node_id="synthetic-network-terminal",
        state_owner_id="authored-test-owner",
        state_evidence_id="synthetic-initial-inventory-record",
        clock_id="synthetic-inventory-clock",
        eos_identity=eos.identity,
        temperature_k=300.,
        volume_m3=1.25,
        mass_kg=2.0,
        minimum_mass_kg=.1,
        maximum_mass_kg=3.0,
        origin=Origin.SYNTHETIC,
    )
    return reservoir, eos


def validate_inventory_step(*, work_directory, **parameters):
    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    reservoir, eos = _fixture()
    pressure = reservoir.pressure_at_mass(reservoir.mass_kg, eos)
    final_mass, residual = reservoir.advance(
        current_mass_kg=reservoir.mass_kg,
        pipe_outward_mass_flow_kg_s=.4,
        duration_s=.5,
    )
    final_pressure = reservoir.pressure_at_mass(final_mass, eos)
    assert final_mass == 1.8
    assert abs(residual) < 1.e-12
    assert final_pressure < pressure
    assert reservoir.identifier == "synthetic-inventory-vessel"
    return ValidationOutcome(True, {
        "reservoir_id": reservoir.identifier,
        "node_id": reservoir.node_id,
        "state_owner_id": reservoir.state_owner_id,
        "state_evidence_id": reservoir.state_evidence_id,
        "clock_id": reservoir.clock_id,
        "eos_identity": eos.identity,
        "initial_mass_kg": reservoir.mass_kg,
        "final_mass_kg": final_mass,
        "initial_pressure_pa": pressure,
        "final_pressure_pa": final_pressure,
        "signed_mass_residual_kg": residual,
        "origin": str(reservoir.origin),
    }, ("Synthetic fixed-volume inventory contract only; not a vessel validation.",))


def validate_rejections(*, work_directory, **parameters):
    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    reservoir, eos = _fixture()
    rejected = {}
    class WrongEOSIdentity:
        identity = "deliberately-wrong-eos-identity"

        def density_pt(self, p_pa, t_k):
            return eos.density_pt(p_pa, t_k)

        def pressure_rho_t(self, rho_kg_m3, t_k):
            return eos.pressure_rho_t(rho_kg_m3, t_k)

        def isothermal_sound_speed_rho_t(self, rho_kg_m3, t_k):
            return eos.isothermal_sound_speed_rho_t(rho_kg_m3, t_k)

    try:
        reservoir.pressure_at_mass(1.0, WrongEOSIdentity())
    except ValueError:
        rejected["wrong_eos"] = True
    else:
        raise AssertionError("Mismatched EOS identity was accepted")
    try:
        reservoir.pressure_at_mass(0.0, eos)
    except ValueError:
        rejected["nonpositive_mass_domain"] = True
    else:
        raise AssertionError("Nonpositive reservoir mass was accepted")
    for label, kwargs in (
        ("depletion", {"pipe_outward_mass_flow_kg_s": 5., "duration_s": 1.}),
        ("ceiling", {"pipe_outward_mass_flow_kg_s": -2., "duration_s": 1.}),
    ):
        try:
            reservoir.advance(current_mass_kg=reservoir.mass_kg, **kwargs)
        except ValueError:
            rejected[label] = True
        else:
            raise AssertionError(f"Reservoir {label} step was accepted")
    try:
        reservoir.require_subsonic(
            mass_kg=reservoir.mass_kg,
            outward_mass_flow_kg_s=1.e6,
            endpoint_area_m2=.01,
            eos=eos,
        )
    except ValueError as error:
        if "supersonic" not in str(error):
            raise AssertionError("Fast endpoint state failed for an unrelated reason") from error
        rejected["supersonic"] = True
    else:
        raise AssertionError("Supersonic reservoir endpoint state was accepted")
    assert set(rejected) == {"wrong_eos", "nonpositive_mass_domain", "depletion",
                            "ceiling", "supersonic"}
    return ValidationOutcome(True, {
        "rejected_contracts": rejected,
        "reservoir_id": reservoir.identifier,
        "node_id": reservoir.node_id,
        "clock_id": reservoir.clock_id,
        "eos_identity": eos.identity,
    }, ("Synthetic rejection contract only; no flow is silently clipped.",))
