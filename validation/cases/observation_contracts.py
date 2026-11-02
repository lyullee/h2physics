"""Deferred adversarial checks for the shared non-time observation contract."""

from dataclasses import replace

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="repository-attachment-head-redirect-integrity",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_repository_size_probe",
            invariants=(
                "attachment size uses a bounded HEAD-only request without reading content",
                "initial attachment URL rejects non-HTTPS and embedded credentials",
                "redirect handler rejects HTTPS downgrade before following it",
                "attachment downloads use the shared credential-free redirect opener",
                "missing, malformed and zero Content-Length reject",
            ),
        ),
        ValidationCase(
            identifier="dataset-rights-license-identity-integrity",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_dataset_rights_integrity",
            invariants=(
                "supported license identifiers bind to an approved license-record host/path",
                "repository license aliases normalize to the canonical HTTPS grant URL while raw metadata remains source-bound",
                "Mendeley human-readable license labels take precedence over opaque record UUIDs",
                "receipt replay requires rights_permitted to be the boolean true",
                "replay receipt license, dataset identity and every attachment URL/checksum bind to a repository-issued Dataset",
                "manually constructed Dataset objects cannot authorize receipt replay",
                "forged license/URL claims reject before cache directory creation or any download",
                "mismatched or credential-bearing license URLs reject before filesystem or network activity",
                "replay requires the canonical HTTPS license locator from the resolved Dataset",
                "receipt replay preflights integer per-file and aggregate byte budgets before directory creation",
                "cache audit and replay reject symlink/junction paths instead of claiming external target bytes",
            ),
        ),
        ValidationCase(
            identifier="observation-table-contract-integrity",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_observation_contracts",
            invariants=(
                "row and experimental identities remain nonempty strings with unique row IDs",
                "source identity and typed measurement context are retained without coercion",
                "nested caller context sequences are frozen into immutable string pairs",
                "quantity, unit and reference basis mismatches remain explicit",
                "experiment splitting rejects a bare text value instead of splitting by character",
                "a split can be rechecked against its original source, preserving complete groups and row data",
                "observation concatenation rejects bare text and non-table members",
                "public arrays remain immutable and content identity includes their meanings",
                "public numeric arrays cannot have NumPy write access re-enabled",
                "immutable array copying preserves scalar shape and rejects object/text dtypes",
            ),
        ),
    )


def validate_observation_contracts(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.observations import ObservationTable, Variable

    variable = Variable("pressure", "pressure", "Pa")
    table = ObservationTable(
        np.array([[101_325.0], [120_000.0]]),
        (variable,),
        np.ones((2, 1), dtype=bool),
        ("rec-a", "rec-b"),
        ("run-1", "run-2"),
        ("measured",),
        "source-1",
        (("instrument", "PT-01"),),
    )
    expected = (
        (table, {"row_ids": ("rec-a", 2)}),
        (table, {"row_ids": ("rec-a", "rec-a")}),
        (table, {"experiment_ids": ("run-1", 2)}),
        (table, {"source_id": 1}),
        (table, {"context": (("instrument", 2),)}),
        (table, {"context": (("instrument", "PT-01"), ("instrument", "PT-02"))}),
    )
    rejected = 0
    for original, changes in expected:
        try:
            replace(original, **changes)
        except (TypeError, ValueError):
            rejected += 1
        else:
            raise AssertionError(f"Malformed observation binding was admitted: {tuple(changes)}")
    try:
        replace(variable, basis_id=1)
    except (TypeError, ValueError):
        rejected += 1
    else:
        raise AssertionError("Non-string variable measurement/reference basis was admitted")
    try:
        table.values[0, 0] = 0.0
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Observation values were mutable after construction")
    for retained in (table.values, table.valid):
        try:
            retained.setflags(write=True)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Observation array allowed write access to be re-enabled")
    from h2physics.core import immutable_array

    scalar = immutable_array(np.array(2.0))
    if scalar.shape != ():
        raise ValueError("Immutable array copying changed a scalar's shape")
    for unsupported in (np.array([object()], dtype=object), np.array(["label"])):
        try:
            immutable_array(unsupported)
        except TypeError:
            rejected += 1
        else:
            raise AssertionError("A nonnumeric dtype was admitted to byte-backed array storage")
    try:
        table.column("pressure", expected=Variable("pressure", "temperature", "Pa"))
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("A quantity mismatch was admitted by the observation API")
    if len(table.content_sha256) != 64:
        raise ValueError("Observation content identity is not a SHA-256 digest")
    from h2physics.observations import concatenate_observations, split_experiments

    try:
        split_experiments(table, "run-1")
    except TypeError:
        rejected += 1
    else:
        raise AssertionError("A bare experiment string was split into character IDs")
    partition = split_experiments(table, {"run-1"})
    if partition.held_out.experiment_ids != ("run-1",):
        raise ValueError("Whole experiment selection did not retain its declared group")
    if partition.require_partition_of(table) is not partition:
        raise ValueError("A valid partition lost its original source check")
    try:
        replace(partition, fitting=table).require_partition_of(table)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("A forged fitting subset was admitted as the source partition")
    for malformed in ("observation-table", (table, object())):
        try:
            concatenate_observations(malformed, source_id="combined")
        except TypeError:
            rejected += 1
        else:
            raise AssertionError("Malformed observation concatenation input was admitted")
    mutable_context_pair = ["operator", "shift-A"]
    mutable_context = [["instrument", "PT-01"], mutable_context_pair]
    frozen = replace(table, context=mutable_context)
    mutable_context_pair[1] = "changed"
    if frozen.context != (("instrument", "PT-01"), ("operator", "shift-A")):
        raise ValueError("Caller mutation changed the retained immutable observation context")
    return ValidationOutcome(
        accepted=True,
        metrics={"rejected_malformed_bindings": rejected, "valid_rows": len(table.row_ids)},
        limitations=("Contract integrity only; this fixture supplies no measured process data or model validation.",),
    )


def validate_repository_size_probe(*, work_directory, **parameters):
    del parameters
    from pathlib import Path
    from unittest.mock import patch

    from h2physics.data import acquire, repositories
    from h2physics.data.models import RemoteFile

    class Response:
        def __init__(self, final_url, headers):
            self._final_url = final_url
            self.headers = headers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return self._final_url

    calls = []

    def open_metadata(request, *, timeout):
        calls.append((request.get_method(), request.full_url, timeout))
        return Response("https://cdn.example.org/archive/data.csv", {"Content-Length": "1234"})

    with patch.object(repositories, "_open_metadata_request", open_metadata):
        size = repositories.head_content_length("https://data.example.org/archive/data.csv")
    assert size == 1234
    assert calls == [("HEAD", "https://data.example.org/archive/data.csv", 30.)]

    class DownloadResponse:
        url = "https://cdn.example.org/archive/data.csv"

        def __init__(self):
            self.remaining = b"abc"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _size):
            result, self.remaining = self.remaining, b""
            return result

    root = Path(work_directory) / "safe-download-cache"
    directory = acquire._cache_directory("redirect-fixture", "v1", root)
    directory.mkdir(parents=True, exist_ok=True)
    download_calls = []

    def safe_download(request, *, timeout):
        download_calls.append((request.get_method(), request.full_url, timeout))
        return DownloadResponse()

    with patch.object(acquire, "open_credential_free_https", safe_download):
        receipt = acquire._download(
            RemoteFile("data.csv", "https://data.example.org/archive/data.csv", 3),
            directory,
            root,
        )
    assert receipt.status == "acquired" and receipt.size_bytes == 3
    assert download_calls == [("GET", "https://data.example.org/archive/data.csv", 45)]

    rejected = 0
    for invalid_url in ("http://data.example.org/file.csv",
                        "https://user:secret@data.example.org/file.csv"):
        try:
            repositories.head_content_length(invalid_url)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Unsafe initial attachment URL was accepted")

    handler = repositories._CredentialFreeHTTPSRedirectHandler()
    for redirect_url in (
        "http://cdn.example.org/file.csv",
        "https://user:secret@cdn.example.org/file.csv",
    ):
        try:
            handler.redirect_request(None, None, 302, "Found", {}, redirect_url)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Unsafe redirect target was not rejected before follow-up")

    for final_url, headers in (
        ("https://cdn.example.org/file.csv", {}),
        ("https://cdn.example.org/file.csv", {"Content-Length": "unknown"}),
        ("https://cdn.example.org/file.csv", {"Content-Length": "0"}),
    ):
        with patch.object(repositories, "_open_metadata_request",
                          lambda request, *, timeout, u=final_url, h=headers: Response(u, h)):
            try:
                repositories.head_content_length("https://data.example.org/file.csv")
            except ValueError:
                rejected += 1
            else:
                raise AssertionError("Unsafe redirect or invalid attachment size was accepted")
    return ValidationOutcome(True, {"valid_head_size_bytes": size,
                                    "rejected_transport_cases": rejected},
        ("Mocked transport contract only; no repository request or external attachment was made.",))


def validate_dataset_rights_integrity(*, work_directory, **parameters):
    import hashlib
    from dataclasses import replace
    from pathlib import Path

    from h2physics.data.acquire import (
        AcquisitionReport, FileReceipt, ReplayBudget, audit_cached_dataset, replay_receipt,
    )
    from h2physics.data.models import Dataset, RemoteFile, _mark_repository_resolved
    from h2physics.data.repositories import _license
    from h2physics.data.reporting import write_receipt

    metadata = b"{}"
    license_url = "https://creativecommons.org/licenses/by/4.0/"
    dataset = Dataset(
        "rights-fixture", "Synthetic rights fixture", "", "v1", ("Fixture author",),
        "CC-BY-4.0", license_url, "https://data.example.org/record",
        hashlib.sha256(metadata).hexdigest(), "synthetic", ("fixture",),
        (), metadata,
    )
    unmarked_dataset = replace(dataset)
    dataset = _mark_repository_resolved(dataset)
    rejected = 0

    def save_bound_receipt(source, path, *, digest="0" * 64):
        receipts = tuple(FileReceipt(
            item.name, f"{source.key}/{source.version}/{item.name.rsplit('/', 1)[-1]}",
            item.size_bytes, digest, bool(item.checksum), "acquired",
        ) for item in source.files)
        write_receipt(AcquisitionReport(source, receipts, (), True), path)

    unmarked_path = Path(work_directory) / "fabricated-dataset-replay.toml"
    unmarked_root = Path(work_directory) / "must-not-be-created-by-fabricated-dataset"
    save_bound_receipt(unmarked_dataset, unmarked_path)
    try:
        replay_receipt(unmarked_path, unmarked_root, dataset=unmarked_dataset)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Receipt replay accepted a manually constructed Dataset")
    assert not unmarked_root.exists()

    for forged_url in (
        "https://example.org/licenses/CC-BY-4.0",
        "https://creativecommons.org/licenses/cc0/1.0/",
        "https://user:secret@creativecommons.org/licenses/by/4.0/",
        "https://creativecommons.org:8443/licenses/by/4.0/",
    ):
        try:
            replace(dataset, license_url=forged_url)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Mismatched or credential-bearing license URL was accepted")

    normalized_id, normalized_url = _license({
        "id": "CC-BY-4.0", "url": "https://unrelated.example.org/license",
    })
    assert normalized_id == "CC-BY-4.0"
    assert normalized_url == license_url
    false_match = _license({"id": "NOT-CC-BY-4.0", "url": "https://example.org/license"})
    assert false_match == ("UNRESOLVED", "https://example.org/license")
    label_url_conflict = _license({
        "id": "NOT-CC-BY-4.0", "url": license_url,
    })
    assert label_url_conflict == ("UNRESOLVED", license_url)
    url_only = _license({"url": license_url})
    assert url_only == ("CC-BY-4.0", license_url)
    mendeley_license = _license({
        "id": "01d9c749-3c4d-4431-9df3-620b2dcfe144",
        "short_name": "CC BY 4.0",
        "full_name": "Creative Commons Attribution 4.0 International",
        "url": "http://creativecommons.org/licenses/by/4.0",
    })
    assert mendeley_license == ("CC-BY-4.0", license_url)
    conflicting = _license({
        "id": "CC0-1.0", "url": "https://creativecommons.org/licenses/by/4.0/",
    })
    assert conflicting == ("UNRESOLVED", "")

    receipt_path = Path(work_directory) / "rights-identity-replay-fixture.toml"
    root = Path(work_directory) / "must-not-be-created-by-invalid-rights"
    for rights_text, recorded_url in (
        ("false", license_url),
        ("true", "https://creativecommons.org/licenses/by-sa/4.0/"),
    ):
        save_bound_receipt(dataset, receipt_path)
        changed_receipt = receipt_path.read_text(encoding="utf-8")
        changed_receipt = changed_receipt.replace(
            "rights_permitted = true", f"rights_permitted = {rights_text}",
        ).replace(f'license_url = "{license_url}"', f'license_url = "{recorded_url}"')
        receipt_path.write_text(changed_receipt, encoding="utf-8")
        try:
            replay_receipt(receipt_path, root, dataset=dataset)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Invalid receipt rights reached replay selection")
        assert not root.exists()

    listed_file = RemoteFile("listed.csv", "https://data.example.org/listed.csv", 4)
    listed_dataset = _mark_repository_resolved(replace(dataset, key="fixture", files=(listed_file,)))
    save_bound_receipt(listed_dataset, receipt_path)
    altered_receipt = receipt_path.read_text(encoding="utf-8").replace(
        'url = "https://data.example.org/listed.csv"',
        'url = "https://attacker.example.org/forged.csv"',
    )
    receipt_path.write_text(altered_receipt, encoding="utf-8")
    forged_root = Path(work_directory) / "must-not-be-created-by-forged-attachment"
    try:
        replay_receipt(receipt_path, forged_root, dataset=listed_dataset)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Receipt replay accepted an attachment URL absent from publisher metadata")
    assert not forged_root.exists()

    def replay_dataset(entries):
        files = tuple(RemoteFile(name, f"https://data.example.org/{name}", size)
                      for name, size in entries)
        return _mark_repository_resolved(
            replace(dataset, key="fixture", version="v1", files=files)
        )

    budget = ReplayBudget(maximum_total_bytes=10, maximum_file_bytes=8)
    budget_cases = (
        (("large.csv", 9),),
        (("first.csv", 6), ("second.csv", 6)),
    )
    for index, entries in enumerate(budget_cases):
        budget_dataset = replay_dataset(entries)
        save_bound_receipt(budget_dataset, receipt_path)
        budget_root = Path(work_directory) / f"budget-preflight-{index}"
        try:
            replay_receipt(receipt_path, budget_root, dataset=budget_dataset, budget=budget)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Over-budget receipt reached replay")
        assert not budget_root.exists()
    payload = b"source-bound cache fixture"
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    linked_file = RemoteFile(
        "linked.csv", "https://data.example.org/linked.csv", len(payload),
        "sha256", payload_sha256,
    )
    linked_dataset = _mark_repository_resolved(
        replace(dataset, key="fixture", files=(linked_file,))
    )
    linked_root = Path(work_directory) / "linked-cache-root"
    outside = Path(work_directory) / "outside-cache.csv"
    outside.write_bytes(payload)
    linked_directory = linked_root / "fixture" / "v1"
    linked_directory.mkdir(parents=True)
    cache_path = linked_directory / linked_file.name
    cache_path.symlink_to(outside)
    audited_link = audit_cached_dataset(linked_dataset, linked_root)
    if len(audited_link.files) != 1 or audited_link.files[0].status != "failed":
        raise AssertionError("Cache audit followed an external symbolic link as publisher data")
    save_bound_receipt(linked_dataset, receipt_path, digest=payload_sha256)
    try:
        replay_receipt(receipt_path, linked_root, dataset=linked_dataset)
    except ValueError as error:
        if "symbolic link" not in str(error):
            raise
        rejected += 1
    else:
        raise AssertionError("Receipt replay accepted bytes through an external cache symlink")
    if not cache_path.is_symlink() or outside.read_bytes() != payload:
        raise AssertionError("A rejected symlink cache changed its external target")
    shared_directory = linked_root / "shared-cache" / "v2"
    shared_directory.mkdir(parents=True)
    (shared_directory / linked_file.name).write_bytes(payload)
    linked_version_directory = linked_root / "fixture" / "v2"
    linked_version_directory.symlink_to(shared_directory, target_is_directory=True)
    aliased_dataset = replace(linked_dataset, version="v2")
    try:
        audit_cached_dataset(aliased_dataset, linked_root)
    except ValueError as error:
        if "identity path" not in str(error):
            raise
        directory_alias_rejected = True
    else:
        raise AssertionError("A dataset version symlink borrowed another cache identity")
    return ValidationOutcome(True, {
        "rejected_forged_rights_bindings": rejected,
        "replay_size_budget_cases_rejected_before_directory_creation": len(budget_cases),
        "cache_symlink_source_claim_rejected": True,
        "cache_identity_directory_symlink_rejected": directory_alias_rejected,
        "false_substring_or_conflicting_license_labels_unresolved": True,
        "empty_label_allows_known_url_only": True,
        "repository_license_alias_normalized": True,
    }, ("Deferred rights-integrity contract only; no URL was fetched and no data was acquired.",))
