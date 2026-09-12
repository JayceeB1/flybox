from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
import pyarrow.ipc as ipc
import pytest

from flybox.config import ProfileRegistry
from flybox.connectome.hashes import sha256_file
from flybox.connectome.ids import BiologicalIdError, exact_uint64_ids, json_id
from flybox.connectome.normalize import NormalizationError, normalize_malecns
from flybox.provenance.schema import validate_manifest


def write_fixture_profiles(config_root: Path, hashes: dict[str, tuple[str, int]]) -> None:
    dataset = config_root / "datasets" / "fixture.yaml"
    dataset.parent.mkdir(parents=True, exist_ok=True)
    dataset.write_text(
        "\n".join(
            [
                "schema: flybox.profile/v1",
                "kind: dataset",
                "id: fixture_dataset",
                'version: "1"',
                "config:",
                "  release: Fixture v1",
                "  license_id: CC-BY-4.0",
                "  source_page: https://example.invalid/download/",
                '  source_checked: "2026-09-12"',
                "  attribution: Fixture authors",
                "  files:",
                *[
                    line
                    for key, filename in [
                        ("annotations", "annotations.feather"),
                        ("neurotransmitters", "neurotransmitters.feather"),
                        ("edges", "edges.feather"),
                    ]
                    for line in [
                        f"    {key}:",
                        f"      filename: {filename}",
                        f"      url: https://fixture.invalid/{filename}",
                        f'      expected_sha256: "{hashes[key][0]}"',
                        f"      expected_bytes: {hashes[key][1]}",
                    ]
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    normalization = config_root / "normalization" / "fixture.yaml"
    normalization.parent.mkdir(parents=True, exist_ok=True)
    normalization.write_text(
        """schema: flybox.profile/v1
kind: normalization
id: fixture_canonical
version: "1"
references:
  dataset: fixture_dataset
config:
  node_policy:
    require_nonempty_superclass: true
    exclude_status: [Glia]
  edge_policy:
    retain_edges_between_retained_nodes: true
    additional_min_contact_count: null
    retain_autapses: true
    ordering: upstream_source_row_order
  output:
    catalog: catalog.feather
    neurons: neurons.feather
    edges: edges.arrow
    manifest: normalization-manifest.json
""",
        encoding="utf-8",
    )


def write_fixture_source(config_root: Path, data_dir: Path) -> Path:
    root = data_dir / "fixture_dataset"
    raw = root / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    annotations = pa.table(
        {
            "bodyId": pa.array([40, 20, 10, 30], type=pa.uint64()),
            "superclass": pa.array(
                ["descending_neuron", "glia", "sensory", None],
                type=pa.string(),
            ),
            "status": pa.array(["Traced", "Glia", "Traced", "Traced"], type=pa.string()),
            "type": pa.array(["DN-test", "glia-test", "R-test", None], type=pa.string()),
            "statusLabel": pa.array(["good", "good", "good", "uncertain"], type=pa.string()),
        }
    )
    transmitters = pa.table(
        {
            "body": pa.array([10, 40], type=pa.uint64()),
            "consensus_nt": pa.array(["acetylcholine", "gaba"], type=pa.string()),
        }
    )
    edges = pa.table(
        {
            "body_pre": pa.array([10, 10, 40, 30], type=pa.uint64()),
            "body_post": pa.array([40, 20, 40, 10], type=pa.uint64()),
            "weight": pa.array([5, 3, 2, 1], type=pa.uint32()),
        }
    )

    feather.write_feather(annotations, raw / "annotations.feather", compression="uncompressed")
    feather.write_feather(
        transmitters,
        raw / "neurotransmitters.feather",
        compression="uncompressed",
    )
    feather.write_feather(edges, raw / "edges.feather", compression="uncompressed")

    hashes = {
        key: sha256_file(raw / filename)
        for key, filename in {
            "annotations": "annotations.feather",
            "neurotransmitters": "neurotransmitters.feather",
            "edges": "edges.feather",
        }.items()
    }
    write_fixture_profiles(config_root, hashes)
    profile_hash = ProfileRegistry.from_directory(config_root).resolve("fixture_dataset").profile_hash

    manifest = {
        "schema": "flybox.dataset-manifest/v1",
        "id": "fixture_dataset",
        "release": "Fixture v1",
        "license_id": "CC-BY-4.0",
        "retrieved_at": "2026-09-12T00:00:00Z",
        "code_revision": "fixture-source",
        "profile_hash": profile_hash,
        "files": [
            {
                "name": filename,
                "url": f"https://fixture.invalid/{filename}",
                "bytes": hashes[key][1],
                "sha256": hashes[key][0],
                "license_id": "CC-BY-4.0",
            }
            for key, filename in [
                ("annotations", "annotations.feather"),
                ("neurotransmitters", "neurotransmitters.feather"),
                ("edges", "edges.feather"),
            ]
        ],
    }
    validate_manifest(manifest)
    (root / "source-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return root


def normalize_fixture(config_root: Path, data_dir: Path) -> dict[str, object]:
    write_fixture_source(config_root, data_dir)
    return normalize_malecns(
        config_root=config_root,
        data_dir=data_dir,
        dataset_profile_id="fixture_dataset",
        normalization_profile_id="fixture_canonical",
        code_revision="normalizer-test",
    )


def test_exact_ids_reject_floats_and_json_ids_are_strings() -> None:
    with pytest.raises(BiologicalIdError, match="floating-point IDs"):
        exact_uint64_ids(np.asarray([10.0], dtype=np.float64))
    ids = exact_uint64_ids(["720575940000000001", 42])
    assert ids.dtype == np.uint64
    assert json_id(ids[0]) == "720575940000000001"


def test_normalization_accounts_nodes_edges_and_contacts(tmp_path: Path) -> None:
    config = tmp_path / "config"
    data = tmp_path / "data"
    manifest = normalize_fixture(config, data)

    assert manifest["evidence"] == "derived"
    assert manifest["physiology_applied"] is False
    assert manifest["neural_dynamics_validated"] is False

    nodes_report = manifest["nodes"]
    assert isinstance(nodes_report, dict)
    assert nodes_report["source_annotation_rows"] == 4
    assert nodes_report["retained_neurons"] == 2
    assert nodes_report["excluded_objects"] == 2

    graph = manifest["graph"]
    assert isinstance(graph, dict)
    assert graph["source_edge_rows"] == 4
    assert graph["retained_edge_rows"] == 2
    assert graph["excluded_edge_rows"] == 2
    assert graph["source_contacts"] == 11
    assert graph["retained_contacts"] == 7
    assert graph["excluded_contacts"] == 4
    assert graph["retained_autapses"] == 1
    assert graph["isolated_retained_neurons"] == 0


def test_normalized_tables_are_lossless_and_simulation_neutral(tmp_path: Path) -> None:
    config = tmp_path / "config"
    data = tmp_path / "data"
    normalize_fixture(config, data)
    output = data / "fixture_dataset" / "normalized"

    catalog = feather.read_table(output / "catalog.feather")
    assert catalog["source_id"].to_pylist() == [10, 20, 30, 40]
    assert catalog["retained"].to_pylist() == [True, False, False, True]
    assert catalog["neurotransmitter"].to_pylist() == ["acetylcholine", None, None, "gaba"]

    nodes = feather.read_table(output / "neurons.feather")
    assert nodes["node_index"].to_pylist() == [0, 1]
    assert nodes["source_id"].to_pylist() == [10, 40]

    edge_reader = ipc.open_file(pa.memory_map(str(output / "edges.arrow"), "r"))
    edge_table = edge_reader.read_all()
    assert edge_table.column_names == ["pre_index", "post_index", "contact_count"]
    assert edge_table["pre_index"].to_pylist() == [0, 1]
    assert edge_table["post_index"].to_pylist() == [1, 1]
    assert edge_table["contact_count"].to_pylist() == [5, 2]
    assert "weight" not in edge_table.column_names
    assert "sign" not in edge_table.column_names


def test_normalization_is_content_deterministic(tmp_path: Path) -> None:
    config_a = tmp_path / "config-a"
    data_a = tmp_path / "data-a"
    first = normalize_fixture(config_a, data_a)

    config_b = tmp_path / "config-b"
    data_b = tmp_path / "data-b"
    second = normalize_fixture(config_b, data_b)

    first_outputs = first["outputs"]
    second_outputs = second["outputs"]
    assert isinstance(first_outputs, dict)
    assert isinstance(second_outputs, dict)
    assert {
        key: value["sha256"] for key, value in first_outputs.items() if isinstance(value, dict)
    } == {
        key: value["sha256"] for key, value in second_outputs.items() if isinstance(value, dict)
    }


def test_normalization_rejects_raw_source_mutation(tmp_path: Path) -> None:
    config = tmp_path / "config"
    data = tmp_path / "data"
    root = write_fixture_source(config, data)
    with (root / "raw" / "annotations.feather").open("ab") as stream:
        stream.write(b"corruption")

    with pytest.raises(NormalizationError, match="does not match manifest"):
        normalize_malecns(
            config_root=config,
            data_dir=data,
            dataset_profile_id="fixture_dataset",
            normalization_profile_id="fixture_canonical",
            code_revision="normalizer-test",
        )
