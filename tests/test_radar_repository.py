"""Authored metadata fixtures; no downloaded repository payloads are redistributed."""

import json
from copy import deepcopy
from unittest.mock import patch

import pytest

from h2physics.data.catalog import DatasetSeed
from h2physics.data.repositories import resolve_dataset

SEED = DatasetSeed("radar-fixture", "radar-kit", "10.35097/fixture", ("release",))


def fixture():
    metadata = {"data": {"attributes": {
        "doi": SEED.identifier, "url": "https://radar.kit.edu/radar/en/dataset/fixture",
        "titles": [{"title": "Authored data fixture"}], "creators": [{"name": "A. Author"}],
        "updated": "2026-01-01T00:00:00Z", "rightsList": [{
            "rightsIdentifier": "cc-by-4.0", "rightsUri": "https://creativecommons.org/licenses/by/4.0/legalcode",
        }],
    }}}
    graph = {"@graph": [{"type": "DataDownload", "schema:contentUrl":
                        "https://www.radar-service.eu/radar-backend/archives/fixture/versions/2/content"}]}
    page = '<script type="application/ld+json">' + json.dumps(graph) + '</script>'
    children = [{"id": name, "parentId": "fixture", "binaryUrl": "http://internal.invalid/unused",
                 "binary": {"name": name + ".zip", "size": 123,
                            "checksum": "a"*32, "checksumType": "MD5"}} for name in ("one", "two")]
    rows = [{"id": item["id"], "titleName": item["binary"]["name"],
             "contentType": "file", "children": children} for item in children]
    listing = {"recordsTotal": 2, "recordsFiltered": 2, "data": rows}
    links = [{"downloadUrl": "https://radar.kit.edu/radar-backend/archives/fixture/retrieveFile/" + name}
             for name in ("one", "two")]
    return metadata, page.encode(), listing, links


def responses(metadata, page, listing, links):
    return [json.dumps(metadata).encode(), page, json.dumps(listing).encode(),
            *(json.dumps(link).encode() for link in links)]


def test_radar_joins_file_identity_preserves_rights_and_uses_public_download_endpoint():
    with patch("h2physics.data.repositories.read_url", side_effect=responses(*fixture())) as reader:
        result = resolve_dataset(SEED)
    assert result.version == "archive-2" and result.acquisition_permitted
    assert result.source_updated_at == "2026-01-01T00:00:00Z"
    assert result.license_url.endswith("/legalcode")
    assert result.authors == ("A. Author",)
    assert [item.name for item in result.files] == ["one.zip", "two.zip"]
    assert all(item.checksum_algorithm == "md5" for item in result.files)
    assert len(result.supporting_metadata) == 4
    assert not any("internal.invalid" in call.args[0] for call in reader.call_args_list)
    assert "order%5B0%5D%5Bcolumn%5D=0" in reader.call_args_list[2].args[0]


@pytest.mark.parametrize("problem", ["foreign_host", "wrong_doi", "ambiguous_license",
                                     "wrong_parent", "foreign_download", "incomplete_listing"])
def test_radar_rejects_ambiguous_or_inconsistent_public_metadata(problem):
    metadata, page, listing, links = deepcopy(fixture())
    if problem == "foreign_host":
        metadata["data"]["attributes"]["url"] = "https://other.invalid/radar/en/dataset/fixture"
    elif problem == "wrong_doi":
        metadata["data"]["attributes"]["doi"] = "10.35097/other"
    elif problem == "ambiguous_license":
        metadata["data"]["attributes"]["rightsList"].append({"rightsIdentifier": "cc-by-sa-4.0"})
    elif problem == "wrong_parent":
        listing["data"][0]["children"][0]["parentId"] = "other"
    elif problem == "foreign_download":
        links[0]["downloadUrl"] = "https://other.invalid/file"
    else:
        listing["recordsTotal"] = 1
    with patch("h2physics.data.repositories.read_url",
               side_effect=responses(metadata, page, listing, links)):
        with pytest.raises(ValueError):
            resolve_dataset(SEED)
