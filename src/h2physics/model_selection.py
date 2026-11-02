"""Explicit model-level/provider selection with no implicit fallback.

The registry owns no physical equation and imports no optional engine.  Callers
register exact factories and must request an exact family, level and provider.
"""

from dataclasses import dataclass, field
from types import MappingProxyType

from .adapters.physical_economics import callable_identity
from .catalog import MODELS, ModelSpec

EXECUTABLE_STATUSES = frozenset(
    {"implemented", "native_adapter_verified", "implemented_unverified"}
)
_BINDING_TOKEN = object()


def _text(*values):
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Declare family, level, provider, revision and evidence identities")


def _strings(values, label, *, allow_empty=False):
    result = frozenset(values)
    if (not allow_empty and not result) or any(not isinstance(value, str) or not value.strip()
                                                for value in result):
        raise ValueError(f"Declare nonempty {label} identities")
    return result


@dataclass(frozen=True, slots=True)
class ModelRequest:
    family_id: str
    level_id: str
    provider_id: str
    accepted_statuses: frozenset[str]
    required_capabilities: frozenset[str]
    required_evidence_ids: frozenset[str] = frozenset()

    def __post_init__(self):
        _text(self.family_id, self.level_id, self.provider_id)
        statuses = _strings(self.accepted_statuses, "accepted status")
        if not statuses <= EXECUTABLE_STATUSES:
            raise ValueError("A request cannot admit planned or unknown implementation status")
        object.__setattr__(self, "accepted_statuses", statuses)
        object.__setattr__(self, "required_capabilities",
                           _strings(self.required_capabilities, "required capability"))
        object.__setattr__(self, "required_evidence_ids",
                           _strings(self.required_evidence_ids, "required evidence", allow_empty=True))


@dataclass(frozen=True, slots=True)
class ProviderBinding:
    family_id: str
    level_id: str
    provider_id: str
    status: str
    revision: str
    capabilities: frozenset[str]
    evidence_ids: frozenset[str]
    factory: object = field(repr=False, compare=False)
    _factory_identity: tuple = field(repr=False, compare=False)
    _token: object = field(repr=False, compare=False)

    @classmethod
    def bind(cls, *, family_id, level_id, provider_id, status, revision,
             capabilities, evidence_ids, factory):
        _text(family_id, level_id, provider_id, revision)
        if status not in EXECUTABLE_STATUSES:
            raise ValueError("Only executable or explicitly unverified source levels can bind a factory")
        if not callable(factory):
            raise TypeError("A provider binding requires its actual callable factory")
        return cls(
            family_id,
            level_id,
            provider_id,
            status,
            revision,
            _strings(capabilities, "provider capability"),
            _strings(evidence_ids, "provider evidence"),
            factory,
            callable_identity(factory),
            _BINDING_TOKEN,
        )

    @property
    def key(self):
        return self.family_id, self.level_id, self.provider_id

    def require_current(self):
        if (self._token is not _BINDING_TOKEN or not callable(self.factory)
                or callable_identity(self.factory) != self._factory_identity):
            raise ValueError("Registered provider factory/callable state changed; bind a new revision")
        return self


class ModelRegistry:
    """Caller-owned registry. Registration and selection never import a provider."""

    def __init__(self, families=MODELS):
        families = tuple(families)
        if not families or any(type(item) is not ModelSpec for item in families):
            raise TypeError("Supply actual catalog ModelSpec records")
        index = {item.identifier: item for item in families}
        if len(index) != len(families):
            raise ValueError("Catalog family identifiers must be unique")
        self._families = MappingProxyType(index)
        self._bindings = {}

    @property
    def families(self):
        return self._families

    @property
    def bindings(self):
        return MappingProxyType(dict(self._bindings))

    def register(self, binding: ProviderBinding):
        if type(binding) is not ProviderBinding:
            raise TypeError("Register a ProviderBinding issued by ProviderBinding.bind")
        binding.require_current()
        if binding.family_id not in self._families:
            raise KeyError("Provider family is absent from the consolidated model catalog")
        if self._families[binding.family_id].status == "planned":
            raise ValueError("A catalog-planned family cannot register an executable factory")
        if binding.key in self._bindings:
            raise ValueError("An exact family/level/provider binding is already registered")
        self._bindings[binding.key] = binding
        return binding

    def select(self, request: ModelRequest):
        if type(request) is not ModelRequest:
            raise TypeError("Supply an explicit ModelRequest")
        key = request.family_id, request.level_id, request.provider_id
        try:
            binding = self._bindings[key]
        except KeyError as error:
            available = tuple(k for k in self._bindings if k[0] == request.family_id)
            raise LookupError(
                f"Exact requested provider is unavailable; no fallback. Available exact keys: {available}"
            ) from error
        binding.require_current()
        if binding.status not in request.accepted_statuses:
            raise ValueError("Requested provider status was not explicitly admitted")
        if not request.required_capabilities <= binding.capabilities:
            raise ValueError("Requested capabilities exceed the exact provider binding")
        if not request.required_evidence_ids <= binding.evidence_ids:
            raise ValueError("Required evidence identities are absent from the provider binding")
        return ModelSelection(self, request, binding)


@dataclass(frozen=True, slots=True)
class ModelSelection:
    registry: ModelRegistry = field(repr=False, compare=False)
    request: ModelRequest
    binding: ProviderBinding

    def require_current(self):
        if self.registry.bindings.get(self.binding.key) is not self.binding:
            raise ValueError("Selected provider is no longer the original registry binding")
        self.binding.require_current()
        return self

    def build(self, /, *args, **kwargs):
        """Call only the selected exact factory; there is no retry or alternative provider."""
        self.require_current()
        result = self.binding.factory(*args, **kwargs)
        self.require_current()
        return BuiltModel(self, result, self.binding._factory_identity)


@dataclass(frozen=True, slots=True)
class BuiltModel:
    selection: ModelSelection
    model: object
    factory_identity: tuple = field(repr=False)

    def require_current(self):
        self.selection.require_current()
        if self.factory_identity != self.selection.binding._factory_identity:
            raise ValueError("Built model and current selected factory identities differ")
        return self
