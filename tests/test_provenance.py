from __future__ import annotations

import json
from pathlib import Path

import pytest

from flybox.provenance.licenses import validate_license_id
from flybox.provenance.schema import ProvenanceError, validate_manifest
from flybox.provenance.validate import validate_path

FIXTURES = Path(__file__).parent / "fixtures" / "provenance"
HEX64 = "a" * 64


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_valid_component_fixture_passes() -> None:
    validate_manifest(load_fixture("valid_component.json"))
    validate_path(FIXTURES / "valid_component.json")


def test_numeric_biological_id_fails_closed() -> None:
    with pytest.raises(ProvenanceError, match="biological IDs must be decimal strings"):
        validate_manifest(load_fixture("invalid_numeric_id.json"))


def test_adapted_code_requires_exact_revision_license_and_notice() -> None:
    with pytest.raises(ProvenanceError) as exc:
        validate_manifest(load_fixture("invalid_adapted_code.json"))
    message = str(exc.value)
    assert "revision" in message
    assert "license_id" in message
    assert "notice_path" in message


def test_unknown_evidence_class_fails() -> None:
    data = load_fixture("valid_component.json")
    data["evidence"] = "probably-real"
    with pytest.raises(ProvenanceError, match="unknown evidence class"):
        validate_manifest(data)


def test_derived_component_requires_lineage() -> None:
    data = load_fixture("valid_component.json")
    data["evidence"] = "derived"
    data["inclusion_state"] = "derived"
    with pytest.raises(ProvenanceError, match="derived artifacts require"):
        validate_manifest(data)


def test_dataset_manifest_requires_source_hashes() -> None:
    manifest: dict[str, object] = {
        "schema": "flybox.dataset-manifest/v1",
        "id": "malecns_v1",
        "release": "MaleCNS v1.0",
        "license_id": "CC-BY-4.0",
        "retrieved_at": "2026-09-12T00:00:00Z",
        "code_revision": "deadbeef",
        "files": [
            {
                "name": "annotations.feather",
                "url": "https://example.invalid/annotations.feather",
                "bytes": 123,
                "sha256": HEX64,
                "license_id": "CC-BY-4.0",
            }
        ],
    }
    validate_manifest(manifest)
    source_file = manifest["files"]
    assert isinstance(source_file, list)
    assert isinstance(source_file[0], dict)
    source_file[0]["sha256"] = "not-a-hash"
    with pytest.raises(ProvenanceError, match="SHA-256"):
        validate_manifest(manifest)


def test_run_manifest_requires_configuration_hash_and_components() -> None:
    manifest: dict[str, object] = {
        "schema": "flybox.run-manifest/v1",
        "run_id": "run-001",
        "code_revision": "deadbeef",
        "configuration_hash": HEX64,
        "components": ["dataset:malecns_v1", "brain:lif-v0"],
    }
    validate_manifest(manifest)
    manifest["components"] = []
    with pytest.raises(ProvenanceError, match="at least one provenance component"):
        validate_manifest(manifest)


def test_license_identifier_rejects_whitespace_and_expressions() -> None:
    assert validate_license_id("Apache-2.0") == "Apache-2.0"
    with pytest.raises(ValueError):
        validate_license_id("Apache-2.0 OR MIT")
