"""Data identity and rights are separate from experimental applicability."""

import hashlib
from dataclasses import dataclass, field
from urllib.parse import urlparse

ACQUISITION_LICENSES = frozenset({"CC0-1.0", "CC-BY-4.0", "etalab-2.0"})
LICENSE_URL_IDENTITIES = {
    "CC0-1.0": frozenset({
        ("creativecommons.org", "/publicdomain/zero/1.0"),
        ("spdx.org", "/licenses/cc0-1.0.html"),
    }),
    "CC-BY-4.0": frozenset({
        ("creativecommons.org", "/licenses/by/4.0"),
        ("creativecommons.org", "/licenses/by/4.0/legalcode"),
        ("spdx.org", "/licenses/cc-by-4.0.html"),
    }),
    "CC-BY-SA-4.0": frozenset({
        ("creativecommons.org", "/licenses/by-sa/4.0"),
        ("creativecommons.org", "/licenses/by-sa/4.0/legalcode"),
        ("spdx.org", "/licenses/cc-by-sa-4.0.html"),
    }),
    "etalab-2.0": frozenset({
        ("spdx.org", "/licenses/etalab-2.0.html"),
    }),
}
_REPOSITORY_DATASET_ISSUER = object()


def license_url_matches(license_id: str, license_url: str, *, require_https: bool = True) -> bool:
    """Check that an informational license URL identifies the declared license.

    This consistency check is not a grantor decision or legal clearance. HTTP is
    allowed only for replaying historical receipts and is never used as a fetch URL.
    """
    if not isinstance(license_id, str) or not isinstance(license_url, str):
        return False
    parsed = urlparse(license_url)
    try:
        port = parsed.port
    except ValueError:
        return False
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    if (parsed.scheme not in allowed_schemes or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or port is not None or parsed.query or parsed.fragment):
        return False
    identity = (parsed.hostname.lower(), parsed.path.rstrip("/").lower())
    return identity in LICENSE_URL_IDENTITIES.get(license_id, ())


@dataclass(frozen=True, slots=True)
class RemoteFile:
    name: str
    url: str
    size_bytes: int
    checksum_algorithm: str = ""
    checksum: str = ""

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("A remote file needs an explicit name")
        basename = self.name.replace("\\", "/").rsplit("/", 1)[-1]
        if (basename in {"", ".", ".."}
                or any(character in basename for character in ':<>"|?*')):
            raise ValueError("Remote attachment name has no safe local basename")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
            raise TypeError("A remote file size must be an integer byte count")
        if self.size_bytes < 0:
            raise ValueError("A remote file size cannot be negative")
        parsed = urlparse(self.url) if isinstance(self.url, str) else None
        if (parsed is None or parsed.scheme != "https" or not parsed.hostname
                or parsed.username is not None or parsed.password is not None):
            raise ValueError("Only HTTPS data resources are accepted")
        if not isinstance(self.checksum_algorithm, str) or self.checksum_algorithm.lower() not in {"", "md5", "sha256"}:
            raise ValueError("Unsupported publisher checksum algorithm")
        algorithm = self.checksum_algorithm.lower()
        object.__setattr__(self, "checksum_algorithm", algorithm)
        if not isinstance(self.checksum, str):
            raise TypeError("Publisher checksum must be text")
        checksum = self.checksum.lower()
        object.__setattr__(self, "checksum", checksum)
        length = {"md5": 32, "sha256": 64}.get(algorithm)
        if (algorithm and not checksum) or (not algorithm and checksum) or (length and (
                       len(checksum) != length or any(c not in "0123456789abcdef" for c in checksum))):
            raise ValueError("Malformed publisher checksum")


@dataclass(frozen=True, slots=True)
class Dataset:
    key: str
    title: str
    doi: str
    version: str
    authors: tuple[str, ...]
    license_id: str
    license_url: str
    metadata_url: str
    metadata_sha256: str
    origin: str
    families: tuple[str, ...]
    files: tuple[RemoteFile, ...]
    metadata_bytes: bytes
    supporting_metadata: tuple[tuple[str, bytes], ...] = ()
    source_updated_at: str = ""
    _repository_issuer: object = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self):
        for name in ("key", "title", "version", "license_id", "metadata_url", "origin"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Dataset {name} must be an explicit nonempty string")
        if (any(value not in "abcdefghijklmnopqrstuvwxyz0123456789-" for value in self.key)
                or self.version in {".", ".."} or self.version != self.version.strip()
                or self.version.endswith(".")
                or any(value not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- "
                       for value in self.version)):
            raise ValueError("Dataset key/version is not safe for an external cache path")
        if not isinstance(self.doi, str) or not isinstance(self.license_url, str):
            raise TypeError("Dataset DOI and license reference must be text, including unresolved values")
        if not isinstance(self.source_updated_at, str):
            raise TypeError("Dataset source update timestamp must remain text")
        metadata_url = urlparse(self.metadata_url)
        if (metadata_url.scheme != "https" or not metadata_url.hostname
                or metadata_url.username is not None or metadata_url.password is not None):
            raise ValueError("Dataset metadata must have an HTTPS source URL")
        license_url = urlparse(self.license_url) if self.license_url else None
        if (self.license_id in ACQUISITION_LICENSES and (license_url is None
                or license_url.scheme != "https" or not license_url.hostname
                or license_url.username is not None or license_url.password is not None)):
            raise ValueError("Dataset rights must link to an HTTPS license record")
        if (self.license_id in LICENSE_URL_IDENTITIES
                and not license_url_matches(self.license_id, self.license_url)):
            raise ValueError("Dataset license URL does not identify its declared license")
        if (not isinstance(self.metadata_sha256, str) or len(self.metadata_sha256) != 64
                or any(value not in "0123456789abcdef" for value in self.metadata_sha256)):
            raise ValueError("Dataset metadata identity must be a lowercase SHA-256")
        if (not isinstance(self.metadata_bytes, bytes)
                or hashlib.sha256(self.metadata_bytes).hexdigest() != self.metadata_sha256):
            raise ValueError("Dataset metadata bytes must match their retained SHA-256")
        sequences = (self.authors, self.families, self.files, self.supporting_metadata)
        if any(isinstance(value, (str, bytes)) or not isinstance(value, (tuple, list))
               for value in sequences):
            raise TypeError("Dataset authors, tags, files and metadata must be explicit sequences")
        authors, families, files = tuple(self.authors), tuple(self.families), tuple(self.files)
        if (any(not isinstance(value, str) or not value.strip() for value in authors)
                or not families or any(not isinstance(value, str) or not value.strip() for value in families)):
            raise ValueError("Dataset authors and physical-family tags must be explicit")
        if any(not isinstance(value, RemoteFile) for value in files):
            raise TypeError("Dataset files must be validated RemoteFile objects")
        normalized = [value.name.replace("\\", "/").rsplit("/", 1)[-1].casefold() for value in files]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Dataset attachments collide after local filename normalization")
        supporting = tuple(self.supporting_metadata)
        if any(not isinstance(item, (tuple, list)) or len(item) != 2
               or not isinstance(item[0], str) or not item[0].strip()
               or not isinstance(item[1], bytes) for item in supporting):
            raise ValueError("Supporting repository metadata must retain source URL and original bytes")
        for source_url, _ in supporting:
            parsed = urlparse(source_url)
            if (parsed.scheme != "https" or not parsed.hostname
                    or parsed.username is not None or parsed.password is not None):
                raise ValueError("Supporting repository metadata must retain an HTTPS source URL")
        for name, value in (("authors", authors), ("families", families),
                            ("files", files), ("supporting_metadata", tuple(tuple(item) for item in supporting))):
            object.__setattr__(self, name, value)

    @property
    def acquisition_permitted(self) -> bool:
        """The initial policy admits explicit attribution or public-domain terms."""
        return self.license_id in ACQUISITION_LICENSES

    @property
    def validation_qualified(self) -> bool:
        # Rights and the presence of observations cannot establish model suitability.
        return False


def _mark_repository_resolved(dataset: Dataset) -> Dataset:
    """Attach an internal issuer marker to a dataset parsed from a repository response."""
    if type(dataset) is not Dataset:
        raise TypeError("Only a validated Dataset can receive the repository issuer")
    object.__setattr__(dataset, "_repository_issuer", _REPOSITORY_DATASET_ISSUER)
    return dataset


def _was_repository_resolved(dataset: Dataset) -> bool:
    return (type(dataset) is Dataset
            and dataset._repository_issuer is _REPOSITORY_DATASET_ISSUER)
