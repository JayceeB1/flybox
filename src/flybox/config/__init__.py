"""Typed, immutable scientific configuration profiles."""

from .canonical import CanonicalConfigError, canonical_hash, canonical_json
from .models import ProfileKind, ResolvedProfile
from .registry import ProfileRegistry, ProfileRegistryError

__all__ = [
    "CanonicalConfigError",
    "ProfileKind",
    "ProfileRegistry",
    "ProfileRegistryError",
    "ResolvedProfile",
    "canonical_hash",
    "canonical_json",
]
