"""Source-bound observations for the licensed cryogenic MOF data record."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from .acquire import _is_linklike
from .models import Dataset, RemoteFile

_DATASET_KEY = "cryo-mof-dormancy"
_DATASET_DOI = "10.57745/FCV2R0"
_DATASET_VERSION = "1.1"
_LICENSE_ID = "etalab-2.0"
_LICENSE_URL = "https://spdx.org/licenses/etalab-2.0.html"
_EXPECTED_FILE = re.compile(r"^H2\.(20|77|87)K--(.+)\.csv$")
_PENDING = set()


@dataclass(frozen=True, slots=True)
class CryoMOFObservation:
    """One exact source row and one direction; values are never assigned a time."""

    source_row: int
    direction: str
    pressure_source_token: str
    uptake_source_token: str
    pressure_value_si: float | None
    uptake_value_si: float | None


@dataclass(frozen=True, slots=True)
class CryoMOFIsothermTable:
    """Two source-ordered adsorption branches tied to one checked CSV attachment."""

    dataset: Dataset = field(repr=False, compare=False)
    source_path: Path = field(repr=False, compare=False)
    source_file_name: str
    source_sha256: str
    source_row_count: int
    source_columns: tuple[str, ...]
    temperature_k: float
    material_label: str
    pressure_quantity: str
    pressure_source_unit: str
    pressure_si_unit: str
    pressure_basis_id: str
    uptake_quantity: str
    uptake_source_unit: str
    uptake_si_unit: str
    uptake_basis_id: str
    observations: tuple[CryoMOFObservation, ...]
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("CryoMOFIsothermTable must be issued by its receipt-checking loader")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "source_path", Path(self.source_path).resolve())
        object.__setattr__(self, "source_columns", tuple(self.source_columns))
        object.__setattr__(self, "observations", tuple(self.observations))
        if (type(self.dataset) is not Dataset or self.dataset.key != _DATASET_KEY
                or self.dataset.doi != _DATASET_DOI or self.dataset.version != _DATASET_VERSION
                or self.dataset.license_id != _LICENSE_ID
                or self.dataset.license_url != _LICENSE_URL):
            raise ValueError("Supply the pinned, explicitly licensed cryogenic MOF dataset receipt")
        if (not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256)
                or type(self.source_row_count) is not int or self.source_row_count < 1
                or len(self.observations) != 2 * self.source_row_count):
            raise ValueError("Retain the exact source digest and both observations for every row")
        if tuple(row.source_row for row in self.observations[::2]) != tuple(
                range(2, self.source_row_count + 2)):
            raise ValueError("Source row identities must preserve file order after the header")
        if any(row.direction != direction for pair in zip(
                self.observations[::2], self.observations[1::2], strict=True)
                for row, direction in zip(pair, ("adsorption", "desorption"), strict=True)):
            raise ValueError("Each source row must retain adsorption then desorption order")
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (
            id(self.dataset), self.dataset.key, self.dataset.title, self.dataset.doi,
            self.dataset.version, self.dataset.authors, self.dataset.license_id,
            self.dataset.license_url, self.dataset.metadata_url,
            self.dataset.metadata_sha256,
            hashlib.sha256(self.dataset.metadata_bytes).hexdigest(),
            self.dataset.origin, self.dataset.families, self.dataset.source_updated_at,
            tuple((item.name, item.url, item.size_bytes, item.checksum_algorithm,
                   item.checksum) for item in self.dataset.files),
            tuple((url, hashlib.sha256(content).hexdigest())
                  for url, content in self.dataset.supporting_metadata),
            self.source_path, self.source_file_name, self.source_sha256,
            self.source_row_count, self.source_columns, self.temperature_k,
            self.material_label, self.pressure_quantity, self.pressure_source_unit,
            self.pressure_si_unit, self.pressure_basis_id, self.uptake_quantity,
            self.uptake_source_unit, self.uptake_si_unit, self.uptake_basis_id,
            tuple((row.source_row, row.direction, row.pressure_source_token,
                   row.uptake_source_token, row.pressure_value_si, row.uptake_value_si)
                  for row in self.observations),
        )

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Cryogenic MOF source receipt or observations changed after loading")
        if _is_linklike(self.source_path) or not self.source_path.is_file():
            raise ValueError("Cryogenic MOF attachment must remain a regular source file")
        remote = next((item for item in self.dataset.files
                       if item.name == self.source_file_name), None)
        if remote is None or self.source_path.stat().st_size != remote.size_bytes:
            raise ValueError("Cryogenic MOF attachment size changed after loading")
        with self.source_path.open("rb") as stream:
            data = stream.read(remote.size_bytes + 1)
        actual = hashlib.sha256(data).hexdigest()
        if actual != self.source_sha256:
            raise ValueError("Cryogenic MOF attachment bytes changed after loading")
        rebuilt = _parse_source(data, self.source_file_name)
        if (rebuilt[0] != self.source_row_count or rebuilt[1] != self.source_columns
                or rebuilt[-1] != self.observations):
            raise ValueError("Cryogenic MOF source rows no longer reproduce the loaded table")
        return self

    def branch(self, direction: str) -> tuple[CryoMOFObservation, ...]:
        self.require_current()
        if direction not in {"adsorption", "desorption"}:
            raise ValueError("Select adsorption or desorption")
        return tuple(row for row in self.observations if row.direction == direction)

    def observation_table(self, direction: str):
        """Project one branch into the shared non-time fitting API with its basis intact."""
        import numpy as np

        from ..core import Origin
        from ..observations import ObservationTable, Variable

        rows = self.branch(direction)
        values = np.asarray([
            (np.nan if row.pressure_value_si is None else row.pressure_value_si,
             np.nan if row.uptake_value_si is None else row.uptake_value_si)
            for row in rows], dtype=float)
        source = f"{self.dataset.doi}:{self.dataset.version}:{self.source_file_name}"
        return ObservationTable(
            values=values,
            variables=(Variable("pressure_coordinate", self.pressure_quantity,
                                self.pressure_si_unit, self.pressure_basis_id),
                       Variable("uptake", self.uptake_quantity,
                                self.uptake_si_unit, self.uptake_basis_id)),
            valid=np.isfinite(values),
            row_ids=tuple(f"{source}:row-{row.source_row}:{direction}" for row in rows),
            experiment_ids=(source,) * len(rows),
            origins=(Origin.MEASURED, Origin.MEASURED), source_id=source,
            context=(("direction", direction), ("material_label", self.material_label),
                     ("temperature_k", str(self.temperature_k)),
                     ("source_sha256", self.source_sha256),
                     ("metadata_sha256", self.dataset.metadata_sha256),
                     ("license_id", self.dataset.license_id),
                     ("basis_qualified", "false")),
        )


def _parse_source(data: bytes, file_name: str):
    match = _EXPECTED_FILE.fullmatch(file_name)
    if not match:
        raise ValueError("Select one declared H2 isotherm CSV member")
    temperature = float(match.group(1))
    material = match.group(2)
    try:
        text = data.decode("utf-8-sig")
        rows = tuple(tuple(cell.strip() for cell in row)
                     for row in csv.reader(io.StringIO(text, newline="")))
    except (UnicodeDecodeError, csv.Error) as error:
        raise ValueError("Cryogenic MOF source must be a UTF-8 comma-delimited table") from error
    if not rows or len(rows[0]) != 4 or any(len(row) != 4 for row in rows[1:]):
        raise ValueError("Expected four paired adsorption/desorption source columns")
    columns = rows[0]
    header = tuple(value.casefold().replace("²", "2").replace("−", "-") for value in columns)
    expected_roles = ("relative pressure adsorption", "quantity adsorbed",
                      "relative pressure desorption", "quantity desorbed")
    if any(role not in label for role, label in zip(expected_roles, header, strict=True)):
        raise ValueError("Source columns do not match the pinned paired-isotherm layout")

    if temperature == 20.0 and all("p/p" in label for label in (header[0], header[2])):
        pressure_quantity, pressure_source_unit, pressure_si_unit = "normalized_pressure", "p/p", "1"
        pressure_basis = "reported normalized pressure; denominator state unresolved"
        pressure_factor = 1.0
    elif temperature in {77.0, 87.0} and all("bar" in label for label in (header[0], header[2])):
        pressure_quantity, pressure_source_unit, pressure_si_unit = "reported_pressure", "bar", "Pa"
        pressure_basis = "reported relative-pressure label; pressure basis unresolved"
        pressure_factor = 1e5
    else:
        raise ValueError("Pressure label/unit combination is outside the reviewed source schema")

    if temperature == 20.0 and all("cm3 g-1 stp" in label for label in (header[1], header[3])):
        uptake_quantity, uptake_source_unit, uptake_si_unit = (
            "reference_specific_volume", "cm3/g STP", "m3/kg")
        uptake_basis = "source-reported reference volume; STP state unresolved"
        uptake_factor = 1e-3
    elif temperature in {77.0, 87.0} and all("mmol/g" in label for label in (header[1], header[3])):
        uptake_quantity, uptake_source_unit, uptake_si_unit = "specific_amount", "mmol/g", "mol/kg"
        uptake_basis = "source-reported uptake; excess/absolute and mass convention unresolved"
        uptake_factor = 1.0
    else:
        raise ValueError("Uptake label/unit combination is outside the reviewed source schema")

    def number(token, factor, label):
        if token == "":
            return None
        try:
            value = float(token)
        except ValueError as error:
            raise ValueError(f"Invalid {label} token at source row: {token!r}") from error
        if not math.isfinite(value):
            raise ValueError(f"Nonfinite {label} value in source data")
        converted = value * factor
        if not math.isfinite(converted):
            raise ValueError(f"{label} conversion overflowed the numeric representation")
        return converted

    observations = []
    for index, row in enumerate(rows[1:], start=2):
        for direction, pressure_index, uptake_index in (
                ("adsorption", 0, 1), ("desorption", 2, 3)):
            pressure_token, uptake_token = row[pressure_index], row[uptake_index]
            observations.append(CryoMOFObservation(
                source_row=index,
                direction=direction,
                pressure_source_token=pressure_token,
                uptake_source_token=uptake_token,
                pressure_value_si=number(pressure_token, pressure_factor, "pressure"),
                uptake_value_si=number(uptake_token, uptake_factor, "uptake"),
            ))
    return (len(rows) - 1, columns, temperature, material,
            pressure_quantity, pressure_source_unit, pressure_si_unit, pressure_basis,
            uptake_quantity, uptake_source_unit, uptake_si_unit, uptake_basis,
            tuple(observations))


def load_cryo_mof_isotherm(path: str | Path, *, dataset: Dataset,
                            expected_sha256: str) -> CryoMOFIsothermTable:
    """Load one checksum-bound H2 isotherm; no time or uptake convention is inferred."""
    if (type(dataset) is not Dataset or dataset.key != _DATASET_KEY
            or dataset.doi != _DATASET_DOI or dataset.version != _DATASET_VERSION
            or dataset.license_id != _LICENSE_ID or dataset.license_url != _LICENSE_URL):
        raise ValueError("Resolve the pinned cryogenic MOF dataset and Etalab license receipt first")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("Supply the file SHA-256 from the separately reviewed acquisition receipt")
    source_path = Path(path)
    if _is_linklike(source_path) or not source_path.is_file():
        raise ValueError("Cryogenic MOF attachment must be a regular non-symlink file")
    source_path = source_path.resolve()
    name = source_path.name
    remote = next((file for file in dataset.files if file.name == name), None)
    if type(remote) is not RemoteFile:
        raise ValueError("File name is absent from the pinned dataset metadata")
    if source_path.stat().st_size != remote.size_bytes:
        raise ValueError("Local attachment size differs from the publisher metadata")
    with source_path.open("rb") as stream:
        data = stream.read(remote.size_bytes + 1)
    if len(data) != remote.size_bytes:
        raise ValueError("Local attachment size differs from the publisher metadata")
    if remote.checksum and hashlib.new(
            remote.checksum_algorithm, data, usedforsecurity=False).hexdigest() != remote.checksum:
        raise ValueError("Local attachment differs from the publisher checksum")
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256:
        raise ValueError("Local attachment differs from the acquisition-receipt SHA-256")
    (count, columns, temperature, material, pressure_quantity, pressure_source_unit,
     pressure_si_unit, pressure_basis, uptake_quantity, uptake_source_unit,
     uptake_si_unit, uptake_basis, observations) = _parse_source(data, name)
    token = object()
    _PENDING.add(token)
    try:
        return CryoMOFIsothermTable(
            dataset=dataset, source_path=source_path, source_file_name=name,
            source_sha256=digest, source_row_count=count, source_columns=columns,
            temperature_k=temperature, material_label=material,
            pressure_quantity=pressure_quantity, pressure_source_unit=pressure_source_unit,
            pressure_si_unit=pressure_si_unit, pressure_basis_id=pressure_basis,
            uptake_quantity=uptake_quantity, uptake_source_unit=uptake_source_unit,
            uptake_si_unit=uptake_si_unit, uptake_basis_id=uptake_basis,
            observations=observations, _issuer=token,
        )
    except Exception:
        _PENDING.discard(token)
        raise


__all__ = ["CryoMOFObservation", "CryoMOFIsothermTable", "load_cryo_mof_isotherm"]
