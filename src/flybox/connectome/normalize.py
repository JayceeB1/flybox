"""Deterministic, simulation-neutral normalization of MaleCNS source tables."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
import pyarrow.ipc as ipc

from flybox.config import ProfileKind, ProfileRegistry
from flybox.provenance.schema import validate_manifest

from .hashes import sha256_file
from .ids import BiologicalIdError, exact_uint64_ids, require_unique_sorted
from .registry import DatasetSpec, load_dataset_spec


class NormalizationError(RuntimeError):
    """Source data or normalization configuration violated an invariant."""


@dataclass(frozen=True, slots=True)
class NormalizationSpec:
    id: str
    version: str
    profile_hash: str
    dataset_profile_hash: str
    require_nonempty_superclass: bool
    exclude_status: tuple[str, ...]
    additional_min_contact_count: int | None
    retain_autapses: bool
    edge_ordering: str
    catalog_filename: str
    neurons_filename: str
    edges_filename: str
    manifest_filename: str


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NormalizationError(f"{path}: expected mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise NormalizationError(f"{path}: keys must be non-empty strings")
    return value


def _bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise NormalizationError(f"{path}: expected boolean")
    return value


def _safe_filename(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise NormalizationError(f"{path}: expected non-empty filename")
    candidate = Path(value)
    if candidate.is_absolute() or candidate.name != value or value in {".", ".."}:
        raise NormalizationError(f"{path}: expected basename without path components")
    return value


def load_normalization_spec(config_root: Path, profile_id: str) -> NormalizationSpec:
    registry = ProfileRegistry.from_directory(config_root)
    resolved = registry.resolve(profile_id)
    if resolved.kind is not ProfileKind.NORMALIZATION:
        raise NormalizationError(
            f"profile {profile_id!r} has kind {resolved.kind.value!r}, expected 'normalization'"
        )
    refs = {reference.name: reference for reference in resolved.references}
    if set(refs) != {"dataset"}:
        raise NormalizationError("normalization profile must reference exactly one 'dataset' profile")

    config = _mapping(resolved.config, "config")
    if set(config) != {"node_policy", "edge_policy", "output"}:
        raise NormalizationError("normalization config requires node_policy, edge_policy and output")

    node = _mapping(config["node_policy"], "config.node_policy")
    if set(node) != {"require_nonempty_superclass", "exclude_status"}:
        raise NormalizationError("node_policy contains missing or unknown keys")
    exclude_status_raw = node["exclude_status"]
    if not isinstance(exclude_status_raw, list) or any(
        not isinstance(value, str) or not value for value in exclude_status_raw
    ):
        raise NormalizationError("config.node_policy.exclude_status: expected string array")

    edge = _mapping(config["edge_policy"], "config.edge_policy")
    required_edge_keys = {
        "retain_edges_between_retained_nodes",
        "additional_min_contact_count",
        "retain_autapses",
        "ordering",
    }
    if set(edge) != required_edge_keys:
        raise NormalizationError("edge_policy contains missing or unknown keys")
    if not _bool(
        edge["retain_edges_between_retained_nodes"],
        "config.edge_policy.retain_edges_between_retained_nodes",
    ):
        raise NormalizationError("canonical normalizer only supports retained-node induced edges")
    threshold = edge["additional_min_contact_count"]
    if threshold is not None and (
        not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1
    ):
        raise NormalizationError("additional_min_contact_count must be null or a positive integer")
    ordering = edge["ordering"]
    if ordering != "upstream_source_row_order":
        raise NormalizationError("only deterministic upstream_source_row_order is supported")

    output = _mapping(config["output"], "config.output")
    if set(output) != {"catalog", "neurons", "edges", "manifest"}:
        raise NormalizationError("output contains missing or unknown keys")

    return NormalizationSpec(
        id=resolved.id,
        version=resolved.version,
        profile_hash=resolved.profile_hash,
        dataset_profile_hash=refs["dataset"].profile_hash,
        require_nonempty_superclass=_bool(
            node["require_nonempty_superclass"],
            "config.node_policy.require_nonempty_superclass",
        ),
        exclude_status=tuple(exclude_status_raw),
        additional_min_contact_count=threshold,
        retain_autapses=_bool(edge["retain_autapses"], "config.edge_policy.retain_autapses"),
        edge_ordering=ordering,
        catalog_filename=_safe_filename(output["catalog"], "config.output.catalog"),
        neurons_filename=_safe_filename(output["neurons"], "config.output.neurons"),
        edges_filename=_safe_filename(output["edges"], "config.output.edges"),
        manifest_filename=_safe_filename(output["manifest"], "config.output.manifest"),
    )


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
        raise NormalizationError("unable to determine FlyBox code revision") from exc
    revision = result.stdout.strip()
    if not revision:
        raise NormalizationError("empty FlyBox code revision")
    return revision


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def _atomic_feather(table: pa.Table, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    feather.write_feather(table, partial, compression="uncompressed", version=2)
    os.replace(partial, path)


def _required_columns(table: pa.Table, names: set[str], source: str) -> None:
    missing = sorted(names - set(table.column_names))
    if missing:
        raise NormalizationError(f"{source}: missing required columns: {', '.join(missing)}")


def _text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _load_and_verify_source_manifest(
    dataset_root: Path,
    dataset: DatasetSpec,
) -> tuple[dict[str, Any], str]:
    manifest_path = dataset_root / "source-manifest.json"
    try:
        manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NormalizationError(f"unable to read source manifest: {exc}") from exc
    if not isinstance(manifest_raw, dict):
        raise NormalizationError("source manifest must be a JSON object")
    validate_manifest(manifest_raw)
    if manifest_raw.get("id") != dataset.id or manifest_raw.get("release") != dataset.release:
        raise NormalizationError("source manifest dataset identity does not match dataset profile")
    if manifest_raw.get("profile_hash") != dataset.profile_hash:
        raise NormalizationError("source manifest was not produced from the current dataset profile")
    records_raw = manifest_raw.get("files")
    if not isinstance(records_raw, list):
        raise NormalizationError("source manifest files must be an array")
    records: dict[str, Mapping[str, Any]] = {}
    for raw in records_raw:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("name"), str):
            raise NormalizationError("invalid source manifest file record")
        records[raw["name"]] = raw

    raw_root = dataset_root / "raw"
    for file_spec in dataset.files:
        record = records.get(file_spec.filename)
        if record is None:
            raise NormalizationError(f"source manifest missing {file_spec.filename}")
        if record.get("url") != file_spec.url or record.get("license_id") != dataset.license_id:
            raise NormalizationError(f"source manifest metadata mismatch for {file_spec.filename}")
        source_path = raw_root / file_spec.filename
        if not source_path.exists():
            raise NormalizationError(f"missing raw source file {source_path}")
        digest, size = sha256_file(source_path)
        if record.get("sha256") != digest or record.get("bytes") != size:
            raise NormalizationError(f"raw source file does not match manifest: {file_spec.filename}")
        if file_spec.expected_sha256 != digest or file_spec.expected_bytes != size:
            raise NormalizationError(f"raw source file does not match pinned profile: {file_spec.filename}")

    manifest_hash, _ = sha256_file(manifest_path)
    return manifest_raw, manifest_hash


def _file_for_key(dataset: DatasetSpec, key: str) -> str:
    for item in dataset.files:
        if item.key == key:
            return item.filename
    raise NormalizationError(f"dataset profile missing required source key {key!r}")


def _build_node_tables(
    annotations_path: Path,
    transmitters_path: Path,
    spec: NormalizationSpec,
) -> tuple[pa.Table, pa.Table, np.ndarray[Any, np.dtype[np.uint64]], dict[str, Any]]:
    annotations = feather.read_table(annotations_path)
    transmitters = feather.read_table(transmitters_path)
    _required_columns(annotations, {"bodyId", "superclass", "status", "type"}, "annotations")
    _required_columns(transmitters, {"body", "consensus_nt"}, "neurotransmitters")

    annotation_ids = exact_uint64_ids(annotations["bodyId"].to_numpy(zero_copy_only=False))
    if len(annotation_ids) != len(require_unique_sorted(annotation_ids)):
        raise NormalizationError("annotation ID accounting failure")
    if len(annotation_ids) and len(np.unique(annotation_ids)) != len(annotation_ids):
        raise NormalizationError("duplicate annotation body IDs")

    nt_ids = exact_uint64_ids(transmitters["body"].to_numpy(zero_copy_only=False))
    if len(nt_ids) and len(np.unique(nt_ids)) != len(nt_ids):
        raise NormalizationError("duplicate neurotransmitter body IDs")
    nt_values = transmitters["consensus_nt"].to_pylist()
    nt_by_id = {int(body): _text(value) for body, value in zip(nt_ids, nt_values, strict=True)}

    superclass = annotations["superclass"].to_pylist()
    status = annotations["status"].to_pylist()
    cell_type = annotations["type"].to_pylist()
    quality = (
        annotations["statusLabel"].to_pylist()
        if "statusLabel" in annotations.column_names
        else [None] * len(annotation_ids)
    )
    order = np.argsort(annotation_ids, kind="stable")

    source_ids: list[int] = []
    retained_values: list[bool] = []
    object_kind: list[str] = []
    inclusion_reason: list[str] = []
    qualities: list[str | None] = []
    superclasses: list[str | None] = []
    cell_types: list[str | None] = []
    nts: list[str | None] = []

    exclude_status = set(spec.exclude_status)
    for source_index in order:
        idx = int(source_index)
        body_id = int(annotation_ids[idx])
        current_superclass = _text(superclass[idx])
        current_status = _text(status[idx])
        has_superclass = current_superclass is not None and bool(current_superclass.strip())
        excluded_non_neural = current_status in exclude_status
        retained = (
            (has_superclass if spec.require_nonempty_superclass else True)
            and not excluded_non_neural
        )
        if excluded_non_neural:
            kind = "non_neuronal"
            reason = "explicit_excluded_status"
        elif retained:
            kind = "neuron_candidate"
            reason = "assigned_neuronal_superclass"
        else:
            kind = "unresolved_object"
            reason = "missing_required_superclass"

        source_ids.append(body_id)
        retained_values.append(retained)
        object_kind.append(kind)
        inclusion_reason.append(reason)
        qualities.append(_text(quality[idx]))
        superclasses.append(current_superclass)
        cell_types.append(_text(cell_type[idx]))
        nts.append(nt_by_id.get(body_id))

    catalog = pa.table(
        {
            "source_id": pa.array(source_ids, type=pa.uint64()),
            "retained": pa.array(retained_values, type=pa.bool_()),
            "object_kind": pa.array(object_kind, type=pa.string()),
            "inclusion_reason": pa.array(inclusion_reason, type=pa.string()),
            "quality": pa.array(qualities, type=pa.string()),
            "superclass": pa.array(superclasses, type=pa.string()),
            "cell_type": pa.array(cell_types, type=pa.string()),
            "neurotransmitter": pa.array(nts, type=pa.string()),
        }
    )
    retained_mask = np.asarray(retained_values, dtype=bool)
    retained_ids = np.asarray(source_ids, dtype=np.uint64)[retained_mask]
    if not len(retained_ids):
        raise NormalizationError("node policy retained zero neurons")
    retained_catalog = catalog.filter(pa.array(retained_mask))
    nodes = retained_catalog.add_column(
        0,
        "node_index",
        pa.array(np.arange(len(retained_ids), dtype=np.uint32), type=pa.uint32()),
    )
    report = {
        "source_annotation_rows": len(source_ids),
        "retained_neurons": len(retained_ids),
        "excluded_objects": int(len(source_ids) - len(retained_ids)),
        "object_kind_counts": dict(Counter(object_kind)),
        "inclusion_reason_counts": dict(Counter(inclusion_reason)),
        "superclass_counts_retained": dict(
            Counter(value or "unknown" for value, keep in zip(superclasses, retained_values) if keep)
        ),
        "neurotransmitter_counts_retained": dict(
            Counter(value or "missing" for value, keep in zip(nts, retained_values) if keep)
        ),
    }
    return catalog, nodes, retained_ids, report


def _edge_batch_arrays(
    batch: pa.RecordBatch,
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any], np.ndarray[Any, Any]]:
    names = set(batch.schema.names)
    required = {"body_pre", "body_post", "weight"}
    missing = sorted(required - names)
    if missing:
        raise NormalizationError(f"edges: missing required columns: {', '.join(missing)}")
    pre = batch.column(batch.schema.get_field_index("body_pre")).to_numpy(zero_copy_only=False)
    post = batch.column(batch.schema.get_field_index("body_post")).to_numpy(zero_copy_only=False)
    weight = batch.column(batch.schema.get_field_index("weight")).to_numpy(zero_copy_only=False)
    return pre, post, weight


def _normalize_edges(
    edges_path: Path,
    output_path: Path,
    retained_ids: np.ndarray[Any, np.dtype[np.uint64]],
    spec: NormalizationSpec,
) -> dict[str, int]:
    reader = ipc.open_file(pa.memory_map(str(edges_path), "r"))
    schema = pa.schema(
        [
            ("pre_index", pa.uint32()),
            ("post_index", pa.uint32()),
            ("contact_count", pa.uint32()),
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial = output_path.with_suffix(output_path.suffix + ".partial")
    partial.unlink(missing_ok=True)

    stats = {
        "source_edge_rows": 0,
        "retained_edge_rows": 0,
        "source_contacts": 0,
        "retained_contacts": 0,
        "source_autapses": 0,
        "retained_autapses": 0,
        "additional_threshold_excluded_rows": 0,
        "autapse_policy_excluded_rows": 0,
    }
    connected = np.zeros(len(retained_ids), dtype=bool)
    try:
        with pa.OSFile(str(partial), "wb") as sink:
            with ipc.new_file(sink, schema) as writer:
                for batch_index in range(reader.num_record_batches):
                    batch = reader.get_batch(batch_index)
                    pre_raw, post_raw, weight_raw = _edge_batch_arrays(batch)
                    pre = exact_uint64_ids(pre_raw)
                    post = exact_uint64_ids(post_raw)
                    weights = np.asarray(weight_raw)
                    if weights.ndim != 1 or len(weights) != len(pre) or len(pre) != len(post):
                        raise NormalizationError("edge columns have inconsistent lengths")
                    if weights.dtype.kind not in "iu":
                        raise NormalizationError("edge contact counts must be integer typed")
                    if weights.dtype.kind == "i" and np.any(weights < 1):
                        raise NormalizationError("edge contact counts must be positive")
                    weights_u64 = weights.astype(np.uint64, copy=False)
                    if np.any(weights_u64 < 1) or np.any(weights_u64 > np.iinfo(np.uint32).max):
                        raise NormalizationError("edge contact count outside uint32 range")

                    stats["source_edge_rows"] += len(pre)
                    stats["source_contacts"] += int(weights_u64.sum(dtype=np.uint64))
                    stats["source_autapses"] += int(np.count_nonzero(pre == post))

                    pre_pos = np.searchsorted(retained_ids, pre)
                    post_pos = np.searchsorted(retained_ids, post)
                    pre_valid = pre_pos < len(retained_ids)
                    post_valid = post_pos < len(retained_ids)
                    pre_match = np.zeros(len(pre), dtype=bool)
                    post_match = np.zeros(len(post), dtype=bool)
                    pre_match[pre_valid] = retained_ids[pre_pos[pre_valid]] == pre[pre_valid]
                    post_match[post_valid] = retained_ids[post_pos[post_valid]] == post[post_valid]
                    keep = pre_match & post_match

                    if spec.additional_min_contact_count is not None:
                        threshold_remove = keep & (weights_u64 < spec.additional_min_contact_count)
                        stats["additional_threshold_excluded_rows"] += int(
                            np.count_nonzero(threshold_remove)
                        )
                        keep &= ~threshold_remove
                    if not spec.retain_autapses:
                        autapse_remove = keep & (pre == post)
                        stats["autapse_policy_excluded_rows"] += int(
                            np.count_nonzero(autapse_remove)
                        )
                        keep &= ~autapse_remove

                    if not np.any(keep):
                        continue
                    pre_index = pre_pos[keep].astype(np.uint32)
                    post_index = post_pos[keep].astype(np.uint32)
                    counts = weights_u64[keep].astype(np.uint32)
                    stats["retained_edge_rows"] += len(pre_index)
                    stats["retained_contacts"] += int(counts.sum(dtype=np.uint64))
                    stats["retained_autapses"] += int(np.count_nonzero(pre[keep] == post[keep]))
                    connected[pre_index] = True
                    connected[post_index] = True
                    writer.write_batch(
                        pa.record_batch(
                            [
                                pa.array(pre_index, type=pa.uint32()),
                                pa.array(post_index, type=pa.uint32()),
                                pa.array(counts, type=pa.uint32()),
                            ],
                            schema=schema,
                        )
                    )
        os.replace(partial, output_path)
    except Exception:
        partial.unlink(missing_ok=True)
        raise

    stats["excluded_edge_rows"] = stats["source_edge_rows"] - stats["retained_edge_rows"]
    stats["excluded_contacts"] = stats["source_contacts"] - stats["retained_contacts"]
    stats["isolated_retained_neurons"] = int(np.count_nonzero(~connected))
    return stats


def normalize_malecns(
    *,
    config_root: Path,
    data_dir: Path,
    dataset_profile_id: str = "malecns_v1",
    normalization_profile_id: str = "malecns_v1_canonical",
    code_revision: str,
) -> dict[str, Any]:
    """Normalize a fully pinned and verified MaleCNS dataset."""

    dataset = load_dataset_spec(config_root, dataset_profile_id)
    spec = load_normalization_spec(config_root, normalization_profile_id)
    if not dataset.fully_pinned:
        raise NormalizationError("dataset profile must be fully pinned before normalization")
    if spec.dataset_profile_hash != dataset.profile_hash:
        raise NormalizationError("normalization profile references a different dataset profile hash")

    dataset_root = data_dir / dataset.id
    _, source_manifest_hash = _load_and_verify_source_manifest(dataset_root, dataset)
    raw_root = dataset_root / "raw"
    output_root = dataset_root / "normalized"

    catalog, nodes, retained_ids, node_report = _build_node_tables(
        raw_root / _file_for_key(dataset, "annotations"),
        raw_root / _file_for_key(dataset, "neurotransmitters"),
        spec,
    )
    catalog_path = output_root / spec.catalog_filename
    nodes_path = output_root / spec.neurons_filename
    edges_path = output_root / spec.edges_filename
    _atomic_feather(catalog, catalog_path)
    _atomic_feather(nodes, nodes_path)
    edge_report = _normalize_edges(
        raw_root / _file_for_key(dataset, "edges"),
        edges_path,
        retained_ids,
        spec,
    )

    outputs: dict[str, dict[str, Any]] = {}
    for key, path in {
        "catalog": catalog_path,
        "neurons": nodes_path,
        "edges": edges_path,
    }.items():
        digest, size = sha256_file(path)
        outputs[key] = {"path": path.name, "sha256": digest, "bytes": size}

    manifest: dict[str, Any] = {
        "schema": "flybox.provenance/v1",
        "id": spec.id,
        "kind": "normalized_connectome",
        "version": spec.version,
        "evidence": "derived",
        "license_id": dataset.license_id,
        "code_revision": code_revision,
        "inclusion_state": "derived",
        "derived_from": [f"sha256:{source_manifest_hash}"],
        "source": {
            "project": "MaleCNS",
            "release": dataset.release,
            "locators": [dataset.source_page],
        },
        "profile_hash": spec.profile_hash,
        "dataset_profile_hash": dataset.profile_hash,
        "source_manifest_sha256": source_manifest_hash,
        "node_policy": {
            "require_nonempty_superclass": spec.require_nonempty_superclass,
            "exclude_status": list(spec.exclude_status),
        },
        "edge_policy": {
            "additional_min_contact_count": spec.additional_min_contact_count,
            "retain_autapses": spec.retain_autapses,
            "ordering": spec.edge_ordering,
        },
        "nodes": node_report,
        "graph": edge_report,
        "outputs": outputs,
        "neural_dynamics_validated": False,
        "physiology_applied": False,
    }
    validate_manifest(manifest)
    _atomic_json(output_root / spec.manifest_filename, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--dataset", default="malecns_v1")
    parser.add_argument("--profile", default="malecns_v1_canonical")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    try:
        manifest = normalize_malecns(
            config_root=args.config_dir,
            data_dir=args.data_dir,
            dataset_profile_id=args.dataset,
            normalization_profile_id=args.profile,
            code_revision=_git_revision(args.repo_root),
        )
    except (BiologicalIdError, NormalizationError, ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
