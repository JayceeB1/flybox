"""Typed configuration profile models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class ProfileKind(StrEnum):
    DATASET = "dataset"
    NORMALIZATION = "normalization"
    BRAIN = "brain"
    BODY = "body"
    SENSORY_BRIDGE = "sensory_bridge"
    MOTOR_BRIDGE = "motor_bridge"
    SCHEDULER = "scheduler"
    EXPERIMENT = "experiment"
    ASSAY = "assay"


@dataclass(frozen=True, slots=True)
class Profile:
    schema: str
    kind: ProfileKind
    id: str
    version: str
    defaults: dict[str, Any]
    config: dict[str, Any]
    references: dict[str, str]
    source_path: Path


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    name: str
    profile_id: str
    profile_hash: str


@dataclass(frozen=True, slots=True)
class ResolvedProfile:
    schema: str
    kind: ProfileKind
    id: str
    version: str
    config: dict[str, Any]
    references: tuple[ResolvedReference, ...]
    profile_hash: str
    source_path: Path
