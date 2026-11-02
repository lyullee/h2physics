"""Read public repository metadata; preserve its unmodified bytes outside the distribution."""

import hashlib
import json
import re
import time
import urllib.request
from urllib.parse import quote, unquote, urlencode, urljoin, urlparse

from ..core import finite
from .catalog import DatasetSeed
from .models import (
    LICENSE_URL_IDENTITIES,
    Dataset,
    RemoteFile,
    _mark_repository_resolved,
    license_url_matches,
)

USER_AGENT = "h2physics/0.1 (public scientific data acquisition)"


class _CredentialFreeHTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject unsafe redirect targets before urllib sends a follow-up request."""

    def __init__(self, allowed_host: str | None = None):
        super().__init__()
        self.allowed_host = allowed_host

    def redirect_request(self, request, response, code, message, headers, new_url):
        target = urlparse(new_url)
        if (target.scheme != "https" or not target.hostname
                or target.username is not None or target.password is not None):
            raise ValueError("Repository metadata redirect left credential-free HTTPS")
        if (self.allowed_host is not None
                and (target.hostname != self.allowed_host or target.port not in (None, 443))):
            raise ValueError("Repository metadata redirect left its pinned host")
        return super().redirect_request(request, response, code, message, headers, new_url)


def _open_metadata_request(request, *, timeout: float, allowed_host: str | None = None):
    handler = _CredentialFreeHTTPSRedirectHandler(allowed_host=allowed_host)
    opener = urllib.request.build_opener(handler)
    return opener.open(request, timeout=timeout)


def open_credential_free_https(request, *, timeout: float):
    """Open HTTPS requests with downgrade/credential redirects blocked pre-follow."""
    return _open_metadata_request(request, timeout=timeout)


def read_url(url: str, *, timeout: float = 30, maximum_bytes: int = 20_000_000,
             headers: dict[str, str] | None = None,
             allowed_host: str | None = None) -> bytes:
    parsed = urlparse(url) if isinstance(url, str) else None
    if (parsed is None or parsed.scheme != "https" or not parsed.hostname
            or parsed.username is not None or parsed.password is not None):
        raise ValueError("Repository metadata requests require a credential-free HTTPS URL")
    if allowed_host is not None:
        try:
            port = parsed.port
        except ValueError as error:
            raise ValueError("Malformed repository metadata URL port") from error
        if parsed.hostname != allowed_host or port not in (None, 443):
            raise ValueError("Repository metadata URL does not match its pinned host")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise TypeError("Metadata request timeout must be numeric")
    timeout = finite(timeout, "metadata request timeout", positive=True)
    if isinstance(maximum_bytes, bool) or not isinstance(maximum_bytes, int) or maximum_bytes < 1:
        raise ValueError("Metadata response byte limit must be a positive integer")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    last_error = None
    for attempt in range(3):
        try:
            with _open_metadata_request(request, timeout=timeout, allowed_host=allowed_host) as response:
                final_url = urlparse(response.geturl())
                if (final_url.scheme != "https" or not final_url.hostname
                        or final_url.username is not None or final_url.password is not None):
                    raise ValueError("Repository metadata redirect left credential-free HTTPS")
                if (allowed_host is not None
                        and (final_url.hostname != allowed_host or final_url.port not in (None, 443))):
                    raise ValueError("Repository metadata redirect left its pinned host")
                data = response.read(maximum_bytes + 1)
            if len(data) > maximum_bytes:
                raise ValueError("Metadata response exceeds the declared size limit")
            return data
        except (OSError, TimeoutError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code == 429:
                retry = error.headers.get("Retry-After", "unspecified")
                raise RuntimeError(f"Metadata rate limited; Retry-After={retry}; retry explicitly later") from error
            last_error = error
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"Metadata retrieval failed for {url}: {last_error}") from last_error


def head_content_length(url: str, *, timeout: float = 30) -> int:
    """Read an attachment size without downloading content or following insecure redirects."""
    parsed = urlparse(url) if isinstance(url, str) else None
    if (parsed is None or parsed.scheme != "https" or not parsed.hostname
            or parsed.username is not None or parsed.password is not None):
        raise ValueError("Attachment size probes require a credential-free HTTPS URL")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise TypeError("Attachment size probe timeout must be numeric")
    timeout = finite(timeout, "attachment size probe timeout", positive=True)
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with _open_metadata_request(request, timeout=timeout) as response:
        final_url = urlparse(response.geturl())
        if (final_url.scheme != "https" or not final_url.hostname
                or final_url.username is not None or final_url.password is not None):
            raise ValueError("Attachment size probe redirect left credential-free HTTPS")
        raw_size = response.headers.get("Content-Length")
    if not isinstance(raw_size, str) or re.fullmatch(r"[0-9]+", raw_size.strip()) is None:
        raise ValueError("Repository attachment response has no valid Content-Length")
    size = int(raw_size)
    if size <= 0:
        raise ValueError("Repository attachment size must be positive")
    return size


def _license(value) -> tuple[str, str]:
    if isinstance(value, dict):
        # Repository licenses may carry an opaque record UUID in `id` and the
        # human-readable grant only in `short_name`/`full_name` (Mendeley Data).
        # Prefer explicit license labels and URLs over that unrelated UUID.
        raw_name = (value.get("rightsIdentifier") or value.get("short_name")
                    or value.get("name") or value.get("full_name")
                    or value.get("rights") or value.get("id", ""))
        raw_url = value.get("url") or value.get("uri") or value.get("rightsUri", "")
        name = raw_name if isinstance(raw_name, str) else ""
        url = raw_url if isinstance(raw_url, str) else ""
    else:
        # Several repositories expose a bare grant URL as the complete license
        # value. Treat it as a locator rather than as an unrecognized label.
        raw = str(value or "")
        if urlparse(raw).scheme:
            name, url = "", raw
        else:
            name, url = raw, ""
    canonical = (
        ("etalab-2.0", "https://spdx.org/licenses/etalab-2.0.html"),
        ("CC-BY-SA-4.0",
         "https://creativecommons.org/licenses/by-sa/4.0/"),
        ("CC0-1.0",
         "https://creativecommons.org/publicdomain/zero/1.0/"),
        ("CC-BY-4.0",
         "https://creativecommons.org/licenses/by/4.0/"),
    )
    aliases = {
        "etalab-2.0": {"etalab-2-0", "open-licence-2-0", "licence-ouverte-2-0"},
        "CC-BY-SA-4.0": {"cc-by-sa-4-0", "cc-by-sa-4-0-international",
                          "creative-commons-attribution-share-alike-4-0-international"},
        "CC0-1.0": {"cc0", "cc0-1-0", "cc0-1-0-universal",
                     "cc0-1-0-public-domain-dedication"},
        "CC-BY-4.0": {"cc-by-4-0", "cc-by-4-0-international",
                      "creative-commons-attribution-4-0-international"},
    }
    normalized_name = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    name_id = next((identifier for identifier, values in aliases.items()
                    if normalized_name in values), None)
    source_url = urlparse(url)
    if (normalized_name and name_id is None):
        retained_url = (url if source_url.scheme == "https" and source_url.hostname
                        and source_url.username is None and source_url.password is None else "")
        return "UNRESOLVED", retained_url
    url_ids = [identifier for identifier in LICENSE_URL_IDENTITIES
               if license_url_matches(identifier, url, require_https=False)]
    url_id = url_ids[0] if len(url_ids) == 1 else None
    if name_id is not None and url_id is not None and name_id != url_id:
        return "UNRESOLVED", ""
    selected_id = name_id or url_id
    if (source_url.scheme == "https" and source_url.hostname
            and source_url.username is None and source_url.password is None):
        retained_url = url
    else:
        retained_url = ""
    for identifier, canonical_url in canonical:
        if identifier == selected_id:
            # The exact publisher URL remains in metadata_bytes; use the stable
            # grant text URL here so ID and locator cannot disagree.
            return identifier, canonical_url
    return "UNRESOLVED", retained_url


def _checksum(value) -> tuple[str, str]:
    if isinstance(value, dict):
        algorithm = str(value.get("type", "")).lower().replace("-", "")
        return algorithm, str(value.get("value", "")).lower()
    if not value:
        return "", ""
    if ":" in value:
        algorithm, digest = value.split(":", 1)
        return algorithm.lower(), digest.lower()
    return "md5", value.lower()


def _tudatalib_api_url(value: str, *, host: str = "tudatalib.ulb.tu-darmstadt.de") -> str:
    """Accept only credential-free HTTPS API/content URLs on the TUdatalib host."""
    parsed = urlparse(value) if isinstance(value, str) else None
    try:
        port = parsed.port if parsed is not None else None
    except ValueError as error:
        raise ValueError("Malformed TUdatalib URL port") from error
    if (parsed is None or parsed.scheme != "https" or parsed.hostname != host
            or parsed.username is not None or parsed.password is not None
            or port not in (None, 443) or parsed.fragment or parsed.query
            or not parsed.path.startswith("/server/api/")):
        raise ValueError("TUdatalib links must remain credential-free HTTPS on its official host")
    return value


def _tudatalib_metadata_value(metadata: dict, key: str, *, required: bool = True) -> str:
    """Read DSpace REST metadata while preserving exact source bytes separately."""
    entries = metadata.get(key, [])
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list):
        raise ValueError(f"TUdatalib metadata field {key} is malformed")
    values = [entry.get("value") for entry in entries
              if isinstance(entry, dict) and isinstance(entry.get("value"), str)
              and entry["value"].strip()]
    if required and not values:
        raise ValueError(f"TUdatalib item is missing required metadata field {key}")
    return values[0] if values else ""


def _tudatalib_authors(metadata: dict) -> tuple[str, ...]:
    values = metadata.get("dc.contributor.author", [])
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        raise ValueError("TUdatalib author metadata is malformed")
    authors = tuple(entry["value"].strip() for entry in values
                    if isinstance(entry, dict) and isinstance(entry.get("value"), str)
                    and entry["value"].strip())
    if not authors:
        raise ValueError("TUdatalib item has no named authors")
    return authors


def _make(seed, url, raw, *, title, doi, version, authors, license_value, files,
          supporting_metadata=(), source_updated_at=""):
    license_id, license_url = _license(license_value)
    return _mark_repository_resolved(Dataset(
        seed.key, title, doi, str(version), tuple(authors), license_id, license_url,
        url, hashlib.sha256(raw).hexdigest(), seed.origin, seed.families, tuple(files), raw,
        tuple(supporting_metadata), source_updated_at,
    ))


def dataset_from_mendeley_bytes(
    seed: DatasetSeed, *, snapshot_bytes: bytes, file_listing_bytes: bytes,
    expected_snapshot_sha256: str, expected_listing_sha256: str,
) -> Dataset:
    """Resolve a Mendeley record from exact staged public metadata responses.

    This parses the same response format as the Mendeley branch in
    :func:`resolve_dataset` and preserves the original bytes. It deliberately
    does not issue the private repository marker used by receipt replay:
    caller-provided hashes are not independent publisher authority. Dataset-
    specific readers must pin these bytes and validate exact source identity.
    """
    if not isinstance(seed, DatasetSeed) or seed.provider != "mendeley":
        raise TypeError("An explicit Mendeley DatasetSeed is required")
    if not isinstance(snapshot_bytes, bytes) or not isinstance(file_listing_bytes, bytes):
        raise TypeError("Mendeley publisher responses must be supplied as exact bytes")
    for label, payload, expected in (
        ("snapshot", snapshot_bytes, expected_snapshot_sha256),
        ("file listing", file_listing_bytes, expected_listing_sha256),
    ):
        if (not isinstance(expected, str) or len(expected) != 64
                or any(character not in "0123456789abcdef" for character in expected)):
            raise ValueError(f"Expected {label} SHA-256 must be lowercase hexadecimal")
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError(f"Staged Mendeley {label} bytes do not match the pinned SHA-256")
    if len(snapshot_bytes) > 20_000_000 or len(file_listing_bytes) > 20_000_000:
        raise ValueError("Staged Mendeley metadata exceeds the response-size limit")
    try:
        data = json.loads(snapshot_bytes)
        listing = json.loads(file_listing_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise ValueError("Staged Mendeley publisher responses must be valid JSON") from error
    if not isinstance(data, dict) or not isinstance(listing, list):
        raise ValueError("Staged Mendeley metadata or file listing has an invalid root type")
    parts = seed.identifier.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise ValueError("Mendeley seed identifier must include dataset ID and version")
    identifier, version = parts
    metadata_url = f"https://data.mendeley.com/public-api/datasets/{identifier}/snapshot/{version}"
    listing_url = (
        f"https://data.mendeley.com/public-api/datasets/{identifier}/files?"
        f"folder_id=root&version={version}&$start=0&$limit=1000"
    )
    if (str(data.get("version")) != version or not isinstance(data.get("name"), str)
            or not data["name"].strip() or not isinstance(data.get("contributors"), list)
            or not isinstance(data.get("licence"), dict)):
        raise ValueError("Staged Mendeley snapshot lacks its required publisher identity fields")
    files = []
    for entry in listing:
        if not isinstance(entry, dict):
            raise ValueError("Mendeley file-list rows must be objects")
        if entry.get("status") != "COMPLETED":
            continue
        name = entry.get("filename")
        file_id = entry.get("id")
        content = entry.get("content_details")
        if (not isinstance(name, str) or not name.strip() or not isinstance(file_id, str)
                or not file_id.strip() or not isinstance(content, dict)):
            raise ValueError("Completed Mendeley file row is missing its filename, ID or content details")
        download_url = content.get("download_url")
        expected_url = (
            f"https://data.mendeley.com/public-files/datasets/{identifier}/files/"
            f"{file_id}/file_downloaded"
        )
        if download_url != expected_url:
            raise ValueError("Staged Mendeley listing contains a noncanonical public file URL")
        checksum = content.get("sha256_hash", "")
        files.append(RemoteFile(
            name, download_url, content.get("size"), "sha256" if checksum else "", checksum,
        ))
    license_id, license_url = _license(data["licence"])
    return Dataset(
        seed.key, data["name"], data.get("doi", ""), str(data["version"]), tuple(
            " ".join(filter(None, (item.get("first_name"), item.get("last_name"))))
            for item in data["contributors"] if isinstance(item, dict)
        ), license_id, license_url, metadata_url, hashlib.sha256(snapshot_bytes).hexdigest(),
        seed.origin, seed.families, tuple(files), snapshot_bytes,
        ((listing_url, file_listing_bytes),),
    )


def dataset_from_figshare_bytes(
    seed: DatasetSeed, *, snapshot_bytes: bytes, expected_snapshot_sha256: str,
) -> Dataset:
    """Parse one pinned Figshare v2 response from staged bytes without network I/O.

    The expected digest must come from a separately reviewed source receipt.
    The resulting object retains the exact response, but is not marked as an
    online repository resolution; consumers must still bind their own identity.
    """
    if not isinstance(seed, DatasetSeed) or seed.provider != "figshare":
        raise TypeError("An explicit Figshare DatasetSeed is required")
    if not isinstance(snapshot_bytes, bytes) or len(snapshot_bytes) > 20_000_000:
        raise ValueError("Staged Figshare metadata must be bounded original bytes")
    if (not isinstance(expected_snapshot_sha256, str)
            or len(expected_snapshot_sha256) != 64
            or any(value not in "0123456789abcdef" for value in expected_snapshot_sha256)
            or hashlib.sha256(snapshot_bytes).hexdigest() != expected_snapshot_sha256):
        raise ValueError("Staged Figshare metadata does not match its pinned SHA-256")
    try:
        data = json.loads(snapshot_bytes)
        if (not isinstance(data, dict) or not seed.identifier.isdecimal()
                or str(data.get("id", "")) != seed.identifier):
            raise ValueError("Figshare response identity differs from the selected dataset seed")
        if data.get("is_public") is not True or data.get("is_confidential") is not False:
            raise ValueError("Only an explicitly public, non-confidential Figshare record is accepted")
        files_data = data["files"]
        authors_data = data["authors"]
        if (not isinstance(files_data, list) or not files_data
                or not isinstance(authors_data, list) or not authors_data):
            raise ValueError("Figshare response must retain nonempty file and author lists")
        files = []
        for item in files_data:
            if not isinstance(item, dict):
                raise ValueError("Figshare file entries must be metadata objects")
            files.append(RemoteFile(
                item["name"], item["download_url"], item["size"],
                *_checksum(item.get("computed_md5")),
            ))
        authors = []
        for author in authors_data:
            if (not isinstance(author, dict) or not isinstance(author.get("full_name"), str)
                    or not author["full_name"].strip()):
                raise ValueError("Figshare author records must retain nonempty public names")
            authors.append(author["full_name"])
        metadata_url = f"https://api.figshare.com/v2/articles/{seed.identifier}"
        license_id, license_url = _license(data.get("license"))
        return Dataset(
            key=seed.key, title=data["title"], doi=data.get("doi", ""),
            version=str(data["version"]), authors=tuple(authors),
            license_id=license_id, license_url=license_url,
            metadata_url=metadata_url, metadata_sha256=expected_snapshot_sha256,
            origin=seed.origin, families=seed.families, files=tuple(files),
            metadata_bytes=snapshot_bytes,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("Pinned Figshare response has an invalid public metadata schema") from error


def resolve_dataset(seed: DatasetSeed) -> Dataset:
    """Return a native metadata object without downloading experimental attachments."""
    if seed.provider == "figshare":
        url = f"https://api.figshare.com/v2/articles/{seed.identifier}"
        raw = read_url(url)
        data = json.loads(raw)
        files = [RemoteFile(x["name"], x["download_url"], x["size"],
                            *_checksum(x.get("computed_md5"))) for x in data["files"]]
        return _make(seed, url, raw, title=data["title"], doi=data.get("doi", ""),
                     version=data["version"], authors=[a["full_name"] for a in data["authors"]],
                     license_value=data.get("license"), files=files)
    if seed.provider == "zenodo":
        url = f"https://zenodo.org/api/records/{seed.identifier}"
        raw = read_url(url)
        data = json.loads(raw)
        metadata = data["metadata"]
        files = [RemoteFile(x["key"], x["links"]["self"], x["size"],
                            *_checksum(x.get("checksum"))) for x in data.get("files", [])]
        return _make(seed, url, raw, title=metadata["title"], doi=metadata.get("doi", ""),
                     version=metadata.get("version", seed.identifier),
                     authors=[a["name"] for a in metadata.get("creators", [])],
                     license_value=metadata.get("license"), files=files)
    if seed.provider == "radar-kit":
        # Published UI metadata and anonymous download-link endpoints. Do not use
        # internal binaryUrl values or authenticated archive-management endpoints.
        url = "https://api.datacite.org/dois/" + quote(seed.identifier, safe="/")
        raw = read_url(url)
        data = json.loads(raw)["data"]["attributes"]
        landing = data["url"]
        parsed = urlparse(landing)
        if parsed.scheme != "https" or parsed.hostname != "radar.kit.edu":
            raise ValueError("RADAR-KIT metadata must identify its public HTTPS landing page")
        match = re.fullmatch(r"/radar/(?:en|de)/dataset/([A-Za-z0-9]+)", parsed.path)
        if match is None or data["doi"].lower() != seed.identifier.lower():
            raise ValueError("RADAR-KIT dataset identity is inconsistent")
        identifier = match.group(1)
        page = read_url(landing)
        graph = []
        pattern = r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        for block in re.findall(pattern, page.decode("utf-8"), re.S):
            record = json.loads(block)
            graph.extend(record.get("@graph", []))
        downloads = [node for node in graph if node.get("type", node.get("@type")) == "DataDownload"]
        if len(downloads) != 1:
            raise ValueError("RADAR-KIT must declare one versioned archive distribution")
        content_url = downloads[0].get("contentUrl", downloads[0].get("schema:contentUrl", ""))
        version_match = re.search(r"/archives/" + re.escape(identifier) + r"/versions/(\d+)/content$", content_url)
        if version_match is None:
            raise ValueError("RADAR-KIT archive version is not explicit")
        license_values = [x for x in data.get("rightsList", []) if _license(x)[0] != "UNRESOLVED"]
        license_ids = {_license(value)[0] for value in license_values}
        if len(license_ids) != 1:
            raise ValueError("RADAR-KIT requires one unambiguous supported dataset license")
        supporting, files, offset, identifiers = [(landing, page)], [], 0, set()
        while True:
            query = urlencode({"folderId": identifier, "start": offset, "length": 100,
                               "draw": 1, "order[0][column]": 0, "order[0][dir]": "asc",
                               "columns[0][data]": "titleName"})
            listing_url = "https://radar.kit.edu/radar/ajax/getFolderContent?" + query
            listing_raw = read_url(listing_url)
            listing = json.loads(listing_raw)
            supporting.append((listing_url, listing_raw))
            rows = listing["data"]
            for row in rows:
                if row.get("contentType") != "file":
                    raise ValueError("Nested RADAR folders require an explicit acquisition extension")
                file_id = row["id"]
                if file_id in identifiers:
                    raise ValueError("RADAR listing repeated a file across pages")
                identifiers.add(file_id)
                matches = [child for child in row["children"] if child["id"] == file_id]
                if len(matches) != 1 or matches[0]["parentId"] != identifier:
                    raise ValueError("RADAR file metadata does not match its listed parent/identity")
                binary = matches[0]["binary"]
                if binary["name"] != row["titleName"]:
                    raise ValueError("RADAR binary and display filenames differ")
                link_url = "https://radar.kit.edu/radar/file/getDownloadLink/" + quote(file_id, safe="")
                link_raw = read_url(link_url)
                supporting.append((link_url, link_raw))
                resource = json.loads(link_raw)["downloadUrl"]
                resource_path = urlparse(resource)
                expected_path = f"/radar-backend/archives/{identifier}/retrieveFile/{file_id}"
                if (resource_path.scheme != "https" or resource_path.hostname != "radar.kit.edu"
                        or resource_path.path != expected_path or resource_path.query):
                    raise ValueError("RADAR did not supply the expected public file link")
                files.append(RemoteFile(binary["name"], resource, binary["size"], *_checksum(
                    {"type": binary["checksumType"], "value": binary["checksum"]})))
            offset += len(rows)
            if offset == listing["recordsTotal"]:
                break
            if not rows or offset > listing["recordsTotal"]:
                raise ValueError("RADAR listing pagination is incomplete or inconsistent")
        return _make(seed, url, raw, title=data["titles"][0]["title"], doi=data["doi"],
                     version="archive-" + version_match.group(1),
                     authors=[author["name"] for author in data["creators"]],
                     license_value=license_values[0], files=files, supporting_metadata=supporting,
                     source_updated_at=data.get("updated", ""))
    if seed.provider in {"dataverse", "dataverse-fr"}:
        base = {"dataverse": "https://dataverse.no",
                "dataverse-fr": "https://entrepot.recherche.data.gouv.fr"}[seed.provider]
        url = (base + "/api/datasets/:persistentId/?persistentId="
               + quote("doi:" + seed.identifier, safe=""))
        raw = read_url(url)
        data = json.loads(raw)["data"]["latestVersion"]
        fields = {f["typeName"]: f["value"] for f in data["metadataBlocks"]["citation"]["fields"]}
        files = []
        for item in data["files"]:
            if item.get("restricted"):
                continue
            x = item["dataFile"]
            # Ingested tabular metadata describes the archival TAB size but the
            # publisher MD5 identifies the original upload. Request that original
            # and preserve its own name/size instead of mixing representations.
            files.append(RemoteFile(x.get("originalFileName", x["filename"]),
                         f"{base}/api/access/datafile/{x['id']}?format=original",
                         x.get("originalFileSize", x["filesize"]), *_checksum(x.get("checksum"))))
        return _make(seed, url, raw, title=fields["title"], doi=seed.identifier,
                     version=f"{data['versionNumber']}.{data['versionMinorNumber']}",
                     authors=[a["authorName"]["value"] for a in fields.get("author", [])],
                     license_value=data.get("license"), files=files,
                     source_updated_at=data.get("lastUpdateTime", ""))
    if seed.provider == "dryad":
        url = "https://datadryad.org/api/v2/datasets/" + quote("doi:" + seed.identifier, safe="")
        raw = read_url(url)
        data = json.loads(raw)
        version_url = urljoin(url, data["_links"]["stash:version"]["href"])
        file_url = version_url + "/files"
        file_raw = read_url(file_url)
        file_data = json.loads(file_raw)
        files = []
        for x in file_data.get("_embedded", {}).get("stash:files", []):
            download = urljoin(url, x["_links"]["stash:download"]["href"])
            algorithm, digest = _checksum({"type": x.get("digestType", ""),
                                           "value": x.get("digest", "")})
            files.append(RemoteFile(x["path"], download, x["size"], algorithm, digest))
        return _make(seed, url, raw, title=data["title"], doi=seed.identifier,
                     version=data["versionNumber"], authors=[
                         " ".join(filter(None, [a.get("firstName"), a.get("lastName")]))
                         for a in data["authors"]], license_value=data.get("license"), files=files,
                     supporting_metadata=((file_url, file_raw),))
    if seed.provider == "tudatalib":
        host = "tudatalib.ulb.tu-darmstadt.de"
        if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                            seed.identifier):
            raise ValueError("TUdatalib item identifier must be a UUID")
        url = f"https://{host}/server/api/core/items/{seed.identifier}"
        raw = read_url(url, allowed_host=host)
        item = json.loads(raw)
        if item.get("uuid") != seed.identifier:
            raise ValueError("TUdatalib item UUID does not match the requested seed")
        links = item.get("_links", {})
        bundle_url = _tudatalib_api_url(urljoin(url, links.get("bundles", {}).get("href", "")))
        bundle_raw = read_url(bundle_url, allowed_host=host)
        bundle_data = json.loads(bundle_raw)
        bundles = bundle_data.get("_embedded", {}).get("bundles", [])
        originals = [bundle for bundle in bundles
                     if isinstance(bundle, dict) and bundle.get("name") == "ORIGINAL"]
        if len(originals) != 1:
            raise ValueError("TUdatalib item must expose exactly one ORIGINAL bundle")
        bitstream_url = _tudatalib_api_url(
            urljoin(bundle_url, originals[0].get("_links", {}).get("bitstreams", {}).get("href", "")))
        bitstream_raw = read_url(bitstream_url, allowed_host=host)
        bitstream_data = json.loads(bitstream_raw)
        bitstreams = bitstream_data.get("_embedded", {}).get("bitstreams", [])
        if not isinstance(bitstreams, list) or not bitstreams:
            raise ValueError("TUdatalib ORIGINAL bundle has no bitstreams")
        files = []
        for stream in bitstreams:
            if not isinstance(stream, dict):
                raise ValueError("TUdatalib bitstream metadata entry is malformed")
            name = stream.get("name")
            size = stream.get("sizeBytes")
            checksum = stream.get("checkSum")
            if (not isinstance(name, str) or not name.strip() or "/" in name or "\\" in name
                    or isinstance(size, bool) or not isinstance(size, int) or size <= 0
                    or not isinstance(checksum, dict)):
                raise ValueError("TUdatalib bitstream name, size or checksum metadata is invalid")
            algorithm, digest = _checksum({"type": checksum.get("checkSumAlgorithm", ""),
                                           "value": checksum.get("value", "")})
            if algorithm != "md5" or not re.fullmatch(r"[0-9a-f]{32}", digest):
                raise ValueError("TUdatalib bitstreams require publisher MD5 checksums")
            content_url = _tudatalib_api_url(
                urljoin(bitstream_url, stream.get("_links", {}).get("content", {}).get("href", "")))
            files.append(RemoteFile(name, content_url, size, algorithm, digest))
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("TUdatalib item metadata map is missing")
        uri_entries = metadata.get("dc.identifier.uri", [])
        if isinstance(uri_entries, dict):
            uri_entries = [uri_entries]
        if not isinstance(uri_entries, list):
            raise ValueError("TUdatalib identifier URI metadata is malformed")
        doi_values = []
        for entry in uri_entries:
            value = entry.get("value") if isinstance(entry, dict) else None
            if not isinstance(value, str):
                continue
            parsed_uri = urlparse(value.strip())
            if parsed_uri.scheme == "https" and parsed_uri.hostname == "doi.org":
                candidate = parsed_uri.path.lstrip("/")
                if candidate and not parsed_uri.query and not parsed_uri.fragment:
                    doi_values.append(candidate)
        if len(doi_values) > 1:
            raise ValueError("TUdatalib item exposes ambiguous dataset DOI identifiers")
        doi = doi_values[0] if doi_values else ""
        if doi != seed.identifier:
            raise ValueError("TUdatalib item DOI does not match the curated dataset identity")
        title = _tudatalib_metadata_value(metadata, "dc.title")
        issued = _tudatalib_metadata_value(metadata, "dc.date.issued")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", issued):
            raise ValueError("TUdatalib release date must be an ISO calendar date")
        license_value = _tudatalib_metadata_value(metadata, "dc.rights.license")
        if _license(license_value)[0] not in {"CC-BY-4.0", "CC0-1.0", "etalab-2.0"}:
            raise ValueError("TUdatalib dataset license is unresolved or outside acquisition policy")
        return _make(seed, url, raw, title=title, doi=doi, version=issued,
                     authors=_tudatalib_authors(metadata), license_value=license_value,
                     files=files, supporting_metadata=((bundle_url, bundle_raw),
                                                       (bitstream_url, bitstream_raw)),
                     source_updated_at=issued)
    if seed.provider == "mendeley":
        identifier, version = seed.identifier.split("/", 1)
        url = f"https://data.mendeley.com/public-api/datasets/{identifier}/snapshot/{version}"
        raw = read_url(url)
        data = json.loads(raw)
        files, supporting, offset = [], [], 0
        while True:
            file_url = (f"https://data.mendeley.com/public-api/datasets/{identifier}/files?"
                        f"folder_id=root&version={version}&$start={offset}&$limit=1000")
            file_raw = read_url(file_url, headers={
                "Accept": "application/vnd.mendeley-public-dataset.1+json"})
            listing = json.loads(file_raw)
            if not isinstance(listing, list):
                raise ValueError("Mendeley did not return a public root-file listing")
            supporting.append((file_url, file_raw))
            for x in listing:
                if x.get("status") != "COMPLETED":
                    continue
                content = x["content_details"]
                checksum = content.get("sha256_hash", "")
                files.append(RemoteFile(x["filename"], content["download_url"], content["size"],
                                        "sha256" if checksum else "", checksum))
            if len(listing) < 1000:
                break
            offset += 1000
        return _make(seed, url, raw, title=data["name"], doi=data.get("doi", ""),
                     version=str(data["version"]), authors=[
                         " ".join(filter(None, [a.get("first_name"), a.get("last_name")]))
                         for a in data.get("contributors", [])],
                     license_value=data.get("licence"), files=files,
                     supporting_metadata=supporting)
    if seed.provider == "openei":
        url = "https://data.openei.org/submissions/" + seed.identifier
        raw = read_url(url)
        records = []
        pattern = r'<script[^>]+type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>'
        for block in re.findall(pattern, raw.decode("utf-8"), re.S):
            record = json.loads(block)
            if isinstance(record, dict) and record.get("@type") == "Dataset":
                records.append(record)
        if len(records) != 1:
            raise ValueError("Exactly one structured repository Dataset record is required")
        data = records[0]
        files = []
        for item in data.get("distribution", []):
            resource = item.get("contentUrl", "")
            if not isinstance(resource, str):
                raise ValueError("OpenEI distribution contentUrl must be text")
            if not resource.endswith((".zip", ".csv", ".txt", ".docx", ".xlsx")):
                continue
            size = head_content_length(resource)
            files.append(RemoteFile(unquote(urlparse(resource).path.rsplit("/", 1)[-1]),
                                    resource, size))
        return _make(seed, url, raw, title=data["name"], doi="", version=data["datePublished"],
                     authors=[a["name"] for a in data.get("creator", [])],
                     license_value=data.get("license"), files=files)
    raise ValueError(f"Unsupported repository provider: {seed.provider}")
