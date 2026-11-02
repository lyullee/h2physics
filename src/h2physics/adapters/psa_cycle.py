"""Actual native warm multibed PSA execution with conserved slot checkpoints.

The pinned PSA-Dyna runner owns schedules, valves, bed equations and all
integration. Its only integration entry point is file-oriented; the public host
API takes Python objects and uses an explicit temporary native I/O bridge.
No native source is copied and no runner globals are patched.
"""

import hashlib
import importlib
import json
import tempfile
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np


from ..adsorption import AdsorptionBasis, AdsorptionDomain
from ..core import immutable_array, Origin, finite
from .psa import PsaDynaBed


def _array(value):
    result = np.array(value, dtype=float, copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError("Native cycle state/ledger must be finite")
    result = immutable_array(result, name="result")
    return result


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


_PENDING_PSA_CYCLE_RUN_ISSUERS: set[object] = set()


def _freeze_run_value(value):
    if isinstance(value, np.ndarray):
        return ("array", value.dtype.str, value.shape,
                hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest())
    if isinstance(value, Mapping):
        return ("mapping", tuple((repr(key), _freeze_run_value(item))
                                 for key, item in sorted(value.items(), key=lambda pair: repr(pair[0]))))
    if isinstance(value, (tuple, list)):
        return (type(value).__name__, tuple(_freeze_run_value(item) for item in value))
    if value is None or type(value) in (str, int, float, bool):
        return (type(value).__name__, repr(value))
    fields = getattr(type(value), "__dataclass_fields__", None)
    if fields is not None:
        return ("dataclass", type(value).__module__, type(value).__qualname__,
                tuple((name, _freeze_run_value(getattr(value, name)))
                      for name, field_info in fields.items() if field_info.init))
    return ("object", type(value).__module__, type(value).__qualname__, id(value))


@dataclass(frozen=True, slots=True)
class PsaCycleNative:
    core: Any
    schedules: Any
    runner: Any
    source_id: str

    @classmethod
    def from_installed(cls, *, source_id):
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("Declare the separately installed native source identity")
        return cls(*(importlib.import_module("psa_dynamic."+name)
                     for name in ("core", "schedules", "runner")), source_id)


@dataclass(frozen=True, slots=True)
class PsaCycleEvidence:
    source_id: str
    energy_reference_id: str
    gas_phase_scope_id: str
    parameter_origin: Origin
    component_absolute_tolerance_mol: float = 1e-8
    energy_absolute_tolerance_j: float = 1e-4

    def __post_init__(self):
        if any(not isinstance(x, str) or not x.strip() for x in
               (self.source_id, self.energy_reference_id, self.gas_phase_scope_id)):
            raise ValueError("Declare source, native energy zero and warm gas phase evidence")
        object.__setattr__(self, "parameter_origin", Origin(self.parameter_origin))
        if self.parameter_origin == Origin.UNRESOLVED:
            raise ValueError("Unresolved parameters cannot define a PSA cycle")
        finite(self.component_absolute_tolerance_mol, "component budget", positive=True)
        finite(self.energy_absolute_tolerance_j, "energy budget", positive=True)


@dataclass(frozen=True, slots=True)
class PsaCyclePoint:
    time_s: float
    native_elapsed_s: float
    completed_cycles: int
    completed_slots_in_cycle: int
    native_state: np.ndarray
    beds: tuple
    inventory_mol: np.ndarray
    stored_energy_j: float
    feed_mol: np.ndarray
    product_mol: np.ndarray
    tail_mol: np.ndarray
    feed_enthalpy_j: float
    product_enthalpy_j: float
    tail_enthalpy_j: float
    ambient_heat_j: float
    vacuum_work_j: float
    component_residual_mol: np.ndarray
    energy_residual_j: float

    def __post_init__(self):
        for name in ("native_state", "inventory_mol", "feed_mol", "product_mol", "tail_mol",
                     "component_residual_mol"):
            object.__setattr__(self, name, _array(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class PsaCycleTotals:
    species: tuple[str, ...]
    feed_mol: np.ndarray
    product_mol: np.ndarray
    tail_mol: np.ndarray
    hydrogen_product_purity: float | None
    hydrogen_product_to_feed_ratio: float | None
    css_hydrogen_recovery: float | None

    def __post_init__(self):
        for name in ("feed_mol", "product_mol", "tail_mol"):
            object.__setattr__(self, name, _array(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class PsaCycleRun:
    points: tuple[PsaCyclePoint, ...]
    totals: PsaCycleTotals
    final_cycle_totals: PsaCycleTotals
    native_result: Mapping
    native_call_results: tuple
    native_checkpoint_metadata: Mapping
    native_schedule: Mapping
    audit_network: Any
    bed_adapter: PsaDynaBed
    native_bindings: PsaCycleNative
    case_parameters: Mapping
    evidence: PsaCycleEvidence
    basis: AdsorptionBasis
    domain: AdsorptionDomain
    clock_id: str
    start_time_s: float
    input_sha256: str
    native_code_sha256: str
    original_integrator_objects_available: bool = False
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_PSA_CYCLE_RUN_ISSUERS:
            raise ValueError("PSA cycle runs are issued only by PsaDynaCycle.run")
        _PENDING_PSA_CYCLE_RUN_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "points", tuple(self.points))
        object.__setattr__(self, "native_call_results", tuple(self.native_call_results))
        if not self.points or not self.clock_id or not self.input_sha256 or not self.native_code_sha256:
            raise ValueError("Issued PSA cycle run must retain its native input and checkpoints")
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self):
        try:
            network_case = self.audit_network.case
            native_code = self.native_bindings.runner.code_hash()
        except Exception as error:
            raise ValueError("Native PSA cycle owner is no longer inspectable") from error
        payload = (
            _freeze_run_value((self.points, self.totals, self.final_cycle_totals,
                               self.native_result, self.native_call_results,
                               self.native_checkpoint_metadata, self.native_schedule,
                               self.case_parameters)),
            id(self.audit_network), _freeze_run_value(network_case),
            id(self.bed_adapter), id(self.bed_adapter.native_bed),
            id(self.native_bindings), self.native_bindings.source_id, native_code,
            id(self.evidence), _freeze_run_value(self.evidence),
            id(self.basis), _freeze_run_value(self.basis),
            id(self.domain), _freeze_run_value(self.domain),
            self.clock_id, self.start_time_s, self.input_sha256, self.native_code_sha256,
            self.original_integrator_objects_available,
        )
        return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()

    def require_current(self):
        if self._fingerprint() != self._seal:
            raise ValueError("Native PSA cycle result changed after issuance")
        return self


class PsaCycleError(RuntimeError):
    def __init__(self, message, *, native_result=None, native_checkpoint_metadata=None,
                 native_state=None, audited_points=(), audit_network=None,
                 native_failure_record=None):
        self.native_result = native_result
        self.native_checkpoint_metadata = native_checkpoint_metadata
        self.native_state = None if native_state is None else _array(native_state)
        self.audited_points = tuple(audited_points)
        self.audit_network = audit_network
        self.native_failure_record = native_failure_record
        super().__init__(message)


class PsaDynaCycle:
    """Native scheduled multibed run; native original solver objects are not exposed.

    A separate actual Network performs admission/snapshot/inventory audits and
    is labeled audit_network. The runner's internal Network/OdeResult cannot be
    retained through the pinned API. Returned checkpoint arrays are the actual
    native serialized states, never surrogate trajectories.
    """

    def __init__(self, native: PsaCycleNative, case: Mapping, *, basis: AdsorptionBasis,
                 domain: AdsorptionDomain, evidence: PsaCycleEvidence,
                 temporary_workspace: str | Path):
        self.native, self.basis, self.domain, self.evidence = native, basis, domain, evidence
        if not isinstance(native.source_id, str) or not native.source_id.strip():
            raise ValueError("Declare actual native source identity")
        self._case = deepcopy(dict(case))
        self._input_bytes = _bytes(self._case)
        self.input_sha256 = hashlib.sha256(self._input_bytes).hexdigest()
        self.workspace = Path(temporary_workspace).resolve()
        if not self.workspace.is_dir():
            raise ValueError("Supply an existing explicit ignored temporary workspace")
        self.schedule = native.schedules.build_schedule(deepcopy(self._case["schedule"]))
        if (not self.schedule.get("timing_inputs_unambiguous")
                or not self.schedule.get("cycle_time_consistent")):
            raise ValueError("Native cycle timing inputs must be unambiguous and consistent")
        self.audit_network = native.core.Network(deepcopy(self._case), deepcopy(self.schedule))
        network = self.audit_network
        order = tuple(item["name"] for item in network.species)
        if order != basis.species or "H2" not in order or len(set(order)) != len(order):
            raise ValueError("Declare the exact native species order including H2")
        if network.reporting_species != "H2":
            raise ValueError("This H2 metric interface requires native reporting_species='H2'")
        if (network.nb < 2 or network.receiver is not None
                or network.bed.energy_mode != "internal_energy"
                or network.bed.equation_of_state != "ideal_gas"
                or network.bed.wall_model != "dynamic_lumped"
                or self._case.get("boundary_mode") not in {None, "fixed_inlet_valve_outlet"}):
            raise ValueError("This first cycle level requires warm multibed ideal-gas/loading storage, dynamic walls and native valve boundaries")
        if domain.minimum_temperature_k <= 100. or domain.maximum_temperature_k >= 1000.:
            raise ValueError("Declare a warm domain strictly inside native 100–1000K bounds")
        solver = self._case["solver"]
        if (solver.get("ledger_integration") != "augmented" or solver.get("negative_tolerance") != 0.
                or not solver.get("record_trace") or solver.get("maximum_cycles", 0) < 1):
            raise ValueError("Require explicit augmented native ledgers, strict accepted positivity, trace and finite cycle limit")
        for key in ("maximum_cycles", "minimum_cycles", "css_consecutive_cycles"):
            value = solver[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Native cycle/count controls must be explicit positive integers")
        for key in ("rtol", "max_step_s", "css_tolerance", "mass_balance_tolerance", "energy_balance_tolerance"):
            finite(solver[key], key, positive=True)
        if "initial_process_state" in self._case:
            raise ValueError("Seeded native process states need a separate admitted restart contract")
        for name in ("cp", "cv", "mw", "vgas", "mass", "thermal_cs", "cwall"):
            values = np.asarray(getattr(network.bed, name))
            if not np.all(np.isfinite(values)) or np.any(values <= 0):
                raise ValueError("Native gas/caloric/geometry storage parameters must be finite and positive")
        domain.require_state(np.asarray(network.yfeed)*network.feed["pressure_bar"]*1e5,
                             network.feed["temperature_k"])
        self.bed = PsaDynaBed(network.bed, basis, domain, energy_reference_id=evidence.energy_reference_id)
        self._audit_case_hash = _hash(network.case)
        self._schedule_hash = _hash(self.schedule)
        self._admit(network.initial())

    def case_parameters(self):
        return deepcopy(self._case)

    def _admit(self, state):
        network = self.audit_network
        raw = np.asarray(state, dtype=float)
        if raw.shape != (network.size,) or not np.all(np.isfinite(raw)):
            raise ValueError("Native checkpoint dimensions/finiteness differ from the admitted Network")
        return tuple(self.bed.snapshot(raw[i*network.bed.size:(i+1)*network.bed.size])
                     for i in range(network.nb))

    def _point(self, state, elapsed, cycles, slots, start, initial=None):
        network = self.audit_network
        beds = self._admit(state)
        inventory = sum((bed.total_inventory_mol for bed in beds), np.zeros(network.ns))
        energy = sum(bed.stored_energy_j for bed in beds)
        ledger = np.asarray(state[network.process_size:])
        ns = network.ns
        feed, product, tail = ledger[:ns], ledger[ns:2*ns], ledger[2*ns:3*ns]
        if np.any(ledger[:3*ns] < 0):
            raise ValueError("Native external stream component integrals cannot be silently clipped")
        heat_terms = ledger[3*ns:]
        if initial is None:
            component_error = np.zeros(ns)
            energy_error = 0.
        else:
            component_error = inventory-initial.inventory_mol-feed+product+tail
            energy_error = energy-initial.stored_energy_j-heat_terms[0]+heat_terms[1]+heat_terms[2]-heat_terms[3]
        point = PsaCyclePoint(start+elapsed, elapsed, cycles, slots, state, beds, inventory, energy,
            feed, product, tail, *heat_terms, component_error, energy_error)
        if (np.max(abs(point.component_residual_mol)) > self.evidence.component_absolute_tolerance_mol
                or abs(point.energy_residual_j) > self.evidence.energy_absolute_tolerance_j):
            raise ValueError("Native checkpoint component/energy boundary audit failed")
        return point

    def _totals(self, feed, product, tail, *, css):
        index = self.basis.species.index("H2")
        purity = float(product[index]/sum(product)) if sum(product) > 0 else None
        ratio = float(product[index]/feed[index]) if feed[index] > 0 else None
        return PsaCycleTotals(self.basis.species, feed, product, tail, purity, ratio, ratio if css else None)

    def run(self, *, start_time_s: float, clock_id: str) -> PsaCycleRun:
        start = finite(start_time_s, "absolute PSA clock start")
        if not isinstance(clock_id, str) or not clock_id.strip():
            raise ValueError("Declare the PSA operation clock")
        if _hash(self.audit_network.case) != self._audit_case_hash or _hash(self.schedule) != self._schedule_hash:
            raise ValueError("The admitted native audit Network/schedule definition changed")
        points, calls = [], []
        result = metadata = state = failure_record = None
        engine_hash = self.native.runner.code_hash()
        try:
            with tempfile.TemporaryDirectory(prefix="psa-cycle-", dir=self.workspace) as directory:
                directory = Path(directory)
                input_path, output = directory/"case.json", directory/"native-output"
                input_path.write_bytes(self._input_bytes)
                maximum_calls = int(self._case["solver"]["maximum_cycles"])*(len(self.schedule["slots"])+1)
                for _ in range(maximum_calls):
                    try:
                        result = self.native.runner.run_case(input_path, output, resume=True,
                                                             cycle_budget=1, step_budget=1)
                    except Exception:
                        failure_path = output/"failure.json"
                        if failure_path.is_file():
                            failure_record = json.loads(failure_path.read_text(encoding="utf-8"))
                        raise
                    calls.append(deepcopy(result))
                    metadata = json.loads((output/"checkpoint.json").read_text(encoding="utf-8"))
                    state_path = output/metadata["state_file"]
                    if hashlib.sha256(state_path.read_bytes()).hexdigest() != metadata["state_sha256"]:
                        raise ValueError("Native checkpoint bytes fail the native recorded SHA256")
                    with np.load(state_path, allow_pickle=False) as saved:
                        state = np.array(saved["state"], copy=True)
                    if (metadata["input_sha256"] != self.input_sha256
                            or metadata["code_sha256"] != engine_hash
                            or result["input_sha256"] != self.input_sha256
                            or result["code_sha256"] != engine_hash):
                        raise ValueError("Native runner case/code identity differs from the admitted inputs")
                    if not points:
                        actual_initial = np.asarray(metadata["cycle_start_state"], dtype=float)
                        if not np.array_equal(actual_initial, self.audit_network.initial()):
                            raise ValueError("Native original initial state differs from the independent admission Network")
                        points.append(self._point(actual_initial, 0., 0, 0, start))
                    cycles, slots = metadata["cycle_index"], metadata["slot_index"]
                    elapsed = cycles*self.schedule["cycle_time_s"]+sum(
                        slot["duration_s"] for slot in self.schedule["slots"][:slots])
                    if elapsed > points[-1].native_elapsed_s:
                        point = self._point(state, elapsed, cycles, slots, start, points[0])
                        points.append(point)
                    elif not np.array_equal(state, points[-1].native_state):
                        raise ValueError("Native cycle finalization changed state without advancing its clock")
                    for row in metadata["step_rows"]:
                        for bed in range(self.audit_network.nb):
                            if (row[f"bed{bed+1}_temperature_min_k"] < self.domain.minimum_temperature_k
                                    or row[f"bed{bed+1}_temperature_max_k"] > self.domain.maximum_temperature_k
                                    or row[f"bed{bed+1}_wall_temperature_min_k"] < self.domain.minimum_temperature_k
                                    or row[f"bed{bed+1}_wall_temperature_max_k"] > self.domain.maximum_temperature_k):
                                raise ValueError("Native accepted BDF-node temperature leaves the declared domain")
                    for material in metadata["trajectory_extrema"].values():
                        if (material["pressure_min_bar"]*1e5 < self.domain.minimum_total_pressure_pa
                                or material["pressure_max_bar"]*1e5 > self.domain.maximum_total_pressure_pa):
                            raise ValueError("Native accepted BDF-node pressure leaves the declared domain")
                    if (result["state_css_converged"]
                            or metadata["cycle_index"] >= self._case["solver"]["maximum_cycles"]):
                        break
                else:
                    raise ValueError("Native step/cycle budget did not complete the declared finite run")
                if self.native.runner.code_hash() != engine_hash:
                    raise ValueError("Native engine source changed during the run")
            last = points[-1]
            totals = self._totals(last.feed_mol, last.product_mol, last.tail_mol, css=False)
            final = result["final_cycle"]
            if final is None:
                raise ValueError("The native runner did not finalize a complete physical cycle")
            final_totals = self._totals(np.array(final["feed_by_component_mol"]),
                np.array(final["product_by_component_mol"]), np.array(final["tail_by_component_mol"]),
                css=bool(result["state_css_converged"]))
            if _hash(self.audit_network.case) != self._audit_case_hash or _hash(self.schedule) != self._schedule_hash:
                raise ValueError("The admitted native audit Network/schedule changed during execution")
            issuer_token = object()
            _PENDING_PSA_CYCLE_RUN_ISSUERS.add(issuer_token)
            try:
                return PsaCycleRun(
                    points=tuple(points), totals=totals, final_cycle_totals=final_totals,
                    native_result=MappingProxyType(deepcopy(result)),
                    native_call_results=tuple(calls),
                    native_checkpoint_metadata=MappingProxyType(deepcopy(metadata)),
                    native_schedule=MappingProxyType(deepcopy(self.schedule)),
                    audit_network=self.audit_network, bed_adapter=self.bed, native_bindings=self.native,
                    case_parameters=MappingProxyType(deepcopy(self._case)), evidence=self.evidence,
                    basis=self.basis, domain=self.domain, clock_id=clock_id, start_time_s=start,
                    input_sha256=self.input_sha256, native_code_sha256=engine_hash,
                    _issuer_token=issuer_token)
            except Exception:
                _PENDING_PSA_CYCLE_RUN_ISSUERS.discard(issuer_token)
                raise
        except Exception as error:
            raise PsaCycleError(f"Native PSA cycle failed: {error}", native_result=result,
                native_checkpoint_metadata=metadata, native_state=state, audited_points=points,
                audit_network=self.audit_network, native_failure_record=failure_record) from error
