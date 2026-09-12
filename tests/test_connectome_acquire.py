from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from flybox.connectome.acquire import AcquisitionError, acquire_dataset
from flybox.connectome.registry import DatasetRegistryError, load_dataset_spec
from flybox.provenance.schema import validate_manifest


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_dataset_profile(
    root: Path,
    files: dict[str, bytes],
    *,
    pinned: bool,
    corrupt_expected_hash: bool = False,
) -> Path:
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
        expected_hash = f'"{expected}"' if pinned else "null"
        expected_bytes = str(len(payload)) if pinned else "null"
        lines.extend(
            [
                f"    {key}:",
                f"      filename: {key}.bin",
                f"      url: https://fixture.invalid/{key}.bin",
                f"      expected_sha256: {expected_hash}",
                f"      expected_bytes: {expected_bytes}",
            ]
        )
    path = root / "datasets" / "fixture.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class FixtureOpener:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.calls: list[str] = []

    def __call__(self, url: str) -> io.BytesIO:
        self.calls.append(url)
        name = url.rsplit("/", 1)[-1].removesuffix(".bin")
        return io.BytesIO(self.files[name])


class InterruptingStream:
    def __init__(self) -> None:
        self.reads = 0
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        del size
        self.reads += 1
        if self.reads == 1:
            return b"partial"
        raise ConnectionError("simulated network interruption")

    def close(self) -> None:
        self.closed = True


def test_pinned_download_writes_valid_manifest_and_reuses_verified_cache(
    tmp_path: Path,
) -> None:
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


def test_network_interruption_fails_closed_and_removes_partial(tmp_path: Path) -> None:
    files = {"annotations": b"complete-content"}
    config = tmp_path / "config"
    data = tmp_path / "data"
    write_dataset_profile(config, files, pinned=True)
    spec = load_dataset_spec(config, "fixture_dataset")
    stream = InterruptingStream()

    with pytest.raises(AcquisitionError, match="download failed"):
        acquire_dataset(
            spec,
            data,
            code_revision="deadbeef",
            opener=lambda _url: stream,
        )

    raw = data / "fixture_dataset" / "raw"
    assert stream.closed
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


def test_unpinned_profile_requires_explicit_bootstrap_and_emits_candidate(
    tmp_path: Path,
) -> None:
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


def test_registry_rejects_non_https_source_url(tmp_path: Path) -> None:
    config = tmp_path / "config"
    path = write_dataset_profile(config, {"annotations": b"abc"}, pinned=True)
    text = path.read_text(encoding="utf-8").replace(
        "https://fixture.invalid/annotations.bin",
        "file:///tmp/annotations.bin",
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DatasetRegistryError, match="absolute HTTPS URL"):
        load_dataset_spec(config, "fixture_dataset")


def test_registry_rejects_path_traversal_filename(tmp_path: Path) -> None:
    config = tmp_path / "config"
    path = write_dataset_profile(config, {"annotations": b"abc"}, pinned=True)
    text = path.read_text(encoding="utf-8").replace(
        "filename: annotations.bin",
        "filename: ../../escape.bin",
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DatasetRegistryError, match="expected a basename"):
        load_dataset_spec(config, "fixture_dataset")


def test_official_malecns_profile_has_reviewed_v1_source_locks() -> None:
    spec = load_dataset_spec(Path("config"), "malecns_v1")
    assert spec.release == "MaleCNS v1.0"
    assert spec.license_id == "CC-BY-4.0"
    assert spec.source_page == "https://male-cns.janelia.org/download/"
    assert spec.fully_pinned

    by_key = {item.key: item for item in spec.files}
    assert set(by_key) == {"annotations", "neurotransmitters", "edges"}
    assert all(
        "/flyem-male-cns/v1.0/connectome-data/flat-connectome/" in item.url
        for item in spec.files
    )
    assert by_key["annotations"].expected_sha256 == (
        "2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2"
    )
    assert by_key["annotations"].expected_bytes == 14483314
    assert by_key["neurotransmitters"].expected_sha256 == (
        "95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621"
    )
    assert by_key["neurotransmitters"].expected_bytes == 43282834
    assert by_key["edges"].expected_sha256 == (
        "e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1"
    )
    assert by_key["edges"].expected_bytes == 1051241946
