"""CLI for validating FlyBox provenance manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .schema import ProvenanceError, validate_manifest


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProvenanceError(("$: top-level manifest must be a JSON object",))
    return data


def validate_path(path: Path) -> None:
    validate_manifest(load_json(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        validate_path(args.manifest)
    except (OSError, json.JSONDecodeError, ProvenanceError) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"valid: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
