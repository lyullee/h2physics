"""Optional native isothermal ADM1 liquid/headspace integration and balance audit.

QSDsan owns reactions, acid/base equilibrium, gas transfer, pressure/vent law and
the complete dynamic solver. This module assembles native objects and observes
their results. No biological rate, stoichiometric coefficient or EOS is supplied
by the host. Component ``kg`` means the native component's measured basis, which
is often COD rather than physical mass.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from importlib import import_module, metadata
from importlib.util import find_spec
from math import isfinite
from pathlib import Path
from types import MappingProxyType
from typing import Any
from uuid import uuid4

import numpy as np


def _positive(value: float, name: str, *, zero: bool = False) -> float:
    value = float(value)
    if not isfinite(value) or value < 0 or (value == 0 and not zero):
        raise ValueError(f"{name} must be finite and {'nonnegative' if zero else 'positive'}")
    return value


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must identify its explicit source/basis")


def _fractions(values: Mapping[str, float], name: str) -> Mapping[str, float]:
    if not values:
        raise ValueError(f"{name} must be explicitly supplied")
    return MappingProxyType({str(k): _positive(v, f"{name}[{k}]", zero=True)
                             for k, v in values.items()})


@dataclass(frozen=True)
class BiologicalEvidence:
    source_id: str
    parameter_source_id: str
    initial_state_source_id: str
    feed_source_id: str
    temperature_source_id: str
    component_basis_id: str
    clock_id: str
    support_start_s: float
    support_end_s: float

    def __post_init__(self) -> None:
        for name in ("source_id", "parameter_source_id", "initial_state_source_id",
                     "feed_source_id", "temperature_source_id", "component_basis_id", "clock_id"):
            _text(getattr(self, name), name)
        if not (isfinite(self.support_start_s) and isfinite(self.support_end_s)
                and self.support_end_s > self.support_start_s):
            raise ValueError("feed/temperature clock support must be finite and increasing")


@dataclass(frozen=True)
class Adm1Geometry:
    liquid_volume_m3: float
    headspace_volume_m3: float
    gas_pipe_coefficient_m3_s_pa: float
    external_pressure_pa: float
    temperature_k: float

    def __post_init__(self) -> None:
        for name in ("liquid_volume_m3", "headspace_volume_m3", "external_pressure_pa",
                     "temperature_k"):
            _positive(getattr(self, name), name)
        _positive(self.gas_pipe_coefficient_m3_s_pa, "gas pipe coefficient", zero=True)
        if not 280 <= self.temperature_k <= 330:
            raise ValueError("this native ADM1 level admits only declared warm liquid operation 280–330 K")


@dataclass(frozen=True)
class BiologicalAudit:
    component_absolute_tolerance_kg: float
    invariant_absolute_tolerance_kg: float
    maximum_pressure_pa: float
    relative_tolerance: float = 1e-6

    def __post_init__(self) -> None:
        for name in ("component_absolute_tolerance_kg", "invariant_absolute_tolerance_kg",
                     "maximum_pressure_pa", "relative_tolerance"):
            _positive(getattr(self, name), name)


@dataclass(frozen=True)
class BiologicalPoint:
    time_s: float
    pressure_pa: float
    gas_outflow_m3_s: float
    measured_inventories_kg: Mapping[str, float]
    liquid_hydrogen_kg: float
    headspace_hydrogen_kg: float
    native_state: tuple[float, ...]


@dataclass(frozen=True)
class BiologicalBalance:
    component_residuals_kg: Mapping[str, float]
    invariant_residuals_kg: Mapping[str, float]
    inlet_measured_kg: Mapping[str, float]
    liquid_outlet_measured_kg: Mapping[str, float]
    dry_gas_outlet_measured_kg: Mapping[str, float]
    reaction_measured_kg: Mapping[str, float]
    hydrogen_formed_kg: float
    hydrogen_consumed_kg: float
    exported_hydrogen_kg: float
    hydrogen_residual_kg: float
    exported_dry_hydrogen_mole_fraction: float | None


@dataclass(frozen=True)
class BiologicalRun:
    evidence: BiologicalEvidence
    points: tuple[BiologicalPoint, ...]
    balance: BiologicalBalance
    native_system: Any
    native_reactor: Any
    native_model: Any
    native_components: Any
    native_solution: Any
    native_initial_state: tuple[float, ...]
    native_versions: Mapping[str, str]
    native_source_hashes: Mapping[str, str]
    native_threshold_zeroing_kg_m3_or_kmol_m3: float = 1e-16
    energy_balance_available: bool = False
    hydrogen_identity: str = "biochemical-molecular-H2-spin-unresolved"
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer_token not in _PENDING_BIOLOGICAL_RUN_TOKENS:
            raise ValueError("BiologicalRun is issued only by the completed native ADM1 run")
        _PENDING_BIOLOGICAL_RUN_TOKENS.remove(self._issuer_token)
        object.__setattr__(self, "points", tuple(self.points))
        object.__setattr__(self, "native_versions", MappingProxyType(dict(self.native_versions)))
        object.__setattr__(self, "native_source_hashes", MappingProxyType(dict(self.native_source_hashes)))
        object.__setattr__(self, "_seal", _biological_run_fingerprint(self))

    def require_current(self) -> BiologicalRun:
        if self._biological_run_fingerprint() != self._seal:
            raise ValueError("BiologicalRun changed after native ADM1 issuance")
        return self

    def _biological_run_fingerprint(self) -> str:
        return _biological_run_fingerprint(self)


_PENDING_BIOLOGICAL_RUN_TOKENS: set[object] = set()


def _issue_biological_run(*args, **kwargs) -> BiologicalRun:
    token = object()
    _PENDING_BIOLOGICAL_RUN_TOKENS.add(token)
    try:
        return BiologicalRun(*args, **kwargs, _issuer_token=token)
    except Exception:
        _PENDING_BIOLOGICAL_RUN_TOKENS.discard(token)
        raise


def _biological_run_fingerprint(run: BiologicalRun) -> str:
    solution = run.native_solution
    system_state = getattr(run.native_system, "_state", ())
    solution_t = tuple(np.asarray(getattr(solution, "t", ()), dtype=float).reshape(-1))
    solution_y = np.asarray(getattr(solution, "y", np.empty((0, 0))), dtype=float)
    points = tuple((point.time_s, point.pressure_pa, point.gas_outflow_m3_s,
                    tuple(sorted(point.measured_inventories_kg.items())),
                    point.liquid_hydrogen_kg, point.headspace_hydrogen_kg,
                    tuple(point.native_state)) for point in run.points)
    balance = run.balance
    balance_record = tuple((name, tuple(sorted(getattr(balance, name).items())))
                           for name in ("component_residuals_kg", "invariant_residuals_kg",
                                        "inlet_measured_kg", "liquid_outlet_measured_kg",
                                        "dry_gas_outlet_measured_kg", "reaction_measured_kg"))
    payload = (
        run.evidence, points, balance_record, balance.hydrogen_formed_kg,
        balance.hydrogen_consumed_kg, balance.exported_hydrogen_kg,
        balance.hydrogen_residual_kg, balance.exported_dry_hydrogen_mole_fraction,
        id(run.native_system), id(run.native_reactor), id(run.native_model),
        id(run.native_components), id(solution), solution_t,
        solution_y.shape, solution_y.tobytes(), bool(getattr(solution, "success", False)),
        tuple(np.asarray(system_state, dtype=float).reshape(-1)),
        tuple(run.native_initial_state), tuple(sorted(run.native_versions.items())),
        tuple(sorted(run.native_source_hashes.items())),
        run.native_threshold_zeroing_kg_m3_or_kmol_m3,
        run.energy_balance_available, run.hydrogen_identity,
    )
    return sha256(repr(payload).encode("utf-8")).hexdigest()


class BiologicalAuditError(RuntimeError):
    """Keep the actual solver object, native objects and completed audit prefix."""

    def __init__(self, message: str, *, system: Any, reactor: Any,
                 solution: Any, points: tuple[BiologicalPoint, ...],
                 native_state: tuple[float, ...] | None = None,
                 time_s: float | None = None, clock_kind: str = "initialization") -> None:
        super().__init__(message)
        self.native_system = system
        self.native_reactor = reactor
        self.native_solution = solution
        self.audited_points = points
        self.native_state = native_state
        self.time_s = time_s
        self.clock_kind = clock_kind
        self.restoration_error: Exception | None = None


@dataclass(frozen=True)
class QsdSanNative:
    qsdsan: Any
    biosteam: Any
    thermosteam: Any
    versions: Mapping[str, str]
    source_hashes: Mapping[str, str]

    @classmethod
    def from_installed(cls) -> QsdSanNative:
        """Import only on request; no install, path manipulation or fallback."""
        versions = {name: metadata.version(name)
                    for name in ("qsdsan", "biosteam", "thermosteam", "scipy", "numpy", "numpoly")}
        required = {"qsdsan": "1.5.3", "biosteam": "2.54.0", "thermosteam": "0.54.2"}
        if any(versions[name] != version for name, version in required.items()):
            raise ValueError(f"native biological revision differs from checked contract: {versions}")
        spec = find_spec("biosteam")
        if spec is None or not spec.origin:
            raise ImportError("actual separately installed BioSTEAM is required")
        native_path = Path(spec.origin).parent / "_system.py"
        system_hash = sha256(native_path.read_bytes()).hexdigest()
        if system_hash != "0b2ce94ba718b78712d73480563350d861e301049d9017a9c15b92de1754aff9":
            raise ValueError("native BioSTEAM requires checked official revision "
                             "0acb320455d3c6cdaace85bf6ca27a1256706918; PyPI2.54.0 has aliased y0")
        versions["biosteam_revision"] = "0acb320455d3c6cdaace85bf6ca27a1256706918"
        source_hashes = MappingProxyType({"biosteam/_system.py": system_hash})
        return cls(import_module("qsdsan"), import_module("biosteam"),
                   import_module("thermosteam"), MappingProxyType(versions), source_hashes)


class QsdSanAdm1Digester:
    """One native, constant-temperature, no-retention liquid/headspace CSTR.

    ``model`` and ``components`` are actual caller-owned QSDsan objects. Initial
    liquid values include every native component in kg(native measured basis)/m3.
    Feed values include every component except bulk H2O in the same units; native
    WasteStream closes its water volume. Headspace inputs are mol/m3 of each of
    native S_h2, S_ch4 and S_IC (CO2), never a guessed air or dry-gas fraction.
    Construction explicitly sets the native process-global thermo package; do
    not concurrently replace native settings during construction/integration.
    """

    def __init__(self, native: QsdSanNative, *, components: Any, model: Any,
                 geometry: Adm1Geometry, evidence: BiologicalEvidence,
                 feed_volume_flow_m3_s: float,
                 feed_concentrations_kg_m3: Mapping[str, float],
                 initial_liquid_concentrations_kg_m3: Mapping[str, float],
                 initial_headspace_mol_m3: Mapping[str, float],
                 audit: BiologicalAudit) -> None:
        q = _positive(feed_volume_flow_m3_s, "feed volume flow", zero=True)
        self.feed = _fractions(feed_concentrations_kg_m3, "feed concentrations")
        self.initial_liquid = _fractions(initial_liquid_concentrations_kg_m3, "initial liquid")
        self.initial_gas = _fractions(initial_headspace_mol_m3, "initial headspace")
        qs = native.qsdsan
        pm = import_module("qsdsan.process_models")
        su = import_module("qsdsan.unit_operations")
        if not isinstance(model, pm.ADM1):
            raise TypeError("the actual native ADM1 model is required")
        if model._components is not components:
            raise ValueError("model and supplied components must retain the same native identity")
        ids = tuple(components.IDs)
        if set(self.initial_liquid) != set(ids) or set(self.feed) != set(ids) - {"H2O"}:
            raise ValueError("explicit complete native component basis is required (feed excludes bulk H2O)")
        if tuple(model._biogas_IDs) != ("S_h2", "S_ch4", "S_IC"):
            raise ValueError("native gas layout differs from checked H2/CH4/CO2 contract")
        if set(self.initial_gas) != set(model._biogas_IDs) or not sum(self.initial_gas.values()):
            raise ValueError("initial headspace requires explicit nonzero H2/CH4/CO2 molar inventory")
        if model._dyn_params:
            raise ValueError("state-dependent native stoichiometry requires a distinct audit contract")
        if audit.maximum_pressure_pa <= geometry.external_pressure_pa:
            raise ValueError("maximum pressure must exceed declared external absolute pressure")
        qs.settings.set_thermo(components)
        tag = "bio_" + uuid4().hex[:12]
        stream = qs.WasteStream(tag + "_feed", T=geometry.temperature_k, thermo=components)
        if q:
            stream.set_flow_by_concentration(flow_tot=q * 86400,
                                            concentrations={k: v * 1000 for k, v in self.feed.items()},
                                            units=("m3/d", "mg/L"))
        else:
            stream.empty()
        gas = qs.WasteStream(tag + "_gas", phase="g", thermo=components)
        liquid = qs.WasteStream(tag + "_liquid", thermo=components)
        reactor = su.AnaerobicCSTR(tag + "_reactor", ins=stream, outs=(gas, liquid),
                                 thermo=components, model=model,
                                 V_liq=geometry.liquid_volume_m3,
                                 V_gas=geometry.headspace_volume_m3,
                                 T=geometry.temperature_k,
                                 headspace_P=geometry.external_pressure_pa / 1e5,
                                 external_P=geometry.external_pressure_pa / 1e5,
                                 pipe_resistance=geometry.gas_pipe_coefficient_m3_s_pa * 86400 * 1e5,
                                 fixed_headspace_P=False, retain_cmps=(), pH_ctrl=None)
        reactor.algebraic_h2 = False
        system = qs.System(tag + "_system", path=(reactor,))
        system.set_dynamic_tracker(reactor, gas, liquid)
        self.native = native
        self.native_components = components
        self.native_model = model
        self.native_reactor = reactor
        self.native_system = system
        self.native_feed = stream
        self.native_gas = gas
        self.native_effluent = liquid
        self.geometry = geometry
        self.evidence = evidence
        self.audit = audit
        self.feed_volume_flow_m3_s = q
        self._ids = ids
        self._gas_indices = np.asarray(components.indices(model._biogas_IDs))
        self._conversion = np.asarray(components.i_mass) / np.asarray(components.chem_MW)
        self._matrix = np.asarray(model.stoichio_eval(), dtype=float)
        if self._matrix.shape != (22, len(ids)) or not np.all(np.isfinite(self._matrix)):
            raise ValueError("native ADM1 process matrix differs from checked layout")
        if (not np.all(np.isfinite(self._conversion[self._gas_indices]))
                or np.any(self._conversion[self._gas_indices] <= 0)):
            raise ValueError("native gas measured-mass/molar conversion must be finite and positive")
        for j, index in enumerate(self._gas_indices):
            row = self._matrix[-3+j]
            if row[index] != -1 or np.count_nonzero(row) != 1:
                raise ValueError("native last three processes must retain actual gas transfer ownership")

    def run(self, *, start_time_s: float, end_time_s: float, sample_count: int,
            rtol: float = 1e-8, atol: float = 1e-11,
            max_step_s: float = 3600) -> BiologicalRun:
        """Run the native BDF solver; sample its dense output for a separate ledger.

        No requested sample is a declaration of an internal accepted solver step.
        The retained native OdeResult.t/y are the accepted-step history. Sampled
        Simpson ledgers need a separate temporal refinement check for each use.
        """
        if not (self.evidence.support_start_s <= start_time_s < end_time_s
                <= self.evidence.support_end_s):
            raise ValueError("requested clock exceeds explicit feed/temperature support")
        if not isinstance(sample_count, int) or isinstance(sample_count, bool) or sample_count < 3:
            raise ValueError("sample_count must be an integer >=3")
        for name, value in (("rtol", rtol), ("atol", atol), ("max_step_s", max_step_s)):
            _positive(value, name)
        system, reactor = self.native_system, self.native_reactor
        solution = None
        previous_solution = getattr(system.scope, "sol", None)
        points: list[BiologicalPoint] = []
        failing = None
        failing_time = float(start_time_s)
        clock_kind = "initialization"
        pending_error = None
        try:
            system.reset_cache()
            system.converge()
            system._load_state()
            native_q_day = float(self.native_feed.state[-1])
            expected_q_day = self.feed_volume_flow_m3_s * 86400
            if abs(native_q_day - expected_q_day) > 1e-12 * abs(expected_q_day):
                raise ValueError("native feed volume differs from explicitly declared SI inlet")
            initial = np.array([self.initial_liquid[k] for k in self._ids]
                               + [self.initial_gas[k] / 1000
                                  for k in self.native_model._biogas_IDs]
                               + [native_q_day], dtype=float)
            # Use the pinned native initializer/state transfer, never a host RHS.
            system._update_state(initial)
            native_initial = tuple(float(x) for x in system._state)
            failing = native_initial
            if not np.array_equal(system._state, initial):
                raise ValueError("native initialization changed explicitly supplied state")
            clock_kind = "native-integration"
            system.dynamic_run(t_span=(start_time_s / 86400, end_time_s / 86400),
                               method="BDF", rtol=rtol, atol=atol,
                               max_step=max_step_s / 86400, dense_output=True,
                               state_reset_hook=None, t_eval=None)
            solution = system.scope.sol
            if not solution.success or solution.sol is None:
                raise ValueError("native integration did not return a successful dense solution")
            if solution.t[-1] != end_time_s / 86400:
                raise ValueError("native integration did not reach the declared end clock")
            if not np.array_equal(solution.y[:, 0], native_initial):
                raise ValueError("native solver changed the initial trajectory state (possible aliased y0)")
            # Accepted states and dense samples have separate truth/clock roles.
            clock_kind = "native-accepted"
            for native_t, state in zip(solution.t, solution.y.T):
                failing = tuple(float(x) for x in state)
                failing_time = float(native_t * 86400)
                self._point(failing_time, state)
            times = np.linspace(start_time_s, end_time_s, sample_count)
            states = solution.sol(times / 86400).T
            clock_kind = "dense-output-sample"
            for t, state in zip(times, states):
                failing = tuple(float(x) for x in state)
                failing_time = float(t)
                points.append(self._point(float(t), state))
            balance = self._balance(times, states, points)
            return _issue_biological_run(
                self.evidence, tuple(points), balance, system, reactor,
                self.native_model, self.native_components, solution,
                native_initial, self.native.versions, self.native.source_hashes,
            )
        except Exception as exc:
            if solution is None:
                candidate = getattr(system.scope, "sol", None)
                if candidate is not previous_solution:
                    solution = candidate
                    if candidate is not None and getattr(candidate, "y", np.empty((0, 0))).size:
                        failing = tuple(map(float, candidate.y[:, -1]))
                        failing_time = float(candidate.t[-1] * 86400)
                        clock_kind = "native-finalization" if candidate.success else "native-integration"
            pending_error = BiologicalAuditError(str(exc), system=system, reactor=reactor,
                                                 solution=solution, points=tuple(points),
                                                 native_state=failing, time_s=failing_time,
                                                 clock_kind=clock_kind)
            raise pending_error from exc
        finally:
            if solution is not None and getattr(solution, "y", np.empty((0, 0))).size:
                # Auditing earlier points updates native pressure/vent caches.
                try:
                    system._update_state(solution.y[:, -1].copy())
                    self.native_reactor.f_q_gas_var_P_headspace(
                        None, solution.y[len(self._ids):-1, -1], self.geometry.temperature_k)
                except Exception as restore_exc:
                    if pending_error is not None:
                        pending_error.restoration_error = restore_exc
                    else:
                        raise BiologicalAuditError(
                            "native endpoint synchronization failed", system=system,
                            reactor=reactor, solution=solution, points=tuple(points),
                            native_state=tuple(map(float, solution.y[:, -1])),
                            time_s=float(solution.t[-1] * 86400),
                            clock_kind="native-finalization") from restore_exc

    def _point(self, t: float, state: np.ndarray) -> BiologicalPoint:
        if not np.all(np.isfinite(state)) or np.any(state < 0):
            raise ValueError("native liquid/headspace state is negative or nonfinite; no host clipping")
        n = len(self._ids)
        inventories = self.geometry.liquid_volume_m3 * state[:n]
        inventories[self._gas_indices] += (self.geometry.headspace_volume_m3 * state[n:-1]
                                          / self._conversion[self._gas_indices])
        qgas = self.native_reactor.f_q_gas_var_P_headspace(None, state[n:-1],
                                                        self.geometry.temperature_k) / 86400
        if not isfinite(qgas) or qgas < 0 or not np.all(np.isfinite(inventories)):
            raise ValueError("native gas outflow/inventory is nonfinite or reverse; no host clipping")
        pressure = float(self.native_reactor.headspace_P * 1e5)
        if not 0 < pressure <= self.audit.maximum_pressure_pa:
            raise ValueError(f"native absolute pressure {pressure} outside declared audit domain")
        h2 = self._ids.index("S_h2")
        i_mass = self.native_components.i_mass[h2]
        liquid_h2 = self.geometry.liquid_volume_m3 * state[h2] * i_mass
        gas_h2 = (self.geometry.headspace_volume_m3 * state[n]
                  * self.native_components.chem_MW[h2])
        return BiologicalPoint(t, pressure, float(qgas),
                               MappingProxyType(dict(zip(self._ids, map(float, inventories)))),
                               float(liquid_h2), float(gas_h2), tuple(map(float, state)))

    def _balance(self, times: np.ndarray, states: np.ndarray,
                 points: list[BiologicalPoint]) -> BiologicalBalance:
        from scipy.integrate import cumulative_simpson

        n = len(self._ids)
        count = len(times)
        cin = np.asarray(self.native_feed.state[:-1]) * 1e-3
        qin = self.native_feed.state[-1] / 86400
        inlet = np.tile(cin * qin, (count, 1))
        liquid_out = states[:, :n] * qin
        gas_out = np.zeros((count, n))
        reaction = np.empty((count, n))
        formed = np.empty(count)
        consumed = np.empty(count)
        dry_moles = np.empty((count, 3))
        h2 = self._ids.index("S_h2")
        for i, (point, state) in enumerate(zip(points, states)):
            rates = np.array(self.native_model.rate_function(np.r_[state, self.geometry.temperature_k]),
                             dtype=float, copy=True)
            if rates.shape != (22,) or not np.all(np.isfinite(rates)):
                raise ValueError("native rate vector is nonfinite or has an unsupported shape")
            biochemical_h2 = self._matrix[:-3, h2] * rates[:-3]
            factor = self.geometry.liquid_volume_m3 / 86400
            reaction[i] = self._matrix[:-3].T @ rates[:-3] * factor
            formed[i] = np.maximum(biochemical_h2, 0).sum() * factor
            consumed[i] = -np.minimum(biochemical_h2, 0).sum() * factor
            dry_moles[i] = point.gas_outflow_m3_s * state[n:-1] * 1000
            gas_out[i, self._gas_indices] = (point.gas_outflow_m3_s * state[n:-1]
                                             / self._conversion[self._gas_indices])
        def integrate(values: np.ndarray) -> np.ndarray:
            if not np.all(np.isfinite(values)):
                raise ValueError("native ledger input is nonfinite")
            integral = cumulative_simpson(values, x=times, axis=0, initial=0)
            if not np.all(np.isfinite(integral)):
                raise ValueError("sampled native ledger quadrature is nonfinite")
            return integral

        inlet_i, liquid_i, gas_i, reaction_i = map(integrate, (inlet, liquid_out, gas_out, reaction))
        inventory = np.array([[p.measured_inventories_kg[k] for k in self._ids] for p in points])
        residual = inventory - inventory[0] - inlet_i + liquid_i + gas_i - reaction_i
        if not np.all(np.isfinite(residual)):
            raise ValueError("native component ledger residual is nonfinite")
        comp_error = np.max(np.abs(residual), axis=0)
        scale = np.max(np.abs(inventory), axis=0)
        if np.any(comp_error > self.audit.component_absolute_tolerance_kg
                  + self.audit.relative_tolerance * scale):
            failures = {k: float(err) for k, err, size in zip(self._ids, comp_error, scale)
                        if err > self.audit.component_absolute_tolerance_kg
                        + self.audit.relative_tolerance * size}
            raise ValueError(f"native component/sample-ledger defect exceeds budget: {failures}")
        boundary_residual = inventory - inventory[0] - inlet_i + liquid_i + gas_i
        invariant_errors = {}
        for name, weights in (("COD", self.native_components.i_COD),
                              ("C", self.native_components.i_C), ("N", self.native_components.i_N)):
            weights = np.asarray(weights)
            if not np.all(np.isfinite(weights)):
                raise ValueError(f"native {name} component weights are nonfinite")
            if np.max(np.abs(self._matrix[:-3] @ weights)) > 1e-9:
                raise ValueError(f"native biochemical matrix does not conserve declared {name} basis")
            error = float(np.max(np.abs(boundary_residual @ weights)))
            inv_scale = float(np.max(np.abs(inventory @ weights)))
            if not (isfinite(error) and isfinite(inv_scale)):
                raise ValueError(f"native {name} invariant ledger is nonfinite")
            if error > (self.audit.invariant_absolute_tolerance_kg
                        + self.audit.relative_tolerance * inv_scale):
                raise ValueError(f"independent native {name} boundary inventory exceeds budget: {error:.8g}")
            invariant_errors[name] = error
        exported = integrate(dry_moles)[-1]
        total = float(exported.sum())
        native_h2_mass_factor = self.native_components.i_mass[h2]
        def mapping(values: np.ndarray) -> Mapping[str, float]:
            return MappingProxyType(dict(zip(self._ids, map(float, values))))

        return BiologicalBalance(mapping(comp_error), MappingProxyType(invariant_errors),
                                 mapping(inlet_i[-1]), mapping(liquid_i[-1]), mapping(gas_i[-1]),
                                 mapping(reaction_i[-1]), float(integrate(formed)[-1] * native_h2_mass_factor),
                                 float(integrate(consumed)[-1] * native_h2_mass_factor),
                                 float(gas_i[-1, h2] * native_h2_mass_factor),
                                 float(comp_error[h2] * native_h2_mass_factor),
                                 float(exported[0] / total) if total > 0 else None)
