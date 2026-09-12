"""Fail-closed scientific provenance validation.

The validator is intentionally dependency-light so provenance checks can run in
bootstrap CI before heavy scientific dependencies are installed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from flybox.contracts import EvidenceClass

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BIOLOGICAL_ID_KEYS = {
    "biological_id",
    "biological_ids",
    "body_id",
    "body_ids",
    "neuron_id",
    "neuron_ids",
    "source_id",
    "source_ids",
    "target_id",
    "target_ids",
}
_ALLOWED_SCHEMA_IDS = {
    "flybox.provenance/v1",
    "flybox.dataset-manifest/v1",
    "flybox.run-manifest/v1",
}


@dataclass(frozen=True, slots=True)
class ProvenanceError(ValueError):
    """One or more provenance invariants were violated."""

    errors: tuple[str, ...]

    def __str__(self) -> str:
        return "invalid provenance manifest:\n- " + "\n- ".join(self.errors)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_string(data: Mapping[str, Any], key: str, path: str, errors: list[str]) -> None:
    if not _is_nonempty_string(data.get(key)):
        errors.append(f"{path}.{key}: required non-empty string")


def _validate_sha256(value: Any, path: str, errors: list[str], *, required: bool) -> None:
    if value is None and not required:
        return
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        errors.append(f"{path}: expected lowercase 64-character SHA-256")


def _walk_biological_ids(value: Any, path: str, errors: list[str]) -> None:
    """Reject JSON-number representations for fields that carry biological IDs."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in _BIOLOGICAL_ID_KEYS:
                values: Sequence[Any]
                if isinstance(child, Sequence) and not isinstance(child, (str, bytes, bytearray)):
                    values = child
                else:
                    values = (child,)
                for index, item in enumerate(values):
                    item_path = child_path if len(values) == 1 else f"{child_path}[{index}]"
                    if not isinstance(item, str) or not item.isascii() or not item.isdecimal():
                        errors.append(
                            f"{item_path}: biological IDs must be decimal strings, never JSON numbers"
                        )
            _walk_biological_ids(child, child_path, errors)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _walk_biological_ids(child, f"{path}[{index}]", errors)


def _validate_component(data: Mapping[str, Any], errors: list[str]) -> None:
    path = "$"
    for key in ("id", "kind", "version", "evidence", "license_id", "code_revision"):
        _require_string(data, key, path, errors)

    evidence = data.get("evidence")
    if isinstance(evidence, str) and evidence not in {item.value for item in EvidenceClass}:
        errors.append(f"$.evidence: unknown evidence class {evidence!r}")

    source = data.get("source")
    if source is not None:
        if not isinstance(source, Mapping):
            errors.append("$.source: expected object")
        else:
            _require_string(source, "project", "$.source", errors)
            if "release" in source and source["release"] is not None:
                _require_string(source, "release", "$.source", errors)
            locators = source.get("locators", [])
            if not isinstance(locators, list) or any(not _is_nonempty_string(v) for v in locators):
                errors.append("$.source.locators: expected array of non-empty strings")

    inclusion_state = data.get("inclusion_state")
    if inclusion_state is not None and inclusion_state not in {
        "dependency",
        "data",
        "adapted-code",
        "reference-only",
        "tooling",
        "original",
        "derived",
    }:
        errors.append(f"$.inclusion_state: unsupported value {inclusion_state!r}")

    if inclusion_state == "adapted-code":
        adapted = data.get("adapted_from")
        if not isinstance(adapted, Mapping):
            errors.append("$.adapted_from: required object for adapted-code")
        else:
            for key in ("project", "revision", "license_id", "notice_path"):
                _require_string(adapted, key, "$.adapted_from", errors)
            source_files = adapted.get("source_files")
            if not isinstance(source_files, list) or not source_files or any(
                not _is_nonempty_string(v) for v in source_files
            ):
                errors.append("$.adapted_from.source_files: required non-empty string array")

    if data.get("evidence") == EvidenceClass.DERIVED.value or inclusion_state == "derived":
        parents = data.get("derived_from")
        if not isinstance(parents, list) or not parents or any(
            not _is_nonempty_string(v) for v in parents
        ):
            errors.append("$.derived_from: derived artifacts require at least one source manifest ID")

    if "sha256" in data:
        _validate_sha256(data.get("sha256"), "$.sha256", errors, required=False)


def _validate_dataset(data: Mapping[str, Any], errors: list[str]) -> None:
    for key in ("id", "release", "license_id", "retrieved_at", "code_revision"):
        _require_string(data, key, "$", errors)

    files = data.get("files")
    if not isinstance(files, list) or not files:
        errors.append("$.files: expected at least one source file")
        return
    for index, item in enumerate(files):
        path = f"$.files[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{path}: expected object")
            continue
        for key in ("name", "url", "license_id"):
            _require_string(item, key, path, errors)
        if not isinstance(item.get("bytes"), int) or isinstance(item.get("bytes"), bool) or item["bytes"] < 0:
            errors.append(f"{path}.bytes: expected non-negative integer")
        _validate_sha256(item.get("sha256"), f"{path}.sha256", errors, required=True)


def _validate_run(data: Mapping[str, Any], errors: list[str]) -> None:
    for key in ("run_id", "code_revision", "configuration_hash"):
        _require_string(data, key, "$", errors)
    _validate_sha256(data.get("configuration_hash"), "$.configuration_hash", errors, required=True)

    components = data.get("components")
    if not isinstance(components, list) or not components:
        errors.append("$.components: expected at least one provenance component ID")
    elif any(not _is_nonempty_string(v) for v in components):
        errors.append("$.components: component IDs must be non-empty strings")


def validate_manifest(data: Mapping[str, Any]) -> None:
    """Validate one FlyBox provenance/dataset/run manifest or raise ProvenanceError."""

    errors: list[str] = []
    schema = data.get("schema")
    if schema not in _ALLOWED_SCHEMA_IDS:
        errors.append(f"$.schema: unsupported or missing schema identifier {schema!r}")
    elif schema == "flybox.provenance/v1":
        _validate_component(data, errors)
    elif schema == "flybox.dataset-manifest/v1":
        _validate_dataset(data, errors)
    elif schema == "flybox.run-manifest/v1":
        _validate_run(data, errors)

    _walk_biological_ids(data, "$", errors)
    if errors:
        raise ProvenanceError(tuple(errors))
