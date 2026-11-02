"""Byte-pinned deltas reconstruct through the actual remote apply program."""

import hashlib
import json
import shutil
import subprocess
import tarfile

import pytest

from h2physics.cluster_validation import source_manifest, verify_source_manifest
from scripts.prepare_hangang_delta import prepare_delta
from scripts.transfer_apply_hangang_delta import _apply_code


def _git(root, *arguments):
    return subprocess.run(
        ["git", "-C", str(root), *arguments], check=True, capture_output=True,
    ).stdout.decode().strip()


def _repositories(tmp_path):
    work = tmp_path / "work"
    base = tmp_path / "base"
    work.mkdir()
    base.mkdir()
    _git(work, "init", "--quiet")
    for name, value in {"keep.txt": "unchanged", "edit.txt": "before", "gone.txt": "delete"}.items():
        (work / name).write_text(value, encoding="utf-8")
        shutil.copyfile(work / name, base / name)
    _git(work, "add", "--all")
    _git(work, "-c", "user.name=Delta Test", "-c", "user.email=delta@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath="+str(tmp_path / "empty-hooks"),
         "commit", "--quiet", "-m", "authored fixture")
    revision = _git(work, "rev-parse", "HEAD")
    (base / "SOURCE_REVISION.txt").write_text(revision+"\n", encoding="utf-8")
    (base / "SOURCE_MANIFEST.sha256").write_bytes(source_manifest(base))
    return work, base


def test_delta_reconstructs_changed_added_deleted_and_unchanged_bytes(tmp_path):
    work, base = _repositories(tmp_path)
    (work / "edit.txt").write_text("after", encoding="utf-8")
    (work / "new.py").write_text("answer = 42\n", encoding="utf-8")
    (work / "gone.txt").unlink()
    _git(work, "add", "--all")
    receipt = prepare_delta(base, work, tmp_path / "package")
    archive = tmp_path / "package" / "delta.tar.gz"
    with tarfile.open(archive) as bundle:
        metadata = json.load(bundle.extractfile("delta/metadata.json"))
        assert set(metadata["changed"]) == {"edit.txt", "new.py"}
        assert metadata["deleted"] == ["gone.txt"]
        assert "delta/files/keep.txt" not in bundle.getnames()
    assert receipt["changed_files"] == 2 and receipt["deleted_files"] == 1
    restored = tmp_path / "restored"
    exec(_apply_code(str(base), str(restored), str(archive), receipt["archive_sha256"]), {})
    assert (restored / "keep.txt").read_bytes() == b"unchanged"
    assert (restored / "edit.txt").read_bytes() == b"after"
    assert (restored / "new.py").read_bytes() == (work / "new.py").read_bytes()
    assert not (restored / "gone.txt").exists()
    assert source_manifest(restored) == source_manifest(work)
    assert hashlib.sha256(source_manifest(restored)).hexdigest() == receipt["target_manifest_sha256"]
    repeated = prepare_delta(base, work, tmp_path / "repeated")
    assert repeated["archive_sha256"] == receipt["archive_sha256"]


def test_changed_base_is_rejected_before_any_delta_is_published(tmp_path):
    work, base = _repositories(tmp_path)
    (base / "keep.txt").write_text("changed outside the pin", encoding="utf-8")
    output = tmp_path / "package"
    with pytest.raises(ValueError, match="Pinned source file changed"):
        prepare_delta(base, work, output)
    assert not output.exists()


def test_bytes_changed_after_initial_audit_are_checked_again(tmp_path, monkeypatch):
    from scripts import prepare_hangang_worktree_snapshot as snapshot

    work, base = _repositories(tmp_path)
    original = snapshot._safe_worktree_paths

    def changed_after_audit(root):
        paths = original(root)
        (root / "edit.txt").write_bytes(b"ghp_" + b"X"*36)
        return paths

    monkeypatch.setattr(snapshot, "_safe_worktree_paths", changed_after_audit)
    output = tmp_path / "package"
    with pytest.raises(ValueError, match="Captured source hygiene failed"):
        prepare_delta(base, work, output)
    assert not output.exists()


def test_admitted_runtime_path_is_excluded_like_worker_manifest(tmp_path):
    work, base = _repositories(tmp_path)
    runtime = work / "venv"
    runtime.mkdir()
    (runtime / "README.md").write_text("runtime-only fixture", encoding="utf-8")
    _git(work, "add", "--all")
    receipt = prepare_delta(base, work, tmp_path / "package")
    archive = tmp_path / "package" / "delta.tar.gz"
    restored = tmp_path / "restored"
    exec(_apply_code(str(base), str(restored), str(archive), receipt["archive_sha256"]), {})
    verify_source_manifest(restored, receipt["target_revision"], receipt["target_manifest_sha256"])
    assert not (restored / "venv").exists()
    assert source_manifest(restored) == source_manifest(work)
