"""Deferred contracts for the non-isothermal caloric gas-pipe wave solver."""


def cases():
    from h2physics.cluster_validation import ValidationCase

    return (
        ValidationCase(
            identifier="hydrogen-pipeline-caloric-euler-closed-wave-ledgers",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_closed_wave_and_energy_ledgers",
            invariants=(
                "uniform-resting-single-phase-state-is-preserved-by-closed-reflective-walls",
                "a-small-velocity-disturbance-produces-a-resolved-nonisothermal-pressure-wave",
                "first-order-rusanov-substeps-remain-within-the-declared-caloric-euler-cfl-limit",
                "closed-wall-mass-and-total-energy-ledgers-close-without-clipping-or-phase-fallback",
                "the-model-uses-mass-momentum-and-total-energy-and-is-distinct-from-fixed-temperature-pipe-waves",
                "trace-eos-identity-fingerprints-exposed-configuration-and-unidentified-provider-is-rejected",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-caloric-euler-reservoir-boundary",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_reservoir_boundary_contract",
            invariants=(
                "fixed-caller-reservoir-ghost-state-is-basis-clock-and-evidence-bound",
                "open-boundary-mass-and-energy-ledgers-use-the-exact-face-flux-applied-to-the-pipe",
                "network-mass-and-total-energy-residuals-close-against-signed-boundary-transfer",
                "wrong-clock-or-two-phase-boundary-state-is-rejected-before-advancement",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-caloric-euler-eos-provenance",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_eos_provenance_contract",
            invariants=(
                "configuration-fingerprint-changes-when-property-provider-configuration-changes",
                "provider-without-caller-identity-or-exposed-configuration-is-rejected",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-pipeline-caloric-euler-source-ledgers",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_source_term_ledgers",
            invariants=(
                "Darcy-factor-momentum-source-does-not-book-stationary-wall-friction-as-external-energy-loss",
                "fixed-wall-heat-sign-is-positive-into-gas-and-cumulative-heat-closes-total-energy-ledger",
                "source-factor-diagnostics-are-output-interval-bounded-and-retain-provider-evidence-and-scheme",
                "negative-factor-and-source-clock-mismatch-are-rejected",
            ),
        ),
    )


class _SyntheticCaloricHydrogen:
    """Authored calorically-perfect gas closure for software contracts only."""

    def __init__(self):
        from h2physics.core import PropertyBasis

        self.basis = PropertyBasis("SyntheticHydrogen", "synthetic-caloric-reference-v1", "normal")
        self.identity = "synthetic-calorically-perfect-hydrogen-v1"
        self.gas_constant_j_kg_k = 4124.0
        self.cv_j_kg_k = 10188.0
        self.cp_j_kg_k = self.cv_j_kg_k + self.gas_constant_j_kg_k
        self.configuration = {
            "gas_constant_j_kg_k": self.gas_constant_j_kg_k,
            "cv_j_kg_k": self.cv_j_kg_k,
        }

    def _state(self, density, internal_energy):
        import math
        from h2physics.core import ThermoState

        temperature = internal_energy / self.cv_j_kg_k
        pressure = density * self.gas_constant_j_kg_k * temperature
        entropy = self.cv_j_kg_k * math.log(temperature / 300.) - self.gas_constant_j_kg_k * math.log(density / 1.)
        sound = math.sqrt((self.cp_j_kg_k / self.cv_j_kg_k) * self.gas_constant_j_kg_k * temperature)
        return ThermoState(
            self.basis, pressure, temperature, density, internal_energy + pressure / density,
            internal_energy, entropy, "gas", self.cp_j_kg_k, self.cv_j_kg_k,
            speed_of_sound_m_s=sound,
        )

    def state_pt(self, pressure_pa, temperature_k):
        rho = pressure_pa / (self.gas_constant_j_kg_k * temperature_k)
        return self._state(rho, self.cv_j_kg_k * temperature_k)

    def state_rho_u(self, density_kg_m3, internal_energy_j_kg):
        return self._state(density_kg_m3, internal_energy_j_kg)


def validate_closed_wave_and_energy_ledgers(*, work_directory, **parameters):
    from dataclasses import replace

    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.caloric_pipe_waves import CaloricPipeWaveModel

    del work_directory, parameters
    eos = _SyntheticCaloricHydrogen()
    count = 32
    pressure = np.full(count, 8.0e6)
    temperature = np.full(count, 300.0)
    velocity = np.zeros(count)
    model = CaloricPipeWaveModel(
        length_m=30., internal_diameter_m=.05, cell_count=count, eos=eos, maximum_cfl=.30,
    )
    altered_eos = _SyntheticCaloricHydrogen()
    altered_eos.configuration = dict(altered_eos.configuration, cv_j_kg_k=altered_eos.cv_j_kg_k + 1.)
    altered_model = CaloricPipeWaveModel(
        length_m=30., internal_diameter_m=.05, cell_count=count, eos=altered_eos, maximum_cfl=.30,
    )
    if model.eos_identity == altered_model.eos_identity:
        raise AssertionError("EOS identity did not change when provider configuration changed")

    class _UnidentifiedClosure(_SyntheticCaloricHydrogen):
        identity = None

        def __init__(self):
            super().__init__()
            del self.configuration

    try:
        CaloricPipeWaveModel(
            length_m=30., internal_diameter_m=.05, cell_count=count,
            eos=_UnidentifiedClosure(), maximum_cfl=.30,
        )
    except ValueError as error:
        if "stable identity" not in str(error):
            raise AssertionError("Unidentified EOS was rejected for an unrelated reason") from error
    else:
        raise AssertionError("EOS without identity or configuration was accepted")
    equilibrium = model.simulate(
        initial_pressure_pa=pressure, initial_temperature_k=temperature,
        initial_velocity_m_s=velocity, time_samples_s=(0., .002, .005),
        clock_id="synthetic-closed-pipe-clock-v1",
    )
    if (equilibrium.pipe_length_m != model.length_m
            or equilibrium.internal_diameter_m != model.internal_diameter_m
            or not np.isclose(equilibrium.area_m2, model.area_m2, rtol=0., atol=1.e-15)
            or equilibrium.clock_id != "synthetic-closed-pipe-clock-v1"):
        raise AssertionError("Closed-wall trace lost pipe geometry or clock identity")
    if (not np.allclose(equilibrium.pressure_pa, pressure[None, :], rtol=0., atol=1.e-6)
            or not np.allclose(equilibrium.temperature_k, temperature[None, :], rtol=0., atol=1.e-12)):
        raise AssertionError("Uniform rest state drifted in a closed pipe")
    if (np.max(np.abs(equilibrium.mass_balance_residual_kg)) > 1.e-12
            or np.max(np.abs(equilibrium.energy_balance_residual_j)) > 1.e-7):
        raise AssertionError("Closed-wall uniform state failed its conservation ledgers")
    centers = equilibrium.cell_center_m
    pulse = 15.0 * np.exp(-((centers - 10.) / 3.) ** 2)
    wave = model.simulate(
        initial_pressure_pa=pressure, initial_temperature_k=temperature,
        initial_velocity_m_s=pulse, time_samples_s=(0., .002, .005),
        clock_id="synthetic-closed-pipe-clock-v1",
    )
    if np.max(np.abs(wave.pressure_pa[-1] - wave.pressure_pa[0])) < 1.:
        raise AssertionError("Caloric Euler velocity disturbance did not produce a pressure wave")
    if (np.max(np.abs(wave.mass_balance_residual_kg)) > 1.e-10
            or np.max(np.abs(wave.energy_balance_residual_j)) > 1.e-6):
        raise AssertionError("Closed-wall Euler update failed mass or total-energy conservation")
    if not 0. < wave.maximum_cfl <= wave.cfl_limit <= .5:
        raise AssertionError("Observed CFL is outside the admitted explicit-scheme range")
    if np.any(wave.density_kg_m3 <= 0.) or np.any(wave.temperature_k <= 0.):
        raise AssertionError("Caloric Euler trace left the positive single-phase state domain")
    try:
        replace(wave, maximum_cfl=0.)
    except ValueError as error:
        if "issued only" not in str(error):
            raise AssertionError("Trace replacement was rejected for an unrelated reason") from error
    else:
        raise AssertionError("A dataclass-replaced caloric trace retained run issuance")
    return ValidationOutcome(True, {
        "cell_count": count,
        "time_samples_s": wave.time_s.tolist(),
        "maximum_cfl": wave.maximum_cfl,
        "cfl_limit": wave.cfl_limit,
        "maximum_pressure_change_pa": float(np.max(np.abs(wave.pressure_pa[-1] - wave.pressure_pa[0]))),
        "maximum_mass_residual_kg": float(np.max(np.abs(wave.mass_balance_residual_kg))),
        "maximum_energy_residual_j": float(np.max(np.abs(wave.energy_balance_residual_j))),
    }, ("Synthetic calorically-perfect gas contract only; no hydrogen EOS or measured-pipe validation.",))


def validate_reservoir_boundary_contract(*, work_directory, **parameters):
    import numpy as np
    from dataclasses import replace

    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.caloric_pipe_waves import CaloricPipeReservoirBoundary, CaloricPipeWaveModel

    del work_directory, parameters
    eos = _SyntheticCaloricHydrogen()
    count = 20
    pressure = [8.0e6] * count
    temperature = [300.] * count
    velocity = [0.] * count
    boundary = CaloricPipeReservoirBoundary(
        "synthetic-low-pressure-boundary", "synthetic-reservoir-owner",
        "synthetic-reservoir-state-evidence", "synthetic-caloric-clock-v1",
        eos.state_pt(6.0e6, 295.), 0.,
    )
    model = CaloricPipeWaveModel(
        length_m=20., internal_diameter_m=.05, cell_count=count, eos=eos, maximum_cfl=.25,
    )
    trace = model.simulate(
        initial_pressure_pa=pressure, initial_temperature_k=temperature,
        initial_velocity_m_s=velocity, time_samples_s=(0., .002, .005),
        clock_id="synthetic-caloric-clock-v1", left_reservoir=boundary,
    )
    if (trace.left_boundary_id != boundary.identifier
            or trace.left_boundary_state_owner_id != boundary.state_owner_id
            or trace.left_boundary_state_evidence_id != boundary.state_evidence_id
            or trace.clock_id != boundary.clock_id
            or trace.pipe_length_m != model.length_m
            or trace.internal_diameter_m != model.internal_diameter_m
            or not np.isclose(trace.area_m2, model.area_m2, rtol=0., atol=1.e-15)):
        raise AssertionError("Trace lost geometry, clock, or reservoir boundary identities")
    if abs(trace.cumulative_boundary_mass_in_kg[-1]) <= 0.:
        raise AssertionError("Pressure mismatch did not create a boundary mass exchange")
    if (np.max(np.abs(trace.mass_balance_residual_kg)) > 1.e-10
            or np.max(np.abs(trace.energy_balance_residual_j)) > 1.e-5):
        raise AssertionError("Open boundary mass/energy ledger did not close")
    bad_clock = replace(boundary, clock_id="different-clock")
    try:
        model.simulate(
            initial_pressure_pa=pressure, initial_temperature_k=temperature,
            initial_velocity_m_s=velocity, time_samples_s=(0., .001),
            clock_id="synthetic-caloric-clock-v1", left_reservoir=bad_clock,
        )
    except ValueError as error:
        if "clock" not in str(error).lower():
            raise AssertionError("Wrong clock was rejected for an unrelated reason") from error
    else:
        raise AssertionError("Mismatched reservoir clock was accepted")
    try:
        CaloricPipeReservoirBoundary(
            "synthetic-two-phase-boundary", "synthetic-reservoir-owner",
            "synthetic-reservoir-state-evidence", "synthetic-caloric-clock-v1",
            replace(boundary.state, phase="two_phase"), 0.,
        )
    except ValueError as error:
        if "single-phase" not in str(error):
            raise AssertionError("Two-phase boundary state was rejected for an unrelated reason") from error
    else:
        raise AssertionError("Two-phase reservoir ghost state was accepted by the gas-only solver")
    return ValidationOutcome(True, {
        "boundary_id": boundary.identifier,
        "clock_id": trace.clock_id,
        "pipe_length_m": trace.pipe_length_m,
        "internal_diameter_m": trace.internal_diameter_m,
        "area_m2": trace.area_m2,
        "net_boundary_mass_kg": float(trace.cumulative_boundary_mass_in_kg[-1]),
        "net_boundary_energy_j": float(trace.cumulative_boundary_energy_in_j[-1]),
        "maximum_mass_residual_kg": float(np.max(np.abs(trace.mass_balance_residual_kg))),
        "maximum_energy_residual_j": float(np.max(np.abs(trace.energy_balance_residual_j))),
    }, ("Synthetic prescribed-state boundary contract; reservoir inventory is not depleted.",))


def validate_eos_provenance_contract(*, work_directory, **parameters):
    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.caloric_pipe_waves import CaloricPipeWaveModel

    del work_directory, parameters
    eos = _SyntheticCaloricHydrogen()
    model = CaloricPipeWaveModel(
        length_m=10., internal_diameter_m=.05, cell_count=4, eos=eos,
    )
    changed = _SyntheticCaloricHydrogen()
    changed.configuration = dict(changed.configuration, cv_j_kg_k=changed.cv_j_kg_k + 1.)
    changed_model = CaloricPipeWaveModel(
        length_m=10., internal_diameter_m=.05, cell_count=4, eos=changed,
    )
    if model.eos_identity == changed_model.eos_identity:
        raise AssertionError("EOS identity did not change with exposed provider configuration")

    class _UnidentifiedClosure(_SyntheticCaloricHydrogen):
        identity = None

        def __init__(self):
            super().__init__()
            del self.configuration

    try:
        CaloricPipeWaveModel(
            length_m=10., internal_diameter_m=.05, cell_count=4,
            eos=_UnidentifiedClosure(),
        )
    except ValueError as error:
        if "stable identity" not in str(error):
            raise AssertionError("Unidentified closure was rejected for an unrelated reason") from error
    else:
        raise AssertionError("EOS without caller identity or configuration was accepted")
    return ValidationOutcome(True, {
        "original_eos_identity": model.eos_identity,
        "changed_eos_identity": changed_model.eos_identity,
        "configuration_fingerprint_changed": True,
        "unidentified_provider_rejected": True,
    }, ("Synthetic provider identity contract only; no hydrogen EOS qualification.",))


def validate_source_term_ledgers(*, work_directory, **parameters):
    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.caloric_pipe_waves import (
        CaloricPipeWallHeatBoundary,
        CaloricPipeWaveModel,
        UniformDarcyFriction,
    )

    del work_directory, parameters
    eos = _SyntheticCaloricHydrogen()
    count = 12
    model = CaloricPipeWaveModel(
        length_m=12., internal_diameter_m=.08, cell_count=count, eos=eos,
        maximum_cfl=.25,
    )
    common = dict(
        initial_pressure_pa=np.full(count, 4.0e6),
        initial_temperature_k=np.full(count, 300.),
        initial_velocity_m_s=np.full(count, 20.),
        time_samples_s=(0., .002, .004),
        clock_id="synthetic-source-ledger-clock-v1",
    )
    friction = UniformDarcyFriction(
        .02, "synthetic-uniform-darcy-factor", "synthetic-friction-owner",
        "synthetic-friction-evidence", common["clock_id"],
    )
    friction_trace = model.simulate(**common, darcy_friction_law=friction)
    if (friction_trace.friction_law_id != friction.identity
            or friction_trace.friction_state_owner_id != friction.state_owner_id
            or friction_trace.friction_evidence_id != friction.evidence_id
            or friction_trace.friction_scheme is None
            or friction_trace.darcy_factor_mean_by_interval.shape != (2, count)
            or friction_trace.darcy_factor_max_by_interval.shape != (2, count)
            or friction_trace.internal_steps_by_interval.shape != (2,)):
        raise AssertionError("Friction trace lost source provenance or bounded output diagnostics")
    if (not np.allclose(friction_trace.total_energy_j, friction_trace.total_energy_j[0],
                        rtol=0., atol=1.e-6)
            or np.max(np.abs(friction_trace.energy_balance_residual_j)) > 1.e-6):
        raise AssertionError("Stationary-wall Darcy friction was incorrectly counted as external energy loss")
    wall = CaloricPipeWallHeatBoundary(
        "synthetic-hot-fixed-wall", "synthetic-wall-owner", "synthetic-wall-evidence",
        common["clock_id"], 320., 2.0,
    )
    heated = model.simulate(**common, wall_heat_boundary=wall)
    expected_delta = heated.cumulative_wall_heat_in_j
    if (np.any(expected_delta[1:] <= 0.)
            or not np.allclose(heated.total_energy_j - heated.total_energy_j[0], expected_delta,
                               rtol=2.e-11, atol=1.e-7)
            or np.max(np.abs(heated.energy_balance_residual_j)) > 1.e-6
            or heated.wall_heat_boundary_id != wall.identifier
            or heated.wall_heat_state_owner_id != wall.state_owner_id
            or heated.wall_heat_evidence_id != wall.state_evidence_id):
        raise AssertionError("Fixed-wall heat sign, provenance, or exact energy ledger failed")
    try:
        UniformDarcyFriction(-.01, "invalid", "owner", "evidence", common["clock_id"])
    except ValueError:
        pass
    else:
        raise AssertionError("Negative Darcy factor was accepted")
    wrong_clock = UniformDarcyFriction(
        .02, "synthetic-wrong-clock-factor", "synthetic-friction-owner",
        "synthetic-friction-evidence", "different-clock",
    )
    try:
        model.simulate(**common, darcy_friction_law=wrong_clock)
    except ValueError as error:
        if "clock" not in str(error).lower():
            raise AssertionError("Wrong source clock was rejected for an unrelated reason") from error
    else:
        raise AssertionError("Mismatched friction clock was accepted")
    return ValidationOutcome(True, {
        "friction_law_id": friction_trace.friction_law_id,
        "friction_internal_steps_by_interval": friction_trace.internal_steps_by_interval.tolist(),
        "wall_heat_boundary_id": heated.wall_heat_boundary_id,
        "cumulative_wall_heat_in_j": heated.cumulative_wall_heat_in_j.tolist(),
        "maximum_friction_energy_residual_j": float(np.max(np.abs(friction_trace.energy_balance_residual_j))),
        "maximum_wall_heat_energy_residual_j": float(np.max(np.abs(heated.energy_balance_residual_j))),
    }, ("Synthetic calorically-perfect gas source-term contracts only; no measured-pipe validation.",))
