"""Explicit PEM EIS-to-stack ohmic parameter bridge.

The measured spectrum is owned by :mod:`h2physics.data.pem`, circuit physics by
the injected native impedance provider, and stack polarization by
:class:`h2physics.electrochemistry.HydrogenStack`. This module only carries a
caller-approved effective resistance parameter between those layers.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ..core import finite
from ..data.pem import PemExperiment, PemSpectrum
from ..electrochemistry import OhmicLoss
from ..impedance import COMPONENT, FREQUENCY, IMPEDANCE
from ..observations import concatenate_observations
from ..research.fitting import FitResult


@dataclass(frozen=True, slots=True)
class PemOhmicLossBinding:
    """Caller-approved effective fitted R0 mapped to an area-specific stack loss.

    This is an integration parameter, not an assertion that fitted R0 isolates
    membrane/electrolyte resistance or remains valid away from the measured
    small-signal operating point.
    """

    area_resistance_ohm_m2: float
    cell_resistance_ohm: float
    active_area_m2: float
    parameter_name: str
    model_id: str
    fitting_data_sha256: str
    source_id: str
    source_member_sha256: str
    spectrum_experiment_id: str
    fit_spectrum_experiment_ids: tuple[str, ...]
    fit_spectrum_sha256s: tuple[str, ...]
    fit_dc_context_row_ids: tuple[tuple[str, ...], ...]
    dc_context_row_ids: tuple[str, ...]
    fit_numerical_rank: int
    fit_parameter_count: int
    fit_condition_number: float
    fit_rank_relative_threshold: float
    maximum_condition_number: float | None
    effective_operating_current_a: float
    effective_block_temperature_k: float
    effective_pressure_pa: float | None
    interpretation_id: str
    _integrity_sha256: str
    _temperature_adjustment: Callable[[float], float] | None = None

    def __post_init__(self):
        for name in (
            "area_resistance_ohm_m2", "cell_resistance_ohm", "active_area_m2",
            "effective_operating_current_a", "effective_block_temperature_k",
            "fit_condition_number", "fit_rank_relative_threshold",
        ):
            finite(getattr(self, name), name, positive=True)
        if (isinstance(self.fit_numerical_rank, bool)
                or not isinstance(self.fit_numerical_rank, int)
                or isinstance(self.fit_parameter_count, bool)
                or not isinstance(self.fit_parameter_count, int)
                or self.fit_parameter_count < 1
                or self.fit_numerical_rank != self.fit_parameter_count):
            raise ValueError("Transferred PEM coefficient needs a full numerical fit rank")
        if not 0 < self.fit_rank_relative_threshold < 1:
            raise ValueError("Retain a numerical rank relative threshold between zero and one")
        if self.maximum_condition_number is not None:
            finite(self.maximum_condition_number, "maximum accepted fit condition number", positive=True)
            if self.fit_condition_number > self.maximum_condition_number:
                raise ValueError("PEM fit condition number exceeds the admitted maximum")
        if self.effective_pressure_pa is not None:
            finite(self.effective_pressure_pa, "effective absolute pressure", positive=True)
        for name in (
            "parameter_name", "model_id", "fitting_data_sha256", "source_id",
            "source_member_sha256", "spectrum_experiment_id", "interpretation_id",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"PEM resistance binding requires {name}")
        rows = tuple(self.dc_context_row_ids)
        if not rows or any(not isinstance(row, str) or not row.strip() for row in rows):
            raise ValueError("Retain the measured rows that establish the EIS operating point")
        object.__setattr__(self, "dc_context_row_ids", rows)
        sweep_ids = tuple(self.fit_spectrum_experiment_ids)
        sweep_hashes = tuple(self.fit_spectrum_sha256s)
        fit_dc_rows = tuple(tuple(group) for group in self.fit_dc_context_row_ids)
        if (not sweep_ids or self.spectrum_experiment_id not in sweep_ids
                or any(not isinstance(item, str) or not item.strip() for item in sweep_ids)
                or len(sweep_ids) != len(set(sweep_ids))
                or len(sweep_hashes) != len(sweep_ids)
                or any(not isinstance(item, str) or len(item) != 64 for item in sweep_hashes)
                or len(fit_dc_rows) != len(sweep_ids)
                or any(not group or any(not isinstance(row, str) or not row.strip()
                                        for row in group) for group in fit_dc_rows)):
            raise ValueError("Retain unique fit-sweep IDs, fingerprints and operating-point rows")
        object.__setattr__(self, "fit_spectrum_experiment_ids", sweep_ids)
        object.__setattr__(self, "fit_spectrum_sha256s", sweep_hashes)
        object.__setattr__(self, "fit_dc_context_row_ids", fit_dc_rows)
        if self._temperature_adjustment is not None and not callable(self._temperature_adjustment):
            raise TypeError("Optional resistance temperature adjustment must be callable")
        expected_digest = self._digest(self._payload(
            self.area_resistance_ohm_m2, self.cell_resistance_ohm, self.active_area_m2,
            self.parameter_name, self.model_id, self.fitting_data_sha256, self.source_id,
            self.source_member_sha256, self.spectrum_experiment_id,
            self.fit_spectrum_experiment_ids, self.fit_spectrum_sha256s,
            self.fit_dc_context_row_ids,
            self.dc_context_row_ids, self.fit_numerical_rank, self.fit_parameter_count,
            self.fit_condition_number, self.fit_rank_relative_threshold,
            self.maximum_condition_number, self.effective_operating_current_a,
            self.effective_block_temperature_k, self.effective_pressure_pa,
            self.interpretation_id, id(self._temperature_adjustment),
        ))
        if self._integrity_sha256 != expected_digest:
            raise ValueError("PEM resistance binding fingerprint does not match its fields")

    @classmethod
    def from_fit(
        cls,
        experiment: PemExperiment,
        spectrum: PemSpectrum | Sequence[PemSpectrum],
        fit: FitResult,
        *,
        parameter_name: str,
        interpretation_id: str,
        expected_model_id: str | None = None,
        temperature_adjustment: Callable[[float], float] | None = None,
        maximum_condition_number: float | None = None,
        operating_spectrum_id: str | None = None,
    ) -> PemOhmicLossBinding:
        """Bind an exact single- or caller-ordered multi-sweep fit to retained PEM data.

        For multiple spectra, select the stack operating context by its full spectrum
        experiment ID. The input sequence order defines the concatenated fitting table.
        """
        if type(experiment) is not PemExperiment:
            raise TypeError("Supply the retained PEM experiment object")
        if type(fit) is not FitResult:
            raise TypeError("Supply the shared observation FitResult")
        sweeps = (spectrum,) if type(spectrum) is PemSpectrum else tuple(spectrum)
        if not sweeps or any(type(item) is not PemSpectrum for item in sweeps):
            raise TypeError("Supply one or more retained PemSpectrum objects")
        sweep_ids = tuple(item.spectrum.experiment_id for item in sweeps)
        if len(set(sweep_ids)) != len(sweep_ids):
            raise ValueError("Selected PEM spectra need unique experiment identities")
        if len(sweeps) == 1:
            operating_spectrum_id = operating_spectrum_id or sweep_ids[0]
        elif operating_spectrum_id is None:
            raise ValueError("Select the stack operating sweep explicitly for a multi-sweep fit")
        if operating_spectrum_id not in sweep_ids:
            raise ValueError("Selected stack operating sweep is absent from the fitted spectra")
        operating_spectrum = sweeps[sweep_ids.index(operating_spectrum_id)]
        for name, value in (("parameter_name", parameter_name),
                            ("interpretation_id", interpretation_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Explicitly identify {name}")
        if fit.purpose != "parameter_estimation":
            raise ValueError("Only a measured/reconstructed PEM parameter-estimation fit is admissible")
        if expected_model_id is not None and fit.model_id != expected_model_id:
            raise ValueError("Fitted impedance model identity differs from the declared circuit")
        if parameter_name not in fit.parameter_values:
            raise KeyError(parameter_name)
        if not _fit_has_finite_parameters(fit):
            raise ValueError("PEM fit result contains invalid parameter or diagnostic values")
        parameter_count = len(fit.parameter_values)
        condition_number = finite(fit.scaled_condition_number,
                                  "fit scaled condition number", positive=True)
        if fit.numerical_rank != parameter_count:
            raise ValueError("PEM coefficient transfer requires full numerical Jacobian rank")
        if any(name == parameter_name and status != 0
               for name, status in fit.active_parameter_bounds):
            raise ValueError("Selected PEM coefficient is active at an optimization bound")
        if maximum_condition_number is not None:
            maximum_condition_number = finite(
                maximum_condition_number, "maximum accepted fit condition number", positive=True,
            )
            if condition_number > maximum_condition_number:
                raise ValueError("PEM fit condition number exceeds the caller's admission limit")
        if fit.input_variables != (FREQUENCY, COMPONENT) or fit.response_variable != IMPEDANCE:
            raise ValueError("Fit result does not use the shared complex-impedance observation contract")
        observation_context = dict(experiment.observations.context)
        if observation_context.get("member_sha256") != experiment.report.member_sha256:
            raise ValueError("PEM member hash differs between the ingestion report and observation context")
        if observation_context.get("active_area_m2") != str(experiment.active_area_m2):
            raise ValueError("PEM active area differs from its retained observation context")
        observation_rows = experiment.observations.row_ids
        row_index = {row_id: index for index, row_id in enumerate(observation_rows)}
        source_row_ids = set(observation_rows)
        spectrum_tables = tuple(
            _validate_spectrum_binding(experiment, item, row_index, source_row_ids)
            for item in sweeps
        )
        fit_table = (spectrum_tables[0] if len(spectrum_tables) == 1 else
                     concatenate_observations(
                         spectrum_tables, source_id=experiment.observations.source_id,
                     ))
        if fit.fitting_data_sha256 != fit_table.content_sha256:
            raise ValueError("Fit data fingerprint differs from the ordered selected PEM sweeps")
        if fit.fitting_row_ids != fit_table.row_ids:
            raise ValueError("Fit row sequence differs from the selected PEM sweep observations")
        if fit.fitting_experiment_ids != tuple(sorted(sweep_ids)):
            raise ValueError("Fit experiment groups differ from the explicitly selected PEM sweeps")

        resistance = finite(fit.parameter_values[parameter_name], parameter_name, positive=True)
        area = finite(experiment.active_area_m2, "PEM active area", positive=True)
        fit_spectrum_hashes = tuple(table.content_sha256 for table in spectrum_tables)
        fit_dc_contexts = tuple(tuple(item.dc_context_row_ids) for item in sweeps)
        payload = cls._payload(
            resistance * area, resistance, area, parameter_name, fit.model_id,
            fit.fitting_data_sha256, experiment.observations.source_id,
            experiment.report.member_sha256, operating_spectrum.spectrum.experiment_id,
            sweep_ids, fit_spectrum_hashes, fit_dc_contexts,
            tuple(operating_spectrum.dc_context_row_ids), fit.numerical_rank, parameter_count,
            condition_number, fit.numerical_rank_relative_threshold,
            maximum_condition_number, operating_spectrum.dc_current_a,
            operating_spectrum.block_temperature_k, operating_spectrum.cathode_pressure_pa,
            interpretation_id, id(temperature_adjustment),
        )
        digest = cls._digest(payload)
        return cls(
            resistance * area, resistance, area, parameter_name, fit.model_id,
            fit.fitting_data_sha256, experiment.observations.source_id,
            experiment.report.member_sha256, operating_spectrum.spectrum.experiment_id,
            sweep_ids, fit_spectrum_hashes, fit_dc_contexts,
            tuple(operating_spectrum.dc_context_row_ids), fit.numerical_rank, parameter_count,
            condition_number, fit.numerical_rank_relative_threshold,
            maximum_condition_number, operating_spectrum.dc_current_a,
            operating_spectrum.block_temperature_k, operating_spectrum.cathode_pressure_pa,
            interpretation_id, digest, temperature_adjustment,
        )

    @staticmethod
    def _payload(*values: Any):
        return tuple(values)

    @staticmethod
    def _digest(payload):
        return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()

    def require_current(self):
        payload = self._payload(
            self.area_resistance_ohm_m2, self.cell_resistance_ohm,
            self.active_area_m2, self.parameter_name, self.model_id,
            self.fitting_data_sha256, self.source_id, self.source_member_sha256,
            self.spectrum_experiment_id,
            self.fit_spectrum_experiment_ids, self.fit_spectrum_sha256s,
            self.fit_dc_context_row_ids, self.dc_context_row_ids,
            self.fit_numerical_rank, self.fit_parameter_count,
            self.fit_condition_number, self.fit_rank_relative_threshold,
            self.maximum_condition_number,
            self.effective_operating_current_a, self.effective_block_temperature_k,
            self.effective_pressure_pa, self.interpretation_id,
            id(self._temperature_adjustment),
        )
        if self._digest(payload) != self._integrity_sha256:
            raise ValueError("PEM resistance binding changed after capture")
        if not abs(self.area_resistance_ohm_m2 - self.cell_resistance_ohm*self.active_area_m2) <= (
            1e-12 * max(abs(self.area_resistance_ohm_m2), 1.0)
        ):
            raise ValueError("Area resistance no longer matches cell resistance times area")
        return self

    def ohmic_loss(self) -> OhmicLoss:
        """Create the shared OhmicLoss callback, requiring explicit caller interpretation."""
        self.require_current()
        value = self.area_resistance_ohm_m2
        adjustment = self._temperature_adjustment
        return OhmicLoss(lambda temperature_k: value * (
            1.0 if adjustment is None else finite(
                adjustment(finite(temperature_k, "stack temperature", positive=True)),
                "caller resistance temperature multiplier", positive=True,
            )
        ))

    def extend_loss_mapping(
        self,
        losses: Mapping[str, Callable[[float, float], float]],
        *,
        component_id: str,
        allow_existing_ohmic_terms: bool = False,
        double_count_evidence_id: str | None = None,
    ) -> PemStackLossMap:
        """Return a new loss map with this contribution, rejecting accidental duplicates.

        Existing ohmic laws may represent distinct interfaces (for example, a
        separately characterized contact), but their coexistence must be an
        explicit caller decision with an evidence identity.
        """
        self.require_current()
        if not isinstance(losses, Mapping):
            raise TypeError("Supply the existing named HydrogenStack loss mapping")
        if not isinstance(component_id, str) or not component_id.strip():
            raise ValueError("Identify the new PEM-derived polarization component")
        copied = dict(losses)
        if any(not isinstance(name, str) or not name.strip() or not callable(model)
               for name, model in copied.items()):
            raise ValueError("Existing stack losses need nonempty names and callable laws")
        if component_id in copied:
            raise ValueError("The requested PEM loss component already exists")
        if not isinstance(allow_existing_ohmic_terms, bool):
            raise TypeError("Declare whether separately owned ohmic laws may coexist")
        existing_ohmic = tuple(name for name, model in copied.items()
                                if isinstance(model, OhmicLoss))
        if existing_ohmic and not allow_existing_ohmic_terms:
            raise ValueError("An ohmic law already exists; prevent double counting or explicitly justify it")
        if existing_ohmic and allow_existing_ohmic_terms:
            if not isinstance(double_count_evidence_id, str) or not double_count_evidence_id.strip():
                raise ValueError("Identify evidence for the distinct coexisting ohmic contributions")
        elif double_count_evidence_id is not None and (
            not isinstance(double_count_evidence_id, str) or not double_count_evidence_id.strip()
        ):
            raise ValueError("Double-count evidence identity must be nonempty when supplied")
        copied[component_id] = self.ohmic_loss()
        return PemStackLossMap(
            self, copied, component_id,
            tuple(name for name, model in copied.items()
                  if name != component_id and isinstance(model, OhmicLoss)),
            double_count_evidence_id,
        )

    def voltage_loss_v(self, current_density_a_m2: float, temperature_k: float) -> float:
        """Evaluate the bridged loss after rechecking the immutable receipt."""
        self.require_current()
        return self.ohmic_loss()(current_density_a_m2, temperature_k)


def _fit_has_finite_parameters(fit: FitResult) -> bool:
    """Apply inexpensive structural checks without rerunning parameter estimation."""
    values = fit.parameter_values
    return bool(
        values
        and all(_finite_parameter(value) for value in values.values())
        and len(fit.fitting_data_sha256) == 64
        and fit.fitting_row_ids
        and fit.fitting_experiment_ids
    )


def _validate_spectrum_binding(experiment, spectrum, row_index, source_row_ids):
    if not spectrum.dc_context_row_ids or spectrum.dc_current_a is None:
        raise ValueError("Every fitted PEM sweep needs a reconstructed DC operating point")
    if spectrum.block_temperature_k is None or spectrum.cathode_pressure_pa is None:
        raise ValueError("Every fitted PEM sweep needs block-temperature and absolute-pressure context")
    if spectrum.spectrum.source_id != experiment.observations.source_id:
        raise ValueError("Spectrum and PEM experiment source identities differ")
    if (spectrum.spectrum.origin.value != "reconstructed"
            or spectrum.spectrum.frequency_origin.value != "measured"):
        raise ValueError("Complex impedance must retain reconstructed response and measured frequency origins")
    if (not set(spectrum.spectrum.row_ids) <= source_row_ids
            or not set(spectrum.dc_context_row_ids) <= source_row_ids):
        raise ValueError("Spectrum/DC context rows do not belong to the retained PEM experiment")
    parent_group = spectrum.spectrum.experiment_id.rsplit("/sweep-", 1)[0]
    dc_indices = tuple(row_index[row] for row in spectrum.dc_context_row_ids)
    point_indices = tuple(row_index[row] for row in spectrum.spectrum.row_ids)
    if (tuple(sorted(point_indices)) != point_indices
            or any(experiment.observations.experiment_ids[index] != parent_group
                   for index in point_indices)):
        raise ValueError("Spectrum points must be an ordered subset of their retained PEM protocol group")
    if (max(dc_indices) >= min(point_indices)
            or any(experiment.measurement_types[index] == "POL_GEIS" for index in dc_indices)):
        raise ValueError("DC context must retain preceding non-EIS operating-point observations")
    if spectrum.dc_gap_s is None or finite(spectrum.dc_gap_s, "PEM DC context gap") < 0:
        raise ValueError("Retain a nonnegative measured DC-to-spectrum time gap")
    return spectrum.spectrum.cartesian_observations()


def _finite_parameter(value) -> bool:
    try:
        finite(value, "fitted parameter")
    except (TypeError, ValueError):
        return False
    return math.isfinite(float(value))


@dataclass(frozen=True, slots=True)
class PemStackLossMap(Mapping[str, Callable[[float, float], float]]):
    """Immutable `HydrogenStack` loss mapping with its PEM/source audit attached."""

    binding: PemOhmicLossBinding
    losses: Mapping[str, Callable[[float, float], float]]
    pem_component_id: str
    existing_ohmic_term_ids: tuple[str, ...]
    double_count_evidence_id: str | None = None
    _entry_bindings: tuple = ()

    def __post_init__(self):
        if type(self.binding) is not PemOhmicLossBinding:
            raise TypeError("Retain the originating PEM EIS source/fit binding")
        self.binding.require_current()
        if not isinstance(self.losses, Mapping):
            raise TypeError("Stack loss receipt requires a mapping")
        copied = dict(self.losses)
        if any(not isinstance(name, str) or not name.strip() or not callable(model)
               for name, model in copied.items()):
            raise ValueError("Every stack loss needs a nonempty name and callable law")
        if (self.pem_component_id not in copied
                or not isinstance(copied[self.pem_component_id], OhmicLoss)):
            raise ValueError("Stack loss receipt must retain its PEM-derived OhmicLoss")
        observed_ohmic = tuple(name for name, model in copied.items()
                               if name != self.pem_component_id and isinstance(model, OhmicLoss))
        if observed_ohmic != tuple(self.existing_ohmic_term_ids):
            raise ValueError("Recorded existing-ohmic names differ from the retained loss mapping")
        if observed_ohmic and (not isinstance(self.double_count_evidence_id, str)
                               or not self.double_count_evidence_id.strip()):
            raise ValueError("Coexisting ohmic terms require retained distinction evidence")
        object.__setattr__(self, "losses", MappingProxyType(copied))
        object.__setattr__(self, "existing_ohmic_term_ids", observed_ohmic)
        object.__setattr__(self, "_entry_bindings",
                           tuple((name, model) for name, model in copied.items()))

    def require_current(self):
        self.binding.require_current()
        if tuple(self.losses.items()) != self._entry_bindings:
            raise ValueError("Stack loss mapping entries changed after capture")
        return self

    def __getitem__(self, key):
        self.require_current()
        return self.losses[key]

    def __iter__(self):
        self.require_current()
        return iter(self.losses)

    def __len__(self):
        self.require_current()
        return len(self.losses)
