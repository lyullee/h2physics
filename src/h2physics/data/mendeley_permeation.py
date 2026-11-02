"""Source-bound normalized permeation tables from a versioned Mendeley record.

The reader preserves publisher coordinates. It does not convert them into a
diffusivity, solubility, trap law, or material qualification.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..core import Origin, immutable_array, _real_numeric_array
from .models import Dataset, license_url_matches

_DATASET_KEY = "hydrogen-diffusivity-ms1700-qp1180"
_DOI = "10.17632/zj7zh24frt.1"
_TITLE = "Hydrogen diffusivity in MS1700 and QP1180 AHSS"
_AUTHORS = ("Giuseppe Macoretta", "Carlo Maria Belardini")
_FAMILIES = ("materials", "hydrogen_transport", "permeation")
_METADATA_URL = "https://data.mendeley.com/public-api/datasets/zj7zh24frt/snapshot/1"
_METADATA_SHA256 = "30ac6159d78ec7f035b415d2fc1eb62413170a7ba0e1af40902926b3293dfaf7"
_FILE_LIST_URL = (
    "https://data.mendeley.com/public-api/datasets/zj7zh24frt/files?"
    "folder_id=root&version=1&$start=0&$limit=1000"
)
_FILE_LIST_SHA256 = "73d644d3be5a2c10e8f5b750bf57c240d27fa526ecfc7919d76db1b9afcec65c"
_FILE_NAME = "MS1700_QP1180_permeation.mat"
_FILE_URL = (
    "https://data.mendeley.com/public-files/datasets/zj7zh24frt/files/"
    "c99a7486-1248-45a0-9ee3-77cc2f23e02e/file_downloaded"
)
_FILE_SIZE = 39_455
_FILE_SHA256 = "db08ef98dd06d5cc7f42bea14ec8e32912f880a1cb6bd4c0ca585761901725fc"
_VARIABLE_ROWS = {"Msdata": 2197, "QPdata": 1333}
_LICENSE_ID = "CC-BY-4.0"
_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
_SOURCE_ID = "mendeley-hydrogen-permeation-ms1700-qp1180-v1"
_PENDING_SERIES_ISSUERS: set[object] = set()
_PENDING_DATASET_ISSUERS: set[object] = set()
_MAX_MAT_BYTES = 500_000


def _issue_series(**values):
    token = object()
    _PENDING_SERIES_ISSUERS.add(token)
    try:
        return NormalizedPermeationSeries(**values, _issuer_token=token)
    except Exception:
        _PENDING_SERIES_ISSUERS.discard(token)
        raise


def _issue_dataset(**values):
    token = object()
    _PENDING_DATASET_ISSUERS.add(token)
    try:
        return MendeleyPermeationDataset(**values, _issuer_token=token)
    except Exception:
        _PENDING_DATASET_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class NormalizedPermeationSeries:
    """One source matrix as normalized-time and normalized-flux columns."""

    material_grade: str
    variable_name: str
    coordinates: np.ndarray
    source_row_ids: tuple[str, ...]
    source_sha256: str
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_SERIES_ISSUERS:
            raise ValueError("Use the checksum-verifying Mendeley reader to issue source series")
        _PENDING_SERIES_ISSUERS.remove(self._issuer_token)
        expected = {"MS1700": ("Msdata", 2197), "QP1180": ("QPdata", 1333)}
        if expected.get(self.material_grade) != (self.variable_name, len(self.source_row_ids)):
            raise ValueError("Permeation series grade, MATLAB variable and row count must match the pinned source")
        if self.source_sha256 != _FILE_SHA256:
            raise ValueError("Permeation series must retain the pinned publisher-listed source bytes")
        rows = tuple(self.source_row_ids)
        expected_rows = tuple(
            f"{_SOURCE_ID}:{self.variable_name}:row-{index}"
            for index in range(1, len(rows) + 1)
        )
        if rows != expected_rows:
            raise ValueError("Permeation row identities must retain source order and one-based row numbers")
        values = _real_numeric_array(self.coordinates, "normalized permeation coordinates")
        if values.shape != (len(rows), 2) or not np.all(np.isfinite(values)):
            raise ValueError("Source coordinates must be a finite two-column numeric table")
        object.__setattr__(self, "coordinates", immutable_array(values, name="permeation coordinates"))
        object.__setattr__(self, "source_row_ids", rows)
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self):
        digest = hashlib.sha256()
        digest.update(self.coordinates.tobytes(order="C"))
        digest.update(repr((self.material_grade, self.variable_name,
                            self.source_row_ids, self.source_sha256)).encode())
        return digest.hexdigest()

    def require_current(self):
        """Reject a changed source series before consuming its coordinate views."""
        if self._fingerprint() != self._seal:
            raise ValueError("Normalized permeation series changed after source-bound loading")
        return self

    @property
    def normalized_time_s_m2(self) -> np.ndarray:
        """First publisher coordinate, retained with the record's stated s/m² unit."""
        self.require_current()
        return self.coordinates[:, 0]

    @property
    def normalized_flux(self) -> np.ndarray:
        """Second publisher coordinate; no dimensional flux unit is inferred."""
        self.require_current()
        return self.coordinates[:, 1]


@dataclass(frozen=True, slots=True)
class MendeleyPermeationDataset:
    """Two normalized source series plus the exact licensed attachment identity."""

    source_id: str
    title: str
    doi: str
    version: str
    authors: tuple[str, ...]
    origin: Origin
    source_file: str
    source_url: str
    source_sha256: str
    license_id: str
    license_url: str
    series: tuple[NormalizedPermeationSeries, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_DATASET_ISSUERS:
            raise ValueError("Use load_mendeley_normalized_permeation to issue this dataset")
        _PENDING_DATASET_ISSUERS.remove(self._issuer_token)
        if (self.source_id != _SOURCE_ID or self.title != _TITLE or self.doi != _DOI
                or self.version != "1" or tuple(self.authors) != _AUTHORS
                or self.origin is not Origin.MEASURED
                or self.source_file != _FILE_NAME or self.source_url != _FILE_URL
                or self.source_sha256 != _FILE_SHA256 or self.license_id != _LICENSE_ID
                or self.license_url != _LICENSE_URL):
            raise ValueError("Permeation result source, version, hash or license differs from the admitted record")
        series = tuple(self.series)
        if (len(series) != 2 or tuple(item.material_grade for item in series) != ("MS1700", "QP1180")
                or any(type(item) is not NormalizedPermeationSeries for item in series)):
            raise ValueError("The pinned record must retain both source material series in order")
        seal = hashlib.sha256()
        seal.update(repr((self.source_id, self.title, self.doi, self.version,
                          tuple(self.authors), self.origin, self.source_file,
                          self.source_url, self.source_sha256, self.license_id,
                          self.license_url)).encode())
        for item in series:
            item.require_current()
            seal.update(item._fingerprint().encode())
        object.__setattr__(self, "series", series)
        object.__setattr__(self, "_seal", seal.hexdigest())

    def require_current(self):
        """Reject altered or detached coordinate tables before downstream use."""
        seal = hashlib.sha256()
        seal.update(repr((self.source_id, self.title, self.doi, self.version,
                          tuple(self.authors), self.origin, self.source_file,
                          self.source_url, self.source_sha256, self.license_id,
                          self.license_url)).encode())
        for item in self.series:
            item.require_current()
            seal.update(item._fingerprint().encode())
        if seal.hexdigest() != self._seal:
            raise ValueError("Mendeley permeation coordinates changed after source-bound loading")
        return self

    def for_grade(self, material_grade: str) -> NormalizedPermeationSeries:
        """Select one explicitly named steel series without changing its coordinates."""
        self.require_current()
        matches = tuple(item for item in self.series if item.material_grade == material_grade)
        if len(matches) != 1:
            raise ValueError("Select exactly one source material grade: MS1700 or QP1180")
        return matches[0]


def _verify_dataset_receipt(dataset: Dataset):
    if type(dataset) is not Dataset:
        raise TypeError("Pass a resolved Dataset receipt for the exact Mendeley source")
    if (dataset.key != _DATASET_KEY or dataset.title != _TITLE or dataset.doi != _DOI
            or dataset.version != "1" or dataset.license_id != _LICENSE_ID
            or dataset.license_url != _LICENSE_URL or dataset.metadata_url != _METADATA_URL
            or dataset.metadata_sha256 != _METADATA_SHA256
            or hashlib.sha256(dataset.metadata_bytes).hexdigest() != _METADATA_SHA256):
        raise ValueError("Resolved dataset metadata is not the pinned Mendeley v1 source")
    try:
        metadata = json.loads(dataset.metadata_bytes)
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise ValueError("Pinned Mendeley metadata bytes are not valid JSON") from error
    license_data = metadata.get("licence") if isinstance(metadata, dict) else None
    contributors = metadata.get("contributors") if isinstance(metadata, dict) else None
    try:
        authors = tuple(" ".join(filter(None, (item.get("first_name"), item.get("last_name"))))
                        for item in contributors)
    except (AttributeError, TypeError):
        authors = ()
    if (not isinstance(metadata, dict) or metadata.get("id") != "zj7zh24frt"
            or metadata.get("version") != 1 or metadata.get("name") != _TITLE
            or metadata.get("doi") != _DOI or not isinstance(license_data, dict)
            or authors != _AUTHORS or dataset.authors != _AUTHORS
            or dataset.origin != "measured" or dataset.families != _FAMILIES
            or license_data.get("short_name") != "CC BY 4.0"
            or not license_url_matches(_LICENSE_ID, license_data.get("url", ""), require_https=False)):
        raise ValueError("Publisher metadata disagrees with the admitted dataset identity or license")
    listing_matches = tuple(
        payload for url, payload in dataset.supporting_metadata if url == _FILE_LIST_URL
    )
    if (len(listing_matches) != 1
            or hashlib.sha256(listing_matches[0]).hexdigest() != _FILE_LIST_SHA256):
        raise ValueError("Pinned Mendeley attachment-listing bytes are missing or changed")
    try:
        listing = json.loads(listing_matches[0])
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise ValueError("Pinned Mendeley attachment listing is not valid JSON") from error
    if not isinstance(listing, list) or len(listing) != 1:
        raise ValueError("Pinned Mendeley v1 record must list exactly one data attachment")
    entry = listing[0]
    if not isinstance(entry, dict):
        raise ValueError("Pinned Mendeley attachment entry must be an object")
    content = entry.get("content_details", {}) if isinstance(entry, dict) else {}
    if (entry.get("filename") != _FILE_NAME or entry.get("size") != _FILE_SIZE
            or content.get("sha256_hash") != _FILE_SHA256
            or content.get("download_url") != _FILE_URL):
        raise ValueError("Publisher attachment listing differs from the pinned MAT file receipt")
    if len(dataset.files) != 1:
        raise ValueError("Resolved source must contain its single pinned MATLAB attachment")
    remote = dataset.files[0]
    if (remote.name != _FILE_NAME or remote.url != _FILE_URL or remote.size_bytes != _FILE_SIZE
            or remote.checksum_algorithm != "sha256" or remote.checksum != _FILE_SHA256):
        raise ValueError("Resolved attachment object differs from the publisher's MAT file listing")


def load_mendeley_normalized_permeation(
    mat_path: str | Path, *, dataset: Dataset,
) -> MendeleyPermeationDataset:
    """Load both MAT arrays after verifying publisher metadata and file bytes.

    The raw matrix column order follows the publisher's normalized-time versus
    normalized-flux description. No row filtering, sorting, scaling, unit
    conversion or fitting is performed.
    """
    _verify_dataset_receipt(dataset)
    path = Path(mat_path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("MAT input must be a regular local file")
    declared_size = path.stat().st_size
    if declared_size != _FILE_SIZE or declared_size > _MAX_MAT_BYTES:
        raise ValueError("MAT file size differs from the bounded publisher record")
    payload = path.read_bytes()
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if len(payload) != _FILE_SIZE or actual_sha256 != _FILE_SHA256:
        raise ValueError("MAT file bytes differ from the publisher-listed SHA-256")
    try:
        from scipy.io import loadmat
    except ImportError as error:
        raise RuntimeError("The SciPy data extra is required to read this MATLAB attachment") from error
    try:
        content = loadmat(
            io.BytesIO(payload), squeeze_me=False,
            verify_compressed_data_integrity=True,
        )
    except (OSError, ValueError, NotImplementedError) as error:
        raise ValueError("Pinned MATLAB attachment could not be read as a supported MAT file") from error
    variables = {key for key in content if not key.startswith("__")}
    if variables != set(_VARIABLE_ROWS):
        raise ValueError("MAT variables differ from the two publisher-listed grade arrays")
    series = []
    for variable_name, grade in (("Msdata", "MS1700"), ("QPdata", "QP1180")):
        values = _real_numeric_array(content[variable_name], variable_name)
        if values.shape != (_VARIABLE_ROWS[variable_name], 2) or not np.all(np.isfinite(values)):
            raise ValueError(f"{variable_name} shape or values differ from the pinned two-column source schema")
        source_rows = tuple(
            f"{_SOURCE_ID}:{variable_name}:row-{index}"
            for index in range(1, _VARIABLE_ROWS[variable_name] + 1)
        )
        series.append(_issue_series(
            material_grade=grade, variable_name=variable_name, coordinates=values,
            source_row_ids=source_rows, source_sha256=actual_sha256,
        ))
    return _issue_dataset(
        source_id=_SOURCE_ID, title=_TITLE, doi=_DOI, version="1",
        authors=_AUTHORS, origin=Origin.MEASURED, source_file=_FILE_NAME,
        source_url=_FILE_URL, source_sha256=actual_sha256, license_id=_LICENSE_ID,
        license_url=_LICENSE_URL, series=tuple(series),
    )


__all__ = [
    "MendeleyPermeationDataset",
    "NormalizedPermeationSeries",
    "load_mendeley_normalized_permeation",
]
