"""Deferred metadata-only contract for the public TUdatalib DSpace API."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="tudatalib-engine-metadata-receipt",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_metadata_contract",
        invariants=(
            "exact item, ORIGINAL bundle, and bitstream-list bytes are retained",
            "item identity, release metadata, named authors, DOI, CC-BY-4.0, sizes, and MD5 are parsed",
            "only credential-free HTTPS links on the official TUdatalib host are accepted",
            "item DOI must match the pinned identifier and unresolved/restricted license metadata is rejected",
            "multiple or absent ORIGINAL bundles and malformed bitstream receipts are rejected",
            "provider resolution requests metadata only and never reads attachment content",
        ),
    ),)


def validate_metadata_contract(*, work_directory):
    """Exercise a mocked receipt; the deferred contract performs no network I/O."""
    from hashlib import sha256
    from unittest.mock import patch

    from h2physics.data.catalog import DATASETS
    from h2physics.data.repositories import resolve_dataset

    seed = next(seed for seed in DATASETS if seed.provider == "tudatalib")
    host = "https://tudatalib.ulb.tu-darmstadt.de/server/api"
    item_url = host + "/core/items/" + seed.identifier
    bundle_url = item_url + "/bundles"
    bitstream_url = host + "/core/bundles/bundle-uuid/bitstreams"
    item_raw = (b'{"uuid":"dbec6035-12f9-4ba6-b776-7b4ec4b11979",'
        b'"metadata":{"dc.title":[{"value":"Hydrogen engine observations"}],'
        b'"dc.identifier.uri":[{"value":"https://tudatalib.ulb.tu-darmstadt.de/handle/tudatalib/5501"},'
        b'{"value":"https://doi.org/10.48328/tudatalib-2291"}],'
        b'"dc.contributor.author":[{"value":"Researcher One"},{"value":"Researcher Two"}],'
        b'"dc.date.issued":[{"value":"2026-07-17"}],'
        b'"dc.rights.license":[{"value":"CC-BY-4.0"}]},'
        b'"_links":{"bundles":{"href":"/server/api/core/items/'
        b'dbec6035-12f9-4ba6-b776-7b4ec4b11979/bundles"}}}')
    bundle_raw = (b'{"_embedded":{"bundles":[{"uuid":"bundle-uuid","name":"ORIGINAL",'
        b'"_links":{"bitstreams":{"href":"/server/api/core/bundles/'
        b'bundle-uuid/bitstreams"}}]}}')
    bitstream_raw = (b'{"_embedded":{"bitstreams":[{"name":"observations.h5",'
        b'"sizeBytes":1234,"checkSum":{"checkSumAlgorithm":"MD5",'
        b'"value":"0123456789abcdef0123456789abcdef"},"_links":{"content":'
        b'{"href":"/server/api/core/bitstreams/file-uuid/content"}}}]}}')
    responses = {item_url: item_raw, bundle_url: bundle_raw, bitstream_url: bitstream_raw}
    with patch("h2physics.data.repositories.read_url", side_effect=lambda url, **kwargs: responses[url]) as mocked:
        dataset = resolve_dataset(seed)
    assert [call.args[0] for call in mocked.call_args_list] == [item_url, bundle_url, bitstream_url]
    assert dataset.metadata_bytes == item_raw
    assert dataset.metadata_sha256 == sha256(item_raw).hexdigest()
    assert dataset.supporting_metadata == ((bundle_url, bundle_raw), (bitstream_url, bitstream_raw))
    assert (dataset.doi, dataset.version, dataset.license_id) == (
        "10.48328/tudatalib-2291", "2026-07-17", "CC-BY-4.0")
    assert dataset.authors == ("Researcher One", "Researcher Two")
    assert len(dataset.files) == 1 and dataset.files[0].size_bytes == 1234

    # Validate the redirect boundary itself without opening a socket.
    from types import SimpleNamespace
    from urllib.request import Request
    from h2physics.data.repositories import _CredentialFreeHTTPSRedirectHandler
    handler = _CredentialFreeHTTPSRedirectHandler("tudatalib.ulb.tu-darmstadt.de")
    try:
        handler.redirect_request(
            Request(item_url), SimpleNamespace(), 302, "Found", {},
            "https://elsewhere.invalid/server/api/core/items/redirected")
    except ValueError:
        pass
    else:
        raise AssertionError("TUdatalib redirects must not leave the pinned publisher host")

    unsafe_item = item_raw.replace(
        b"/server/api/core/items/dbec6035-12f9-4ba6-b776-7b4ec4b11979/bundles",
        b"https://elsewhere.invalid/bundles")
    responses[item_url] = unsafe_item
    with patch("h2physics.data.repositories.read_url", side_effect=lambda url, **kwargs: responses[url]):
        try:
            resolve_dataset(seed)
        except ValueError:
            pass
        else:
            raise AssertionError("Cross-host API link must be rejected")
    responses[item_url] = item_raw

    doi_mismatch = item_raw.replace(
        b"10.48328/tudatalib-2291", b"10.48328/tudatalib-9999")
    responses[item_url] = doi_mismatch
    with patch("h2physics.data.repositories.read_url", side_effect=lambda url, **kwargs: responses[url]):
        try:
            resolve_dataset(seed)
        except ValueError:
            pass
        else:
            raise AssertionError("A DOI that differs from the pinned item identity must be rejected")
    responses[item_url] = item_raw

    missing_license = item_raw.replace(b'"dc.rights.license":[{"value":"CC-BY-4.0"}],', b"")
    responses[item_url] = missing_license
    with patch("h2physics.data.repositories.read_url", side_effect=lambda url, **kwargs: responses[url]):
        try:
            resolve_dataset(seed)
        except ValueError:
            pass
        else:
            raise AssertionError("Missing or unresolved license metadata must be rejected")
    responses[item_url] = item_raw

    duplicate_original = bundle_raw.replace(
        b"]}}", b',{"uuid":"second","name":"ORIGINAL","_links":{"bitstreams":{"href":"/server/api/core/bundles/second/bitstreams"}}}]}')
    responses[bundle_url] = duplicate_original
    with patch("h2physics.data.repositories.read_url", side_effect=lambda url, **kwargs: responses[url]):
        try:
            resolve_dataset(seed)
        except ValueError:
            pass
        else:
            raise AssertionError("Ambiguous ORIGINAL bundles must be rejected")

    return ValidationOutcome(True, {
        "happy_path_metadata_requests": 3,
        "item_sha256": dataset.metadata_sha256,
        "retained_supporting_snapshots": len(dataset.supporting_metadata),
        "rejected_unsafe_identity_or_ambiguous_receipts": 4,
    }, ("Metadata contract only; no file content, experiments, or model calculation",))
