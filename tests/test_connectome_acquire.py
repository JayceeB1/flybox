from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from flybox.connectome.acquire import AcquisitionError, acquire_dataset
from flybox.connectome.registry import load_dataset_spec
from flybox.provenance.schema import validate_manifest


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_dataset_profile(
    root: Path,
    files: dict[str, bytes],
    *,
    pinned: bool,
    corrupt_expected_hash: bool = False,
) -> None:
    lines = [
        "schema: flybox.profile/v1",
        "kind: dataset",
        "id: fixture_dataset",
        'version: "1"',
        "config:",
        "  release: Fixture v1",
        "  license_id: CC-BY-4.0",
        "  source_page: https://example.invalid/download/",
        '  source_checked: "2026-09-12"',
        "  attribution: Fixture authors",
        "  files:",
    ]
    for index, (key, payload) in enumerate(files.items()):
        expected = digest(payload)
        if corrupt_expected_hash and index == 0:
            expected = "0" * 64
        lines.extend(
            [
                f"    {key}:",
                f"      filename: {key}.bin",
                f"      url: https://fixture.invalid/{key}.bin",
                f"      expected_sha256: {expected if pinned else 'null'}",
                f"      expected_bytes: {len(payload) if pinned else 'null'}",
            ]
        )
    path = root / "datasets" / "fixture.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class FixtureOpener:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.calls: list[str] = []

    def __call__(self, url: str) -> io.BytesIO:
        self.calls.append(url)
        name = url.rsplit("/", 1)[-1].removesuffix(".bin")
        return io.BytesIO(self.files[name])


def test_pinned_download_writes_valid_manifest_and_reuses_verified_cache(tmp_path: Path) -> None:
    files = {"annotations": b"abc", "edges": b"defgh"}
    config = tmp_path / "config"
    data = tmp_path / "data"
    write_dataset_profile(config, files, pinned=True)
    spec = load_dataset_spec(config, "fixture_dataset")
    opener = FixtureOpener(files)

    manifest = acquire_dataset(spec, data, code_revision="deadbeef", opener=opener)
    validate_manifest(manifest)
    assert len(opener.calls) == 2
    manifest_path = data / "fixture_dataset" / "source-manifest.json"
    assert manifest_path.exists()
    assert not manifest_path.with_suffix(".json.partial").exists()

    class NoNetwork:
        def __call__(self, url: str) -> io.BytesIO:
            raise AssertionError(f"network should not be used for verified cache: {url}")

    cached = acquire_dataset(spec, data, code_revision="deadbeef", opener=NoNetwork())
    assert cached["files"] == manifest["files"]


def test_download_hash_mismatch_fails_and_removes_partial(tmp_path: Path) -> None:
    files = {"annotations": b"abc"}
    config = tmp_path / "config"
    data = tmp_path / "data"
    write_dataset_profile(config, files, pinned=True, corrupt_expected_hash=True)
    spec = load_dataset_spec(config, "fixture_dataset")

    with pytest.raises(AcquisitionError, match="SHA-256 mismatch"):
        acquire_dataset(spec, data, code_revision="deadbeef", opener=FixtureOpener(files))

    raw = data / "fixture_dataset" / "raw"
    assert not (raw / "annotations.bin").exists()
    assert not (raw / "annotations.bin.partial").exists()


def test_corrupt_cached_file_is_rejected_without_redownload(tmp_path: Path) -> None:
    files = {"annotations": b"abc"}
    config = tmp_path / "config"
    data = tmp_path / "data"
    write_dataset_profile(config, files, pinned=True)
    spec = load_dataset_spec(config, "fixture_dataset")
    target = data / "fixture_dataset" / "raw" / "annotations.bin"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"corrupt")

    with pytest.raises(AcquisitionError, match="cached file mismatch"):
        acquire_dataset(spec, data, code_revision="deadbeef", opener=FixtureOpener(files))


def test_verify_only_requires_existing_files(tmp_path: Path) -> None:
    files = {"annotations": b"abc"}
    config = tmp_path / "config"
    write_dataset_profile(config, files, pinned=True)
    spec = load_dataset_spec(config, "fixture_dataset")

    with pytest.raises(AcquisitionError, match="missing required file"):
        acquire_dataset(
            spec,
            tmp_path / "data",
            code_revision="deadbeef",
            verify_only=True,
            opener=FixtureOpener(files),
        )


def test_unpinned_profile_requires_explicit_bootstrap_and_emits_candidate(tmp_path: Path) -> None:
    files = {"annotations": b"abc", "edges": b"xyz"}
    config = tmp_path / "config"
    data = tmp_path / "data"
    write_dataset_profile(config, files, pinned=False)
    spec = load_dataset_spec(config, "fixture_dataset")
    assert not spec.fully_pinned

    with pytest.raises(AcquisitionError, match="not fully pinned"):
        acquire_dataset(spec, data, code_revision="deadbeef", opener=FixtureOpener(files))

    manifest = acquire_dataset(
        spec,
        data,
        code_revision="deadbeef",
        bootstrap_hashes=True,
        opener=FixtureOpener(files),
    )
    validate_manifest(manifest)
    candidate_path = data / "fixture_dataset" / "bootstrap-lock-candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert candidate["status"] == "UNREVIEWED_BOOTSTRAP_CANDIDATE"
    assert candidate["files"]["annotations"]["expected_sha256"] == digest(b"abc")
    assert candidate["files"]["edges"]["expected_bytes"] == 3


def test_bootstrap_and_verify_only_are_mutually_exclusive(tmp_path: Path) -> None:
    files = {"annotations": b"abc"}
    config = tmp_path / "config"
    write_dataset_profile(config, files, pinned=False)
    spec = load_dataset_spec(config, "fixture_dataset")
    with pytest.raises(AcquisitionError, match="mutually exclusive"):
        acquire_dataset(
            spec,
            tmp_path / "data",
            code_revision="deadbeef",
            verify_only=True,
            bootstrap_hashes=True,
            opener=FixtureOpener(files),
        )


def test_official_malecns_profile_uses_reviewed_v1_sources() -> None:
    spec = load_dataset_spec(Path("config"), "malecns_v1")
    assert spec.release == "MaleCNS v1.0"
    assert spec.license_id == "CC-BY-4.0"
    assert spec.source_page == "https://male-cns.janelia.org/download/"
    assert {item.key for item in spec.files} == {"annotations", "neurotransmitters", "edges"}
    assert all("/flyem-male-cns/v1.0/connectome-data/flat-connectome/" in item.url for item in spec.files)
    assert not spec.fully_pinned
