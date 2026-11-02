"""Narrow actual MEC ledger projection into the existing native economics owner.

Implemented_unverified. No DCF, annualization, tariff or microbial/electrode
algorithm is reproduced. The public common source-binding/projection contract retains the actual MEC
producer verification hook and reuses the existing native finance owner.
"""

from dataclasses import dataclass
from types import MappingProxyType

from ..core import finite
from ..thermochemical import ThermochemicalInventory
from .hydrogen_economics import evaluate_hydrogen_economics
from .microbial_cell import MicrobialCellTrace
from .physical_economics import (
    PhysicalCostProjection,
    QuantityBoundary,
    ReportingWindow,
    SourceSnapshot,
    callable_identity,
    finite_sum,
    quantity_definition,
    require_validated_projection,
)

STATUS = "implemented_unverified"
SUPPORTED_TARIFF_QUANTITIES = frozenset(
    (
        "stack_electricity_j",
        "stack_heat_input_j",
        "stack_heat_rejection_j",
        "electrical_work_into_j",
        "required_heat_input_j",
        "required_heat_rejection_j",
    )
)
QUANTITY_MEANINGS = MappingProxyType(
    {
        "electrical_work_into_j": "actual MEC applied external electrical work; not measured grid purchase",
        "required_heat_input_j": "sum of positive required isothermal MEC duties; no utility availability claim",
        "required_heat_rejection_j": "magnitude of negative required isothermal MEC duties; not a heat-sale credit",
        "stack_electricity_j": "actual MEC applied external electrical work; not measured grid purchase",
        "stack_heat_input_j": "sum of positive required isothermal MEC duties; no utility availability claim",
        "stack_heat_rejection_j": "magnitude of negative required isothermal MEC duties; not a heat-sale credit",
    }
)
UNRESOLVED_COSTS = (
    "harvest_not_resolved",
    "sale_not_observed",
    "substrate_nutrient_and_biomass_handling_costs_unresolved",
    "anode_potential_and_activity_boundary_support_unresolved",
    "product_conditioning_and_pressure_work_unresolved",
    "thermal_utility_availability_unresolved",
    "full_plant_auxiliary_and_inventory_cost_scope_unresolved",
)


def _fields(value):
    return {n: getattr(value, n) for n in value.__dataclass_fields__}


def _inventory_snapshot(value):
    if not isinstance(value, ThermochemicalInventory):
        raise TypeError("MEC report requires actual finite phase-resolved inventories")
    # Revalidate actual fields without evaluating any new thermodynamic law.
    checked = ThermochemicalInventory(
        value.amounts_mol, value.temperature_k, value.pressure_pa, value.energy_basis_id
    )
    return _fields(checked)


def _species_snapshot(items):
    return tuple(
        (s.identifier, dict(s.elements), s.molar_mass_kg_mol, s.phase, s.charge) for s in items
    )


def _method_function(method):
    return getattr(method, "__func__", method)


def _conversion_snapshot(conversion):
    return (
        conversion.reaction.identifier,
        _species_snapshot(conversion.reaction.species),
        conversion.reaction.coefficients,
        conversion.extent_mol,
        conversion.initial_mol,
        conversion.final_mol,
        conversion.maximum_roundoff_correction_mol,
    )


def _point_snapshot(point):
    if point is None:
        return None
    return (
        point.potential_v,
        point.current_density_a_m2,
        point.hydrogen_rate_mol_m2_s,
        point.electron_consumption_mol_m2_s,
        dict(point.phase_current_a_m2),
        dict(point.native_production_rates_kmol_m2_s),
        dict(point.native_phase_states),
    )


def _source_values(trace, window, hydrogen_id):
    if type(trace) is not MicrobialCellTrace or not trace.steps:
        raise TypeError("Supply an actual nonempty MicrobialCellTrace, not a PV-shaped surrogate")
    if (
        not callable(getattr(trace, "require_current", None))
        or trace.require_current() is not trace
    ):
        raise TypeError(
            "Use an original producer-verified MEC trace with its public require_current hook"
        )
    if not isinstance(window, ReportingWindow):
        raise TypeError("Supply the existing explicit ReportingWindow")
    ReportingWindow(**_fields(window))
    if window.selected_product_basis not in {"generated_h2_kg", "h2_stock_increase_kg"}:
        raise ValueError(
            "Select explicitly generated or batch-stock-increase H2; no receiver/harvest/sale is inferred"
        )
    if (
        window.start_s != trace.steps[0].stage.start_s
        or window.end_s != trace.steps[-1].stage.end_s
        or window.clock_id != trace.evidence.clock_id
    ):
        raise ValueError("MEC report must cover the exact complete original source window/clock")
    if trace.kernel.enthalpy is not trace.caloric_provider:
        raise ValueError("Actual MEC kernel/caloric provider ownership changed")
    native = trace.native_cathode
    native.require_current()
    if (
        trace.evidence.caloric_basis_id != trace.caloric_provider.basis_id
        or native.evidence.caloric_reference_id != trace.caloric_provider.basis_id
        or trace.evidence.electrode_reference_id != native.evidence.electrode_reference_id
    ):
        raise ValueError("MEC caloric/electrode potential reference bindings differ")
    species = tuple(trace.caloric_provider.species)
    hydrogen = tuple(s for s in species if s.identifier == hydrogen_id)
    if (
        len(hydrogen) != 1
        or dict(hydrogen[0].elements) != {"H": 2}
        or hydrogen[0].charge
        or hydrogen[0].phase not in {"gas", "ideal-gas", "vapor"}
    ):
        raise ValueError("Identify the actual neutral gas H2 species")
    molar_mass = finite(hydrogen[0].molar_mass_kg_mol, "actual H2 kg/mol", positive=True)
    if molar_mass != native.phases[0].molecular_weights[0] / 1000.0:
        raise ValueError("Finite/native cathode H2 atomic-weight bases differ")
    previous, previous_time, rows, bindings = (
        trace.initial,
        window.start_s,
        [],
        [
            trace,
            trace.initial,
            trace.final,
            trace.kernel,
            trace.caloric_provider,
            trace.kinetics,
            trace.kinetics.callback,
            trace.kinetics.native_model,
            trace.geometry,
            trace.owner,
            trace.admission,
            *callable_identity(trace.require_current),
            *callable_identity(trace.owner.verify_result),
            native,
            native.interface,
            native.source_interface,
            _method_function(native.require_current),
            *native.phases,
            *tuple(getattr(trace.caloric_provider, "functions", ())),
            *tuple(getattr(trace.caloric_provider, "owned_phases", ())),
        ],
    )
    for step in trace.steps:
        stage, kt = step.stage, step.kernel_trace
        if (
            step.before is not previous
            or stage.start_s != previous_time
            or stage.end_s <= stage.start_s
            or stage.clock_id != window.clock_id
            or kt.initial is not step.before
            or kt.final is not step.after
            or kt.enthalpy_provider is not trace.caloric_provider
        ):
            raise ValueError(
                "MEC steps must retain original contiguous state and finite-kernel pointers"
            )
        if (
            step.rate_state.inventory is not step.before
            or step.rate_state.time_s != stage.start_s
            or step.rate_state.clock_id != window.clock_id
        ):
            raise ValueError("MEC rate context lost its original finite state/clock")
        before, after = _inventory_snapshot(step.before), _inventory_snapshot(step.after)
        if (
            before["energy_basis_id"] != trace.caloric_provider.basis_id
            or after["energy_basis_id"] != trace.caloric_provider.basis_id
        ):
            raise ValueError("MEC source inventory uses another phase caloric reference")
        amounts = {
            name: finite(getattr(step, name), "reported MEC " + name)
            for name in (
                "current_a",
                "applied_voltage_v",
                "transferred_electrons_mol",
                "hydrogen_generated_mol",
                "biomass_generated_mol",
                "electric_work_into_j",
                "isothermal_heat_required_into_j",
                "current_residual_a",
                "electron_residual_mol",
                "energy_residual_j",
            )
        }
        if (
            min(
                amounts[n]
                for n in (
                    "current_a",
                    "applied_voltage_v",
                    "transferred_electrons_mol",
                    "hydrogen_generated_mol",
                    "biomass_generated_mol",
                    "electric_work_into_j",
                )
            )
            < 0
        ):
            raise ValueError(
                "The source's forward MEC production/electricity ledger cannot be negative"
            )
        stock_change = (
            after["amounts_mol"].get(hydrogen_id, 0.0) - before["amounts_mol"].get(hydrogen_id, 0.0)
        ) * molar_mass
        if (
            abs(stock_change - amounts["hydrogen_generated_mol"] * molar_mass)
            > window.mass_tolerance_kg
        ):
            raise ValueError(
                "MEC finite stock change differs from generated H2; no unrecorded harvest is admitted"
            )
        point = step.cathode
        if stage.connected:
            if (
                point is None
                or point.native_interface is not native.interface
                or step.native_root_result is None
                or not step.native_root_result.converged
            ):
                raise ValueError("Connected MEC ledger lost its actual native cathode/root result")
        elif point is not None or step.native_root_result is not None:
            raise ValueError(
                "Disconnected MEC stage must not masquerade as an evaluated native root"
            )
        point_data = _point_snapshot(point)
        # Preserve voltage/reference/phase/source metadata without re-evaluating
        # current, microbial kinetics, thermochemistry, charge or material laws.
        root = (
            None
            if step.native_root_result is None
            else {
                key: getattr(step.native_root_result, key)
                for key in ("root", "converged", "iterations", "function_calls", "flag")
            }
        )
        conversions = tuple(_conversion_snapshot(c) for s in kt.steps for c in s.conversions)
        rows.append(
            (
                _fields(stage),
                before,
                after,
                amounts,
                _fields(step.rates),
                _fields(step.rate_state),
                step.noncathode_loss_voltages_v,
                point_data,
                root,
                conversions,
                tuple(_point_snapshot(p) for p in step.cathode_trials),
                kt.element_residual_mol,
                kt.mass_residual_kg,
                kt.energy_residual_j,
            )
        )
        bindings.extend(
            (
                step,
                stage,
                step.before,
                step.after,
                kt,
                step.rates,
                step.rate_state,
                point,
                step.native_root_result,
            )
        )
        bindings.extend(step.cathode_trials)
        previous, previous_time = step.after, stage.end_s
    if previous is not trace.final:
        raise ValueError(
            "Original MEC final inventory pointer differs from its last completed step"
        )
    initial = finite(trace.initial.amounts_mol.get(hydrogen_id, 0.0), "initial H2 mol") * molar_mass
    final = finite(trace.final.amounts_mol.get(hydrogen_id, 0.0), "final H2 mol") * molar_mass
    if min(initial, final) < 0:
        raise ValueError("Finite MEC H2 inventory cannot be negative")
    generated = finite_sum(
        (row[3]["hydrogen_generated_mol"] * molar_mass for row in rows),
        "finite MEC generated H2 kg",
    )
    if (
        abs(generated - finite(trace.hydrogen_generated_mol, "source total H2 mol") * molar_mass)
        > window.mass_tolerance_kg
        or abs(final - initial - generated) > window.mass_tolerance_kg
    ):
        raise ValueError("MEC step/generated/stock reporting correspondence failed")
    electricity = finite_sum(
        (row[3]["electric_work_into_j"] for row in rows), "MEC electrical work J"
    )
    heat = finite_sum(
        (row[3]["isothermal_heat_required_into_j"] for row in rows), "MEC signed required heat J"
    )
    if electricity != finite(
        trace.electric_work_into_j, "MEC reported total work"
    ) or heat != finite(trace.isothermal_heat_required_into_j, "MEC reported total required heat"):
        raise ValueError("MEC step and aggregate utility ledger correspondence changed")
    q = dict(
        generated_h2_kg=generated,
        cell_initial_h2_kg=initial,
        cell_final_h2_kg=final,
        cell_stock_increase_kg=final - initial,
        harvested_h2_kg=None,
        exported_sale_h2_kg=None,
        stack_electricity_j=electricity,
        stack_heat_input_j=finite_sum(
            (max(row[3]["isothermal_heat_required_into_j"], 0.0) for row in rows),
            "MEC required heating",
        ),
        stack_heat_rejection_j=finite_sum(
            (max(-row[3]["isothermal_heat_required_into_j"], 0.0) for row in rows),
            "MEC required cooling",
        ),
        cell_signed_isothermal_heat_required_j=heat,
        transferred_electrons_mol=finite(trace.transferred_electrons_mol, "source electron ledger"),
        biomass_generated_mol=finite_sum(
            (row[3]["biomass_generated_mol"] for row in rows), "biomass formula units"
        ),
        external_pressure_work_j=None,
    )
    residuals = {
        name: finite(getattr(trace, name), name)
        for name in (
            "electron_equivalent_residual_mol",
            "hydrogen_residual_mol",
            "mass_residual_kg",
            "enthalpy_residual_j",
        )
    }
    payload = (
        "MEC-fixed-P-batch-to-native-economics-v1",
        _fields(window),
        hydrogen_id,
        _fields(trace.evidence),
        _fields(trace.geometry),
        _fields(native.evidence),
        _species_snapshot(species),
        trace.caloric_provider.basis_id,
        trace.kinetics.source_id,
        trace.kinetics.parameter_source_id,
        trace.kinetics.origin,
        dict(trace.kinetics.parameters),
        rows,
        q,
        residuals,
        trace.status,
        dict(QUANTITY_MEANINGS),
        UNRESOLVED_COSTS,
    )
    q.update(
        initial_h2_stock_kg=initial,
        final_h2_stock_kg=final,
        h2_stock_increase_kg=final - initial,
        sold_h2_kg=None,
        electrical_work_into_j=electricity,
        required_heat_input_j=q["stack_heat_input_j"],
        required_heat_rejection_j=q["stack_heat_rejection_j"],
        signed_required_heat_j=heat,
    )
    if trace.require_current() is not trace:
        raise ValueError("MEC source audit did not retain the original producer object")
    admission = trace.admission
    if admission.original_trace is not trace:
        raise ValueError("MEC admission is not bound to this original trace")
    payload = (
        payload,
        {
            "producer_content_sha256": admission.content_sha256,
            "owner_configuration_sha256": admission.owner_configuration_sha256,
            "native_state_sha256": admission.native_state_sha256,
            "verification_scope": admission.verification_scope,
        },
    )
    return q, UNRESOLVED_COSTS, payload, tuple(bindings)


@dataclass(frozen=True, slots=True)
class MicrobialSourceAdapter:
    """Actual MEC producer hook plus reported-ledger snapshot; no physical replay."""

    identifier: str = "h2physics-microbial-cell-source-v2"

    def snapshot(self, source, window, hydrogen_id):
        quantities, gaps, content, identities = _source_values(source, window, hydrogen_id)
        uid = source.evidence.process_id
        components = {
            "electrical_work_into_j": (uid + ":applied-electric-work",),
            "stack_electricity_j": (uid + ":applied-electric-work",),
            "required_heat_input_j": (uid + ":isothermal-heating",),
            "stack_heat_input_j": (uid + ":isothermal-heating",),
            "required_heat_rejection_j": (uid + ":isothermal-rejection",),
            "stack_heat_rejection_j": (uid + ":isothermal-rejection",),
            "external_pressure_work_j": (uid + ":unresolved-pressure-work",),
        }
        boundaries = {
            name: QuantityBoundary(
                name,
                uid + ":" + quantity_definition(name).boundary_role,
                source.evidence.caloric_basis_id,
                window.evidence_id,
                components.get(name, ()),
            )
            for name in quantities
        }
        return SourceSnapshot(
            source,
            window,
            hydrogen_id,
            uid,
            "MEC original producer identity/content/native-state seal; no physical recomputation",
            quantities,
            boundaries,
            gaps,
            content,
            identities,
        )


class MicrobialCostProjection:
    """Compatible named factory returning the actual source-neutral projection."""

    def __new__(cls, *args, **kwargs):
        raise TypeError("Use from_microbial_cell or PhysicalCostProjection.from_source")

    @classmethod
    def from_microbial_cell(cls, trace, window, *, hydrogen_id):
        return PhysicalCostProjection.from_source(
            trace, MicrobialSourceAdapter(), window, hydrogen_id=hydrogen_id
        )

    @classmethod
    def from_pv_electrolysis(cls, *args, **kwargs):
        raise TypeError("Use the actual PV projection factory for a PV trace")


class MicrobialEconomicsError(ValueError):
    def __init__(
        self,
        message,
        *,
        projection,
        annual_basis,
        inputs,
        native,
        window_cost,
        original,
        financial_result=None,
    ):
        super().__init__(message)
        self.projection, self.annual_basis, self.financial_inputs = projection, annual_basis, inputs
        self.source_trace = getattr(projection, "source", None)
        self.native_provider, self.window_utility_cost = native, window_cost
        self.original_error = original
        self.native_object = getattr(original, "native_object", None)
        self.native_input = getattr(original, "native_input", None)
        self.native_stdout = getattr(original, "native_stdout", "")
        self.financial_result = financial_result
        if financial_result is not None and self.native_object is None:
            self.native_object = financial_result.native_object
            self.native_input = financial_result.native_input_before
            self.native_stdout = financial_result.native_stdout


def evaluate_microbial_economics(
    projection, annual_basis, financial_inputs, *, native, window_cost=None
):
    """Return the existing original HydrogenEconomicsResult, with actual MEC source."""
    result = None
    try:
        require_validated_projection(projection)
        if (
            type(projection.source_binding.adapter) is not MicrobialSourceAdapter
            or type(projection.source) is not MicrobialCellTrace
        ):
            raise TypeError("Bind an actual producer-verified MEC source adapter")
        result = evaluate_hydrogen_economics(
            projection, annual_basis, financial_inputs, native=native, window_cost=window_cost
        )
        require_validated_projection(projection)
        if result.projection is not projection or result.projection.source is not projection.source:
            raise ValueError("Native economic result lost the actual MEC source binding")
        return result
    except Exception as error:
        raise MicrobialEconomicsError(
            str(error),
            projection=projection,
            annual_basis=annual_basis,
            inputs=financial_inputs,
            native=native,
            window_cost=window_cost,
            original=error,
            financial_result=result,
        ) from error
