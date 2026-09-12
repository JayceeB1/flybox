"""Canonical serialization and scientific configuration hashing."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

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


class CanonicalConfigError(ValueError):
    """Raised when a profile cannot be represented canonically."""


def merge_defaults(defaults: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively apply defaults while letting explicit config win."""

    merged: dict[str, Any] = {}
    for key, value in defaults.items():
        merged[key] = value
    for key, value in config.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = merge_defaults(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged


def _canonicalize(value: Any, path: str = "$") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalConfigError(f"{path}: non-finite numbers are not allowed")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key in sorted(value):
            if not isinstance(raw_key, str) or not raw_key:
                raise CanonicalConfigError(f"{path}: mapping keys must be non-empty strings")
            child = value[raw_key]
            child_path = f"{path}.{raw_key}"
            if raw_key in _BIOLOGICAL_ID_KEYS:
                items: Sequence[Any]
                if isinstance(child, Sequence) and not isinstance(child, (str, bytes, bytearray)):
                    items = child
                else:
                    items = (child,)
                for index, item in enumerate(items):
                    item_path = child_path if len(items) == 1 else f"{child_path}[{index}]"
                    if not isinstance(item, str) or not item.isascii() or not item.isdecimal():
                        raise CanonicalConfigError(
                            f"{item_path}: biological IDs must be decimal strings"
                        )
            result[raw_key] = _canonicalize(child, child_path)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_canonicalize(item, f"{path}[{index}]") for index, item in enumerate(value)]
    raise CanonicalConfigError(f"{path}: unsupported configuration value {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Return deterministic JSON for one resolved scientific configuration."""

    canonical = _canonicalize(value)
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(value: Any) -> str:
    """SHA-256 over canonical UTF-8 JSON."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
