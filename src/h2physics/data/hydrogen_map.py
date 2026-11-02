"""Source-pinned reader for the Wasserstoffatlas facility inventory CSV."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field
from pathlib import Path

SOURCE_DOI = "10.5281/zenodo.10548190"
SOURCE_URL = "https://zenodo.org/records/10548190"
SOURCE_FILE = "Bestand.csv"
SOURCE_SIZE = 181145
SOURCE_MD5 = "078c7049bbef5967194105c35e2af720"
SOURCE_SHA256 = "050e7b8a5a45d554640c2668ab87b6e9c3d0d4658e7ee4a572d7a0864092e8fe"
LICENSE = "CC-BY-4.0"
ATTRIBUTION = "Schumm, Leon; Birett, Falk; Hofrichter, Andreas; Heusgen, Valentin; Rahim, Stefan (2024), Wasserstoffatlas (Hydrogen Map) Dataset, v6, Zenodo, https://doi.org/10.5281/zenodo.10548190."

_COLUMNS = (
    "id", "Standort", "Endprodukt", "yearStart", "yearEnd", "ElLeistung", "UmVerf",
    "Status", "Art", "name", "Emissionen", "Branche", "Quelle", "Nachfrage",
    "NutzSek", "NUTS0", "NUTS1", "NUTS2", "NUTS3", "geometry",
)
_PENDING_ISSUERS: set[object] = set()
_ISSUED_INVENTORIES: dict[object, int] = {}


@dataclass(frozen=True, slots=True)
class HydrogenMapFacility:
    """One source row; source tokens and unqualified units are preserved verbatim."""

    row_number: int
    source_id: str
    location_label: str
    end_product: str
    start_year_token: str
    end_year_token: str
    electrical_capacity_token: str
    conversion_process: str
    status: str
    facility_type: str
    name: str
    emissions_token: str
    sector: str
    source_lineage: str
    demand_token: str
    utilization_sector: str
    nuts0: str
    nuts1: str
    nuts2: str
    nuts3: str
    geometry_wkt: str


@dataclass(frozen=True, slots=True)
class HydrogenMapInventory:
    """Pinned source inventory with required reuse attribution."""

    path: Path
    rows: tuple[HydrogenMapFacility, ...]
    sha256: str
    md5: str
    attribution: str = ATTRIBUTION
    license: str = LICENSE
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_ISSUERS:
            raise ValueError("Hydrogen Map inventory receipts must be issued by the pinned source reader")
        if self.path.name != SOURCE_FILE or self.license != LICENSE or self.attribution != ATTRIBUTION:
            raise ValueError("Hydrogen Map source path or rights attribution differs from the pinned record")
        _PENDING_ISSUERS.remove(token)
        _ISSUED_INVENTORIES[token] = id(self)

    def require_current(self) -> None:
        if _ISSUED_INVENTORIES.get(self._issuer_token) != id(self):
            raise ValueError("Hydrogen Map inventory receipt was not issued by this reader")
        if (self.path.name != SOURCE_FILE or self.license != LICENSE
                or self.attribution != ATTRIBUTION):
            raise ValueError("Hydrogen Map inventory path or source rights attribution was changed")
        other = read_hydrogen_map_inventory(self.path)
        if other.sha256 != self.sha256 or other.rows != self.rows:
            raise ValueError("Hydrogen Map inventory bytes or parsed rows changed")


def read_hydrogen_map_inventory(path: str | Path) -> HydrogenMapInventory:
    """Read only the reviewed Bestand.csv byte revision; no unit inference is performed."""
    source_path = Path(path)
    raw = source_path.read_bytes()
    md5 = hashlib.md5(raw).hexdigest()
    sha256 = hashlib.sha256(raw).hexdigest()
    if len(raw) != SOURCE_SIZE or md5 != SOURCE_MD5 or sha256 != SOURCE_SHA256:
        raise ValueError("Wasserstoffatlas Bestand.csv differs from the reviewed publisher revision")
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != _COLUMNS:
        raise ValueError("Unexpected Wasserstoffatlas inventory CSV schema")
    rows = []
    for row_number, item in enumerate(reader, start=2):
        if None in item or any(item.get(name) is None for name in _COLUMNS):
            raise ValueError(f"Malformed inventory row {row_number}")
        values = [item[name] for name in _COLUMNS]
        rows.append(HydrogenMapFacility(row_number, *values))
    if len(rows) != 1049:
        raise ValueError(f"Unexpected Bestand.csv row count: {len(rows)}")
    token = object()
    _PENDING_ISSUERS.add(token)
    try:
        return HydrogenMapInventory(source_path, tuple(rows), sha256, md5, _issuer_token=token)
    except Exception:
        _PENDING_ISSUERS.discard(token)
        raise
