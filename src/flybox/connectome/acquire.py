"""Atomic, fail-closed acquisition for versioned connectome datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from flybox.provenance.schema import validate_manifest

from .hashes import sha256_file
from .registry import DatasetFileSpec, DatasetSpec, load_dataset_spec

_CHUNK_SIZE = 8 * 1024 * 1024


class AcquisitionError(RuntimeError):
    """Dataset acquisition or verification failed."""


class ResponseLike(Protocol):
    def read(self, size: int = -1) -> bytes: ...
    def close(self) -> None: ...


Opener = Callable[[str], ResponseLike]


def _default_opener(url: str) -> ResponseLike:
    response = urllib.request.urlopen(url, timeout=60)  # noqa: S310 - reviewed registry URLs
    return cast(ResponseLike, response)


def _git_revision(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AcquisitionError("unable to determine FlyBox code revision") from exc
    revision = result.stdout.strip()
    if not revision:
        raise AcquisitionError("empty FlyBox code revision")
    return revision


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def _verify_existing(
    path: Path,
    spec: DatasetFileSpec,
    *,
    allow_unpinned: bool,
) -> tuple[str, int]:
    digest, size = sha256_file(path)
    if spec.expected_sha256 is None or spec.expected_bytes is None:
        if not allow_unpinned:
            raise AcquisitionError(
                f"{spec.key}: source is not pinned; use --bootstrap-hashes "
                "for an explicit audit run"
            )
        return digest, size
    if digest != spec.expected_sha256 or size != spec.expected_bytes:
        raise AcquisitionError(
            f"{spec.key}: cached file mismatch: sha256={digest} bytes={size}, "
            f"expected sha256={spec.expected_sha256} bytes={spec.expected_bytes}"
        )
    return digest, size


def _download(
    spec: DatasetFileSpec,
    target: Path,
    *,
    opener: Opener,
    allow_unpinned: bool,
) -> tuple[str, int]:
    if not spec.pinned and not allow_unpinned:
        raise AcquisitionError(
            f"{spec.key}: source is not pinned; bootstrap hashes must be reviewed first"
        )
    partial = target.with_suffix(target.suffix + ".partial")
    partial.unlink(missing_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    total = 0
    try:
        with closing(opener(spec.url)) as response, partial.open("wb") as output:
            while chunk := response.read(_CHUNK_SIZE):
                output.write(chunk)
                digest.update(chunk)
                total += len(chunk)
        actual = digest.hexdigest()
        if spec.expected_sha256 is not None and actual != spec.expected_sha256:
            raise AcquisitionError(
                f"{spec.key}: downloaded SHA-256 mismatch: {actual} != {spec.expected_sha256}"
            )
        if spec.expected_bytes is not None and total != spec.expected_bytes:
            raise AcquisitionError(
                f"{spec.key}: downloaded size mismatch: {total} != {spec.expected_bytes}"
            )
        os.replace(partial, target)
        return actual, total
    except AcquisitionError:
        partial.unlink(missing_ok=True)
        raise
    except (OSError, urllib.error.URLError) as exc:
        partial.unlink(missing_ok=True)
        raise AcquisitionError(f"{spec.key}: download failed: {exc}") from exc
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def acquire_dataset(
    spec: DatasetSpec,
    data_dir: Path,
    *,
    code_revision: str,
    verify_only: bool = False,
    bootstrap_hashes: bool = False,
    opener: Opener = _default_opener,
) -> dict[str, object]:
    """Acquire/verify all source files and emit a provenance-valid source manifest."""

    if verify_only and bootstrap_hashes:
        raise AcquisitionError("--verify-only and --bootstrap-hashes are mutually exclusive")
    if not spec.fully_pinned and not bootstrap_hashes:
        raise AcquisitionError(
            f"dataset {spec.id!r} is not fully pinned; run an explicit bootstrap-hash audit first"
        )

    root = data_dir / spec.id
    raw_dir = root / "raw"
    records: list[dict[str, object]] = []
    for item in spec.files:
        target = raw_dir / item.filename
        if target.exists():
            digest, size = _verify_existing(target, item, allow_unpinned=bootstrap_hashes)
        else:
            if verify_only:
                raise AcquisitionError(f"{item.key}: missing required file {target}")
            digest, size = _download(
                item,
                target,
                opener=opener,
                allow_unpinned=bootstrap_hashes,
            )
        records.append(
            {
                "name": item.filename,
                "url": item.url,
                "bytes": size,
                "sha256": digest,
                "license_id": spec.license_id,
            }
        )

    retrieved_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    manifest: dict[str, object] = {
        "schema": "flybox.dataset-manifest/v1",
        "id": spec.id,
        "release": spec.release,
        "license_id": spec.license_id,
        "retrieved_at": retrieved_at,
        "code_revision": code_revision,
        "profile_hash": spec.profile_hash,
        "source_page": spec.source_page,
        "source_checked": spec.source_checked,
        "attribution": spec.attribution,
        "files": records,
    }
    validate_manifest(manifest)
    _atomic_json(root / "source-manifest.json", manifest)

    if bootstrap_hashes:
        candidate = {
            "schema": "flybox.dataset-lock-candidate/v1",
            "status": "UNREVIEWED_BOOTSTRAP_CANDIDATE",
            "dataset": spec.id,
            "release": spec.release,
            "source_page": spec.source_page,
            "generated_at": retrieved_at,
            "files": {
                item.key: {
                    "filename": record["name"],
                    "url": record["url"],
                    "expected_sha256": record["sha256"],
                    "expected_bytes": record["bytes"],
                }
                for item, record in zip(spec.files, records, strict=True)
            },
        }
        _atomic_json(root / "bootstrap-lock-candidate.json", candidate)

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset")
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--bootstrap-hashes", action="store_true")
    args = parser.parse_args()

    try:
        spec = load_dataset_spec(args.config_dir, args.dataset)
        manifest = acquire_dataset(
            spec,
            args.data_dir,
            code_revision=_git_revision(args.repo_root),
            verify_only=args.verify_only,
            bootstrap_hashes=args.bootstrap_hashes,
        )
    except (AcquisitionError, ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
