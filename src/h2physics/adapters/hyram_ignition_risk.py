"""Bind typed HyRAM ignition outputs to the existing conditional-risk branches.

This is an object adapter only: it neither loads HyRAM nor evaluates risk.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from ..core import Origin, finite
from .conditional_risk import ConditionalHarmBinding, ConditionalRiskNative
from .hyram_ignition import HyRAMIgnitionProbability

_OUTCOMES = ("no_ignition", "immediate_ignition", "delayed_ignition")
_PENDING = {}


def _issue_binding_token(values):
    token = object()
    _PENDING[token] = tuple(id(value) for value in values)
    return token


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _probability(value: float, name: str) -> float:
    number = finite(value, name)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be finite and lie in [0, 1]")
    return number


def _nonnegative(value: float, name: str) -> float:
    number = finite(value, name)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _lineage_digest(*, table_id, table_evidence_id, table_sha256, release_rate_kg_s,
                    immediate_probability, delayed_probability, total_probability,
                    hyram_version, native_module_path, native_module_sha256,
                    partition_evidence_id, outcome_branch_ids, outcome_probabilities):
    payload = (
        table_id, table_evidence_id, table_sha256, release_rate_kg_s,
        immediate_probability, delayed_probability, total_probability,
        hyram_version, native_module_path, native_module_sha256,
        partition_evidence_id,
        tuple((outcome, outcome_branch_ids[outcome], outcome_probabilities[outcome])
              for outcome in _OUTCOMES),
    )
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class HyRAMIgnitionRiskBinding:
    """Risk request and lineage for one explicit no/immediate/delayed LOC split.

    HyRAM ignition outputs are release-relative probabilities. They become
    mutually exclusive conditional-on-LOC branches only when paired with the
    caller's explicit LOC frequency. This value binding is not a signature that
    authenticates the upstream HyRAM evaluation.
    """

    request: Any
    frequency: Any
    receptor_id: str
    partition_evidence_id: str
    outcome_branch_ids: Mapping[str, str]
    outcome_probabilities: Mapping[str, float]
    probability_factor_ids: Mapping[str, tuple[str, ...]]
    harm_bindings: Mapping[str, ConditionalHarmBinding]
    table_id: str
    table_evidence_id: str
    table_sha256: str
    release_rate_kg_s: float
    total_probability: float
    hyram_version: str
    native_module_path: str
    native_module_sha256: str
    origin: Origin
    lineage_sha256: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _frequency_identity: int = field(init=False, repr=False, compare=False)
    _request_digest: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        expected = tuple(id(value) for value in (
            self.request, self.frequency, self.outcome_branch_ids,
            self.outcome_probabilities, self.probability_factor_ids,
            self.harm_bindings,
        ))
        if _PENDING.get(self._issuer) != expected:
            raise TypeError("Create an ignition-risk binding through its producer")
        _PENDING.pop(self._issuer)
        if not callable(getattr(self.request, "digest", None)):
            raise TypeError("request must retain an actual native risk input")
        _text(self.receptor_id, "risk receptor identity")
        _text(self.partition_evidence_id, "partition evidence identity")
        branch_ids = dict(self.outcome_branch_ids)
        probabilities = {k: _probability(v, f"{k} branch probability")
                         for k, v in self.outcome_probabilities.items()}
        factor_ids = {k: tuple(v) for k, v in self.probability_factor_ids.items()}
        harms = dict(self.harm_bindings)
        if set(branch_ids) != set(_OUTCOMES) or set(probabilities) != set(_OUTCOMES):
            raise ValueError("Retain all three explicit ignition outcomes")
        if set(factor_ids) != set(_OUTCOMES):
            raise ValueError("Retain probability-factor IDs for all outcomes")
        if not math.isclose(math.fsum(probabilities.values()), 1.0,
                            rel_tol=0.0, abs_tol=1e-14):
            raise ValueError("The three branches must partition one LOC event")
        if len(set(branch_ids.values())) != len(_OUTCOMES):
            raise ValueError("Outcome branch IDs must be distinct")
        if set(harms) != set(branch_ids.values()):
            raise ValueError("Retain one explicit harm binding per risk branch")
        for outcome in _OUTCOMES:
            _text(branch_ids[outcome], f"{outcome} branch ID")
            ids = tuple(_text(item, f"{outcome} probability factor ID")
                        for item in factor_ids[outcome])
            if not ids or len(set(ids)) != len(ids):
                raise ValueError(f"{outcome} needs unique probability-factor IDs")
            factor_ids[outcome] = ids
        for harm in harms.values():
            if type(harm) is not ConditionalHarmBinding:
                raise TypeError("Retain the exact typed ConditionalHarmBinding per branch")
            harm.require_current()
        _text(self.table_id, "HyRAM table identity")
        _text(self.table_evidence_id, "HyRAM table evidence identity")
        _text(self.hyram_version, "HyRAM package version")
        _text(self.native_module_path, "HyRAM native module path")
        for label, digest in (("table", self.table_sha256),
                              ("HyRAM native module", self.native_module_sha256),
                              ("risk lineage", self.lineage_sha256)):
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)):
                raise ValueError(f"Retain a lowercase SHA-256 for {label}")
        rate = _nonnegative(self.release_rate_kg_s, "release rate kg/s")
        object.__setattr__(self, "release_rate_kg_s", rate)
        object.__setattr__(self, "origin", Origin(self.origin))
        object.__setattr__(self, "outcome_branch_ids", MappingProxyType(branch_ids))
        object.__setattr__(self, "outcome_probabilities", MappingProxyType(probabilities))
        object.__setattr__(self, "probability_factor_ids", MappingProxyType(factor_ids))
        object.__setattr__(self, "harm_bindings", MappingProxyType(harms))
        object.__setattr__(self, "_frequency_identity", id(self.frequency))
        object.__setattr__(self, "_request_digest", self.request.digest())
        self.require_current()

    def require_current(self):
        if id(self.frequency) != self._frequency_identity:
            raise ValueError("Caller-owned LOC frequency object was replaced")
        if self.request.digest() != self._request_digest:
            raise ValueError("Native branch request changed after ignition binding")
        if getattr(self.request, "frequency", None) is not self.frequency:
            raise ValueError("The handoff did not retain the exact LOC frequency object")
        if (self.request.receptor_id != self.receptor_id
                or self.request.partition_basis != self.partition_evidence_id):
            raise ValueError("Native request lost its declared receptor or partition evidence")
        branches = {branch.id: branch for branch in self.request.branches}
        if set(branches) != set(self.harm_bindings):
            raise ValueError("Native risk branches and retained harm bindings differ")
        for outcome in _OUTCOMES:
            branch = branches[self.outcome_branch_ids[outcome]]
            harm = self.harm_bindings[branch.id]
            harm.require_current()
            if (branch.conditional_probability != self.outcome_probabilities[outcome]
                    or branch.probability_basis != self.partition_evidence_id
                    or tuple(branch.probability_factor_ids)
                    != self.probability_factor_ids[outcome]
                    or branch.harm_probability != harm.probability
                    or branch.harm_basis != harm.response_model_id):
                raise ValueError("Native branch differs from its explicit probability/harm binding")
        immediate = self.outcome_probabilities["immediate_ignition"]
        delayed = self.outcome_probabilities["delayed_ignition"]
        total = _probability(self.total_probability, "total ignition probability")
        if not math.isclose(total, math.fsum((immediate, delayed)), rel_tol=0., abs_tol=1e-14):
            raise ValueError("Stored total does not close immediate/delayed outcomes")
        expected_lineage = _lineage_digest(
            table_id=self.table_id,
            table_evidence_id=self.table_evidence_id,
            table_sha256=self.table_sha256,
            release_rate_kg_s=self.release_rate_kg_s,
            immediate_probability=immediate,
            delayed_probability=delayed,
            total_probability=total,
            hyram_version=self.hyram_version,
            native_module_path=self.native_module_path,
            native_module_sha256=self.native_module_sha256,
            partition_evidence_id=self.partition_evidence_id,
            outcome_branch_ids=self.outcome_branch_ids,
            outcome_probabilities=self.outcome_probabilities,
        )
        if self.lineage_sha256 != expected_lineage:
            raise ValueError("Ignition probability/provider lineage digest does not match its fields")
        return self


def bind_hyram_ignition_to_risk(
    result: HyRAMIgnitionProbability,
    native: ConditionalRiskNative,
    *,
    frequency: Any,
    receptor_id: str,
    partition_evidence_id: str,
    outcome_branch_ids: Mapping[str, str],
    probability_factor_ids: Mapping[str, Sequence[str]],
    harm_bindings: Mapping[str, ConditionalHarmBinding],
    harm_factor_ids: Mapping[str, str],
    additional_factors: Mapping[str, Sequence[Any]] | None = None,
) -> HyRAMIgnitionRiskBinding:
    """Build native conditional-risk branches while retaining caller frequency.

    The partition evidence identity must also be included in the native risk
    context. Branch IDs, factor IDs and harm results remain caller-owned.
    Neither a frequency nor a conditional-on-ignition conversion is inferred.
    """
    if type(result) is not HyRAMIgnitionProbability:
        raise TypeError("Supply a typed HyRAM ignition result")
    if type(native) is not ConditionalRiskNative:
        raise TypeError("Supply the installed conditional-risk owner")
    native.require_current()
    risk = native.risk_module
    if type(frequency) is not risk.Frequency:
        raise TypeError("Supply the exact caller-created native LOC Frequency")
    receptor_id = _text(receptor_id, "risk receptor identity")
    partition_evidence_id = _text(partition_evidence_id, "partition evidence identity")
    if set(outcome_branch_ids) != set(_OUTCOMES):
        raise ValueError("Declare IDs for no, immediate and delayed ignition outcomes")
    ids = {key: _text(outcome_branch_ids[key], f"{key} branch ID") for key in _OUTCOMES}
    if len(set(ids.values())) != len(_OUTCOMES):
        raise ValueError("The three risk branch IDs must be unique")
    if set(probability_factor_ids) != set(_OUTCOMES):
        raise ValueError("Declare probability factor IDs for each outcome")
    probability_ids = {}
    for outcome in _OUTCOMES:
        values = tuple(_text(v, f"{outcome} probability factor ID")
                       for v in probability_factor_ids[outcome])
        if not values or len(set(values)) != len(values):
            raise ValueError(f"{outcome} requires unique probability-factor IDs")
        probability_ids[outcome] = values
    if set(harm_bindings) != set(ids.values()) or set(harm_factor_ids) != set(ids.values()):
        raise ValueError("Explicit harm and harm-factor bindings are required for all branches")
    extra = {} if additional_factors is None else {
        key: tuple(values) for key, values in additional_factors.items()
    }
    if set(extra) - set(ids.values()):
        raise ValueError("Additional factors may only target declared ignition branches")
    if any(type(factor) is not risk.Factor for values in extra.values() for factor in values):
        raise TypeError("Additional branch factors must be native risk Factor objects")

    table = result.table
    if table.fuel_species.lower() not in {"h2", "hydrogen"}:
        raise ValueError("Only hydrogen ignition results may enter this risk handoff")
    immediate = _probability(result.immediate_probability, "immediate probability")
    delayed = _probability(result.delayed_probability, "delayed probability")
    total = _probability(result.total_probability, "total ignition probability")
    if not math.isclose(total, math.fsum((immediate, delayed)), rel_tol=0., abs_tol=1e-14):
        raise ValueError("Immediate and delayed release-relative probabilities do not close")
    no_ignition = 1.0 - total
    probabilities = {"no_ignition": no_ignition,
                     "immediate_ignition": immediate,
                     "delayed_ignition": delayed}
    if not math.isclose(math.fsum(probabilities.values()), 1.0, rel_tol=0., abs_tol=1e-14):
        raise ValueError("No/immediate/delayed branches do not partition one LOC")
    rate = _nonnegative(result.release_rate_kg_s, "HyRAM release rate kg/s")
    if set(harm_bindings) != set(ids.values()):
        raise ValueError("Harm binding keys must match the explicit branch IDs")

    branches = []
    for outcome in _OUTCOMES:
        branch_id = ids[outcome]
        harm = harm_bindings[branch_id]
        if type(harm) is not ConditionalHarmBinding:
            raise TypeError("Each branch needs a typed ConditionalHarmBinding")
        harm.require_current()
        branches.append(risk.Branch(
            id=branch_id,
            conditional_probability=probabilities[outcome],
            probability_basis=partition_evidence_id,
            probability_factor_ids=probability_ids[outcome],
            harm_probability=harm.probability,
            harm_factor_id=_text(harm_factor_ids[branch_id], "branch harm factor ID"),
            harm_basis=harm.response_model_id,
            factors=extra.get(branch_id, ()),
        ))
    request = risk.RiskInput(
        frequency=frequency,
        receptor_id=receptor_id,
        branches=tuple(branches),
        partition_basis=partition_evidence_id,
        mutually_exclusive_exhaustive=True,
    )
    table_sha = table.content_sha256
    lineage_sha = _lineage_digest(
        table_id=table.table_id,
        table_evidence_id=table.evidence_id,
        table_sha256=table_sha,
        release_rate_kg_s=rate,
        immediate_probability=immediate,
        delayed_probability=delayed,
        total_probability=total,
        hyram_version=result.hyram_version,
        native_module_path=result.native_module_path,
        native_module_sha256=result.native_module_sha256,
        partition_evidence_id=partition_evidence_id,
        outcome_branch_ids=ids,
        outcome_probabilities=probabilities,
    )
    token = _issue_binding_token((
        request, frequency, ids, probabilities, probability_ids, harm_bindings,
    ))
    return HyRAMIgnitionRiskBinding(
        request=request,
        frequency=frequency,
        receptor_id=receptor_id,
        partition_evidence_id=partition_evidence_id,
        outcome_branch_ids=ids,
        outcome_probabilities=probabilities,
        probability_factor_ids=probability_ids,
        harm_bindings=harm_bindings,
        table_id=table.table_id,
        table_evidence_id=table.evidence_id,
        table_sha256=table_sha,
        release_rate_kg_s=rate,
        total_probability=total,
        hyram_version=result.hyram_version,
        native_module_path=result.native_module_path,
        native_module_sha256=result.native_module_sha256,
        origin=table.origin,
        lineage_sha256=lineage_sha,
        _issuer=token,
    )


__all__ = ["HyRAMIgnitionRiskBinding", "bind_hyram_ignition_to_risk"]
