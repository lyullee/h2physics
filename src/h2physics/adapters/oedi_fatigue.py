"""No-fit comparison of measured OEDI crack-growth points with native HELPR rates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field as dataclass_field

import numpy as np

from ..core import immutable_array, finite
from ..data.oedi_fatigue import FatigueGrowthSeries, OediFatigueDataset
from .fracture_fatigue import (
    HelprFatigueLaw,
    HydrogenCrackEnvironment,
    NativeHelprObjects,
)


@dataclass(frozen=True, slots=True)
class OediFatiguePoint:
    """One source row with measured, native-return and accepted-rate values aligned."""

    dataset_source_id: str
    dataset_source_sha256: str
    dataset_source_url: str
    dataset_license_id: str
    dataset_license_url: str
    series_id: str
    source_columns_one_based: tuple[int, int]
    source_row_id: str
    delta_k_pa_sqrt_m: float
    observed_growth_m_per_cycle: float
    native_raw_return: object
    predicted_growth_m_per_cycle: float
    rate_ratio: float
    log10_rate_ratio: float | None

    def __post_init__(self):
        for name in (
            "dataset_source_id", "dataset_source_url", "dataset_license_id",
            "dataset_license_url", "series_id",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"A fatigue diagnostic point requires {name}")
        digest = self.dataset_source_sha256
        if (not isinstance(digest, str) or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)):
            raise ValueError("A fatigue diagnostic point requires a lowercase source SHA-256")
        columns = tuple(self.source_columns_one_based)
        if (len(columns) != 2 or any(type(value) is not int or value < 1 for value in columns)
                or columns[1] != columns[0] + 1):
            raise ValueError("A fatigue point must retain its adjacent one-based workbook columns")
        object.__setattr__(self, "source_columns_one_based", columns)
        if not isinstance(self.source_row_id, str) or not self.source_row_id.strip():
            raise ValueError("A fatigue diagnostic point requires a source row identity")
        row_prefix = f"{self.dataset_source_id}:row-"
        if not self.source_row_id.startswith(row_prefix):
            raise ValueError("The point row identity must belong to the declared source dataset")
        try:
            source_row_number = int(self.source_row_id.removeprefix(row_prefix))
        except ValueError as error:
            raise ValueError("The source row identity must contain a one-based row number") from error
        if source_row_number < 1:
            raise ValueError("The source row identity must contain a positive one-based row number")
        for name in (
            "delta_k_pa_sqrt_m", "observed_growth_m_per_cycle",
            "predicted_growth_m_per_cycle", "rate_ratio",
        ):
            value = finite(getattr(self, name), name)
            object.__setattr__(self, name, value)
        delta = self.delta_k_pa_sqrt_m
        observed = self.observed_growth_m_per_cycle
        predicted = self.predicted_growth_m_per_cycle
        ratio = self.rate_ratio
        if delta <= 0 or observed <= 0 or predicted < 0 or ratio < 0:
            raise ValueError("Fatigue point inputs and rates are outside their physical numeric domain")
        if not np.isscalar(self.native_raw_return):
            raise TypeError("The native fatigue point return must be a scalar")
        if finite(self.native_raw_return, "raw HELPR return") != predicted:
            raise ValueError("Raw native return and accepted SI rate must agree")
        if not np.isclose(ratio, predicted / observed, rtol=2e-12, atol=0.0):
            raise ValueError("Point rate ratio must equal prediction divided by observation")
        expected_log = np.log10(predicted) - np.log10(observed) if predicted > 0 else None
        if expected_log is None:
            if self.log10_rate_ratio is not None:
                raise ValueError("A zero prediction has no finite log-rate ratio")
        else:
            if self.log10_rate_ratio is None:
                raise ValueError("A positive prediction requires a finite log-rate ratio")
            log_ratio = finite(self.log10_rate_ratio, "log-rate ratio")
            if not np.isclose(log_ratio, expected_log, rtol=2e-12, atol=2e-12):
                raise ValueError("Point log-rate ratio must match its prediction and observation")
            object.__setattr__(self, "log10_rate_ratio", log_ratio)


@dataclass(frozen=True, slots=True)
class OediFatigueComparison:
    """Raw and log-space diagnostics; this result is not a material qualification."""

    dataset: OediFatigueDataset
    series: FatigueGrowthSeries
    law: HelprFatigueLaw
    environment: HydrogenCrackEnvironment
    temperature_interpretation_id: str
    gas_composition_interpretation_id: str
    native_owner: NativeHelprObjects
    source_row_ids: tuple[str, ...]
    native_raw_returns: tuple[object, ...]
    delta_k_pa_sqrt_m: np.ndarray
    observed_growth_m_per_cycle: np.ndarray
    predicted_growth_m_per_cycle: np.ndarray
    rate_ratio: np.ndarray
    log10_rate_ratio: np.ndarray
    positive_prediction_log_rmse: float | None
    _integrity_identity: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)
    _integrity_sha256: str = dataclass_field(default="", init=False, repr=False, compare=False)

    @property
    def points(self) -> tuple[OediFatiguePoint, ...]:
        """Return immutable row records joining source observations to native results."""
        self.require_current()
        return tuple(
            OediFatiguePoint(
                dataset_source_id=self.dataset.series[0].observations.source_id,
                dataset_source_sha256=self.dataset.source_sha256,
                dataset_source_url=self.dataset.source_url,
                dataset_license_id=self.dataset.license_id,
                dataset_license_url=self.dataset.license_url,
                series_id=self.series.series_id,
                source_columns_one_based=self.series.source_columns,
                source_row_id=row_id,
                delta_k_pa_sqrt_m=float(delta_k),
                observed_growth_m_per_cycle=float(observed),
                native_raw_return=raw,
                predicted_growth_m_per_cycle=float(predicted),
                rate_ratio=float(ratio),
                log10_rate_ratio=(None if not np.isfinite(log_ratio) else float(log_ratio)),
            )
            for row_id, delta_k, observed, raw, predicted, ratio, log_ratio in zip(
                self.source_row_ids,
                self.delta_k_pa_sqrt_m,
                self.observed_growth_m_per_cycle,
                self.native_raw_returns,
                self.predicted_growth_m_per_cycle,
                self.rate_ratio,
                self.log10_rate_ratio,
                strict=True,
            )
        )

    def __post_init__(self):
        if (type(self.dataset) is not OediFatigueDataset
                or type(self.series) is not FatigueGrowthSeries
                or not any(item is self.series for item in self.dataset.series)):
            raise TypeError("Comparison must retain its exact series object from the pinned dataset")
        if (type(self.law) is not HelprFatigueLaw
                or type(self.environment) is not HydrogenCrackEnvironment
                or type(self.native_owner) is not NativeHelprObjects):
            raise TypeError("Comparison must retain the actual selected law, environment and native owner")
        if (not isinstance(self.gas_composition_interpretation_id, str)
                or not self.gas_composition_interpretation_id.strip()):
            raise ValueError("Record the measured evidence or explicit assumption for test-gas composition")
        if (self.series.environment == "H2"
                and self.environment.hydrogen_mole_fraction <= 0):
            raise ValueError("An H2 observation cannot be bound to a gas state without hydrogen")
        if (self.series.environment == "air"
                and (self.law.selection.model_name != "paris_law"
                     or self.environment.hydrogen_mole_fraction != 0)):
            raise ValueError("Air observations require an explicitly selected non-H2 Paris-law state")
        self.law.require_sources()
        self.law.require_definition(self.native_owner)
        selection = self.law.selection
        expected_arguments = {"model_name": selection.model_name}
        if selection.model_name == "paris_law":
            expected_arguments.update(
                c=selection.paris_coefficient_si * 1.0e6**selection.paris_exponent,
                m=selection.paris_exponent,
            )
        if (dict(self.native_owner.arguments) != expected_arguments
                or self.native_owner.growth.model_arguments != expected_arguments):
            raise ValueError("Native owner parameters differ from the selected HELPR law")
        native_environment = self.native_owner.environment
        if self.native_owner.growth.environment_specification is not native_environment:
            raise ValueError("Native comparison owner no longer binds its admitted environment")
        if native_environment is None:
            if (selection.model_name != "paris_law"
                    or self.environment.hydrogen_mole_fraction != 0):
                raise ValueError("A comparison without a native gas environment cannot represent H2")
        else:
            if (selection.model_name == "paris_law"
                    or self.environment.fugacity_basis_id != "HELPR-native-Abel-Noble"):
                raise ValueError("Native gas state and selected HELPR law use different environment bases")
            admitted = (
                (native_environment.max_pressure * 1.0e6, self.environment.maximum_pressure_pa, 1.0e-12),
                (native_environment.min_pressure * 1.0e6, self.environment.minimum_pressure_pa, 1.0e-12),
                (native_environment.temperature, self.environment.temperature_k, 1.0e-12),
                (native_environment.volume_fraction_h2, self.environment.hydrogen_mole_fraction, 1.0e-12),
                (native_environment.reference_pressure * 1.0e6, selection.reference_pressure_pa, 1.0e-12),
                (native_environment.fugacity * 1.0e6, self.environment.hydrogen_fugacity_pa,
                 selection.fugacity_compatibility_relative_budget),
            )
            if any(not np.isclose(a, b, rtol=tolerance, atol=0.0)
                   for a, b, tolerance in admitted):
                raise ValueError("Retained comparison environment differs from the native admitted state")

        rows = tuple(self.source_row_ids)
        if any(not isinstance(row, str) or not row.strip() for row in rows):
            raise ValueError("Comparison row identities must be nonempty strings")
        if len(rows) != len(set(rows)):
            raise ValueError("Comparison row identities must be unique")
        source_table = self.series.observations
        source_delta, delta_valid = source_table.column("stress_intensity_factor_range")
        source_growth, growth_valid = source_table.column("crack_growth_rate")
        admitted_rows = delta_valid & growth_valid
        expected_ids = tuple(
            row_id for row_id, keep in zip(source_table.row_ids, admitted_rows, strict=True) if keep
        )
        if rows != expected_ids:
            raise ValueError("Comparison row identities differ from the admitted source series rows")
        raw_returns = tuple(self.native_raw_returns)
        if len(raw_returns) != len(rows):
            raise ValueError("Every measured row must retain its original native return")
        if (not np.array_equal(np.asarray(self.delta_k_pa_sqrt_m), source_delta[admitted_rows])
                or not np.array_equal(np.asarray(self.observed_growth_m_per_cycle),
                                      source_growth[admitted_rows])):
            raise ValueError("Comparison observations differ from their retained workbook rows")

        count = len(rows)
        if count == 0:
            raise ValueError("A comparison must retain unique source-row identities")
        object.__setattr__(self, "source_row_ids", rows)
        object.__setattr__(self, "native_raw_returns", raw_returns)
        if (
            not isinstance(self.temperature_interpretation_id, str)
            or not self.temperature_interpretation_id.strip()
        ):
            raise ValueError("Record the evidence or assumption mapping RT to model temperature")
        for name in (
            "delta_k_pa_sqrt_m",
            "observed_growth_m_per_cycle",
            "predicted_growth_m_per_cycle",
            "rate_ratio",
            "log10_rate_ratio",
        ):
            values = np.array(getattr(self, name), dtype=float, copy=True)
            if values.shape != (count,):
                raise ValueError(f"Comparison {name} must align with its source rows")
            if name != "log10_rate_ratio" and not np.all(np.isfinite(values)):
                raise ValueError(f"Comparison {name} must be finite")
            values = immutable_array(values, name="values")
            object.__setattr__(self, name, values)
        if np.any(self.delta_k_pa_sqrt_m <= 0) or np.any(
            self.observed_growth_m_per_cycle <= 0
        ):
            raise ValueError("Observed fatigue points must be positive")
        if np.any(self.predicted_growth_m_per_cycle < 0) or np.any(self.rate_ratio < 0):
            raise ValueError("Native fatigue rates cannot be negative")
        if any(
            not np.isscalar(raw)
            or finite(raw, "original native fatigue return") != predicted
            for raw, predicted in zip(
                raw_returns, self.predicted_growth_m_per_cycle, strict=True
            )
        ):
            raise ValueError("Original native returns must match the accepted m/cycle rates")
        expected_ratio = self.predicted_growth_m_per_cycle / self.observed_growth_m_per_cycle
        if not np.allclose(self.rate_ratio, expected_ratio, rtol=2e-12, atol=0.0):
            raise ValueError("Rate ratios must equal native predictions divided by observations")
        positive = self.predicted_growth_m_per_cycle > 0
        expected_log_ratio = np.full(count, np.nan, dtype=float)
        expected_log_ratio[positive] = (
            np.log10(self.predicted_growth_m_per_cycle[positive])
            - np.log10(self.observed_growth_m_per_cycle[positive])
        )
        if np.any(~np.isfinite(self.log10_rate_ratio[positive])) or not np.allclose(
            self.log10_rate_ratio,
            expected_log_ratio,
            rtol=2e-12,
            atol=2e-12,
            equal_nan=True,
        ):
            raise ValueError("Log-rate ratios must match the positive prediction/observation pairs")
        expected_rmse = (
            float(np.sqrt(np.mean(np.square(expected_log_ratio[positive]))))
            if np.any(positive)
            else None
        )
        if (expected_rmse is None) != (self.positive_prediction_log_rmse is None):
            raise ValueError("Log-rate RMSE exists exactly when a positive prediction exists")
        if self.positive_prediction_log_rmse is not None:
            value = finite(self.positive_prediction_log_rmse, "positive-prediction log RMSE")
            if value < 0:
                raise ValueError("Log RMSE cannot be negative")
            if not np.isclose(value, expected_rmse, rtol=2e-12, atol=2e-12):
                raise ValueError("Log-rate RMSE must summarize the retained per-row log ratios")
            object.__setattr__(self, "positive_prediction_log_rmse", value)
        object.__setattr__(self, "_integrity_identity", self._object_bindings())
        object.__setattr__(self, "_integrity_sha256", self._content_fingerprint())

    def _object_bindings(self):
        return (
            self.dataset, self.series, self.law, self.environment, self.native_owner,
            self.source_row_ids, self.native_raw_returns, self.delta_k_pa_sqrt_m,
            self.observed_growth_m_per_cycle, self.predicted_growth_m_per_cycle,
            self.rate_ratio, self.log10_rate_ratio,
        )

    def _content_fingerprint(self):
        table = self.series.observations
        arrays = tuple(
            (array.dtype.str, array.shape, hashlib.sha256(
                np.ascontiguousarray(array).tobytes()
            ).hexdigest())
            for array in (
                self.delta_k_pa_sqrt_m, self.observed_growth_m_per_cycle,
                self.predicted_growth_m_per_cycle, self.rate_ratio, self.log10_rate_ratio,
            )
        )
        payload = (
            self.dataset.source_file, self.dataset.source_sha256, self.dataset.source_md5,
            self.dataset.source_url, self.dataset.license_id, self.dataset.license_url,
            self.dataset.publisher, self.dataset.material, self.dataset.material_form,
            self.dataset.temper, self.dataset.condition_metadata_discrepancy,
            self.dataset.condition_resolution, self.dataset.condition_authority_url,
            self.dataset.related_condition_source_url, self.dataset.condition_identity_admitted,
            table.content_sha256, self.series.series_id, self.series.environment,
            self.series.pressure_mpa, self.series.temperature_label, self.series.r_ratio,
            self.series.orientation, self.series.test_method, self.series.frequency_hz,
            self.series.source_columns, self.series.reference,
            repr(self.law.selection), tuple(sorted(self.law.source_sha256.items())),
            self.native_owner.definition_sha256, repr(dict(self.native_owner.arguments)),
            repr(self.native_owner.growth.model_arguments),
            repr(self.native_owner.environment), repr(self.environment),
            self.temperature_interpretation_id, self.gas_composition_interpretation_id,
            self.source_row_ids, tuple(float(value) for value in self.native_raw_returns),
            arrays, self.positive_prediction_log_rmse,
        )
        return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()

    def require_current(self) -> "OediFatigueComparison":
        current = self._object_bindings()
        if (not self._integrity_identity
                or any(value is not original for value, original in zip(
                    current, self._integrity_identity, strict=True,
                ))):
            raise ValueError("OEDI fatigue comparison lost its original source/result objects")
        self.law.require_sources()
        self.law.require_definition(self.native_owner)
        if self._content_fingerprint() != self._integrity_sha256:
            raise ValueError("OEDI source rows, model conditions or comparison values changed")
        return self


class OediFatigueComparisonError(RuntimeError):
    """A failed native point evaluation with admitted objects and completed rows."""

    def __init__(
        self, message, *, dataset, series, environment,
        temperature_interpretation_id, gas_composition_interpretation_id,
        law, native_owner, failure_row_id, failure_stage, cause, completed,
    ):
        super().__init__(message)
        if (type(dataset) is not OediFatigueDataset
                or type(series) is not FatigueGrowthSeries
                or not any(item is series for item in dataset.series)):
            raise TypeError("Failure diagnostics must retain the exact pinned dataset series")
        if (type(law) is not HelprFatigueLaw
                or type(environment) is not HydrogenCrackEnvironment
                or type(native_owner) is not NativeHelprObjects
                or not isinstance(cause, BaseException)):
            raise TypeError("Failure diagnostics require the admitted native law, state, owner and cause")
        if failure_stage not in {
            "source_or_native_definition_precheck",
            "native_point_evaluation",
            "native_return_admission",
            "completed_prefix_append",
        }:
            raise ValueError("Failure diagnostic stage is not a declared native-call boundary")
        if (not isinstance(failure_row_id, str) or not failure_row_id.strip()
                or not isinstance(temperature_interpretation_id, str)
                or not temperature_interpretation_id.strip()
                or not isinstance(gas_composition_interpretation_id, str)
                or not gas_composition_interpretation_id.strip()):
            raise ValueError("Failure diagnostics require source row and explicit condition interpretations")
        table = series.observations
        source_delta, delta_valid = table.column("stress_intensity_factor_range")
        source_growth, growth_valid = table.column("crack_growth_rate")
        admitted_row_ids = tuple(
            row_id for row_id, keep in zip(table.row_ids, delta_valid & growth_valid, strict=True)
            if keep
        )
        admitted_indices = {
            row_id: index for index, row_id in enumerate(table.row_ids)
            if delta_valid[index] and growth_valid[index]
        }
        retained = tuple(tuple(item) for item in completed)
        completed_row_ids = tuple(item[0] for item in retained if len(item) == 3)
        if (any(len(item) != 3 for item in retained)
                or completed_row_ids != admitted_row_ids[:len(retained)]
                or len(retained) >= len(admitted_row_ids)
                or failure_row_id != admitted_row_ids[len(retained)]):
            raise ValueError("Failure row and completed predictions must form the ordered source-row prefix")
        for row_id, rate, _ in retained:
            if not isinstance(row_id, str):
                raise ValueError("Completed native rows require source row identities")
        for row_id, rate, raw_return in retained:
            accepted_rate = finite(rate, "completed native growth rate")
            if (accepted_rate < 0 or not np.isscalar(raw_return)
                    or finite(raw_return, "completed raw native return") != accepted_rate):
                raise ValueError("Completed raw native returns must equal accepted nonnegative rates")
        self.dataset = dataset
        self.series = series
        self.environment = environment
        self.temperature_interpretation_id = temperature_interpretation_id
        self.gas_composition_interpretation_id = gas_composition_interpretation_id
        self.law = law
        self.native_owner = native_owner
        self.failure_row_id = failure_row_id
        self.failure_stage = failure_stage
        self.cause = cause
        self.completed = retained
        self._admitted_source_indices = admitted_indices
        self._source_delta_k = source_delta
        self._source_growth = source_growth

    def diagnostic_record(self) -> dict[str, object]:
        """Return a compact, serialization-ready failure receipt without raw exception text."""
        owner = self.native_owner
        environment = self.environment
        model_selection = self.law.selection
        return {
            "dataset_source_id": self.dataset.series[0].observations.source_id,
            "dataset_source_sha256": self.dataset.source_sha256,
            "dataset_source_url": self.dataset.source_url,
            "dataset_license_id": self.dataset.license_id,
            "dataset_license_url": self.dataset.license_url,
            "series_id": self.series.series_id,
            "series_environment": self.series.environment,
            "series_pressure_mpa": self.series.pressure_mpa,
            "series_source_columns_one_based": self.series.source_columns,
            "series_r_ratio": self.series.r_ratio,
            "series_frequency_hz": self.series.frequency_hz,
            "temperature_interpretation_id": self.temperature_interpretation_id,
            "gas_composition_interpretation_id": self.gas_composition_interpretation_id,
            "native_model_name": model_selection.model_name,
            "native_model_evidence_id": model_selection.model_evidence_id,
            "native_model_arguments": dict(owner.arguments),
            "native_definition_sha256": owner.definition_sha256,
            "native_source_module_hashes": dict(self.law.source_sha256),
            "native_environment_evidence_id": environment.evidence_id,
            "native_environment_origin": environment.origin.value,
            "native_pressure_minimum_pa": environment.minimum_pressure_pa,
            "native_pressure_maximum_pa": environment.maximum_pressure_pa,
            "native_temperature_k": environment.temperature_k,
            "native_hydrogen_mole_fraction": environment.hydrogen_mole_fraction,
            "native_hydrogen_fugacity_pa": environment.hydrogen_fugacity_pa,
            "native_fugacity_basis_id": environment.fugacity_basis_id,
            "failure_row_id": self.failure_row_id,
            "failure_stage": self.failure_stage,
            "failure_exception_type": type(self.cause).__name__,
            "completed_row_ids": tuple(row_id for row_id, _, _ in self.completed),
            "completed_delta_k_pa_sqrt_m": tuple(
                float(self._source_delta_k[self._admitted_source_indices[row_id]])
                for row_id, _, _ in self.completed
            ),
            "completed_observed_growth_m_per_cycle": tuple(
                float(self._source_growth[self._admitted_source_indices[row_id]])
                for row_id, _, _ in self.completed
            ),
            "completed_predictions_m_per_cycle": tuple(rate for _, rate, _ in self.completed),
            "completed_native_returns": tuple(raw for _, _, raw in self.completed),
            "failure_delta_k_pa_sqrt_m": float(
                self._source_delta_k[self._admitted_source_indices[self.failure_row_id]]
            ),
            "failure_observed_growth_m_per_cycle": float(
                self._source_growth[self._admitted_source_indices[self.failure_row_id]]
            ),
        }


def compare_oedi_fatigue_series(
    dataset: OediFatigueDataset,
    series_id: str,
    law: HelprFatigueLaw,
    environment: HydrogenCrackEnvironment,
    *,
    temperature_interpretation_id: str,
    gas_composition_interpretation_id: str,
) -> OediFatigueComparison:
    """Evaluate an actual native HELPR rate at each measured delta-K, without fitting.

    The caller supplies an actual, evidence-bound gas environment. Pressure must
    match the selected workbook series. HELPR's point API does not accept test
    frequency, so the series' measured frequency is retained but not modeled by
    this comparison. Because the workbook gives only an ``RT`` label, the caller
    must identify the evidence or explicit assumption used to map that label to
    the numeric environment temperature. The workbook also does not establish
    gas purity, so the caller must identify the evidence or explicit composition
    assumption used by the native environment. Material-heat identity and
    vessel-life qualification are outside this operator.
    """
    if type(dataset) is not OediFatigueDataset:
        raise TypeError("Pass the checksum-pinned OEDI dataset object")
    if not dataset.condition_identity_admitted:
        raise ValueError("The workbook condition has not been admitted for comparison")
    if type(law) is not HelprFatigueLaw:
        raise TypeError("Pass the actual pinned HELPR native-law adapter")
    if type(environment) is not HydrogenCrackEnvironment:
        raise TypeError("Pass an explicit measured-condition-compatible H2 environment")
    if (
        not isinstance(temperature_interpretation_id, str)
        or not temperature_interpretation_id.strip()
    ):
        raise ValueError("Identify evidence or an explicit assumption for the RT temperature mapping")
    if (not isinstance(gas_composition_interpretation_id, str)
            or not gas_composition_interpretation_id.strip()):
        raise ValueError("Identify evidence or an explicit assumption for the test-gas composition")
    series = next((item for item in dataset.series if item.series_id == series_id), None)
    if series is None:
        raise KeyError(series_id)
    if series.environment == "H2":
        if environment.hydrogen_mole_fraction <= 0:
            raise ValueError("An H2 workbook series needs a hydrogen-bearing native environment")
    elif law.selection.model_name != "paris_law" or environment.hydrogen_mole_fraction != 0:
        raise ValueError("Air reference points require an explicit non-H2 supplied Paris law")
    if not np.isclose(
        environment.minimum_pressure_pa,
        series.pressure_mpa * 1.0e6,
        rtol=1.0e-10,
        atol=0.0,
    ) or not np.isclose(
        environment.maximum_pressure_pa,
        series.pressure_mpa * 1.0e6,
        rtol=1.0e-10,
        atol=0.0,
    ):
        raise ValueError("Native environment pressure must equal the workbook test pressure")

    table = series.observations
    delta_k, delta_k_valid = table.column("stress_intensity_factor_range")
    observed, growth_valid = table.column("crack_growth_rate")
    admitted = delta_k_valid & growth_valid
    if not np.any(admitted):
        raise ValueError("The selected workbook series has no complete fatigue-rate rows")
    delta_k, observed = delta_k[admitted], observed[admitted]
    row_ids = tuple(row for row, keep in zip(table.row_ids, admitted, strict=True) if keep)
    if np.any(delta_k <= 0) or np.any(observed <= 0):
        raise ValueError("Stress-intensity and measured growth values must be positive")

    law.require_sources()
    owner = law.make_native(environment)
    predicted, native_raw_returns, completed = [], [], []
    for row_id, delta_pa in zip(row_ids, delta_k, strict=True):
        failure_stage = "source_or_native_definition_precheck"
        try:
            law.require_sources()
            law.require_definition(owner)
            failure_stage = "native_point_evaluation"
            native_result = owner.growth.calc_change_in_crack_size(
                delta_n=1.0,
                delta_k=float(delta_pa / 1.0e6),
                r_ratio=series.r_ratio,
                cycle_index=0,
            )
            failure_stage = "native_return_admission"
            rate = finite(native_result, "native HELPR crack growth rate")
            if rate < 0:
                raise ValueError("Native HELPR returned a negative crack-growth rate")
            law.require_definition(owner)
            failure_stage = "completed_prefix_append"
            predicted.append(rate)
            native_raw_returns.append(native_result)
            completed.append((row_id, rate, native_result))
        except Exception as error:
            raise OediFatigueComparisonError(
                f"HELPR fatigue comparison failed at source row {row_id}",
                dataset=dataset,
                series=series,
                environment=environment,
                temperature_interpretation_id=temperature_interpretation_id,
                gas_composition_interpretation_id=gas_composition_interpretation_id,
                law=law,
                native_owner=owner,
                failure_row_id=row_id,
                failure_stage=failure_stage,
                cause=error,
                completed=completed,
            ) from error
    law.require_sources()
    predicted_array = np.asarray(predicted, dtype=float)
    ratio = predicted_array / observed
    positive = predicted_array > 0
    log_ratio = np.full(predicted_array.shape, np.nan, dtype=float)
    log_ratio[positive] = np.log10(predicted_array[positive]) - np.log10(observed[positive])
    log_rmse = (
        float(np.sqrt(np.mean(np.square(log_ratio[positive])))) if np.any(positive) else None
    )
    return OediFatigueComparison(
        dataset,
        series,
        law,
        environment,
        temperature_interpretation_id,
        gas_composition_interpretation_id,
        owner,
        row_ids,
        tuple(native_raw_returns),
        delta_k,
        observed,
        predicted_array,
        ratio,
        log_ratio,
        log_rmse,
    )


__all__ = [
    "OediFatiguePoint",
    "OediFatigueComparison",
    "OediFatigueComparisonError",
    "compare_oedi_fatigue_series",
]
