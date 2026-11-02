"""Non-time observations with explicit variables, origins and experiment identities."""

import hashlib
from collections.abc import Collection
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .core import Origin, immutable_array

GAS_VOLUME_FRACTION_BASIS = "gas-phase H2 volume / total sample gas volume"


@dataclass(frozen=True, slots=True)
class Variable:
    name: str
    quantity: str
    unit: str
    basis_id: str = ""

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.name, self.quantity, self.unit)):
            raise ValueError("Observation variable name, quantity and unit must be explicit")
        if not isinstance(self.basis_id, str):
            raise TypeError("Observation measurement/reference basis must be a string")
        if (self.quantity in {"reference_specific_volume", "specific_amount", "normalized_pressure", "reported_pressure"}
                and not self.basis_id.strip()):
            raise ValueError("This observation quantity needs an explicit measurement/reference basis")

    def require_compatible(self, other: "Variable"):
        if not isinstance(other, Variable):
            raise TypeError("Compare observation variables with another Variable contract")
        if (self.quantity, self.unit, self.basis_id) != (other.quantity, other.unit, other.basis_id):
            raise ValueError("Observation quantity, unit or measurement/reference basis differs")


@dataclass(frozen=True, slots=True)
class ObservationTable:
    values: NDArray[np.float64]
    variables: tuple[Variable, ...]
    valid: NDArray[np.bool_]
    row_ids: tuple[str, ...]
    experiment_ids: tuple[str, ...]
    origins: tuple[Origin, ...]
    source_id: str
    context: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        variables = tuple(self.variables)
        values = np.array(self.values, dtype=float, copy=True)
        valid = np.array(self.valid, dtype=bool, copy=True)
        row_ids, experiment_ids = tuple(self.row_ids), tuple(self.experiment_ids)
        origins = tuple(Origin(value) for value in self.origins)
        context = tuple(tuple(item) if isinstance(item, (tuple, list)) else item
                        for item in self.context)
        if not variables or not all(isinstance(variable, Variable) for variable in variables):
            raise ValueError("An observation table needs declared Variable objects")
        if values.ndim != 2 or values.shape[1] != len(variables) or valid.shape != values.shape:
            raise ValueError("Observation arrays must match the declared variable columns")
        if (len(row_ids) != len(values)
                or any(not isinstance(row, str) or not row.strip() for row in row_ids)):
            raise ValueError("Every observation row needs a unique, nonempty source-row identity")
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("Observation source-row identities must be unique")
        if (len(experiment_ids) != len(values)
                or any(not isinstance(value, str) or not value.strip() for value in experiment_ids)):
            raise ValueError("Every row needs its experimental grouping identity")
        if (len(origins) != len(variables)
                or any(not isinstance(variable.name, str) or not variable.name.strip()
                       for variable in variables)
                or len({v.name for v in variables}) != len(variables)):
            raise ValueError("Variables need unique names and one declared origin each")
        if (not isinstance(self.source_id, str) or not self.source_id.strip()
                or np.any(valid & ~np.isfinite(values))):
            raise ValueError("Source identity is required; nonfinite values cannot be marked valid")
        if (any(not isinstance(item, tuple) or len(item) != 2 for item in context)
                or any(not isinstance(key, str) or not key.strip()
                       or not isinstance(value, str)
                       for key, value in context)
                or len({key for key, _ in context}) != len(context)):
            raise ValueError("Context keys must be nonempty and unique")
        context = tuple((key, value) for key, value in context)
        values = immutable_array(values, name="observation values")
        valid = immutable_array(valid, name="observation validity mask")
        for name, value in (("values", values), ("valid", valid), ("variables", variables),
                            ("row_ids", row_ids), ("experiment_ids", experiment_ids),
                            ("origins", origins), ("context", context)):
            object.__setattr__(self, name, value)

    def column(self, name: str, *, expected: Variable | None = None):
        index = next((i for i, variable in enumerate(self.variables) if variable.name == name), None)
        if index is None:
            raise KeyError(name)
        if expected is not None:
            expected.require_compatible(self.variables[index])
        return self.values[:, index], self.valid[:, index]

    def complete_rows(self, *names: str):
        """Return a mask; observations are not dropped until the caller selects rows."""
        if not names:
            raise ValueError("Declare the variables required by the observation operator")
        return np.logical_and.reduce([self.column(name)[1] for name in names])

    @property
    def content_sha256(self):
        """Fingerprint actual arrays and their meanings, not only an external filename."""
        digest = hashlib.sha256()

        def add(value):
            payload = value if isinstance(value, bytes) else str(value).encode("utf-8")
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)

        add("h2physics-observations-v1")
        add(self.values.shape)
        add(np.asarray(self.values, dtype="<f8").tobytes(order="C"))
        add(self.valid.tobytes(order="C"))
        add(self.source_id)
        for label, group in (("variables", self.variables), ("origins", self.origins),
                              ("rows", self.row_ids), ("experiments", self.experiment_ids),
                              ("context", self.context)):
            add(label)
            add(len(group))
            for value in group:
                if isinstance(value, Variable):
                    for field in (value.name, value.quantity, value.unit, value.basis_id):
                        add(field)
                elif isinstance(value, tuple):
                    for item in value:
                        add(item)
                else:
                    add(value)
        return digest.hexdigest()

    def select_rows(self, selection) -> "ObservationTable":
        indices = np.arange(len(self.values))[selection]
        if np.ndim(indices) != 1:
            raise ValueError("Select a one-dimensional observation row sequence")
        return ObservationTable(self.values[indices], self.variables, self.valid[indices],
                                 tuple(self.row_ids[i] for i in indices),
                                 tuple(self.experiment_ids[i] for i in indices), self.origins,
                                 self.source_id, self.context)


@dataclass(frozen=True, slots=True)
class ExperimentPartition:
    fitting: ObservationTable
    held_out: ObservationTable

    def require_partition_of(self, source: ObservationTable):
        """Verify that both children are the exact whole-group split of ``source``.

        This permits a partition to travel through Python APIs while retaining a
        caller-checkable link to the original immutable observation table. It
        validates row/data lineage only; group separation does not establish
        statistical independence or an external validation basis.
        """
        if type(source) is not ObservationTable:
            raise TypeError("A partition must be checked against its original ObservationTable")
        if type(self.fitting) is not ObservationTable or type(self.held_out) is not ObservationTable:
            raise TypeError("Partition members must be ObservationTable objects")
        held_groups = set(self.held_out.experiment_ids)
        available = set(source.experiment_ids)
        if not held_groups or not held_groups < available:
            raise ValueError("Held-out rows must identify a nonempty proper subset of source groups")
        mask = np.asarray([group in held_groups for group in source.experiment_ids], dtype=bool)
        expected_fitting = source.select_rows(~mask)
        expected_held_out = source.select_rows(mask)
        if (self.fitting.content_sha256 != expected_fitting.content_sha256
                or self.held_out.content_sha256 != expected_held_out.content_sha256):
            raise ValueError("Partition rows, values, masks or metadata differ from the exact source split")
        return self


def split_experiments(table: ObservationTable, held_out: Collection[str]) -> ExperimentPartition:
    """Partition whole declared groups; no random row split or independence claim."""
    if type(table) is not ObservationTable:
        raise TypeError("Partition an ObservationTable by its declared experiment identities")
    if isinstance(held_out, (str, bytes)):
        raise TypeError("held_out must be a collection of whole experiment IDs, not text")
    held_out = set(held_out)
    if any(not isinstance(group, str) or not group.strip() for group in held_out):
        raise TypeError("Held-out experiment IDs must be nonempty strings")
    available = set(table.experiment_ids)
    if not held_out or not held_out < available:
        raise ValueError("Held-out groups must be a nonempty proper subset of known experiments")
    mask = np.array([group in held_out for group in table.experiment_ids], dtype=bool)
    return ExperimentPartition(table.select_rows(~mask), table.select_rows(mask)).require_partition_of(table)


def concatenate_observations(tables: Collection[ObservationTable], *, source_id: str):
    """Preserve row order/groups and retain parent fingerprints; no clock is invented."""
    if isinstance(tables, (str, bytes)):
        raise TypeError("tables must be a collection of ObservationTable objects, not text")
    tables = tuple(tables)
    if not tables or any(type(table) is not ObservationTable for table in tables):
        raise TypeError("Concatenation requires one or more ObservationTable objects")
    if any(t.variables != tables[0].variables or t.origins != tables[0].origins for t in tables):
        raise ValueError("Concatenation needs matching variables, meanings and origins")
    context = tuple(item for i, table in enumerate(tables)
                    for item in ((f"parent_{i}_source", table.source_id),
                                 (f"parent_{i}_sha256", table.content_sha256)))
    return ObservationTable(np.concatenate([t.values for t in tables]), tables[0].variables,
        np.concatenate([t.valid for t in tables]), tuple(row for t in tables for row in t.row_ids),
        tuple(group for t in tables for group in t.experiment_ids), tables[0].origins, source_id, context)
