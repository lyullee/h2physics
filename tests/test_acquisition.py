import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from h2physics.data.acquire import (
    _local_name,
    acquire_dataset,
    audit_cached_dataset,
    replay_receipt,
)
from h2physics.data.models import Dataset, RemoteFile, _mark_repository_resolved
from h2physics.data.reporting import write_receipt


def dataset(files=(), license_id="CC-BY-4.0", version="1"):
    return Dataset("test-source", "Original test collection", "", version, ("Test author",),
                   license_id, "https://creativecommons.org/licenses/by/4.0/",
                   "https://example.org/metadata", hashlib.sha256(b"{}").hexdigest(),
                   "synthetic", ("test",), tuple(files), b"{}")


def test_unclear_rights_prevent_network_and_filesystem_acquisition(tmp_path):
    with patch("urllib.request.urlopen", side_effect=AssertionError("Network must remain unused")):
        report = acquire_dataset(dataset(license_id="UNRESOLVED"), tmp_path / "absent")
    assert not report.rights_permitted
    assert not (tmp_path / "absent").exists()


def test_cached_attachment_must_match_publisher_hash(tmp_path):
    folder = tmp_path / "test-source/1"
    folder.mkdir(parents=True)
    (folder / "data.csv").write_bytes(b"bad")
    file = RemoteFile("data.csv", "https://example.org/data.csv", 3, "sha256", "0" * 64)
    report = acquire_dataset(dataset([file]), tmp_path)
    assert report.files[0].status == "failed"
    assert "checksum" in report.files[0].error
    assert (folder / "data.csv").read_bytes() == b"bad"


def test_selection_budget_and_safe_version(tmp_path):
    file = RemoteFile("large.csv", "https://example.org/large.csv", 100)
    report = acquire_dataset(dataset([file]), tmp_path, maximum_total_bytes=50)
    assert report.omitted_files == ("large.csv",)
    with pytest.raises(ValueError, match="version"):
        acquire_dataset(dataset(version="../outside"), tmp_path)
    assert _local_name("folder/sub/data.csv") == "data.csv"
    with pytest.raises(ValueError):
        _local_name("unsafe:name.csv")


def test_valid_cached_receipt_roundtrips_attribution_and_hash(tmp_path):
    import tomllib

    payload = b"x,y\n1,2\n"
    folder = tmp_path / "test-source/1"
    folder.mkdir(parents=True)
    (folder / "data.csv").write_bytes(payload)
    file = RemoteFile("data.csv", "https://example.org/data.csv", len(payload),
                      "sha256", hashlib.sha256(payload).hexdigest())
    report = acquire_dataset(dataset([file]), tmp_path)
    target = tmp_path / "receipt.toml"
    write_receipt(report, target)
    record = tomllib.loads(target.read_text(encoding="utf-8"))
    assert record["authors"] == ["Test author"]
    assert record["files"][0]["publisher_checksum_verified"]
    assert not record["validation_qualified"]
    assert Path(record["files"][0]["relative_path"]).parts == ("test-source", "1", "data.csv")


def test_read_only_cache_audit_does_not_count_partial_or_missing_files(tmp_path):
    folder = tmp_path / "test-source/Version v1"
    folder.mkdir(parents=True)
    (folder / "data.csv.part-authored").write_bytes(b"unfinished")
    files = [RemoteFile("data.csv", "https://example.org/data.csv", 10)]
    with patch("urllib.request.urlopen", side_effect=AssertionError("No download during cache audit")):
        result = audit_cached_dataset(dataset(files, version="Version v1"), tmp_path)
    assert result.acquired_bytes == 0
    assert result.files[0].status == "not_acquired"
    assert not (folder / "repository-metadata.json").exists()


def test_replay_pins_local_hash_even_when_publisher_has_no_checksum(tmp_path):
    folder = tmp_path / "test-source/1"
    folder.mkdir(parents=True)
    payload = b"x,y\n1,2\n"
    (folder / "data.csv").write_bytes(payload)
    remote = RemoteFile("data.csv", "https://example.org/data.csv", len(payload))
    source = _mark_repository_resolved(dataset([remote]))
    target = tmp_path / "receipt.toml"
    write_receipt(acquire_dataset(source, tmp_path), target)
    assert replay_receipt(target, tmp_path, dataset=source)[0].status == "cached"
    (folder / "data.csv").write_bytes(b"x,y\n8,9\n")
    with pytest.raises(ValueError, match="recorded SHA-256"):
        replay_receipt(target, tmp_path, dataset=source)


def test_http429_defers_remaining_network_but_still_audits_cached_files(tmp_path):
    import urllib.error

    folder = tmp_path / "test-source/1"
    folder.mkdir(parents=True)
    (folder / "cached.csv").write_bytes(b"data")
    files = [RemoteFile("a.csv", "https://example.org/a", 2),
             RemoteFile("b.csv", "https://example.org/b", 3),
             RemoteFile("cached.csv", "https://example.org/c", 4)]
    throttle = urllib.error.HTTPError(files[0].url, 429, "Too Many Requests", {"Retry-After": "120"}, None)
    with patch("urllib.request.urlopen", side_effect=throttle) as reader:
        report = acquire_dataset(dataset(files), tmp_path)
    assert reader.call_count == 1
    assert [entry.status for entry in report.files] == ["deferred", "deferred", "cached"]
    assert "120" in report.files[0].error
    assert report.acquired_bytes == 4
    assert not list(folder.glob("*.part-*"))
