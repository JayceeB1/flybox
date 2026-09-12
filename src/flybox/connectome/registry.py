"""Typed dataset registry adapter over FlyBox immutable profiles."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flybox.config import ProfileKind, ProfileRegistry
from flybox.provenance.licenses import validate_license_id

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DATASET_KEYS = {
    "release",
    "license_id",
    "source_page",
    "source_checked",
    "attribution",
    "files",
}
_FILE_KEYS = {"filename", "url", "expected_sha256", "expected_bytes"}


class DatasetRegistryError(ValueError):
    """Raised when a dataset profile is malformed or scientifically ambiguous."""


@dataclass(frozen=True, slots=True)
class DatasetFileSpec:
    key: str
    filename: str
    url: str
    expected_sha256: str | None
    expected_bytes: int | None

    @property
    def pinned(self) -> bool:
        return self.expected_sha256 is not None and self.expected_bytes is not None


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    id: str
    profile_hash: str
    release: str
    license_id: str
    source_page: str
    source_checked: str
    attribution: str
    files: tuple[DatasetFileSpec, ...]

    @property
    def fully_pinned(self) -> bool:
        return all(item.pinned for item in self.files)


def _nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DatasetRegistryError(f"{path}: expected non-empty string")
    return value.strip()


def _optional_sha256(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise DatasetRegistryError(f"{path}: expected lowercase 64-character SHA-256 or null")
    return value


def _optional_bytes(value: Any, path: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DatasetRegistryError(f"{path}: expected non-negative integer or null")
    return value


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DatasetRegistryError(f"{path}: expected mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise DatasetRegistryError(f"{path}: keys must be non-empty strings")
    return value


def load_dataset_spec(config_root: Path, profile_id: str) -> DatasetSpec:
    """Resolve one dataset profile into a strict acquisition contract."""

    resolved = ProfileRegistry.from_directory(config_root).resolve(profile_id)
    if resolved.kind is not ProfileKind.DATASET:
        raise DatasetRegistryError(
            f"profile {profile_id!r} has kind {resolved.kind.value!r}, expected 'dataset'"
        )

    config = _mapping(resolved.config, f"profile:{profile_id}.config")
    unknown = sorted(set(config) - _DATASET_KEYS)
    if unknown:
        raise DatasetRegistryError(
            f"profile:{profile_id}.config: unknown keys: {', '.join(unknown)}"
        )

    release = _nonempty_string(config.get("release"), "config.release")
    license_id = validate_license_id(
        _nonempty_string(config.get("license_id"), "config.license_id")
    )
    source_page = _nonempty_string(config.get("source_page"), "config.source_page")
    source_checked = _nonempty_string(config.get("source_checked"), "config.source_checked")
    attribution = _nonempty_string(config.get("attribution"), "config.attribution")

    files_raw = _mapping(config.get("files"), "config.files")
    if not files_raw:
        raise DatasetRegistryError("config.files: at least one file is required")

    files: list[DatasetFileSpec] = []
    for key in sorted(files_raw):
        raw = _mapping(files_raw[key], f"config.files.{key}")
        unknown_file_keys = sorted(set(raw) - _FILE_KEYS)
        if unknown_file_keys:
            raise DatasetRegistryError(
                f"config.files.{key}: unknown keys: {', '.join(unknown_file_keys)}"
            )
        files.append(
            DatasetFileSpec(
                key=key,
                filename=_nonempty_string(raw.get("filename"), f"config.files.{key}.filename"),
                url=_nonempty_string(raw.get("url"), f"config.files.{key}.url"),
                expected_sha256=_optional_sha256(
                    raw.get("expected_sha256"),
                    f"config.files.{key}.expected_sha256",
                ),
                expected_bytes=_optional_bytes(
                    raw.get("expected_bytes"),
                    f"config.files.{key}.expected_bytes",
                ),
            )
        )

    filenames = [item.filename for item in files]
    if len(filenames) != len(set(filenames)):
        raise DatasetRegistryError("config.files: filenames must be unique")

    for item in files:
        if (item.expected_sha256 is None) != (item.expected_bytes is None):
            raise DatasetRegistryError(
                f"config.files.{item.key}: expected_sha256 and expected_bytes must be pinned together"
            )

    return DatasetSpec(
        id=resolved.id,
        profile_hash=resolved.profile_hash,
        release=release,
        license_id=license_id,
        source_page=source_page,
        source_checked=source_checked,
        attribution=attribution,
        files=tuple(files),
    )
