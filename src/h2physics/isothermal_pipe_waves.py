"""Finite-volume pressure waves in a closed, isothermal hydrogen pipe segment.

This deliberately narrow solver uses the one-dimensional isothermal Euler
equations with a pluggable single-phase EOS and Darcy-Weisbach wall momentum loss. It adds
line momentum storage and acoustic propagation; it does not replace the
repository's quasi-steady Darcy links or inventory linepack models.

Governing-equation provenance: M. Gugat, R. Krug and A. Martin, “Transient
gas pipeline flow: analytical examples, numerical simulation and a comparison
to the quasi-static approach,” Optimization and Engineering 24 (2023),
https://doi.org/10.1007/s11081-021-09690-4. The implementation below is an
independent finite-volume formulation, not copied source code.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from .core import finite, immutable_array
from .pipe_reservoir_boundary import FiniteReservoirPressureBoundary
from .thermo.isothermal_eos import CoolPropIsothermalEOS, IsothermalSinglePhaseEOS

_R_UNIVERSAL_J_MOL_K = 8.31446261815324


@dataclass(frozen=True, slots=True)
class IsothermalPipeWaveTrace:
    """Immutable sampled pipe states, signed boundary flows and mass ledgers."""

    time_s: np.ndarray = field(repr=False, compare=False)
    cell_center_m: np.ndarray = field(repr=False, compare=False)
    pressure_pa: np.ndarray = field(repr=False, compare=False)
    velocity_m_s: np.ndarray = field(repr=False, compare=False)
    density_kg_m3: np.ndarray = field(repr=False, compare=False)
    face_mass_flow_kg_s: np.ndarray = field(repr=False, compare=False)
    total_mass_kg: np.ndarray = field(repr=False, compare=False)
    mass_balance_residual_kg: np.ndarray = field(repr=False, compare=False)
    isothermal_sound_speed_m_s: np.ndarray = field(repr=False, compare=False)
    eos_closure_id: str
    maximum_cfl: float
    cfl_limit: float
    darcy_friction_factor: float
    temperature_k: float
    boundary_mass_in_kg: np.ndarray | None = field(default=None, repr=False, compare=False)
    boundary_mass_out_kg: np.ndarray | None = field(default=None, repr=False, compare=False)
    left_reservoir_pressure_pa: np.ndarray | None = field(default=None, repr=False, compare=False)
    right_reservoir_pressure_pa: np.ndarray | None = field(default=None, repr=False, compare=False)
    boundary_clock_id: str | None = None
    left_reservoir_id: str | None = None
    right_reservoir_id: str | None = None
    left_reservoir_state_owner_id: str | None = None
    right_reservoir_state_owner_id: str | None = None
    left_reservoir_state_evidence_id: str | None = None
    right_reservoir_state_evidence_id: str | None = None

    def __post_init__(self):
        time = immutable_array(self.time_s, dtype=float, name="time_s")
        centers = immutable_array(self.cell_center_m, dtype=float, name="cell_center_m")
        pressure = immutable_array(self.pressure_pa, dtype=float, name="pressure_pa")
        velocity = immutable_array(self.velocity_m_s, dtype=float, name="velocity_m_s")
        density = immutable_array(self.density_kg_m3, dtype=float, name="density_kg_m3")
        face_flow = immutable_array(self.face_mass_flow_kg_s, dtype=float,
                                    name="face_mass_flow_kg_s")
        total_mass = immutable_array(self.total_mass_kg, dtype=float, name="total_mass_kg")
        residual = immutable_array(self.mass_balance_residual_kg, dtype=float,
                                  name="mass_balance_residual_kg")
        sound_speed = immutable_array(self.isothermal_sound_speed_m_s, dtype=float,
                                      name="isothermal_sound_speed_m_s")
        if time.ndim != 1 or len(time) < 2 or np.any(np.diff(time) <= 0.):
            raise ValueError("Trace times must be a strictly increasing one-dimensional sequence")
        n_time, n_cells = len(time), len(centers)
        boundary_in = immutable_array(
            np.zeros(n_time) if self.boundary_mass_in_kg is None else self.boundary_mass_in_kg,
            dtype=float, name="boundary_mass_in_kg")
        boundary_out = immutable_array(
            np.zeros(n_time) if self.boundary_mass_out_kg is None else self.boundary_mass_out_kg,
            dtype=float, name="boundary_mass_out_kg")
        left_pressure = (None if self.left_reservoir_pressure_pa is None else
                         immutable_array(self.left_reservoir_pressure_pa, dtype=float,
                                         name="left_reservoir_pressure_pa"))
        right_pressure = (None if self.right_reservoir_pressure_pa is None else
                          immutable_array(self.right_reservoir_pressure_pa, dtype=float,
                                          name="right_reservoir_pressure_pa"))
        if (centers.ndim != 1 or n_cells < 2
                or pressure.shape != (n_time, n_cells)
                or velocity.shape != pressure.shape or density.shape != pressure.shape
                or sound_speed.shape != pressure.shape
                or face_flow.shape != (n_time, n_cells + 1)
                or total_mass.shape != (n_time,) or residual.shape != (n_time,)
                or boundary_in.shape != (n_time,) or boundary_out.shape != (n_time,)
                or (left_pressure is not None and left_pressure.shape != (n_time,))
                or (right_pressure is not None and right_pressure.shape != (n_time,))):
            raise ValueError("Trace arrays have incompatible time, cell, or face dimensions")
        if (not all(np.all(np.isfinite(x)) for x in
                    (time, centers, pressure, velocity, density, sound_speed, face_flow,
                     total_mass, residual, boundary_in, boundary_out))
                or (left_pressure is not None and not np.all(np.isfinite(left_pressure)))
                or (right_pressure is not None and not np.all(np.isfinite(right_pressure)))
                or np.any(pressure <= 0.) or np.any(density <= 0.)
                or np.any(sound_speed <= 0.)
                or np.any(boundary_in < 0.) or np.any(boundary_out < 0.)
                or (left_pressure is not None and np.any(left_pressure <= 0.))
                or (right_pressure is not None and np.any(right_pressure <= 0.))
                or np.any(total_mass <= 0.)):
            raise ValueError("Trace arrays must be finite and pressure, density, sound speed, and mass positive")
        cfl = finite(self.maximum_cfl, "maximum_cfl")
        cfl_limit = finite(self.cfl_limit, "cfl_limit", positive=True)
        if cfl < 0. or cfl > cfl_limit + 1e-14 or cfl_limit > 0.5:
            raise ValueError("Observed CFL must be within its limit, which cannot exceed 0.5")
        finite(self.darcy_friction_factor, "darcy_friction_factor")
        if self.darcy_friction_factor < 0.:
            raise ValueError("Darcy friction factor cannot be negative")
        if not isinstance(self.eos_closure_id, str) or not self.eos_closure_id.strip():
            raise ValueError("Trace eos_closure_id must identify its property closure")
        finite(self.temperature_k, "temperature_k", positive=True)
        open_ids = (self.left_reservoir_id, self.right_reservoir_id)
        open_owners = (self.left_reservoir_state_owner_id,
                       self.right_reservoir_state_owner_id)
        open_evidence = (self.left_reservoir_state_evidence_id,
                         self.right_reservoir_state_evidence_id)
        for identifier, owner, evidence, pressure_history in zip(
                open_ids, open_owners, open_evidence,
                (left_pressure, right_pressure), strict=True):
            if identifier is None:
                if owner is not None or evidence is not None or pressure_history is not None:
                    raise ValueError("Closed ends cannot retain partial reservoir ownership metadata")
            elif (not isinstance(identifier, str) or not identifier.strip()
                    or not isinstance(owner, str) or not owner.strip()
                    or not isinstance(evidence, str) or not evidence.strip()
                    or pressure_history is None):
                raise ValueError("Open-end trace must retain reservoir ID, owner, evidence and pressure history")
        if any(value is not None for value in open_ids):
            if not isinstance(self.boundary_clock_id, str) or not self.boundary_clock_id.strip():
                raise ValueError("Open reservoir trace must retain its declared clock")
        elif self.boundary_clock_id is not None:
            raise ValueError("Closed-end trace cannot declare a reservoir clock")
        for name, value in (("time_s", time), ("cell_center_m", centers),
                            ("pressure_pa", pressure), ("velocity_m_s", velocity),
                            ("density_kg_m3", density),
                            ("isothermal_sound_speed_m_s", sound_speed),
                            ("face_mass_flow_kg_s", face_flow),
                            ("total_mass_kg", total_mass),
                            ("mass_balance_residual_kg", residual)):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "boundary_mass_in_kg", boundary_in)
        object.__setattr__(self, "boundary_mass_out_kg", boundary_out)
        object.__setattr__(self, "left_reservoir_pressure_pa", left_pressure)
        object.__setattr__(self, "right_reservoir_pressure_pa", right_pressure)


@dataclass(frozen=True, slots=True)
class IdealHydrogenIsothermalEOS:
    """Explicit analytic reference for numerical verification, not fluid properties.

    Production models use CoolProp by default. Select this reference only when
    an ideal-gas benchmark is the intended mathematical problem.
    """

    molecular_mass_kg_mol: float = 0.00201588

    def __post_init__(self):
        finite(self.molecular_mass_kg_mol, "molecular_mass_kg_mol", positive=True)

    @property
    def identity(self) -> str:
        return f"ideal-hydrogen-isothermal-M{self.molecular_mass_kg_mol:.12g}-kgmol"

    @property
    def specific_gas_constant_j_kg_k(self) -> float:
        return _R_UNIVERSAL_J_MOL_K / self.molecular_mass_kg_mol

    def density_pt(self, p_pa: float, t_k: float) -> float:
        p = finite(p_pa, "p_pa", positive=True)
        t = finite(t_k, "t_k", positive=True)
        return p / (self.specific_gas_constant_j_kg_k * t)

    def pressure_rho_t(self, rho_kg_m3: float, t_k: float) -> float:
        rho = finite(rho_kg_m3, "rho_kg_m3", positive=True)
        t = finite(t_k, "t_k", positive=True)
        return rho * self.specific_gas_constant_j_kg_k * t

    def isothermal_sound_speed_rho_t(self, rho_kg_m3: float, t_k: float) -> float:
        finite(rho_kg_m3, "rho_kg_m3", positive=True)
        finite(t_k, "t_k", positive=True)
        return float(np.sqrt(self.specific_gas_constant_j_kg_k * t_k))


@dataclass(frozen=True, slots=True)
class IsothermalPipeWaveModel:
    """One horizontal, constant-area, closed-ended hydrogen pipe segment.

    Pressures are absolute Pa, temperature is K, length/diameter are m,
    velocity is m/s, and time is s. EOS is provided by the shared
    ``IsothermalSinglePhaseEOS`` API; the default is CoolProp HEOS hydrogen.
    Missing CoolProp or a rejected native state raises an error; no ideal-gas
    fallback is selected.
    The wall condition is impermeable at both ends. A constant caller-selected
    Darcy friction factor damps momentum.
    """

    length_m: float
    internal_diameter_m: float
    cell_count: int
    temperature_k: float
    darcy_friction_factor: float = 0.0
    maximum_cfl: float = 0.4
    maximum_internal_steps: int = 2_000_000
    eos: IsothermalSinglePhaseEOS = field(default_factory=CoolPropIsothermalEOS,
                                          repr=False, compare=False)

    def __post_init__(self):
        finite(self.length_m, "length_m", positive=True)
        finite(self.internal_diameter_m, "internal_diameter_m", positive=True)
        finite(self.temperature_k, "temperature_k", positive=True)
        finite(self.darcy_friction_factor, "darcy_friction_factor")
        if self.darcy_friction_factor < 0.:
            raise ValueError("darcy_friction_factor cannot be negative")
        if isinstance(self.cell_count, bool) or not isinstance(self.cell_count, int) or self.cell_count < 2:
            raise ValueError("cell_count must be an integer of at least two")
        cfl = finite(self.maximum_cfl, "maximum_cfl", positive=True)
        if cfl > 0.5:
            raise ValueError("maximum_cfl must not exceed 0.5 for this explicit update")
        if (isinstance(self.maximum_internal_steps, bool)
                or not isinstance(self.maximum_internal_steps, int)
                or self.maximum_internal_steps < 1):
            raise ValueError("maximum_internal_steps must be a positive integer")
        for method in ("density_pt", "pressure_rho_t", "isothermal_sound_speed_rho_t"):
            if not callable(getattr(self.eos, method, None)):
                raise TypeError(f"EOS closure must implement {method}(...)")
        identity = getattr(self.eos, "identity", None)
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("EOS closure must provide a stable nonempty identity")

    @property
    def cell_length_m(self) -> float:
        return self.length_m / self.cell_count

    @property
    def cross_section_area_m2(self) -> float:
        return float(np.pi * self.internal_diameter_m**2 / 4.)

    def simulate(self, *, initial_pressure_pa: Sequence[float],
                 initial_velocity_m_s: Sequence[float],
                 time_samples_s: Sequence[float],
                 left_reservoir: FiniteReservoirPressureBoundary | None = None,
                 right_reservoir: FiniteReservoirPressureBoundary | None = None,
                 clock_id: str | None = None) -> IsothermalPipeWaveTrace:
        """Advance the finite-volume solution to each requested sample time.

        The spatial update is first-order Rusanov flux on cell averages. Closed
        ends retain zero boundary mass flux and pressure wall traction. Optional
        pressure reservoirs supply one incoming subsonic characteristic at an
        open end while the adjacent cell supplies the outgoing characteristic.
        At each substep,
        the maximum acoustic/convective speed sets ``dt <= CFL*dx/(|u|+c)``.
        Darcy drag is applied by its exact local momentum decay map after each
        conservative flux update. Internal states that become nonpositive are
        rejected rather than clipped. No output interpolation is used.
        """
        if any(isinstance(value, (str, bytes)) for value in
               (initial_pressure_pa, initial_velocity_m_s, time_samples_s)):
            raise TypeError("Initial fields and time_samples_s must be numeric sequences")
        try:
            pressures = np.asarray(tuple(initial_pressure_pa), dtype=float)
            velocities = np.asarray(tuple(initial_velocity_m_s), dtype=float)
            times = np.asarray(tuple(time_samples_s), dtype=float)
        except (TypeError, ValueError) as error:
            raise TypeError("Initial pressure, velocity, and time samples must be numeric sequences") from error
        shape = (self.cell_count,)
        if pressures.shape != shape or velocities.shape != shape:
            raise ValueError("Initial pressure and velocity need exactly one value per pipe cell")
        if (times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times))
                or times[0] != 0. or np.any(np.diff(times) <= 0.)):
            raise ValueError("time_samples_s must start at zero and increase strictly")
        has_reservoir = left_reservoir is not None or right_reservoir is not None
        if has_reservoir:
            if not isinstance(clock_id, str) or not clock_id.strip():
                raise ValueError("Open reservoir boundaries require the run clock identity")
            for side, boundary in (("left", left_reservoir), ("right", right_reservoir)):
                if boundary is None:
                    continue
                if type(boundary) is not FiniteReservoirPressureBoundary:
                    raise TypeError(f"{side} reservoir must be a FiniteReservoirPressureBoundary")
                boundary.require_compatible(
                    start_time_s=float(times[0]), end_time_s=float(times[-1]),
                    clock_id=clock_id, eos_identity=self.eos.identity,
                    temperature_k=self.temperature_k,
                )
                for pressure_knot in boundary.pressure_pa:
                    knot_density = finite(
                        self.eos.density_pt(float(pressure_knot), self.temperature_k),
                        f"{side} reservoir EOS density", positive=True,
                    )
                    replayed_pressure = finite(
                        self.eos.pressure_rho_t(knot_density, self.temperature_k),
                        f"{side} reservoir EOS replay pressure", positive=True,
                    )
                    knot_sound_speed = finite(
                        self.eos.isothermal_sound_speed_rho_t(knot_density, self.temperature_k),
                        f"{side} reservoir isothermal sound speed", positive=True,
                    )
                    if (not np.isclose(replayed_pressure, pressure_knot,
                                       rtol=1e-6, atol=1e-3)
                            or knot_sound_speed <= 0.):
                        raise ValueError("Reservoir pressure knots do not close through the selected EOS")
        elif clock_id is not None:
            raise ValueError("Declare clock_id only when using a pressure-reservoir boundary")
        if (not np.all(np.isfinite(pressures)) or np.any(pressures <= 0.)
                or not np.all(np.isfinite(velocities))):
            raise ValueError("Initial pressure must be finite and positive; velocity finite")

        temperature = self.temperature_k
        area = self.cross_section_area_m2
        dx = self.cell_length_m
        density = np.asarray([self.eos.density_pt(float(p), temperature) for p in pressures], dtype=float)
        if not np.all(np.isfinite(density)) or np.any(density <= 0.):
            raise ValueError("EOS closure returned nonpositive or nonfinite initial density")
        pressure_replayed = np.asarray([
            self.eos.pressure_rho_t(float(rho), temperature) for rho in density
        ], dtype=float)
        if (not np.all(np.isfinite(pressure_replayed)) or np.any(pressure_replayed <= 0.)
                or not np.allclose(pressure_replayed, pressures, rtol=1e-6, atol=1e-3)):
            raise ValueError("EOS pressure/density mappings do not close at the initial state")
        conserved = np.vstack((density, density * velocities))
        characteristic_reference_density = float(density[0])
        characteristic_reference_sound_speed = finite(
            self.eos.isothermal_sound_speed_rho_t(
                characteristic_reference_density, temperature,
            ), "characteristic reference sound speed", positive=True,
        )
        initial_total_mass = float(np.sum(density) * area * dx)
        pressure_samples = [pressures.copy()]
        velocity_samples = [velocities.copy()]
        density_samples = [density.copy()]
        sound_speed_samples = [[
            self.eos.isothermal_sound_speed_rho_t(float(rho), temperature) for rho in density
        ]]
        total_mass_samples = [initial_total_mass]
        residual_samples = [0.]
        face_flow_samples = [np.zeros(self.cell_count + 1)]
        boundary_mass_in_samples = [0.]
        boundary_mass_out_samples = [0.]
        cumulative_boundary_mass_in = 0.
        cumulative_boundary_mass_out = 0.
        elapsed_steps = 0
        observed_maximum_cfl = 0.
        friction_rate = self.darcy_friction_factor / (2. * self.internal_diameter_m)

        def characteristic_potential(rho_value, sound_speed=None):
            """Integrate c_T(rho)/rho over log density with composite Simpson."""
            rho_value = finite(rho_value, "characteristic density", positive=True)
            log_reference = float(np.log(characteristic_reference_density))
            log_target = float(np.log(rho_value))
            if log_target == log_reference:
                return 0.0
            nodes = np.linspace(log_reference, log_target, 5)
            samples = []
            for index, log_density in enumerate(nodes):
                if index == 0:
                    value = characteristic_reference_sound_speed
                elif index == len(nodes)-1 and sound_speed is not None:
                    value = sound_speed
                else:
                    value = finite(
                        self.eos.isothermal_sound_speed_rho_t(
                            float(np.exp(log_density)), temperature,
                        ), "characteristic quadrature sound speed", positive=True,
                    )
                samples.append(value)
            step_log = (log_target-log_reference)/4.0
            return step_log/3.0 * (
                samples[0] + 4.0*samples[1] + 2.0*samples[2]
                + 4.0*samples[3] + samples[4]
            )

        def reservoir_ghost(boundary, side, time_s, rho_inside, velocity_inside,
                            sound_inside):
            pressure_reservoir = boundary.pressure_at(time_s)
            rho_reservoir = finite(
                self.eos.density_pt(pressure_reservoir, temperature),
                f"{side} reservoir EOS density", positive=True,
            )
            pressure_replayed = finite(
                self.eos.pressure_rho_t(rho_reservoir, temperature),
                f"{side} reservoir EOS replay pressure", positive=True,
            )
            sound_reservoir = finite(
                self.eos.isothermal_sound_speed_rho_t(rho_reservoir, temperature),
                f"{side} reservoir sound speed", positive=True,
            )
            if not np.isclose(pressure_replayed, pressure_reservoir,
                              rtol=1e-6, atol=1e-3):
                raise ValueError("Reservoir pressure does not replay through the pipe EOS")
            if abs(velocity_inside) >= sound_inside:
                raise ValueError("Open reservoir coupling supports only subsonic adjacent pipe states")
            phi_inside = characteristic_potential(rho_inside, sound_inside)
            phi_reservoir = characteristic_potential(rho_reservoir, sound_reservoir)
            if side == "left":
                incoming = phi_reservoir
                outgoing = velocity_inside - phi_inside
                velocity_boundary = 0.5 * (incoming + outgoing)
                phi_boundary = 0.5 * (incoming - outgoing)
            else:
                incoming = -phi_reservoir
                outgoing = velocity_inside + phi_inside
                velocity_boundary = 0.5 * (outgoing + incoming)
                phi_boundary = 0.5 * (outgoing - incoming)
            rho_low, rho_high = sorted((rho_inside, rho_reservoir))
            sound_low = finite(self.eos.isothermal_sound_speed_rho_t(
                rho_low, temperature), "lower characteristic bracket speed", positive=True)
            sound_high = finite(self.eos.isothermal_sound_speed_rho_t(
                rho_high, temperature), "upper characteristic bracket speed", positive=True)
            phi_low = characteristic_potential(
                rho_low, sound_low,
            )
            phi_high = characteristic_potential(
                rho_high, sound_high,
            )
            if phi_high < phi_low or phi_boundary < phi_low or phi_boundary > phi_high:
                raise ValueError("Characteristic ghost state lies outside the local EOS density bracket")
            if rho_low == rho_high:
                rho_boundary = rho_low
            elif (abs(sound_inside-characteristic_reference_sound_speed) <=
                  1e-12 * max(sound_inside, characteristic_reference_sound_speed)
                  and abs(sound_reservoir-characteristic_reference_sound_speed) <=
                  1e-12 * max(sound_reservoir, characteristic_reference_sound_speed)):
                rho_boundary = characteristic_reference_density * float(np.exp(
                    phi_boundary / characteristic_reference_sound_speed
                ))
            else:
                low_log, high_log = float(np.log(rho_low)), float(np.log(rho_high))
                trial_log = 0.5*(low_log+high_log)
                rho_boundary = float(np.exp(trial_log))
                converged = False
                for _ in range(20):
                    trial_sound = finite(
                        self.eos.isothermal_sound_speed_rho_t(rho_boundary, temperature),
                        "characteristic trial sound speed", positive=True,
                    )
                    trial_phi = characteristic_potential(rho_boundary, trial_sound)
                    residual_phi = trial_phi - phi_boundary
                    if abs(residual_phi) <= 1e-10 * max(abs(phi_boundary), 1.):
                        converged = True
                        break
                    if residual_phi < 0.:
                        low_log = trial_log
                    else:
                        high_log = trial_log
                    newton_log = trial_log - residual_phi / trial_sound
                    trial_log = (newton_log if low_log < newton_log < high_log
                                 else 0.5*(low_log+high_log))
                    rho_boundary = float(np.exp(trial_log))
                if not converged:
                    raise ValueError("EOS characteristic ghost-state solve did not converge")
            sound_boundary = finite(
                self.eos.isothermal_sound_speed_rho_t(rho_boundary, temperature),
                "characteristic boundary sound speed", positive=True,
            )
            if abs(velocity_boundary) >= sound_boundary:
                raise ValueError("Characteristic ghost state is not subsonic")
            pressure_boundary = finite(
                self.eos.pressure_rho_t(rho_boundary, temperature),
                "characteristic boundary pressure", positive=True,
            )
            return rho_boundary, velocity_boundary, pressure_boundary, sound_boundary

        def rusanov_face(rho_left, velocity_left, pressure_left, sound_left,
                         rho_right, velocity_right, pressure_right, sound_right):
            momentum_left = rho_left * velocity_left
            momentum_right = rho_right * velocity_right
            speed = max(abs(velocity_left) + sound_left,
                        abs(velocity_right) + sound_right)
            mass_flux = 0.5 * (momentum_left + momentum_right) \
                - 0.5 * speed * (rho_right - rho_left)
            momentum_flux = 0.5 * (
                rho_left * velocity_left**2 + pressure_left
                + rho_right * velocity_right**2 + pressure_right
            ) - 0.5 * speed * (momentum_right - momentum_left)
            return mass_flux, momentum_flux

        def maximum_wave_speed(state, boundary_time_s):
            rho, momentum = state
            velocity = momentum / rho
            sounds = np.asarray([
                self.eos.isothermal_sound_speed_rho_t(float(value), temperature)
                for value in rho
            ], dtype=float)
            if not np.all(np.isfinite(sounds)) or np.any(sounds <= 0.):
                raise FloatingPointError("EOS closure returned invalid isothermal sound speed")
            speeds = list(np.abs(velocity) + sounds)
            if left_reservoir is not None:
                ghost = reservoir_ghost(
                    left_reservoir, "left", boundary_time_s,
                    float(rho[0]), float(velocity[0]), float(sounds[0]),
                )
                speeds.append(abs(ghost[1]) + ghost[3])
            if right_reservoir is not None:
                ghost = reservoir_ghost(
                    right_reservoir, "right", boundary_time_s,
                    float(rho[-1]), float(velocity[-1]), float(sounds[-1]),
                )
                speeds.append(abs(ghost[1]) + ghost[3])
            return float(max(speeds))

        def spatial_step(state, dt, boundary_time_s):
            rho, momentum = state
            speed = momentum / rho
            pressure = np.asarray([
                self.eos.pressure_rho_t(float(value), temperature) for value in rho
            ], dtype=float)
            local_sound_speed = np.asarray([
                self.eos.isothermal_sound_speed_rho_t(float(value), temperature)
                for value in rho
            ], dtype=float)
            if (not np.all(np.isfinite(pressure)) or np.any(pressure <= 0.)
                    or not np.all(np.isfinite(local_sound_speed))
                    or np.any(local_sound_speed <= 0.)):
                raise FloatingPointError("EOS closure returned an invalid pressure or isothermal sound speed")
            face_flux = np.zeros((2, self.cell_count + 1), dtype=float)
            if left_reservoir is None:
                face_flux[1, 0] = pressure[0]
            else:
                ghost = reservoir_ghost(
                    left_reservoir, "left", boundary_time_s,
                    float(rho[0]), float(speed[0]), float(local_sound_speed[0]),
                )
                face_flux[:, 0] = rusanov_face(
                    *ghost, float(rho[0]), float(speed[0]),
                    float(pressure[0]), float(local_sound_speed[0]),
                )
            if right_reservoir is None:
                face_flux[1, -1] = pressure[-1]
            else:
                ghost = reservoir_ghost(
                    right_reservoir, "right", boundary_time_s,
                    float(rho[-1]), float(speed[-1]), float(local_sound_speed[-1]),
                )
                face_flux[:, -1] = rusanov_face(
                    float(rho[-1]), float(speed[-1]), float(pressure[-1]),
                    float(local_sound_speed[-1]), *ghost,
                )
            for face in range(1, self.cell_count):
                left = face - 1
                right = face
                face_flux[:, face] = rusanov_face(
                    float(rho[left]), float(speed[left]), float(pressure[left]),
                    float(local_sound_speed[left]), float(rho[right]),
                    float(speed[right]), float(pressure[right]),
                    float(local_sound_speed[right]),
                )
            updated = state - (dt / dx) * (face_flux[:, 1:] - face_flux[:, :-1])
            if not np.all(np.isfinite(updated)) or np.any(updated[0] <= 0.):
                raise FloatingPointError("Finite-volume update produced a nonpositive/nonfinite density")
            if friction_rate:
                velocity_before_drag = updated[1] / updated[0]
                updated[1] /= 1. + friction_rate * np.abs(velocity_before_drag) * dt
            return updated, face_flux[0]

        if has_reservoir:
            _initial_state, initial_boundary_flux = spatial_step(conserved, 0., 0.)
            face_flow_samples[0] = initial_boundary_flux * area

        for target_time in times[1:]:
            current_time = float(times[len(total_mass_samples) - 1])
            while current_time < target_time:
                rho, momentum = conserved
                speed = momentum / rho
                local_sound_speed = np.asarray([
                    self.eos.isothermal_sound_speed_rho_t(float(value), temperature)
                    for value in rho
                ], dtype=float)
                if not np.all(np.isfinite(local_sound_speed)) or np.any(local_sound_speed <= 0.):
                    raise FloatingPointError("EOS closure returned invalid isothermal sound speed")
                remaining = float(target_time - current_time)
                max_characteristic_speed = float(np.max(np.abs(speed) + local_sound_speed))
                dt = min(remaining, self.maximum_cfl * dx / max_characteristic_speed)
                for _ in range(12):
                    max_characteristic_speed = maximum_wave_speed(
                        conserved, current_time + 0.5 * dt,
                    )
                    permitted = self.maximum_cfl * dx / max_characteristic_speed
                    if dt <= min(remaining, permitted) * (1. + 1e-12):
                        break
                    dt = min(remaining, permitted)
                max_characteristic_speed = maximum_wave_speed(
                    conserved, current_time + 0.5 * dt,
                )
                if (dt * max_characteristic_speed / dx
                        > self.maximum_cfl * (1. + 1e-12)):
                    raise FloatingPointError(
                        "Boundary characteristic speeds could not satisfy the declared CFL bound"
                    )
                if not np.isfinite(dt) or dt <= 0.:
                    raise FloatingPointError("CFL controller could not form a positive finite timestep")
                next_time = current_time + dt
                if next_time <= current_time:
                    raise FloatingPointError("CFL timestep is below floating-point time resolution")
                conserved, face_mass_flow = spatial_step(
                    conserved, dt, current_time + 0.5 * dt,
                )
                left_boundary_rate = float(face_mass_flow[0] * area)
                right_boundary_rate = float(face_mass_flow[-1] * area)
                cumulative_boundary_mass_in += dt * (
                    max(left_boundary_rate, 0.) + max(-right_boundary_rate, 0.)
                )
                cumulative_boundary_mass_out += dt * (
                    max(-left_boundary_rate, 0.) + max(right_boundary_rate, 0.)
                )
                observed_maximum_cfl = max(
                    observed_maximum_cfl, dt * max_characteristic_speed / dx,
                )
                elapsed_steps += 1
                if elapsed_steps > self.maximum_internal_steps:
                    raise RuntimeError("maximum_internal_steps reached before all requested times")
                current_time = min(float(target_time), next_time)
            density = conserved[0]
            velocity = conserved[1] / density
            pressure = np.asarray([
                self.eos.pressure_rho_t(float(value), temperature) for value in density
            ], dtype=float)
            local_sound_speed = np.asarray([
                self.eos.isothermal_sound_speed_rho_t(float(value), temperature)
                for value in density
            ], dtype=float)
            total_mass = float(np.sum(density) * area * dx)
            pressure_samples.append(pressure.copy())
            velocity_samples.append(velocity.copy())
            density_samples.append(density.copy())
            sound_speed_samples.append(local_sound_speed.copy())
            total_mass_samples.append(total_mass)
            residual_samples.append(
                total_mass - initial_total_mass - cumulative_boundary_mass_in
                + cumulative_boundary_mass_out
            )
            face_flow_samples.append(face_mass_flow.copy() * area)
            boundary_mass_in_samples.append(cumulative_boundary_mass_in)
            boundary_mass_out_samples.append(cumulative_boundary_mass_out)

        centers = (np.arange(self.cell_count, dtype=float) + 0.5) * dx
        return IsothermalPipeWaveTrace(
            time_s=times, cell_center_m=centers, pressure_pa=pressure_samples,
            velocity_m_s=velocity_samples, density_kg_m3=density_samples,
            face_mass_flow_kg_s=face_flow_samples, total_mass_kg=total_mass_samples,
            mass_balance_residual_kg=residual_samples,
            isothermal_sound_speed_m_s=sound_speed_samples,
            eos_closure_id=self.eos.identity,
            maximum_cfl=observed_maximum_cfl, cfl_limit=self.maximum_cfl,
            darcy_friction_factor=self.darcy_friction_factor,
            temperature_k=temperature,
            boundary_mass_in_kg=boundary_mass_in_samples,
            boundary_mass_out_kg=boundary_mass_out_samples,
            left_reservoir_pressure_pa=(None if left_reservoir is None else
                [left_reservoir.pressure_at(float(t)) for t in times]),
            right_reservoir_pressure_pa=(None if right_reservoir is None else
                [right_reservoir.pressure_at(float(t)) for t in times]),
            boundary_clock_id=clock_id if has_reservoir else None,
            left_reservoir_id=None if left_reservoir is None else left_reservoir.identifier,
            right_reservoir_id=None if right_reservoir is None else right_reservoir.identifier,
            left_reservoir_state_owner_id=(None if left_reservoir is None
                                           else left_reservoir.state_owner_id),
            right_reservoir_state_owner_id=(None if right_reservoir is None
                                            else right_reservoir.state_owner_id),
            left_reservoir_state_evidence_id=(None if left_reservoir is None
                                              else left_reservoir.state_evidence_id),
            right_reservoir_state_evidence_id=(None if right_reservoir is None
                                               else right_reservoir.state_evidence_id),
        )


__all__ = ["IsothermalSinglePhaseEOS", "IdealHydrogenIsothermalEOS",
           "FiniteReservoirPressureBoundary", "IsothermalPipeWaveTrace",
           "IsothermalPipeWaveModel"]
