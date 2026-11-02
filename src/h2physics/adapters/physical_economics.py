"""Public source-neutral physical reporting and finite utility pricing contracts.

No native import, finance equation or physical solver is implemented here.
Validated means source/cache correspondence, not independent qualification.
"""

import dataclasses
import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol, runtime_checkable

import numpy as np

from ..core import Origin, finite

_BINDING_TOKEN = object()


def require_text(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Declare source, quantity, unit, boundary and evidence identities")


def finite_sum(values, label="finite sum"):
    """Public finite accounting sum; it does not annualize or discount quantities."""
    try:
        return finite(math.fsum(finite(v, label + " term") for v in values), label)
    except OverflowError as error:
        raise ValueError(f"{label} exceeds finite arithmetic") from error


def stable_snapshot(
    value, *, maximum_items=2_000_000, maximum_depth=128, maximum_array_bytes=268_435_456
):
    """Read-only portable content snapshot; never serializes native object repr.

    Raw diagnostic nonfinite floats are explicitly labelled, never made zero.
    Physical quantities are admitted separately through strict finite guards.
    Array shape/dtype/original bytes survive even when diagnostic NaNs occur.
    """
    if (
        type(maximum_items) is not int
        or maximum_items < 1
        or type(maximum_depth) is not int
        or maximum_depth < 1
        or type(maximum_array_bytes) is not int
        or maximum_array_bytes < 1
    ):
        raise ValueError("Snapshot item/depth/array-byte budgets must be positive integers")
    count, array_bytes, visiting = 0, 0, set()

    def walk(item, depth):
        nonlocal count, array_bytes
        count += 1
        if count > maximum_items or depth > maximum_depth:
            raise ValueError("Source snapshot exceeds declared item/depth budget")
        if item is None or isinstance(item, (str, bool, int)):
            return item
        if isinstance(item, np.generic):
            return walk(item.item(), depth + 1)
        if isinstance(item, float):
            return item if math.isfinite(item) else MappingProxyType({"nonfinite": str(item)})
        if isinstance(item, np.ndarray):
            if item.dtype.hasobject:
                raise TypeError("Object arrays need an explicit source-owner content mapper")
            array_bytes += item.nbytes
            if array_bytes > maximum_array_bytes:
                raise ValueError("Source arrays exceed the declared snapshot byte budget")
            array = np.array(item, copy=True, order="C")
            return MappingProxyType(
                {
                    "array_dtype": array.dtype.str,
                    "array_shape": tuple(array.shape),
                    "array_bytes_sha256": hashlib.sha256(array.tobytes()).hexdigest(),
                }
            )
        if dataclasses.is_dataclass(item) and not isinstance(item, type):
            item = {f.name: getattr(item, f.name) for f in dataclasses.fields(item)}
        if isinstance(item, (Mapping, tuple, list)):
            marker = id(item)
            if marker in visiting:
                raise ValueError("Cyclic source metadata is not a portable evidence snapshot")
            visiting.add(marker)
            try:
                if isinstance(item, Mapping):
                    if any(not isinstance(k, str) for k in item):
                        raise TypeError("Portable evidence mappings need explicit string keys")
                    return MappingProxyType({k: walk(v, depth + 1) for k, v in item.items()})
                return tuple(walk(v, depth + 1) for v in item)
            finally:
                visiting.remove(marker)
        raise TypeError("Map opaque/native objects explicitly; retain their identities separately")

    return walk(value, 0)


def _plain(value):
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    return value


def snapshot_sha256(value):
    """Public stable content hash, including typed array-byte digests."""
    return hashlib.sha256(
        json.dumps(
            _plain(stable_snapshot(value)), sort_keys=True, allow_nan=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def callable_identity(function):
    """Actual bound owner/function/code references, without invoking the function."""
    original = getattr(function, "__func__", function)
    return (getattr(function, "__self__", None), original, getattr(original, "__code__", None))


@dataclass(frozen=True, slots=True)
class QuantityDefinition:
    identifier: str
    quantity: str
    unit: str
    boundary_role: str
    product_role: str | None = None
    billable: bool = False
    nonnegative: bool = True

    def __post_init__(self):
        require_text(self.identifier, self.quantity, self.unit, self.boundary_role)
        if {"hydrogen_mass": "kg", "energy": "J", "amount": "mol"}.get(self.quantity) != self.unit:
            raise ValueError(
                "Declare actual SI quantity/unit identity; no implicit unit conversion"
            )
        if self.product_role not in {
            None,
            "generated",
            "initial_stock",
            "final_stock",
            "stock_change",
            "harvested",
            "sold",
        }:
            raise ValueError("Declare a distinct generated/stock/harvest/sale role")
        if self.product_role is not None and self.quantity != "hydrogen_mass":
            raise ValueError("Product roles use explicit H2 mass units")
        if type(self.billable) is not bool or type(self.nonnegative) is not bool:
            raise TypeError("Declare billing/sign contracts explicitly")
        if self.billable and self.unit != "J":
            raise ValueError(
                "Current UtilityTariff is USD/J; other material costs remain explicit annual inputs"
            )
        if self.billable and not self.nonnegative:
            raise ValueError(
                "Billable energy must be oriented nonnegative; no implicit signed credit"
            )


def _definition(name, quantity, role, product=None, billable=False, nonnegative=True):
    return QuantityDefinition(
        name,
        quantity,
        {"energy": "J", "amount": "mol", "hydrogen_mass": "kg"}[quantity],
        role,
        product,
        billable,
        nonnegative,
    )


_DEFINITIONS = (
    _definition("generated_h2_kg", "hydrogen_mass", "net generated H2", "generated"),
    _definition(
        "initial_h2_stock_kg", "hydrogen_mass", "finite initial inventory", "initial_stock"
    ),
    _definition("final_h2_stock_kg", "hydrogen_mass", "finite final inventory", "final_stock"),
    _definition(
        "h2_stock_increase_kg",
        "hydrogen_mass",
        "finite stock change",
        "stock_change",
        nonnegative=False,
    ),
    _definition("harvested_h2_kg", "hydrogen_mass", "resolved harvest boundary", "harvested"),
    _definition("sold_h2_kg", "hydrogen_mass", "resolved sale boundary", "sold"),
    _definition("exported_sale_h2_kg", "hydrogen_mass", "legacy resolved sale boundary", "sold"),
    *(
        _definition(
            n,
            "hydrogen_mass",
            "legacy finite receiver inventory",
            r,
            nonnegative=r != "stock_change",
        )
        for n, r in (
            ("receiver_initial_h2_kg", "initial_stock"),
            ("receiver_final_h2_kg", "final_stock"),
            ("receiver_stock_increase_kg", "stock_change"),
        )
    ),
    *(
        _definition(n, "hydrogen_mass", "finite cell inventory", r, nonnegative=r != "stock_change")
        for n, r in (
            ("cell_initial_h2_kg", "initial_stock"),
            ("cell_final_h2_kg", "final_stock"),
            ("cell_stock_increase_kg", "stock_change"),
        )
    ),
    *(
        _definition(n, "energy", role, billable=True)
        for n, role in (
            ("electrical_work_into_j", "applied component electrical work"),
            ("required_heat_input_j", "gross required heating"),
            ("required_heat_rejection_j", "gross required rejection"),
            ("external_pressure_work_j", "separately resolved pressure work"),
            ("stack_electricity_j", "legacy component electrical work"),
            ("pv_electricity_j", "native PV generation"),
            ("stack_heat_input_j", "legacy component heating"),
            ("stack_heat_rejection_j", "legacy component rejection"),
            ("receiver_heat_input_j", "finite receiver heating"),
            ("receiver_heat_rejection_j", "finite receiver rejection"),
        )
    ),
    *(
        _definition(n, "energy", "signed reported thermal ledger", nonnegative=False)
        for n in (
            "signed_required_heat_j",
            "cell_signed_isothermal_heat_required_j",
            "stack_heat_rejected_j",
            "receiver_heat_into_j",
        )
    ),
    _definition("transferred_electrons_mol", "amount", "actual circuit electron transfer"),
    _definition("biomass_generated_mol", "amount", "declared biomass formula-unit generation"),
)
QUANTITY_REGISTRY = MappingProxyType({d.identifier: d for d in _DEFINITIONS})


def quantity_definition(identifier):
    """Resolve and revalidate a public, explicit SI quantity definition."""
    try:
        value = QUANTITY_REGISTRY[identifier]
    except KeyError as error:
        raise ValueError("Unregistered physical economic quantity") from error
    QuantityDefinition(**{f.name: getattr(value, f.name) for f in dataclasses.fields(value)})
    return value


@dataclass(frozen=True, slots=True)
class QuantityBoundary:
    quantity_id: str
    boundary_id: str
    basis_id: str
    evidence_id: str
    billing_components: tuple[str, ...] = ()

    def __post_init__(self):
        definition = quantity_definition(self.quantity_id)
        require_text(self.boundary_id, self.basis_id, self.evidence_id)
        components = tuple(self.billing_components)
        if len(set(components)) != len(components):
            raise ValueError("Billing component identities cannot be repeated")
        if components:
            require_text(*components)
        if definition.billable and not components:
            raise ValueError("Billable energy needs explicit overlap/boundary component identities")
        object.__setattr__(self, "billing_components", components)


@dataclass(frozen=True, slots=True)
class ReportingWindow:
    start_s: float
    end_s: float
    clock_id: str
    evidence_id: str
    selected_product_basis: str
    mass_tolerance_kg: float = 1e-10

    def __post_init__(self):
        if finite(self.start_s, "report start") >= finite(self.end_s, "report end"):
            raise ValueError("Declare an increasing physical-seconds reporting window")
        require_text(self.clock_id, self.evidence_id)
        finite(self.mass_tolerance_kg, "reporting mass tolerance", positive=True)
        definition = quantity_definition(self.selected_product_basis)
        if definition.product_role not in {"generated", "stock_change", "harvested", "sold"}:
            raise ValueError("Select explicit generated/stock-change/harvested/sold H2 mass")


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    source: object
    window: ReportingWindow
    hydrogen_id: str
    source_id: str
    verification_kind: str
    quantities: Mapping[str, float | None]
    boundaries: Mapping[str, QuantityBoundary]
    unresolved: tuple[str, ...]
    content: object
    identities: tuple

    def __post_init__(self):
        require_text(self.hydrogen_id, self.source_id, self.verification_kind)
        if type(self.window) is not ReportingWindow:
            raise TypeError("Use the actual public ReportingWindow")
        ReportingWindow(
            **{f.name: getattr(self.window, f.name) for f in dataclasses.fields(self.window)}
        )
        quantities, boundaries = dict(self.quantities), dict(self.boundaries)
        if not quantities or set(quantities) != set(boundaries):
            raise ValueError("Every reported quantity needs an explicit unit/boundary record")
        for name, value in quantities.items():
            definition = quantity_definition(name)
            boundary = boundaries[name]
            if type(boundary) is not QuantityBoundary or boundary.quantity_id != name:
                raise TypeError("Bind an actual matching QuantityBoundary")
            QuantityBoundary(
                **{f.name: getattr(boundary, f.name) for f in dataclasses.fields(boundary)}
            )
            if value is not None:
                value = finite(value, "physical quantity " + name)
                if definition.nonnegative and value < 0:
                    raise ValueError("A declared oriented physical quantity cannot be negative")
                quantities[name] = value
        if (
            self.window.selected_product_basis not in quantities
            or quantities[self.window.selected_product_basis] is None
        ):
            raise ValueError(
                "The selected physical product role is absent/unavailable; never substitute generated H2"
            )
        gaps = tuple(self.unresolved)
        if len(set(gaps)) != len(gaps):
            raise ValueError("Unknown cost identities must be distinct")
        if gaps:
            require_text(*gaps)
        object.__setattr__(self, "quantities", MappingProxyType(quantities))
        object.__setattr__(self, "boundaries", MappingProxyType(boundaries))
        object.__setattr__(self, "unresolved", gaps)
        object.__setattr__(self, "content", stable_snapshot(self.content))
        object.__setattr__(self, "identities", tuple(self.identities))


@runtime_checkable
class PhysicalSourceAdapter(Protocol):
    identifier: str

    def snapshot(self, source, window: ReportingWindow, hydrogen_id: str) -> SourceSnapshot: ...


def _snapshot_material(snapshot):
    return (
        snapshot.source_id,
        snapshot.verification_kind,
        snapshot.hydrogen_id,
        snapshot.window,
        dict(snapshot.quantities),
        dict(snapshot.boundaries),
        snapshot.unresolved,
        snapshot.content,
        {name: quantity_definition(name) for name in snapshot.quantities},
    )


class SourceAuditError(ValueError):
    """Actual source/adapter/cache and original source-owner failure are retained."""

    def __init__(
        self, message, *, source, adapter, window, hydrogen_id, original, cached_snapshot=None
    ):
        super().__init__(message)
        self.source, self.adapter, self.window, self.hydrogen_id = (
            source,
            adapter,
            window,
            hydrogen_id,
        )
        self.original_error, self.cached_snapshot = original, cached_snapshot


def _audit_source(adapter, source, window, hydrogen_id, cached_snapshot=None):
    try:
        return adapter.snapshot(source, window, hydrogen_id)
    except Exception as error:
        raise SourceAuditError(
            str(error),
            source=source,
            adapter=adapter,
            window=window,
            hydrogen_id=hydrogen_id,
            original=error,
            cached_snapshot=cached_snapshot,
        ) from error


@dataclass(frozen=True, slots=True)
class ValidatedSourceBinding:
    source: object
    adapter: PhysicalSourceAdapter
    window: ReportingWindow
    hydrogen_id: str
    cached_snapshot: SourceSnapshot
    fingerprint: str
    _adapter_id: str = field(repr=False)
    _audit_identity: tuple = field(repr=False)
    _identity_seal: tuple = field(repr=False)
    _token: object = field(repr=False)

    def __post_init__(self):
        if self._token is not _BINDING_TOKEN:
            raise TypeError("Create source bindings with ValidatedSourceBinding.bind")

    @classmethod
    def bind(cls, source, adapter, window, *, hydrogen_id):
        if not isinstance(adapter, PhysicalSourceAdapter):
            raise TypeError("Provide an explicit source-owner snapshot adapter")
        require_text(adapter.identifier, hydrogen_id)
        audit = callable_identity(adapter.snapshot)
        snapshot = _audit_source(adapter, source, window, hydrogen_id)
        if (
            type(snapshot) is not SourceSnapshot
            or snapshot.source is not source
            or snapshot.window is not window
            or snapshot.hydrogen_id != hydrogen_id
            or any(
                a is not b for a, b in zip(callable_identity(adapter.snapshot), audit, strict=True)
            )
        ):
            raise ValueError("Source audit changed its actual source/window/call binding")
        fingerprint = snapshot_sha256((adapter.identifier, _snapshot_material(snapshot)))
        return cls(
            source,
            adapter,
            window,
            hydrogen_id,
            snapshot,
            fingerprint,
            adapter.identifier,
            audit,
            (
                source,
                adapter,
                window,
                snapshot,
                snapshot.quantities,
                snapshot.boundaries,
                snapshot.content,
                snapshot.unresolved,
                snapshot.identities,
                *snapshot.identities,
            ),
            _BINDING_TOKEN,
        )

    def require_current(self):
        if (
            self._token is not _BINDING_TOKEN
            or self.adapter.identifier != self._adapter_id
            or any(
                a is not b
                for a, b in zip(
                    callable_identity(self.adapter.snapshot), self._audit_identity, strict=True
                )
            )
            or self.source is not self._identity_seal[0]
            or self.adapter is not self._identity_seal[1]
            or self.window is not self._identity_seal[2]
        ):
            raise ValueError("Original source/adapter/window/audit binding changed")
        if (
            snapshot_sha256((self._adapter_id, _snapshot_material(self.cached_snapshot)))
            != self.fingerprint
        ):
            raise ValueError("Cached physical projection/source metadata mutated")
        cached = self.cached_snapshot
        cached_identities = (
            self.source,
            self.adapter,
            self.window,
            cached,
            cached.quantities,
            cached.boundaries,
            cached.content,
            cached.unresolved,
            cached.identities,
            *cached.identities,
        )
        if (
            self.cached_snapshot.source is not self.source
            or self.cached_snapshot.window is not self.window
            or self.cached_snapshot.hydrogen_id != self.hydrogen_id
            or len(cached_identities) != len(self._identity_seal)
            or any(a is not b for a, b in zip(cached_identities, self._identity_seal, strict=True))
        ):
            raise ValueError("Cached source/identity proof was replaced")
        current = _audit_source(
            self.adapter, self.source, self.window, self.hydrogen_id, self.cached_snapshot
        )
        if (
            type(current) is not SourceSnapshot
            or current.source is not self.source
            or current.window is not self.window
            or current.hydrogen_id != self.hydrogen_id
        ):
            raise ValueError("Current source audit returned another source/clock/material")
        identities = (
            self.source,
            self.adapter,
            self.window,
            cached,
            cached.quantities,
            cached.boundaries,
            cached.content,
            cached.unresolved,
            cached.identities,
            *current.identities,
        )
        if (
            len(identities) != len(self._identity_seal)
            or any(a is not b for a, b in zip(identities, self._identity_seal, strict=True))
            or snapshot_sha256((self._adapter_id, _snapshot_material(current))) != self.fingerprint
        ):
            raise ValueError("Actual source/native/cache correspondence changed after binding")
        if self.adapter.identifier != self._adapter_id or any(
            a is not b
            for a, b in zip(
                callable_identity(self.adapter.snapshot), self._audit_identity, strict=True
            )
        ):
            raise ValueError("Source audit changed its own callable/identity during admission")
        return self


@runtime_checkable
class PhysicalEconomicProjection(Protocol):
    source: object
    window: ReportingWindow
    hydrogen_id: str
    quantities: Mapping[str, float | None]
    unresolved: tuple[str, ...]
    source_fingerprint: str
    source_binding: ValidatedSourceBinding

    def require_current(self): ...
    def price_window(self, tariffs): ...


def require_validated_projection(projection):
    """Admit a protocol implementation only with an actual factory-issued binding."""
    if (
        not isinstance(projection, PhysicalEconomicProjection)
        or type(projection.source_binding) is not ValidatedSourceBinding
    ):
        raise TypeError(
            "A structural duck type alone is not a validated physical source projection"
        )
    binding = projection.source_binding.require_current()
    snapshot = binding.cached_snapshot
    if (
        projection.source is not binding.source
        or projection.window is not binding.window
        or projection.hydrogen_id != binding.hydrogen_id
        or projection.source_fingerprint != binding.fingerprint
        or dict(projection.quantities) != dict(snapshot.quantities)
        or tuple(projection.unresolved) != snapshot.unresolved
    ):
        raise ValueError("Projection cache differs from its actual validated source binding")
    return projection


@dataclass(frozen=True, slots=True)
class PhysicalCostProjection:
    source: object
    window: ReportingWindow
    hydrogen_id: str
    quantities: Mapping[str, float | None]
    unresolved: tuple[str, ...]
    source_fingerprint: str
    source_binding: ValidatedSourceBinding | None = None

    def __post_init__(self):
        if self.source_binding is None:
            # Preserve the original six-argument PV constructor only through a
            # fresh real source audit; supplied cache/fingerprint must still match.
            from .hydrogen_economics import PVSourceAdapter

            binding = ValidatedSourceBinding.bind(
                self.source, PVSourceAdapter(), self.window, hydrogen_id=self.hydrogen_id
            )
            object.__setattr__(self, "source_binding", binding)
        object.__setattr__(self, "quantities", MappingProxyType(dict(self.quantities)))
        object.__setattr__(self, "unresolved", tuple(self.unresolved))
        require_validated_projection(self)

    @classmethod
    def from_source(cls, source, adapter, window, *, hydrogen_id):
        binding = ValidatedSourceBinding.bind(source, adapter, window, hydrogen_id=hydrogen_id)
        snapshot = binding.cached_snapshot
        return cls(
            source,
            window,
            hydrogen_id,
            snapshot.quantities,
            snapshot.unresolved,
            binding.fingerprint,
            binding,
        )

    @classmethod
    def from_pv_electrolysis(cls, trace, window, *, hydrogen_id):
        from .hydrogen_economics import PVSourceAdapter

        return cls.from_source(trace, PVSourceAdapter(), window, hydrogen_id=hydrogen_id)

    @property
    def quantity_boundaries(self):
        return self.source_binding.cached_snapshot.boundaries

    @property
    def verification_kind(self):
        return self.source_binding.cached_snapshot.verification_kind

    def require_current(self):
        return require_validated_projection(self)

    def price_window(self, tariffs):
        return price_projection_window(self, tariffs)


@dataclass(frozen=True, slots=True)
class UtilityTariff:
    quantity: str
    usd_per_j: float
    currency: str
    base_year: int
    source_id: str
    billing_boundary_id: str
    origin: Origin

    def __post_init__(self):
        definition = quantity_definition(self.quantity)
        if not definition.billable or definition.unit != "J":
            raise ValueError("USD/J tariffs need an explicitly billable registered energy boundary")
        if self.currency != "USD" or finite(self.usd_per_j, "explicit USD/J tariff") < 0:
            raise ValueError(
                "Declare a nonnegative USD/J charge; no exchange rate/credit is inferred"
            )
        if type(self.base_year) is not int or self.base_year < 1:
            raise ValueError("Declare the explicit USD reference year")
        require_text(self.source_id, self.billing_boundary_id)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Resolve tariff origin or explicitly declare a synthetic quote")


@dataclass(frozen=True, slots=True)
class WindowUtilityCost:
    projection: PhysicalEconomicProjection
    line_items: tuple
    total_usd: float
    currency: str
    base_year: int
    physical_fingerprint: str
    _fingerprint: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        items = tuple(self.line_items)
        if not items or any(type(item) is not tuple or len(item) != 3 for item in items):
            raise ValueError("Retain each original tariff, physical amount and finite cost")
        if type(self.base_year) is not int or self.base_year < 1 or self.currency != "USD":
            raise ValueError("Retain an explicit USD currency and base year")
        if (not isinstance(self.physical_fingerprint, str)
                or len(self.physical_fingerprint) != 64):
            raise ValueError("Bind the priced window to a source fingerprint")
        object.__setattr__(self, "line_items", items)
        object.__setattr__(self, "_fingerprint", self._current_fingerprint())

    def _current_fingerprint(self):
        quote_rows = tuple(
            (id(quote), {f.name: getattr(quote, f.name) for f in dataclasses.fields(quote)},
             amount, cost)
            for quote, amount, cost in self.line_items
        )
        return snapshot_sha256((
            id(self.projection), self.physical_fingerprint, quote_rows, self.total_usd,
            self.currency, self.base_year,
        ))

    def require_current(self):
        if self._current_fingerprint() != self._fingerprint:
            raise ValueError("Finite utility cost receipt changed after construction")
        replay = price_projection_window(
            self.projection, tuple(item[0] for item in self.line_items)
        )
        if (
            replay.line_items != self.line_items
            or replay.total_usd != self.total_usd
            or replay.currency != self.currency
            or replay.base_year != self.base_year
            or replay.physical_fingerprint != self.physical_fingerprint
        ):
            raise ValueError("Finite utility cost/quote/source correspondence changed")
        return self


def price_projection_window(projection, tariffs):
    """Single public finite tariff implementation, independent of source/provider."""
    require_validated_projection(projection)
    prices = tuple(tariffs)
    if not prices or not all(type(p) is UtilityTariff for p in prices):
        raise TypeError("Supply actual explicit UtilityTariff objects")
    for price in prices:
        # Revalidate current fields while retaining the caller's original quote.
        UtilityTariff(**{f.name: getattr(price, f.name) for f in dataclasses.fields(price)})
    if len({(p.currency, p.base_year) for p in prices}) != 1:
        raise ValueError("All finite tariff currency/reference years must agree")
    snapshot = projection.source_binding.cached_snapshot
    used, items = set(), []
    for price in prices:
        if price.quantity not in snapshot.quantities:
            raise ValueError("Tariff quantity is absent/not applicable to this actual source")
        amount = snapshot.quantities[price.quantity]
        if amount is None:
            raise ValueError("Unknown physical utility is not zero cost")
        components = set(snapshot.boundaries[price.quantity].billing_components)
        if used & components:
            raise ValueError(
                "Tariff aliases/aggregate components would bill the same physical transfer twice"
            )
        used.update(components)
        items.append(
            (price, amount, finite(amount * price.usd_per_j, "finite utility window cost"))
        )
    require_validated_projection(projection)
    return WindowUtilityCost(
        projection,
        tuple(items),
        finite_sum((v[2] for v in items), "finite window cost"),
        prices[0].currency,
        prices[0].base_year,
        projection.source_fingerprint,
    )
