"""Finite-source and receptor bindings to an actual optional conditional-risk engine.

Native PRCT owns branch aggregation, credit validation and calculation receipts.
The host preserves source/harm identities and declared conditional assumptions;
it does not derive annual frequencies, protection credit or missing hazard fields.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, is_dataclass
from dataclasses import field as dataclass_field
from importlib import metadata
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import Origin, PropertyBasis, ThermoState, finite
from ..release import SourceLocation
from ..sources import IntervalMassSource

_REVIEWED_CODE = "0d5239de3ba9a919a0a0b38a912fc86899d92f10da5e6a9e7a563d8abeec9152"
_PENDING_RISK_RESULT_ISSUERS = {}
_PENDING_RISK_NATIVE_ISSUERS = {}


def _issue_risk_native_token(package, risk, contracts, api):
    token = object()
    _PENDING_RISK_NATIVE_ISSUERS[token] = tuple(
        id(value) for value in (package, risk, contracts, api)
    )
    return token


def _issue_risk_result_token(parents):
    token = object()
    _PENDING_RISK_RESULT_ISSUERS[token] = tuple(id(value) for value in parents)
    return token


def _text(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Declare nonempty model, source, frame, clock and evidence identities")


def _origin(value):
    value = Origin(value)
    if value == Origin.UNRESOLVED:
        raise ValueError("Conditional input origins must be resolved explicitly")
    return value


def _plain(value):
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _digest(value):
    return hashlib.sha256(
        json.dumps(_plain(value), sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def finite_source_sha256(source: IntervalMassSource):
    """Bind interval contents and their physical meanings, not a source label alone."""
    if not isinstance(source, IntervalMassSource):
        raise TypeError("An actual finite IntervalMassSource is required")
    source.require_current()
    if (
        not isinstance(source.location, SourceLocation)
        or not isinstance(source.state, ThermoState)
        or not isinstance(source.state.basis, PropertyBasis)
    ):
        raise TypeError(
            "Physical source location, ThermoState and PropertyBasis objects are required"
        )
    # A surrounding interval object does not make its exposed nested objects
    # valid. Reapply their original physical contracts before binding them.
    PropertyBasis(**{f.name: getattr(source.state.basis, f.name) for f in fields(PropertyBasis)})
    ThermoState(**{f.name: getattr(source.state, f.name) for f in fields(ThermoState)})
    SourceLocation(**{f.name: getattr(source.location, f.name) for f in fields(SourceLocation)})
    _text(source.state.phase, source.state.basis.spin_composition)
    _origin(source.origin)
    finite(source.total_mass_kg, "finite source total mass")
    # Revalidate exposed arrays as well as their original frozen constructor.
    checked = IntervalMassSource(
        source.location,
        source.edges_s,
        source.mass_kg,
        source.state,
        source.origin,
        source.evidence_id,
        source.end_reason,
    )
    return _digest(checked)


@dataclass(frozen=True, slots=True)
class RiskReceptor:
    receptor_id: str
    frame_id: str
    clock_id: str
    position_m: tuple[float, float, float]
    position_evidence_id: str
    origin: Origin

    def __post_init__(self):
        _text(self.receptor_id, self.frame_id, self.clock_id, self.position_evidence_id)
        position = tuple(finite(v, "receptor position") for v in self.position_m)
        if len(position) != 3:
            raise ValueError("A receptor needs three coordinates in the declared frame")
        object.__setattr__(self, "position_m", position)
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class ConditionalHarmBinding:
    probability: float
    receptor_id: str
    frame_id: str
    clock_id: str
    support_s: tuple[float, float]
    source_id: str
    response_model_id: str
    position_m: tuple[float, float, float]
    evidence_ids: tuple[str, ...]
    origin: Origin
    exposure_result: Any = None
    exposure_signature: str | None = None

    def __post_init__(self):
        probability = finite(self.probability, "conditional harm probability")
        if not 0 <= probability <= 1:
            raise ValueError("Conditional harm probability must lie in [0,1]")
        _text(
            self.receptor_id, self.frame_id, self.clock_id, self.source_id, self.response_model_id
        )
        support = tuple(finite(v, "harm support") for v in self.support_s)
        if len(support) != 2 or support[0] > support[1]:
            raise ValueError("Declare ordered exposure support without extending it")
        evidence = tuple(self.evidence_ids)
        if not evidence or len(set(evidence)) != len(evidence):
            raise ValueError("Unique harm/model/binding evidence is required")
        _text(*evidence)
        object.__setattr__(self, "probability", probability)
        object.__setattr__(self, "support_s", support)
        position = tuple(finite(v, "harm receptor position") for v in self.position_m)
        if len(position) != 3:
            raise ValueError("Harm receptor needs three explicit coordinates")
        object.__setattr__(self, "position_m", position)
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "origin", _origin(self.origin))
        if self.exposure_result is None and self.exposure_signature is not None:
            raise ValueError("A computed exposure signature requires its actual result")
        self.require_current()

    @classmethod
    def from_exposure(cls, result, *, binding_evidence_id: str, origin: Origin):
        """Keep the actual computed exposure result; never infer its missing source physics."""
        from .hyram_exposure import ExposureResult, HyRAMExposure

        if not isinstance(result, ExposureResult):
            raise TypeError("Supply the actual computed ExposureResult")
        HyRAMExposure(
            result.native_module, quadrature_relative_tolerance=result.quadrature_relative_tolerance
        ).verify_result(result)
        if result.status != "conditional-on-supplied-exposure" or result.probability is None:
            raise ValueError("A probability-bearing supplied-exposure result is required")
        return cls(
            result.probability,
            result.receptor_id,
            result.frame_id,
            result.clock_id,
            tuple(result.support_s),
            result.source_id,
            result.model_id,
            tuple(result.input.receptor.position_m),
            tuple(
                dict.fromkeys(
                    (result.evidence_id, result.assumption_evidence_id, binding_evidence_id)
                )
            ),
            origin,
            result,
            _exposure_signature(result),
        )

    def require_current(self):
        if self.exposure_result is not None:
            from .hyram_exposure import ExposureResult, HyRAMExposure

            if not isinstance(self.exposure_result, ExposureResult):
                raise TypeError("Computed exposure provenance requires its actual ExposureResult")
            HyRAMExposure(
                self.exposure_result.native_module,
                quadrature_relative_tolerance=self.exposure_result.quadrature_relative_tolerance,
            ).verify_result(self.exposure_result)
            if self.exposure_signature != _exposure_signature(self.exposure_result):
                raise ValueError("Actual supplied exposure identity/probability changed")
            result = self.exposure_result
            if (
                self.probability,
                self.receptor_id,
                self.frame_id,
                self.clock_id,
                self.support_s,
                self.source_id,
                self.response_model_id,
                self.position_m,
            ) != (
                result.probability,
                result.receptor_id,
                result.frame_id,
                result.clock_id,
                tuple(result.support_s),
                result.source_id,
                result.model_id,
                tuple(result.input.receptor.position_m),
            ):
                raise ValueError("Harm binding differs from its actual computed exposure")


def _exposure_signature(result):
    if result.input.content_sha256 != result.input_sha256:
        raise ValueError("Supplied exposure input changed after its probability was calculated")
    return _digest(
        (
            result.status,
            result.probability,
            result.receptor_id,
            result.frame_id,
            result.clock_id,
            tuple(result.support_s),
            result.source_id,
            result.model_id,
            result.evidence_id,
            result.assumption_evidence_id,
            result.native_source_sha256,
            tuple(result.input.receptor.position_m),
            result.input_sha256,
            result.selection,
        )
    )


@dataclass(frozen=True, slots=True)
class RiskBindingEvidence:
    source_binding_evidence_id: str
    source_to_harm_assumption_id: str
    partition_evidence_id: str
    origin: Origin

    def __post_init__(self):
        _text(
            self.source_binding_evidence_id,
            self.source_to_harm_assumption_id,
            self.partition_evidence_id,
        )
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class ConditionalRiskNative:
    package: Any
    risk_module: Any
    contracts: Any
    api: Any
    version: str
    source_sha256: str
    native_bindings: tuple
    _issuer: object = dataclass_field(default=None, repr=False, compare=False)
    _identity_bindings: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        expected = tuple(
            id(value) for value in (self.package, self.risk_module, self.contracts, self.api)
        )
        if _PENDING_RISK_NATIVE_ISSUERS.get(self._issuer) != expected:
            raise TypeError("Create reviewed conditional-risk owners through from_installed()")
        _PENDING_RISK_NATIVE_ISSUERS.pop(self._issuer)
        if self.version != "0.1.0" or self.source_sha256 != _REVIEWED_CODE:
            raise ValueError("Native conditional-risk owner differs from the reviewed revision")
        object.__setattr__(self, "_identity_bindings", (
            self.package, self.risk_module, self.contracts, self.api, self.version,
            self.source_sha256, tuple(self.native_bindings),
        ))
        self.require_current()

    @classmethod
    def from_installed(cls):
        version = metadata.version("process-risk-consequence-toolkit")
        if version != "0.1.0":
            raise ValueError("Native conditional-risk revision differs from the reviewed contract")
        package = importlib.import_module("ccps_consequence")
        risk = importlib.import_module("ccps_consequence.risk")
        contracts = importlib.import_module("ccps_consequence.contracts")
        api = importlib.import_module("ccps_consequence.api")
        actual = contracts.code_digest()
        if actual != _REVIEWED_CODE:
            raise ValueError("Native risk source differs from the reviewed wheel")
        bindings = (
            risk.risk,
            risk.RiskInput,
            risk.RiskOutput,
            contracts.Context,
            api.calculate,
            api.CALCULATIONS["risk/conditional"].function,
        )
        return cls(
            package, risk, contracts, api, version, actual, bindings,
            _issuer=_issue_risk_native_token(package, risk, contracts, api),
        )

    def require_current(self):
        if not self._identity_bindings:
            raise ValueError("Conditional-risk owner has no installed-module receipt")
        current_identity = (
            self.package, self.risk_module, self.contracts, self.api, self.version,
            self.source_sha256, tuple(self.native_bindings),
        )
        if any(current is not original for current, original in zip(
            current_identity, self._identity_bindings, strict=True
        )):
            raise ValueError("Conditional-risk owner lost its installed module identities")
        r, c, a = self.risk_module, self.contracts, self.api
        current = (
            r.risk,
            r.RiskInput,
            r.RiskOutput,
            c.Context,
            a.calculate,
            a.CALCULATIONS["risk/conditional"].function,
        )
        if current != self.native_bindings or c.code_digest() != self.source_sha256:
            raise ValueError("Native conditional-risk functions/classes/source changed")


@dataclass(frozen=True, slots=True)
class ConditionalRiskResult:
    original_request: Any
    original_context: Any
    native_request: Any
    native_context: Any
    native_output: Any
    native_receipt: Any
    source: IntervalMassSource
    source_sha256: str
    receptor: RiskReceptor
    harm_bindings: Mapping[str, ConditionalHarmBinding]
    evidence: RiskBindingEvidence
    native: ConditionalRiskNative
    status: str = "conditional-single-LOC-on-supplied-source-harm-and-frequency"
    _issuer: object = dataclass_field(default=None, repr=False, compare=False)
    _identity_bindings: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)
    _content_sha256: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        expected_issuer = tuple(id(value) for value in (
            self.original_request, self.original_context, self.native_request,
            self.native_context, self.native_output, self.native_receipt, self.source,
            self.receptor, self.evidence, self.native,
        ))
        if _PENDING_RISK_RESULT_ISSUERS.get(self._issuer) != expected_issuer:
            raise TypeError("Create conditional-risk results through the native evaluation owner")
        _PENDING_RISK_RESULT_ISSUERS.pop(self._issuer)
        if self.status != "conditional-single-LOC-on-supplied-source-harm-and-frequency":
            raise ValueError("Conditional-risk result status cannot be relabeled")
        if not isinstance(self.harm_bindings, Mapping):
            raise TypeError("Retain the original branch-to-harm mapping")
        bindings = MappingProxyType(dict(self.harm_bindings))
        object.__setattr__(self, "harm_bindings", bindings)
        content = self._current_content_sha256()
        object.__setattr__(self, "_content_sha256", content)
        object.__setattr__(self, "_identity_bindings", self._object_bindings())

    def _object_bindings(self):
        return (
            self.original_request, self.original_context, self.native_request,
            self.native_context, self.native_output, self.native_receipt, self.source,
            self.receptor, self.evidence, self.native, self.harm_bindings,
            *tuple(self.harm_bindings[key] for key in sorted(self.harm_bindings)),
        )

    def _current_content_sha256(self):
        if type(self.native) is not ConditionalRiskNative:
            raise TypeError("Retain the actual reviewed native-risk owner")
        self.native.require_current()
        risk, contracts = self.native.risk_module, self.native.contracts
        if (type(self.original_request) is not risk.RiskInput
                or type(self.original_context) is not contracts.Context
                or type(self.native_request) is not risk.RiskInput
                or type(self.native_context) is not contracts.Context
                or type(self.native_output) is not risk.RiskOutput
                or type(self.native_receipt) is not contracts.Receipt):
            raise TypeError("Retain original and owned native request/context/output objects")
        if (self.original_request.digest() != self.native_request.digest()
                or self.original_context.digest() != self.native_context.digest()):
            raise ValueError("Owned native request/context no longer match the original inputs")
        request_payload = self.native_request.model_dump(mode="json")
        context_payload = self.native_context.model_dump(mode="json")
        if (self.native_output.model_dump(mode="json") != self.native_receipt.outputs
                or self.native_output.complete_facility_qra_claim
                or self.native_receipt.complete_facility_qra_claim
                or self.native_receipt.calculation_id != "risk/conditional"
                or self.native_receipt.normalized_inputs != request_payload
                or self.native_receipt.context.model_dump(mode="json") != context_payload
                or self.native_receipt.code_digest != self.native.source_sha256
                or self.native_receipt.output_digest
                != contracts.digest(self.native_receipt.outputs)):
            raise ValueError("Typed native output and incomplete-QRA receipt no longer agree")
        if type(self.receptor) is not RiskReceptor or type(self.evidence) is not RiskBindingEvidence:
            raise TypeError("Retain typed receptor and risk-binding evidence")
        if (self.receptor.receptor_id != self.native_request.receptor_id
                or self.receptor.frame_id != self.source.location.coordinate_frame_id
                or self.receptor.clock_id != self.source.location.clock_id):
            raise ValueError("Risk receptor no longer matches the finite source/native request")
        source_sha = finite_source_sha256(self.source)
        if source_sha != self.source_sha256:
            raise ValueError("Finite source changed after the conditional-risk calculation")
        branches = {branch.id: branch for branch in self.native_request.branches}
        if set(self.harm_bindings) != set(branches):
            raise ValueError("Every native branch must retain its original harm binding")
        harm_content = []
        required_evidence = {
            self.source.evidence_id,
            self.evidence.source_binding_evidence_id,
            self.evidence.source_to_harm_assumption_id,
            self.evidence.partition_evidence_id,
            self.receptor.position_evidence_id,
            *self.native_request.frequency.evidence_ids,
        }
        for key in sorted(branches):
            branch, binding = branches[key], self.harm_bindings[key]
            if type(binding) is not ConditionalHarmBinding:
                raise TypeError("Retain the actual typed branch harm binding")
            binding.require_current()
            if ((binding.probability, binding.response_model_id, binding.receptor_id,
                 binding.frame_id, binding.clock_id, binding.position_m)
                    != (branch.harm_probability, branch.harm_basis,
                        self.receptor.receptor_id, self.receptor.frame_id,
                        self.receptor.clock_id, self.receptor.position_m)):
                raise ValueError("Branch harm no longer matches the original receptor and branch")
            required_evidence.update(binding.evidence_ids)
            required_evidence.update((branch.probability_basis, branch.harm_basis))
            required_evidence.update(factor.basis for factor in branch.factors)
            harm_content.append((
                key, binding.probability, binding.receptor_id, binding.frame_id,
                binding.clock_id, binding.support_s, binding.source_id,
                binding.response_model_id, binding.position_m, binding.evidence_ids,
                binding.origin, binding.exposure_signature,
            ))
        if self.evidence.partition_evidence_id != self.native_request.partition_basis:
            raise ValueError("Risk partition evidence differs from the retained native request")
        if not required_evidence <= {item.id for item in self.native_context.evidence}:
            raise ValueError("Native context no longer resolves all bound source/harm evidence")
        return _digest((
            self.original_request.digest(), self.original_context.digest(),
            request_payload, context_payload, self.native_output.model_dump(mode="json"),
            self.native_receipt.model_dump(mode="json"), source_sha,
            self.receptor, self.evidence, tuple(harm_content), self.native.version,
            self.native.source_sha256, self.status,
        ))

    def require_current(self):
        if not self._identity_bindings or any(
            current is not bound
            for current, bound in zip(self._object_bindings(), self._identity_bindings, strict=True)
        ):
            raise ValueError("Conditional-risk result lost its original object bindings")
        if self._current_content_sha256() != self._content_sha256:
            raise ValueError("Conditional-risk inputs, evidence or native output changed")
        return self

    @property
    def annual_harm_frequency_per_year(self):
        self.require_current()
        return self.native_output.annual_harm_frequency_per_year


class ConditionalRiskError(RuntimeError):
    """Original inputs/native objects and partial returned receipts survive failure."""

    def __init__(
        self,
        message,
        *,
        native,
        original_request,
        original_context,
        source,
        receptor,
        harm_bindings,
        evidence,
        stage,
        owned_request=None,
        owned_context=None,
        native_output=None,
        native_receipt=None,
        source_sha256=None,
    ):
        super().__init__(message)
        self.native = native
        self.original_request, self.original_context = original_request, original_context
        self.source, self.receptor = source, receptor
        self.harm_bindings, self.evidence = MappingProxyType(dict(harm_bindings)), evidence
        self.stage = stage
        self.native_request, self.native_context = owned_request, owned_context
        self.native_output, self.native_receipt = native_output, native_receipt
        self.source_sha256 = source_sha256


def conditional_risk(
    native: ConditionalRiskNative,
    request,
    context,
    *,
    source: IntervalMassSource,
    receptor: RiskReceptor,
    harm_bindings: Mapping[str, ConditionalHarmBinding],
    evidence: RiskBindingEvidence,
) -> ConditionalRiskResult:
    """Execute native single-LOC risk with explicit finite-source/receptor bindings.

    The native receipt API internally normalizes its typed input. No user JSON,
    file, HTTP call or replacement risk solver is needed. The additional direct
    native call retains the actual typed RiskOutput, independently cross-checked
    against that native receipt rather than reconstructed from its dictionary.
    """
    owned_request = owned_context = output = receipt = source_sha = None
    bindings = dict(harm_bindings)
    stage = "native-input-admission"
    try:
        native.require_current()
        r, c = native.risk_module, native.contracts
        if type(request) is not r.RiskInput or type(context) is not c.Context:
            raise TypeError("Actual native RiskInput and Context objects are required")
        # Native frozen models can still be replaced through model_copy(update).
        # Validate current Python values rather than trusting instance identity.
        owned_request = r.RiskInput.model_validate(request.model_dump(mode="python"), strict=True)
        owned_context = c.Context.model_validate(context.model_dump(mode="python"), strict=True)
        original_signature = (request.digest(), context.digest())
        stage = "physical-source-and-harm-binding"
        source_sha = finite_source_sha256(source)
        if not isinstance(receptor, RiskReceptor) or not isinstance(evidence, RiskBindingEvidence):
            raise TypeError("Explicit receptor and source/partition evidence are required")
        if (
            receptor.receptor_id != owned_request.receptor_id
            or receptor.frame_id != source.location.coordinate_frame_id
            or receptor.clock_id != source.location.clock_id
        ):
            raise ValueError("Source, receptor, native case frame/clock/identity differ")
        if evidence.partition_evidence_id != owned_request.partition_basis:
            raise ValueError("Native branch partition and host evidence differ")
        if set(bindings) != {b.id for b in owned_request.branches}:
            raise ValueError("Every native branch requires exactly one harm binding")
        required = {
            source.evidence_id,
            evidence.source_binding_evidence_id,
            evidence.source_to_harm_assumption_id,
            evidence.partition_evidence_id,
            receptor.position_evidence_id,
            *owned_request.frequency.evidence_ids,
        }
        for branch in owned_request.branches:
            binding = bindings[branch.id]
            if not isinstance(binding, ConditionalHarmBinding):
                raise TypeError("Every branch needs explicit ConditionalHarmBinding")
            binding.require_current()
            if (binding.receptor_id, binding.frame_id, binding.clock_id) != (
                receptor.receptor_id,
                receptor.frame_id,
                receptor.clock_id,
            ):
                raise ValueError("Harm and receptor frame/clock/identity differ")
            if binding.position_m != receptor.position_m:
                raise ValueError("Harm and risk receptor coordinates differ")
            if (
                binding.probability != branch.harm_probability
                or binding.response_model_id != branch.harm_basis
            ):
                raise ValueError("Native branch probability/model differs from its harm evidence")
            required.update(binding.evidence_ids)
            required.add(branch.probability_basis)
            required.add(branch.harm_basis)
            required.update(f.basis for f in branch.factors)
        if not required <= {e.id for e in owned_context.evidence}:
            raise ValueError(
                "Native context does not resolve all source, receptor, partition and harm evidence"
            )
        stage = "native-risk-evaluation"
        receipt = native.api.calculate("risk/conditional", owned_request, context=owned_context)
        output = native.risk_module.risk(owned_request)
        stage = "completed-result-audit"
        if output.model_dump(mode="json") != receipt.outputs:
            raise ValueError(
                "Actual typed native output differs from its native calculation receipt"
            )
        if output.complete_facility_qra_claim or receipt.complete_facility_qra_claim:
            raise ValueError("A single conditional LOC result cannot claim complete facility QRA")
        if (request.digest(), context.digest()) != original_signature:
            raise ValueError("Original native request/context changed during calculation")
        if source_sha != finite_source_sha256(source):
            raise ValueError("Finite physical source changed during risk calculation")
        for binding in bindings.values():
            binding.require_current()
        native.require_current()
        return ConditionalRiskResult(
            request,
            context,
            owned_request,
            owned_context,
            output,
            receipt,
            source,
            source_sha,
            receptor,
            MappingProxyType(bindings),
            evidence,
            native,
            _issuer=_issue_risk_result_token((
                request, context, owned_request, owned_context, output, receipt,
                source, receptor, evidence, native,
            )),
        )
    except Exception as exc:
        raise ConditionalRiskError(
            str(exc),
            native=native,
            original_request=request,
            original_context=context,
            source=source,
            receptor=receptor,
            harm_bindings=bindings,
            evidence=evidence,
            stage=stage,
            owned_request=owned_request,
            owned_context=owned_context,
            native_output=output,
            native_receipt=receipt,
            source_sha256=source_sha,
        ) from exc
