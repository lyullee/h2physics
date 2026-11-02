"""Bounded, checksum-verified acquisition; external files are never executed."""

import hashlib
import os
import time
import tomllib
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..core import finite
from .models import Dataset, RemoteFile, _was_repository_resolved
from .repositories import USER_AGENT, open_credential_free_https


@dataclass(frozen=True, slots=True)
class FileReceipt:
    name: str
    relative_path: str
    size_bytes: int
    sha256: str
    publisher_checksum_verified: bool
    status: str
    error: str = ""


@dataclass(frozen=True, slots=True)
class AcquisitionReport:
    dataset: Dataset
    files: tuple[FileReceipt, ...]
    omitted_files: tuple[str, ...]
    rights_permitted: bool

    @property
    def acquired_bytes(self) -> int:
        return sum(x.size_bytes for x in self.files if x.status in {"acquired", "cached"})


@dataclass(frozen=True, slots=True)
class ReplayBudget:
    """Explicit byte limits for replaying completed files from a public receipt."""

    maximum_total_bytes: int = 500_000_000
    maximum_file_bytes: int = 250_000_000

    def __post_init__(self):
        for name in ("maximum_total_bytes", "maximum_file_bytes"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer byte limit")


class RepositoryRateLimit(RuntimeError):
    """A public server requested throttling; no immediate automatic retry is made."""


def _verify_replay_receipt(record: dict, dataset: Dataset) -> list[dict]:
    """Bind editable receipt claims to an independently resolved publisher record."""
    if (type(dataset) is not Dataset or not _was_repository_resolved(dataset)
            or not dataset.acquisition_permitted):
        raise ValueError("Receipt replay requires a repository-resolved Dataset with permitted rights")
    identity = {
        "key": dataset.key,
        "title": dataset.title,
        "doi": dataset.doi,
        "version": dataset.version,
        "origin": dataset.origin,
        "source_updated_at": dataset.source_updated_at,
        "license_id": dataset.license_id,
        "license_url": dataset.license_url,
        "metadata_url": dataset.metadata_url,
        "metadata_sha256": dataset.metadata_sha256,
    }
    if any(record.get(key, "") != value for key, value in identity.items()):
        raise ValueError("Replay receipt dataset identity differs from the resolved publisher record")
    if (record.get("rights_permitted") is not True
            or tuple(record.get("authors", ())) != dataset.authors
            or tuple(record.get("families", ())) != dataset.families
            or record.get("validation_qualified") is not False
            or isinstance(record.get("listed_file_count"), bool)
            or not isinstance(record.get("listed_file_count"), int)
            or record.get("listed_file_count") != len(dataset.files)):
        raise ValueError("Replay receipt rights, attribution, or attachment count differs from its Dataset")

    recorded_support = record.get("supporting_metadata", [])
    if not isinstance(recorded_support, list) or len(recorded_support) != len(dataset.supporting_metadata):
        raise ValueError("Replay receipt omits publisher supporting-metadata provenance")
    for item, (url, payload) in zip(recorded_support, dataset.supporting_metadata, strict=True):
        if (not isinstance(item, dict) or item.get("url") != url
                or item.get("sha256") != hashlib.sha256(payload).hexdigest()):
            raise ValueError("Replay receipt supporting metadata differs from the resolved publisher response")

    entries = record.get("files", [])
    omitted = record.get("omitted_files", [])
    if not isinstance(entries, list) or not isinstance(omitted, list):
        raise ValueError("Replay receipt must contain file entries and an omitted-file list")
    remotes = {item.name: item for item in dataset.files}
    if len(remotes) != len(dataset.files):
        raise ValueError("Resolved Dataset attachment names are not unique")
    seen: set[str] = set()
    completed_bytes = 0
    allowed_statuses = {"acquired", "cached", "failed", "deferred"}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Replay receipt file entries must be tables")
        name = entry.get("name")
        remote = remotes.get(name) if isinstance(name, str) else None
        if remote is None or name in seen:
            raise ValueError("Replay receipt contains an unlisted or duplicate attachment")
        seen.add(name)
        if (entry.get("url") != remote.url
                or entry.get("publisher_checksum_algorithm") != remote.checksum_algorithm
                or entry.get("publisher_checksum") != remote.checksum):
            raise ValueError("Replay receipt attachment URL/checksum differs from the publisher listing")
        status = entry.get("status")
        if status not in allowed_statuses:
            raise ValueError("Replay receipt contains an unsupported acquisition status")
        size_bytes = entry.get("size_bytes")
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int):
            raise ValueError("Replay receipt file sizes must be integer byte counts")
        if status in {"acquired", "cached"}:
            digest = entry.get("sha256")
            if (size_bytes != remote.size_bytes
                    or not isinstance(digest, str) or len(digest) != 64
                    or any(character not in "0123456789abcdef" for character in digest)
                    or entry.get("publisher_checksum_verified") is not bool(remote.checksum)
                    or entry.get("relative_path") != PurePosixPath(
                        dataset.key, dataset.version, _local_name(remote.name)
                    ).as_posix()):
                raise ValueError("Completed receipt file differs from its publisher size or local identity")
            completed_bytes += remote.size_bytes
        elif (size_bytes != 0 or entry.get("sha256") != ""
              or entry.get("publisher_checksum_verified") is not False
              or entry.get("relative_path") != ""):
            raise ValueError("Incomplete receipt entries must not claim acquired bytes")
        if not isinstance(entry.get("error", ""), str):
            raise ValueError("Replay receipt error field must remain text")

    if (any(not isinstance(name, str) or name not in remotes or name in seen for name in omitted)
            or len(omitted) != len(set(omitted))):
        raise ValueError("Replay receipt omitted-file names do not match the publisher listing")
    seen.update(omitted)
    if seen != set(remotes):
        raise ValueError("Replay receipt must account for every publisher-listed attachment exactly once")
    acquired_bytes = record.get("acquired_bytes")
    if (isinstance(acquired_bytes, bool) or not isinstance(acquired_bytes, int)
            or acquired_bytes != completed_bytes):
        raise ValueError("Replay receipt acquired-byte total differs from its completed file entries")
    return entries


def _hash_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm, usedforsecurity=False)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _local_name(name: str) -> str:
    result = PurePosixPath(name.replace("\\", "/")).name
    if result in {"", ".", ".."} or any(c in result for c in ':<>"|?*'):
        raise ValueError("Remote attachment has an unsafe local filename")
    return result


def _is_linklike(path: Path) -> bool:
    """Detect file links before cache readers hash or accept their targets."""
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or (callable(is_junction) and is_junction())


def _cache_directory(key: str, version: str, root: Path) -> Path:
    if not key or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in key):
        raise ValueError("Dataset key must be a safe lowercase identifier")
    if (version in {"", ".", ".."} or version != version.strip() or version.endswith(".")
            or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- " for c in version)):
        raise ValueError("Invalid dataset version")
    key_directory = root / key
    version_directory = key_directory / version
    if _is_linklike(key_directory) or _is_linklike(version_directory):
        raise ValueError("Dataset cache identity path must not contain a symbolic link or junction")
    directory = version_directory.resolve()
    if not directory.is_relative_to(root.resolve()):
        raise ValueError("Dataset directory escapes the cache root")
    return directory


def _download(remote: RemoteFile, directory: Path, root: Path, *, expected_sha256: str = "") -> FileReceipt:
    name = _local_name(remote.name)
    destination = directory / name
    if _is_linklike(destination):
        raise ValueError(f"Cached attachment path must not be a symbolic link or junction: {name}")
    if destination.exists():
        if destination.stat().st_size != remote.size_bytes:
            raise ValueError(f"Existing attachment has a different size: {name}")
        if remote.checksum and _hash_file(destination, remote.checksum_algorithm) != remote.checksum:
            raise ValueError(f"Existing attachment fails publisher checksum: {name}")
        digest = _hash_file(destination, "sha256")
        if expected_sha256 and digest != expected_sha256:
            raise ValueError("Existing attachment fails the recorded SHA-256")
        return FileReceipt(remote.name, destination.relative_to(root).as_posix(),
                           remote.size_bytes, digest,
                           bool(remote.checksum), "cached")
    temporary = destination.with_name(name + ".part-" + uuid.uuid4().hex)
    try:
        request = urllib.request.Request(remote.url, headers={"User-Agent": USER_AGENT})
        try:
            response = open_credential_free_https(request, timeout=45)
        except urllib.error.HTTPError as error:
            if error.code == 429:
                retry = error.headers.get("Retry-After", "unspecified; wait before explicit retry")
                raise RepositoryRateLimit(f"HTTP 429; Retry-After={retry}") from error
            raise
        with response, temporary.open("xb") as target:
            if not response.url.startswith("https://"):
                raise ValueError("Attachment redirected outside HTTPS")
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > remote.size_bytes:
                    raise ValueError("Attachment exceeds its published size")
                target.write(chunk)
        if total != remote.size_bytes:
            raise ValueError(f"Attachment size mismatch: expected {remote.size_bytes}, got {total}")
        if remote.checksum and _hash_file(temporary, remote.checksum_algorithm) != remote.checksum:
            raise ValueError("Downloaded attachment fails publisher checksum")
        digest = _hash_file(temporary, "sha256")
        if expected_sha256 and digest != expected_sha256:
            raise ValueError("Downloaded attachment fails the recorded SHA-256")
        os.replace(temporary, destination)
        return FileReceipt(remote.name, destination.relative_to(root).as_posix(),
                           total, digest, bool(remote.checksum), "acquired")
    finally:
        if temporary.exists():
            temporary.unlink()


def audit_cached_dataset(dataset: Dataset, root: Path) -> AcquisitionReport:
    """Read-only verification of complete cached files while a long acquisition runs.

    Temporary downloads are never inspected or counted. Missing and corrupt files
    remain explicit. This function does not fetch attachments or change raw files.
    Publisher checksums remain necessary when the repository supplies them.
    """
    root = Path(root).resolve()
    if not dataset.acquisition_permitted:
        return AcquisitionReport(dataset, (), tuple(f.name for f in dataset.files), False)
    directory = _cache_directory(dataset.key, dataset.version, root)
    receipts = []
    names = set()
    for remote in dataset.files:
        name = _local_name(remote.name)
        if name.casefold() in names:
            raise ValueError("Attachments collide after local path normalization")
        names.add(name.casefold())
        path = directory / name
        if _is_linklike(path):
            receipts.append(FileReceipt(remote.name, "", 0, "", False, "failed",
                                        "Cached attachment path is a symbolic link or junction"))
            continue
        if not path.is_file():
            receipts.append(FileReceipt(remote.name, "", 0, "", False, "not_acquired"))
            continue
        try:
            if path.stat().st_size != remote.size_bytes:
                raise ValueError("Cached file size differs from the publisher record")
            if remote.checksum and _hash_file(path, remote.checksum_algorithm) != remote.checksum:
                raise ValueError("Cached file fails the publisher checksum")
            receipts.append(FileReceipt(remote.name, path.relative_to(root).as_posix(),
                                        remote.size_bytes, _hash_file(path, "sha256"),
                                        bool(remote.checksum), "cached"))
        except (ValueError, OSError) as error:
            receipts.append(FileReceipt(remote.name, "", 0, "", False, "failed", str(error)))
    return AcquisitionReport(dataset, tuple(receipts), (), True)


def replay_receipt(receipt_path: Path, root: Path, *, dataset: Dataset,
                   budget: ReplayBudget = ReplayBudget()) -> tuple[FileReceipt, ...]:
    """Reacquire completed files from a receipt bound to a resolved publisher Dataset.

    The public receipt is the explicit replay input. It does not replace or
    rewrite publisher metadata, expand to a newer version, or hide changed bytes.
    The caller supplies a freshly resolved Dataset; editable receipt claims about
    rights and attachment URLs are compared to that publisher record before the
    cache directory is created. Failed/omitted/unavailable attachments require a
    new discovery acquisition.
    """
    if not isinstance(budget, ReplayBudget):
        raise TypeError("Receipt replay needs an explicit ReplayBudget contract")
    record = tomllib.loads(Path(receipt_path).read_text(encoding="utf-8"))
    entries = _verify_replay_receipt(record, dataset)
    root = Path(root).resolve()
    directory = _cache_directory(record["key"], record["version"], root)
    selected = [f for f in entries if isinstance(f, dict)
                and f.get("status") in {"acquired", "cached"}]
    if sum(isinstance(f, dict) and f.get("status") in {"acquired", "cached"}
           for f in entries) != len(selected):
        raise ValueError("Completed replay entries must be mappings")
    names = set()
    total_bytes = 0
    for file in selected:
        name = _local_name(file["name"])
        if name.casefold() in names:
            raise ValueError("Receipt attachment names collide")
        names.add(name.casefold())
        size = file.get("size_bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("Replay attachment size must be a nonnegative integer")
        if size > budget.maximum_file_bytes:
            raise ValueError("Replay attachment exceeds its per-file byte budget")
        total_bytes += size
        if total_bytes > budget.maximum_total_bytes:
            raise ValueError("Replay attachments exceed their aggregate byte budget")
        digest = file["sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Replay needs a recorded SHA-256 for every completed file")
        RemoteFile(file["name"], file["url"], size,
                   file["publisher_checksum_algorithm"], file["publisher_checksum"])
    directory.mkdir(parents=True, exist_ok=True)
    receipts = []
    for file in selected:
        remote = RemoteFile(file["name"], file["url"], file["size_bytes"],
                            file["publisher_checksum_algorithm"], file["publisher_checksum"])
        receipts.append(_download(remote, directory, root, expected_sha256=file["sha256"]))
    return tuple(receipts)


def acquire_dataset(
    dataset: Dataset, root: Path, *, maximum_total_bytes: int = 500_000_000,
    maximum_file_bytes: int = 250_000_000,
    suffixes: tuple[str, ...] = (".csv", ".tsv", ".txt", ".md", ".xlsx", ".mat", ".h5", ".zip", ".docx"),
    minimum_download_interval_s: float = 0.,
) -> AcquisitionReport:
    """Acquire selected files after license review, retaining omissions and failures.

    Selection is deterministic and favors small metadata/data attachments. Budgets apply
    to published sizes; receipt counts must not be represented as complete datasets when
    files are omitted. Archive contents are inspected separately without execution.
    """
    root = Path(root).resolve()
    if maximum_total_bytes <= 0 or maximum_file_bytes <= 0:
        raise ValueError("Acquisition limits must be positive")
    interval = finite(minimum_download_interval_s, "minimum_download_interval_s")
    if interval < 0:
        raise ValueError("Download interval cannot be negative")
    if not dataset.acquisition_permitted:
        return AcquisitionReport(dataset, (), tuple(x.name for x in dataset.files), False)
    directory = _cache_directory(dataset.key, dataset.version, root)
    directory.mkdir(parents=True, exist_ok=True)
    # Preserve each exact metadata snapshot rather than overwriting older evidence.
    (directory / f"repository-metadata-{dataset.metadata_sha256}.json").write_bytes(dataset.metadata_bytes)
    for index, (_, payload) in enumerate(dataset.supporting_metadata):
        digest = hashlib.sha256(payload).hexdigest()
        (directory / f"repository-file-list-{index}-{digest}.json").write_bytes(payload)
    receipts, omitted, selected_size, names = [], [], 0, set()
    rate_limit = ""
    next_network_time = 0.
    for remote in sorted(dataset.files, key=lambda f: (f.size_bytes, f.name)):
        name = _local_name(remote.name)
        if (Path(name).suffix.lower() not in suffixes or remote.size_bytes > maximum_file_bytes
                or selected_size + remote.size_bytes > maximum_total_bytes):
            omitted.append(remote.name)
            continue
        if name.casefold() in names:
            raise ValueError("Attachments collide after local path normalization")
        names.add(name.casefold())
        selected_size += remote.size_bytes
        if rate_limit and not (directory / name).exists():
            receipts.append(FileReceipt(remote.name, "", 0, "", False, "deferred", rate_limit))
            continue
        error = None
        for attempt in range(3):
            try:
                if interval and not (directory / name).exists():
                    while (delay := next_network_time - time.monotonic()) > 0:
                        time.sleep(min(delay, 30.))
                    next_network_time = time.monotonic() + interval
                receipt = _download(remote, directory, root)
                receipts.append(receipt)
                error = None
                break
            except RepositoryRateLimit as exception:
                rate_limit = str(exception)
                receipts.append(FileReceipt(remote.name, "", 0, "", False, "deferred", rate_limit))
                break
            except (OSError, TimeoutError, ValueError) as exception:
                error = str(exception)
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
        if error is not None:
            receipts.append(FileReceipt(remote.name, "", 0, "", False, "failed", error))
    return AcquisitionReport(dataset, tuple(receipts), tuple(omitted), True)
