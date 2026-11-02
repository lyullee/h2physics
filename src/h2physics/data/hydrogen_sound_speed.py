"""Hash-bound rows from the CC BY 4.0 compiled hydrogen acoustic archive."""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from .pif import PropertyFile, acoustic_columns, read_property_file

_DOI = "10.5281/zenodo.21355851"
_METADATA_SHA256 = "1d83651ff168e7eae59c3688e25957392169034ebbdbd05c2cefe3c8b75ee3ad"
_ARCHIVE_SHA256 = "38a5c10a9fb06c41a32f4fbba4ac0d1dabb3b38a7e80490ebc587a2e6dcfd553"
_ARCHIVE_MD5 = "d564f1a2e5b19d1c979d7f321f05de2b"
_ARCHIVE_SIZE = 45826
_METADATA_SIZE = 6458
_PENDING: set[object] = set()


def _hash(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


@dataclass(frozen=True, slots=True)
class HydrogenAcousticFile:
    member_path: str
    member_sha256: str
    property_file: PropertyFile
    source_rows: tuple[str, ...]


def _issue(**values):
    token = object()
    _PENDING.add(token)
    try:
        return HydrogenAcousticDataset(**values, _issuer=token)
    except Exception:
        _PENDING.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class HydrogenAcousticDataset:
    doi: str
    license_id: str
    license_url: str
    authors: tuple[str, ...]
    archive_path: Path = field(repr=False, compare=False)
    metadata_path: Path = field(repr=False, compare=False)
    archive_sha256: str
    metadata_sha256: str
    files: tuple[HydrogenAcousticFile, ...]
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Use load_hydrogen_acoustic_dataset() to issue source rows")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "archive_path", Path(self.archive_path).resolve())
        object.__setattr__(self, "metadata_path", Path(self.metadata_path).resolve())
        object.__setattr__(self, "authors", tuple(self.authors))
        object.__setattr__(self, "files", tuple(self.files))
        if (self.doi != _DOI or self.license_id != "CC-BY-4.0"
                or self.license_url != "https://creativecommons.org/licenses/by/4.0/"
                or self.archive_sha256 != _ARCHIVE_SHA256
                or self.metadata_sha256 != _METADATA_SHA256
                or not self.authors or len(self.files) != 30):
            raise ValueError("Acoustic source receipt differs from the admitted Zenodo v1 record")
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (self.doi, self.license_id, self.license_url, self.authors,
                self.archive_path, self.metadata_path, self.archive_sha256,
                self.metadata_sha256,
                tuple((item.member_path, item.member_sha256, item.property_file.name,
                       tuple(item.property_file.metadata.items()),
                       tuple((loop.tags, loop.values.tobytes()) for loop in item.property_file.loops),
                       item.source_rows) for item in self.files))

    def require_current(self):
        if self._payload() != self._seal:
            raise ValueError("Acoustic dataset rows or license receipt changed after loading")
        if _hash(self.archive_path) != (_ARCHIVE_SHA256, _ARCHIVE_SIZE):
            raise ValueError("Acoustic archive bytes changed after source admission")
        if _hash(self.metadata_path) != (_METADATA_SHA256, _METADATA_SIZE):
            raise ValueError("Zenodo metadata bytes changed after source admission")
        return self

    def file(self, member_path: str) -> HydrogenAcousticFile:
        self.require_current()
        matches = tuple(item for item in self.files if item.member_path == member_path)
        if len(matches) != 1:
            raise ValueError("Select one exact acquired acoustic PIF member")
        return matches[0]


def load_hydrogen_acoustic_dataset(archive_path: str | Path,
                                  metadata_path: str | Path) -> HydrogenAcousticDataset:
    """Read the original numeric PIF subset without executing the bundled reader.

    Only the 30 `.txt` measurement files inside the pinned archive are parsed.
    The separately listed `pif_reader.py` is not acquired or executed here.
    """
    archive_path, metadata_path = Path(archive_path), Path(metadata_path)
    archive_path, metadata_path = archive_path.resolve(), metadata_path.resolve()
    archive_hash, archive_size = _hash(archive_path)
    metadata_hash, metadata_size = _hash(metadata_path)
    if (archive_hash != _ARCHIVE_SHA256 or archive_size != _ARCHIVE_SIZE
            or metadata_hash != _METADATA_SHA256 or metadata_size != _METADATA_SIZE):
        raise ValueError("Acoustic archive or Zenodo metadata differs from the pinned source receipt")
    metadata_bytes = metadata_path.read_bytes()
    try:
        response = json.loads(metadata_bytes)
        record = response["metadata"]
        file_records = response["files"]
        license_record = record["license"]
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Pinned acoustic Zenodo response lacks required identity and license fields") from exc
    if (response.get("doi") != _DOI or record.get("doi") != _DOI
            or license_record.get("id") != "cc-by-4.0"
            or record.get("access_right") != "open"):
        raise ValueError("Acoustic dataset DOI, open-access statement or CC BY 4.0 license changed")
    remote = next((item for item in file_records
                   if item.get("key") == "H2_speedofsound_dataset.zip"), None)
    if (remote is None or remote.get("size") != _ARCHIVE_SIZE
            or remote.get("checksum") != f"md5:{_ARCHIVE_MD5}"):
        raise ValueError("Zenodo archive listing differs from the pinned measurement attachment")
    authors = tuple(item["name"] for item in record.get("creators", []))
    files = []
    with ZipFile(archive_path) as archive:
        members = tuple(sorted(name for name in archive.namelist()
                               if name.endswith(".txt") and "summary" not in name.casefold()))
        if len(members) != 30:
            raise ValueError("Acoustic source archive must contain the 30 reviewed measurement PIF files")
        for member in members:
            path = PurePosixPath(member)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Acoustic archive contains an unsafe member path")
            payload = archive.read(member)
            member_hash = hashlib.sha256(payload).hexdigest()
            import io
            import zipfile
            try:
                parsed = read_property_file(io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8-sig"))
                rows = tuple(f"{_DOI}:{member}:loop-{loop_index}:row-{row_index}"
                    for loop_index, loop in enumerate(parsed.loops, start=1)
                    for row_index in range(1, len(loop.values) + 1))
                for loop in parsed.loops:
                    acoustic_columns(parsed, loop)
            except (UnicodeDecodeError, ValueError, TypeError) as exc:
                raise ValueError(f"Acoustic PIF member {member!r} is outside the reviewed numeric subset") from exc
            files.append(HydrogenAcousticFile(member, member_hash, parsed, rows))
    return _issue(doi=_DOI, license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/", authors=authors,
        archive_path=archive_path, metadata_path=metadata_path,
        archive_sha256=archive_hash, metadata_sha256=metadata_hash, files=tuple(files))
