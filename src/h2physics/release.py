"""A shared, phase-aware short-nozzle kernel and explicit source-plane histories.

Original implementation from steady mass/energy conservation and an isentropic
equilibrium path. Ideal-gas verification uses NASA Glenn's analytical relations:
https://www.grc.nasa.gov/www/k-12/airplane/mflchk.html
Property input/phase meanings follow the injected provider, for example:
https://coolprop.org/coolprop/HighLevelAPI.html

This level assumes a stationary reservoir, negligible inlet kinetic energy,
adiabatic flow, instantaneous phase equilibrium and equal phase velocities.
It does not resolve pipe friction, nucleation delay or the external jet.
"""

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import numpy as np
from scipy.optimize import brentq, minimize_scalar

from .core import Origin, PropertyProvider, ThermoState, TimeSeries, finite

if TYPE_CHECKING:
    from .sources import IntervalMassSource


@dataclass(frozen=True, slots=True)
class NozzleOpening:
    """An effective-area closure; the factor is not a measured velocity model."""

    opening_id: str
    nominal_area_m2: float
    effective_area_factor: float
    area_basis_id: str

    def __post_init__(self):
        if not self.opening_id.strip() or not self.area_basis_id.strip():
            raise ValueError("Opening identity and effective-area interpretation are required")
        finite(self.nominal_area_m2, "nominal_area_m2", positive=True)
        factor = finite(self.effective_area_factor, "effective_area_factor", positive=True)
        if factor > 1:
            raise ValueError("This effective-area factor must lie in (0, 1]")

    @classmethod
    def circular(cls, opening_id: str, diameter_m: float, *, effective_area_factor: float,
                 area_basis_id: str):
        diameter = finite(diameter_m, "diameter_m", positive=True)
        return cls(opening_id, math.pi * diameter**2 / 4, effective_area_factor, area_basis_id)

    def effective_area_m2(self, opening_fraction: float) -> float:
        fraction = finite(opening_fraction, "opening_fraction")
        if not 0 <= fraction <= 1:
            raise ValueError("Opening fraction must lie in [0, 1]")
        return self.nominal_area_m2 * self.effective_area_factor * fraction


@dataclass(frozen=True, slots=True)
class NozzleSearch:
    initial_grid_points: int = 33
    maximum_refinements: int = 3
    relative_flux_tolerance: float = 1e-7
    relative_pressure_tolerance: float = 1e-6
    upstream_relative_tolerance: float = 2e-6
    enthalpy_roundoff_j_kg: float = 1e-5

    def __post_init__(self):
        if (isinstance(self.initial_grid_points, bool)
                or not isinstance(self.initial_grid_points, int) or self.initial_grid_points < 5):
            raise ValueError("Search needs at least five grid points")
        if (isinstance(self.maximum_refinements, bool)
                or not isinstance(self.maximum_refinements, int) or self.maximum_refinements < 1):
            raise ValueError("At least one independent grid refinement is required")
        for name in ("relative_flux_tolerance", "relative_pressure_tolerance",
                     "upstream_relative_tolerance", "enthalpy_roundoff_j_kg"):
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class NozzleDiagnostics:
    property_evaluations: int
    grid_refinements: int
    relative_flux_change: float
    relative_pressure_change: float
    maximum_negative_enthalpy_roundoff_j_kg: float
    maximum_quality_roundoff: float = 0.
    sonic_refinements: int = 0


@dataclass(frozen=True, slots=True)
class NozzleResult:
    opening: NozzleOpening
    upstream_stagnation: ThermoState
    back_pressure_pa: float
    effective_area_m2: float
    exit_state: ThermoState | None
    velocity_m_s: float
    mass_flux_kg_m2_s: float
    mass_flow_kg_s: float
    regime: Literal["choked", "back_pressure_limited", "closed", "no_forward_pressure"]
    diagnostics: NozzleDiagnostics
    model_id: str = "homogeneous-equilibrium-isentropic-effective-area-v1"

    @property
    def withdrawal_energy_w(self) -> float:
        """Energy removed from a stagnant reservoir; includes outlet kinetic energy."""
        return self.mass_flow_kg_s * self.upstream_stagnation.enthalpy_j_kg

    @property
    def kinetic_power_w(self) -> float:
        return self.mass_flow_kg_s * self.velocity_m_s**2 / 2

    @property
    def static_enthalpy_flow_w(self) -> float:
        return 0. if self.exit_state is None else self.mass_flow_kg_s * self.exit_state.enthalpy_j_kg

    @property
    def energy_residual_w(self) -> float:
        return self.static_enthalpy_flow_w + self.kinetic_power_w - self.withdrawal_energy_w

    @property
    def effective_area_thrust_n(self) -> float:
        """Axial momentum plus pressure force under this declared area closure only."""
        if self.exit_state is None:
            return 0.
        return (self.mass_flow_kg_s * self.velocity_m_s
                + (self.exit_state.pressure_pa - self.back_pressure_pa) * self.effective_area_m2)


class HomogeneousIsentropicNozzle:
    """One EOS path for gas, liquid and equilibrium two-phase inlet states.

Both pressure endpoints participate. Every sampled interior maximum is refined
in log pressure, and a finer grid must reproduce the selected flux and pressure.
Provider errors and nonconvergence are surfaced rather than skipped. This is a
numerical convergence check, not proof of global optimality or physical validity.
"""

    def __init__(self, properties: PropertyProvider, *, search: NozzleSearch | None = None):
        self.properties = properties
        self.search = search or NozzleSearch()

    def solve(self, upstream_stagnation: ThermoState, *, back_pressure_pa: float,
              opening: NozzleOpening, opening_fraction: float = 1.) -> NozzleResult:
        upstream = upstream_stagnation
        self.properties.basis.require_compatible(upstream.basis)
        back = finite(back_pressure_pa, "back_pressure_pa", positive=True)
        area = opening.effective_area_m2(opening_fraction)
        empty = NozzleDiagnostics(0, 0, 0., 0., 0.)
        if area == 0 or back >= upstream.pressure_pa:
            return NozzleResult(opening, upstream, back, area, None, 0., 0., 0.,
                                "closed" if area == 0 else "no_forward_pressure", empty)
        search = self.search
        recovered = self.properties.state_ps(upstream.pressure_pa, upstream.entropy_j_kg_k)
        self.properties.basis.require_compatible(recovered.basis)
        for name in ("pressure_pa", "temperature_k", "density_kg_m3", "enthalpy_j_kg",
                     "entropy_j_kg_k"):
            expected, actual = getattr(upstream, name), getattr(recovered, name)
            if abs(actual - expected) > search.upstream_relative_tolerance * max(abs(expected), 1.):
                raise ValueError(f"Upstream state is inconsistent with the nozzle provider: {name}")
        if upstream.vapor_mass_fraction is not None:
            if (recovered.vapor_mass_fraction is None
                    or abs(recovered.vapor_mass_fraction - upstream.vapor_mass_fraction)
                    > search.upstream_relative_tolerance):
                raise ValueError("Upstream vapor fraction is inconsistent with the nozzle provider")

        # Cache is per call: no reservoir state, provider or reference can leak to another solve.
        cache: dict[float, tuple[float, ThermoState, float]] = {}
        roundoff = quality_roundoff = 0.
        sonic_refinements = 0

        def evaluate(log_pressure):
            nonlocal roundoff, quality_roundoff
            key = float(log_pressure)
            if key not in cache:
                pressure = float(np.clip(math.exp(key), back, upstream.pressure_pa))
                state = self.properties.state_ps(pressure, upstream.entropy_j_kg_k)
                self.properties.basis.require_compatible(state.basis)
                if state.raw_vapor_mass_fraction is not None:
                    quality_roundoff = max(quality_roundoff,
                                          abs(state.raw_vapor_mass_fraction - state.vapor_mass_fraction))
                if not math.isclose(state.pressure_pa, pressure,
                                    rel_tol=search.upstream_relative_tolerance):
                    raise ValueError("Provider returned a different path pressure")
                if abs(state.entropy_j_kg_k - upstream.entropy_j_kg_k) > (
                        search.upstream_relative_tolerance * max(abs(upstream.entropy_j_kg_k), 1.)):
                    raise ValueError("Provider did not preserve path entropy")
                drop = upstream.enthalpy_j_kg - state.enthalpy_j_kg
                if drop < -search.enthalpy_roundoff_j_kg:
                    raise ValueError("Nozzle path enthalpy exceeds upstream stagnation enthalpy")
                roundoff = max(roundoff, -drop)
                velocity = math.sqrt(2 * max(0., drop))
                cache[key] = (state.density_kg_m3 * velocity, state, velocity)
            return cache[key]

        lower, upper = math.log(back), math.log(upstream.pressure_pa)
        # The upstream endpoint has exactly zero kinetic energy by the reservoir assumption.
        cache[upper] = (0., upstream, 0.)
        previous = None
        flux_change = pressure_change = math.inf
        for refinement in range(search.maximum_refinements + 1):
            count = (search.initial_grid_points - 1) * 2**refinement + 1
            grid = np.linspace(lower, upper, count)
            values = np.array([evaluate(x)[0] for x in grid])
            candidates = [float(grid[0]), float(grid[-1])]
            # A true interior maximum can lie inside the first/last cell even
            # when the endpoint exceeds its nearest grid neighbor. Refine those
            # boundary cells too, especially close to the choking transition.
            brackets = []
            if values[0] >= values[1]:
                brackets.append((grid[0], grid[1]))
            if values[-1] >= values[-2]:
                brackets.append((grid[-2], grid[-1]))
            for index in range(1, count - 1):
                if values[index] >= values[index - 1] and values[index] >= values[index + 1]:
                    brackets.append((grid[index - 1], grid[index + 1]))
                    candidates.append(float(grid[index]))
            for bracket in brackets:
                center = (bracket[0] + bracket[1]) / 2
                half_width = (bracket[1] - bracket[0]) / 2
                left_state, right_state = evaluate(bracket[0])[1], evaluate(bracket[1])[1]
                left_sound, right_sound = left_state.speed_of_sound_m_s, right_state.speed_of_sound_m_s
                if (left_sound is not None and right_sound is not None
                        and left_state.phase != "two_phase" and right_state.phase != "two_phase"):
                    # For a thermodynamically consistent single phase, dG/dP=0
                    # is exactly v²=a². The sign-changing root resolves a flat
                    # maximum more reliably than differences in nearly equal G.
                    def sonic_residual(x):
                        _, candidate, speed = evaluate(center + x * half_width)
                        sound = candidate.speed_of_sound_m_s
                        if sound is None or candidate.phase == "two_phase":
                            raise ValueError("Sonic pressure bracket crosses an unsupported phase")
                        return speed**2 - sound**2

                    if sonic_residual(-1.) > 0 and sonic_residual(1.) < 0:
                        root = brentq(sonic_residual, -1., 1., xtol=1e-11, rtol=1e-12)
                        root_pressure = float(center + root * half_width)
                        candidate_flux = evaluate(root_pressure)[0]
                        if candidate_flux < max(evaluate(x)[0] for x in (*bracket, center)) * (1-search.relative_flux_tolerance):
                            raise ValueError("Provider sound speed and isentropic flux are inconsistent")
                        candidates.append(root_pressure)
                        sonic_refinements += 1
                        continue
                # Optimize a local coordinate around zero. SciPy's bounded
                # stopping rule also scales with |x|; using dimensional log(P)
                # near 15–20 otherwise limits pressure resolution prematurely.
                optimum = minimize_scalar(
                    lambda x: -evaluate(center + x * half_width)[0], bounds=(-1., 1.),
                    method="bounded", options={"xatol": 1e-11, "maxiter": 100},
                )
                if not optimum.success:
                    raise RuntimeError("Local nozzle pressure maximization did not converge")
                candidates.append(float(center + optimum.x * half_width))
            best = max(candidates, key=lambda x: evaluate(x)[0])
            flux, state, velocity = evaluate(best)
            # Numerically indistinguishable near-boundary maxima belong to the
            # endpoint within the caller's declared pressure/flux resolution.
            boundary_flux = evaluate(lower)[0]
            if (abs(state.pressure_pa - back) / back <= search.relative_pressure_tolerance
                    and abs(flux - boundary_flux) <= search.relative_flux_tolerance * max(flux, 1e-30)):
                best = lower
                flux, state, velocity = evaluate(lower)
            if previous is not None:
                flux_change = abs(flux - previous[0]) / max(flux, previous[0], 1e-30)
                pressure_change = abs(state.pressure_pa - previous[1]) / state.pressure_pa
                if (flux_change <= search.relative_flux_tolerance
                        and pressure_change <= search.relative_pressure_tolerance):
                    diagnostics = NozzleDiagnostics(len(cache), refinement, flux_change,
                                                   pressure_change, roundoff, quality_roundoff,
                                                   sonic_refinements)
                    regime = "back_pressure_limited" if best == lower else "choked"
                    return NozzleResult(opening, upstream, back, area, state, velocity,
                                        flux, area * flux, regime, diagnostics)
            previous = flux, state.pressure_pa
        raise RuntimeError(f"Nozzle grid refinement failed: flux={flux_change}, pressure={pressure_change}")


@dataclass(frozen=True, slots=True)
class SourceLocation:
    source_id: str
    clock_id: str
    coordinate_frame_id: str
    position_m: tuple[float, float, float]
    direction_unit: tuple[float, float, float]

    def __post_init__(self):
        if not all(isinstance(item, str) and item.strip()
                   for item in (self.source_id, self.clock_id, self.coordinate_frame_id)):
            raise ValueError("Source, clock and coordinate-frame identities are required")
        for name in ("position_m", "direction_unit"):
            raw = getattr(self, name)
            if not isinstance(raw, (tuple, list, np.ndarray)):
                raise TypeError(f"{name} must be a three-coordinate sequence")
            values = tuple(finite(value, name) for value in raw)
            if len(values) != 3:
                raise ValueError("Source position and direction need three coordinates")
            object.__setattr__(self, name, values)
        if not math.isclose(math.sqrt(sum(x*x for x in self.direction_unit)), 1., abs_tol=1e-10):
            raise ValueError("Direction must already be a unit vector")


@dataclass(frozen=True, slots=True)
class SourceHistory:
    """Predicted nozzle-plane samples. No atmospheric or ground partition is inferred.

    Samples describe a window, including its final endpoint. No interpolation or
    integration rule is implicit; discontinuities need separate windows.
    """

    location: SourceLocation
    time_s: tuple[float, ...]
    samples: tuple[NozzleResult, ...]
    end_reason: Literal["window_end", "isolation", "pressure_equalized", "inventory_limit"]

    def __post_init__(self):
        times = tuple(finite(value, "time_s") for value in self.time_s)
        samples = tuple(self.samples)
        if not times or len(times) != len(samples) or any(b <= a for a, b in zip(times, times[1:])):
            raise ValueError("Source samples need a nonempty, strictly increasing matching clock")
        if self.end_reason not in {"window_end", "isolation", "pressure_equalized", "inventory_limit"}:
            raise ValueError("Source end reason must be explicit")
        first = samples[0]
        for sample in samples:
            first.upstream_stagnation.basis.require_compatible(sample.upstream_stagnation.basis)
            if sample.opening != first.opening or sample.model_id != first.model_id:
                raise ValueError("A source window must retain the same opening and model identity")
        if self.end_reason == "isolation" and samples[-1].regime != "closed":
            raise ValueError("Isolation must include a closed final source sample")
        if self.end_reason == "pressure_equalized" and samples[-1].regime != "no_forward_pressure":
            raise ValueError("Pressure equalization must include a no-forward-pressure final sample")
        object.__setattr__(self, "time_s", times)
        object.__setattr__(self, "samples", samples)

    def mass_flow_series(self) -> TimeSeries:
        return TimeSeries(np.array(self.time_s), np.array([[s.mass_flow_kg_s] for s in self.samples]),
                          ("released_hydrogen",), ("kg/s",),
                          np.ones((len(self.samples), 1), dtype=bool), self.location.clock_id,
                          Origin.PREDICTED, self.location.source_id, ("mass_flow",))

    def interval_mass_source(
        self,
        *,
        representative_state: ThermoState,
        flow_rule: Literal["left_hold", "right_hold", "trapezoid"],
        quadrature_evidence_id: str,
        state_projection_evidence_id: str,
    ) -> "IntervalMassSource":
        """Return the finite mass bins from an explicit source projection.

        Use ``interval_mass_projection`` when the caller also needs the sampled
        nozzle energy ledgers and the representative-state discrepancy receipt.
        """
        return self.interval_mass_projection(
            representative_state=representative_state,
            flow_rule=flow_rule,
            quadrature_evidence_id=quadrature_evidence_id,
            state_projection_evidence_id=state_projection_evidence_id,
        ).source

    def interval_mass_projection(
        self,
        *,
        representative_state: ThermoState,
        flow_rule: Literal["left_hold", "right_hold", "trapezoid"],
        quadrature_evidence_id: str,
        state_projection_evidence_id: str,
    ) -> "NozzleSourceProjection":
        """Project sampled nozzle mass and energy fluxes onto finite source bins.

        The selected quadrature is applied independently between adjacent native
        sample times. A single representative thermodynamic state is mandatory
        because ``IntervalMassSource`` carries one state for the full window;
        the caller therefore owns and labels this thermodynamic projection.
        Neither the quadrature nor the state projection is inferred from sparse
        samples. The returned bins preserve the source clock and event endpoint.
        """
        if len(self.time_s) < 2:
            raise ValueError("At least two nozzle samples are needed for finite interval masses")
        if flow_rule not in {"left_hold", "right_hold", "trapezoid"}:
            raise ValueError("Select left_hold, right_hold or trapezoid flow integration explicitly")
        for name, value in (("quadrature evidence", quadrature_evidence_id),
                            ("state-projection evidence", state_projection_evidence_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name}")
        if not isinstance(representative_state, ThermoState):
            raise TypeError("Supply one explicit representative ThermoState for the finite source")
        rates = np.asarray([sample.mass_flow_kg_s for sample in self.samples], dtype=float)
        if not np.all(np.isfinite(rates)) or np.any(rates < 0.):
            raise ValueError("Nozzle history must contain finite nonnegative outward mass flows")
        for sample in self.samples:
            representative_state.basis.require_compatible(sample.upstream_stagnation.basis)
        duration = np.diff(np.asarray(self.time_s, dtype=float))
        sampled = {
            "mass_flow": rates,
            "withdrawal_energy": np.asarray([s.withdrawal_energy_w for s in self.samples]),
            "exit_static_enthalpy": np.asarray([s.static_enthalpy_flow_w for s in self.samples]),
            "exit_kinetic": np.asarray([s.kinetic_power_w for s in self.samples]),
        }
        for name, values in sampled.items():
            if values.shape != rates.shape or not np.all(np.isfinite(values)):
                raise ValueError(f"Nozzle history has invalid sampled {name} values")
        interval = {
            name: _integrate_sampled_rate(values, duration, flow_rule)
            for name, values in sampled.items()
        }

        from .sources import IntervalMassSource

        evidence = ":".join((self.location.source_id, flow_rule,
            quadrature_evidence_id.strip(), state_projection_evidence_id.strip()))
        source = IntervalMassSource(
            self.location,
            np.asarray(self.time_s, dtype=float),
            interval["mass_flow"],
            representative_state,
            Origin.PREDICTED,
            evidence,
            self.end_reason,
        )
        projected_enthalpy = interval["mass_flow"] * representative_state.enthalpy_j_kg
        native_energy_residual = (interval["exit_static_enthalpy"] + interval["exit_kinetic"]
                                  - interval["withdrawal_energy"])
        return NozzleSourceProjection(
            self,
            source,
            representative_state,
            flow_rule,
            quadrature_evidence_id.strip(),
            state_projection_evidence_id.strip(),
            tuple(float(x) for x in rates),
            tuple(float(x) for x in sampled["withdrawal_energy"]),
            tuple(float(x) for x in sampled["exit_static_enthalpy"]),
            tuple(float(x) for x in sampled["exit_kinetic"]),
            tuple(float(x) for x in interval["mass_flow"]),
            tuple(float(x) for x in interval["withdrawal_energy"]),
            tuple(float(x) for x in interval["exit_static_enthalpy"]),
            tuple(float(x) for x in interval["exit_kinetic"]),
            tuple(float(x) for x in native_energy_residual),
            tuple(float(x) for x in projected_enthalpy),
            tuple(float(x) for x in projected_enthalpy - interval["exit_static_enthalpy"]),
        )


def _integrate_sampled_rate(values, duration, rule):
    if rule == "left_hold":
        return np.asarray(values[:-1], dtype=float) * duration
    if rule == "right_hold":
        return np.asarray(values[1:], dtype=float) * duration
    if rule == "trapezoid":
        return .5 * (np.asarray(values[:-1], dtype=float) + np.asarray(values[1:], dtype=float)) * duration
    raise ValueError("Select left_hold, right_hold or trapezoid flow integration explicitly")


@dataclass(frozen=True, slots=True)
class NozzleSourceProjection:
    """Immutable mass/energy projection receipt for one sampled nozzle history."""

    history: SourceHistory
    source: "IntervalMassSource"
    representative_state: ThermoState
    flow_rule: Literal["left_hold", "right_hold", "trapezoid"]
    quadrature_evidence_id: str
    state_projection_evidence_id: str
    sample_mass_flow_kg_s: tuple[float, ...]
    sample_withdrawal_energy_w: tuple[float, ...]
    sample_static_enthalpy_w: tuple[float, ...]
    sample_kinetic_power_w: tuple[float, ...]
    interval_mass_kg: tuple[float, ...]
    interval_withdrawal_energy_j: tuple[float, ...]
    interval_static_enthalpy_j: tuple[float, ...]
    interval_kinetic_energy_j: tuple[float, ...]
    nozzle_energy_residual_j: tuple[float, ...]
    representative_enthalpy_j: tuple[float, ...]
    state_projection_residual_j: tuple[float, ...]
    _identity_bindings: tuple = field(default=(), init=False, repr=False, compare=False)
    _numeric_binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _metadata_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        from .sources import IntervalMassSource

        if type(self.history) is not SourceHistory or type(self.source) is not IntervalMassSource:
            raise TypeError("Projection needs its original nozzle history and finite mass source")
        self.source.require_current()
        if not isinstance(self.representative_state, ThermoState):
            raise TypeError("Retain the exact representative thermodynamic state")
        if self.flow_rule not in {"left_hold", "right_hold", "trapezoid"}:
            raise ValueError("Unsupported nozzle source quadrature")
        if any(not isinstance(identity, str) or not identity.strip() for identity in (
            self.quadrature_evidence_id, self.state_projection_evidence_id,
        )):
            raise ValueError("Retain quadrature and thermodynamic-state projection evidence")
        self.representative_state.basis.require_compatible(
            self.history.samples[0].upstream_stagnation.basis
        )
        if (self.source.location is not self.history.location
                or self.source.state is not self.representative_state
                or self.source.end_reason != self.history.end_reason
                or not np.array_equal(self.source.edges_s, np.asarray(self.history.time_s))):
            raise ValueError("Finite source lost the exact nozzle-history clock/state/end boundary")
        expected_evidence = ":".join((self.history.location.source_id, self.flow_rule,
            self.quadrature_evidence_id, self.state_projection_evidence_id))
        if self.source.evidence_id != expected_evidence or self.source.origin != Origin.PREDICTED:
            raise ValueError("Finite source evidence/origin differs from its projection receipt")
        numeric_names = (
            "sample_mass_flow_kg_s", "sample_withdrawal_energy_w", "sample_static_enthalpy_w",
            "sample_kinetic_power_w", "interval_mass_kg", "interval_withdrawal_energy_j",
            "interval_static_enthalpy_j", "interval_kinetic_energy_j", "nozzle_energy_residual_j",
            "representative_enthalpy_j", "state_projection_residual_j",
        )
        for name in numeric_names:
            column = tuple(finite(x, name) for x in getattr(self, name))
            object.__setattr__(self, name, column)
        numeric_values = tuple(getattr(self, name) for name in numeric_names)
        sample_count, interval_count = len(self.history.time_s), len(self.source.mass_kg)
        if any(len(numeric_values[i]) != sample_count for i in range(4)) or any(
            len(numeric_values[i]) != interval_count for i in range(4, len(numeric_values))
        ):
            raise ValueError("Projection sample and interval ledgers are not aligned")
        if (self.interval_mass_kg != tuple(float(x) for x in self.source.mass_kg)
                or any(m < 0. for m in self.interval_mass_kg)
                or any(rate < 0. for rate in self.sample_mass_flow_kg_s)
                or any(power < 0. for power in self.sample_kinetic_power_w)):
            raise ValueError("Projection mass bins differ from the retained finite source")
        sample_pairs = (
            (self.sample_mass_flow_kg_s, tuple(float(s.mass_flow_kg_s) for s in self.history.samples)),
            (self.sample_withdrawal_energy_w, tuple(float(s.withdrawal_energy_w) for s in self.history.samples)),
            (self.sample_static_enthalpy_w, tuple(float(s.static_enthalpy_flow_w) for s in self.history.samples)),
            (self.sample_kinetic_power_w, tuple(float(s.kinetic_power_w) for s in self.history.samples)),
        )
        if any(captured != current for captured, current in sample_pairs):
            raise ValueError("Projection sample values differ from the retained nozzle history")
        duration = np.diff(np.asarray(self.history.time_s, dtype=float))
        pairs = (
            (self.interval_mass_kg,
             _integrate_sampled_rate(self.sample_mass_flow_kg_s, duration, self.flow_rule)),
            (self.interval_withdrawal_energy_j,
             _integrate_sampled_rate(self.sample_withdrawal_energy_w, duration, self.flow_rule)),
            (self.interval_static_enthalpy_j,
             _integrate_sampled_rate(self.sample_static_enthalpy_w, duration, self.flow_rule)),
            (self.interval_kinetic_energy_j,
             _integrate_sampled_rate(self.sample_kinetic_power_w, duration, self.flow_rule)),
        )
        for retained, expected in pairs:
            if not np.allclose(retained, expected, rtol=1e-13, atol=1e-12):
                raise ValueError("Projection interval ledger differs from its declared quadrature")
        expected_projected = np.asarray(self.interval_mass_kg) * self.representative_state.enthalpy_j_kg
        if not np.allclose(self.representative_enthalpy_j, expected_projected,
                           rtol=1e-13, atol=1e-10):
            raise ValueError("Representative enthalpy projection differs from finite mass and state")
        for total, static, kinetic, residual in zip(
            self.interval_withdrawal_energy_j,
            self.interval_static_enthalpy_j,
            self.interval_kinetic_energy_j,
            self.nozzle_energy_residual_j,
            strict=True,
        ):
            if not math.isclose(static + kinetic - total, residual, rel_tol=1e-12, abs_tol=1e-10):
                raise ValueError("Nozzle energy residual differs from its integrated component ledgers")
        for projected, native, residual in zip(
            self.representative_enthalpy_j,
            self.interval_static_enthalpy_j,
            self.state_projection_residual_j,
            strict=True,
        ):
            if not math.isclose(projected - native, residual, rel_tol=1e-12, abs_tol=1e-10):
                raise ValueError("Representative-state discrepancy differs from the static enthalpy ledger")
        object.__setattr__(self, "_identity_bindings", (
            self.history, self.history.location, self.history.samples, *self.history.samples,
            self.source, self.source.location, self.source.state, self.representative_state,
        ))
        object.__setattr__(self, "_numeric_binding", self._numeric_payload())
        object.__setattr__(self, "_metadata_binding", self._metadata_payload())

    def _numeric_payload(self):
        return (
            tuple(float(x) for x in self.history.time_s),
            tuple(float(s.mass_flow_kg_s) for s in self.history.samples),
            tuple(float(s.withdrawal_energy_w) for s in self.history.samples),
            tuple(float(s.static_enthalpy_flow_w) for s in self.history.samples),
            tuple(float(s.kinetic_power_w) for s in self.history.samples),
            tuple(float(x) for x in self.source.edges_s),
            tuple(float(x) for x in self.source.mass_kg),
            tuple(float(x) for x in self.interval_mass_kg),
            tuple(float(x) for x in self.interval_withdrawal_energy_j),
            tuple(float(x) for x in self.interval_static_enthalpy_j),
            tuple(float(x) for x in self.interval_kinetic_energy_j),
            tuple(float(x) for x in self.nozzle_energy_residual_j),
            tuple(float(x) for x in self.representative_enthalpy_j),
            tuple(float(x) for x in self.state_projection_residual_j),
        )

    def _metadata_payload(self):
        return (
            self.flow_rule,
            self.quadrature_evidence_id,
            self.state_projection_evidence_id,
            self.history.end_reason,
            self.source.end_reason,
            self.source.evidence_id,
            self.source.origin,
            repr(self.representative_state),
            repr(self.history.location),
            tuple((repr(sample.opening), sample.model_id, sample.regime,
                   sample.back_pressure_pa, repr(sample.upstream_stagnation),
                   repr(sample.exit_state)) for sample in self.history.samples),
        )

    @property
    def total_mass_kg(self):
        return float(sum(self.interval_mass_kg))

    @property
    def total_nozzle_energy_residual_j(self):
        return float(sum(self.nozzle_energy_residual_j))

    @property
    def total_state_projection_residual_j(self):
        return float(sum(self.state_projection_residual_j))

    def require_current(self):
        self.source.require_current()
        current_objects = (
            self.history, self.history.location, self.history.samples, *self.history.samples,
            self.source, self.source.location, self.source.state, self.representative_state,
        )
        if any(a is not b for a, b in zip(current_objects, self._identity_bindings, strict=True)):
            raise ValueError("Nozzle projection lost its original history/source/state objects")
        if (self._numeric_payload() != self._numeric_binding
                or self._metadata_payload() != self._metadata_binding):
            raise ValueError("Nozzle mass/energy projection changed after construction")
        return self

    def compare_refinement(self, finer: "NozzleSourceProjection") -> "QuadratureRefinementComparison":
        """Compare precomputed source ledgers on nested native sample grids.

        This reports observed grid sensitivity only. It does not estimate or
        bound physical or quadrature error; callers must obtain the finer
        samples from their source model and select both grids explicitly.
        """
        return QuadratureRefinementComparison(
            self, finer, _refinement_interval_values(self, finer),
        )


def _refinement_interval_values(coarse, fine):
    """Validate nested source histories and aggregate each fine ledger by coarse bin."""
    if type(coarse) is not NozzleSourceProjection or type(fine) is not NozzleSourceProjection:
        raise TypeError("Supply two NozzleSourceProjection receipts")
    coarse.require_current()
    fine.require_current()
    if coarse is fine or len(fine.history.time_s) <= len(coarse.history.time_s):
        raise ValueError("The comparison needs a distinct, strictly finer source history")
    if (coarse.history.location != fine.history.location
            or coarse.history.end_reason != fine.history.end_reason
            or coarse.flow_rule != fine.flow_rule
            or coarse.representative_state != fine.representative_state):
        raise ValueError("Refinement histories must retain source, boundary, rule and state")
    fine_edges = {time: index for index, time in enumerate(fine.history.time_s)}
    if any(time not in fine_edges for time in coarse.history.time_s):
        raise ValueError("Finer sample grid must contain every coarse sample time exactly")
    for coarse_index, time in enumerate(coarse.history.time_s):
        fine_index = fine_edges[time]
        if coarse.history.samples[coarse_index] != fine.history.samples[fine_index]:
            raise ValueError("Shared sample times must retain identical nozzle results")

    channels = (
        ("mass_kg", coarse.interval_mass_kg, fine.interval_mass_kg),
        ("withdrawal_energy_j", coarse.interval_withdrawal_energy_j,
         fine.interval_withdrawal_energy_j),
        ("static_enthalpy_j", coarse.interval_static_enthalpy_j,
         fine.interval_static_enthalpy_j),
        ("kinetic_energy_j", coarse.interval_kinetic_energy_j,
         fine.interval_kinetic_energy_j),
        ("nozzle_energy_residual_j", coarse.nozzle_energy_residual_j,
         fine.nozzle_energy_residual_j),
        ("representative_enthalpy_j", coarse.representative_enthalpy_j,
         fine.representative_enthalpy_j),
        ("state_projection_residual_j", coarse.state_projection_residual_j,
         fine.state_projection_residual_j),
    )
    differences = []
    for name, coarse_values, fine_values in channels:
        coarse_by_bin, fine_by_bin = [], []
        for coarse_index, (left, right) in enumerate(
            zip(coarse.history.time_s, coarse.history.time_s[1:]),
        ):
            i, j = fine_edges[left], fine_edges[right]
            coarse_by_bin.append(float(coarse_values[coarse_index]))
            fine_by_bin.append(float(math.fsum(fine_values[i:j])))
        differences.append((name, tuple(coarse_by_bin), tuple(fine_by_bin)))
    return tuple(differences)


@dataclass(frozen=True, slots=True)
class QuadratureRefinementComparison:
    """Observed coarse-to-fine ledger changes on shared source-time bins."""

    coarse: NozzleSourceProjection
    fine: NozzleSourceProjection
    interval_values: tuple[tuple[str, tuple[float, ...], tuple[float, ...]], ...]

    def __post_init__(self):
        expected_values = _refinement_interval_values(self.coarse, self.fine)
        if not self.interval_values:
            raise ValueError("At least one refinement comparison channel is required")
        if self.interval_values != expected_values:
            raise ValueError("Comparison interval ledger differs from its source projection receipts")
        names = tuple(item[0] for item in self.interval_values)
        if len(set(names)) != len(names):
            raise ValueError("Refinement comparison channel names must be unique")
        count = len(self.coarse.interval_mass_kg)
        for name, coarse_values, fine_values in self.interval_values:
            if (not name or len(coarse_values) != count or len(fine_values) != count
                    or any(not math.isfinite(x) for x in (*coarse_values, *fine_values))):
                raise ValueError("Refinement ledgers must be finite and aligned to coarse intervals")

    def absolute_changes(self, channel: str) -> tuple[float, ...]:
        self.require_current()
        for name, coarse, fine in self.interval_values:
            if name == channel:
                return tuple(abs(b - a) for a, b in zip(coarse, fine, strict=True))
        raise KeyError(channel)

    def signed_changes(self, channel: str) -> tuple[float, ...]:
        self.require_current()
        for name, coarse, fine in self.interval_values:
            if name == channel:
                return tuple(b - a for a, b in zip(coarse, fine, strict=True))
        raise KeyError(channel)

    def relative_changes(self, channel: str) -> tuple[float, ...]:
        """Return absolute change divided by max(abs(coarse), abs(fine))."""
        self.require_current()
        for name, coarse, fine in self.interval_values:
            if name == channel:
                result = []
                for a, b in zip(coarse, fine, strict=True):
                    scale = max(abs(a), abs(b))
                    result.append(0.0 if scale == 0.0 else abs(b - a) / scale)
                return tuple(result)
        raise KeyError(channel)

    def summary(self, channel: str) -> "QuadratureChannelSummary":
        """Return interval and whole-window sensitivity metrics for one ledger."""
        self.require_current()
        for name, coarse, fine in self.interval_values:
            if name == channel:
                coarse_total, fine_total = math.fsum(coarse), math.fsum(fine)
                difference = fine_total - coarse_total
                total_scale = max(abs(coarse_total), abs(fine_total))
                relative_total = 0.0 if total_scale == 0.0 else abs(difference) / total_scale
                absolute = tuple(abs(b - a) for a, b in zip(coarse, fine, strict=True))
                relative = self.relative_changes(channel)
                return QuadratureChannelSummary(
                    channel, coarse_total, fine_total, difference, abs(difference),
                    relative_total, max(absolute, default=0.0), max(relative, default=0.0),
                )
        raise KeyError(channel)

    @property
    def summaries(self) -> tuple["QuadratureChannelSummary", ...]:
        self.require_current()
        return tuple(self.summary(name) for name, _, _ in self.interval_values)

    def require_current(self):
        self.coarse.require_current()
        self.fine.require_current()
        return self


@dataclass(frozen=True, slots=True)
class QuadratureChannelSummary:
    """Compact integrated and worst-interval observed grid-sensitivity metrics."""

    channel: str
    coarse_total: float
    fine_total: float
    signed_total_change: float
    absolute_total_change: float
    relative_total_change: float
    maximum_absolute_interval_change: float
    maximum_relative_interval_change: float

    def __post_init__(self):
        if not self.channel.strip():
            raise ValueError("A comparison channel name is required")
        for name in (
            "coarse_total", "fine_total", "signed_total_change", "absolute_total_change",
            "relative_total_change", "maximum_absolute_interval_change",
            "maximum_relative_interval_change",
        ):
            value = finite(getattr(self, name), name)
            if name != "signed_total_change" and value < 0.0:
                raise ValueError("Absolute and relative comparison metrics cannot be negative")
            object.__setattr__(self, name, value)
