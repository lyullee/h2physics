"""Finite physical reporting to optional native pyH2A discounted cash flow.

Implemented_unverified: no native execution performed for this development.
No finance, discount, tax or depreciation equation is implemented here.
"""

import contextlib
import copy
import dataclasses
import hashlib
import importlib
import importlib.metadata
import inspect
import io
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import numpy as np

from ..core import immutable_array, Origin, finite
from .physical_economics import (
    PhysicalCostProjection as PhysicalCostProjection,
)
from .physical_economics import (
    PhysicalEconomicProjection,
    QuantityBoundary,
    SourceSnapshot,
    WindowUtilityCost,
    callable_identity,
    finite_sum,
    quantity_definition,
    require_validated_projection,
    snapshot_sha256,
    stable_snapshot,
)
from .physical_economics import (
    ReportingWindow as ReportingWindow,
)
from .physical_economics import (
    UtilityTariff as UtilityTariff,
)
from .pv_electrolysis import PVElectrolysisTrace
from .pv_electrolysis import _definition as _pv_definition

STATUS = "implemented_unverified"
VERSION = "0.0a8"
PACKAGE_SHA256 = "a69e8c5a3e89dbd6ee6ff1f5477c0707560b6bf95d2d3b04171382dcfd078d84"
FINANCIAL_KEYS = frozenset(
    (
        "ref year",
        "startup year",
        "basis year",
        "current year capital costs",
        "startup time",
        "plant life",
        "depreciation length",
        "depreciation type",
        "equity",
        "interest",
        "debt",
        "startup cost fixed",
        "startup revenues",
        "startup cost variable",
        "decommissioning",
        "salvage",
        "inflation",
        "irr",
        "state tax",
        "federal tax",
        "working capital",
    )
)
WORKFLOW = (
    "production_scaling",
    "initial_equity_depreciable_capital",
    "non_depreciable_capital_costs",
    "replacement_costs",
    "fixed_operating_costs",
    "variable_operating_costs",
)
ANNUAL_ARRAYS = (
    "years",
    "plant_years",
    "annual_sales",
    "annual_revenue",
    "annual_taxes",
    "annual_pre_depreciation_income",
    "after_tax_income",
    "annual_charge",
    "annual_replacement_costs",
    "annual_initial_depreciable_capital",
    "annual_non_depreciable_capital",
    "fixed_operating_costs",
    "variable_operating_costs",
    "interest_per_year",
    "principal_payment",
    "working_capital_reserve",
    "decommissioning_costs",
    "salvage_income",
)


def _text(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(
            "Declare source, clock, grade, reporting and financial evidence identities"
        )


def _positive_integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be an explicit positive integer")
    return value


# Compatibility aliases for existing owner internals; public hooks live in physical_economics.
_sum = finite_sum
_digest = snapshot_sha256


def _array(value):
    result = np.array(value, dtype=float, copy=True)
    if result.ndim != 1 or not np.all(np.isfinite(result)):
        raise ValueError("Native annual output must be a finite one-dimensional array")
    result = immutable_array(result, name="result")
    return result


def _pv_values(trace, window, hydrogen_id):
    if type(trace) is not PVElectrolysisTrace or not trace.steps:
        raise TypeError("Supply an actual nonempty PVElectrolysisTrace")
    if not isinstance(window, ReportingWindow):
        raise TypeError("Supply an actual explicit ReportingWindow")
    ReportingWindow(
        window.start_s,
        window.end_s,
        window.clock_id,
        window.evidence_id,
        window.selected_product_basis,
        window.mass_tolerance_kg,
    )
    if (
        window.start_s != trace.initial.time_s
        or window.end_s != trace.final.time_s
        or window.clock_id != trace.evidence.clock_id
    ):
        raise ValueError("Reporting window must exactly match this entire physical trace/clock")
    candidates = tuple(s for s in trace.caloric_provider.species if s.identifier == hydrogen_id)
    if (
        len(candidates) != 1
        or dict(candidates[0].elements) != {"H": 2}
        or candidates[0].charge
        or candidates[0].phase not in {"gas", "vapor", "ideal-gas"}
    ):
        raise ValueError("Select the actual neutral H2 species; no mol-to-mass basis is inferred")
    molar_mass = finite(candidates[0].molar_mass_kg_mol, "H2 molar mass", positive=True)
    if molar_mass != trace.stack.geometry.hydrogen_molar_mass_kg_mol:
        raise ValueError("Physical stack and inventory H2 molar-mass bases differ")
    records, previous = [], trace.initial
    for step in trace.steps:
        stage = step.point.stage
        if (
            step.before is not previous
            or step.before.time_s != stage.start_s
            or step.after.time_s != stage.end_s
            or stage.clock_id != window.clock_id
        ):
            raise ValueError("Physical ledger steps must be original contiguous source states")
        row = {
            name: finite(getattr(step, name), name)
            for name in (
                "extent_mol_h2",
                "electricity_j",
                "pv_electricity_j",
                "stack_heat_rejected_j",
                "receiver_heat_into_j",
                "caloric_residual_j",
                "mass_residual_kg",
            )
        }
        if min(row[k] for k in ("extent_mol_h2", "electricity_j", "pv_electricity_j")) < 0:
            raise ValueError(
                "Production/electricity ledger cannot be negative in this one-way source"
            )
        change = (
            step.after.amounts_mol.get(hydrogen_id, 0.0)
            - step.before.amounts_mol.get(hydrogen_id, 0.0)
        ) * molar_mass
        if abs(change - row["extent_mol_h2"] * molar_mass) > window.mass_tolerance_kg:
            raise ValueError(
                "Physical H2 inventory change differs from generated extent; no unrecorded sales"
            )
        records.append(
            (
                stage.identifier,
                stage.start_s,
                stage.end_s,
                stage.source_id,
                row,
                _stock_signature(step.before),
                _stock_signature(step.after),
            )
        )
        previous = step.after
    if previous is not trace.final:
        raise ValueError("Physical final pointer differs from its last original ledger state")
    initial = (
        finite(trace.initial.amounts_mol.get(hydrogen_id, 0.0), "initial H2 inventory") * molar_mass
    )
    final = finite(trace.final.amounts_mol.get(hydrogen_id, 0.0), "final H2 inventory") * molar_mass
    if min(initial, final) < 0:
        raise ValueError("Finite H2 stocks cannot be negative")
    generated = _sum((r[4]["extent_mol_h2"] * molar_mass for r in records), "generated H2 mass")
    quantities = dict(
        generated_h2_kg=generated,
        receiver_initial_h2_kg=initial,
        receiver_final_h2_kg=final,
        receiver_stock_increase_kg=final - initial,
        stack_electricity_j=_sum((r[4]["electricity_j"] for r in records), "stack electricity"),
        pv_electricity_j=_sum((r[4]["pv_electricity_j"] for r in records), "PV generation"),
        stack_heat_rejected_j=_sum(
            (r[4]["stack_heat_rejected_j"] for r in records), "stack rejected heat"
        ),
        receiver_heat_into_j=_sum((r[4]["receiver_heat_into_j"] for r in records), "receiver heat"),
    )
    # Native production model currently supplies no export/sale ledger or priced
    # external pressure-work amount. None is deliberately not converted to zero.
    quantities["exported_sale_h2_kg"] = None
    for prefix, source_key, input_sign in (
        ("stack", "stack_heat_rejected_j", -1),
        ("receiver", "receiver_heat_into_j", 1),
    ):
        quantities[prefix + "_heat_input_j"] = _sum(
            (max(input_sign * r[4][source_key], 0.0) for r in records), "gross heat input"
        )
        quantities[prefix + "_heat_rejection_j"] = _sum(
            (max(-input_sign * r[4][source_key], 0.0) for r in records), "gross heat rejection"
        )
    quantities["external_pressure_work_j"] = trace.required_external_pressure_work_j
    gaps = ["exported_sale_not_observed"]
    if trace.required_external_pressure_work_j is None:
        gaps.append("external_pressure_work_amount_unresolved")
    else:
        finite(trace.required_external_pressure_work_j, "external pressure work")
    if not trace.full_plant_energy_closed:
        gaps.append("full_plant_energy_or_auxiliaries_unresolved")
    if not trace.thermal_utility_availability_solved:
        gaps.append("thermal_utility_supply_unresolved")
    if not trace.water_oxygen_vessel_dynamics_solved:
        gaps.append("water_oxygen_boundary_unresolved")
    payload = (
        window.start_s,
        window.end_s,
        window.clock_id,
        window.evidence_id,
        window.selected_product_basis,
        window.mass_tolerance_kg,
        hydrogen_id,
        molar_mass,
        records,
        quantities,
        gaps,
        trace.caloric_provider.basis_id,
        trace.native_pv.source_sha256,
        trace.energy_coordinate,
        trace.pressure_work_resolved,
        trace.evidence.source_id,
    )
    return quantities, tuple(gaps), _digest(payload)


def _stock_signature(stock):
    state = stock.receiver
    for name in ("pressure_pa", "temperature_k", "density_kg_m3"):
        finite(getattr(state, name), "source receiver " + name, positive=True)
    return (
        stock.time_s,
        dict(stock.amounts_mol),
        stock.receiver_internal_energy_j,
        state.basis.fluid,
        state.basis.reference_id,
        state.basis.spin_composition,
        state.pressure_pa,
        state.temperature_k,
        state.density_kg_m3,
        state.enthalpy_j_kg,
        state.internal_energy_j_kg,
        state.entropy_j_kg_k,
        state.phase,
    )


def _native_cache_snapshot(value, native):
    if isinstance(value, native.pandas.DataFrame):
        return {
            "kind": "native-pandas-frame",
            "columns": tuple(value.columns),
            "index": tuple(value.index),
            "dtypes": tuple(str(v) for v in value.dtypes),
            "values": value.to_numpy(copy=True),
        }
    return value


@dataclass(frozen=True, slots=True)
class PVSourceAdapter:
    """PV reporting auditor; native definitions/caches are read, not recomputed."""

    identifier: str = "h2physics-pv-electrolysis-source-v2"

    def snapshot(self, source, window, hydrogen_id):
        source.require_current()
        q, gaps, _ = _pv_values(source, window, hydrogen_id)
        q.update(
            initial_h2_stock_kg=q["receiver_initial_h2_kg"],
            final_h2_stock_kg=q["receiver_final_h2_kg"],
            h2_stock_increase_kg=q["receiver_stock_increase_kg"],
            harvested_h2_kg=None,
            sold_h2_kg=None,
            electrical_work_into_j=q["stack_electricity_j"],
            required_heat_input_j=finite_sum(
                (q["stack_heat_input_j"], q["receiver_heat_input_j"]), "PV total heating"
            ),
            required_heat_rejection_j=finite_sum(
                (q["stack_heat_rejection_j"], q["receiver_heat_rejection_j"]), "PV total rejection"
            ),
        )
        uid = source.evidence.source_id
        basis = source.caloric_provider.basis_id
        components = {
            "electrical_work_into_j": (uid + ":direct-DC",),
            "stack_electricity_j": (uid + ":direct-DC",),
            "pv_electricity_j": (uid + ":direct-DC",),
            "required_heat_input_j": (uid + ":stack-heating", uid + ":receiver-heating"),
            "required_heat_rejection_j": (uid + ":stack-rejection", uid + ":receiver-rejection"),
            "stack_heat_input_j": (uid + ":stack-heating",),
            "receiver_heat_input_j": (uid + ":receiver-heating",),
            "stack_heat_rejection_j": (uid + ":stack-rejection",),
            "receiver_heat_rejection_j": (uid + ":receiver-rejection",),
            "external_pressure_work_j": (uid + ":pressure-work",),
        }
        boundaries = {
            name: QuantityBoundary(
                name,
                uid + ":" + quantity_definition(name).boundary_role,
                basis,
                window.evidence_id,
                components.get(name, ()),
            )
            for name in q
        }
        identities = [
            source,
            source.initial,
            source.final,
            source.native_pv,
            source.native_system,
            source.stack,
            source.stack.geometry,
            source.stack.thermochemistry,
            source.gas,
            source.caloric_provider,
            *source.gas.native_objects,
            *callable_identity(source.gas.state_pt),
            *callable_identity(source.native_pv.require_current),
            *callable_identity(source.stack.evaluate),
            *callable_identity(source.stack.thermochemistry),
        ]
        for function in getattr(source.caloric_provider, "functions", ()):
            identities.extend(callable_identity(function))
        caches = []
        for step in source.steps:
            point = step.point
            if point.pv.native_system is not source.native_system:
                raise ValueError("Native PV cache lost its actual system identity")
            identities.extend(
                (
                    step,
                    step.before,
                    step.after,
                    point,
                    point.pv,
                    point.stage,
                    point.stack,
                    point.native_root_result,
                    point.pv.native_iv_result,
                    point.pv.native_scaled_iv,
                    step.native_conversion,
                    step.native_conversion.reaction,
                    step.native_conversion.initial_mol,
                    step.native_conversion.final_mol,
                    step.native_inlet_state,
                )
            )
            identities.extend(point.probes)
            root = (
                None
                if point.native_root_result is None
                else {
                    name: getattr(point.native_root_result, name)
                    for name in ("root", "converged", "iterations", "function_calls", "flag")
                }
            )
            c = step.native_conversion
            caches.append(
                (
                    point.stage,
                    point.stack,
                    point.mode,
                    point.topology,
                    point.status,
                    point.pv_voltage_v,
                    point.pv_current_a,
                    point.pv_power_w,
                    point.load_line_residual_a,
                    point.undrawn_mpp_headroom_w,
                    point.probes,
                    point.pv.native_parameters,
                    _native_cache_snapshot(point.pv.native_iv_result, source.native_pv),
                    _native_cache_snapshot(point.pv.native_scaled_iv, source.native_pv),
                    root,
                    (
                        c.reaction.identifier,
                        c.reaction.coefficients,
                        c.extent_mol,
                        c.initial_mol,
                        c.final_mol,
                        c.maximum_roundoff_correction_mol,
                        c.reaction.species,
                    ),
                    {
                        f.name: getattr(step, f.name)
                        for f in dataclasses.fields(step)
                        if f.name not in {"point", "before", "after", "native_conversion"}
                    },
                    step.before.receiver,
                    step.after.receiver,
                )
            )
        for loss in source.stack.losses.values():
            identities.extend((loss, *callable_identity(loss)))
            if hasattr(loss, "__dataclass_fields__"):
                identities.extend(
                    getattr(loss, n)
                    for n in loss.__dataclass_fields__
                    if callable(getattr(loss, n))
                )
        source.require_current()
        content = (
            source.evidence,
            source.pressure_boundary,
            source.stack.geometry,
            _pv_definition(source.native_system),
            source.gas.basis,
            source.caloric_provider.basis_id,
            getattr(source.caloric_provider, "temperature_bounds_k", None),
            getattr(source.caloric_provider, "pressure_bounds_pa", None),
            tuple(
                (s.identifier, dict(s.elements), s.molar_mass_kg_mol, s.phase, s.charge)
                for s in source.caloric_provider.species
            ),
            caches,
            q,
            gaps,
            source.status,
            source.energy_coordinate,
            source.continuous_pressure_feedback,
            source.full_plant_energy_closed,
            source.pressure_work_resolved,
            source.thermal_utility_availability_solved,
            source.water_oxygen_vessel_dynamics_solved,
        )
        return SourceSnapshot(
            source,
            window,
            hydrogen_id,
            uid,
            "PV producer-issued original result and structural/native/cache audit; no physical replay",
            q,
            boundaries,
            gaps,
            stable_snapshot(content),
            tuple(identities),
        )


@dataclass(frozen=True, slots=True)
class AnnualFinancialBasis:
    currency: str
    base_year: int
    operating_year_label: int
    seconds_in_operating_year: float
    annual_product_kg_at_gate: float
    annual_generated_h2_kg: float
    annual_initial_h2_inventory_kg: float
    annual_final_h2_inventory_kg: float
    annual_nonproduct_h2_out_kg: float
    product_grade_id: str
    product_pressure_pa: float
    product_gate_evidence_id: str
    representation: str
    representation_evidence_id: str
    annual_inventory_reconciliation_id: str
    annual_repetition_evidence_id: str
    capacity_factor: float | None
    capacity_factor_evidence_id: str
    unresolved_cost_resolutions: Mapping[str, str]
    window_repetitions: float | None = None
    origin: Origin = Origin.UNRESOLVED

    def __post_init__(self):
        if self.currency != "USD":
            raise ValueError("Reviewed native monetary basis is USD; no exchange rate is supplied")
        _positive_integer(self.base_year, "constant-dollar reference year")
        _positive_integer(self.operating_year_label, "operating year label")
        finite(self.seconds_in_operating_year, "explicit annual duration seconds", positive=True)
        finite(self.annual_product_kg_at_gate, "explicit annual gate production kg", positive=True)
        for name in (
            "annual_generated_h2_kg",
            "annual_initial_h2_inventory_kg",
            "annual_final_h2_inventory_kg",
            "annual_nonproduct_h2_out_kg",
        ):
            if finite(getattr(self, name), name) < 0:
                raise ValueError(
                    "Annual H2 production/stocks/nonproduct removal must be explicit and nonnegative"
                )
        if not math.isclose(
            self.annual_initial_h2_inventory_kg,
            self.annual_final_h2_inventory_kg,
            abs_tol=1e-10,
            rel_tol=1e-10,
        ):
            raise ValueError(
                "Constant repeated annual production cannot draw down startup inventory every year"
            )
        if not math.isclose(
            self.annual_generated_h2_kg - self.annual_nonproduct_h2_out_kg,
            self.annual_product_kg_at_gate,
            abs_tol=1e-10,
            rel_tol=1e-10,
        ):
            raise ValueError(
                "Explicit annual generated/product/nonproduct H2 reconciliation failed"
            )
        finite(self.product_pressure_pa, "product pressure Pa absolute", positive=True)
        _text(
            self.product_grade_id,
            self.product_gate_evidence_id,
            self.representation_evidence_id,
            self.annual_inventory_reconciliation_id,
            self.annual_repetition_evidence_id,
            self.capacity_factor_evidence_id,
        )
        if (
            self.capacity_factor is not None
            and not 0 < finite(self.capacity_factor, "capacity factor") <= 1
        ):
            raise ValueError(
                "Declared capacity factor must lie in (0,1]; it is never reapplied to annual kg"
            )
        if self.representation not in {"independent_annual_inputs", "explicit_window_repetition"}:
            raise ValueError(
                "Declare independent annual evidence or explicit representative-window repetition"
            )
        if self.representation == "explicit_window_repetition":
            finite(self.window_repetitions, "explicit window multiplicity", positive=True)
        elif self.window_repetitions is not None:
            raise ValueError(
                "Independent annual quantities must not also use a trajectory multiplier"
            )
        resolutions = dict(self.unresolved_cost_resolutions)
        for key, value in resolutions.items():
            _text(key, value)
        object.__setattr__(self, "unresolved_cost_resolutions", MappingProxyType(resolutions))
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError(
                "Annual economics needs declared source or explicit synthetic evidence"
            )

    def require(self, projection):
        require_validated_projection(projection)
        if set(projection.unresolved) - set(self.unresolved_cost_resolutions):
            raise ValueError(
                "Explicitly resolve every physical cost/export gap; None is not zero cost"
            )
        if self.representation == "explicit_window_repetition":
            quantities = projection.source_binding.cached_snapshot.quantities
            selected = projection.window.selected_product_basis
            physical = quantities[selected]
            role = quantity_definition(selected).product_role
            expected = finite(physical * self.window_repetitions, "declared repeated-window kg")
            target = (
                self.annual_generated_h2_kg
                if role in {"generated", "stock_change"}
                else self.annual_product_kg_at_gate
            )
            if role == "stock_change":
                generated = quantities.get("generated_h2_kg")
                if generated is None or not math.isclose(
                    physical, generated, rel_tol=1e-10, abs_tol=projection.window.mass_tolerance_kg
                ):
                    raise ValueError(
                        "A stock change is not automatically generated production; supply independent annual evidence"
                    )
            if not math.isclose(expected, target, rel_tol=1e-10, abs_tol=1e-12):
                raise ValueError(
                    "Annual kg differ from the explicitly selected generated/harvest/sale physical-window role"
                )
            covered = (
                projection.window.end_s - projection.window.start_s
            ) * self.window_repetitions
            if not math.isclose(
                covered, self.seconds_in_operating_year, rel_tol=1e-10, abs_tol=1e-6
            ):
                raise ValueError(
                    "Declared window repetitions do not cover the explicitly supplied annual duration"
                )
        return self


@dataclass(frozen=True, slots=True)
class AnnualFinancialInputs:
    """All native financial scalars and annual monetary quantities are caller inputs."""

    financial_values: Mapping[str, float | str]
    construction_fractions: tuple[float, ...]
    depreciable_capital_usd: float
    nondepreciable_capital_usd: float
    fixed_operating_cost_usd_year: float
    variable_operating_cost_usd_year: float
    additional_variable_cost_usd_year: float
    replacement_usd_by_analysis_year: tuple[float, ...]
    financial_evidence: Mapping[str, str]
    utility_scope_evidence_id: str
    variable_cost_annual_basis_id: str
    capital_scope_evidence_id: str
    native_lookup_evidence_id: str

    def __post_init__(self):
        values, evidence = dict(self.financial_values), dict(self.financial_evidence)
        if set(values) != FINANCIAL_KEYS or set(evidence) != FINANCIAL_KEYS:
            raise ValueError(
                "Supply every native financial field and its evidence; no default financial values"
            )
        for key, value in evidence.items():
            _text(key, value)
        for key in FINANCIAL_KEYS - {"debt", "depreciation type"}:
            finite(values[key], "native financial input " + key)
        if values["debt"] != "Constant" or values["depreciation type"] != "MACRS":
            raise ValueError(
                "Reviewed engine implements Constant debt and MACRS; unsupported labels cannot change its law"
            )
        for key in (
            "ref year",
            "startup year",
            "basis year",
            "current year capital costs",
            "plant life",
            "depreciation length",
        ):
            _positive_integer(values[key], key)
        startup = values["startup time"]
        if (
            isinstance(startup, bool)
            or not isinstance(startup, int)
            or not 0 <= startup < values["plant life"]
        ):
            raise ValueError("Startup time must be an integer within the declared operating life")
        for key in (
            "equity",
            "startup cost fixed",
            "startup revenues",
            "startup cost variable",
            "decommissioning",
            "salvage",
            "state tax",
            "federal tax",
            "working capital",
        ):
            if not 0 <= values[key] <= 1:
                raise ValueError(
                    "Native financial fractional fields must be explicit numbers in [0,1]"
                )
        if min(values["interest"], values["irr"], values["inflation"]) < 0:
            raise ValueError(
                "This restricted bridge admits nonnegative interest/IRR/inflation only"
            )
        if values["state tax"] == 1 or values["federal tax"] == 1:
            raise ValueError("A fully taxed sales denominator is outside this native cost bridge")
        fractions = tuple(
            finite(v, "construction allocation fraction") for v in self.construction_fractions
        )
        if (
            not fractions
            or min(fractions) < 0
            or not math.isclose(
                _sum(fractions, "construction fractions"), 1.0, abs_tol=1e-12, rel_tol=0
            )
        ):
            raise ValueError("Declare the complete ordered construction allocation summing to one")
        replacement = tuple(
            finite(v, "replacement USD") for v in self.replacement_usd_by_analysis_year
        )
        if len(replacement) != len(fractions) + values["plant life"] or min(replacement) < 0:
            raise ValueError(
                "Explicit replacement amounts must cover every construction and operating year"
            )
        if any(replacement[: len(fractions)]):
            raise ValueError(
                "Native engine zeroes construction-year replacements; nonzero requests are refused"
            )
        for name in (
            "depreciable_capital_usd",
            "nondepreciable_capital_usd",
            "fixed_operating_cost_usd_year",
            "variable_operating_cost_usd_year",
            "additional_variable_cost_usd_year",
        ):
            if finite(getattr(self, name), name) < 0:
                raise ValueError("This bridge admits nonnegative explicit capital/operating costs")
        _text(
            self.utility_scope_evidence_id,
            self.variable_cost_annual_basis_id,
            self.capital_scope_evidence_id,
            self.native_lookup_evidence_id,
        )
        object.__setattr__(self, "financial_values", MappingProxyType(values))
        object.__setattr__(self, "financial_evidence", MappingProxyType(evidence))
        object.__setattr__(self, "construction_fractions", fractions)
        object.__setattr__(self, "replacement_usd_by_analysis_year", replacement)


def _package_hash(root):
    digest = hashlib.sha256()
    for path in sorted(
        (p for p in root.rglob("*") if p.is_file() and p.suffix not in {".pyc", ".pyo"}),
        key=lambda p: p.relative_to(root).as_posix(),
    ):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _bindings(module):
    result = []
    for name, value in vars(module).items():
        if inspect.isfunction(value):
            result.append((name, value, value.__code__))
    for name, value in vars(module.Discounted_Cash_Flow).items():
        if inspect.isfunction(value):
            result.append(("class:" + name, value, value.__code__))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class NativeHydrogenEconomics:
    module: object
    native_class: object
    root: Path
    source_sha256: str
    call_bindings: tuple

    @classmethod
    def from_installed(cls):
        """Explicit optional import only; never install or mutate sys.path."""
        if importlib.metadata.version("pyH2A") != VERSION:
            raise ValueError("Install the explicitly reviewed pyH2A0.0a8 distribution")
        module = importlib.import_module("pyH2A.Discounted_Cash_Flow")
        root = Path(module.__file__).resolve().parent
        actual = _package_hash(root)
        if actual != PACKAGE_SHA256:
            raise ValueError("Native package/resources differ from the reviewed wheel")
        return cls(module, module.Discounted_Cash_Flow, root, actual, _bindings(module))

    def require_current(self):
        if (
            self.module.__name__ != "pyH2A.Discounted_Cash_Flow"
            or importlib.import_module("pyH2A.Discounted_Cash_Flow") is not self.module
            or Path(self.module.__file__).resolve().parent != self.root.resolve()
            or self.native_class.__module__ != self.module.__name__
            or Path(self.native_class.__init__.__code__.co_filename).resolve()
            != Path(self.module.__file__).resolve()
            or importlib.metadata.version("pyH2A") != VERSION
            or self.native_class is not self.module.Discounted_Cash_Flow
            or self.source_sha256 != PACKAGE_SHA256
            or _package_hash(self.root) != PACKAGE_SHA256
            or _bindings(self.module) != self.call_bindings
        ):
            raise ValueError("Native financial source/class/function bindings changed")

    def require_lookup_domain(self, basis, inputs):
        values = inputs.financial_values
        if (
            not values["startup year"]
            <= basis.operating_year_label
            < values["startup year"] + values["plant life"]
        ):
            raise ValueError(
                "Representative operating-year label lies outside the explicit financial life"
            )
        if any(
            values[k] != basis.base_year
            for k in ("ref year", "basis year", "current year capital costs")
        ):
            raise ValueError(
                "Explicit monetary/reference/capital years must equal the declared USD base year"
            )
        # Reject the native nearest-year/nearest-MACRS fallback before invocation.
        for filename in (
            "Plant_Cost_Index.csv",
            "GDP_Implicit_Deflator_Price_Index.csv",
            "Labor_Index.csv",
            "SRI_Chemical_Price_Index.csv",
        ):
            rows = (self.root / "Lookup_Tables" / filename).read_text().splitlines()
            years = {
                float(line.split()[0])
                for line in rows
                if line.strip() and not line.lstrip().startswith("#")
            }
            if float(basis.base_year) not in years:
                raise ValueError(
                    "Declared monetary year is absent from an actual native lookup; no nearest-year substitution"
                )
        header = (self.root / "Lookup_Tables/MACRS.csv").read_text().splitlines()[0].split()
        if values["depreciation length"] not in tuple(float(v) for v in header[1:]):
            raise ValueError("Depreciation length is absent from the actual native MACRS table")


class HydrogenEconomicsError(ValueError):
    def __init__(
        self,
        message,
        *,
        projection,
        annual_basis,
        inputs,
        native=None,
        native_input=None,
        native_stdout="",
        native_provider=None,
        window_cost=None,
    ):
        super().__init__(message)
        self.projection, self.annual_basis, self.inputs = projection, annual_basis, inputs
        self.native_object, self.native_input = native, native_input
        self.native_stdout, self.native_provider = native_stdout, native_provider
        self.window_utility_cost = window_cost


_PENDING_ECONOMICS_RESULT_TOKENS: set[object] = set()


@dataclass(frozen=True, slots=True)
class HydrogenEconomicsResult:
    lcoh_usd_kg: float
    denominator: str
    currency: str
    base_year: int
    projection: PhysicalEconomicProjection
    annual_basis: AnnualFinancialBasis
    financial_inputs: AnnualFinancialInputs
    window_utility_cost: WindowUtilityCost | None
    native_provider: NativeHydrogenEconomics
    native_object: object
    native_input_before: Mapping
    native_npv: Mapping
    native_contributions: Mapping
    annual_arrays: Mapping
    native_cash_flow_return: float
    native_stdout: str
    input_fingerprint: str
    status: str = STATUS
    _issuer_token: object = dataclasses.field(default=None, repr=False, compare=False)
    _seal: str = dataclasses.field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ECONOMICS_RESULT_TOKENS:
            raise ValueError("Economics results are issued only by the native evaluation path")
        _PENDING_ECONOMICS_RESULT_TOKENS.remove(self._issuer_token)
        if type(self.native_object) is not self.native_provider.native_class:
            raise TypeError("Retain the exact admitted native economics object")
        if self.native_object.h2_cost != self.lcoh_usd_kg:
            raise ValueError("Issued LCOH must equal the actual native result")
        object.__setattr__(self, "_seal", self._content_fingerprint())

    def _content_fingerprint(self):
        return _digest((
            self.lcoh_usd_kg, self.denominator, self.currency, self.base_year,
            id(self.projection), self.projection.source_fingerprint,
            {n: getattr(self.annual_basis, n) for n in self.annual_basis.__dataclass_fields__},
            {n: getattr(self.financial_inputs, n) for n in self.financial_inputs.__dataclass_fields__},
            None if self.window_utility_cost is None else self.window_utility_cost._fingerprint,
            id(self.native_provider), self.native_provider.source_sha256, id(self.native_object),
            self.native_object.h2_cost, self.native_object.npv_dict,
            self.native_object.contributions,
            {name: np.asarray(getattr(self.native_object, name)) for name in ANNUAL_ARRAYS},
            dict(self.native_input_before), dict(self.native_npv), self.native_contributions,
            {k: np.asarray(v) for k, v in self.annual_arrays.items()},
            self.native_cash_flow_return, self.native_stdout, self.input_fingerprint, self.status,
        ))

    def require_current(self):
        self.projection.require_current()
        self.native_provider.require_current()
        if self.window_utility_cost is not None:
            self.window_utility_cost.require_current()
        expected_input_fingerprint = _digest((
            dict(self.native_input_before), self.projection.source_fingerprint,
            {n: getattr(self.annual_basis, n) for n in self.annual_basis.__dataclass_fields__},
            {n: getattr(self.financial_inputs, n) for n in self.financial_inputs.__dataclass_fields__},
            None if self.window_utility_cost is None else (
                self.window_utility_cost.total_usd,
                [(vars_from_tariff(p), amount, cost)
                 for p, amount, cost in self.window_utility_cost.line_items],
            ),
        ))
        if expected_input_fingerprint != self.input_fingerprint:
            raise ValueError("Native economic input fingerprint changed after evaluation")
        if self.native_object.h2_cost != self.lcoh_usd_kg:
            raise ValueError("Retained native LCOH no longer matches the issued result")
        if _digest(self.native_object.npv_dict) != _digest(dict(self.native_npv)):
            raise ValueError("Native NPV output changed after economics result issuance")
        if self._content_fingerprint() != self._seal:
            raise ValueError("Native economics result or its retained basis changed")
        return self


def native_input_dictionary(annual_basis, financial_inputs):
    """Build complete direct-dict native inputs; do not load packaged Defaults.md."""
    f = financial_inputs
    return {
        "Financial Input Values": {k: {"Value": v} for k, v in f.financial_values.items()},
        "Construction": {
            f"construction-{i + 1}": {"Value": v} for i, v in enumerate(f.construction_fractions)
        },
        "Workflow": {
            name: {"Type": "function", "Position": i + 1} for i, name in enumerate(WORKFLOW)
        },
        "Technical Operating Parameters and Specifications": {
            "Output per Year at Gate": {"Value": annual_basis.annual_product_kg_at_gate}
        },
        "Depreciable Capital Costs": {"Inflated": {"Value": f.depreciable_capital_usd}},
        "Non-Depreciable Capital Costs": {"Inflated": {"Value": f.nondepreciable_capital_usd}},
        "Fixed Operating Costs": {"Total": {"Value": f.fixed_operating_cost_usd_year}},
        "Variable Operating Costs": {"Total": {"Value": f.variable_operating_cost_usd_year}},
        "Replacement": {
            "Total": {"Value": np.array(f.replacement_usd_by_analysis_year, dtype=float)}
        },
    }


def evaluate_hydrogen_economics(
    projection, annual_basis, financial_inputs, *, native, window_cost=None
):
    """Execute only on explicit call; preserve the actual native object even on failure."""
    if not isinstance(native, NativeHydrogenEconomics):
        raise TypeError("Supply the actual reviewed native provider")
    if not isinstance(annual_basis, AnnualFinancialBasis) or not isinstance(
        financial_inputs, AnnualFinancialInputs
    ):
        raise TypeError("Supply explicit annual representativeness and complete financial inputs")
    # Revalidate every current field; frozen dataclasses are not a permission to
    # bypass a nested/native boundary with mutated prior evidence.
    basis = AnnualFinancialBasis(
        **{n: getattr(annual_basis, n) for n in annual_basis.__dataclass_fields__}
    )
    inputs = AnnualFinancialInputs(
        **{n: getattr(financial_inputs, n) for n in financial_inputs.__dataclass_fields__}
    )
    basis.require(projection)
    if window_cost is not None:
        if type(window_cost) is not WindowUtilityCost or window_cost.projection is not projection:
            raise ValueError("Window utility cost must bind this exact physical projection")
        WindowUtilityCost.require_current(window_cost)
        if (window_cost.currency, window_cost.base_year) != (basis.currency, basis.base_year):
            raise ValueError("Window utility price and annual currency/reference years differ")
    if basis.representation == "explicit_window_repetition":
        if window_cost is None:
            raise ValueError(
                "Representative-window economics requires actual finite utility pricing"
            )
        expected = finite(
            window_cost.total_usd * basis.window_repetitions
            + inputs.additional_variable_cost_usd_year,
            "explicit linked annual variable cost",
        )
        if not math.isclose(
            expected, inputs.variable_operating_cost_usd_year, rel_tol=1e-10, abs_tol=1e-9
        ):
            raise ValueError(
                "Native annual variable cost does not match explicit priced-window linkage"
            )
    native.require_current()
    native.require_lookup_domain(basis, inputs)
    original = native_input_dictionary(basis, inputs)
    fingerprint = _digest(
        (
            original,
            projection.source_fingerprint,
            {n: getattr(basis, n) for n in basis.__dataclass_fields__},
            {n: getattr(inputs, n) for n in inputs.__dataclass_fields__},
            None
            if window_cost is None
            else (
                window_cost.total_usd,
                [(vars_from_tariff(p), amount, cost) for p, amount, cost in window_cost.line_items],
            ),
        )
    )
    attempted, output = None, io.StringIO()
    try:
        # Allocate before __init__ so partial native inputs/arrays survive failure.
        attempted = native.native_class.__new__(native.native_class)
        with contextlib.redirect_stdout(output):
            native.native_class.__init__(
                attempted, copy.deepcopy(original), print_info=False, check_processing=False
            )
            raw_cash_flow = attempted.cash_flow()
        native.require_current()
        require_validated_projection(projection)
        if window_cost is not None:
            WindowUtilityCost.require_current(window_cost)
        if _digest(original) != _digest(native_input_dictionary(basis, inputs)):
            raise ValueError("Caller-owned financial inputs mutated during native execution")
        # Native cash_flow warns rather than raises on its own failed NPV gate.
        # Preserve and refuse any native diagnostic warning; never replace its law.
        if "Warning:" in output.getvalue():
            raise ValueError(
                "Native economic engine emitted a warning; inspect retained original stdout/object"
            )
        cost = finite(attempted.h2_cost, "native levelized hydrogen cost USD/kg")
        denominator = finite(
            attempted.npv_dict["h2_sales"], "native discounted H2 denominator", positive=True
        )
        if cost < 0 or attempted.output_per_year_at_gate != basis.annual_product_kg_at_gate:
            raise ValueError("Native cost/production denominator differs from its admitted inputs")
        arrays = {name: _array(getattr(attempted, name)) for name in ANNUAL_ARRAYS}
        n = len(arrays["years"])
        if any(len(v) != n for v in arrays.values()):
            raise ValueError("Native annual arrays do not share its actual analysis-year grid")
        npv = {k: finite(v, "native NPV output " + k) for k, v in attempted.npv_dict.items()}
        contributions = copy.deepcopy(attempted.contributions)
        for value in contributions["Data"].values():
            finite(value, "native levelized cost contribution")
        finite(denominator, "native discounted denominator", positive=True)
        token = object()
        _PENDING_ECONOMICS_RESULT_TOKENS.add(token)
        try:
            return HydrogenEconomicsResult(
                cost,
                "native Output per Year at Gate input; native annual_sales/startup revenues and discounted h2_sales",
                "USD",
                basis.base_year,
                projection,
                basis,
                inputs,
                window_cost,
                native,
                attempted,
                copy.deepcopy(original),
                MappingProxyType(npv),
                contributions,
                MappingProxyType(arrays),
                finite(raw_cash_flow, "opaque native cash_flow return"),
                output.getvalue(),
                fingerprint,
                _issuer_token=token,
            )
        except Exception:
            _PENDING_ECONOMICS_RESULT_TOKENS.discard(token)
            raise
    except Exception as error:
        raise HydrogenEconomicsError(
            str(error),
            projection=projection,
            annual_basis=basis,
            inputs=inputs,
            native=attempted,
            native_input=original,
            native_stdout=output.getvalue(),
            native_provider=native,
            window_cost=window_cost,
        ) from error


def vars_from_tariff(tariff):
    return {name: getattr(tariff, name) for name in tariff.__dataclass_fields__}
