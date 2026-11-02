"""Typed access to the optional native HyRAM+ ignition-probability kernel.

This adapter does not reproduce the kernel or add an independent correlation.
Its output is an absolute probability relative to one release, as HyRAM defines
it; it is not a conditional probability conditioned on ignition.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import inspect
from dataclasses import dataclass
from pathlib import Path

from ..core import Origin, finite


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _nonnegative(value: float, name: str) -> float:
    number = finite(value, name)
    if number < 0:
        raise ValueError(f"{name} cannot be negative")
    return number


@dataclass(frozen=True, slots=True)
class HyRAMIgnitionTable:
    """Explicit release-rate threshold table passed to the native HyRAM kernel.

    Thresholds use kg/s and divide ``len(thresholds) + 1`` bins. The immediate
    and delayed probabilities are each relative to a release, and their sum
    must not exceed one. Values and their evidentiary basis remain caller-owned.
    """

    table_id: str
    fuel_species: str
    flow_thresholds_kg_s: tuple[float, ...]
    immediate_probability: tuple[float, ...]
    delayed_probability: tuple[float, ...]
    evidence_id: str
    origin: Origin

    def __post_init__(self):
        _identity(self.table_id, "ignition table identity")
        species = _identity(self.fuel_species, "HyRAM fuel species")
        if species.lower() not in {"h2", "hydrogen"}:
            raise ValueError("This adapter is scoped to hydrogen release probabilities")
        thresholds = tuple(_nonnegative(v, "flow threshold")
                           for v in self.flow_thresholds_kg_s)
        immediate = tuple(_nonnegative(v, "immediate ignition probability")
                          for v in self.immediate_probability)
        delayed = tuple(_nonnegative(v, "delayed ignition probability")
                        for v in self.delayed_probability)
        if not thresholds:
            raise ValueError("Supply at least one flow threshold for the native HyRAM lookup")
        if any(b <= a for a, b in zip(thresholds, thresholds[1:])):
            raise ValueError("Flow thresholds must be strictly increasing")
        if len(immediate) != len(thresholds) + 1 or len(delayed) != len(thresholds) + 1:
            raise ValueError("Each probability vector must have one entry per rate bin")
        if any(p > 1 for p in immediate + delayed) or any(a + b > 1 for a, b in zip(immediate, delayed)):
            raise ValueError("Release-relative ignition probabilities must sum to at most one")
        object.__setattr__(self, "fuel_species", species)
        object.__setattr__(self, "flow_thresholds_kg_s", thresholds)
        object.__setattr__(self, "immediate_probability", immediate)
        object.__setattr__(self, "delayed_probability", delayed)
        object.__setattr__(self, "evidence_id", _identity(self.evidence_id, "table evidence identity"))
        origin = Origin(self.origin)
        if origin == Origin.UNRESOLVED:
            raise ValueError("Resolve the input table origin")
        object.__setattr__(self, "origin", origin)

    def as_native_mapping(self) -> dict[str, list[float]]:
        """Return a fresh mapping in the documented HyRAM+ QRA input shape."""
        return {
            "flow_thresholds": list(self.flow_thresholds_kg_s),
            "immed_ign_probs": list(self.immediate_probability),
            "delayed_ign_probs": list(self.delayed_probability),
        }

    @property
    def content_sha256(self) -> str:
        payload = repr((self.table_id, self.fuel_species, self.flow_thresholds_kg_s,
                        self.immediate_probability, self.delayed_probability,
                        self.evidence_id, self.origin)).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class HyRAMIgnitionProbability:
    """Owner-linked result from the currently installed HyRAM+ native routine."""

    table: HyRAMIgnitionTable
    release_rate_kg_s: float
    immediate_probability: float
    delayed_probability: float
    total_probability: float
    hyram_version: str
    native_module_sha256: str
    native_module_path: str
    probability_basis: str = "each ignition class relative to a hydrogen release"

    def __post_init__(self):
        if not isinstance(self.table, HyRAMIgnitionTable):
            raise TypeError("Retain the explicit HyRAM ignition table")
        rate = _nonnegative(self.release_rate_kg_s, "hydrogen release rate")
        immediate = _nonnegative(self.immediate_probability, "immediate probability")
        delayed = _nonnegative(self.delayed_probability, "delayed probability")
        total = _nonnegative(self.total_probability, "total ignition probability")
        if immediate > 1 or delayed > 1 or total > 1:
            raise ValueError("Native ignition probability is outside [0, 1]")
        if abs(total - (immediate + delayed)) > 1e-14:
            raise ValueError("Total probability must equal the two release-relative branches")
        _identity(self.hyram_version, "HyRAM+ version")
        if (len(self.native_module_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.native_module_sha256)):
            raise ValueError("Retain the lowercase SHA-256 of the native kernel source")
        _identity(self.native_module_path, "native kernel module path")
        object.__setattr__(self, "release_rate_kg_s", rate)


def evaluate_hyram_ignition_probability(
        release_rate_kg_s: float, *, table: HyRAMIgnitionTable) -> HyRAMIgnitionProbability:
    """Evaluate the exact native HyRAM+ rate-bin kernel using an explicit table.

    The HyRAM+ dependency is optional and imported only on invocation. This
    narrow function avoids the full QRA workflow and its separate component
    leak, detection, consequence, harm and frequency assumptions. The rate is
    supplied by the caller; it is not recomputed from an orifice or inventory.
    """
    if not isinstance(table, HyRAMIgnitionTable):
        raise TypeError("Supply a typed, evidence-bound hydrogen ignition table")
    rate = _nonnegative(release_rate_kg_s, "hydrogen release rate")
    kernel = importlib.import_module("hyram.qra.ignition_probs")
    function = getattr(kernel, "get_ignition_probability", None)
    if not callable(function):
        raise RuntimeError("Installed HyRAM+ has no supported ignition probability kernel")
    if tuple(inspect.signature(function).parameters)[:2] != ("mass_flow_rate", "ign_probs"):
        raise RuntimeError("Installed HyRAM+ ignition kernel signature is not supported")
    source_path = inspect.getsourcefile(function)
    if not source_path:
        raise RuntimeError("Cannot identify the loaded HyRAM+ probability implementation")
    module_path = Path(source_path).resolve()
    module_sha256 = hashlib.sha256(module_path.read_bytes()).hexdigest()
    immediate, delayed = function(rate, table.as_native_mapping())
    immediate = _nonnegative(immediate, "native immediate ignition probability")
    delayed = _nonnegative(delayed, "native delayed ignition probability")
    if immediate > 1 or delayed > 1 or immediate + delayed > 1:
        raise ValueError("HyRAM+ returned probabilities outside the admissible release basis")
    version = importlib.metadata.version("hyram")
    return HyRAMIgnitionProbability(table, rate, immediate, delayed,
        immediate + delayed, version, module_sha256, str(module_path))


def hyram_default_hydrogen_ignition_table() -> HyRAMIgnitionTable:
    """Capture the currently installed HyRAM+ default hydrogen rate table.

    The returned content hash and provider version identify the captured values;
    callers needing another release or facility basis should provide their own
    evidence-bound ``HyRAMIgnitionTable`` instead.
    """
    defaults = importlib.import_module("hyram.qra.defaults")
    function = getattr(defaults, "get_default_ignition_probs", None)
    if not callable(function):
        raise RuntimeError("Installed HyRAM+ has no supported default ignition table")
    native = function("h2")
    version = importlib.metadata.version("hyram")
    return HyRAMIgnitionTable(
        table_id=f"hyram-default-hydrogen-ignition:{version}",
        fuel_species="h2",
        flow_thresholds_kg_s=tuple(native["flow_thresholds"]),
        immediate_probability=tuple(native["immed_ign_probs"]),
        delayed_probability=tuple(native["delayed_ign_probs"]),
        evidence_id=f"HyRAM+ {version} native default table:h2",
        origin=Origin.PREDICTED,
    )


__all__ = ["HyRAMIgnitionTable", "HyRAMIgnitionProbability",
           "evaluate_hyram_ignition_probability", "hyram_default_hydrogen_ignition_table"]
