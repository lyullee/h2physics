import json
from unittest.mock import patch

from h2physics.data.catalog import DatasetSeed
from h2physics.data.repositories import resolve_dataset


def test_dryad_uses_declared_sha256_instead_of_guessing_md5():
    metadata = {
        "_links": {"stash:version": {"href": "/api/v2/versions/1"}},
        "title": "Original synthetic metadata fixture", "versionNumber": 1,
        "authors": [{"firstName": "A", "lastName": "Researcher"}],
        "license": "https://spdx.org/licenses/CC0-1.0.html",
    }
    files = {"_embedded": {"stash:files": [{
        "path": "data.csv", "size": 5, "digestType": "sha-256", "digest": "a" * 64,
        "_links": {"stash:download": {"href": "/api/v2/files/1/download"}},
    }]}}
    with patch("h2physics.data.repositories.read_url", side_effect=[
        json.dumps(metadata).encode(), json.dumps(files).encode(),
    ]):
        result = resolve_dataset(DatasetSeed("dryad-test", "dryad", "10.0/test", ("test",)))
    assert result.files[0].checksum_algorithm == "sha256"
    assert result.license_id == "CC0-1.0"
    assert len(result.supporting_metadata) == 1


def test_dataverse_preserves_original_upload_name_size_and_updated_at():
    metadata = {"data": {"latestVersion": {
        "versionNumber": 1, "versionMinorNumber": 1, "lastUpdateTime": "2026-01-02T03:04:05Z",
        "license": {"name": "etalab 2.0", "uri": "https://spdx.org/licenses/etalab-2.0.html"},
        "metadataBlocks": {"citation": {"fields": [{"typeName": "title", "value": "Authored fixture"}]}},
        "files": [{"dataFile": {"id": 1, "filename": "archival.tab", "filesize": 5,
                                   "originalFileName": "source.csv", "originalFileSize": 9,
                                   "checksum": {"type": "MD5", "value": "a"*32}}}],
    }}}
    with patch("h2physics.data.repositories.read_url", return_value=json.dumps(metadata).encode()):
        result = resolve_dataset(DatasetSeed("fr-test", "dataverse-fr", "10.0/test", ("test",)))
    assert result.acquisition_permitted
    assert result.files[0].name == "source.csv" and result.files[0].size_bytes == 9
    assert result.files[0].url.endswith("?format=original")
    assert result.source_updated_at == "2026-01-02T03:04:05Z"
