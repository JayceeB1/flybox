"""Strict, versioned FlyBox configuration profile registry."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from .canonical import canonical_hash, merge_defaults
from .models import Profile, ProfileKind, ResolvedProfile, ResolvedReference

_PROFILE_SCHEMA = "flybox.profile/v1"
_ALLOWED_KEYS = {"schema", "kind", "id", "version", "defaults", "config", "references"}


class ProfileRegistryError(ValueError):
    """Raised when profile discovery or resolution fails."""


def _string_mapping(value: Any, path: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ProfileRegistryError(f"{path}: expected mapping")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise ProfileRegistryError(f"{path}: reference names must be non-empty strings")
        if not isinstance(item, str) or not item:
            raise ProfileRegistryError(f"{path}.{key}: profile reference must be a string ID")
        result[key] = item
    return result


def _object_mapping(value: Any, path: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ProfileRegistryError(f"{path}: expected mapping")
    result: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise ProfileRegistryError(f"{path}: keys must be non-empty strings")
        result[key] = item
    return result


def load_profile(path: Path) -> Profile:
    """Load one strict YAML profile."""

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ProfileRegistryError(f"{path}: unable to load profile: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise ProfileRegistryError(f"{path}: profile must be a mapping")

    unknown = sorted(set(raw) - _ALLOWED_KEYS)
    if unknown:
        message = ", ".join(map(str, unknown))
        raise ProfileRegistryError(f"{path}: unknown top-level keys: {message}")

    if raw.get("schema") != _PROFILE_SCHEMA:
        raise ProfileRegistryError(f"{path}: schema must be {_PROFILE_SCHEMA!r}")

    profile_id = raw.get("id")
    version = raw.get("version")
    if not isinstance(profile_id, str) or not profile_id:
        raise ProfileRegistryError(f"{path}: id must be a non-empty string")
    if not isinstance(version, str) or not version:
        raise ProfileRegistryError(f"{path}: version must be a non-empty string")

    try:
        kind = ProfileKind(raw.get("kind"))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ProfileKind)
        raise ProfileRegistryError(f"{path}: kind must be one of {allowed}") from exc

    return Profile(
        schema=_PROFILE_SCHEMA,
        kind=kind,
        id=profile_id,
        version=version,
        defaults=_object_mapping(raw.get("defaults"), f"{path}.defaults"),
        config=_object_mapping(raw.get("config"), f"{path}.config"),
        references=_string_mapping(raw.get("references"), f"{path}.references"),
        source_path=path,
    )


class ProfileRegistry:
    """Collection of named profiles with deterministic recursive resolution."""

    def __init__(self, profiles: Mapping[str, Profile]) -> None:
        self._profiles = dict(profiles)

    @classmethod
    def from_directory(cls, root: Path) -> ProfileRegistry:
        profiles: dict[str, Profile] = {}
        paths = sorted([*root.rglob("*.yaml"), *root.rglob("*.yml")])
        for path in paths:
            profile = load_profile(path)
            if profile.id in profiles:
                other = profiles[profile.id].source_path
                raise ProfileRegistryError(
                    f"duplicate profile id {profile.id!r}: {other} and {profile.source_path}"
                )
            profiles[profile.id] = profile
        return cls(profiles)

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._profiles))

    def get(self, profile_id: str) -> Profile:
        try:
            return self._profiles[profile_id]
        except KeyError as exc:
            raise ProfileRegistryError(f"unknown profile id {profile_id!r}") from exc

    def resolve(self, profile_id: str) -> ResolvedProfile:
        return self._resolve(profile_id, stack=())

    def _resolve(self, profile_id: str, stack: tuple[str, ...]) -> ResolvedProfile:
        if profile_id in stack:
            cycle = " -> ".join((*stack, profile_id))
            raise ProfileRegistryError(f"profile reference cycle: {cycle}")
        profile = self.get(profile_id)
        next_stack = (*stack, profile_id)

        references: list[ResolvedReference] = []
        for name, referenced_id in sorted(profile.references.items()):
            resolved = self._resolve(referenced_id, next_stack)
            references.append(
                ResolvedReference(
                    name=name,
                    profile_id=resolved.id,
                    profile_hash=resolved.profile_hash,
                )
            )

        config = merge_defaults(profile.defaults, profile.config)
        payload = {
            "schema": profile.schema,
            "kind": profile.kind.value,
            "id": profile.id,
            "version": profile.version,
            "config": config,
            "references": [
                {
                    "name": ref.name,
                    "profile_id": ref.profile_id,
                    "profile_hash": ref.profile_hash,
                }
                for ref in references
            ],
        }
        digest = canonical_hash(payload)
        return ResolvedProfile(
            schema=profile.schema,
            kind=profile.kind,
            id=profile.id,
            version=profile.version,
            config=config,
            references=tuple(references),
            profile_hash=digest,
            source_path=profile.source_path,
        )

    def resolve_all(self) -> tuple[ResolvedProfile, ...]:
        return tuple(self.resolve(profile_id) for profile_id in self.ids())
