"""Serialization helpers for resolved immutable profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ResolvedProfile


def resolved_profile_dict(profile: ResolvedProfile) -> dict[str, Any]:
    return {
        "schema": profile.schema,
        "kind": profile.kind.value,
        "id": profile.id,
        "version": profile.version,
        "config": profile.config,
        "references": [
            {
                "name": ref.name,
                "profile_id": ref.profile_id,
                "profile_hash": ref.profile_hash,
            }
            for ref in profile.references
        ],
        "profile_hash": profile.profile_hash,
        "source_path": profile.source_path.as_posix(),
    }


def write_resolved_profile(profile: ResolvedProfile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(resolved_profile_dict(profile), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
